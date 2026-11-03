import {useEffect,useState,useRef,useId,useLayoutEffect} from 'react';
import type {CompanyWorkflow} from './workflow';
import {companyRequest,CompanyError} from '../company/client';
import {InformationResponse,type InformationItem} from './information-response';
import {BusinessCard,BusinessField,useBusinessDraft,input,primary,secondary} from './business-ui';
type Item=InformationItem;
type Pending={context:string;company:string;versionTitle:string;ordinal?:number;versionId?:string;title:string;message:string;due:string;requestId?:string;uncertain?:boolean};
function SendConfirmation({pending,busy,onCancel,onSend,onCheck}:{pending:Pending;busy:boolean;onCancel:()=>void;onSend:()=>void;onCheck:()=>void}){
 const dialog=useRef<HTMLDialogElement>(null),cancel=useRef<HTMLButtonElement>(null),titleId=useId();
 useEffect(()=>{const previous=document.activeElement,d=dialog.current;d?.showModal();cancel.current?.focus();return()=>{d?.close();if(previous instanceof HTMLElement&&previous.isConnected)previous.focus();};},[]);
 return <dialog className="request-confirmation" ref={dialog} aria-labelledby={titleId} onCancel={e=>{e.preventDefault();if(!busy)onCancel();}}>
 <h2 id={titleId}>보완요청 발송 전 확인</h2><dl><dt>요청 대상 기업</dt><dd>{pending.company}</dd><dt>개선요구·제출본</dt><dd>{pending.versionTitle} {pending.ordinal&&'· 제출본 v'+pending.ordinal}</dd><dt>요청 제목</dt><dd>{pending.title}</dd><dt>요청 내용</dt><dd className="whitespace-pre-wrap">{pending.message}</dd><dt>기업 응답 기한</dt><dd>{pending.due||'미지정'}</dd></dl>
 {pending.versionId&&<details><summary>기술 상세정보</summary><p>Version ID: {pending.versionId}</p></details>}
 {pending.uncertain&&<p role="alert">저장·발송 결과를 확인하지 못했습니다. 요청 이력을 확인한 뒤 진행하세요. 확인 없이 새 요청을 만들지 않습니다.</p>}
 <div className="request-confirmation-actions"><button ref={cancel} type="button" disabled={busy} onClick={onCancel}>돌아가기</button>{pending.uncertain&&pending.requestId&&<button type="button" disabled={busy} onClick={onCheck}>저장·발송 상태 확인</button>}<button type="button" disabled={busy||pending.uncertain} onClick={onSend}>{busy?'처리 중':'수요기업에 발송하기'}</button></div></dialog>;
}

