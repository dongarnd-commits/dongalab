import {useEffect,useState,useRef,useId,useLayoutEffect} from 'react';
import type {CompanyWorkflow} from './workflow';
import {companyRequest,CompanyError} from '../company/client';
import {storeAttachment} from './company-attachments';
import {BusinessCard,BusinessField,useBusinessDraft,input,primary,secondary} from './business-ui';
type Reply={id:string;ordinal:number;message:string;submitted:boolean;file_ids:string[]};
type Item={id:string;title:string;message:string;due_date:string|null;sent_at?:string|null;sender_name?:string|null;state:string;response_ordinal:number;responses:Reply[];reviews:{id:string;outcome:string;note:string}[]};
const labels:Record<string,string>={DRAFT:'작성 중',WAITING_RESPONSE:'답변 대기',REVIEW_REQUIRED:'운영자 확인 대기',VERIFIED:'확인 완료',REVISION_REQUESTED:'재보완 요청'};

type Pending={context:string;company:string;versionTitle:string;ordinal?:number;versionId?:string;title:string;message:string;due:string;requestId?:string;uncertain?:boolean};
function SendConfirmation({pending,busy,onCancel,onSend,onCheck}:{pending:Pending;busy:boolean;onCancel:()=>void;onSend:()=>void;onCheck:()=>void}){
 const dialog=useRef<HTMLDialogElement>(null),cancel=useRef<HTMLButtonElement>(null),titleId=useId();
 useEffect(()=>{const previous=document.activeElement,d=dialog.current;d?.showModal();cancel.current?.focus();return()=>{d?.close();if(previous instanceof HTMLElement&&previous.isConnected)previous.focus();};},[]);
 return <dialog className="request-confirmation" ref={dialog} aria-labelledby={titleId} onCancel={e=>{e.preventDefault();if(!busy)onCancel();}}>
 <h2 id={titleId}>보완 요청 최종 확인</h2><dl><dt>요청 대상 기업</dt><dd>{pending.company}</dd><dt>개선요구·제출본</dt><dd>{pending.versionTitle} {pending.ordinal&&'· 제출본 v'+pending.ordinal}</dd><dt>요청 제목</dt><dd>{pending.title}</dd><dt>요청 내용</dt><dd className="whitespace-pre-wrap">{pending.message}</dd>{pending.due&&<><dt>응답 기한</dt><dd>{pending.due}</dd></>}</dl>
 {pending.versionId&&<details><summary>기술 상세정보</summary><p>Version ID: {pending.versionId}</p></details>}
 {pending.uncertain&&<p role="alert">저장·발송 결과를 확인하지 못했습니다. 요청 이력을 확인한 뒤 진행하세요. 확인 없이 새 요청을 만들지 않습니다.</p>}
 <div className="request-confirmation-actions"><button ref={cancel} type="button" disabled={busy} onClick={onCancel}>발송 취소</button>{pending.uncertain&&pending.requestId&&<button type="button" disabled={busy} onClick={onCheck}>저장·발송 상태 확인</button>}<button type="button" disabled={busy||pending.uncertain} onClick={onSend}>{busy?'처리 중':'최종 발송'}</button></div></dialog>;
}

