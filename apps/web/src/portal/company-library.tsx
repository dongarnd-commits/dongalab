import {usePortalWorkState} from './portal-work-state';
import {useEffect,useState} from 'react';
import {FileSelection} from './file-selection';
import {companyRequest,uploadAccept,maxUpload} from '../company/client';
import type {InformationItem} from './information-response';
import {storeAttachment} from './company-attachments';
import type {CompanyWorkflow} from './workflow';
import type {CompanyData} from '../company/client';
import {BusinessCard,primary,secondary,useBusinessDraft} from './business-ui';

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
 const [draft,setDraft]=useBusinessDraft<Record<string,File>>(w,'library-replacements',()=>({}));
 usePortalWorkState({dirty:Object.keys(draft).length>0},w.session.id+':'+w.cid+':library-replacements');
 const [selectionError,setSelectionError]=useState<Record<string,string>>({});
 const context=w.session.id+':'+w.cid;
 const [responseLinks,setResponseLinks]=useState<{context:string;items:InformationItem[]|null;error:boolean}>(()=>({context,items:null,error:false}));
 useEffect(()=>{const controller=new AbortController();void companyRequest<InformationItem[]>('/'+w.cid+'/information-requests',undefined,controller.signal).then(items=>{if(!controller.signal.aborted)setResponseLinks({context,items,error:false});}).catch(()=>{if(!controller.signal.aborted)setResponseLinks({context,items:null,error:true});});return()=>controller.abort();},[context,w.cid]);
 const requests=responseLinks.context===context?responseLinks.items:null,linksError=responseLinks.context===context&&responseLinks.error;
 const detail=w.detail;
 if(!detail)return <p role="status">첨부자료를 불러오고 있습니다.</p>;
 const active=detail.files.filter(file=>!file.lifecycle);
 function clear(fileId:string){setDraft(previous=>{const next={...previous};delete next[fileId];return next;});setSelectionError(previous=>({...previous,[fileId]:''}));}
 function select(fileId:string,files:File[]){
  if(!files.length)return;
  const file=files[0];
  if(files.length!==1||!file.size||file.size>maxUpload||!/\.(pdf|docx|xlsx|txt|png|jpe?g)$/i.test(file.name)){setSelectionError(previous=>({...previous,[fileId]:'교체할 파일 1개를 선택해 주세요. 지원 형식의 20MB 이하 파일만 사용할 수 있습니다.'}));return;}
  setDraft(previous=>({...previous,[fileId]:file}));setSelectionError(previous=>({...previous,[fileId]:''}));
 }
 return <><p className="mb-5 text-sm text-slate-600">현재 등록자료 {active.length}건입니다. 파일 교체와 등록 해제는 아래에서 따로 적용합니다. 이전 제출본과 원본 이력은 보존합니다.</p>
 {requests===null&&!linksError&&<p role="status">보완답변의 첨부 연결을 확인하고 있습니다.</p>}
 {linksError&&<p role="alert">보완답변에 연결된 자료를 확인하지 못했습니다. 일부 자료의 업무 분류가 미확인 상태입니다. 보완 요청함에서 연결을 확인하거나 이 화면을 다시 열어 주세요.</p>}
 {!active.length&&<BusinessCard><p>현재 등록된 첨부자료가 없습니다.</p><p>기업등록·재무·사업이력·개선요구 화면에서 자료를 첨부해 주세요.</p></BusinessCard>}
 {active.map(file=>{
  const matches=(ids:string[])=>ids.some(id=>detail.evidence.some(e=>e.id===id&&e.file_id===file.id));
  const versions=detail.improvements.flatMap(root=>root.versions.filter(v=>matches(v.data.evidence_ids)).map(v=>({root:root.id,title:v.data.title,ordinal:v.ordinal,current:v.ordinal===root.current_ordinal})));
  const currentNeeds=detail.improvements.filter(root=>root.versions.some(v=>v.ordinal===root.current_ordinal&&matches(v.data.evidence_ids)));
  const business=detail.business_extractions?.filter(item=>item.file_id===file.id)??[];
  const parseIds=new Set(business.map(item=>item.parse_id));
  const profile=detail.inputs.find(item=>item.ordinal===detail.company.current_ordinal)?.data;
  const financials=profile?.financials.filter(row=>row.source_parse_id&&parseIds.has(row.source_parse_id))??[];
  const history=profile?.history.filter(row=>row.source_parse_id&&parseIds.has(row.source_parse_id))??[];
  const factEvidence=detail.facts.some(fact=>fact.versions.some(v=>v.ordinal===fact.current_ordinal&&v.current_valid&&matches([v.evidence_id])));
  const candidateEvidence=detail.candidates.some(candidate=>matches([candidate.evidence_id]));
  const responseUses=requests?.filter(request=>request.responses.some(response=>response.ordinal===request.response_ordinal&&response.file_ids.includes(file.id)))??[];
  const oldResponse=(requests??[]).some(request=>request.responses.some(response=>response.ordinal!==request.response_ordinal&&response.file_ids.includes(file.id)));
  const uses=[...(responseUses.length?['저장된 보완답변 첨부']:[]),...(financials.length?['저장된 재무정보']:[]),...(history.length?['저장된 사업이력']:[]),...(currentNeeds.length?['현재 개선요구 첨부']:[]),...(factEvidence?['확인된 기업정보 근거']:[]),...(candidateEvidence&&!factEvidence?['기업정보 검토 후보의 근거']:[])];
  const oldBusiness=detail.inputs.some(item=>item.ordinal!==detail.company.current_ordinal&&[...item.data.financials,...item.data.history].some(row=>row.source_parse_id&&parseIds.has(row.source_parse_id)));
  const oldUses=versions.some(v=>!v.current)||oldBusiness||oldResponse;
  return <BusinessCard key={file.id}><article data-file-id={file.id}>
   <h3 className="mb-3 break-all font-bold">{file.name}</h3><p className="text-sm text-slate-500">등록일 {file.created_at?new Date(file.created_at).toLocaleDateString('ko-KR'):'확인 필요'}</p>
   <p className="my-3 text-sm">현재 확인되는 연결: {uses.join(' · ')||(requests===null?'일부 업무 연결 미확인':'업무 미분류')}</p>
   {!uses.length&&<p className="text-sm text-slate-500">{requests===null?'보완답변의 연결 여부는 아직 확인되지 않았습니다.':'현재 기업정보·개선요구·최신 보완답변에 저장된 연결이 확인되지 않습니다.'} 파일 내용이나 분석 시도만으로 분류하지 않습니다.</p>}
   {financials.map((row,index)=><p className="my-2 text-sm" key={'finance:'+index}>저장된 재무연도: {row.year}</p>)}
   {history.map((row,index)=><p className="my-2 text-sm" key={'history:'+index}>저장된 수행이력: {row.name} · {row.period}</p>)}
   {responseUses.map(request=><p className="my-2 text-sm" key={request.id}>연결된 보완 요청: {request.title}</p>)}
   {file.site_id&&<p>사업장: {detail.sites.find(s=>s.id===file.site_id)?.name??'확인 필요'}</p>}
   {currentNeeds.map(root=><p className="my-2 text-sm" key={root.id}>현재 연결된 개선요구: {root.title}</p>)}
   {oldUses&&<p className="text-sm text-slate-500">이전 저장본·제출본에도 연결된 자료입니다. 해당 업무의 이력에서 확인할 수 있습니다.</p>}
   <a className={secondary} href={'/api/company/files/'+file.id+'/download'}>원본 다운로드</a>
   <details className="my-4"><summary>파일 교체</summary><p className="my-3 text-sm">새 파일을 선택한 뒤 ‘파일 교체 적용’을 눌러야 반영됩니다. 단순 선택 취소는 등록된 원본에 영향을 주지 않습니다. 작성 중인 개선요구의 첨부는 허용된 경우 함께 바뀌며 이미 제출한 내용은 유지됩니다.</p>
    <FileSelection label={file.name+' 교체 파일'} accept={uploadAccept} files={draft[file.id]?[draft[file.id]]:[]} disabled={w.busy} maxFiles={1} hint="교체할 새 원본 1개 · 선택 후 아래 버튼으로 적용" onFiles={files=>select(file.id,files)} onRemove={()=>clear(file.id)}/>
    {selectionError[file.id]&&<p role="alert">{selectionError[file.id]}</p>}
    <button className={primary+' mt-3'} disabled={w.busy||!draft[file.id]} onClick={()=>{
     const selected=draft[file.id];if(!selected||!window.confirm(currentNeeds.some(root=>root.state==='DRAFT')?'선택한 파일로 교체할까요? 작성 중인 개선요구의 첨부도 변경하며, 이미 제출한 기록은 유지됩니다.':'선택한 파일로 교체할까요? 이미 제출한 자료의 기록은 변경되지 않습니다.'))return;
     void w.run(async()=>{try{await replaceFile(w,file,selected);clear(file.id);}catch(error){try{await w.reload();}catch{/* Preserve the original failure. */}throw error;}},'새 파일을 등록하고 기존 원본의 교체 이력을 저장했습니다.');
    }}>파일 교체 적용</button><p className="my-3 text-sm text-slate-500">교체가 완료되지 않으면 기존 원본과 선택 파일을 보존합니다. 업로드 후 연결 변경이 실패한 새 파일은 별도 등록자료로 남을 수 있으므로 현재 목록을 확인해 주세요.</p>
   </details>
   <button className={secondary} disabled={w.busy} onClick={()=>{if(!window.confirm('이 파일의 현재 등록을 해제할까요? 기존 원본은 영구 삭제되지 않으며 이미 제출한 기록도 유지됩니다. 현재 개선요구의 첨부는 해당 업무에서 따로 확인해 주세요.'))return;void w.run(async()=>{await w.request('/files/'+file.id+'/lifecycle',{kind:'CANCELLED',note:'기업 담당자가 현재 자료 등록 취소'});await w.reload();clear(file.id);},'현재 자료 등록을 해제했습니다. 원본과 이전 제출 이력은 보존합니다.');}}>자료 등록 해제</button>
   {(file.parses.length>0||versions.length>0)&&<details className="mt-4"><summary>분석·연결 이력 상세</summary>{file.parses.map((parse,index)=><p key={index}>{parse.error?'읽기 실패 기록':'자료 읽기 기록'} · 읽은 기록만으로 업무 연결이나 정보 확인이 완료되지는 않습니다.</p>)}{versions.map(v=><p key={v.root+':'+v.ordinal}>{v.title} · 저장본 {v.ordinal} · {v.current?'현재 연결':'이전 연결'}</p>)}</details>}
  </article></BusinessCard>;
 })}</>;
}