export function InformationRequestsPanel({w,operator=false,improvementVersionId,hideComposer=false,requestId,expectedResponseId,onReviewed,onSelectRequest}:{w:CompanyWorkflow;operator?:boolean;improvementVersionId?:string;hideComposer?:boolean;requestId?:string;expectedResponseId?:string;onReviewed?:()=>void;onSelectRequest?:(id:string,responseId?:string)=>void}){
 const listContext=w.session.id+':'+w.cid;
 const [listing,setListing]=useState<{context:string;items:Item[]|null;error:string}>(()=>({context:listContext,items:null,error:''}));
 const [refreshing,setRefreshing]=useState(false);
 const items=listing.context===listContext?listing.items:null,listError=listing.context===listContext?listing.error:'';
 const [draft,setDraft]=useBusinessDraft<{title:string;message:string;due:string;answers:Record<string,{message:string;files:File[];expected:number}>}>(w,'information-requests:'+(improvementVersionId??'company'),()=>({title:'',message:'',due:'',answers:{}}));
 const path='/'+w.cid+'/information-requests';
 const target=w.detail?.improvements.find(i=>i.versions.some(v=>v.id===improvementVersionId));
 const targetVersion=target?.versions.find(v=>v.id===improvementVersionId);
 const validTarget=!improvementVersionId||!!targetVersion;
 async function load(){setRefreshing(true);try{const rows=await w.request<Item[]>(path);if(alive.current)setListing({context:listContext,items:rows,error:''});return rows;}catch(error){if(alive.current)setListing(previous=>({context:listContext,items:previous.context===listContext?previous.items:null,error:'보완 요청을 불러오지 못했습니다. 연결 상태와 접근권한을 확인한 뒤 다시 조회해 주세요.'}));throw error;}finally{if(alive.current)setRefreshing(false);}}
 useEffect(()=>{const controller=new AbortController();void companyRequest<Item[]>(path,undefined,controller.signal).then(value=>{if(!controller.signal.aborted)setListing({context:listContext,items:value,error:''});}).catch(()=>{if(!controller.signal.aborted)setListing({context:listContext,items:null,error:'보완 요청을 불러오지 못했습니다. 받은 요청이 없는 것으로 판단하지 마세요. 다시 조회해 주세요.'});});return()=>controller.abort();},[path,listContext]);
 useEffect(()=>{const controller=new AbortController();const refresh=(event:Event)=>{if((event as CustomEvent<{company:string}>).detail?.company!==w.cid)return;void companyRequest<Item[]>(path,undefined,controller.signal).then(value=>{if(!controller.signal.aborted)setListing({context:listContext,items:value,error:''});}).catch(()=>{if(!controller.signal.aborted)setListing(previous=>({context:listContext,items:previous.context===listContext?previous.items:null,error:'최신 보완 요청을 확인하지 못했습니다. 아래에 이전 조회 결과가 있으면 최신 상태를 다시 확인해 주세요.'}));});};window.addEventListener('datco-information-requests-changed',refresh);return()=>{controller.abort();window.removeEventListener('datco-information-requests-changed',refresh);};},[path,w.cid,listContext]);
 const command=<T,>(url:string,body:unknown)=>operator?companyRequest<T>(url,body):w.request<T>(url,body);
 const contextKey=w.session.id+':'+w.cid+':'+(improvementVersionId??'company')+':'+(requestId??'');
 const currentContext=useRef(contextKey);useLayoutEffect(()=>{currentContext.current=contextKey;},[contextKey]);
 const alive=useRef(true),sending=useRef(false);const [unknownCreation,setUnknownCreation]=useState(false);
 const [pending,setPending]=useState<Pending|null>(null),[unresolved,setUnresolved]=useState<Pending|null>(null);
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;};},[]);
 const preview=pending?.context===contextKey?pending:null;
 const stillCurrent=(p:Pending)=>alive.current&&currentContext.current===p.context;
 function prepare(){if(!validTarget||unknownCreation||unresolved)return;setPending({context:contextKey,company:w.detail?.company.name??'',versionTitle:targetVersion?.data.title??'기업 공통정보 보완 요청',ordinal:targetVersion?.ordinal,versionId:improvementVersionId,title:draft.title,message:draft.message,due:draft.due});}
 function send(){
  const p=preview?{...preview}:null;if(!p||p.uncertain||sending.current||w.busy)return;
  void w.run(async()=>{
   if(!stillCurrent(p)||!validTarget)throw Error('대상 기업과 제출본을 다시 확인해 주세요.');
   sending.current=true;
   try{
    if(!p.requestId){const r=await command<{id:string}>(path,{title:p.title,message:p.message,due_date:p.due||null,...(p.versionId?{improvement_version_id:p.versionId}:{})});p.requestId=r.id;}
    if(!stillCurrent(p))return;
    await command('/information-requests/'+p.requestId+'/send',{});
    if(!stillCurrent(p))return;
    setPending(null);setUnresolved(null);setDraft({...draft,title:'',message:'',due:''});await load();window.dispatchEvent(new CustomEvent('datco-information-requests-changed',{detail:{company:w.cid}}));
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
   else if(['WAITING_RESPONSE','REVIEW_REQUIRED','VERIFIED','REVISION_REQUESTED'].includes(r.state)){setPending(null);setUnresolved(null);setDraft({...draft,title:'',message:'',due:''});await load();window.dispatchEvent(new CustomEvent('datco-information-requests-changed',{detail:{company:w.cid}}));}
   else throw Error('요청 상태를 다시 확인해 주세요.');
  },'요청 저장·발송 상태를 확인했습니다.');
 }

 return <>{preview&&<SendConfirmation pending={preview} busy={w.busy} onCancel={()=>setPending(null)} onSend={send} onCheck={checkState}/>} {unknownCreation&&<p role="alert">요청 생성 결과가 불확실합니다. 이력을 조회하고 저장 상태를 확인해 주세요.</p>}{unresolved&&!preview&&<p role="alert">기존 요청의 저장·발송 상태를 먼저 확인하세요. 새 요청을 자동 생성하지 않습니다.{unresolved.requestId&&<button type="button" onClick={()=>setPending({...unresolved})}>기존 요청 확인 계속</button>}</p>}{operator&&!hideComposer&&<details className="request-manual-compose"><summary>{improvementVersionId?'기존 분석과 별도의 수동 요청 작성':'새 기업 공통정보 보완요청 작성'}</summary><BusinessCard title="보완 요청 작성">{improvementVersionId&&<div><p>요청 대상: {w.detail?.company.name} · {targetVersion?.data.title??'제출본 확인 필요'} · 제출본 v{targetVersion?.ordinal??'미확인'}</p><details><summary>기술 상세정보</summary><p>Version ID: {improvementVersionId}</p></details></div>}<form onSubmit={e=>{e.preventDefault();prepare();}}><BusinessField label="요청 제목"><input required className={input} maxLength={300} value={draft.title} onChange={e=>setDraft({...draft,title:e.target.value})}/></BusinessField><BusinessField label="확인·보완할 내용"><textarea required className={input} maxLength={10000} value={draft.message} onChange={e=>setDraft({...draft,message:e.target.value})}/></BusinessField><BusinessField label="응답 기한"><input className={input} type="date" value={draft.due} onChange={e=>setDraft({...draft,due:e.target.value})}/></BusinessField><button className={primary} disabled={w.busy||!validTarget||unknownCreation||!!unresolved}>보완 요청 발송</button></form></BusinessCard></details>}
 {!operator&&<p className="mb-4 text-sm text-slate-600">선택한 기업에 발송된 보완 요청입니다. 같은 기업의 입력 담당자가 함께 확인·답변하는 목록이며, 현재 계정에만 지정된 제안서 목록과는 다릅니다.</p>}
 {((items===null&&!listError)||refreshing)&&<p role="status">보완 요청을 불러오고 있습니다.</p>}
 {listError&&<p role="alert">{listError}</p>}
 {(items!==null||listError)&&<button className={secondary+' mb-4'} disabled={w.busy||refreshing} onClick={()=>void w.run(async()=>{await load();},'')}>{refreshing?'조회 중':'보완 요청 다시 조회'}</button>}
 {items!==null&&!listError&&!items.filter(item=>item.company_id===w.cid&&(!operator||(item.improvement_version_id??'')===(improvementVersionId??''))&&(!requestId||item.id===requestId)).length&&<BusinessCard><p>{operator?'이 대상의 보완 요청 이력이 없습니다.':'선택한 기업에 받은 보완 요청이 없습니다.'}</p></BusinessCard>}
 {requestId&&items&&!items.some(r=>r.id===requestId&&r.company_id===w.cid&&(r.improvement_version_id??'')===(improvementVersionId??''))&&<p role="alert">요청 대상 기업과 제출본을 확인할 수 없습니다.</p>}
 {items?.filter(item=>item.company_id===w.cid&&(!operator||(item.improvement_version_id??'')===(improvementVersionId??''))&&(!requestId||item.id===requestId)).map(item=>operator&&!requestId&&onSelectRequest?<BusinessCard key={item.id} title={item.title}><p>{item.state==='REVIEW_REQUIRED'?'기업 답변 검토 필요':item.state==='VERIFIED'?'확인 완료':item.state==='REVISION_REQUESTED'?'재보완 요청':'보완요청 현황'}</p><button className={secondary} onClick={()=>onSelectRequest(item.id,item.responses.at(-1)?.submitted?item.responses.at(-1)?.id:undefined)}>{item.state==='REVIEW_REQUIRED'?'기업 답변 검토':'보완요청 현황'}</button></BusinessCard>:<InformationResponse key={item.id} item={item} w={w} operator={operator} load={load} command={command} onReviewed={onReviewed} expectedResponseId={expectedResponseId}/>)}
 </>;
}
