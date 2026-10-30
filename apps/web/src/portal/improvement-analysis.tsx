import {useCallback,useEffect,useId,useRef,useState,type ReactNode} from 'react';
import {companyRequest} from '../company/client';
import {ReviewCommands,usableReview,sameReviews} from './operator-review-flow';

type Provider={id:string;label:string;status:string;reason:string};
type StructuredResult={provider:string;provider_version:string;context:{company_id:string;improvement_version_id:string;input_digest:string};structure:Record<string,{text:string;uncertainty:string}[]|unknown>;limitations:string[]};
type Fresh={usable:boolean;reasons:string[];warnings:string[]};
type Evidence={kind:string;quote:string;field?:string;version_id?:string;evidence_id?:string;inspection_id?:string;file_id?:string;descriptor?:string;page?:number|null};
type Review={id:string;actor_id?:string;request_key?:string;ordinal:number;decision:string;note:string;question:string};
type Candidate={id:string;category:string;content:string;reason:string;data:{rule_id:string;rule_version:string;uncertainty:string;claim_kind:string;evidence:Evidence[];question?:string;search_scope?:{inspection_id:string;status:string;exclude_reason:string;locations:{page:number|null;descriptor:string}[]}[]};reviews:Review[]};
type Input={id:string;file_id:string|null;data:{name?:string;digest?:string;included?:boolean;exclude_reason?:string};origin:string};
type Run={diagnostics?:{structured_result?:StructuredResult};run:{id:string;created_at:string};manifest:{job_id:string;data:{input_policy?:string;common_file_ids?:string[]}};status:string;freshness:Fresh;candidates:Candidate[];inputs:Input[];inspections:{id:string;input_id:string;data:{status:string;method:string;parser_version?:string;reuse_verified?:boolean;scope_known?:boolean;error_code?:string;limitations:string[];locations:{page:number|null;descriptor:string}[]}}[]};
type Sources={selection_token:string;files:{id:string;name:string;direct:boolean;inactive:boolean;supported:boolean;default_included:boolean;parse_id:string|null}[]};
type DraftVersion={id:string;request_key?:string;ordinal:number;title:string;message:string;due_date:string|null;review_ids:string[]};
type Draft={id:string;request_key?:string;company_id:string;version_id:string;run_id:string;versions:DraftVersion[];deliveries:{request_id:string}[];freshness:Fresh};
type Job={id:string;state:string;error?:string;retry_allowed?:boolean;attempts:{id:string}[];runs:{id:string}[]};
const categories:Record<string,string>={STRUCTURE:'구조화 후보',MISSING_INFORMATION:'부족정보 후보',CONFLICT:'충돌 후보',PROCESSING_LIMITATION:'자료처리 한계'};
const decisions:Record<string,string>={USE_FOR_REQUEST:'요청 활용',EXCLUDE:'제외',NEEDS_CHECK:'추가 확인'};
const reasons:Record<string,string>={NEW_SUBMIT_VERSION:'새 제출본이 있습니다.',COMPANY_INPUT_CHANGED:'분석에 사용한 기업정보가 변경되었습니다.',FACT_BASIS_CHANGED:'확인 Fact 또는 근거가 변경되었습니다.',SITE_CHANGED:'사업장 정보가 변경되었습니다.',SOURCE_CHANGED:'사용한 자료가 변경되었습니다.',NEW_ATTEMPT:'재분석 실행을 확인해 주세요.',ANALYSIS_FAILED:'분석 실패',RULE_CHANGED:'분석 규칙이 변경되었습니다.',NEW_COMMON_SOURCE_REVIEW_SUGGESTED:'새 공통자료가 있습니다. 이번 과제와의 관련성 재검토가 필요합니다.',NEWER_WORKING_VERSION:'새 작성본이 있습니다. 이 결과는 선택한 제출본 기준입니다.'};
Object.assign(reasons,{VERIFIED_ANSWER_CHANGED:'검토 완료된 기업 답변이 변경되었습니다. 새 답변을 포함하여 재분석해 주세요.',REVIEW_CHANGED:'선택한 후보의 검토가 변경되었습니다. 최신 검토로 초안을 다시 구성해 주세요.',NEW_FACT_REVIEW_SUGGESTED:'새 확인 Fact가 있습니다. 이번 과제와의 관련성 재검토가 필요합니다.'});
const key=()=>crypto.randomUUID();
type SubmissionRecord={id:string;actor_id?:string;request_key?:string;draft_id?:string;ordinal:number;decision:string;actor_name:string;created_at:string;note:string;analysis_limit:string};
type SubmissionReviews={history:SubmissionRecord[];projection:{current:boolean;label:string;status:string;latest:SubmissionRecord|null;job_id:string|null}};
const judgementLabels:Record<string,string>={COMPLETED:'검토 완료 — 추가 보완요청 없음',NEEDS_CHECK:'추가 확인 필요 — 판단 보류',PREPARE_REQUEST:'보완요청 작성'};

