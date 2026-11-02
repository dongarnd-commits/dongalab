import {useEffect,useRef} from 'react';
import {Menu,PanelLeftClose,PanelLeftOpen} from 'lucide-react';
import './portal-menu.css';
type Props={collapsed:boolean;onCollapse:()=>void;mobileOpen:boolean;onMobile:(open:boolean)=>void};
export function PortalMenu({collapsed,onCollapse,mobileOpen,onMobile}:Props){
 const trigger=useRef<HTMLButtonElement>(null);
 useEffect(()=>{if(!mobileOpen)return;const target=trigger.current;const key=(e:KeyboardEvent)=>{if(e.key==='Escape'){e.preventDefault();onMobile(false);}};
  window.addEventListener('keydown',key);const timer=setTimeout(()=>document.querySelector<HTMLButtonElement>('#portal-side-nav nav button')?.focus(),0);
  return()=>{clearTimeout(timer);window.removeEventListener('keydown',key);target?.focus();};
 },[mobileOpen,onMobile]);
 return <><button type="button" className="portal-menu-desktop" aria-label={collapsed?'메뉴 펼치기':'메뉴 접기'} aria-expanded={!collapsed} aria-controls="portal-side-nav" onClick={onCollapse}>{collapsed?<PanelLeftOpen size={20}/>:<PanelLeftClose size={20}/>}</button><button ref={trigger} type="button" className="portal-menu-mobile" aria-label={mobileOpen?'메뉴 닫기':'메뉴 열기'} aria-expanded={mobileOpen} aria-controls="portal-side-nav" onClick={()=>onMobile(!mobileOpen)}><Menu size={20}/></button></>;
}
