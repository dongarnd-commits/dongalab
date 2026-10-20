import type {PortalProps} from "../../portal/types";
// UI reproduction from the user-provided MagicPath DATCOV02 v0.2. Development preview only.
import React, { useEffect, useRef, useState } from 'react';
import { LayoutDashboard, Building2, ChartColumnIncreasing, ClipboardPenLine, Paperclip, ScanSearch, MessageSquareText, FileCheck2, Menu, X, ChevronRight, ChevronLeft, LogOut, UserRound, Files, UploadCloud, Check, ArrowRight, Layers3, FileText, FileSpreadsheet, Image as ImageIcon, LockKeyhole, ShieldCheck, RefreshCw, Trash2, Pencil, History, Plus, Info, CheckCircle2, Sparkles, Send, FileDown } from 'lucide-react';
import type {LucideIcon} from 'lucide-react';
type Screen = 'home' | 'onboarding' | 'extraction' | 'company' | 'finance' | 'needs' | 'files' | 'review' | 'requests' | 'proposals';
type CandidateKey = 'company' | 'reg' | 'industry' | 'address' | 'person' | 'revenue' | 'employees';
type Candidate = {
  key: CandidateKey;
  label: string;
  value: string;
  source: string;
  selected: boolean;
};
type Doc = {
  id: number;
  name: string;
  size: string;
  type: string;
  category: string;
  version: number;
  status: string;
  history: string[];
  file?: File;
  description: string;
  siteId: number | null;
  improvement: string;
  editing: boolean;
  savedInfo?: {category:string;description:string;siteId:number|null;improvement:string};
  siteRemoved?: boolean;
  origin: UploadStage;
  usedIn: UploadStage[];
};
type FieldData = {
  company: string;
  reg: string;
  industry: string;
  address: string;
  person: string;
  revenue: string;
  employees: string;
  site: string;
};
type Decision = '미확인' | '확인' | '수정 요청';
type UploadStage = 'onboarding'|'finance'|'needs'|'files';
const stageNames:Record<UploadStage,string>={onboarding:'기업정보 등록 시작',finance:'재무·사업이력',needs:'개선요구 등록',files:'첨부자료 관리'};
const categories=['사업자등록증','사업자등록증명원','사업장 기본정보 확인자료','재무제표','매출자료','정부지원사업 수행자료','재무자료','기업소개서','공정·현장자료','지원사업 이력','기타'];
const menu:Array<{head:string;items:Array<{id:Screen;name:string;icon:LucideIcon}>}>=[
 {head:'홈',items:[{id:'home',name:'기업 홈',icon:LayoutDashboard}]},
 {head:'1. 기업 등록',items:[{id:'onboarding',name:'기업정보 등록 시작',icon:UploadCloud},{id:'extraction',name:'추출정보 확인',icon:ScanSearch},{id:'company',name:'기업 · 사업장 관리',icon:Building2},{id:'finance',name:'재무 · 사업이력',icon:ChartColumnIncreasing}]},
 {head:'2. 개선요구',items:[{id:'needs',name:'개선요구 등록',icon:ClipboardPenLine}]},
 {head:'3. 관련자료',items:[{id:'files',name:'첨부자료 관리',icon:Paperclip}]},
 {head:'4. 분석·제출',items:[{id:'review',name:'분석 결과 확인',icon:Sparkles}]},
 {head:'5. 진행·제안',items:[{id:'requests',name:'보완 요청함',icon:MessageSquareText},{id:'proposals',name:'받은 제안서',icon:FileCheck2}]}];