function AnalysisConfirmation({busy,onCancel,children}:{busy:boolean;onCancel:()=>void;children:ReactNode}){
 const dialog=useRef<HTMLDialogElement>(null),cancel=useRef<HTMLButtonElement>(null),titleId=useId();
 useEffect(()=>{const previous=document.activeElement,d=dialog.current;d?.showModal();cancel.current?.focus();return()=>{d?.close();if(previous instanceof HTMLElement&&previous.isConnected)previous.focus();};},[]);
 return <dialog className="request-confirmation" ref={dialog} aria-labelledby={titleId} onCancel={e=>{e.preventDefault();if(!busy)onCancel();}}><h3 id={titleId}>보완요청 발송 전 확인</h3>{children}<button ref={cancel} className="op-btn op-btn-outline" type="button" disabled={busy} onClick={onCancel}>돌아가기</button></dialog>;
}

function CandidateReview({candidate:c,disabled,selected,edit,commonNote,onSelect,onEdit,onReview}:{candidate:Candidate;disabled:boolean;selected:boolean;edit:{note?:string;question?:string};commonNote:string;onSelect:(selected:boolean)=>void;onEdit:(edit:{note?:string;question?:string})=>void;onReview:(c:Candidate,decision:string,note:string,question:string)=>void}){
 const latest=c.reviews.at(-1),question=edit.question??latest?.question??c.data.question??'',note=edit.note??'';
 return <article className="intake-candidate" data-candidate-id={c.id}>
 <div className="intake-candidate-heading"><label><input type="checkbox" aria-label={c.content+' 보완항목 선택'} checked={selected} disabled={disabled} onChange={e=>onSelect(e.target.checked)}/><strong>{c.content}</strong></label><span>{categories[c.category]}</span></div>
 <p className="intake-question">{question||'시스템 질문이 없습니다. 필요하면 개별 질문을 작성하세요.'}</p>
 {c.category==='PROCESSING_LIMITATION'&&<p className="intake-limit">미검사·처리 한계입니다. 실제 정보 부재를 뜻하지 않습니다.</p>}
 {latest&&<p className="intake-review-state">최근 검토: {decisions[latest.decision]} · {latest.note}</p>}
 <details><summary>근거·개별 검토</summary><p>{c.reason}</p><p>{c.data.uncertainty} · {c.data.claim_kind==='DIRECT_SOURCE'?'원문에 명시된 후보':'검토가 필요한 후보'}</p>
 <details><summary>적용 규칙·원문 근거</summary><p>{c.data.rule_id} · {c.data.rule_version}</p>{c.data.evidence.length?c.data.evidence.map((e,i)=><blockquote key={i} className="intake-text"><p>{e.kind==='IMPROVEMENT'?'선택 제출본 '+e.field:e.kind==='COMPANY_INPUT'?'분석 당시 기업 입력':e.kind==='SITE'?'제출본에 기록된 사업장':e.kind==='FACT'?'분석에 사용한 확인 Fact':e.kind==='RESPONSE'?'DATCO 검토 완료된 기업 보완답변':'기업자료 원문 · '+(e.descriptor??'')}</p>{e.quote}{e.file_id&&<p><a href={'/api/company/files/'+e.file_id+'/download'}>근거 원본 확인</a></p>}</blockquote>):<p>직접 인용 없음. 자료 검사 범위와 처리 한계를 확인하세요.</p>}</details>
 {c.data.search_scope&&<details><summary>이 규칙의 검사 범위와 불확실성</summary>{c.data.search_scope.map(s=><p key={s.inspection_id}><a href={'#analysis-inspection-'+s.inspection_id}>{s.status}</a> · {s.locations.map(l=>l.descriptor).join(', ')||'검사한 원문 위치 없음'}{s.exclude_reason&&' · 제외 사유: '+s.exclude_reason}</p>)}</details>}
 <label>확인 의견<textarea aria-label="확인 의견" maxLength={5000} placeholder="비워두면 공통 운영자 검토 의견을 사용합니다." value={note} disabled={disabled} onChange={e=>onEdit({...edit,note:e.target.value})}/></label>
 <label>기업에 확인할 질문<textarea aria-label="기업에 확인할 질문" maxLength={5000} value={question} disabled={disabled} onChange={e=>onEdit({...edit,question:e.target.value})}/></label>
 <div className="intake-actions">{Object.entries(decisions).map(([value,label])=><button type="button" className="op-btn op-btn-outline" key={value} disabled={disabled||!(note.trim()||commonNote.trim())} onClick={()=>onReview(c,value,note.trim()||commonNote.trim(),question)}>{label}</button>)}</div>
 <details><summary>검토 이력</summary>{c.reviews.map(r=><p key={r.id}>검토 {r.ordinal} · {decisions[r.decision]} · {r.note}</p>)}</details></details></article>;
}

function StructuredSummary({result}:{result:StructuredResult}){
 const sections:Record<string,string>={current_state:'현재 업무·현황',problems:'핵심 문제',cause_candidates:'원인 후보 · 인과관계 확인 필요',goals:'개선목표',required_functions:'필요 업무·시스템 기능',scope_constraints:'범위·제약조건'};
 return <details className="intake-structure"><summary>요구사항 분석 구조와 한계</summary><p>{result.provider} · {result.provider_version} · 사람 검토 전 후보</p>{Object.entries(sections).map(([field,label])=>{const values=result.structure[field];return <section key={field}><h4>{label}</h4>{Array.isArray(values)&&values.length?values.map((v,i)=><p key={i}>{v.text} · {v.uncertainty}</p>):<p>이 규칙·검사 범위에서 구조화한 후보 없음 · 필요하면 운영자 추가 확인</p>}</section>;})}{result.limitations.map((text,i)=><p key={i}>{text}</p>)}<details><summary>정확한 분석 입력</summary><p>기업: {result.context.company_id}</p><p>제출 Version: {result.context.improvement_version_id}</p><p>입력 Digest: {result.context.input_digest}</p></details></details>;
}

