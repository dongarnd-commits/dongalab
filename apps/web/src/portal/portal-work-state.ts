import {createContext,useContext,useId,useLayoutEffect,useRef} from 'react';
export type PortalWorkState={dirty?:boolean;busy?:boolean;uncertain?:boolean};
export function createPortalWorkStore(){
 const entries=new Map<string,PortalWorkState>();
 return {set:(key:string,value:PortalWorkState)=>{entries.set(key,value);},clear:(key:string)=>{entries.delete(key);},read:()=>({dirty:[...entries.values()].some(s=>s.dirty),busy:[...entries.values()].some(s=>s.busy),uncertain:[...entries.values()].some(s=>s.uncertain)})};
}
export const PortalWorkContext=createContext<ReturnType<typeof createPortalWorkStore>|null>(null);
/** Register semantic changes, never search/filter selection. retainKey preserves cached drafts across screens. */
export function usePortalWorkState(state:PortalWorkState,retainKey?:string){
 const store=useContext(PortalWorkContext),id=useId(),key=retainKey??id,latest=useRef(state);const {dirty,busy,uncertain}=state;
 useLayoutEffect(()=>{const current={dirty,busy,uncertain};latest.current=current;store?.set(key,current);},[store,key,dirty,busy,uncertain]);
 useLayoutEffect(()=>()=>{if(retainKey&&(latest.current.dirty||latest.current.uncertain))store?.set(key,{...latest.current,busy:false});else store?.clear(key);},[store,key,retainKey]);
 return ()=>{latest.current={};store?.clear(key);};
}
