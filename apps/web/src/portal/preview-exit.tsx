import {createContext,useContext,useId,useLayoutEffect,useState,type ReactNode} from 'react';
import {createPortalWorkStore,PortalWorkContext} from './portal-work-state';
import {LogoutDialog} from './logout-dialog';
const PreviewExitContext=createContext<(exit:()=>void)=>void>(exit=>exit());
const PreviewDiscardContext=createContext<Map<string,()=>void>|null>(null);
/** Preview exits share draft confirmation only; this never calls an authentication API. */
export function PreviewExitProvider({children}:{children:ReactNode}){
 const [discarders]=useState(()=>new Map<string,()=>void>());
 const [work]=useState(createPortalWorkStore),[pending,setPending]=useState<(()=>void)|null>(null);
 const request=(exit:()=>void)=>{if(work.read().dirty)setPending(()=>exit);else exit();};
 return <PortalWorkContext.Provider value={work}><PreviewExitContext.Provider value={request}><PreviewDiscardContext.Provider value={discarders}>{children}</PreviewDiscardContext.Provider>{pending&&<LogoutDialog preview busy={false} onContinue={()=>setPending(null)} onDiscard={()=>{for(const discard of discarders.values())discard();setPending(null);pending();}}/>}</PreviewExitContext.Provider></PortalWorkContext.Provider>;
}
export const usePreviewExit=()=>useContext(PreviewExitContext);

/** Restore only local drafts to their existing reflection baseline on explicit discard. */
export function usePreviewDiscard(discard:()=>void){
 const registry=useContext(PreviewDiscardContext),id=useId();
 useLayoutEffect(()=>{registry?.set(id,discard);return()=>{registry?.delete(id);};},[registry,id,discard]);
}
