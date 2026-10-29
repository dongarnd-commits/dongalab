import {useRef,useState,useEffect} from 'react';
import {CompanyError} from '../company/client';
import type {CompanyWorkflow} from './workflow';
import {storeAttachment} from './company-attachments';
import {BusinessCard,BusinessField,useBusinessDraft,input,primary,secondary} from './business-ui';
import {requestLabels,savedResponse,savedReview,sameIds,type ResponseRecord,type ReviewRecord} from './request-flow';
export type InformationItem={id:string;company_id:string;improvement_version_id?:string|null;title:string;message:string;due_date:string|null;sent_at?:string|null;sender_name?:string|null;state:string;response_ordinal:number;responses:ResponseRecord[];reviews:ReviewRecord[]};
type ResponseBody={expected_ordinal:number;message:string;submit:boolean;file_ids:string[]};
type ReviewBody={response_id:string;outcome:string;note:string};
export function InformationResponse({item,w,operator,load,command,onReviewed,expectedResponseId}:{item:InformationItem;w:CompanyWorkflow;operator:boolean;load:()=>Promise<InformationItem[]>;command:<T>(path:string,body:unknown)=>Promise<T>;onReviewed?:()=>void;expectedResponseId?:string}){
 const responses=[...item.responses].sort((a,b)=>a.ordinal-b.ordinal),latest=responses.at(-1),submitted=[...responses].reverse().find(r=>r.submitted);
 const [answer,setAnswer]=useBusinessDraft(w,'response:'+item.id,()=>({message:operator?'':latest?.message??'',files:[] as File[],fileIds:latest?.file_ids??[],expected:item.response_ordinal}));
 const uploaded=useRef(new Map<File,string>()),pendingResponse=useRef<ResponseBody|null>(null),pendingReview=useRef<ReviewBody|null>(null),lock=useRef(false),alive=useRef(true);
 const [uncertain,setUncertain]=useState(false),[localError,setLocalError]=useState(''),[uploadedFiles,setUploadedFiles]=useState(()=>new Set<File>());
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;};},[]);
 const editable=!operator&&['WAITING_RESPONSE','REVISION_REQUESTED'].includes(item.state);
 const changed=()=>window.dispatchEvent(new CustomEvent('datco-information-requests-changed',{detail:{company:w.cid}}));
 async function observe(){const rows=await load();const row=rows.find(r=>r.id===item.id);if(!row||row.company_id!==w.cid||row.improvement_version_id!==item.improvement_version_id)throw Error('요청 대상이 변경되었습니다.');return row;}
 function work(fn:()=>Promise<void>,message=''){if(lock.current||w.busy)return;lock.current=true;void w.run(fn,message).finally(()=>{lock.current=false;});}
 async function check(){
  const row=await observe();if(!alive.current)return;
  if(pendingReview.current){
   const body=pendingReview.current;
   if(savedReview(row.reviews,body,w.session.id)){pendingReview.current=null;setUncertain(false);changed();onReviewed?.();return;}
   if(row.state!=='REVIEW_REQUIRED'||row.responses.at(-1)?.id!==body.response_id)throw Error('최신 답변 또는 검토가 변경되었습니다. 이력을 확인하세요.');
   pendingReview.current=null;
  }
  if(pendingResponse.current){
   const body=pendingResponse.current,found=savedResponse(row.responses,body,w.session.id);
   if(found){setAnswer({...answer,message:found.message,fileIds:found.file_ids,files:[],expected:found.ordinal});pendingResponse.current=null;setUncertain(false);setLocalError('');await w.reload();return;}
   if(row.response_ordinal!==body.expected_ordinal)throw Error('다른 답변이 저장되었습니다. 최신 답변을 다시 확인하세요.');
   pendingResponse.current=null;
  }
  setUncertain(false);setLocalError('서버 이력을 확인했습니다. 필요한 경우 직접 다시 저장하세요.');
 }
 async function respond(submit:boolean){
  if(uncertain)return;setLocalError('');let ids=[...answer.fileIds];
  try{
   for(const file of answer.files){let id=uploaded.current.get(file);if(!id){id=(await storeAttachment(w,file)).id;uploaded.current.set(file,id);setUploadedFiles(new Set(uploaded.current.keys()));}ids.push(id);}
   ids=[...new Set(ids)];
   const body={message:answer.message,file_ids:ids,expected_ordinal:answer.expected,submit};pendingResponse.current=body;
   const saved=await command<ResponseRecord>('/information-requests/'+item.id+'/responses',body);
   const row=await observe();if(!alive.current)return;
   if(!row.responses.some(r=>r.id===saved.id))throw Error('저장된 답변을 다시 확인해야 합니다.');
   setAnswer({...answer,files:[],fileIds:ids,expected:saved.ordinal});pendingResponse.current=null;setUncertain(false);uploaded.current.clear();await w.reload();changed();
  }catch(e){
   if(!alive.current)throw e;
   const definite=e instanceof CompanyError&&[400,401,403,404,409,422].includes(e.status);
   setUncertain(!!pendingResponse.current&&!definite);if(definite)pendingResponse.current=null;
   setLocalError('자료 업로드와 답변 연결 저장은 별도입니다. 업로드된 원본은 보존하며 서버 상태를 확인한 뒤 재시도하세요.');
   try{await observe();await w.reload();}catch{/* Keep the original failure, no automatic write. */}
   throw e;
  }
 }
 async function review(outcome:string){
  if(!latest?.submitted||uncertain)return;
  const body={response_id:latest.id,outcome,note:answer.message};pendingReview.current=body;setLocalError('');
  try{
   const saved=await command<ReviewRecord>('/information-requests/'+item.id+'/review',body);
   const row=await observe();if(!alive.current)return;
   if(!row.reviews.some(r=>r.id===saved.id&&r.response_id===body.response_id)||row.state!==outcome)throw Error('검토 결과의 최신 상태를 확인해야 합니다.');
   pendingReview.current=null;changed();onReviewed?.();
  }catch(e){
   if(!alive.current)throw e;
   const definite=e instanceof CompanyError&&[400,401,403,404,409,422].includes(e.status);
   setUncertain(!definite);if(definite)pendingReview.current=null;
   setLocalError('검토 결과를 확인하지 못했습니다. 자동 복귀·재실행하지 않습니다. 서버 상태를 확인하세요.');
   try{await observe();}catch{/* Never retry a review automatically. */}
   throw e;
  }
 }
 const files=(reply:ResponseRecord)=><>{reply.file_ids.length?reply.file_ids.map(id=><p key={id}><a className={secondary} href={'/api/company/files/'+id+'/download'}>{w.detail?.files.find(f=>f.id===id)?.name??'첨부 원본'}</a></p>):<p>제출 첨부자료 없음</p>}</>;
 const current=operator?submitted:editable?undefined:submitted;
 return <article data-request-id={item.id}><BusinessCard title={item.title}><p>{!operator&&item.state==='REVIEW_REQUIRED'?'DATCO 담당자 확인 대기':requestLabels[item.state]} · 기업 응답 기한: {item.due_date??'미지정'}</p><p>{w.detail?.company.name}</p>
 {item.sent_at&&<p>발송 담당자 {operator?item.sender_name:'DATCO 담당자'} · {new Date(item.sent_at).toLocaleString('ko-KR')}</p>}
 {operator&&item.sender_name&&<details><summary>내부 발송 책임 정보</summary><p>{item.sender_name}</p></details>}
 {item.improvement_version_id&&<p>관련 제출본: {w.detail?.improvements.flatMap(i=>i.versions).find(v=>v.id===item.improvement_version_id)?.data.title} · v{w.detail?.improvements.flatMap(i=>i.versions).find(v=>v.id===item.improvement_version_id)?.ordinal}</p>}
 <details open={!current}><summary>발송된 요청 내용</summary><p className="whitespace-pre-wrap">{item.message}</p></details>
 {current&&<section aria-label="최신 제출 답변"><h4>{operator?'기업의 최신 제출 답변':'보완답변 제출 완료'}</h4>{!operator&&item.state==='REVIEW_REQUIRED'&&<p>DATCO 담당자 확인 대기</p>}<p className="whitespace-pre-wrap">{current.message}</p>{files(current)}{current.created_at&&<p>제출 일시: {new Date(current.created_at).toLocaleString('ko-KR')}</p>}</section>}
 {item.state==='REVISION_REQUESTED'&&<section aria-label="재보완 판단"><h4>DATCO 담당자의 재보완 요청</h4><p>{item.reviews.at(-1)?.note}</p><p>같은 요청의 다음 답변을 기다리고 있습니다.</p></section>}
 {expectedResponseId&&latest?.id!==expectedResponseId&&<p role="alert">목록 진입 후 답변 Version이 변경되었습니다. 최신 답변을 확인하세요.</p>}
 {localError&&<p role="alert">{localError}</p>}
 {uncertain&&<p role="alert">저장 결과가 불확실합니다. 확인 없이 같은 Action을 다시 실행하지 않습니다.</p>}
 {(uncertain||localError)&&<button className={secondary} disabled={w.busy} onClick={()=>work(check)}>답변·검토 저장 상태 확인</button>}
 {editable&&<section aria-label="현재 답변 작성"><h4>작성 중인 최신 답변</h4><p role="status">{w.busy?'저장 중':uncertain?'저장 결과 확인 필요':latest&&!latest.submitted&&answer.message===latest.message&&!answer.files.length&&sameIds(answer.fileIds,latest.file_ids)?'답변 초안 저장 완료':'저장되지 않은 변경사항'}</p><BusinessField label="보완 답변"><textarea aria-label="보완 답변" className={input} disabled={w.busy||uncertain} value={answer.message} maxLength={10000} onChange={e=>setAnswer({...answer,message:e.target.value})}/></BusinessField>
 <p>현재 답변에 포함할 첨부자료 {answer.fileIds.length}건</p>{answer.fileIds.map(id=><p key={id}>{w.detail?.files.find(f=>f.id===id)?.name??'저장된 첨부자료'} <button className={secondary} disabled={w.busy||uncertain} onClick={()=>setAnswer({...answer,fileIds:answer.fileIds.filter(v=>v!==id)})}>현재 답변에서 제외</button></p>)}
 <BusinessField label="답변 첨부자료"><input type="file" multiple disabled={w.busy||uncertain} onChange={e=>{setAnswer({...answer,files:[...answer.files,...Array.from(e.target.files??[])]});e.target.value='';}}/></BusinessField>
 <p>선택 파일 {answer.files.length}건</p>{answer.files.map((file,i)=><p key={i}>{file.name} · {file.size.toLocaleString()} bytes {uploadedFiles.has(file)&&'· 업로드 완료, 답변 연결 저장 확인 필요'} <button className={secondary} disabled={w.busy||uncertain} aria-label={file.name+' 선택 취소'} onClick={()=>setAnswer({...answer,files:answer.files.filter((_,n)=>n!==i)})}>선택 취소</button></p>)}
 {[false,true].map(submit=><button key={String(submit)} disabled={w.busy||uncertain||!answer.message.trim()} className={submit?primary:secondary} onClick={()=>work(()=>respond(submit),submit?'보완 답변을 제출했습니다.':'보완 답변 초안을 저장했습니다.')}>{submit?'보완답변 제출':'답변 초안 저장'}</button>)}</section>}
 {operator&&item.state==='REVIEW_REQUIRED'&&latest?.submitted&&<section aria-label="운영자 답변 판단"><BusinessField label="확인 또는 재보완 사유"><textarea className={input} value={answer.message} disabled={w.busy||uncertain} maxLength={5000} onChange={e=>setAnswer({...answer,message:e.target.value})}/></BusinessField>{['VERIFIED','REVISION_REQUESTED'].map(outcome=><button key={outcome} className={outcome==='VERIFIED'?primary:secondary} disabled={w.busy||uncertain||!answer.message.trim()||!!expectedResponseId&&latest.id!==expectedResponseId} onClick={()=>work(()=>review(outcome))}>{outcome==='VERIFIED'?'확인 완료':'재보완 요청'}</button>)}</section>}
 <details><summary>보완요청 및 답변 이력</summary><p className="whitespace-pre-wrap">{item.message}</p>{item.responses.filter(r=>r.id!==current?.id).map(reply=><section key={reply.id}><h4>작성 이력 v{reply.ordinal} · {reply.submitted?'제출한 답변':'저장한 초안'}</h4><p className="whitespace-pre-wrap">{reply.message}</p>{files(reply)}</section>)}{item.reviews.map(r=><p key={r.id}>{requestLabels[r.outcome]} · {r.note}{operator&&' · '+r.actor_id}</p>)}</details>
 </BusinessCard></article>;
}
