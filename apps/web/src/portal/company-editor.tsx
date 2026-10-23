import {useEffect,useRef,type ReactNode} from 'react';
import {secondary} from './business-ui';
export function BusinessEditor({title,busy,close,children}:{title:string;busy:boolean;close:()=>void;children:ReactNode}){
 const dialog=useRef<HTMLDialogElement>(null);
 useEffect(()=>{const element=dialog.current!,previous=document.activeElement as HTMLElement|null;element.showModal();element.querySelector<HTMLElement>('h2')?.focus();return()=>{element.close();previous?.focus();};},[]);
 return <dialog ref={dialog} className="business-editor" aria-label={title} onCancel={event=>{event.preventDefault();if(!busy)close();}}><div className="business-editor-header"><h2 tabIndex={-1}>{title}</h2><button className={secondary} disabled={busy} onClick={close} aria-label="편집창 닫기">닫기</button></div><div className="business-editor-body">{children}</div></dialog>;
}
