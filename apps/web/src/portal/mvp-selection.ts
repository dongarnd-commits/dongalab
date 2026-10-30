import {useEffect} from 'react';
/** URL references are navigation hints only. Each consumer validates scoped API results. */
export function useMvpDirty(onDirty:((value:boolean)=>void)|undefined,value:boolean){
 useEffect(()=>{onDirty?.(value);return()=>onDirty?.(false);},[onDirty,value]);
}
export function readMvpSelection(company:string,version:string,key:string){
 const q=new URLSearchParams(window.location.search);
 return q.get('mvp_company')===company&&q.get('mvp_version')===version?q.get('mvp_'+key)??'':'';
}
export function writeMvpSelection(company:string,version:string,values:Record<string,string>){
 const url=new URL(window.location.href);
 if(url.searchParams.get('mvp_company')!==company||url.searchParams.get('mvp_version')!==version){
  for(const key of Array.from(url.searchParams.keys()))if(key.startsWith('mvp_'))url.searchParams.delete(key);
 }
 url.searchParams.set('mvp_company',company);url.searchParams.set('mvp_version',version);
 for(const [key,value]of Object.entries(values)){if(value)url.searchParams.set('mvp_'+key,value);else url.searchParams.delete('mvp_'+key);}
 window.history.replaceState(window.history.state,'',url);
}
