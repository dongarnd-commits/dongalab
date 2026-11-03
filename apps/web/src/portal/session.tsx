import React, {useEffect,useRef,useState} from 'react';
import {createRoot} from 'react-dom/client';
import type {PortalIdentity} from './types';
import {createPortalWorkStore,PortalWorkContext} from './portal-work-state';
import {LogoutDialog} from './logout-dialog';
export function mountPortal(render:(identity:PortalIdentity,logout:()=>void)=>React.ReactNode){
 const identity:PortalIdentity=JSON.parse(document.getElementById('portal-identity')!.textContent!);
 function Session(){
  const [ready,setReady]=useState(false),[error,setError]=useState('');
  const ending=useRef(false);
  const [work]=useState(createPortalWorkStore),[confirmLogout,setConfirmLogout]=useState(false),[loggingOut,setLoggingOut]=useState(false),[logoutError,setLogoutError]=useState('');
  // Error UI is committed without business data before revealing a failed cached-page check.
  useEffect(()=>{if(error)document.getElementById('root')!.style.visibility='visible';},[error]);
  useEffect(()=>{
   let live=true,sequence=0,pending=false,cacheHidden=false,request:AbortController|null=null;const channel=new BroadcastChannel('datco-session');
   const exit=()=>{live=false;++sequence;request?.abort();setReady(false);sessionStorage.clear();window.location.replace(identity.role==='DATCO_OPERATOR'&&window.location.pathname==='/portal/operator'&&new URLSearchParams(window.location.search).has('company')&&new URLSearchParams(window.location.search).has('version')?'/login?returnTo='+encodeURIComponent(window.location.pathname+window.location.search):'/login');};
   const check=async(fresh=false)=>{if(!live||ending.current||pending&&!fresh)return;const epoch=++sequence;request?.abort();request=new AbortController();pending=true;try{
    const r=await fetch('/api/notice/session',{cache:'no-store',credentials:'same-origin',signal:AbortSignal.any([request.signal,AbortSignal.timeout(10000)])});
    if(!live||ending.current||epoch!==sequence)return;
    if(r.status===401||r.status===403){exit();return;}if(!r.ok)throw Error();
    const actual=await r.json();if(!live||ending.current||epoch!==sequence)return;
    if(actual.id!==identity.id||actual.role!==identity.role){exit();return;}
    setError('');setReady(true);if(!cacheHidden)document.getElementById('root')!.style.visibility='visible';
    window.dispatchEvent(new Event('datco-session-verified'));
   }catch{if(live&&!ending.current&&epoch===sequence){setReady(false);setError('세션을 확인할 수 없습니다. 다시 로그인해 주세요.');}}
   finally{if(epoch===sequence)pending=false;}};
   // Preserve mounted business UI during normal session checks. Hide only cached page restoration.
   const hide=()=>{cacheHidden=true;++sequence;request?.abort();pending=false;document.getElementById('root')!.style.visibility='hidden';};
   const show=()=>{cacheHidden=false;void check(true);};
   const focus=()=>void check();const visible=()=>{if(!document.hidden)void check();};
   channel.onmessage=exit;window.addEventListener('pagehide',hide);window.addEventListener('pageshow',show);window.addEventListener('focus',focus);document.addEventListener('visibilitychange',visible);
   // Session security polling is retained; business revalidation follows this single verified event.
   const timer=window.setInterval(()=>{if(!document.hidden)void check();},15000);void check();
   return()=>{live=false;++sequence;request?.abort();clearInterval(timer);channel.close();window.removeEventListener('pagehide',hide);window.removeEventListener('pageshow',show);window.removeEventListener('focus',focus);document.removeEventListener('visibilitychange',visible);};
  },[]);
  const logout=async()=>{
   if(ending.current)return;
   const state=work.read();
   if(state.busy||state.uncertain){setConfirmLogout(false);setLogoutError(state.busy?'저장·제출·발송 처리 중입니다. 결과가 표시된 뒤 로그아웃해 주세요.':'처리 결과가 불확실합니다. 해당 업무의 저장·발송 상태를 다시 조회한 뒤 로그아웃해 주세요.');return;}
   ending.current=true;setLoggingOut(true);setLogoutError('');
   try{
    const r=await fetch('/api/notice/session/logout',{method:'POST',cache:'no-store',signal:AbortSignal.timeout(10000)});
    if(!r.ok)throw Error();
    sessionStorage.clear();const ch=new BroadcastChannel('datco-session');ch.postMessage('account-change');ch.close();
    window.location.replace(identity.role==='DATCO_OPERATOR'&&window.location.pathname==='/portal/operator'&&new URLSearchParams(window.location.search).has('company')&&new URLSearchParams(window.location.search).has('version')?'/login?returnTo='+encodeURIComponent(window.location.pathname+window.location.search):'/login');
   }catch{ending.current=false;setLoggingOut(false);setConfirmLogout(false);setLogoutError('로그아웃을 확인하지 못했습니다. 작성 내용을 유지했습니다. 다시 시도해 주세요.');}
  };
  const requestLogout=()=>{const state=work.read();if(state.busy||state.uncertain){void logout();return;}if(state.dirty)setConfirmLogout(true);else void logout();};
  if(!ready)return <main role="status" style={{padding:32,fontFamily:'sans-serif'}}>{error||'세션 확인 중입니다.'}{error&&<><button onClick={()=>void logout()}>로그아웃 재시도</button><a href="/login">로그인으로 이동</a></>}</main>;
  return <PortalWorkContext.Provider value={work}><div style={{display:'contents'}} inert={loggingOut}>{render(identity,requestLogout)}</div>{loggingOut&&<div className="portal-session-feedback" role="status">로그아웃 중입니다. 서버 결과를 기다려 주세요.</div>}{logoutError&&<div className="portal-session-feedback portal-session-error" role="alert">{logoutError}<button type="button" onClick={requestLogout}>로그아웃 재시도</button><button type="button" onClick={()=>setLogoutError('')}>작성 화면으로 돌아가기</button></div>}{confirmLogout&&<LogoutDialog busy={loggingOut} onContinue={()=>setConfirmLogout(false)} onDiscard={()=>void logout()}/>}</PortalWorkContext.Provider>;
 }
 createRoot(document.getElementById('root')!).render(<Session/>);
}
