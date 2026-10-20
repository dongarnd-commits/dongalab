import React, {useEffect,useRef,useState} from 'react';
import {createRoot} from 'react-dom/client';
import type {PortalIdentity} from './types';
export function mountPortal(render:(identity:PortalIdentity,logout:()=>void)=>React.ReactNode){
 const identity:PortalIdentity=JSON.parse(document.getElementById('portal-identity')!.textContent!);
 function Session(){
  const [ready,setReady]=useState(false),[error,setError]=useState('');
  const ending=useRef(false);
  useEffect(()=>{
   let live=true,sequence=0;const channel=new BroadcastChannel('datco-session');
   const exit=()=>{live=false;setReady(false);sessionStorage.clear();window.location.replace('/login');};
   const check=async()=>{if(ending.current)return;const epoch=++sequence;try{
    const r=await fetch('/api/notice/session',{cache:'no-store',credentials:'same-origin',signal:AbortSignal.timeout(10000)});
    if(!live||ending.current||epoch!==sequence)return;
    if(r.status===401||r.status===403){exit();return;}if(!r.ok)throw Error();
    const actual=await r.json();if(!live||ending.current||epoch!==sequence)return;
    if(actual.id!==identity.id||actual.role!==identity.role){exit();return;}
    setError('');setReady(true);
   }catch{if(live&&epoch===sequence){setReady(false);setError('세션을 확인할 수 없습니다. 다시 로그인해 주세요.');}}};
   const hide=()=>{++sequence;setReady(false);document.getElementById('root')!.style.visibility='hidden';};
   const show=()=>{setReady(false);document.getElementById('root')!.style.visibility='visible';void check();};
   const visible=()=>{if(document.hidden)hide();else show();};
   channel.onmessage=exit;window.addEventListener('pagehide',hide);window.addEventListener('pageshow',show);window.addEventListener('focus',show);document.addEventListener('visibilitychange',visible);
   const timer=window.setInterval(()=>{if(!document.hidden)void check();},15000);void check();
   return()=>{live=false;++sequence;clearInterval(timer);channel.close();window.removeEventListener('pagehide',hide);window.removeEventListener('pageshow',show);window.removeEventListener('focus',show);document.removeEventListener('visibilitychange',visible);};
  },[]);
  const logout=async()=>{ending.current=true;setReady(false);setError('로그아웃 중입니다.');try{
   const r=await fetch('/api/notice/session/logout',{method:'POST',cache:'no-store',signal:AbortSignal.timeout(10000)});
   if(!r.ok)throw Error();sessionStorage.clear();const ch=new BroadcastChannel('datco-session');ch.postMessage('account-change');ch.close();window.location.replace('/login');
  }catch{setError('로그아웃을 확인하지 못했습니다. 다시 시도해 주세요.');}};
  if(!ready)return <main role="status" style={{padding:32,fontFamily:'sans-serif'}}>{error||'세션 확인 중입니다.'}{error&&<><button onClick={()=>void logout()}>로그아웃 재시도</button><a href="/login">로그인으로 이동</a></>}</main>;
  return <>{render(identity,()=>void logout())}</>;
 }
 createRoot(document.getElementById('root')!).render(<Session/>);
}
