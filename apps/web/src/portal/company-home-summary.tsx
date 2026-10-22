import {useEffect,useState} from 'react';
import {companyRequest} from '../company/client';
import type {CompanyWorkflow} from './workflow';
export function CompanyHomeSummary({w}:{w:CompanyWorkflow}){
 const [state,setState]=useState<{requests:number;proposals:number}|null>(null),[error,setError]=useState(false);
 useEffect(()=>{if(!w.cid)return;const controller=new AbortController();void Promise.all([companyRequest<{state:string}[]>('/'+w.cid+'/information-requests',undefined,controller.signal),fetch('/api/proposal/inbox/'+w.cid,{signal:controller.signal,credentials:'same-origin',cache:'no-store'}).then(async r=>{if(!r.ok)throw Error();return r.json() as Promise<unknown[]>;})]).then(([requests,proposals])=>{if(!controller.signal.aborted)setState({requests:requests.filter(r=>r.state!=='VERIFIED').length,proposals:proposals.length});}).catch(()=>{if(!controller.signal.aborted)setError(true);});return()=>controller.abort();},[w.cid,w.session.id]);
 if(!w.detail)return <p role={w.error?'alert':'status'}>{w.error||'기업 현황을 조회 중입니다.'}</p>;
 return <div className="mb-5 rounded-xl border border-slate-200 bg-white p-4 text-sm" aria-label="실제 기업 현황"><p>등록 사업장 {w.detail.sites.length}개 · 개선요구 {w.detail.improvements.length}건 · 제출 이력이 있는 개선요구 {w.detail.improvements.filter(i=>i.versions.some(v=>v.reviews?.some(r=>r.outcome==='SUBMIT'))).length}건</p>{error?<p role="alert">보완 요청·제안서 현황을 조회하지 못했습니다. 해당 메뉴에서 다시 확인해 주세요.</p>:state?<p>미완료 보완 요청 {state.requests}건 · 받은 제안서 {state.proposals}건</p>:<p role="status">보완 요청·제안서 현황 조회 중입니다.</p>}</div>;
}
