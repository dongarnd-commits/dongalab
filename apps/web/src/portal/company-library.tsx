import {storeAttachment} from './company-attachments';
import type {CompanyWorkflow} from './workflow';
import type {CompanyData} from '../company/client';
import {BusinessCard,secondary} from './business-ui';

async function replaceFile(w:CompanyWorkflow,file:CompanyData['files'][number],selected:File){
 const before=await w.request<CompanyData>('/'+w.cid);
 const linked=before.improvements.filter(root=>root.versions.find(v=>v.ordinal===root.current_ordinal)?.data.evidence_ids.some(id=>before.evidence.some(e=>e.id===id&&e.file_id===file.id)));
 if(linked.length>1)throw Error('여러 업무에 연결된 파일입니다. 각 업무의 첨부자료를 먼저 확인해 주세요.');
 for(const root of linked){
  const cached=w.drafts.get(w.cid+':need-v13:'+root.id) as {data:unknown;base:unknown;files:File[];fileIds:string[]}|undefined;
  if(!cached)continue;
  const data=root.versions.find(v=>v.ordinal===root.current_ordinal)!.data;
  const savedIds=[...new Set(before.evidence.filter(e=>data.evidence_ids.includes(e.id)&&e.file_id).map(e=>e.file_id!))].sort();
  if(JSON.stringify(cached.data)!==JSON.stringify(cached.base)||cached.files.length||JSON.stringify([...new Set(cached.fileIds)].sort())!==JSON.stringify(savedIds))throw Error('개선요구의 작성 중인 내용을 먼저 저장한 뒤 파일을 교체해 주세요.');
 }
 const replacement=await storeAttachment(w,selected,file.site_id??'');
 if(replacement.id===file.id)throw Error('현재 파일과 다른 새 원본을 선택해 주세요.');
 try{await w.request('/files/'+file.id+'/lifecycle',{kind:'REPLACED',replacement_id:replacement.id,note:'기업 담당자가 새 원본과 작성 중인 첨부자료로 교체'});}
 catch(error){
  const current=await w.request<CompanyData>('/'+w.cid),event=current.files.find(f=>f.id===file.id)?.lifecycle;
  if(event?.kind!=='REPLACED'||event.replacement_id!==replacement.id)throw error;
 }
 const actual=await w.reload();
 for(const root of linked){if(actual?.improvements.find(i=>i.id===root.id)?.current_ordinal!==root.current_ordinal)w.drafts.delete(w.cid+':need-v13:'+root.id);}
}
export function CompanyLibrary({w}:{w:CompanyWorkflow}){
 return <>{!w.detail?.files.some(file=>!file.lifecycle)&&<BusinessCard><p>등록된 첨부자료가 없습니다.</p><p>기업등록·재무·사업이력·개선요구 화면에서 자료를 첨부해 주세요.</p></BusinessCard>}{w.detail?.files.filter(file=>!file.lifecycle).map(file=>{
  const versions=w.detail!.improvements.flatMap(root=>root.versions.filter(v=>v.data.evidence_ids.some(id=>w.detail!.evidence.some(e=>e.id===id&&e.file_id===file.id))).map(v=>({name:v.data.title,site:v.data.site_id})));
  const currentNeeds=w.detail!.improvements.filter(root=>root.versions.find(v=>v.ordinal===root.current_ordinal)?.data.evidence_ids.some(id=>w.detail!.evidence.some(e=>e.id===id&&e.file_id===file.id)));
  const parses=file.parses as (typeof file.parses[number]&{parser_version?:string})[];
  const business=w.detail!.business_extractions?.filter(item=>item.file_id===file.id)??[];
  const uses=[...new Set([...business.map(item=>item.kind==='finance'?'재무정보 분석':'사업이력 분석'),...parses.flatMap(p=>p.parser_version?.startsWith('company-business-finance-')?['재무정보 분석']:p.parser_version?.startsWith('company-business-history-')?['사업이력 분석']:p.parser_version?.startsWith('company-registration-')?['기업등록']:[]),...(versions.length?['개선요구']:[])])];
  return <BusinessCard key={file.id}><article data-file-id={file.id}><h3 className="mb-3 font-bold">{file.name}</h3><p className="text-sm text-slate-500">등록일 {file.created_at?new Date(file.created_at).toLocaleDateString('ko-KR'):'확인 필요'}</p><p className="my-3 text-sm">연결 업무: {uses.join(' · ')||'업무 미분류'}</p>{[...new Set(business.flatMap(item=>item.entries.map(entry=>item.kind==='finance'?'재무연도: '+entry.year:'수행이력: '+entry.name+' · '+entry.period+(entry.agency?' · '+entry.agency:''))))].map(label=><p className="my-2 text-sm" key={label}>{label}</p>)}{file.site_id&&<p>사업장: {w.detail!.sites.find(s=>s.id===file.site_id)?.name??'확인 필요'}</p>}{currentNeeds.map(root=><p className="my-2 text-sm" key={root.id}>현재 연결된 개선요구: {root.title.length>48?root.title.slice(0,48)+'…':root.title}</p>)}{versions.length>0&&<p className="text-sm text-slate-500">이전 제출 자료는 해당 업무에서 확인할 수 있습니다.</p>}{!file.lifecycle&&<div className="my-3 flex flex-wrap gap-3"><label className={secondary}>파일 교체<input className="block max-w-full" aria-label={file.name+' 교체 파일'} type="file" disabled={w.busy} onChange={e=>{const selected=e.target.files?.[0];e.currentTarget.value='';if(!selected||!window.confirm(currentNeeds.some(root=>root.state==='DRAFT')?'파일을 교체할까요? 작성 중인 개선요구의 첨부도 변경하며, 이미 제출한 기록은 유지됩니다.':'파일을 교체할까요? 이미 제출한 자료의 기록은 변경되지 않습니다.'))return;void w.run(()=>replaceFile(w,file,selected),'새 파일을 등록하고 기존 원본의 교체 이력을 저장했습니다.');}}/></label><button className={secondary} disabled={w.busy} onClick={()=>{if(!window.confirm('이 파일을 현재 자료함에서 제외할까요? 이미 제출한 자료의 기록은 변경되지 않습니다. 원본은 영구 삭제되지 않습니다.'))return;void w.run(async()=>{await w.request('/files/'+file.id+'/lifecycle',{kind:'CANCELLED',note:'기업 담당자가 현재 자료 등록 취소'});await w.reload();},'자료 등록 취소 이력을 저장했습니다.');}}>등록 취소</button></div>}<a className={secondary} href={'/api/company/files/'+file.id+'/download'}>원본 다운로드</a></article></BusinessCard>;
 })}</>;
}
