import {usePortalWorkState} from './portal-work-state';
import {PortalErrorMessage,PortalReasonCodes,portalReasonText} from './portal-feedback';
import {useEffect,useRef,useState} from 'react';
import {portalApi} from './admin-live';
import {assetStatusLabel,type AssetItem} from './dmp-assets';
import {useMvpDirty} from './mvp-selection';

type Demand={id:string;kind:string;text:string;evidence:Record<string,unknown>[];uncertainty:string};
type Feature=AssetItem&{revision_id:string;feature_id:string;demand_ids?:string[];reasons?:string[];limitations?:string[];role?:string};
type Selection={feature_revision_id:string;asset_version_id:string|null;system_version_id:string|null;module_version_id:string|null;role?:string};
type Coverage={demand_id?:string;requirement:string;capability_version_id:null;feature_revision_ids:string[];role:string;addressed_scope:string;unaddressed_scope:string;missing_information:string[];status:'ADDRESSED'|'PARTIAL'|'UNRESOLVED';evidence_refs:Record<string,unknown>[]};
type Integration={from_asset_id:string;to_asset_id:string;data:string;workflow:string;prerequisites:string[];verification:'VERIFIED'|'UNVERIFIED';evidence_note:string;uncertainty:string};
type Alternative={id:string;name:string;kind:string;why:string|string[];systems:{id:string;name:string;version_id:string|null}[];modules:{id:string;name:string;version_id:string|null}[];feature_selections:Selection[];features:Feature[];coverage:Coverage[];integrations:Integration[];conditions:string[];unresolved:string[]};
type Run={id:string;improvement_version_id:string;analysis_run_id:string|null;input_digest:string;rule_version:string;input:{basis?:{run_id?:string;review_ids?:string[];source_version_id?:string}|null};data:{status?:string;demands:Demand[];candidates:Feature[];alternatives:Alternative[];uncovered_demands:string[];limitations:string[]};current_valid:boolean;stale_reasons:string[];created_at?:string};
type Form={name:string;selections:Selection[];coverage:Coverage[];integrations:Integration[];conditions:string;unresolved:string};
type SavedVersion={id:string;ordinal:number;data:{source_mode?:string;name:string;improvement_version_id:string;asset_basis?:{recommendation_id:string;alternative_id:string};asset_selections?:Selection[];coverage:Coverage[];asset_integrations?:Integration[];conditions:string[];unresolved:string[];asset_review_note?:string}};
const Card=({title,children}:{title:string;children:React.ReactNode})=><section className="intake-card mvp-card"><h2>{title}</h2>{children}</section>;
const split=(s:string)=>s.split('\n').map(x=>x.trim()).filter(Boolean);
const list=(value:string|string[])=>Array.isArray(value)?value:[value];
const kindLabel:Record<string,string>={SINGLE_MODULE:'단독 구성',MULTI_MODULE:'복합 모듈',CROSS_SYSTEM:'시스템 간 연계',PARTIAL:'부분 구성'};
const selectionOf=(feature:Feature):Selection=>({feature_revision_id:feature.revision_id,asset_version_id:feature.asset_version_id??null,system_version_id:feature.system_version_id??null,module_version_id:feature.module_version_id??null,role:feature.data?.role||feature.role||'추가 선택 기능의 역할 확인 필요'});
function RecommendationNotes({values}:{values:string[]}){
 const isMethod=(value:string)=>['등록된 기능 표현을 이용한','자동 초안은 사람 검토 전','규칙 기반 원천 기술자산 후보','분석 입력 Version과 구조화'].some(prefix=>value.startsWith(prefix));
 return <>{values.filter(value=>!isMethod(value)).map((value,i)=><p className="mvp-limit" key={i}>{value}</p>)}{values.some(isMethod)&&<details><summary>추천 방식과 사용한 자료</summary>{values.filter(isMethod).map((value,i)=><p key={i}>{value}</p>)}</details>}</>;
}
function AlternativeReason({value}:{value:Alternative}){
 return <><p>기업이 요청한 업무와 연결된 기능 후보입니다. 해결 범위와 제공 조건을 확인해 주세요.</p><details><summary>추천 근거 상세</summary>{list(value.why).map((why,i)=><p key={i}>{why}</p>)}</details></>;
}
function SelectedFunctionSummary({features}:{features:Feature[]}){
 return <div className="intake-table"><table aria-label="선택 기능 요약"><thead><tr><th>선택 기능·모듈</th><th>무엇을 하는 기능인가요?</th><th>제공 확인</th></tr></thead><tbody>{features.map(f=><tr key={f.revision_id}><td><strong>{f.name}</strong><p>{f.system_name} · {f.module_name}</p></td><td data-selected-function-description>{f.description??f.data.description}</td><td><p>{assetStatusLabel[f.availability]??'제공 확인 필요'}</p><p>{f.availability_evidence||'제공 확인 근거가 없습니다.'}</p>{f.mapping_status==='SOURCE_CLASSIFICATION'&&<p>모듈 관계 확인 필요</p>}<details><summary>출처·버전 확인</summary><p>{f.external_id} · {f.revision_id}</p>{f.reasons?.map((reason,i)=><p key={i}>{reason}</p>)}</details></td></tr>)}</tbody></table></div>;
}

