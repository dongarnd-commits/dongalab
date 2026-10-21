import React,{useCallback,useEffect,useRef,useState} from 'react';
import type {PortalIdentity} from './types';
import './context.css';
export type CompanyRef={id:string;name:string};
type SiteVersion={ordinal:number;data:{name:string;address:string;industry:string;process:string}};
type Site={id:string;name:string;current_ordinal:number;versions:SiteVersion[]};
type ImprovementVersion={id:string;ordinal:number;site_ordinal:number;data:Record<string,string>};
type Improvement={id:string;site_id:string;title:string;state:string;current_ordinal:number;versions:ImprovementVersion[]};
export type NavigationContext={company:CompanyRef & {current_ordinal:number};sites:Site[];improvements:Improvement[];selection:{company_id:string;site_id:string|null;site_ordinal:number|null;improvement_id:string|null;improvement_version_id:string|null;improvement_ordinal:number|null;is_latest_version:boolean|null}};
export type ContextState={status:'loading'|'ready'|'empty'|'error';companies:CompanyRef[];value:NavigationContext|null;error:string};
const keys=['company','site','site_version','improvement','version','context_actor'];
export function selectedContext(value:NavigationContext|null|undefined){
 const s=value?.sites.find(s=>s.id===value.selection.site_id),sv=s?.versions.find(v=>v.ordinal===value?.selection.site_ordinal);
 const i=value?.improvements.find(i=>i.id===value.selection.improvement_id),v=i?.versions.find(v=>v.id===value?.selection.improvement_version_id);
 return {site:s,siteVersion:sv,improvement:i,version:v};
}
function editQuery(changes:Record<string,string|null>){const u=new URL(window.location.href);for(const [key,value] of Object.entries(changes)){if(value)u.searchParams.set(key,value);else u.searchParams.delete(key);}if(u.href!==window.location.href)window.history.replaceState({},'',u);}
class ReadFailure extends Error{constructor(public status:number){super();}}
async function read(url:string,signal:AbortSignal){const r=await fetch(url,{cache:'no-store',signal});if(!r.ok)throw new ReadFailure(r.status);return r.json();}
export function useBusinessContext(session:PortalIdentity){
 const [state,setState]=useState<ContextState>({status:'loading',companies:[],value:null,error:''});const generation=useRef(0),controller=useRef<AbortController|null>(null);
 const load=useCallback(async(verified=false)=>{
  const epoch=++generation.current;controller.current?.abort();const request=new AbortController();controller.current=request;
  let companies:CompanyRef[]=[];
  try{
   const u=new URL(window.location.href);if(u.searchParams.has('context_actor')&&u.searchParams.get('context_actor')!==session.id){for(const k of keys)u.searchParams.delete(k);window.history.replaceState({},'',u);}
   const [actor,list]=verified?[session,await read('/api/company',request.signal)]:await Promise.all([read('/api/notice/session',request.signal),read('/api/company',request.signal)]);
   if(epoch!==generation.current||request.signal.aborted)return;
   if(actor.id!==session.id||actor.role!==session.role){setState({status:'loading',companies:[],value:null,error:''});window.location.replace('/login');return;}
   if(!Array.isArray(list)||list.some(c=>typeof c.id!=='string'||typeof c.name!=='string'))throw Error();
   companies=list.map(c=>({id:c.id,name:c.name}));let cid=u.searchParams.get('company');
   if(!cid&&companies.length===1)cid=companies[0].id;
   if(!cid){setState({status:companies.length?'ready':'empty',companies,value:null,error:''});return;}
   const query=new URLSearchParams();for(const [key,param] of [['site','site_id'],['site_version','site_ordinal'],['improvement','improvement_id'],['version','version_id']]){const v=u.searchParams.get(key);if(v)query.set(param,v);}
   const value:NavigationContext=await read('/api/company/'+encodeURIComponent(cid)+'/navigation?'+query,request.signal);
   if(epoch!==generation.current||request.signal.aborted)return;
   if(value.company.id!==cid||value.selection.company_id!==cid||!companies.some(c=>c.id===cid))throw new ReadFailure(404);
   const selected=value.selection;editQuery({company:cid,site:selected.site_id,site_version:selected.site_ordinal?.toString()??null,improvement:selected.improvement_id,version:selected.improvement_version_id,context_actor:session.id});
   setState(previous=>previous.status==='ready'&&JSON.stringify(previous.companies)===JSON.stringify(companies)&&JSON.stringify(previous.value)===JSON.stringify(value)?previous:{status:'ready',companies,value,error:''});
  }catch(e){if(epoch!==generation.current||request.signal.aborted)return;if(e instanceof ReadFailure&&e.status===401){setState({status:'loading',companies:[],value:null,error:''});window.location.replace('/login');return;}
   const error=e instanceof ReadFailure?(e.status===403?'접근권한이 없습니다.':e.status===404?'선택 항목이 없거나 접근할 수 없습니다.':e.status===409?'사업장과 개선요구의 수정 이력을 다시 선택해 주세요.':e.status===422?'선택 값이 올바르지 않습니다.':'조회를 완료하지 못했습니다.'):'연결을 확인하고 다시 조회해 주세요.';
   setState({status:'error',companies,value:null,error});}
 },[session]);
 useEffect(()=>{const initial=window.setTimeout(()=>void load(),0);const changed=()=>{setState({status:'loading',companies:[],value:null,error:''});void load();};const verified=()=>void load(true);window.addEventListener('popstate',changed);window.addEventListener('datco-session-verified',verified);return()=>{controller.current?.abort();clearTimeout(initial);window.removeEventListener('popstate',changed);window.removeEventListener('datco-session-verified',verified);};},[load]);
 const choose=(changes:Record<string,string|null>)=>{setState({status:'loading',companies:[],value:null,error:''});editQuery({...changes,context_actor:session.id});return load();};
 return {state,refresh:()=>void load(),choose};
}
export type BusinessContext=ReturnType<typeof useBusinessContext>;
export function CompanyContextStatus({business,hideEmpty=false}:{business:BusinessContext;hideEmpty?:boolean}){const {state,choose}=business;if(state.status==='ready'||hideEmpty&&state.status==='empty')return null;return <p role={state.status==='error'?'alert':'status'}>{state.status==='error'?state.error:state.status==='empty'?'접근 가능한 기업이 없습니다.':'조회 중입니다.'}{state.status==='error'&&<button type="button" onClick={()=>choose({company:null,site:null,site_version:null,improvement:null,version:null})}>선택 초기화</button>}</p>;}
export function BusinessContextBar({business,view='operator',onNavigate,embedded=false}:{business:BusinessContext;embedded?:boolean;view?:'summary'|'sites'|'improvements'|'operator';onNavigate?:(page:'company'|'needs')=>void}){
 const {state,choose,refresh}=business,value=state.value,selected=selectedContext(value);
 const sites=view==='sites'||view==='improvements'||view==='operator',needs=view==='improvements'||view==='operator';
 return <section className={embedded?"portal-business-selection":"portal-context"} aria-label={embedded?(view==='sites'?'사업장 선택':'개선요구 선택'):'기업 업무 정보'} data-company-id={value?.company.id??''} data-site-id={value?.selection.site_id??''} data-improvement-id={value?.selection.improvement_id??''} data-version-id={value?.selection.improvement_version_id??''}>
 {!embedded&&<div className="portal-context-row"><strong>{value?.company.name??'기업 업무 정보'}</strong><button type="button" onClick={refresh}>다시 조회</button></div>}
 {state.status==='loading'&&<p role="status">조회 중입니다.</p>}{state.status==='error'&&<><p role="alert">{state.error}</p><button type="button" onClick={()=>choose({company:null,site:null,site_version:null,improvement:null,version:null})}>선택 초기화</button></>}{state.status==='empty'&&<p>접근 가능한 기업이 없습니다. 기업 신규 등록은 후속 단계에서 연결합니다.</p>}
 {state.status!=='loading'&&state.companies.length>1&&<label>접근 가능한 기업<select aria-label="업무 기업 선택" value={value?.company.id??''} onChange={e=>choose({company:e.target.value,site:null,site_version:null,improvement:null,version:null})}><option value="">기업 선택</option>{state.companies.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label>}
 {value&&<>
 {view==='summary'&&<><p>등록된 사업장: {value.sites.map(s=>s.name).join(', ')||'등록된 사업장이 없습니다.'}</p><p>등록된 개선요구</p>{value.improvements.length?<ul>{value.improvements.map(i=><li key={i.id}>{i.id===selected.improvement?.id?selected.version?.data.title??i.title:i.title} · 현재 {improvementStateLabel(i.state)}</li>)}</ul>:<p>등록된 개선요구가 없습니다.</p>}<div className="portal-context-row"><button type="button" onClick={()=>onNavigate?.('company')}>사업장 관리</button><button type="button" onClick={()=>onNavigate?.('needs')}>개선요구 관리</button></div></>}
 {sites&&(value.sites.length>1?<label>사업장<select aria-label="업무 사업장 선택" value={value.selection.site_id??''} onChange={e=>choose({site:e.target.value,site_version:null,improvement:null,version:null})}><option value="">사업장 선택</option>{value.sites.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></label>:<p>사업장: {selected.siteVersion?.data.name??selected.site?.name??'등록된 사업장이 없습니다.'}</p>)}
 {sites&&selected.siteVersion&&<p>선택한 사업장: {selected.siteVersion.data.name} · {selected.siteVersion.data.address}</p>}
 {view==='sites'&&<button type="button" onClick={()=>onNavigate?.('needs')}>이 사업장의 개선요구 확인</button>}
 {needs&&value.selection.site_id&&<label>개선요구<select aria-label="업무 개선요구 선택" value={value.selection.improvement_id??''} onChange={e=>choose({improvement:e.target.value,version:null,site_version:null})}><option value="">{value.improvements.some(i=>i.site_id===value.selection.site_id)?'개선요구 선택':'등록된 개선요구가 없습니다.'}</option>{value.improvements.filter(i=>i.site_id===value.selection.site_id).map(i=><option key={i.id} value={i.id}>{i.title}</option>)}</select></label>}
 {needs&&selected.improvement&&<><p>현재 업무 상태: {improvementStateLabel(selected.improvement.state)}{value.selection.is_latest_version?'':' · 이전 작성 내용 조회 중'}</p><details><summary>수정 이력</summary><label>작성 내용 선택<select aria-label="개선요구 수정 이력" value={value.selection.improvement_version_id??''} onChange={e=>choose({version:e.target.value,site_version:null})}>{selected.improvement.versions.map(v=><option key={v.id} value={v.id}>{v.data.title} · {v.ordinal===selected.improvement?.current_ordinal?'최신 기록':'이전 기록'}</option>)}</select></label><p>선택한 작성 내용을 유지합니다. 새 기록이 생겨도 자동으로 변경하지 않습니다.</p></details></>}
 </>}
 {!value&&state.status==='ready'&&<p>기업을 선택해 업무 정보를 확인하세요.</p>}
 </section>;
}
export function improvementStateLabel(state:string){return ({DRAFT:'작성 중',SUBMITTED:'제출됨',UNDER_REVIEW:'검토 중',CONFIRMED:'확인됨',NEEDS_INFO:'보완 필요'} as Record<string,string>)[state]??state;}
export function ContextReadout({value}:{value:NavigationContext|null}){const {siteVersion,version}=selectedContext(value);if(!value)return null;return <section className="portal-context-readout" aria-label="선택 업무 원문"><h3>{value.company.name} · {siteVersion?.data.name??'사업장 미선택'}</h3>{version?<><h4>{version.data.title}</h4>{[['원문','original_text'],['As-Is','as_is'],['문제','problem'],['개선목표','goal'],['To-Be','to_be'],['제약','constraints']].map(([label,key])=><p key={key}><b>{label}</b><span>{version.data[key]||'입력 내용 없음'}</span></p>)}</>:<p>개선요구를 선택하면 저장된 작성 내용을 확인할 수 있습니다.</p>}</section>;}
