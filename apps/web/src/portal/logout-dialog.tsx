import {useEffect,useId,useRef} from 'react';
import './portal-menu.css';
export function LogoutDialog({busy,onContinue,onDiscard,preview=false}:{busy:boolean;onContinue:()=>void;onDiscard:()=>void;preview?:boolean}){
 const dialog=useRef<HTMLDialogElement>(null),cancel=useRef<HTMLButtonElement>(null),title=useId();
 useEffect(()=>{const previous=document.activeElement,d=dialog.current;d?.showModal();cancel.current?.focus();return()=>{d?.close();if(previous instanceof HTMLElement&&previous.isConnected)previous.focus();};},[]);
 return <dialog ref={dialog} className="portal-confirm" aria-labelledby={title} onCancel={e=>{e.preventDefault();if(!busy)onContinue();}}><h2 id={title}>{preview?'반영하지 않은 미리보기 변경사항이 있습니다':'저장하지 않은 변경사항이 있습니다'}</h2><p>{preview?'계속 작성하거나 변경을 버리고 미리보기를 종료할 수 있습니다. 실제 서버 저장·전송·세션 폐기는 수행하지 않습니다.':'계속 작성하거나 변경을 버리고 로그아웃할 수 있습니다. 저장·제출·발송·승인은 자동으로 실행하지 않습니다.'}</p><div><button ref={cancel} type="button" disabled={busy} onClick={onContinue}>계속 작성</button><button type="button" className="portal-confirm-primary" disabled={busy} onClick={onDiscard}>{preview?'변경을 버리고 미리보기 종료':'변경을 버리고 로그아웃'}</button></div></dialog>;
}