export function AssetSolutionReview({cid,vid,onDirty,onNext,refresh}:{cid:string;vid:string;onDirty:(value:boolean)=>void;onNext:()=>void;refresh:()=>Promise<void>}){
 const [runs,setRuns]=useState<Run[]>([]),[runId,setRunId]=useState(''),[alternativeId,setAlternativeId]=useState(''),[comp,setComp]=useState<{id:string;version_id:string;ordinal:number}|null>(null),[history,setHistory]=useState<SavedVersion[]>([]);
 const [form,setForm]=useState<Form|null>(null),[baseline,setBaseline]=useState(''),[note,setNote]=useState(''),[reviewed,setReviewed]=useState(false),[compare,setCompare]=useState<string[]>([]);
 const [replaceWith,setReplaceWith]=useState<Record<string,string>>({});
 const [busy,setBusy]=useState(false),[loading,setLoading]=useState(true),[error,setError]=useState<string|Error>(''),[message,setMessage]=useState('');
 const gate=useRef(false),command=useRef<{signature:string;key:string}|null>(null),restored=useRef(false),interaction=useRef(0);
 const run=runs.find(r=>r.id===runId),alternative=run?.data.alternatives.find(a=>a.id===alternativeId);
 const dirty=!!form&&(JSON.stringify(form)!==baseline||!!note.trim()||reviewed);
 useMvpDirty(onDirty,dirty);
 usePortalWorkState({busy});
 const persist=(key:string,value:string)=>{const u=new URL(window.location.href);if(value)u.searchParams.set(key,value);else u.searchParams.delete(key);window.history.replaceState({},'',u);};
 const canLeave=()=>!dirty||window.confirm('저장하지 않은 추천안 검토 내용을 버리고 이동할까요?');
 async function perform(work:()=>Promise<void>){if(gate.current)return;gate.current=true;setBusy(true);setError('');setMessage('');try{await work();}catch(e){setError(e instanceof Error?e:'처리 결과를 확인하지 못했습니다. 저장 여부를 다시 조회하세요.');}finally{gate.current=false;setBusy(false);}}
 useEffect(()=>{const controller=new AbortController();void portalApi<Run[]>('capability','/improvements/'+vid+'/asset-solutions',undefined,controller.signal).then(value=>{
  if(controller.signal.aborted)return;setRuns(value);const u=new URL(window.location.href),hint=u.searchParams.get('asset_run'),chosen=value.find(r=>r.id===hint)??value[0];
  if(chosen){setRunId(chosen.id);const aid=u.searchParams.get('asset_alternative');const restoredAlternative=chosen.data.alternatives.find(a=>a.id===aid);if(restoredAlternative){setAlternativeId(restoredAlternative.id);if(!u.searchParams.get('asset_composition')){const copied={name:restoredAlternative.name,selections:structuredClone(restoredAlternative.feature_selections),coverage:structuredClone(restoredAlternative.coverage),integrations:structuredClone(restoredAlternative.integrations),conditions:restoredAlternative.conditions.join('\n'),unresolved:restoredAlternative.unresolved.join('\n')};setForm(copied);setBaseline(JSON.stringify(copied));}}}
  setLoading(false);
 }).catch(e=>{if(!controller.signal.aborted){setError(e instanceof Error?e:'추천 이력 조회 실패');setLoading(false);}});return()=>controller.abort();},[vid]);
 useEffect(()=>{
  if(loading||!runs.length||restored.current)return;
  restored.current=true;const u=new URL(window.location.href),id=u.searchParams.get('asset_composition');if(!id)return;
  const controller=new AbortController(),epoch=interaction.current;
  void portalApi<{root:{id:string};versions:SavedVersion[]}>('capability','/compositions/'+encodeURIComponent(id),undefined,controller.signal).then(result=>{
   if(controller.signal.aborted||interaction.current!==epoch)return;const v=result.versions.at(-1),basis=v?.data.asset_basis;
   if(!v||v.data.source_mode!=='DMP_ASSET'||v.data.improvement_version_id!==vid||!basis||!runs.some(r=>r.id===basis.recommendation_id))return;
   setComp({id:result.root.id,version_id:v.id,ordinal:v.ordinal});setHistory(result.versions);setRunId(basis.recommendation_id);setAlternativeId(basis.alternative_id);
   const saved={name:v.data.name,selections:v.data.asset_selections??[],coverage:v.data.coverage,integrations:v.data.asset_integrations??[],conditions:v.data.conditions.join('\n'),unresolved:v.data.unresolved.join('\n')};setForm(saved);setBaseline(JSON.stringify(saved));setNote('');setReviewed(false);
  }).catch(e=>{if(!controller.signal.aborted)setError(e instanceof Error?e:'저장된 구성 조회 실패');});return()=>controller.abort();
 },[loading,runs,vid]);
 async function generate(){
  if(!canLeave())return;interaction.current++;
  await perform(async()=>{
   const result=await portalApi<Run>('capability','/improvements/'+vid+'/asset-solutions',{idempotency_key:crypto.randomUUID()});
   setRuns(old=>old.some(r=>r.id===result.id)?old.map(r=>r.id===result.id?result:r):[...old,result]);setRunId(result.id);setAlternativeId('');setForm(null);setComp(null);setHistory([]);setNote('');setReviewed(false);setCompare([]);persist('asset_run',result.id);persist('asset_alternative','');persist('asset_composition','');
   setMessage(result.data.alternatives.length?'실제 기술자산을 근거로 검토할 구성 초안을 생성했습니다. 대안을 비교한 뒤 선택하세요.':'현재 확인된 솔루션이 없습니다. 미해결 요구와 추가 확인사항을 검토하세요.');
  });
 }
 function choose(value:Alternative){
  if(!canLeave())return;interaction.current++;
  setAlternativeId(value.id);const copied:Form={name:value.name,selections:structuredClone(value.feature_selections),coverage:structuredClone(value.coverage),integrations:structuredClone(value.integrations),conditions:value.conditions.join('\n'),unresolved:value.unresolved.join('\n')};setForm(copied);setBaseline(JSON.stringify(copied));setNote('');setReviewed(false);setComp(null);setHistory([]);command.current=null;persist('asset_alternative',value.id);persist('asset_composition','');setMessage('추천 초안을 검토란에 불러왔습니다. 저장·확정은 실행하지 않았습니다.');
 }
 const features=run?Array.from(new Map([...run.data.candidates,...(alternative?.features??[])].map(f=>[f.revision_id,f])).values()):[];
 const selectedFeatures=form?features.filter(f=>form.selections.some(s=>s.feature_revision_id===f.revision_id)):[];
 const selectionChanged=!!form&&!!alternative&&JSON.stringify(form.selections.map(s=>s.feature_revision_id).sort())!==JSON.stringify(alternative.feature_selections.map(s=>s.feature_revision_id).sort());
 function changeSelection(nextIds:string[]){
  if(!form||!run)return;
  const selected=features.filter(f=>nextIds.includes(f.revision_id));
  const selections=selected.map(f=>form.selections.find(s=>s.feature_revision_id===f.revision_id)??selectionOf(f));
  const coverage=form.coverage.map(row=>{
   const ids=row.feature_revision_ids.filter(id=>nextIds.includes(id));
   return ids.length?{...row,feature_revision_ids:ids}:{...row,feature_revision_ids:[],status:'UNRESOLVED' as const,addressed_scope:'',unaddressed_scope:row.unaddressed_scope||'연결 기능을 제외하여 해결범위 재검토 필요',missing_information:row.missing_information.length?row.missing_information:['대체 기능과 적용 가능 범위를 확인하세요.']};
  });
  for(const feature of selected.filter(f=>!form.selections.some(s=>s.feature_revision_id===f.revision_id))){
   for(const demandId of feature.demand_ids??[]){
    const demand=run.data.demands.find(d=>d.id===demandId);if(!demand)continue;
    const existing=coverage.find(row=>row.demand_id===demandId);if(existing){existing.feature_revision_ids=Array.from(new Set([...existing.feature_revision_ids,feature.revision_id]));existing.status='PARTIAL';existing.role=existing.role||feature.data?.role||'추가 선택 기능의 역할 확인 필요';existing.addressed_scope=existing.addressed_scope||feature.description||feature.data?.description||feature.name;existing.unaddressed_scope=existing.unaddressed_scope||'추가한 기능의 적용조건·제공범위 확인 필요';}else coverage.push({demand_id:demandId,requirement:demand.text,capability_version_id:null,feature_revision_ids:[feature.revision_id],role:feature.data?.role||'추가 선택 기능의 역할 확인 필요',addressed_scope:feature.description||feature.data?.description||feature.name,unaddressed_scope:'운영자가 추가한 기능의 적용조건·제공범위 확인 필요',missing_information:['추가한 기능의 제공 검증과 기존 구성의 연계를 확인하세요.'],status:'PARTIAL',evidence_refs:demand.evidence});
   }
  }
  const endpoints=new Set(selected.flatMap(f=>[f.id,f.feature_id,f.system_id,f.module_id]));const integrations=form.integrations.filter(link=>endpoints.has(link.from_asset_id)&&endpoints.has(link.to_asset_id));
  setForm({...form,selections,coverage,integrations,unresolved:integrations.length<form.integrations.length?form.unresolved+'\n기능·모듈 제외에 따라 연계 초안을 제거했습니다. 남은 요구와 대체 연계를 확인하세요.':form.unresolved});setReviewed(false);setMessage('선택 구성을 변경했습니다. 새로 포함하거나 교체한 모듈의 선행 조건과 등록된 연계를 다시 검토해 주세요. 초안 저장은 고객 제안 가능 판단과 별개입니다.');
 }
 const moduleOptions=Array.from(new Map(features.map(f=>[f.module_id??'',{id:f.module_id??'',name:f.module_name??'원천 그룹 확인 필요'}])).values()).filter(m=>m.id);
 const selectedModules=moduleOptions.filter(m=>selectedFeatures.some(f=>f.module_id===m.id));
 const assetOptions=Array.from(new Map(selectedFeatures.flatMap(f=>[{id:f.system_id??'',name:(f.system_name??'시스템 확인 필요')+' · 시스템'},{id:f.module_id??'',name:(f.module_name??'그룹 확인 필요')+(f.mapping_status==='SOURCE_CLASSIFICATION'?' · 원천 분류':' · 모듈')},{id:f.feature_id,name:f.name+' · 원천 기능'},{id:f.id,name:f.name+' · 관리 연결'}]).filter(a=>a.id).map(a=>[a.id,a])).values());
 const issues=form?.coverage.flatMap((row,i)=>{
  const label='요구별 해결범위 '+(i+1),addressed=!!row.addressed_scope.trim(),remaining=!!row.unaddressed_scope.trim()||row.missing_information.some(s=>!!s.trim()),values:string[]=[];
  if(!row.role.trim())values.push(label+': 실제 역할을 확인하세요.');
  if(row.status==='PARTIAL'&&(!addressed||!remaining||!row.feature_revision_ids.length))values.push(label+': 해결 범위와 남은 범위·확인사항이 모두 필요합니다.');
  if(row.status==='ADDRESSED'&&(!addressed||remaining||!row.feature_revision_ids.length))values.push(label+': 실제 연결 기능과 해결 범위가 필요합니다. 남은 사항이 있으면 일부 해결을 선택하세요.');
  if(row.status==='ADDRESSED'&&row.feature_revision_ids.some(id=>features.find(f=>f.revision_id===id)?.availability!=='VERIFIED'))values.push(label+': 제공 검증이 완료되지 않은 기능은 해결 완료로 표시할 수 없습니다.');
  if(row.status==='UNRESOLVED'&&(addressed||!remaining))values.push(label+': 해결 범위를 비우고 남은 범위·확인사항을 남기세요.');
  return values;
 })??[];
 const canSave=!!run?.current_valid&&!!form?.name.trim()&&!!form.selections.length&&!!form.coverage.length&&!issues.length&&!!note.trim()&&reviewed;
 async function save(){if(!form||!run||!alternative)return;
  await perform(async()=>{
   const data={source_mode:'DMP_ASSET',name:form.name,improvement_version_id:vid,capability_version_ids:[],asset_basis:{recommendation_id:run.id,alternative_id:alternative.id},asset_selections:form.selections,asset_review_note:note,basis:run.input.basis??undefined,coverage:form.coverage.map(c=>({...c,missing_information:c.missing_information.filter(s=>s.trim())})),asset_integrations:form.integrations,conditions:split(form.conditions),unresolved:split(form.unresolved)};
   const body={data,expected_version:comp?.version_id??null},signature=JSON.stringify(body);if(command.current?.signature!==signature)command.current={signature,key:crypto.randomUUID()};
   const result=await portalApi<{id:string;version_id:string;ordinal:number}>('capability',comp?'/compositions/'+comp.id+'/versions':'/compositions',{...body,idempotency_key:command.current.key});
   setComp(result);setBaseline(JSON.stringify(form));setNote('');setReviewed(false);command.current=null;persist('asset_composition',result.id);onDirty(false);
   const detail=await portalApi<{versions:SavedVersion[]}>('capability','/compositions/'+result.id);setHistory(detail.versions);await refresh();setMessage('검토한 기술자산 조합 v'+result.ordinal+'을 저장했습니다. 지원사업 검토·매칭은 별도입니다.');
  });
 }
 return <div data-testid="asset-solution-review" data-company-id={cid} data-version-id={vid}>
 <Card title="기업 요구에 맞는 시스템·모듈 추천"><p>등록된 기능으로 단독·복합 구성 초안을 만듭니다. 적용 범위와 실제 제공 가능성을 검토한 뒤 사용하세요.</p>
 <div className="intake-actions"><button className="op-btn op-btn-primary" disabled={busy} onClick={()=>void generate()}>자동 추천 구성안 생성</button><label>보존된 추천 결과<select aria-label="보존된 기술자산 추천" value={runId} disabled={busy} onChange={e=>{if(!canLeave())return;interaction.current++;setRunId(e.target.value);setAlternativeId('');setForm(null);setComp(null);setNote('');setReviewed(false);setCompare([]);persist('asset_run',e.target.value);persist('asset_alternative','');persist('asset_composition','');}}><option value="">추천 결과 선택</option>{runs.map((r,i)=><option key={r.id} value={r.id}>추천 {i+1}{r.current_valid?' · 현재 입력과 일치':' · 과거 결과'}</option>)}</select></label></div>
 {loading&&<p role="status">보존된 추천 결과를 조회합니다.</p>}{!loading&&!runs.length&&<p>생성된 추천안이 없습니다. 위 버튼으로 현재 요구와 기술자산을 분석하세요. 조회만으로 분석이나 구성을 저장하지 않습니다.</p>}
 {error&&<PortalErrorMessage error={error}/>}{message&&<p role="status">{message}</p>}
 {run&&<><p>{run.current_valid?'현재 입력과 일치하는 추천 초안':'과거 추천 · 새 구성에 사용 불가'}</p>{!run.current_valid&&<div role="alert"><p>기업 요구·분석 검토·기술자산이 변경되었습니다. 과거 결과를 보존하며 새 추천을 생성해야 합니다.</p>{run.stale_reasons.map(reason=><p key={reason}>{portalReasonText(reason,'변경된 입력이 있어 다시 검토해야 합니다.')}</p>)}<PortalReasonCodes codes={run.stale_reasons}/></div>}
 {run.data.status==='INPUT_INSUFFICIENT'&&<p>요구사항을 판단할 입력이 부족합니다. 필요한 추가정보부터 확인하세요.</p>}<h3>해결할 핵심 요구</h3>{run.data.demands.map(d=><details key={d.id}><summary>{d.text}{run.data.uncovered_demands.includes(d.id)?' · 해결 후보 없음':''}</summary><p>{d.uncertainty}</p>{d.evidence.map((e,i)=><blockquote key={i}>{String(e.quote??e.text??'근거 위치를 확인하세요.')}</blockquote>)}</details>)}
 <RecommendationNotes values={run.data.limitations}/>
 {!run.data.alternatives.length&&<p>현재 확인된 솔루션 없음. 부족한 입력과 실제 보유기술의 한계를 구분해 검토하세요.</p>}
 <div className="mvp-alternatives">{run.data.alternatives.map(a=><article className="mvp-option" key={a.id} data-alternative-id={a.id}><h3>{a.name}</h3><p>{kindLabel[a.kind]??a.kind} · {a.features.length}개 실제 기능</p><p>시스템: {a.systems.map(s=>s.name).join(' · ')}</p><p>모듈·원천 그룹: {a.modules.map(m=>m.name).join(' · ')}</p><AlternativeReason value={a}/><p>미해결·확인 필요: {a.unresolved.join(' · ')||'요구별 범위와 제공 조건을 확인하세요.'}</p><label className="mvp-checkbox"><input type="checkbox" aria-label={a.name+' 비교'} checked={compare.includes(a.id)} onChange={e=>setCompare(e.target.checked?[...compare,a.id]:compare.filter(id=>id!==a.id))}/>이 대안 비교</label><button className="op-btn op-btn-outline" disabled={busy||!run.current_valid} onClick={()=>choose(a)}>이 구성안 검토</button></article>)}</div>
 {compare.length>0&&<section aria-label="추천 구성안 비교"><h3>선택한 대안 비교</h3><div className="intake-table"><table><thead><tr><th>대안</th><th>연결 모듈</th><th>요구별 해결범위</th><th>연계 확인</th><th>남은 사항</th></tr></thead><tbody>{run.data.alternatives.filter(a=>compare.includes(a.id)).map(a=><tr key={a.id}><td>{a.name}</td><td>{a.modules.map(m=>m.name).join(' · ')}</td><td>{a.coverage.map((c,i)=><p key={i}>{c.requirement} · {c.status==='UNRESOLVED'?'미해결':'일부 해결 후보'}</p>)}</td><td>{a.integrations.map((l,i)=><p key={i}>{l.workflow} · {l.verification==='VERIFIED'?'검증 근거 있음':'연계 미검증'}</p>)}</td><td>{a.unresolved.join(' · ')}</td></tr>)}</tbody></table></div></section>}
 <details><summary>추천 입력·규칙·원천 식별</summary><p>{run.rule_version} · {run.input_digest}</p><p>추천 실행: {run.id} · 분석 실행: {run.analysis_run_id??'별도 분석 출처 없음'}</p><p>과거 결과의 입력·원천을 현재 상태로 교체하지 않습니다.</p></details>
 <button className="op-btn op-btn-outline" onClick={()=>{if(!canLeave())return;const u=new URL(window.location.href);u.searchParams.set('screen','requests');u.searchParams.set('company',cid);u.searchParams.set('version',run.input.basis?.source_version_id??vid);u.searchParams.delete('request_scope');window.location.assign(u.href);}}>이 기업의 추가정보 요청 검토</button></>}
 </Card>
 {form&&alternative&&run&&<Card title="추천 구성안 수정·운영자 검토"><fieldset disabled={busy||!run.current_valid}><legend>{alternative.name} 검토</legend><p>생성된 초안을 바탕으로 수정합니다. 제공 확인 필요·미검증 연계·미해결 사항은 확인될 때까지 남겨 주세요.</p>
 <label>조합 이름<input aria-label="기술자산 조합 이름" value={form.name} onChange={e=>{setForm({...form,name:e.target.value});setReviewed(false);}}/></label>
 {selectionChanged&&<p role="status" data-testid="asset-selection-review-notice">자동 초안의 기능 구성을 변경했습니다. 최종 구성의 선행 조건과 등록된 연계를 다시 확인하세요. 미검증 초안 저장과 고객 제안 가능 판단은 별개입니다.</p>}
 <h3>선택한 시스템·모듈과 기능</h3><SelectedFunctionSummary features={selectedFeatures}/>
 <details><summary>기능 추가·제외·모듈 교체</summary><p>이번 추천의 실제 기능 후보에서 선택합니다. 제외 후 남은 요구와 연계를 다시 검토하세요.</p>{selectedModules.map(module=><div className="intake-actions" key={module.id}><label>{module.name} 모듈 교체<select aria-label={module.name+' 교체 모듈'} value={replaceWith[module.id]??''} onChange={e=>setReplaceWith({...replaceWith,[module.id]:e.target.value})}><option value="">다른 실제 후보 모듈 선택</option>{moduleOptions.filter(m=>m.id!==module.id).map(m=><option value={m.id} key={m.id}>{m.name}</option>)}</select></label><button type="button" className="op-btn op-btn-outline" disabled={!replaceWith[module.id]} onClick={()=>{const kept=form.selections.filter(selection=>features.find(f=>f.revision_id===selection.feature_revision_id)?.module_id!==module.id).map(s=>s.feature_revision_id);changeSelection(Array.from(new Set([...kept,...features.filter(f=>f.module_id===replaceWith[module.id]).map(f=>f.revision_id)])));}}>선택 모듈로 교체</button></div>)}{features.map(f=><label key={f.revision_id} className="mvp-checkbox"><input type="checkbox" aria-label={f.name+' 구성 포함'} checked={form.selections.some(s=>s.feature_revision_id===f.revision_id)} onChange={e=>changeSelection(e.target.checked?[...form.selections.map(s=>s.feature_revision_id),f.revision_id]:form.selections.filter(s=>s.feature_revision_id!==f.revision_id).map(s=>s.feature_revision_id))}/>{f.system_name} · {f.module_name} · {f.name} · {assetStatusLabel[f.availability]??'제공 확인 필요'}<details><summary>기능 원천·근거</summary><p>{f.description??f.data?.description}</p><p>{f.external_id} · {f.revision_id}</p><p>{f.availability_evidence||'제공 검증 근거 미등록'}</p>{f.reasons?.map((r,i)=><p key={i}>{r}</p>)}</details></label>)}</details>
 {form.coverage.map((row,index)=>{const update=(patch:Partial<Coverage>)=>{setForm({...form,coverage:form.coverage.map((c,i)=>i===index?{...c,...patch}:c)});setReviewed(false);};return <fieldset key={index}><legend>{row.requirement}</legend><label>수행 역할<input aria-label={'자산 해결범위 '+(index+1)+' 수행 역할'} value={row.role} onChange={e=>update({role:e.target.value})}/></label><label>검토한 해결 상태<select aria-label={'자산 해결범위 '+(index+1)+' 해결 상태'} value={row.status} onChange={e=>update({status:e.target.value as Coverage['status']})}><option value="PARTIAL">일부 해결·확인 필요</option><option value="UNRESOLVED">미해결</option><option value="ADDRESSED" disabled={!row.feature_revision_ids.length||row.feature_revision_ids.some(id=>features.find(f=>f.revision_id===id)?.availability!=='VERIFIED')}>해결 범위 확인 완료</option></select></label>{(['addressed_scope','unaddressed_scope'] as const).map(key=><label key={key}>{key==='addressed_scope'?'해결하는 범위':'제외·미해결 범위'}<textarea aria-label={'자산 해결범위 '+(index+1)+(key==='addressed_scope'?' 설명':' 제외·미해결 범위')} value={row[key]} onChange={e=>update({[key]:e.target.value})}/></label>)}<label>추가 확인사항<textarea aria-label={'자산 해결범위 '+(index+1)+' 추가 확인사항'} value={row.missing_information.join('\n')} onChange={e=>update({missing_information:e.target.value.split('\n')})}/></label><details><summary>연결한 실제 기능·분석 근거</summary>{row.feature_revision_ids.map(id=><p key={id}>{features.find(f=>f.revision_id===id)?.name??'기능 참조 재확인 필요'}</p>)}{row.evidence_refs.map((e,i)=><blockquote key={i}>{String(e.quote??e.text??'연결된 입력 출처를 확인하세요.')}</blockquote>)}</details></fieldset>;})}
 <h3>데이터·업무 연결 초안</h3>{form.integrations.map((link,index)=>{const update=(patch:Partial<Integration>)=>{setForm({...form,integrations:form.integrations.map((l,i)=>i===index?{...l,...patch,verification:'UNVERIFIED',evidence_note:''}:l)});setReviewed(false);};return <fieldset key={index}><legend>연계 {index+1} · {link.verification==='VERIFIED'?'검증 근거 있음':'미검증 · 추가 확인 필요'}</legend><p>{link.evidence_note||'연계 검증 근거가 없습니다.'}</p>{(['from_asset_id','to_asset_id'] as const).map((key,position)=><label key={key}>{position?'받는 기술자산':'보내는 기술자산'}<select aria-label={'자산 연계 '+(index+1)+' '+key} value={link[key]} onChange={e=>update({[key]:e.target.value})}>{assetOptions.map(m=><option key={m.id} value={m.id}>{m.name}</option>)}</select></label>)}{(['data','workflow','uncertainty'] as const).map(key=><label key={key}>{{data:'전달 데이터',workflow:'업무 연결',uncertainty:'연계 불확실성'}[key]}<textarea aria-label={'자산 연계 '+(index+1)+' '+key} value={link[key]} onChange={e=>update({[key]:e.target.value})}/></label>)}<label>연계 선행조건<textarea value={link.prerequisites.join('\n')} onChange={e=>update({prerequisites:e.target.value.split('\n')})}/></label><button type="button" className="op-btn op-btn-outline" onClick={()=>{setForm({...form,integrations:form.integrations.filter((_,i)=>i!==index),unresolved:form.unresolved+'\n제외한 연계의 필요성과 대체 방안을 검토해야 합니다.'});setReviewed(false);}}>이 연계 제외</button></fieldset>;})}
 <button type="button" className="op-btn op-btn-outline" disabled={selectedModules.length<2} onClick={()=>{if(selectedModules.length<2)return;setForm({...form,integrations:[...form.integrations,{from_asset_id:selectedModules[0].id,to_asset_id:selectedModules[1].id,data:'연결할 실제 데이터를 확인하세요.',workflow:'모듈 사이 업무 연결 범위를 검토하세요.',prerequisites:['인터페이스·데이터 형식 제공 여부 확인'],verification:'UNVERIFIED',evidence_note:'',uncertainty:'운영자가 추가한 연계 초안이며 실제 연결은 검증되지 않았습니다.'}]});setReviewed(false);}}>추가 연계 검토 항목</button>
 <label>적용조건<textarea aria-label="자산 구성 적용조건" value={form.conditions} onChange={e=>{setForm({...form,conditions:e.target.value});setReviewed(false);}}/></label><label>미해결·추가 확인사항<textarea aria-label="자산 구성 미해결 사항" value={form.unresolved} onChange={e=>{setForm({...form,unresolved:e.target.value});setReviewed(false);}}/></label>
 <label>운영자 검토 의견<textarea aria-label="기술자산 조합 검토 의견" value={note} onChange={e=>setNote(e.target.value)}/></label><label className="mvp-checkbox"><input type="checkbox" aria-label="기술자산 조합 근거·제공상태·연계 검토" checked={reviewed} onChange={e=>setReviewed(e.target.checked)}/>선택한 기능·제공 검증 상태·해결범위·연계와 남은 사항을 검토했습니다.</label>
 {issues.length>0&&<div aria-label="기술자산 조합 저장 조건">{issues.map((issue,i)=><p key={i}>{issue}</p>)}</div>}
 <button className="op-btn op-btn-primary" disabled={busy||!canSave} onClick={()=>void save()}>{comp?'검토한 기술자산 조합 새 버전 저장':'검토한 기술자산 조합 저장'}</button>
 </fieldset><button className="op-btn op-btn-outline" disabled={!comp||busy||dirty||!run.current_valid} onClick={onNext}>이 조합의 지원사업 검토·매칭</button>
 {history.length>0&&<details><summary>보존된 기술자산 조합 이력</summary>{history.map(v=><section key={v.id}><h3>v{v.ordinal} · {v.data.name}</h3><p>{v.data.asset_review_note}</p><p>{v.data.unresolved.join(' · ')}</p></section>)}</details>}
 </Card>}
 </div>;
}