const preset: FieldData = {
  company: '',
  reg: '',
  industry: '',
  address: '',
  person: '',
  revenue: '',
  employees: '',
  site: '제1사업장'
};
const B = 'inline-flex cursor-pointer items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-[12px] font-semibold transition-all focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-blue-100 disabled:cursor-not-allowed disabled:opacity-40';
const P = B + ' bg-[#1767C7] text-white hover:bg-[#1256AD]';
const S = B + ' border border-slate-200 bg-white text-slate-700 hover:bg-slate-50';
const I = 'w-full rounded-xl border border-[#DDE5EE] bg-white px-3.5 py-3 text-[13px] text-slate-800 outline-none placeholder:text-slate-400 focus:border-blue-400 focus:ring-4 focus:ring-blue-50';
function Chip({
  children,
  color = 'gray'
}: {
  children: React.ReactNode;
  color?: 'gray' | 'green' | 'blue' | 'amber' | 'violet';
}) {
  const C = {
    gray: 'bg-slate-100 text-slate-600',
    green: 'bg-emerald-50 text-emerald-700',
    blue: 'bg-blue-50 text-blue-700',
    amber: 'bg-amber-50 text-amber-700',
    violet: 'bg-violet-50 text-violet-700'
  };
  return <span className={'inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-semibold ' + C[color]}>{children}</span>;
}
function Card({
  children,
  className = ''
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={'rounded-[20px] border border-[#E8ECF2] bg-white shadow-[0_3px_18px_rgba(37,66,103,.035)] ' + className}>{children}</div>;
}
function Header({
  eyebrow,
  title,
  sub,
  children
}: {
  eyebrow: string;
  title: string;
  sub: string;
  children?: React.ReactNode;
}) {
  return <div className="mb-6 flex flex-wrap items-end justify-between gap-4"><div><div className="mb-2 text-[10px] font-bold tracking-[.17em] text-blue-600">{eyebrow}</div><h1 className="text-[26px] font-extrabold tracking-[-.035em] text-slate-900 md:text-[30px]">{title}</h1><p className="mt-2 text-[13px] leading-6 text-slate-500">{sub}</p></div>{children}</div>;
}
function Label({
  name,
  children,
  hint
}: {
  name: string;
  children: React.ReactNode;
  hint?: string;
}) {
  return <label className="block"><span className="mb-2 block text-[12px] font-semibold text-slate-700">{name}</span>{children}{hint && <p className="mt-1.5 text-[11px] leading-5 text-slate-400">{hint}</p>}</label>;
}
function FileIcon({
  name
}: {
  name: string;
}) {
  const x = name.split('.').pop()?.toLowerCase();
  const Icon = x === 'xlsx' || x === 'csv' ? FileSpreadsheet : ['jpg', 'jpeg', 'png'].includes(x || '') ? ImageIcon : FileText;
  return <div className={'grid h-11 w-11 shrink-0 place-items-center rounded-xl ' + (x === 'xlsx' || x === 'csv' ? 'bg-green-50 text-green-600' : 'bg-blue-50 text-[#1767C7]')}><Icon size={21} /></div>;
}
function Sep() {
  return <div className="h-px bg-slate-100" />;
}
function IntakeFiles({disabled=false,stage,documents,onFiles,onReference,onManage,onReview}:{disabled?:boolean;stage:'onboarding'|'finance';documents:Doc[];onFiles:(files:FileList|null,category:string)=>void;onReference:(id:number)=>void;onManage:()=>void;onReview:()=>void}){
 const types=stage==='onboarding'?categories.slice(0,3):categories.slice(3,6);
 const [category,setCategory]=useState(types[0]);const [drag,setDrag]=useState(false);const depth=useRef(0);const picker=useRef<HTMLInputElement>(null);
 return <div className="mt-4 space-y-4" data-intake={stage}>
  <Label name="등록 자료 유형"><select aria-label="등록 자료 유형" className={I} value={category} onChange={e=>setCategory(e.target.value)}>{types.map(x=><option key={x}>{x}</option>)}</select></Label>
  <div data-intake-dropzone data-dragging={drag} onDragEnter={e=>{e.preventDefault();depth.current++;setDrag(true);}} onDragOver={e=>{e.preventDefault();e.dataTransfer.dropEffect='copy';}} onDragLeave={e=>{e.preventDefault();if(--depth.current<=0){depth.current=0;setDrag(false);}}} onDrop={e=>{e.preventDefault();depth.current=0;setDrag(false);onFiles(e.dataTransfer.files,category);}} className={'rounded-2xl border-2 border-dashed p-5 text-center '+(drag?'border-blue-600 bg-blue-100':'border-blue-200 bg-blue-50/30')}>
   <p className="text-[12px] font-bold">{stage==='onboarding'?'기업·사업장 기본정보 확인자료':'재무·정부사업 자료로 가져오기'}</p><p className="mt-2 text-[11px] leading-6 text-slate-500">선택한 자료 유형으로 등록합니다. 문서 내용은 검증하지 않습니다.<br/>파일 선택 또는 드래그 앤 드롭 · 파일당 15MB 이하</p>
   <input disabled={disabled} ref={picker} type="file" multiple accept=".txt,.csv,.json,.pdf,.docx,.xlsx,.jpg,.jpeg,.png" className="hidden" onChange={e=>{onFiles(e.target.files,category);e.target.value='';}}/><button disabled={disabled} className={P+' mt-3'} onClick={()=>picker.current?.click()}>서류 선택 <UploadCloud size={15}/></button>
  </div>
  <p role="note" className="rounded-xl bg-amber-50 p-3 text-[12px] leading-6 text-amber-800">파싱 미연결 · 실제 추출 후보는 생성하지 않습니다. 등록 자료를 확인한 뒤 직접 입력해 주세요. 파일은 공통 자료함에서 함께 관리합니다.</p>
  <div className="flex flex-wrap gap-2"><button className={S} onClick={onReview}>{stage==='onboarding'?'추출정보 확인':'추출·입력내용 검토'}</button><button className={S} onClick={onManage}>공통 자료함 열기</button></div>
  <details className="rounded-xl border border-slate-200 p-3 text-[12px]"><summary className="cursor-pointer font-semibold">기존 자료 참조 (중복 업로드 없이 연결)</summary><div className="mt-3 space-y-2">{documents.length?documents.map(d=><div key={d.id} className="flex flex-wrap items-center justify-between gap-2"><span className="break-all">{d.name} · {d.category}</span><button className={S} disabled={d.usedIn.includes(stage)} onClick={()=>onReference(d.id)}>{d.usedIn.includes(stage)?'이 단계에서 참조 중':'이 단계에서 참조'}</button></div>):<p>참조할 자료가 없습니다.</p>}</div></details>
  {documents.some(d=>d.usedIn.includes(stage))&&<ul className="space-y-1 text-[12px] text-slate-600">{documents.filter(d=>d.usedIn.includes(stage)).map(d=><li key={d.id}>{d.name} · {d.category} · 파싱 미연결</li>)}</ul>}
 </div>;
}
export const DATCOV02 = ({session,onLogout}:PortalProps) => {
  const authenticated=!!session;
  const [loggedIn, setLoggedIn] = useState(() => authenticated || new URLSearchParams(window.location.search).get('screen') !== null && new URLSearchParams(window.location.search).get('screen') !== 'login');
  const [loginId, setLoginId] = useState('');
  const [password, setPassword] = useState('');
  const [loginErr, setLoginErr] = useState('');
  const [page, setPage] = useState<Screen>(() => {const p=new URLSearchParams(window.location.search).get('screen');return menu.flatMap(g=>g.items).some(x=>x.id===p)?p as Screen:'home';});
  const [mobileMenu, setMobileMenu] = useState(false);
  const [data, setData] = useState<FieldData>(preset);
  const [sites, setSites] = useState(authenticated?[]:[{id:1,name:preset.site,address:'',person:'',open:true}]);
  const [historyStatus, setHistoryStatus] = useState<'yes'|'none'|'unknown'>('unknown');
  const [projects, setProjects] = useState<Array<{id:number;name:string;period:string;agency:string;details:string;evidence:string}>>([]);
  const [financeReview,setFinanceReview]=useState(false);
  const [financeSaved,setFinanceSaved]=useState(false);
  const [inputChecked,setInputChecked]=useState(false);
  const [fileReturn,setFileReturn]=useState<Screen|null>(null);
  const [typeFilter,setTypeFilter]=useState('');
  const [stageFilter,setStageFilter]=useState('');
  const [fileQuery,setFileQuery]=useState('');
  const [financeYear, setFinanceYear] = useState(authenticated?'':'2025');
  const [saved, setSaved] = useState(false);
  const [problem, setProblem] = useState(authenticated?'':'재고 수량이 실제 수량과 다르고 입출고를 수기로 처리합니다. 생산실적과 불량 발생 현황을 체계적으로 관리하고 싶습니다.');
  const [goal, setGoal] = useState(authenticated?'':'재고·입출고 현황과 생산실적·품질정보를 통합적으로 확인하고 관리하고 싶습니다.');
  const [limits, setLimits] = useState(authenticated?'':'기존 ERP 연동 가능 여부와 현장 데이터 수집 방식 확인이 필요합니다.');
  const [needSaved, setNeedSaved] = useState(false);
  const [documents, setDocuments] = useState<Doc[]>([]);
  const [dragging, setDragging] = useState(false);
  const dragDepth = useRef(0);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [candidateSource,setCandidateSource] = useState('');
  const [changing, setChanging] = useState<number | null>(null);
  const [audit, setAudit] = useState<string[]>([]);
  const [busy] = useState(false);
  const [requestSent] = useState(false);
  const [decision] = useState<Decision>('미확인');
  const [opinion, setOpinion] = useState('');
  const [proposalTab, setProposalTab] = useState<'overview' | 'solution' | 'notice' | 'response'>('overview');
  const [proposalOpen, setProposalOpen] = useState(false);
  const [toaster, setToaster] = useState('');
  const [confirm, setConfirm] = useState(false);
  const upload = useRef<HTMLInputElement>(null);
  const replace = useRef<HTMLInputElement>(null);
  const scroller = useRef<HTMLElement>(null);
  const notify = (s: string) => setToaster(s);
  const goto = (p: Screen) => {
    if(p==='files'){setFileReturn(null);setTypeFilter('');setStageFilter('');setFileQuery('');}
    setPage(p);
    const u=new URL(window.location.href);u.searchParams.set('screen',p);window.history.pushState({},'',u);
    setMobileMenu(false);
    setToaster('');
    scroller.current?.scrollTo(0, 0);
  };
  const openFiles=(from:Screen)=>{goto('files');setFileReturn(from);};
  const referenceFile=(id:number,stage:UploadStage)=>{setDocuments(a=>a.map(d=>d.id===id?{...d,usedIn:Array.from(new Set([...d.usedIn,stage]))}:d));notify('기존 파일을 이 단계에서 참조합니다. 중복 파일이나 실제 서버 연결은 생성하지 않았습니다.');};
  const update = (k: keyof FieldData, val: string) => {
    setData(x => ({
      ...x,
      [k]: val
    }));
    setSaved(false);
  };
  const logout = () => {
    if(authenticated){onLogout?.();return;}
    setLoggedIn(false);
    setPassword('');
    setLoginErr('');
    setToaster('');
    setPage('home');
    const u=new URL(window.location.href);u.searchParams.set('screen','login');window.history.pushState({},'',u);
  };
  useEffect(()=>{const back=()=>{const p=new URLSearchParams(window.location.search).get('screen');setLoggedIn(authenticated||(!!p&&p!=='login'));if(menu.flatMap(g=>g.items).some(x=>x.id===p))setPage(p as Screen);setMobileMenu(false);};window.addEventListener('popstate',back);return()=>window.removeEventListener('popstate',back);},[authenticated]);
  const doLogin=(ev:React.FormEvent)=>{ev.preventDefault();setPassword('');setLoginErr('');setLoggedIn(true);goto('home');};
  const receive=async(fileList:FileList|File[]|null,toReplace:number|null=null,origin:UploadStage='files',category='기타')=>{
    if(authenticated){notify('자료 업로드 미연결: 실제 파일을 전송하지 않았습니다.');return;}
    if(!fileList?.length)return;
    const errors:string[]=[];
    if(fileList.length>5)errors.push('한 번에 최대 5개 파일만 추가할 수 있습니다. 나머지는 다시 선택해 주세요.');
    for(const [j,f] of Array.from(fileList).slice(0,5).entries()){
      if(!/\.(txt|csv|json|pdf|docx|xlsx|jpg|jpeg|png)$/i.test(f.name)){errors.push(f.name+': 지원하지 않는 파일 형식입니다.');continue;}
      if(f.size>15*1024*1024){errors.push(f.name+': 파일당 15MB 이하만 선택할 수 있습니다.');continue;}
      const old=toReplace!==null&&j===0?documents[toReplace]:undefined;
      const item:Doc={id:old?.id??Date.now()+j,name:f.name,size:(f.size/1024).toFixed(1)+' KB',type:f.type,category:old?.category??category,version:(old?.version??0)+1,status:'미리보기 · 미업로드',history:old?[...old.history,old.name+' · 미리보기']:[],file:f,description:old?.description??'',siteId:old?.siteId??null,improvement:old?.improvement??'',editing:old?.editing??true,savedInfo:old?.savedInfo,siteRemoved:old?.siteRemoved,origin:old?.origin??origin,usedIn:old?.usedIn??[origin]};
      setDocuments(prev=>old?prev.map((v,k)=>k===toReplace?item:v):[...prev,item]);
      if(!old&&origin==='onboarding')setCandidateSource(f.name+' · 파싱 미연결');
      setAudit(a=>['미리보기 목록 변경: '+f.name,...a]);
    }
    notify(errors.length?errors.join(' '):'파일명·크기 미리보기만 표시합니다. 업로드·파싱·서버 저장은 다음 단계에서 연결합니다.');
  };
  const infoOf=(doc:Doc)=>({category:doc.category,description:doc.description,siteId:doc.siteId,improvement:doc.improvement});
  const isDirty=(doc:Doc)=>!doc.savedInfo||JSON.stringify(infoOf(doc))!==JSON.stringify(doc.savedInfo);
  const removeSite=(id:number)=>{
    if(!window.confirm('이 사업장 입력 카드를 미리보기에서 삭제할까요? 연결된 자료는 사업장을 다시 선택해야 합니다. 실제 DB는 변경하지 않습니다.'))return;
    setSites(a=>a.filter(x=>x.id!==id));
    setDocuments(a=>a.map(x=>x.siteId===id||x.savedInfo?.siteId===id?{...x,siteId:x.siteId===id?null:x.siteId,savedInfo:x.savedInfo?{...x.savedInfo,siteId:x.savedInfo.siteId===id?null:x.savedInfo.siteId}:undefined,siteRemoved:true}:x));
  };
  const saveDocumentInfo=(id:number)=>{
    setDocuments(a=>a.map(x=>x.id===id?{...x,savedInfo:infoOf(x),siteRemoved:x.siteRemoved&&x.siteId===null}:x));
    notify('자료정보를 현재 UI 미리보기 세션에 반영했습니다. PostgreSQL·서버 저장은 수행하지 않았습니다.');
  };
  const onUpload = async (ev: React.ChangeEvent<HTMLInputElement>) => {
    await receive(ev.target.files,null,fileReturn==='onboarding'||fileReturn==='finance'||fileReturn==='needs'?fileReturn:'files');
    ev.target.value = '';
  };
  const onReplace = async (ev: React.ChangeEvent<HTMLInputElement>) => {
    await receive(ev.target.files, changing);
    ev.target.value = '';
    setChanging(null);
  };
  const applyCandidates = () => {
    setData(d => {
      let next = {
        ...d
      };
      for (const c of candidates.filter(x => x.selected)) {
        next = {
          ...next,
          [c.key]: c.value
        };
      }
      return next;
    });
    setSaved(false);
    goto('company');
    notify('미리보기 입력란에만 반영했습니다. 실제 DB 저장·Fact 확정은 연결되지 않았습니다.');
  };
  const downloadText = (name: string, text: string) => {
    const blob = new Blob(['\ufeff' + text], {
      type: 'text/plain;charset=utf-8'
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = name;
    a.click();
    URL.revokeObjectURL(url);
  };
  const progress=[saved&&financeSaved,needSaved,documents.some(d=>d.savedInfo),inputChecked,false];
  const visibleDocs=documents.filter(d=>(!typeFilter||d.category===typeFilter)&&(!stageFilter||d.origin===stageFilter)&&(!fileQuery||(d.name+' '+d.description+' '+(d.savedInfo?.description??'')).toLowerCase().includes(fileQuery.toLowerCase())));
  const problems=authenticated?[]:[{title:'재고관리',desc:'미리보기 예시: 수량 불일치 및 현황 확인'},{title:'입출고 관리',desc:'미리보기 예시: 기록·흐름 관리'},{title:'생산실적',desc:'미리보기 예시: 현황 수집·추적'},{title:'품질관리',desc:'미리보기 예시: 불량정보 관리'}];
  if (!loggedIn) return <div className="flex h-[900px] min-h-[680px] w-full bg-[#F7F9FD] text-slate-800" style={{
    fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, Segoe UI, Noto Sans KR, sans-serif'
  }}>
  <div className="hidden w-[48%] flex-col justify-between overflow-hidden bg-[#113967] p-12 text-white lg:flex">
   <div className="flex items-center gap-3"><div className="grid h-11 w-11 place-items-center rounded-xl bg-white/20"><Layers3 size={23} /></div><div><b className="text-xl">DATCO ONE</b><p className="text-[11px] tracking-[.07em] text-blue-200">정부지원사업 운영관리</p></div></div>
   <div><p className="mb-5 text-[11px] font-semibold tracking-[.2em] text-blue-200">DATCO BUSINESS PLATFORM</p><h1 className="text-[39px] font-extrabold leading-[1.4] tracking-[-.05em]">기업의 가능성을<br />실질적인 성장으로<br />연결합니다.</h1><p className="mt-6 max-w-[390px] text-[14px] leading-8 text-blue-100/90">기업정보 등록부터 개선과제 분석, DATCO 솔루션 검토, 정부지원사업과 맞춤형 제안서까지.</p></div><p className="text-[11px] text-blue-200/80">DATCO · Business Portal</p>
  </div>
  <div className="flex flex-1 items-center justify-center px-5 py-10"><form onSubmit={doLogin} className="w-full max-w-[435px] rounded-[25px] border border-slate-100 bg-white p-8 shadow-[0_15px_65px_rgba(32,58,91,.07)] md:p-10">
   <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-blue-50 text-[#1767C7]"><LockKeyhole size={23} /></div><h2 className="text-[27px] font-extrabold text-slate-900">DATCO ONE 로그인</h2><p className="mt-2 text-[13px] text-slate-500">계정에 따라 수요기업·DATCO 운영자·관리자 업무화면으로 연결되는 공통 로그인입니다.</p>
   <div className="mt-8 space-y-4"><Label name="아이디"><input disabled={authenticated} className={I} value={loginId} onChange={e => setLoginId(e.target.value)} autoComplete="username" placeholder="아이디 또는 이메일" /></Label><Label name="비밀번호"><input disabled={authenticated} className={I} type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password" placeholder="비밀번호를 입력해 주세요" /></Label></div>
   {loginErr && <p className="mt-3 text-[12px] text-rose-600" role="alert">{loginErr}</p>}
   <button disabled={authenticated} type="submit" className={P + ' mt-7 w-full py-3.5'}>미리보기 시작 <ArrowRight size={16} /></button>
   <div className="mt-6 rounded-xl bg-slate-50 p-4 text-[11px] leading-6 text-slate-500"><p className="mb-1 font-semibold text-slate-700">개발 전용 화면 미리보기</p><p>실제 계정을 입력하지 마세요.</p><p>인증·권한·세션을 생성하지 않습니다.</p><p className="mt-2 text-slate-400">로그인 버튼은 수요기업 홈 미리보기로만 이동합니다.</p></div>
  </form></div>
 </div>;
  return <div className="flex h-[900px] min-h-[690px] w-full overflow-hidden bg-[#F7F9FC] text-slate-800" style={{
    fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, Segoe UI, Noto Sans KR, sans-serif'
  }}>
  {mobileMenu && <div className="fixed inset-0 z-40 bg-slate-900/40 lg:hidden" onClick={() => setMobileMenu(false)} />}
  <aside className={'fixed inset-y-0 left-0 z-50 flex w-[254px] shrink-0 flex-col border-r border-slate-200 bg-white transition-transform lg:static lg:translate-x-0 ' + (mobileMenu ? 'translate-x-0' : '-translate-x-full')}>
   <div className="flex h-[75px] items-center gap-3 border-b border-slate-100 px-5"><div className="grid h-9 w-9 place-items-center rounded-xl bg-[#1767C7] text-white"><Layers3 size={19} /></div><div><b className="text-[17px] tracking-tight">DATCO <span className="text-[#1767C7]">ONE</span></b><p className="text-[10px] text-slate-400">정부지원사업 운영관리</p></div><button className="ml-auto lg:hidden" onClick={() => setMobileMenu(false)} aria-label="메뉴 닫기"><X size={20} /></button></div>
   <div className="min-h-0 flex-1 overflow-y-auto px-3 py-5">{menu.map(g => <div key={g.head} className="mb-6"><p className="mb-2 px-3 text-[10px] font-bold tracking-[.12em] text-slate-400">{g.head}</p>{g.items.map(x => <button key={x.id} onClick={() => goto(x.id)} className={'my-0.5 flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-[12px] font-semibold transition-colors ' + (page === x.id ? 'bg-[#EAF3FF] text-[#1465BF]' : 'text-slate-600 hover:bg-slate-50')}><x.icon size={18} /><span className="flex-1">{x.name}</span>{page === x.id && <span className="h-1.5 w-1.5 rounded-full bg-blue-600" />}{x.id === 'requests' && !authenticated && !requestSent && <span className="rounded-full bg-amber-100 px-2 text-[10px] text-amber-700">1</span>}</button>)}</div>)}</div>
   <div className="m-3 rounded-xl border border-slate-100 bg-[#F7F9FC] p-4"><div className="flex items-center gap-2"><ShieldCheck className="text-[#1767C7]" size={17} /><span className="text-[12px] font-semibold">기업정보 보호</span></div><p className="mt-2 text-[11px] leading-6 text-slate-500">문서 추출 후보와 확정된 기업정보를 구분합니다.</p></div>
   <div className="flex items-center gap-3 border-t border-slate-100 px-5 py-4"><div className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-blue-50 text-blue-600"><UserRound size={18} /></div><div className="min-w-0 flex-1"><p title={session?.name} className="truncate text-[12px] font-bold">{session?.name??"수요기업 사용자"}</p><p className="truncate text-[11px] text-slate-400">{session?.role??"회사 담당자"}</p></div><button onClick={logout} className="rounded-lg p-2 text-slate-500 hover:bg-rose-50 hover:text-rose-600" title="로그아웃" aria-label="로그아웃"><LogOut size={19} /></button></div>
  </aside>
  <div className="flex min-w-0 flex-1 flex-col">
   <header className="flex h-[75px] shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4 md:px-8"><div className="flex items-center gap-3"><button className="rounded-lg p-2 text-slate-500 lg:hidden" onClick={() => setMobileMenu(true)} aria-label="메뉴 열기"><Menu size={20} /></button><span className="hidden text-[12px] text-slate-400 sm:block">수요기업 포털</span><ChevronRight size={15} className="hidden text-slate-300 sm:block" /><span className="text-[13px] font-bold">{menu.flatMap(x => x.items).find(x => x.id === page)?.name}</span></div><div className="flex items-center gap-3"><Chip color="blue">{authenticated?<span className="block max-w-[160px] truncate" title={session.name}>{session.name}</span>:data.company || '기업정보 입력 중'}</Chip><div className="grid h-8 w-8 place-items-center rounded-full bg-[#EAF3FF] text-[12px] font-bold text-[#1767C7]">기</div><button onClick={logout} className={S + ' hidden sm:inline-flex'}><LogOut size={15} /> 로그아웃</button></div></header>
   <main ref={scroller} className="min-h-0 flex-1 overflow-y-auto"><div className="mx-auto max-w-[1190px] px-4 pb-14 pt-7 md:px-8">
    {authenticated&&<p role="note" className="mb-5 rounded-xl bg-blue-50 p-4 text-sm">인증된 기업 포털 · 업무 데이터 연결 후 표시됩니다. 입력·업로드·저장·분석·제출·승인은 아직 연결되지 않았습니다. <button className="underline" onClick={()=>window.location.assign(new URL("/",window.location.href).href)}>기존 업무 화면 열기</button></p>}
    {toaster && <div role="status" className="mb-5 flex items-center justify-between gap-3 rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-[12px] text-blue-800"><div className="flex items-center gap-2"><Info size={16} /><span>{toaster}</span></div><button onClick={() => setToaster('')} aria-label="알림 닫기"><X size={16} /></button></div>}


    {page === 'home' && <>
     <Header eyebrow="COMPANY DASHBOARD" title="기업 홈" sub="우리 기업의 업무 진행 현황과 다음 할 일을 확인하세요." />

     <Card className="p-6"><div className="mb-4 flex items-center justify-between"><h3 className="text-[15px] font-bold">업무 진행 단계</h3><span className="text-[12px] font-semibold text-blue-600">{authenticated?"—":progress.filter(Boolean).length+" / 5"}</span></div><div className="mb-5 h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-blue-600" style={{
                  width: progress.filter(Boolean).length * 20 + '%'
                }} /></div><div aria-label="5단계 업무 진행" className="grid gap-2 sm:grid-cols-5">{[{
                  t: '기업 등록',
                  s: 'onboarding'
                }, {
                  t: '개선요구 작성',
                  s: 'needs'
                }, {
                  t: '관련자료 제출',
                  s: 'files'
                }, {
                  t: '분석·입력내용 확인',
                  s: 'review'
                }, {
                  t: '결과·제안서 확인',
                  s: 'proposals'
                }].map((x, i) => <button key={x.t} onClick={() => goto(x.s as Screen)} className="flex items-center gap-2 rounded-xl bg-slate-50 px-3 py-4 text-left hover:bg-blue-50 sm:flex-col sm:items-start"><span className={'grid h-7 w-7 shrink-0 place-items-center rounded-full text-[11px] font-bold ' + (progress[i] ? 'bg-emerald-100 text-emerald-700' : 'bg-white text-slate-500')}>{progress[i] ? <Check size={15} /> : i + 1}</span><span className="text-[11px] font-semibold">{x.t}</span></button>)}</div></Card>
     <p className="mt-3 text-[11px] text-amber-700">{authenticated?"업무 데이터가 미연결되어 진행 상태를 표시하지 않습니다.":"진행 표시는 미리보기 세션 기준입니다. 실제 저장·분석·전송 완료를 의미하지 않습니다."}</p>
     <div className="mt-5 grid gap-4 lg:grid-cols-2"><Card className="p-6"><h3 className="mb-4 text-[15px] font-bold">자주 사용하는 업무</h3><div className="grid gap-3 sm:grid-cols-2">{[{
                    t: '기업정보 관리',
                    d: '기본정보·사업장·재무',
                    i: Building2,
                    s: 'company'
                  }, {
                    t: '개선요구 작성',
                    d: '문제점·목표 입력',
                    i: ClipboardPenLine,
                    s: 'needs'
                  }, {
                    t: '증빙자료 관리',
                    d: '첨부·교체·이력',
                    i: Files,
                    s: 'files'
                  }, {
                    t: '제안서 확인',
                    d: '열람·수정 요청·확인',
                    i: FileCheck2,
                    s: 'proposals'
                  }].map(x => <button key={x.s} onClick={() => goto(x.s as Screen)} className="flex gap-3 rounded-xl border border-slate-100 p-4 text-left hover:border-blue-200 hover:bg-blue-50/20"><div className="grid h-9 w-9 place-items-center rounded-lg bg-blue-50 text-blue-600"><x.i size={18} /></div><div><p className="text-[12px] font-bold">{x.t}</p><p className="mt-1 text-[11px] text-slate-400">{x.d}</p></div></button>)}</div></Card><Card className="p-6"><h3 className="mb-4 text-[15px] font-bold">확인할 업무</h3>{[{
                  t: '보완자료 요청 확인',
                  d: '추가 자료 제출 및 답변',
                  s: 'requests'
                }, {
                  t: '기업정보 문서 추출',
                  d: '문서 선택 후 입력값 검토',
                  s: 'onboarding'
                }, {
                  t: '도착한 제안서',
                  d: '서비스·지원사업 검토 내용',
                  s: 'proposals'
                }].map(x => <button key={x.t} onClick={() => goto(x.s as Screen)} className="flex w-full items-center justify-between gap-3 border-b border-slate-100 py-4 text-left last:border-0"><div><p className="text-[12px] font-bold">{x.t}</p><p className="mt-1 text-[11px] text-slate-500">{x.d}</p></div><ChevronRight size={17} className="text-slate-400" /></button>)}</Card></div>
    </>}


    {page === 'onboarding' && <>
     <Header eyebrow="COMPANY ONBOARDING / 01" title="기업정보 등록" sub="보유 서류에서 정보를 가져오거나 필요한 정보를 직접 작성할 수 있습니다." />
     <div className="grid gap-5 lg:grid-cols-2"><Card className="p-6 md:p-8"><div className="grid h-12 w-12 place-items-center rounded-xl bg-blue-50 text-blue-600"><UploadCloud size={25} /></div><h2 className="mt-4 text-[18px] font-bold">서류로 기업정보 가져오기</h2><p className="mt-3 min-h-[65px] text-[13px] leading-7 text-slate-500">사업자등록증·사업자등록증명원 등 기업·사업장 기본정보 확인자료를 등록합니다. 현재 미리보기는 문서 내용을 추출하지 않습니다.</p><IntakeFiles disabled={authenticated} stage="onboarding" documents={documents} onFiles={(files,category)=>{void receive(files,null,'onboarding',category);}} onReference={id=>referenceFile(id,'onboarding')} onManage={()=>openFiles('onboarding')} onReview={()=>goto('extraction')}/></Card>
      <Card className="p-6 md:p-8"><div className="grid h-12 w-12 place-items-center rounded-xl bg-slate-100 text-slate-600"><Pencil size={24} /></div><h2 className="mt-4 text-[18px] font-bold">기업정보 직접 입력</h2><p className="mt-3 min-h-[65px] text-[13px] leading-7 text-slate-500">첨부자료가 없거나 추출할 수 없는 항목이 있다면 직접 입력하거나 누락된 내용을 보완할 수 있습니다.</p><div className="mt-3 space-y-4 rounded-xl bg-slate-50 p-5">{['기업명·사업자등록정보', '사업장·담당자·업종', '재무정보 및 지원사업 이력'].map(x => <div key={x} className="flex items-center gap-2 text-[12px] text-slate-600"><CheckCircle2 size={16} className="text-blue-600" />{x}</div>)}</div><button onClick={() => goto('company')} className={S + ' mt-5'}>직접 작성 <ArrowRight size={15} /></button></Card></div>
      <div className="mt-5 flex items-start gap-3 rounded-2xl border border-blue-100 bg-blue-50 p-5 text-[12px] leading-6 text-blue-800"><Info size={17} className="mt-1 shrink-0" />서류 추출값은 저장된 확정 정보가 아니라 후보입니다. 사용자가 검토·수정한 이후 기업정보에 반영합니다.</div>
    </>}


    {page === 'extraction' && <>
     <Header eyebrow="EXTRACTION / 02" title="추출된 기업정보 확인" sub="원본에서 가져온 정보의 값과 출처를 확인하고 기업정보 입력란에 반영하세요."><Chip color="blue">{candidates.length}개 후보</Chip></Header>
     <div className="grid gap-5 lg:grid-cols-[.85fr_1.55fr]"><Card className="p-6"><h3 className="text-[14px] font-bold">추출 원본</h3><div className="mt-4 flex gap-3 rounded-xl bg-slate-50 p-4"><FileIcon name={candidateSource || 'info.txt'} /><div><p className="break-all text-[12px] font-semibold">{candidateSource || '등록된 추출 원본이 없습니다.'}</p><p className="mt-1 text-[11px] text-slate-400">등록 자료 · 파싱 미연결</p></div></div><div className="mt-5 rounded-xl bg-amber-50 p-4 text-[12px] leading-6 text-amber-800">추출값을 적용해도 DATCO의 최종 Fact 확정이 자동으로 이루어지는 것은 아닙니다.</div><button onClick={() => goto('onboarding')} className={S + ' mt-5 w-full'}><ChevronLeft size={15} /> 다른 서류 선택</button></Card>
     <Card className="p-6"><div className="mb-4 flex items-center justify-between"><h3 className="text-[14px] font-bold">항목별 정보 검토</h3><Chip color="amber">사용자 확인 필요</Chip></div>{candidates.length === 0 ? <div className="rounded-xl bg-slate-50 px-5 py-10 text-center"><p className="text-[13px] text-slate-500">추출된 항목이 없습니다.</p><button className={S + ' mt-3'} onClick={() => goto('company')}>직접 정보 입력</button></div> : <div className="space-y-3">{candidates.map((x, i) => <div key={x.key} className="flex gap-3 rounded-xl border border-slate-100 p-4"><input disabled={authenticated} type="checkbox" aria-label={x.label + ' 적용'} checked={x.selected} onChange={e => setCandidates(a => a.map((v, j) => j === i ? {
                      ...v,
                      selected: e.target.checked
                    } : v))} className="mt-8 h-4 w-4 accent-blue-600" /><div className="min-w-0 flex-1"><Label name={x.label}><input disabled={authenticated} className={I} value={x.value} onChange={e => setCandidates(a => a.map((v, j) => j === i ? {
                          ...v,
                          value: e.target.value
                        } : v))} /></Label><p className="mt-2 text-[11px] text-slate-400">출처: {x.source}</p></div></div>)}</div>}<div className="mt-6 flex flex-wrap justify-end gap-2"><button className={S} onClick={() => goto('company')}>직접 입력</button><button className={P} disabled={authenticated || (!candidates.length)} onClick={applyCandidates}><Check size={15} /> 선택한 정보 적용</button></div></Card></div>
    </>}


    {page === 'company' && <>
     <Header eyebrow="COMPANY / 03" title="기업 · 사업장 관리" sub="문서에서 가져온 값을 수정하거나 직접 정보를 작성할 수 있습니다."><Chip color={saved ? 'green' : 'amber'}>{saved ? '미리보기 보관 · 서버 미저장' : '확인·저장 필요'}</Chip></Header>
     <Card className="mb-5 flex flex-wrap items-center justify-between gap-3 p-4"><div className="flex items-center gap-2 text-[12px] text-slate-600"><Info size={18} className="text-blue-600" />서류에서 추출한 입력 후보를 가져올 수 있습니다.</div><button className={S} onClick={() => goto('onboarding')}><UploadCloud size={15} /> 문서에서 다시 가져오기</button></Card>
     <Card className="p-5 md:p-7"><h3 className="mb-5 text-[16px] font-bold">기업 기본정보</h3><div className="grid gap-5 sm:grid-cols-2">{[{
                  key: 'company',
                  label: '기업명'
                }, {
                  key: 'reg',
                  label: '사업자등록번호'
                }, {
                  key: 'industry',
                  label: '업종'
                }, {
                  key: 'person',
                  label: '담당자'
                }].map(f => <Label key={f.key} name={f.label}><input disabled={authenticated} className={I} placeholder={f.label + ' 입력'} value={data[f.key as keyof FieldData]} onChange={e => update(f.key as keyof FieldData, e.target.value)} /></Label>)}</div><div className="mt-7 flex justify-end gap-2"><button disabled={authenticated} className={P} onClick={() => {
                  if (!data.company.trim()) {
                    notify('기업명을 입력해 주세요.');
                    return;
                  }
                  setSaved(true);notify('미리보기 입력값을 현재 세션에 보관했습니다. 실제 서버 저장은 미연결입니다.');
                }}><Check size={15} /> 기업정보 저장</button><button className={S} onClick={() => goto('finance')}>재무정보 이동 <ArrowRight size={15} /></button></div></Card>
<Card className="mt-5 p-6"><div className="flex flex-wrap items-center justify-between gap-3"><h3 className="text-[16px] font-bold">사업장 목록</h3><button disabled={authenticated} className={P} onClick={()=>setSites(a=>[...a,{id:Date.now(),name:'',address:'',person:'',open:true}])}><Plus size={15}/> 사업장 추가</button></div><p className="mt-3 text-[12px] text-slate-500">미리보기 입력 · 현재 화면 세션에서만 유지되며 실제 DB에 저장되지 않습니다.</p><div className="mt-5 space-y-4">{sites.map((site,i)=><section key={site.id} aria-label={'사업장 '+(i+1)} className="rounded-xl border border-slate-200 p-4"><div className="flex flex-wrap items-center justify-between gap-3"><h4 className="text-[14px] font-bold">사업장 {i+1} — {site.name||'이름 입력 필요'}</h4><button disabled={authenticated} className={S} onClick={()=>removeSite(site.id)}><Trash2 size={15}/> 사업장 삭제</button><button disabled={authenticated} className={S} aria-expanded={site.open} onClick={()=>setSites(a=>a.map(x=>x.id===site.id?{...x,open:!x.open}:x))}>{site.open?'접기':'수정 · 펼치기'}</button></div>{site.open&&<div className="mt-4 grid gap-4 sm:grid-cols-2">{([{key:'name',label:'사업장명'},{key:'address',label:'사업장 소재지'},{key:'person',label:'사업장 담당자'}] as const).map(f=><Label key={f.key} name={f.label}><input disabled={authenticated} className={I} value={site[f.key]} onChange={e=>setSites(a=>a.map(x=>x.id===site.id?{...x,[f.key]:e.target.value}:x))}/></Label>)}</div>}</section>)}</div></Card>    </>}


    {page === 'finance' && <>
     <Header eyebrow="FINANCE / 04" title="재무 · 사업이력" sub="연도와 단위를 구분해 재무정보 및 기존 지원사업 수행이력을 관리합니다." />
     <div className="mb-5 grid gap-5 lg:grid-cols-2"><Card className="p-6"><h2 className="text-[18px] font-bold">재무·정부사업 자료로 가져오기</h2><IntakeFiles disabled={authenticated} stage="finance" documents={documents} onFiles={(files,category)=>{void receive(files,null,'finance',category);}} onReference={id=>referenceFile(id,'finance')} onManage={()=>openFiles('finance')} onReview={()=>setFinanceReview(true)}/></Card><Card className="p-6"><h2 className="text-[18px] font-bold">직접 입력</h2><p className="mt-3 text-[13px] leading-7 text-slate-500">자료가 없거나 파싱이 미연결된 항목은 아래 재무정보와 수행이력에 직접 입력하세요.</p><button disabled={authenticated} className={S+' mt-4'} onClick={()=>document.getElementById('finance-direct')?.scrollIntoView({block:'start'})}>직접 입력으로 이동</button></Card></div>
     {financeReview&&<Card className="mb-5 p-5"><h3 className="text-[15px] font-bold">재무 자료 추출·입력내용 검토</h3><p className="mt-3 text-[12px] leading-6 text-amber-800">파싱 미연결 · 추출 후보가 없습니다. 자동 입력·후보 적용은 수행하지 않았습니다.</p><ul className="mt-3 text-[12px]">{documents.filter(d=>d.usedIn.includes('finance')).map(d=><li key={d.id}>{d.name} · {d.category}</li>)}</ul><button className={P+' mt-4'} disabled={authenticated || (true)}>추출 후보 적용 (파싱 미연결)</button><button disabled={authenticated} className={S+' ml-2 mt-4'} onClick={()=>document.getElementById('finance-direct')?.scrollIntoView({block:'start'})}>직접 입력폼 확인</button></Card>}
     <div id="finance-direct"/>
     <Card className="p-6"><h3 className="mb-5 text-[15px] font-bold">재무정보</h3><div className="grid gap-4 sm:grid-cols-3"><Label name="기준 연도"><select disabled={authenticated} className={I} value={financeYear} onChange={e=>setFinanceYear(e.target.value)}><option>2025</option><option>2024</option><option>2023</option></select></Label><Label name="매출액 (원)"><input disabled={authenticated} type="text" className={I} value={data.revenue} placeholder="금액 입력" onChange={e => update('revenue', e.target.value)} /></Label><Label name="상시근로자 수 (명)"><input disabled={authenticated} type="text" className={I} value={data.employees} placeholder="인원 입력" onChange={e => update('employees', e.target.value)} /></Label></div><Sep /><div className="mt-6"><h3 className="text-[14px] font-bold">정부지원사업 수행이력</h3><fieldset className="mt-4"><legend className="text-[12px] font-semibold text-slate-700">수행이력 여부</legend><div className="mt-3 flex flex-wrap gap-4">{([{value:'yes',label:'수행이력 있음'},{value:'none',label:'수행이력 없음'},{value:'unknown',label:'아직 확인하지 못함'}] as const).map(x=><label key={x.value} className="flex items-center gap-2 text-[13px]"><input disabled={authenticated} type="radio" name="history-status" checked={historyStatus===x.value} onChange={()=>setHistoryStatus(x.value)}/>{x.label}</label>)}</div></fieldset>{historyStatus==='yes'?<div className="mt-5 space-y-4">{projects.map((item,i)=><section key={item.id} aria-label={'수행이력 '+(i+1)} className="rounded-xl border border-slate-200 p-4"><div className="mb-4 flex items-center justify-between"><h4 className="text-[14px] font-bold">수행사업 {i+1}</h4><button disabled={authenticated} className={S} onClick={()=>setProjects(a=>a.filter(x=>x.id!==item.id))}><Trash2 size={15}/> 제외</button></div><div className="grid gap-4 sm:grid-cols-2">{([{key:'name',label:'수행사업명'},{key:'period',label:'수행연도 또는 기간'},{key:'agency',label:'지원기관'},{key:'details',label:'주요 수행내용'},{key:'evidence',label:'관련 증빙 메모 (선택)'}] as const).map(f=><Label key={f.key} name={f.label}>{f.key==='details'?<textarea disabled={authenticated} className={I+' min-h-[100px]'} value={item[f.key]} onChange={e=>setProjects(a=>a.map(x=>x.id===item.id?{...x,[f.key]:e.target.value}:x))}/>:<input disabled={authenticated} className={I} value={item[f.key]} onChange={e=>setProjects(a=>a.map(x=>x.id===item.id?{...x,[f.key]:e.target.value}:x))}/>}</Label>)}</div></section>)}<button disabled={authenticated} className={S} onClick={()=>setProjects(a=>[...a,{id:Date.now(),name:'',period:'',agency:'',details:'',evidence:''}])}><Plus size={15}/> 수행사업 추가</button><p className="text-[12px] text-slate-500">자료 업로드 없이 직접 입력할 수 있습니다. 실제 저장은 미연결입니다.</p></div>:<p className="mt-4 rounded-xl bg-slate-50 p-5 text-[13px] text-slate-600">{historyStatus==='none'?'수행이력 없음으로 선택했습니다.':'수행이력 미확인입니다. 이력이 없는 것으로 간주하지 않습니다.'}</p>}</div><div className="mt-5 flex justify-end gap-2"><button disabled={authenticated} className={P} onClick={() => {
                  setFinanceSaved(true);notify('재무·사업이력 입력을 현재 미리보기 세션에 보관했습니다. 실제 서버 저장은 미연결입니다.');
                }}><Check size={15} /> 저장</button><button className={S} onClick={() => goto('needs')}>개선요구 등록 <ArrowRight size={15} /></button></div></Card>
    </>}


    {page === 'needs' && <>
     <Header eyebrow="IMPROVEMENT / 05" title="개선요구 등록" sub="현재 문제와 희망하는 개선 방향을 자유롭게 작성하세요."><Chip color={needSaved ? 'green' : 'amber'}>{needSaved ? '요구사항 작성 완료' : '작성 중'}</Chip></Header>
     <div className="grid gap-5 lg:grid-cols-[1.6fr_.75fr]"><Card className="p-6"><div className="space-y-5"><Label name="현재 문제 (As-Is)"><textarea disabled={authenticated} aria-label="현재 문제 (As-Is)" className={I + ' min-h-[150px] resize-y leading-6'} value={problem} onChange={e => {
                      setProblem(e.target.value);
                      setNeedSaved(false);
                    }} /></Label><Label name="희망 개선목표 (To-Be)"><textarea disabled={authenticated} aria-label="희망 개선목표 (To-Be)" className={I + ' min-h-[130px] resize-y leading-6'} value={goal} onChange={e => {
                      setGoal(e.target.value);
                      setNeedSaved(false);
                    }} /></Label><Label name="적용 제약 및 확인 필요사항"><textarea disabled={authenticated} aria-label="적용 제약 및 확인 필요사항" className={I + ' min-h-[90px] resize-y'} value={limits} onChange={e => setLimits(e.target.value)} /></Label></div><div className="mt-6 flex flex-wrap justify-end gap-2"><button className={S} onClick={() => openFiles('needs')}>관련자료 첨부 <Paperclip size={15} /></button><button disabled={authenticated} className={P} onClick={() => {
                    if (!problem.trim() || !goal.trim()) return notify('현재 문제와 개선목표를 입력해 주세요.');
                    setNeedSaved(true);setInputChecked(false);goto('review');notify('개선요구를 미리보기 세션에 보관했습니다. 실제 분석·서버 저장·DATCO 전송은 미연결입니다.');
                  }}><Check size={15} /> 개선요구 저장</button></div></Card><Card className="h-fit p-5"><div className="flex items-center gap-2 text-blue-600"><Sparkles size={20} /><h3 className="text-[14px] font-bold text-slate-800">작성 가이드</h3></div><div className="mt-4 space-y-4">{['어떤 문제가 반복되고 있나요?', '현재 어떤 방법으로 관리하나요?', '개선 후 무엇을 확인하고 싶나요?', '현재 시스템이나 예산 제약이 있나요?'].map((q, i) => <div className="flex items-start gap-3" key={q}><span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-blue-50 text-[11px] font-bold text-blue-700">{i + 1}</span><p className="text-[12px] leading-6 text-slate-500">{q}</p></div>)}</div></Card></div>
    </>}


    {page === 'files' && <>
     <Header eyebrow="DOCUMENTS / 06" title="첨부자료 관리" sub="자료 추가, 분류 변경, 파일 교체, 이력 확인을 한곳에서 관리합니다." />
     {fileReturn&&<Card className="mb-5 flex flex-wrap items-center justify-between gap-3 p-4"><p className="text-[12px]">전체 단계의 공통 자료함 · 입력은 원래 화면에 유지됩니다.</p><button className={S} onClick={()=>goto(fileReturn)}>{fileReturn==='needs'?'개선요구 등록':fileReturn==='finance'?'재무·사업이력':'기업정보 등록 시작'}으로 돌아가기</button></Card>}
     <Card className="mb-5 grid gap-4 p-5 sm:grid-cols-3"><Label name="자료 검색"><input disabled={authenticated} aria-label="자료 검색" className={I} placeholder="파일명 또는 설명" value={fileQuery} onChange={e=>setFileQuery(e.target.value)}/></Label><Label name="자료 유형 필터"><select disabled={authenticated} aria-label="자료 유형 필터" className={I} value={typeFilter} onChange={e=>setTypeFilter(e.target.value)}><option value="">전체 자료 유형</option>{categories.map(c=><option key={c}>{c}</option>)}</select></Label><Label name="등록 단계 필터"><select disabled={authenticated} aria-label="등록 단계 필터" className={I} value={stageFilter} onChange={e=>setStageFilter(e.target.value)}><option value="">전체 등록 단계</option>{Object.entries(stageNames).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></Label></Card>
     <Card className="p-5 md:p-7"><div data-preview-dropzone data-dragging={dragging} onDragEnter={e=>{e.preventDefault();dragDepth.current++;setDragging(true);}} onDragOver={e=>{e.preventDefault();e.dataTransfer.dropEffect='copy';}} onDragLeave={e=>{e.preventDefault();if(--dragDepth.current<=0){dragDepth.current=0;setDragging(false);}}} onDrop={e=>{e.preventDefault();dragDepth.current=0;setDragging(false);void receive(e.dataTransfer.files,null,fileReturn==='onboarding'||fileReturn==='finance'||fileReturn==='needs'?fileReturn:'files');}} className={'flex flex-wrap items-center justify-between gap-4 rounded-2xl border-2 border-dashed p-6 '+(dragging?'border-blue-600 bg-blue-100 ring-4 ring-blue-100':'border-blue-200 bg-blue-50/30')}><div><h2 className="text-[15px] font-bold">기업 서류와 증빙자료 등록</h2><p className="mt-2 text-[12px] text-blue-700">파일을 이곳에 끌어다 놓거나 파일 추가 버튼을 눌러 주세요.</p><p className="mt-2 text-[12px] text-slate-500">TXT, CSV, JSON, PDF, DOCX, XLSX, JPG, PNG · 파일당 15MB 이하</p></div><div className="flex flex-wrap gap-2"><input disabled={authenticated} ref={upload} type="file" multiple accept=".txt,.csv,.json,.pdf,.docx,.xlsx,.jpg,.jpeg,.png" onChange={onUpload} className="hidden" /><button className={P} disabled={authenticated || (busy)} onClick={() => upload.current?.click()}><Plus size={16} /> 파일 추가</button></div></div>
      <div className="mb-4 mt-7 flex items-center justify-between"><h3 className="text-[15px] font-bold">등록된 자료 <span className="text-blue-600">{documents.length}</span><span className="ml-2 text-[11px] text-slate-400">검색 결과 {visibleDocs.length}개</span></h3><button onClick={() => goto('onboarding')} className={S}>서류로 정보 가져오기 <ArrowRight size={15} /></button></div>
      <input disabled={authenticated} type="file" ref={replace} accept=".txt,.csv,.json,.pdf,.docx,.xlsx,.jpg,.jpeg,.png" onChange={onReplace} className="hidden" />
      <div className="space-y-3">{visibleDocs.length === 0 ? <div className="rounded-xl border border-dashed border-slate-200 p-9 text-center text-[13px] text-slate-400">{documents.length?'조건에 맞는 자료가 없습니다. 검색 조건을 변경해 주세요.':'등록된 파일이 없습니다. 새 파일을 추가해 주세요.'}</div> : visibleDocs.map((doc) => <div key={doc.id} data-preview-document={doc.id} className="rounded-xl border border-slate-100 px-4 py-4"><div className="flex flex-wrap items-center gap-3"><FileIcon name={doc.name} /><div className="min-w-[175px] flex-1"><p className="break-all text-[12px] font-bold">{doc.name}</p><p className="mt-1 text-[11px] text-slate-400">{doc.size} · v{doc.version} · {doc.savedInfo?.category??'자료정보 미반영'}</p><p className="mt-2 whitespace-pre-wrap text-[12px] text-slate-600">{doc.savedInfo?.description||'반영된 자료 설명 없음'}</p><p className="mt-1 text-[11px] text-amber-700">{isDirty(doc)?'미저장 변경사항 · 미리보기 반영 필요':'미리보기 반영됨 · 서버 미저장'}</p></div><p className="text-[11px] text-slate-500">등록 단계: {stageNames[doc.origin]} · 참조 단계: {doc.usedIn.map(k=>stageNames[k]).join(', ')}</p><Chip color={doc.status.includes('후보') ? 'green' : 'amber'}>{doc.status}</Chip><button disabled={authenticated} className={S} onClick={() => {
                      setChanging(documents.findIndex(d=>d.id===doc.id));
                      replace.current?.click();
                    }}><RefreshCw size={15} /> 교체</button><button disabled={authenticated} className={S} onClick={() => {
                      setDocuments(a => a.filter(x => x.id !== doc.id));
                      setAudit(a => ['자료 제외: ' + doc.name, ...a]);
                      notify('자료를 현재 목록에서 제외했습니다. 실제 저장소 파일은 변경되지 않습니다.');
                    }}><Trash2 size={15} /> 제외</button></div><div className="mt-3 flex flex-wrap items-center justify-between border-t border-slate-100 pt-3"><Label name="자료 유형"><select disabled={authenticated} aria-label="자료 유형" value={doc.category} onChange={e => {
                        setDocuments(a => a.map((x) => x.id === doc.id ? {
                          ...x,
                          category: e.target.value
                        } : x));
                        setAudit(a => ['분류 변경: ' + doc.name, ...a]);
                      }} className={I + ' !w-[190px]'}>{categories.map(x => <option key={x}>{x}</option>)}</select></Label><p className="text-[11px] text-slate-400">{doc.history.length ? '이전 버전: ' + doc.history.join(', ') : '등록된 변경 이력 없음'}</p></div><div className="mt-4 border-t border-slate-100 pt-4"><div className="mb-3 flex items-center justify-between"><h4 className="text-[13px] font-bold">자료 설명 및 연결</h4><button disabled={authenticated} className={S} onClick={()=>setDocuments(a=>a.map(x=>x.id===doc.id?{...x,editing:!x.editing}:x))}>{doc.editing?'설명 편집 접기':'설명 수정'}</button></div>{doc.editing?<div className="grid gap-4 sm:grid-cols-2"><div className="sm:col-span-2"><Label name="자료 설명"><textarea disabled={authenticated} aria-label="자료 설명" className={I+' min-h-[110px] resize-y'} placeholder="자료의 내용과 확인할 사항을 입력해 주세요." value={doc.description} onChange={e=>setDocuments(a=>a.map(x=>x.id===doc.id?{...x,description:e.target.value}:x))}/></Label></div><Label name="관련 사업장"><select disabled={authenticated} aria-label="관련 사업장" className={I} value={doc.siteId??''} onChange={e=>setDocuments(a=>a.map(x=>x.id===doc.id?{...x,siteId:e.target.value?Number(e.target.value):null}:x))}><option value="">선택하지 않음</option>{sites.map((x,i)=><option key={x.id} value={x.id}>사업장 {i+1} — {x.name||'이름 입력 필요'}</option>)}</select></Label><Label name="관련 개선과제"><select disabled={authenticated} aria-label="관련 개선과제" className={I} value={doc.improvement} onChange={e=>setDocuments(a=>a.map(x=>x.id===doc.id?{...x,improvement:e.target.value}:x))}><option value="">선택하지 않음</option><option value="current">현재 작성 중인 개선과제</option></select></Label></div>:<div className="space-y-2 text-[12px] text-slate-600"><p className="whitespace-pre-wrap">{doc.description||'자료 설명 미입력'}</p><p>관련 사업장: {sites.find(x=>x.id===doc.siteId)?.name||'선택하지 않음'}</p><p>관련 개선과제: {doc.improvement?'현재 작성 중인 개선과제':'선택하지 않음'}</p></div>}<div className="mt-3 flex flex-wrap gap-2" aria-label="기존 자료 참조">{(['onboarding','finance','needs'] as const).map(stage=><button key={stage} className={S} disabled={authenticated || (doc.usedIn.includes(stage))} onClick={()=>referenceFile(doc.id,stage)}>{stageNames[stage]}{doc.usedIn.includes(stage)?' 참조 중':'에서 참조'}</button>)}</div><p className="mt-3 text-[11px] text-slate-400">미리보기 입력 · 실제 자료 설명 저장/연결은 미연결</p>{doc.siteRemoved&&<p role="alert" className="mt-2 text-[12px] text-amber-700">연결한 사업장이 삭제되었습니다. 관련 사업장을 다시 선택하고 자료정보 저장을 눌러 주세요.</p>}<button disabled={authenticated} className={P+' mt-3'} onClick={()=>saveDocumentInfo(doc.id)}>자료정보 저장</button></div></div>)}</div>
     </Card><Card className="mt-5 p-6"><div className="flex items-center gap-2"><History size={18} className="text-blue-600" /><h3 className="text-[14px] font-bold">자료 변경 이력</h3></div><div className="mt-3 space-y-2">{audit.length ? audit.slice(0, 8).map((a, i) => <p className="text-[12px] text-slate-500" key={i}>{a}</p>) : <p className="text-[12px] text-slate-400">변경 이력이 없습니다.</p>}</div></Card>
    </>}


    {page === 'review' && <>
     <Header eyebrow="ANALYSIS / 07" title="분석 결과 확인" sub="기업의 개선 요구를 항목별로 구조화하여 검토하고 입력값을 확인합니다."><Chip color="violet">{authenticated?"분석 미연결":"미리보기 예시 · 분석 미연결"}</Chip></Header>
     <Card className="p-6"><div className="mb-5 flex items-center gap-2"><Sparkles size={19} className="text-blue-600" /><h3 className="text-[15px] font-bold">개선요구 항목 정리</h3></div><p className="rounded-xl bg-slate-50 p-4 text-[12px] leading-7 text-slate-600"><b className="text-slate-900">입력 원문 · As-Is</b><br />{problem}</p><div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{problems.map((x, i) => <div className="rounded-xl border border-slate-100 bg-white p-4" key={x.title}><p className="text-[10px] font-bold text-blue-600">문제 {i + 1}</p><h4 className="mt-3 text-[13px] font-bold">{x.title}</h4><p className="mt-2 text-[11px] leading-6 text-slate-500">{x.desc}</p></div>)}</div><p className="mt-5 text-[12px] leading-7"><b>개선목표 · To-Be:</b> {goal}</p><p className="mt-2 text-[11px] leading-6 text-amber-700">{authenticated?"데이터 연결 후 표시됩니다. 실제 AI 분석은 수행하지 않았습니다.":"화면 디자인을 위한 고정 예시입니다. 입력 문장을 분석하지 않으며 실제 AI·사실확인 결과가 아닙니다."}</p><p className="mt-2 whitespace-pre-wrap text-[12px]">제약 및 확인 필요사항: {limits}</p><button className={S+' mt-5 mr-2'} onClick={()=>goto('needs')}>개선요구 수정</button><button disabled={authenticated} className={P + ' mt-5'} onClick={() => {
                setInputChecked(true);goto('home');notify('입력내용을 미리보기에서 확인했습니다. 실제 DATCO 전송은 미연결입니다.');
              }}><Check size={15} /> 입력내용 확인</button></Card>
    </>}


    {page === 'requests' && <>
     <Header eyebrow="REQUESTS / 08" title="보완 요청함" sub="추가로 필요한 자료와 담당자 요청사항을 확인하고 보완할 수 있습니다." />
     {authenticated?<Card className="p-6">데이터 연결 후 표시됩니다.</Card>:<>
     <Card className="p-6"><div className="flex flex-wrap items-center justify-between gap-3"><div className="flex items-center gap-3"><div className="grid h-11 w-11 place-items-center rounded-xl bg-amber-50 text-amber-600"><MessageSquareText size={21} /></div><div><h3 className="text-[15px] font-bold">공정 운영자료 추가 요청</h3><p className="mt-1 text-[11px] text-slate-500">제1사업장 · 요청 내용 예시</p></div></div><Chip color={requestSent ? 'green' : 'amber'}>{requestSent ? '제출 완료' : '응답 필요'}</Chip></div><p className="mt-5 text-[12px] leading-7 text-slate-600">현재 재고 입출고 기록 방식과 생산 작업실적 관리 방법을 확인할 수 있는 자료를 등록해 주세요.</p><div className="mt-6 flex flex-wrap justify-end gap-2"><button className={S} onClick={() => goto('files')}><Paperclip size={15} /> 자료 등록</button><button disabled={authenticated} className={P} onClick={() => {
                  notify('미연결: 서버 저장·분석·제출·승인은 다음 단계에서 연결합니다. 실제 처리하지 않았습니다.');
                  notify('미연결: 실제 저장·분석·제출·승인은 수행하지 않았습니다. 다음 단계에서 연결합니다.');
                }}><Send size={15} /> 보완 완료 표시</button></div></Card></>}
    </>}


    {page === 'proposals' && <>
     <Header eyebrow="PROPOSALS / 09" title={proposalOpen ? '제안서 상세 · 확인' : '받은 제안서'} sub="서비스 개선 방향, 정부지원사업 후보와 제안 범위를 확인하세요."><Chip color={decision === '확인' ? 'green' : 'amber'}>{authenticated?'데이터 미연결':decision === '미확인' ? '검토 대기' : decision}</Chip></Header>
     {authenticated?<Card className="p-6">데이터 연결 후 표시됩니다.</Card>:<>
     {!proposalOpen ? <Card className="p-6"><div className="flex flex-wrap items-center gap-4"><div className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl bg-blue-50 text-blue-600"><FileCheck2 size={27} /></div><div className="min-w-[210px] flex-1"><h3 className="text-[16px] font-bold">재고·생산·품질관리 개선 제안서</h3><p className="mt-2 text-[12px] text-slate-500">{data.company || '㈜한빛정밀'} · {data.site} · 제안서 v1.0</p><div className="mt-2"><Chip color="blue">사전 준비된 예시 제안서</Chip></div></div><button className={P} onClick={() => setProposalOpen(true)}>제안서 열람 <ArrowRight size={15} /></button></div></Card> : <>
      <button onClick={() => setProposalOpen(false)} className="mb-5 flex items-center gap-1 text-[12px] font-semibold text-blue-700"><ChevronLeft size={15} /> 제안서 목록으로</button><Card className="overflow-hidden"><div className="bg-[#F7FAFF] p-6"><Chip color="blue">ProposalVersion v1.0 · 예시</Chip><h2 className="mt-3 text-[20px] font-extrabold">재고·생산·품질관리 개선 제안</h2><p className="mt-2 text-[12px] text-slate-500">{data.company || '㈜한빛정밀'} · {data.site}</p></div><div className="flex gap-1 overflow-x-auto border-b border-slate-100 px-4">{[{
                    id: 'overview',
                    n: '제안 요약'
                  }, {
                    id: 'solution',
                    n: '서비스 구성'
                  }, {
                    id: 'notice',
                    n: '지원사업 검토'
                  }, {
                    id: 'response',
                    n: '확인 · 회신'
                  }].map(t => <button key={t.id} onClick={() => setProposalTab(t.id as typeof proposalTab)} className={'shrink-0 border-b-2 px-4 py-4 text-[12px] font-bold ' + (proposalTab === t.id ? 'border-blue-600 text-blue-700' : 'border-transparent text-slate-500')}>{t.n}</button>)}</div><div className="p-6">
       {proposalTab === 'overview' && <div className="space-y-5"><h3 className="text-[15px] font-bold">제안 배경</h3><p className="text-[13px] leading-8 text-slate-600">{problem}</p><Sep /><h3 className="text-[15px] font-bold">개선 목표</h3><p className="text-[13px] leading-8 text-slate-600">{goal}</p><div className="rounded-xl bg-amber-50 p-4 text-[12px] text-amber-800">제안서 내용은 실제 고객에게 전달된 확정 문서가 아닌 준비된 예시입니다.</div></div>}
       {proposalTab === 'solution' && <div className="space-y-3">{['재고 및 입출고 관리', '생산 실적 관리', '품질 및 불량 이력 관리'].map((x, i) => <div key={x} className="flex gap-3 rounded-xl border border-slate-100 p-4"><span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-blue-50 text-[12px] font-bold text-blue-700">{i + 1}</span><div><p className="text-[13px] font-bold">{x}</p><p className="mt-1 text-[12px] text-slate-500">기존 기업 문제의 해결범위 및 전제조건 검토 예시</p></div></div>)}<p className="mt-4 text-[11px] leading-6 text-amber-700">실제 DMP Capability 카탈로그 연동 전이므로 검증된 공급 가능 기능이 아닙니다.</p></div>}
       {proposalTab === 'notice' && <div className="rounded-xl border border-slate-100 p-5"><Chip color="amber">공식 공고 아님</Chip><h3 className="mt-3 text-[16px] font-bold">제조혁신 지원사업 후보 A (가상)</h3><p className="mt-3 text-[12px] leading-7 text-slate-600">기업 개선목표와의 연관성을 설명하기 위한 예시입니다. 지원자격, 신청기간, 비용 및 사업 내용은 공식 원천 검토가 필요합니다.</p></div>}
       {proposalTab === 'response' && <div><h3 className="text-[15px] font-bold">제안서 확인 및 의견</h3><p className="mt-3 text-[12px] leading-7 text-slate-500">v1.0 제안 내용을 확인하고 의견을 남겨 주세요. 현재 동작은 화면 상태만 변경합니다.</p><textarea disabled={authenticated} className={I + ' mt-5 min-h-[100px] resize-y'} value={opinion} onChange={e => setOpinion(e.target.value)} placeholder="검토 의견을 입력해 주세요." /><div className="mt-5 flex flex-wrap gap-2"><button disabled={authenticated} className={P} onClick={() => setConfirm(true)}><Check size={15} /> 제안서 확인</button><button disabled={authenticated} className={S} onClick={() => {
                        notify('미연결: 서버 저장·분석·제출·승인은 다음 단계에서 연결합니다. 실제 처리하지 않았습니다.');
                        notify('미연결: 실제 저장·분석·제출·승인은 수행하지 않았습니다. 다음 단계에서 연결합니다.');
                      }}><Pencil size={15} /> 수정 요청</button><button disabled={authenticated} className={S} onClick={() => downloadText('DATCO_제안서_예시.txt', 'DATCO ONE 제안서\n기업: ' + (data.company || '㈜한빛정밀') + '\n개선문제: ' + problem + '\n개선목표: ' + goal + '\n참고: 검토용 예시 문서')}><FileDown size={15} /> 예시 TXT 다운로드</button></div></div>}
      </div></Card></>}</>}
    </>}


    <nav aria-label="미리보기 화면 이동" className="mt-6 flex flex-wrap items-center gap-3"><button className={S} onClick={()=>window.history.back()}>이전 화면</button><button className={S} onClick={()=>goto('home')}>홈으로</button><button className={P} onClick={()=>{const list=menu.flatMap(g=>g.items);goto(list[(list.findIndex(x=>x.id===page)+1)%list.length].id);}}>다음 화면</button><span className="text-[11px] text-amber-700">미리보기 데이터 · 실제 업무 처리 없음</span></nav>
    <footer className="mt-9 flex flex-wrap justify-between gap-3 border-t border-slate-200 pt-5 text-[10px] leading-5 text-slate-400"><span>DATCO ONE · 수요기업 포털</span><span>화면 체험 환경의 입력값은 서버에 저장되지 않습니다. 실제 SSO·AI·DMP 연동은 별도 구축 대상입니다.</span></footer>
   </div></main>
  </div>
  {confirm && <div className="fixed inset-0 z-[80] grid place-items-center bg-slate-900/50 p-4"><div className="w-full max-w-[420px] rounded-3xl bg-white p-7 shadow-2xl" role="dialog" aria-modal="true" aria-label="제안서 확인"><div className="mb-3 grid h-12 w-12 place-items-center rounded-xl bg-blue-50 text-blue-600"><FileCheck2 size={25} /></div><h2 className="text-[19px] font-bold">제안서 v1.0을 확인하시겠습니까?</h2><p className="mt-3 text-[12px] leading-7 text-slate-500">이 동작은 화면의 확인 상태만 변경하며 DATCO 운영자에게 전송하거나 실제 승인 처리하지 않습니다.</p><div className="mt-6 flex justify-end gap-2"><button disabled={authenticated} className={S} onClick={() => setConfirm(false)}>취소</button><button disabled={authenticated} className={P} onClick={() => {
            notify('미연결: 서버 저장·분석·제출·승인은 다음 단계에서 연결합니다. 실제 처리하지 않았습니다.');
            setConfirm(false);
            notify('미연결: 실제 저장·분석·제출·승인은 수행하지 않았습니다. 다음 단계에서 연결합니다.');
          }}>확인</button></div></div></div>}
 </div>;
};