export function ImprovementAnalysisPanel({cid,vid,actorId,company,title,submissionOrdinal,requests,autoStart,onRequests,onFinished,onDirty,onDraftActive}:{cid:string;vid:string;actorId:string;company:string;title:string;submissionOrdinal:number;onFinished:(message:string)=>void;requests:boolean;autoStart:boolean;onRequests:()=>void;onDirty:(dirty:boolean)=>void;onDraftActive:(active:boolean)=>void}){
 const [providers,setProviders]=useState<Provider[]>([]),[provider,setProvider]=useState('RULE');
 const [sources,setSources]=useState<Sources|null>(null),[common,setCommon]=useState<string[]>([]),[excluded,setExcluded]=useState<Record<string,string>>({});
 const [runs,setRuns]=useState<Run[]>([]),[runId,setRunId]=useState(''),[drafts,setDrafts]=useState<Draft[]>([]),[draft,setDraft]=useState<Draft|null>(null);
 const [form,setForm]=useState({title:'',message:'',due:''}),[dirty,setDirty]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[job,setJob]=useState<Job|null>(null),[confirm,setConfirm]=useState(false);
 const [whole,setWhole]=useState<SubmissionReviews|null>(null),[note,setNote]=useState('');
 const [saveState,setSaveState]=useState('');
 const [choices,setChoices]=useState<Record<string,boolean>>({}),[edits,setEdits]=useState<Record<string,{note?:string;question?:string}>>({}),[recovered,setRecovered]=useState(false),[sendUncertain,setSendUncertain]=useState(false);
 const draftSelected=useRef(false);
 const commands=useRef(new ReviewCommands()),pendingJudgement=useRef(''),returnAfterSend=useRef(false);
 const alive=useRef(true),sending=useRef(false),entryRequested=useRef(false),selectionInitialized=useRef(false),requestKeys=useRef<Record<string,string>>({});
 const commandKey=(op:string)=>requestKeys.current[op]??(requestKeys.current[op]=key());
 const changed=useCallback((event='datco-analysis-changed')=>{window.dispatchEvent(new CustomEvent(event,{detail:{version:vid}}));},[vid]);
 const run=runs.find(r=>r.run.id===runId)??runs.at(-1),version=draft?.versions.at(-1);
 const load=useCallback(async()=>{const [s,r,d,h,p]=await Promise.all([companyRequest<Sources>('/improvements/'+vid+'/analysis-inputs'),companyRequest<Run[]>('/improvements/'+vid+'/analysis-runs'),companyRequest<Draft[]>('/improvements/'+vid+'/analysis-drafts'),companyRequest<SubmissionReviews>('/improvements/'+vid+'/submission-reviews'),companyRequest<{providers:Provider[]}>('/analysis/providers')]);if(alive.current){setProviders(p.providers);setSources(s);setRuns(r);setDrafts(d);setWhole(h);if(requests&&!draftSelected.current){const target=h.projection.current&&h.projection.latest?.decision==='PREPARE_REQUEST'?h.projection.latest.draft_id:undefined;const saved=d.find(x=>x.id===target&&x.freshness.usable&&!x.deliveries.length);if(saved){draftSelected.current=true;const v=saved.versions.at(-1)!;setDraft(saved);setForm({title:v.title,message:v.message,due:v.due_date??''});onDraftActive(true);}}const pendingKey=commands.current.key(pendingJudgement.current);setRecovered(!!pendingKey&&h.history.some(r=>r.request_key===pendingKey&&r.actor_id===actorId));if(!selectionInitialized.current){selectionInitialized.current=true;setCommon(r.at(-1)?.manifest.data.common_file_ids??[]);}}return {s,r,d,h};},[vid,actorId,requests,onDraftActive]);
 async function action(work:()=>Promise<unknown>){if(sending.current)return;sending.current=true;setBusy(true);setError('');try{await work();}catch(e){if(alive.current){setError((e instanceof Error?e.message:'처리 상태를 확인해 주세요.')+' 일부 검토 또는 초안이 저장됐을 수 있습니다. 서버 상태를 다시 확인하세요.');try{await load();}catch{setError(old=>old+' 서버 재조회에도 실패했습니다. 확인 전에는 다시 저장하거나 이동하지 마세요.');}}}finally{sending.current=false;if(alive.current)setBusy(false);}}
 useEffect(()=>{alive.current=true;void (async()=>{const data=await load();if(!alive.current||!autoStart||entryRequested.current)return;entryRequested.current=true;const latest=data.r.at(-1);let j:Job;
   if(data.h.projection.job_id){j=await companyRequest<Job>('/analysis-jobs/'+data.h.projection.job_id);if(['QUEUED','PROCESSING'].includes(j.state)||(latest?.freshness.usable&&latest.manifest.data.input_policy==='submitted-review-v1')){if(alive.current)setJob(j);return;}}
   j=await companyRequest<Job>('/improvements/'+vid+'/analysis-jobs',{idempotency_key:key(),selection_token:data.s.selection_token,mode:'ENSURE',provider:'RULE',reason:'운영자 제출본 상세 진입에 따른 사전 분석'});if(alive.current){setJob(j);changed();if(!['QUEUED','PROCESSING'].includes(j.state))await load();}
  })().catch(e=>{if(alive.current)setError(e.message);});return()=>{alive.current=false;};},[load,vid,autoStart,changed]);
 useEffect(()=>{onDirty(dirty);const warn=(e:BeforeUnloadEvent)=>{if(dirty)e.preventDefault();};window.addEventListener('beforeunload',warn);return()=>{window.removeEventListener('beforeunload',warn);onDirty(false);};},[dirty,onDirty]);
 useEffect(()=>()=>onDraftActive(false),[onDraftActive]);
 useEffect(()=>{if(!job||!['QUEUED','PROCESSING'].includes(job.state))return;const timer=setTimeout(()=>{void companyRequest<Job>('/analysis-jobs/'+job.id).then(async j=>{if(!alive.current)return;setJob(j);if(!['QUEUED','PROCESSING'].includes(j.state)){await load();changed();}}).catch(e=>{if(alive.current)setError(e.message);});},1000);return()=>clearTimeout(timer);},[job,load,changed]);
 function open(d:Draft){draftSelected.current=true;setSaveState('');if(d.company_id!==cid||d.version_id!==vid)throw Error('초안의 기업·제출본이 일치하지 않습니다.');if(dirty&&!window.confirm('저장하지 않은 수정을 버리고 다른 초안을 여시겠습니까?'))return;const v=d.versions.at(-1)!;setDraft(d);setForm({title:v.title,message:v.message,due:v.due_date??''});setDirty(false);setConfirm(false);setSendUncertain(false);returnAfterSend.current=false;onDraftActive(true);}
 async function refreshDraft(check=false){if(!draft)return;const d=await companyRequest<Draft>('/analysis-drafts/'+draft.id);if(!alive.current)return d;if(d.company_id!==cid||d.version_id!==vid)throw Error('초안 대상이 변경되었습니다.');setDraft(d);setDrafts(old=>old.map(x=>x.id===d.id?d:x));if(check)setSendUncertain(false);const saved=d.versions.at(-1)!;if(saved.request_key===commands.current.key('save:'+d.id)&&saved.title===form.title.trim()&&saved.message===form.message.trim()&&(saved.due_date??'')===form.due){setDirty(false);setSaveState('');commands.current.clear('save:'+d.id);}if(d.deliveries.length){setConfirm(false);window.dispatchEvent(new CustomEvent('datco-information-requests-changed',{detail:{company:cid,version:vid}}));if(returnAfterSend.current){const h=await companyRequest<SubmissionReviews>('/improvements/'+vid+'/submission-reviews');if(alive.current){onDirty(false);onFinished(`보완요청 발송이 확인되었습니다. ${company} · 제출본 v${submissionOrdinal} · 현재 업무 상태: ${h.projection.label}`);}}}return d;}
 async function saveDraft(){if(!draft||!version)return;setSaveState('저장 중');try{const slot='save:'+draft.id;await commands.current.execute<DraftVersion>(slot,{expected_ordinal:version.ordinal,title:form.title,message:form.message,due_date:form.due||null,review_ids:version.review_ids},body=>companyRequest('/analysis-drafts/'+draft.id+'/versions',body),async key=>(await companyRequest<Draft>('/analysis-drafts/'+draft.id)).versions.find(v=>v.request_key===key));await refreshDraft();if(alive.current){setDirty(false);commands.current.clear(slot);setSaveState('');}}catch(e){setSaveState([400,401,403,404,409,422].includes((e as {status?:number})?.status??0)?'저장 실패':'저장 결과 확인 필요');throw e;}}
 const processing=!!job&&['QUEUED','PROCESSING'].includes(job.state);
 const disabled=busy||processing||!run?.freshness.usable||run.run.id!==runs.at(-1)?.run.id;
 const isSelected=(c:Candidate)=>choices[(run?.run.id??'')+':'+c.id]??c.reviews.at(-1)?.decision==='USE_FOR_REQUEST';
 const selected=run?.candidates.filter(isSelected)??[];
 const selectionCount=selected.length;
 const missing=run?.candidates.filter(c=>c.category==='MISSING_INFORMATION')??[],conflicts=run?.candidates.filter(c=>c.category==='CONFLICT')??[],limits=run?.candidates.filter(c=>c.category==='PROCESSING_LIMITATION')??[],structures=run?.candidates.filter(c=>c.category==='STRUCTURE')??[];
 function changeChoice(c:Candidate,value:boolean){setChoices(old=>({...old,[(run?.run.id??'')+':'+c.id]:value}));}
 function candidateEdit(c:Candidate){return edits[(run?.run.id??'')+':'+c.id]??{};}
 async function recordReview(c:Candidate,decision:string,note:string,question:string){
  if(!alive.current)throw Error('검토 화면이 변경되었습니다.');
  const slot='review:'+c.id;
  const result=await commands.current.execute<Review>(slot,{expected_review_ordinal:c.reviews.at(-1)?.ordinal??0,decision,note,question},body=>companyRequest('/analysis-candidates/'+c.id+'/reviews',body),async key=>{const data=await load();return data.r.flatMap(r=>r.candidates).find(x=>x.id===c.id)?.reviews.find(r=>r.request_key===key&&r.actor_id===actorId);});
  return result;
 }
 async function judge(decision:string,draftId?:string){
  const slot='judge:'+decision+':'+(draftId??'');pendingJudgement.current=slot;
  const before=await load();if(!alive.current)return;const basis=runId?before.r.find(r=>r.run.id===runId):before.r.at(-1);
  if((basis?.run.id??null)!==(run?.run.id??null))throw Error('분석 결과가 새로 도착했습니다. 내용을 확인한 뒤 판단을 다시 선택하세요.');
  if((before.h.history.at(-1)?.ordinal??0)!==(whole?.history.at(-1)?.ordinal??0))throw Error('최신 검토 이력이 변경되었습니다. 서버 기록을 확인한 뒤 다시 선택하세요.');
  await commands.current.execute<SubmissionRecord>(slot,{expected_ordinal:whole?.history.at(-1)?.ordinal??0,decision,note,run_id:basis?.run.id??null,job_id:basis?.manifest.job_id??before.h.projection.job_id??null,draft_id:draftId??null,analysis_limit:basis?'':'분석 결과 미확보: '+(job?.error??job?.state??'상태 확인 필요')},body=>companyRequest('/improvements/'+vid+'/submission-reviews',body),async key=>{const data=await load();return data.h.history.find(r=>r.request_key===key&&r.actor_id===actorId);});
  const data=await load();if(!alive.current)return;
  commands.current.clear(slot);pendingJudgement.current='';setRecovered(false);changed('datco-submission-reviewed');
  if(decision!=='PREPARE_REQUEST'){onDirty(false);onFinished(`검토 판단이 저장되었습니다. ${company} · 제출본 v${submissionOrdinal} · 현재 업무 상태: ${data.h.projection.label}`);}
 }
 async function prepareDraft(){
  if(!run||!selected.length)return;
  const chosen=selected.map(c=>c.id),originalRun=run.run.id,accepted=new Map<string,string>();
  let data=await load();
  if(data.r.at(-1)?.run.id!==originalRun||!data.r.at(-1)?.freshness.usable)throw Error('분석 결과가 변경되었습니다. 최신 결과를 확인하세요.');
  for(const id of chosen){
   if(!alive.current)throw Error('검토 화면이 변경되었습니다.');
   const c=data.r.at(-1)!.candidates.find(c=>c.id===id);if(!c)throw Error('선택한 후보가 없습니다.');
   const edit=edits[originalRun+':'+id]??{};
   if(usableReview(c.reviews.at(-1),edit)){accepted.set(id,c.reviews.at(-1)!.id);commands.current.clear('review:'+id);continue;}
   const reviewNote=edit.note?.trim()||note.trim();if(!reviewNote)throw Error('선택 항목을 확인한 운영자 검토 의견을 입력하세요.');
   const saved=await recordReview(c,'USE_FOR_REQUEST',reviewNote,edit.question??c.reviews.at(-1)?.question??c.data.question??'');accepted.set(id,saved.id);
   data=await load();commands.current.clear('review:'+id);
   if(data.r.at(-1)?.run.id!==originalRun||!data.r.at(-1)?.freshness.usable)throw Error('분석 결과가 변경되었습니다.');
  }
  if(!alive.current)return;
  const current=data.r.at(-1)!;
  const ids=chosen.map(id=>{const r=current.candidates.find(c=>c.id===id)?.reviews.at(-1);if(r?.decision!=='USE_FOR_REQUEST'||r.id!==accepted.get(id))throw Error('후보의 최신 검토가 변경되었습니다.');return r.id;});
  const reused=[...data.d].reverse().find(d=>d.run_id===originalRun&&!d.deliveries.length&&d.freshness.usable&&sameReviews(d.versions.at(-1)!.review_ids,ids));
  const d=reused??await commands.current.execute<Draft>('draft',{run_id:originalRun,review_ids:ids},body=>companyRequest('/analysis-drafts',body),async key=>(await load()).d.find(d=>d.request_key===key));
  if(!alive.current)return;
  const verified=await companyRequest<Draft>('/analysis-drafts/'+d.id);if(!alive.current)return;
  if(!verified.freshness.usable||!sameReviews(verified.versions.at(-1)!.review_ids,ids))throw Error('초안의 최신 검토 근거가 변경되었습니다. 서버 상태를 확인하세요.');
  if(!data.h.projection.current||data.h.history.at(-1)?.decision!=='PREPARE_REQUEST'||data.h.history.at(-1)?.draft_id!==d.id)await judge('PREPARE_REQUEST',d.id);
  if(alive.current){commands.current.clear('draft');open(verified);onRequests();}
 }
 function candidateRow(c:Candidate){return <CandidateReview key={c.id} candidate={c} disabled={disabled} selected={isSelected(c)} edit={candidateEdit(c)} commonNote={note} onSelect={value=>changeChoice(c,value)} onEdit={edit=>setEdits(old=>({...old,[(run?.run.id??'')+':'+c.id]:edit}))} onReview={(c,decision,note,question)=>void action(async()=>{await recordReview(c,decision,note,question);await load();commands.current.clear('review:'+c.id);changeChoice(c,decision==='USE_FOR_REQUEST');})}/>;}
 return <div data-testid="improvement-analysis">{error&&<p role="alert">{error}</p>}
 {!requests&&<><section className="intake-card"><h2>Rule 기반 사전 분석 결과</h2><p>Rule 기반 검토 후보입니다. 분석 성공은 정보의 완전성이나 공식 확정을 뜻하지 않습니다.</p>
 <p role="status">{processing?'분석 중':job?.state==='FAILED'?'분석 실패':run?'분석 결과 도착':'분석 준비 중'}{job?.error&&' · '+job.error}</p>
 {run&&<dl className="intake-analysis-summary" aria-label="시스템 분석 요약"><div><dt>분석 결과</dt><dd>{run.status==='SUCCEEDED'?'완료':run.status==='PARTIAL'?'부분 완료':'실패'}</dd></div><div><dt>추가 확인 후보</dt><dd>{missing.length}건</dd></div><div><dt>정보 충돌 후보</dt><dd>{conflicts.length}건</dd></div><div><dt>자료 처리 한계</dt><dd>{limits.length||run.status==='PARTIAL'?'있음':'해당 후보 없음'}</dd></div></dl>}{run&&<><p>{run.freshness.usable?'현재 입력에 활용 가능한 분석':'과거 분석 · 현재 활용 제한'}</p>{[...run.freshness.reasons,...run.freshness.warnings].map(r=><p key={r}>{reasons[r]??r}</p>)}
 {!run.candidates.length&&<p>이 규칙·검사 범위에서 생성된 후보가 없습니다. 완전한 정보나 적격을 의미하지 않습니다.</p>} <section aria-label="핵심 추가 확인사항"><h3>핵심 추가 확인사항 · {missing.length}건</h3>{missing.map(candidateRow)}{!missing.length&&<p>이 규칙·검사 범위에서 생성된 부족정보 후보가 없습니다.</p>}</section>
 {!!conflicts.length&&<section aria-label="정보 충돌"><h3>정보 충돌 · {conflicts.length}건</h3>{conflicts.map(candidateRow)}</section>}
 {!!limits.length&&<section aria-label="미검사·자료 처리 한계"><h3>미검사·자료 처리 한계 · {limits.length}건</h3><p>읽지 못한 자료를 정보가 없다는 근거로 판단하지 않습니다.</p>{limits.map(candidateRow)}</section>}
 {run.diagnostics?.structured_result&&<StructuredSummary result={run.diagnostics.structured_result}/>}
 <details className="intake-structure"><summary>원문 구조화 후보 · {structures.length}건</summary>{structures.map(candidateRow)}</details>
</>}
{job?.retry_allowed&&<button className="op-btn op-btn-outline" disabled={busy||processing} onClick={()=>void action(async()=>{const j=await companyRequest<Job>('/analysis-jobs/'+job.id+'/retry',{idempotency_key:commandKey('retry'),expected_attempt:job.attempts.length});if(alive.current){setJob(j);setRunId('');delete requestKeys.current.retry;changed();}})}>같은 입력 재시도</button>}
 <details className="intake-analysis-details"><summary>상세 분석·근거·실행 이력</summary>
 <details><summary>참고자료 추가·수동 재분석</summary><label>분석 방식<select aria-label="분석 방식" value={provider} disabled={busy||processing} onChange={e=>setProvider(e.target.value)}>{providers.map(p=><option key={p.id} value={p.id} disabled={p.status!=='AVAILABLE'}>{p.label}{p.status!=='AVAILABLE'?' — 연결 미설정':''}</option>)}</select></label><p>자동 진입은 Rule로 실행합니다. 외부 AI 4종은 연결 미설정이며 실행할 수 없습니다.</p><details><summary>분석 제공자 상태</summary>{providers.map(p=><p key={p.id}>{p.label} · {p.status==='AVAILABLE'?'사용 가능':'연결 미설정'}{p.reason&&' · '+p.reason}</p>)}</details><p>제출본문·직접 근거·확인 Fact·제출 당시 사업장을 기본 검사합니다. 선택하지 않은 공통자료는 관련성이 없다고 판단한 자료가 아닙니다.</p>{sources?.files.map(f=><div className="intake-text" key={f.id}><label><input type="checkbox" checked={f.direct?!(f.id in excluded):common.includes(f.id)} disabled={busy||processing||!f.direct&&!f.supported} onChange={e=>{if(f.direct){setExcluded(old=>{const next={...old};if(e.target.checked)delete next[f.id];else next[f.id]='';return next;});}else setCommon(old=>e.target.checked?[...old,f.id]:old.filter(x=>x!==f.id));}}/>{f.name} · {f.direct?'제출본 직접 첨부':'선택 가능한 공통 참고자료'}{!f.supported&&' · 본문 처리 미지원'}</label>{f.direct&&f.id in excluded&&<input aria-label={f.name+' 제외 사유'} placeholder="직접 근거 제외 사유 (3자 이상)" maxLength={1000} value={excluded[f.id]} disabled={busy} onChange={e=>setExcluded(old=>({...old,[f.id]:e.target.value}))}/>}</div>)}
 <button className="op-btn op-btn-outline" disabled={busy||processing||!sources||providers.find(p=>p.id===provider)?.status!=='AVAILABLE'||Object.values(excluded).some(v=>v.trim().length<3)} onClick={()=>void action(async()=>{const j=await companyRequest<Job>('/improvements/'+vid+'/analysis-jobs',{idempotency_key:commandKey('analysis'),selection_token:sources!.selection_token,excluded_files:excluded,common_file_ids:common,provider,reason:'운영자 참고자료 선택·명시 재분석'});if(alive.current){setJob(j);setRunId('');delete requestKeys.current.analysis;changed();}})}>선택 범위로 재분석</button></details>
 <details><summary>과거 분석 이력</summary><label>분석 이력<select aria-label="분석 이력" value={run?.run.id??''} disabled={busy||processing} onChange={e=>setRunId(e.target.value)}>{runs.map(r=><option key={r.run.id} value={r.run.id}>{new Date(r.run.created_at).toLocaleString('ko-KR')} · {r.status}</option>)}</select></label></details>
 <button className="op-btn op-btn-outline" disabled={busy} onClick={()=>void action(load)}>분석 상태 다시 조회</button>
 {run&&<>
 <details><summary>실제 자료 검사 범위와 한계</summary><p>COMPLETE는 추출 가능한 텍스트 범위만 의미하며 표·도면·의미 전체의 이해가 아닙니다.</p>{run.inspections.map(i=>{const f=run.inputs.find(x=>x.id===i.input_id);return <article id={'analysis-inspection-'+i.id} key={i.id}><h4>{f?.data.name} · {i.data.status}</h4><p>{f?.origin==='DIRECT_ATTACHMENT'?'제출본 직접 첨부':'공통 참고자료'} · {i.data.method}</p>{i.data.status==='NOT_SELECTED'&&<p>선택하지 않은 참고자료. 관련성 제외 판단이나 정보 부재 근거가 아닙니다.</p>}{f?.data.exclude_reason&&<p>명시 제외 사유: {f.data.exclude_reason}</p>}<p>{i.data.parser_version}</p>{i.data.error_code&&<p>{i.data.error_code}</p>}{i.data.limitations.map((l,n)=><p key={n}>{l}</p>)}<p>{i.data.locations.map(l=>l.descriptor).join(', ')||'검사한 본문 위치 없음'}</p>{f?.file_id&&<a href={'/api/company/files/'+f.file_id+'/download'}>원본 확인</a>}</article>;})}{!run.inspections.length&&<p>첨부 0건 · 제출본문과 고정된 입력 맥락을 검사했습니다.</p>}</details>

 </>}</details></section>
 <section className="intake-card"><h2>검토 판단 및 후속 조치</h2><p>명시적으로 저장한 판단만 이력과 대시보드에 반영합니다. 공식 CONFIRM이나 기업 Fact 확정이 아닙니다.</p>{whole?.projection.latest&&<p data-testid="submission-latest">{whole.projection.current?'현재 검토 판단':'과거 검토 · 재검토 필요'} · {whole.projection.latest.actor_name} · {new Date(whole.projection.latest.created_at).toLocaleString('ko-KR')} · {whole.projection.latest.note}</p>}
 <p>선택한 보완항목 {selectionCount}건 · 선택만으로 Review를 저장하지 않습니다. 선택 해제는 기존 검토의 제외 판단이 아닙니다.</p><label>운영자 검토 의견<textarea aria-label="운영자 검토 의견" maxLength={5000} value={note} disabled={busy} onChange={e=>setNote(e.target.value)}/></label>
 <p>공통 의견은 새로 ‘요청 활용’으로 저장할 선택 항목에 적용됩니다. 기존 최신 Review는 재사용하며, 개별 변경은 펼쳐보기에서 입력하세요. 여러 Review는 순차 저장하므로 중간 실패 시 일부만 저장될 수 있습니다.</p>
 <div className="intake-actions"><button className="op-btn op-btn-primary" disabled={disabled||!note.trim()||!selectionCount} onClick={()=>void action(prepareDraft)}>보완요청 작성</button><button className="op-btn op-btn-outline" disabled={!sources||!whole||busy||!note.trim()||!!run&&disabled} onClick={()=>void action(()=>judge('NEEDS_CHECK'))}>추가 확인 필요 — 판단 보류</button><button className="op-btn op-btn-outline" disabled={disabled||!note.trim()} onClick={()=>void action(()=>judge('COMPLETED'))}>검토 완료 — 추가 보완요청 없음</button></div>
 <button className="op-btn op-btn-outline" disabled={busy} onClick={()=>void action(load)}>저장 결과 다시 확인</button>
 {recovered&&<p role="status">해당 요청 키의 검토 판단이 서버에 저장된 것을 확인했습니다.<button className="op-btn op-btn-outline" disabled={busy} onClick={()=>{onDirty(false);onFinished(`검토 판단 저장이 확인되었습니다. ${company} · 제출본 v${submissionOrdinal} · 현재 업무 상태: ${whole?.projection.label}`);}}>확인한 결과로 목록 복귀</button></p>}
 {!!drafts.length&&<details><summary>저장된 분석 초안 이어보기</summary>{drafts.map(d=><button className="op-btn op-btn-outline" key={d.id} disabled={busy} onClick={()=>void action(async()=>{const current=await companyRequest<Draft>('/analysis-drafts/'+d.id);if(alive.current){open(current);onRequests();}})}>{d.versions.at(-1)?.title} · v{d.versions.at(-1)?.ordinal}</button>)}</details>}
 <details><summary>제출본 검토 이력</summary>{whole?.history.map(r=><article key={r.id}><p>{r.ordinal} · {r.actor_name} · {new Date(r.created_at).toLocaleString('ko-KR')} · {judgementLabels[r.decision]}</p><p>{r.note}</p>{r.analysis_limit&&<p>{r.analysis_limit}</p>}</article>)}{!whole?.history.length&&<p>저장된 제출본 검토 판단이 없습니다.</p>}</details></section></>}
 {requests&&<section className="intake-card"><h2>수요기업 보완자료 요청</h2><p>서버에 저장된 초안입니다. 최종 확인 전에는 요청을 생성·발송하지 않습니다.</p><button className="op-btn op-btn-outline" disabled={busy} onClick={()=>void action(load)}>초안 목록 새로 조회</button>{drafts.map(d=><button className="op-btn op-btn-outline" key={d.id} disabled={busy} onClick={()=>void action(async()=>{const current=await companyRequest<Draft>('/analysis-drafts/'+d.id);if(alive.current)open(current);})}>{d.versions.at(-1)?.title} · v{d.versions.at(-1)?.ordinal}{d.deliveries.length?' · 발송 완료':''}</button>)}{!drafts.length&&<p>저장된 분석 기반 초안이 없습니다.</p>}
 {draft&&version&&<><p>대상: {company} · {title} · 제출본 v{submissionOrdinal} · 초안 v{version.ordinal}</p><details><summary>선택한 보완항목·요청 이유</summary>{runs.find(r=>r.run.id===draft.run_id)?.candidates.filter(c=>c.reviews.some(r=>version.review_ids.includes(r.id))).map(c=><section key={c.id}><h4>{c.content}</h4><p>{c.reviews.find(r=>version.review_ids.includes(r.id))?.question||c.data.question}</p><p>요청 이유: {c.reason}</p></section>)}</details><p role="status">{saveState||(draft.deliveries.length?'수요기업에 발송 완료':dirty?'저장되지 않은 변경사항':'초안 저장 완료')}</p>{!draft.deliveries.length&&<p>아직 수요기업에 발송되지 않았습니다.</p>}{[...draft.freshness.reasons,...draft.freshness.warnings].map(r=><p key={r}>{reasons[r]??r}</p>)}
 <label>보완자료 요청 제목<input aria-label="보완자료 요청 제목" maxLength={300} value={form.title} disabled={busy||!!draft.deliveries.length} onChange={e=>{setForm({...form,title:e.target.value});setDirty(true);}}/></label><label>수요기업에 요청할 사항<textarea aria-label="수요기업에 요청할 사항" maxLength={10000} value={form.message} disabled={busy||!!draft.deliveries.length} onChange={e=>{setForm({...form,message:e.target.value});setDirty(true);}}/></label><p>기업 응답 기한은 수요기업에게 전달되는 업무기한입니다. 미지정 시 기한 없이 전달됩니다.</p><label>기업 응답 기한<input aria-label="기업 응답 기한" type="date" value={form.due} disabled={busy||!!draft.deliveries.length} onChange={e=>{setForm({...form,due:e.target.value});setDirty(true);}}/></label>
 <button className="op-btn op-btn-outline" disabled={busy||!dirty||!draft.freshness.usable||!!draft.deliveries.length||!form.title.trim()||!form.message.trim()} onClick={()=>void action(saveDraft)}>요청 초안 저장</button>
 <button className="op-btn op-btn-primary" disabled={busy||dirty||!draft.freshness.usable||!!draft.deliveries.length} onClick={()=>setConfirm(true)}>수요기업에 보완요청 보내기</button><details open={!!error||sendUncertain}><summary>저장·발송 상세 확인</summary><button className="op-btn op-btn-outline" disabled={busy} onClick={()=>void action(()=>refreshDraft(true))}>저장·발송 상태 확인</button></details><button className="op-btn op-btn-outline" disabled={busy} onClick={()=>{if(dirty&&!window.confirm('저장하지 않은 수정을 버리고 초안을 닫으시겠습니까?'))return;draftSelected.current=true;setDraft(null);setDirty(false);setConfirm(false);onDraftActive(false);}}>초안 닫기 · 수동 요청 작성</button>
 {!!draft.deliveries.length&&<p role="status">수요기업에 발송 완료. 아래 기존 보완요청 이력에서 응답을 확인하세요.</p>}
 {confirm&&<AnalysisConfirmation key={vid+draft.id+version.id} busy={busy} onCancel={()=>setConfirm(false)}><p>{company} · {title} · 제출본 v{submissionOrdinal} · 저장된 초안 v{version.ordinal}</p><details><summary>정확한 제출 Version</summary><p>{vid}</p></details><h4>{version.title}</h4><p className="intake-text">{version.message}</p><p>기업 응답 기한: {version.due_date??'미지정'}</p>{error&&<p role="alert">{error} 저장·발송 상태를 확인하세요.</p>}{sendUncertain&&<p>발송 결과 확인 전에는 새 발송을 실행하지 않습니다.</p>}<button className="op-btn op-btn-outline" disabled={busy} onClick={()=>void action(()=>refreshDraft(true))}>저장·발송 상태 확인</button><button className="op-btn op-btn-primary" disabled={busy||sendUncertain} onClick={()=>void action(async()=>{returnAfterSend.current=true;setSendUncertain(true);let failure:unknown;try{await companyRequest('/analysis-drafts/'+draft.id+'/send',{expected_ordinal:version.ordinal});}catch(e){failure=e;setSendUncertain(true);}const observed=await refreshDraft();if(!observed?.deliveries.length){setSendUncertain(true);throw failure??Error('발송 결과를 확인할 수 없습니다. 저장·발송 상태를 확인하세요.');}setConfirm(false);})}>수요기업에 발송하기</button></AnalysisConfirmation>}
 </> }</section>}
 </div>;
}
