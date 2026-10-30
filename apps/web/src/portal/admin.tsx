import React,{useEffect,useState} from 'react';
import AdminPortal from '../ui-preview/admin/AdminPortal';
import {mountPortal} from './session';
import type {PortalIdentity} from './types';
import {AdminLive} from './admin-live';
export type AdminCatalogRead={status:'loading'|'ready'|'error';data:{features:number;published:number}|null};
function Portal({session,onLogout}:{session:PortalIdentity;onLogout:()=>void}){
 const [catalogRead,setCatalogRead]=useState<AdminCatalogRead>({status:'loading',data:null});
 useEffect(()=>{const abort=new AbortController();let epoch=0;
  const load=async()=>{const request=++epoch;try{const r=await fetch('/api/workspace',{cache:'no-store',signal:abort.signal});if(!r.ok)throw Error();const d=await r.json();if(abort.signal.aborted||request!==epoch)return;if(d.actor?.id!==session.id||d.actor?.role!==session.role){window.location.replace('/login');return;}
   if(!d.catalog||!Number.isSafeInteger(d.catalog.features)||d.catalog.features<0||!Number.isSafeInteger(d.catalog.published)||d.catalog.published<0)throw Error();
   setCatalogRead({status:'ready',data:{features:d.catalog.features,published:d.catalog.published}});
  }catch{if(!abort.signal.aborted&&request===epoch)setCatalogRead({status:'error',data:null});}};
  const first=window.setTimeout(()=>void load(),0),timer=window.setInterval(()=>void load(),15000);return()=>{abort.abort();clearTimeout(first);clearInterval(timer);};
 },[session.id,session.role]);
 return <AdminPortal session={session} onLogout={onLogout} catalogRead={catalogRead} renderLive={(screen,detail)=>['overview','reference','users','infrastructure','ai-quality'].includes(screen)?<AdminLive key={session.id+screen} session={session} screen={screen} detail={detail}/>:null}/>;
}
mountPortal((session,onLogout)=><Portal session={session} onLogout={onLogout}/>);
