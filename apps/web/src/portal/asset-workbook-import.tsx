import {useRef,useState} from 'react';
import {portalApi} from './admin-live';
import {PortalErrorMessage,PortalRequestError} from './portal-feedback';
import {usePortalWorkState} from './portal-work-state';

type Data={system:string;feature_group:string;name:string;description:string;feature_id:string};
type Row={row_key:string;sheet:string;row:number;cells:Record<string,{cell:string;merged_range?:string}>;data:Data;status:'NEW'|'CHANGED'|'SAME'|'DUPLICATE_SUSPECT'|'UNKNOWN_ID';target_feature_id:string|null;candidates:(Omit<Data,'feature_id'>&{feature_id:string})[];previous:Omit<Data,'feature_id'>|null};
type Preview={filename:string;file_sha256:string;parser_version:string;catalog_digest:string;preview_digest:string;rows:Row[];unsupported:{sheet:string;row:number|null;reason:string;reason_codes?:string[]}[];limitations:string[]};
type Result={import_id:string|null;changed:number;unchanged:number;catalog_digest:string;file_sha256:string};
const labels:Record<Row['status'],string>={NEW:'신규',CHANGED:'변경',SAME:'동일',DUPLICATE_SUSPECT:'중복 의심 · 연결 확인',UNKNOWN_ID:'기존 ID 없음 · 연결 확인'};
const exception=(row:Row)=>row.status==='DUPLICATE_SUSPECT'||row.status==='UNKNOWN_ID';

