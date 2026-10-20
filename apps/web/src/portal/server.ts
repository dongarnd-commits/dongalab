import {readFile} from 'node:fs/promises';
import path from 'node:path';
import type {PortalRole} from './types';
const roles:Record<string,PortalRole>={company:'COMPANY_EDITOR',operator:'DATCO_OPERATOR',admin:'DATCO_ADMIN'};
const headers={'Cache-Control':'no-store, private','Vary':'Cookie','X-Robots-Tag':'noindex, nofollow','X-Content-Type-Options':'nosniff'};
export async function servePortal(request:Request,portal:string){
 const role=roles[portal];if(!role)return new Response('Not Found',{status:404,headers});
 const origin=process.env.API_ORIGIN??'http://127.0.0.1:8000';
 try{
  const response=await fetch(origin+'/notice/session',{headers:{Cookie:request.headers.get('cookie')??''},cache:'no-store',signal:AbortSignal.timeout(10000)});
  if(response.status===401)return new Response(null,{status:303,headers:{...headers,Location:'/login'}});
  if(!response.ok)return new Response('Session unavailable',{status:503,headers});
  const actor=await response.json();if(actor.role!==role)return new Response('Forbidden',{status:403,headers});
  if(typeof actor.id!=='string')return new Response('Session unavailable',{status:503,headers});
  // Identity only: no Company/Site/Improvement/business context is projected here.
  let name=actor.id;
  const workspace=await fetch(origin+'/workspace',{headers:{Cookie:request.headers.get('cookie')??''},cache:'no-store',signal:AbortSignal.timeout(10000)});
  if(workspace.ok){const info=await workspace.json();if(info.actor?.id===actor.id&&typeof info.actor.username==='string')name=info.actor.username;}
  const identity=JSON.stringify({id:actor.id,role:actor.role,name}).replaceAll('<','\u003c');
  const directory=path.join(process.cwd(),'.role-portals',portal);
  const [js,css]=await Promise.all([readFile(path.join(directory,'portal.js'),'utf8'),readFile(path.join(directory,'portal.css'),'utf8')]);
  return new Response(`<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>DATCO ONE</title><style>${css.replaceAll('</style','<\/style')}</style></head><body><div id="root"></div><script type="application/json" id="portal-identity">${identity}</script><script>${js.replaceAll('</script','<\/script')}</script></body></html>`,{headers:{...headers,'Content-Type':'text/html; charset=utf-8','Content-Security-Policy':"default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; connect-src 'self'; form-action 'none'; base-uri 'none'; frame-ancestors 'none'"}});
 }catch{return new Response('Portal unavailable',{status:503,headers});}
}
