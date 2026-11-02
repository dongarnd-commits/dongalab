import {useEffect,useState} from 'react';
import {companyRequest} from '../company/client';
import type {CompanyWorkflow} from './workflow';
export function CompanyHomeSummary({w}:{w:CompanyWorkflow}){
 const [state,setState]=useState<{cid:string;requests:number;proposals:number}|null>(null),[error,setError]=useState<string|null>(null);
 useEffect(()=>{const cid=w.cid;if(!cid)return;const controller=new AbortController();const deadline=setTimeout(()=>{setError(cid);controller.abort();},15000);void Promise.all([companyRequest<{state:string}[]>('/'+w.cid+'/information-requests',undefined,controller.signal),fetch('/api/proposal/inbox/'+w.cid,{signal:controller.signal,credentials:'same-origin',cache:'no-store'}).then(async r=>{if(!r.ok)throw Error();return r.json() as Promise<unknown[]>;})]).then(([requests,proposals])=>{clearTimeout(deadline);if(!controller.signal.aborted)setState({cid,requests:requests.filter(r=>r.state!=='VERIFIED').length,proposals:proposals.length});}).catch(()=>{if(!controller.signal.aborted)setError(cid);});return()=>{clearTimeout(deadline);controller.abort();};},[w.cid,w.session.id]);
 if(!w.cid)return <p>기업을 선택하거나 ‘기업정보 등록 시작’에서 서류 업로드 또는 직접 입력으로 시작하세요.</p>;
 if(!w.detail)return <p role={w.error?'alert':'status'}>{w.error||'기업 현황을 조회 중입니다.'}</p>;
 return <div className="mb-5 rounded-xl border border-slate-200 bg-white p-4 text-sm" aria-label="실제 기업 현황"><p>등록 사업장 {w.detail.sites.length}개 · 개선요구 {w.detail.improvements.length}건 · 제출 이력이 있는 개선요구 {w.detail.improvements.filter(i=>i.versions.some(v=>v.reviews?.some(r=>r.outcome==='SUBMIT'))).length}건</p>{error===w.cid?<p role="alert">보완 요청·제안서 현황을 조회하지 못했습니다. 해당 메뉴에서 다시 확인해 주세요.</p>:state?.cid===w.cid?<p>미완료 보완 요청 {state.requests}건 · 받은 제안서 {state.proposals}건</p>:<p role="status">보완 요청·제안서 현황 조회 중입니다.</p>}</div>;
}
