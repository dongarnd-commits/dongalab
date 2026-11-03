import {useEffect,useRef,useState} from 'react';
import type {CompanyWorkflow} from './workflow';
import {storeAttachment} from './company-attachments';
import {uploadAccept} from '../company/client';
import {FileSelection} from './file-selection';
import {BusinessCard,BusinessField,useBusinessDraft,input,primary,secondary} from './business-ui';

type Proposal={version_id:string;ordinal:number;title:string;created_at:string;sections:{heading:string;body:string}[];approval:{id:string;mode:string;state:string;closure_reason:string|null};files:{id:string;kind:string}[];decisions:{outcome:string;reason:string;created_at:string;authorization?:{actual_approver_name:string;actual_approver_title:string;approved_at:string;method:string;context:string;file_id:string|null;recorded_at:string;recorder_name:string}|null}[]};
const decisions:Record<string,string>={APPROVE:'승인 처리 완료',REVISION_REQUEST:'수정 요청 전달',REJECT:'진행하지 않음'};
async function request<T>(path:string,body?:unknown,signal?:AbortSignal):Promise<T>{
 const response=await fetch('/api/proposal'+path,{method:body===undefined?'GET':'POST',credentials:'same-origin',headers:body===undefined?undefined:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),signal,cache:'no-store'});
 if(!response.ok)throw Error(response.status===409?'현재 검토 대상이나 입력이 변경되었습니다. 최신 제안서를 다시 확인해 주세요.':response.status===422?'실제 승인권자·시각·승인근거를 모두 확인해 주세요.':response.status===401?'로그인 상태를 다시 확인해 주세요.':response.status===403||response.status===404?'이 계정에서 확인하거나 처리할 수 없는 제안서입니다. 담당자에게 지정 대상을 확인해 주세요.':'제안서를 조회하거나 처리하지 못했습니다. 연결 상태를 확인한 뒤 다시 조회해 주세요.');
 return response.json();
}
export function CompanyProposals({w}:{w:CompanyWorkflow}){
 const context=w.session.id+':'+w.cid,path='/inbox/'+w.cid;
 const [listing,setListing]=useState<{context:string;items:Proposal[]|null;error:string}>(()=>({context,items:null,error:''}));
 const [selected,setSelected]=useState(''),[refreshing,setRefreshing]=useState(false);
 const sequence=useRef(0),alive=useRef(true);
 const items=listing.context===context?listing.items:null,error=listing.context===context?listing.error:'';
 const active=items?.find(item=>item.version_id===selected);
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;};},[]);
 async function load(){
  const current=++sequence.current;setRefreshing(true);
  try{const value=await request<Proposal[]>(path);if(alive.current&&sequence.current===current)setListing({context,items:value,error:''});}
  catch(failure){if(alive.current&&sequence.current===current)setListing(previous=>({context,items:previous.context===context?previous.items:null,error:failure instanceof Error?failure.message:'제안서를 불러오지 못했습니다. 다시 조회해 주세요.'}));throw failure;}
  finally{if(alive.current&&sequence.current===current)setRefreshing(false);}
 }
 useEffect(()=>{
  const controller=new AbortController(),current=++sequence.current;
  void request<Proposal[]>(path,undefined,controller.signal).then(value=>{if(!controller.signal.aborted&&sequence.current===current)setListing({context,items:value,error:''});}).catch(failure=>{if(!controller.signal.aborted&&sequence.current===current)setListing({context,items:null,error:failure instanceof Error?failure.message:'제안서를 불러오지 못했습니다. 다시 조회해 주세요.'});});
  return()=>controller.abort();
 },[path,context]);
 return <><p className="mb-4 text-sm text-slate-600">현재 로그인한 계정이 검토 대상으로 지정된 제안서만 표시합니다. 회사 전체의 발송 현황이 아닙니다. 제안서가 보이지 않으면 DATCO 담당자에게 수신 계정을 확인해 주세요.</p>
 {((items===null&&!error)||refreshing)&&<p role="status">받은 제안서를 불러오고 있습니다.</p>}
 {error&&<p role="alert">{error}{items!==null&&' 아래 내용은 이전 조회 결과일 수 있습니다.'}</p>}
 {(items!==null||error)&&<button className={secondary+' mb-4'} disabled={w.busy||refreshing} onClick={()=>void w.run(load,'')}>{refreshing?'조회 중':'받은 제안서 다시 조회'}</button>}
 {items!==null&&!items.length&&!error&&<BusinessCard><p>현재 계정에 지정되어 발송된 제안서가 없습니다.</p><p>다른 담당자에게 발송된 제안서는 이 목록에 표시되지 않습니다.</p></BusinessCard>}
 {items?.map(item=><BusinessCard key={item.version_id} title={item.title}><article data-proposal-version-id={item.version_id}>
  <p>전달본 {item.ordinal} · {new Date(item.created_at).toLocaleString('ko-KR')} · {item.approval.state==='OPEN'?'검토 요청 도착':item.approval.closure_reason==='SUPERSEDED'?'새 전달본으로 대체된 과거 자료':'검토 기록 있음'}</p>
  <div className="my-3 flex flex-wrap gap-3"><button className={secondary} aria-pressed={selected===item.version_id} onClick={()=>setSelected(item.version_id)}>제안서 본문 확인</button>{item.files.map(file=><a key={file.id} className={secondary} href={'/api/proposal/files/'+file.id+'/download'}>{file.kind==='PDF'?'이 전달본 PDF':'이 전달본 DOCX'} 내려받기</a>)}</div>
  {item.decisions.map((decision,index)=><div className="my-4 rounded-xl bg-slate-50 p-4" key={index}><p>{decision.authorization&&decision.outcome==='APPROVE'?'내부 승인근거 전달 완료':decisions[decision.outcome]??'처리 기록'} · {decision.reason} · {new Date(decision.created_at).toLocaleString('ko-KR')}</p>{decision.authorization&&<><p>실제 승인권자: {decision.authorization.actual_approver_name} · {decision.authorization.actual_approver_title}</p><p>실제 승인 시각: {new Date(decision.authorization.approved_at).toLocaleString('ko-KR')} · {decision.authorization.method==='ORAL'?'구두 승인 기록':'결재 문서'}</p><p>기록 담당자: {decision.authorization.recorder_name} · 기록 시각 {new Date(decision.authorization.recorded_at).toLocaleString('ko-KR')}</p><p className="whitespace-pre-wrap">{decision.authorization.context}</p>{decision.authorization.file_id&&<a className={secondary} href={'/api/company/files/'+decision.authorization.file_id+'/download'}>보존된 결재 원본 내려받기</a>}</>}</div>)}
 </article></BusinessCard>)}
 {active&&<ProposalContents key={active.version_id} active={active} w={w} reload={load}/>}</>;
}
function ProposalContents({active,w,reload}:{active:Proposal;w:CompanyWorkflow;reload:()=>Promise<void>}){
 const [draft,setDraft]=useBusinessDraft(w,'proposal-authorization:'+active.version_id,()=>({name:'',title:'',time:'',method:'ORAL',context:'',file:null as File|null,reason:'',confirmed:false}));
 const record=active.approval.state==='OPEN'&&active.approval.mode==='COMPANY_RECORDED_AUTHORIZATION'&&w.session.role==='COMPANY_EDITOR';
 return <BusinessCard title={active.title+' · 전달본 '+active.ordinal}><div className="space-y-6"><p>이 전달본의 본문 {active.sections.length}개 항목</p>{active.sections.map((section,index)=><section key={index}><h3 className="font-bold">{section.heading}</h3><p className="whitespace-pre-wrap">{section.body}</p></section>)}</div>
 {active.approval.closure_reason==='SUPERSEDED'&&<p className="my-4">이전 전달본입니다. 현재 검토할 제안서는 목록에서 최신 전달본을 확인해 주세요.</p>}
 {record&&<form onSubmit={e=>e.preventDefault()}><p className="my-5 rounded-xl bg-amber-50 p-4">이 계정은 기업 내부에서 이미 승인받은 내용을 기록하도록 지정되어 있습니다. 실제 승인권자에게 확인한 뒤 근거를 전달해 주세요. 담당자의 기록은 승인권자 본인의 전자서명과 구분됩니다.</p>
 {([['name','실제 승인권자 성명'],['title','실제 승인권자 직책'],['time','실제 승인 시각']] as const).map(([key,label])=><BusinessField key={key} label={label}><input className={input} disabled={w.busy} type={key==='time'?'datetime-local':'text'} step={key==='time'?1:undefined} maxLength={200} value={draft[key]} onChange={e=>setDraft({...draft,[key]:e.target.value})}/></BusinessField>)}
 <BusinessField label="승인 방식"><select aria-label="승인 방식" className={input} disabled={w.busy} value={draft.method} onChange={e=>setDraft({...draft,method:e.target.value})}><option value="ORAL">구두 승인 기록</option><option value="DOCUMENT">결재 문서</option></select></BusinessField>
 <BusinessField label="승인 확인 방법·경위"><textarea className={input} disabled={w.busy} maxLength={5000} value={draft.context} onChange={e=>setDraft({...draft,context:e.target.value})}/></BusinessField>
 {draft.method==='DOCUMENT'&&<><FileSelection label="결재파일" accept={uploadAccept} files={draft.file?[draft.file]:[]} maxFiles={1} disabled={w.busy} hint="기존 내부 결재 원본 · 선택만으로 등록되지 않으며 승인근거 전달 시 저장합니다" onFiles={files=>{if(files[0])setDraft({...draft,file:files[0]});}} onRemove={()=>setDraft({...draft,file:null})}/><p className="my-3 text-sm text-slate-500">선택 취소는 아직 전달하지 않은 결재파일만 제외합니다. 보존된 결재 원본은 삭제하지 않습니다.</p></>}
 <BusinessField label="검토 의견·수정 요청사항"><textarea className={input} disabled={w.busy} maxLength={5000} value={draft.reason} onChange={e=>setDraft({...draft,reason:e.target.value})}/></BusinessField>
 <label className="my-4 block"><input type="checkbox" disabled={w.busy} checked={draft.confirmed} onChange={e=>setDraft({...draft,confirmed:e.target.checked})}/>현재 전달본 {active.ordinal}의 내용과 실제 승인근거를 확인했습니다.</label>
 <div className="flex flex-wrap gap-3">{(['REVISION_REQUEST','APPROVE'] as const).map(outcome=><button type="button" key={outcome} className={outcome==='APPROVE'?primary:secondary} disabled={w.busy||!draft.reason.trim()||(outcome==='APPROVE'&&(!draft.confirmed||!draft.name.trim()||!draft.title.trim()||!draft.time||(draft.method==='ORAL'?!draft.context.trim():!draft.file)))} onClick={()=>void w.run(async()=>{let authorization;if(outcome==='APPROVE'){const file=draft.method==='DOCUMENT'&&draft.file?await storeAttachment(w,draft.file):null;authorization={actual_approver_name:draft.name,actual_approver_title:draft.title,approved_at:new Date(draft.time).toISOString(),method:draft.method,context:draft.context,file_id:file?.id??null};}await request('/approvals/'+active.approval.id+'/decision',{outcome,reason:draft.reason,idempotency_key:crypto.randomUUID(),...(authorization?{authorization}:{})});await reload();setDraft({...draft,confirmed:false});},outcome==='APPROVE'?'기업 내부 승인근거와 처리 결과를 기록했습니다.':'제안서 수정 요청을 기록했습니다.')}>{outcome==='APPROVE'?'내부 승인근거 기록 및 승인 전달':'제안서 수정 요청'}</button>)}</div>
 </form>}
 </BusinessCard>;
}