export function AssetWorkbookImport({onApplied}:{onApplied?:()=>void|Promise<void>}){
 const [file,setFile]=useState<File|null>(null),[preview,setPreview]=useState<Preview|null>(null),[selected,setSelected]=useState<string[]>([]),[resolutions,setResolutions]=useState<Record<string,string>>({}),[advanced,setAdvanced]=useState<Record<string,boolean>>({}),[confirmed,setConfirmed]=useState(false),[page,setPage]=useState(1),[filter,setFilter]=useState(''),[busy,setBusy]=useState(false),[uncertain,setUncertain]=useState(false),[error,setError]=useState<Error|string>(''),[message,setMessage]=useState('');
 const gate=useRef(false),command=useRef<{signature:string;key:string}|null>(null);
 usePortalWorkState({dirty:!!preview&&(selected.length>0||Object.keys(resolutions).length>0),busy,uncertain});
 const rows=preview?.rows.filter(row=>!filter||row.status===filter)??[];
 const chosen=preview?.rows.filter(row=>selected.includes(row.row_key))??[];
 const invalid=chosen.some(row=>{const resolution=resolutions[row.row_key]?.trim();return exception(row)&&!resolution||!!resolution&&!/^(NEW|DMP-[A-F0-9]{16})$/.test(resolution);});
 async function inspect(){
  if(!file||gate.current)return;
  if(preview&&selected.length&&!window.confirm('확정하지 않은 등록 범위 선택을 버리고 새 자료를 비교할까요?'))return;
  gate.current=true;setBusy(true);setError('');setMessage('');
  try{
   const response=await fetch('/api/capability/asset-imports/preview',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','X-Upload-Name':encodeURIComponent(file.name)},body:file,cache:'no-store'});
   const data=await response.json();if(!response.ok)throw new PortalRequestError(data.reason??'UNKNOWN_ERROR');
   const value=data as Preview;setPreview(value);setSelected(value.rows.filter(row=>row.status==='NEW'||row.status==='CHANGED').map(row=>row.row_key));setResolutions({});setAdvanced({});setConfirmed(false);setPage(1);setFilter('');command.current=null;setUncertain(false);
   setMessage('비교 결과를 확인하세요. 원본 보관과 자료 비교만 완료했으며 기술자산 등록은 아직 확정하지 않았습니다.');
  }catch(e){setError(e instanceof Error?e:'자료 비교 실패');}finally{gate.current=false;setBusy(false);}
 }
 async function apply(){
  if(!preview||!confirmed||!chosen.length||invalid||gate.current)return;
  gate.current=true;setBusy(true);setError('');setMessage('');
  const body={file_sha256:preview.file_sha256,parser_version:preview.parser_version,catalog_digest:preview.catalog_digest,preview_digest:preview.preview_digest,selections:chosen.map(row=>({row_key:row.row_key,resolution:resolutions[row.row_key]?.trim()||null})).sort((a,b)=>a.row_key.localeCompare(b.row_key))};
  const signature=JSON.stringify(body);if(command.current?.signature!==signature)command.current={signature,key:crypto.randomUUID()};
  try{
   const result=await portalApi<Result>('capability','/asset-imports/apply',{...body,idempotency_key:command.current.key});
   setSelected([]);setResolutions({});setAdvanced({});setConfirmed(false);setPreview(null);command.current=null;setUncertain(false);
   setMessage(result.changed+'개 신규·변경 항목을 반영했습니다. 동일 '+result.unchanged+'개는 새 버전을 만들지 않았습니다. 파일에 없는 기존 항목과 과거 추천·전달 문서는 보존했습니다.');
   try{await onApplied?.();}catch{setError('등록은 완료됐으나 목록을 다시 조회하지 못했습니다. 기술자산 다시 조회를 눌러 확인하세요.');}
  }catch(e){
   setError(e instanceof Error?e:'등록 결과를 확인하지 못했습니다.');
   const known=e instanceof PortalRequestError&& !['API_UNAVAILABLE','STORAGE_UNAVAILABLE','UNKNOWN_ERROR'].includes(e.code);
   setUncertain(!known);
  }finally{gate.current=false;setBusy(false);}
 }
 function toggle(row:Row,checked:boolean){setSelected(checked?[...selected,row.row_key]:selected.filter(key=>key!==row.row_key));setConfirmed(false);}
 return <section className="da-box" data-testid="asset-workbook-import"><div className="da-box-heading"><h3>Excel 개발자료 등록·갱신</h3></div>
 <p>개발·보유 자료의 표를 기존 기술자산과 비교하고 선택한 항목만 반영합니다. 등록 확정은 제공 검증 완료나 실제 모듈 소속 확정이 아닙니다.</p>
 <details><summary>지원하는 Excel 표와 읽지 못하는 내용</summary><p>20MB 이하 XLSX만 지원합니다. 첫 행에 시스템, 기능그룹(또는 모듈), 기능명(또는 기능), 기능설명(또는 설명)을 두세요. 기존 원천을 명시하려면 원천기능ID 열을 사용합니다. system, feature_group, name, description, feature_id도 같은 필드명으로 지원하며 여러 시트를 비교할 수 있습니다.</p><p>system·feature_group의 명시적인 세로 병합만 분류값으로 읽습니다. 빈 셀의 임의 상속, 수식 계산, 도형·이미지, 날짜·단위·스타일 해석은 지원하지 않습니다. 지원하지 않는 행·시트·내용은 아래에서 따로 표시합니다.</p></details>
 <div className="da-detail-nav"><label>Excel 개발자료<input type="file" accept=".xlsx" disabled={busy||uncertain} onChange={e=>{const next=e.target.files?.[0]??null;if(next&&(!next.name.toLowerCase().endsWith('.xlsx')||next.size>20*1024*1024||!next.size)){setError('20MB 이하의 비어 있지 않은 XLSX 파일을 선택하세요.');return;}setFile(next);setError('');}}/></label><button className="da-btn da-btn-outline" disabled={busy||!file||uncertain} onClick={()=>void inspect()}>원본 보관·기존 자료와 비교</button></div>
 {busy&&<p role="status">{uncertain?'같은 등록 요청의 결과를 확인하고 있습니다.':'선택한 자료를 처리하고 있습니다. 잠시 기다려 주세요.'}</p>}{error&&<PortalErrorMessage error={error}/>}{message&&<p role="status">{message}</p>}
 {uncertain&&<p role="alert">등록 응답을 확인하지 못했습니다. 선택과 내용을 바꾸지 말고 아래 등록 버튼으로 같은 요청을 다시 확인하세요. 결과가 확인될 때까지 로그아웃할 수 없습니다.</p>}
 {preview&&<><p>{preview.filename} · 비교 가능한 표 항목 {preview.rows.length}개 · 미지원 위치 {preview.unsupported.length}곳</p><p>신규 {preview.rows.filter(r=>r.status==='NEW').length} · 변경 {preview.rows.filter(r=>r.status==='CHANGED').length} · 동일 {preview.rows.filter(r=>r.status==='SAME').length} · 예외 {preview.rows.filter(exception).length}</p>
 <a href={'/api/capability/asset-imports/'+preview.file_sha256+'/original'}>보관한 Excel 원본 다운로드</a><details><summary>비교 기준과 원본 식별</summary><p>파일 SHA256: {preview.file_sha256}</p><p>Parser: {preview.parser_version}</p><p>기술자산 기준: {preview.catalog_digest}</p></details>
 {!!preview.unsupported.length&&<details open><summary>읽지 못하거나 등록에서 제외한 위치 {preview.unsupported.length}곳</summary><ul>{preview.unsupported.map((item,i)=><li key={i}>{item.sheet}{item.row?' '+item.row+'행':''}: {item.reason}{!!item.reason_codes?.length&&<details><summary>담당자 확인용 상세 사유</summary><code>{item.reason_codes.join(' · ')}</code></details>}</li>)}</ul><p>이 위치는 정상 추출·등록 성공 건수에 포함하지 않습니다.</p></details>}
 <div className="da-detail-nav"><button className="da-btn da-btn-outline" disabled={busy||uncertain} onClick={()=>{setSelected(preview.rows.filter(row=>row.status==='NEW'||row.status==='CHANGED').map(row=>row.row_key));setConfirmed(false);}}>명확한 신규·변경 항목 묶음 선택</button><button className="da-btn da-btn-outline" disabled={busy||uncertain} onClick={()=>{setSelected([]);setConfirmed(false);}}>등록 선택 모두 해제</button><label>비교 결과 필터<select value={filter} disabled={busy||uncertain} onChange={e=>{setFilter(e.target.value);setPage(1);}}><option value="">모든 결과</option>{Object.entries(labels).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label></div>
 <div className="da-table-scroll"><table className="da-table"><thead><tr><th>등록 선택</th><th>원천 분류·기능</th><th>비교·예외 검토</th><th>원문 위치</th></tr></thead><tbody>{rows.slice((page-1)*20,page*20).map(row=><tr key={row.row_key}><td><input aria-label={row.data.name+' 등록 선택 '+row.row_key} type="checkbox" checked={selected.includes(row.row_key)} disabled={busy||uncertain} onChange={e=>toggle(row,e.target.checked)}/></td><td><strong>{row.data.name}</strong>{row.data.system} · {row.data.feature_group}<details><summary>이번 자료와 기존 내용</summary><p>{row.data.description||'설명 없음'}</p>{row.previous&&<p>기존: {row.previous.system} · {row.previous.feature_group} · {row.previous.name} · {row.previous.description}</p>}</details></td><td>{labels[row.status]}{row.target_feature_id&&<p>{row.target_feature_id}</p>}{exception(row)&&<><label>어떤 기존 기능의 자료인지 확인<select aria-label={'예외 연결 '+row.row_key} value={(!!resolutions[row.row_key]||advanced[row.row_key])&&!row.candidates.some(candidate=>candidate.feature_id===resolutions[row.row_key])&&resolutions[row.row_key]!=='NEW'?'CUSTOM':resolutions[row.row_key]??''} disabled={busy||uncertain} onChange={e=>{if(e.target.value==='CUSTOM'){setAdvanced({...advanced,[row.row_key]:true});setResolutions({...resolutions,[row.row_key]:''});}else{setAdvanced({...advanced,[row.row_key]:false});setResolutions({...resolutions,[row.row_key]:e.target.value});}setConfirmed(false);}}><option value="">연결할 기능 또는 별도 신규 등록 선택</option>{row.candidates.map(candidate=><option key={candidate.feature_id} value={candidate.feature_id}>{candidate.system} · {candidate.feature_group} · {candidate.name}</option>)}<option value="NEW">기존 기능과 다른 별도 신규 항목으로 등록</option><option value="CUSTOM">다른 기존 기능에 연결 (고급)</option></select></label><details open={advanced[row.row_key]??false} onToggle={e=>setAdvanced(previous=>({...previous,[row.row_key]:e.currentTarget.open}))}><summary>다른 기존 원천 ID 입력·식별 상세</summary><label>기존 원천기능ID<input aria-label={'고급 예외 연결 '+row.row_key} value={resolutions[row.row_key]??''} placeholder="기술자산 상세의 원천기능ID" disabled={busy||uncertain} onChange={e=>{setResolutions({...resolutions,[row.row_key]:e.target.value});setConfirmed(false);}}/></label>{row.candidates.map(candidate=><p key={candidate.feature_id}>{candidate.name}: {candidate.feature_id}</p>)}</details><p>유사한 이름·설명을 자동 병합하지 않습니다. 예외만 따로 확인하세요.</p></>}</td><td>{row.sheet} · {row.row}행<details><summary>필드별 원문 셀</summary>{Object.entries(row.cells).map(([field,location])=><p key={field}>{field}: {location.cell}{location.merged_range?' (명시 병합 '+location.merged_range+')':''}</p>)}</details></td></tr>)}</tbody></table></div>
 <div className="da-detail-nav"><button className="da-btn da-btn-outline" disabled={busy||page<=1} onClick={()=>setPage(page-1)}>이전 비교 페이지</button><span>{page} / {Math.max(1,Math.ceil(rows.length/20))} 페이지</span><button className="da-btn da-btn-outline" disabled={busy||page*20>=rows.length} onClick={()=>setPage(page+1)}>다음 비교 페이지</button></div>
 <p>선택 {chosen.length}개만 반영합니다. 동일 항목은 새 버전을 만들지 않으며 이번 파일에 빠진 기존 항목은 삭제하거나 제공 중단하지 않습니다.</p><label><input type="checkbox" checked={confirmed} disabled={busy||!chosen.length||invalid||uncertain} onChange={e=>setConfirmed(e.target.checked)}/>선택한 범위와 예외 연결을 검토했으며 자료 등록을 확정합니다.</label>
 {invalid&&<p>선택한 예외가 어느 기존 기능의 자료인지 또는 별도 신규 항목인지 확인하세요.</p>}<div className="da-detail-nav"><button className="da-btn da-btn-primary" disabled={busy||!chosen.length||invalid||!confirmed} onClick={()=>void apply()}>{uncertain?'같은 등록 요청 결과 다시 확인':'선택한 자료 등록 확정'}</button><button className="da-btn da-btn-outline" disabled={busy||uncertain} onClick={()=>{setPreview(null);setSelected([]);setResolutions({});setAdvanced({});setConfirmed(false);}}>확정하지 않고 비교 닫기</button></div>
 </>}
 </section>;
}