export function InformationRequestsPanel({w,operator=false,improvementVersionId}:{w:CompanyWorkflow;operator?:boolean;improvementVersionId?:string}){
 const [items,setItems]=useState<Item[]|null>(null);
 const [draft,setDraft]=useBusinessDraft<{title:string;message:string;due:string;answers:Record<string,{message:string;files:File[];expected:number}>}>(w,'information-requests:'+(improvementVersionId??'company'),()=>({title:'',message:'',due:'',answers:{}}));
 const path='/'+w.cid+'/information-requests';
 const target=w.detail?.improvements.find(i=>i.versions.some(v=>v.id===improvementVersionId));
 const targetVersion=target?.versions.find(v=>v.id===improvementVersionId);
 const validTarget=!improvementVersionId||!!targetVersion;
 async function load(){setItems(await w.request<Item[]>(path));}
 useEffect(()=>{const controller=new AbortController();void companyRequest<Item[]>(path,undefined,controller.signal).then(value=>setItems(value)).catch(()=>{});return()=>controller.abort();},[path,w.session.id]);
 const command=<T,>(url:string,body:unknown)=>operator?companyRequest<T>(url,body):w.request<T>(url,body);
 const contextKey=w.session.id+':'+w.cid+':'+(improvementVersionId??'company');
 const currentContext=useRef(contextKey);useLayoutEffect(()=>{currentContext.current=contextKey;},[contextKey]);
 const alive=useRef(true),sending=useRef(false);const [unknownCreation,setUnknownCreation]=useState(false);
 const [pending,setPending]=useState<Pending|null>(null),[unresolved,setUnresolved]=useState<Pending|null>(null);
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;};},[]);
 const preview=pending?.context===contextKey?pending:null;
 const stillCurrent=(p:Pending)=>alive.current&&currentContext.current===p.context;
 function prepare(){if(!validTarget||unknownCreation||unresolved)return;setPending({context:contextKey,company:w.detail?.company.name??'',versionTitle:targetVersion?.data.title??'기업 공통 보완 요청',ordinal:targetVersion?.ordinal,versionId:improvementVersionId,title:draft.title,message:draft.message,due:draft.due});}
 function send(){
  const p=preview?{...preview}:null;if(!p||p.uncertain||sending.current||w.busy)return;
  void w.run(async()=>{
   if(!stillCurrent(p)||!validTarget)throw Error('대상 기업·Version을 다시 확인해 주세요.');
   sending.current=true;
   try{
    if(!p.requestId){const r=await command<{id:string}>(path,{title:p.title,message:p.message,due_date:p.due||null,...(p.versionId?{improvement_version_id:p.versionId}:{})});p.requestId=r.id;}
    if(!stillCurrent(p))return;
    await command('/information-requests/'+p.requestId+'/send',{});
    if(!stillCurrent(p))return;
    setPending(null);setUnresolved(null);setDraft({...draft,title:'',message:'',due:''});await load();
   }catch(error){
    if(error instanceof CompanyError&&[401,403,404].includes(error.status)){if(stillCurrent(p))setPending(null);throw error;}
    if(stillCurrent(p)){p.uncertain=true;if(!p.requestId)setUnknownCreation(true);setPending({...p});setUnresolved({...p});}
    throw Error('저장·발송 상태를 재확인해 주세요. 중복 발송을 막기 위해 자동 재시도하지 않습니다.');
   }finally{sending.current=false;}
  },'보완 요청을 발송했습니다.');
 }
 function checkState(){
  const p=preview;if(!p?.requestId)return;
  void w.run(async()=>{
   const list=await companyRequest<(Item&{company_id:string;improvement_version_id?:string})[]>(path);
   if(!stillCurrent(p))return;
   const r=list.find(r=>r.id===p.requestId);
   if(!r||r.company_id!==w.cid||(p.versionId&&r.improvement_version_id!==p.versionId))throw Error('요청 대상과 저장 상태를 확인할 수 없습니다.');
   if(r.state==='DRAFT'){setPending({...p,uncertain:false});setUnresolved({...p,uncertain:false});}
   else if(['WAITING_RESPONSE','REVIEW_REQUIRED','VERIFIED','REVISION_REQUESTED'].includes(r.state)){setPending(null);setUnresolved(null);setDraft({...draft,title:'',message:'',due:''});await load();}
   else throw Error('요청 상태를 다시 확인해 주세요.');
  },'요청 저장·발송 상태를 확인했습니다.');
 }

 return <>{preview&&<SendConfirmation pending={preview} busy={w.busy} onCancel={()=>setPending(null)} onSend={send} onCheck={checkState}/>} {unknownCreation&&<p role="alert">요청 생성 결과가 불확실합니다. 이력을 조회하고 저장 상태를 확인해 주세요.</p>}{unresolved&&!preview&&<p role="alert">기존 요청의 저장·발송 상태를 먼저 확인하세요. 새 요청을 자동 생성하지 않습니다.{unresolved.requestId&&<button type="button" onClick={()=>setPending({...unresolved})}>기존 요청 확인 계속</button>}</p>}{operator&&<BusinessCard title="보완 요청 작성">{improvementVersionId&&<div><p>요청 대상: {w.detail?.company.name} · {targetVersion?.data.title??'Version 확인 필요'} · 제출본 v{targetVersion?.ordinal??'미확인'}</p><details><summary>기술 상세정보</summary><p>Version ID: {improvementVersionId}</p></details></div>}<form onSubmit={e=>{e.preventDefault();prepare();}}><BusinessField label="요청 제목"><input required className={input} maxLength={300} value={draft.title} onChange={e=>setDraft({...draft,title:e.target.value})}/></BusinessField><BusinessField label="확인·보완할 내용"><textarea required className={input} maxLength={10000} value={draft.message} onChange={e=>setDraft({...draft,message:e.target.value})}/></BusinessField><BusinessField label="응답 기한"><input className={input} type="date" value={draft.due} onChange={e=>setDraft({...draft,due:e.target.value})}/></BusinessField><button className={primary} disabled={w.busy||!validTarget||unknownCreation||!!unresolved}>보완 요청 발송</button></form></BusinessCard>}
 {items===null?<button className={secondary} onClick={()=>void w.run(load,'')}>보완 요청 조회</button>:!items.length&&<BusinessCard><p>{operator?'보완 요청 이력이 없습니다.':'받은 보완 요청이 없습니다.'}</p></BusinessCard>}
 {items?.map(item=>{const latest=item.responses.at(-1),answer=draft.answers[item.id]??{message:operator?'':latest?.message??'',files:[],expected:item.response_ordinal};const set=(value:typeof answer)=>setDraft({...draft,answers:{...draft.answers,[item.id]:value}});return <BusinessCard key={item.id} title={item.title}><p>{labels[item.state]} {item.due_date&&'· 기한 '+item.due_date}</p>{item.sent_at&&<p className="my-2 text-sm text-slate-500">발송 담당자 {item.sender_name} · {new Date(item.sent_at).toLocaleString('ko-KR')}</p>}<p className="my-3 whitespace-pre-wrap">{item.message}</p>{item.responses.map(reply=><details key={reply.id}><summary>답변 {reply.ordinal} · {reply.submitted?'제출본':'저장한 초안'}</summary><p className="whitespace-pre-wrap">{reply.message}</p>{reply.file_ids.map(id=><p key={id}><a className={secondary} href={'/api/company/files/'+id+'/download'}>{w.detail?.files.find(f=>f.id===id)?.name??'첨부 원본'}</a></p>)}</details>)}{item.reviews.map(review=><p key={review.id} className="my-3 whitespace-pre-wrap">{labels[review.outcome]}: {review.note}</p>)}
 {!operator&&['WAITING_RESPONSE','REVISION_REQUESTED'].includes(item.state)&&<><BusinessField label="보완 답변"><textarea className={input} value={answer.message} maxLength={10000} onChange={e=>set({...answer,message:e.target.value})}/></BusinessField><BusinessField label="답변 첨부자료"><input type="file" multiple disabled={w.busy} onChange={e=>set({...answer,files:Array.from(e.target.files??[])})}/></BusinessField>{[false,true].map(submit=><button key={String(submit)} disabled={w.busy||!answer.message.trim()} className={submit?primary:secondary} onClick={()=>void w.run(async()=>{const fileIds=[...(latest?.file_ids??[])];for(const file of answer.files)fileIds.push((await storeAttachment(w,file)).id);const saved=await command<Reply>('/information-requests/'+item.id+'/responses',{message:answer.message,file_ids:[...new Set(fileIds)],expected_ordinal:answer.expected,submit});set({...answer,files:[],expected:saved.ordinal});await load();await w.reload();},submit?'보완 답변을 제출했습니다.':'보완 답변 초안을 저장했습니다.')}>{submit?'답변 제출':'답변 초안 저장'}</button>)}</>}
 {operator&&item.state==='REVIEW_REQUIRED'&&latest&&<><BusinessField label="확인 또는 재보완 사유"><textarea className={input} value={answer.message} maxLength={5000} onChange={e=>set({...answer,message:e.target.value})}/></BusinessField>{(['VERIFIED','REVISION_REQUESTED'] as const).map(outcome=><button key={outcome} className={secondary} disabled={w.busy||!answer.message.trim()} onClick={()=>void w.run(async()=>{await command('/information-requests/'+item.id+'/review',{response_id:latest.id,outcome,note:answer.message});await load();},outcome==='VERIFIED'?'보완 답변을 확인했습니다.':'재보완을 요청했습니다.')}>{labels[outcome]}</button>)}</>}
 </BusinessCard>;})}</>;
}
