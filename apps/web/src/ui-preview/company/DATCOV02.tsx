// UI reproduction from the user-provided MagicPath DATCOV02 v0.2. Development preview only.
import React, { useEffect, useRef, useState } from 'react';
import { LayoutDashboard, Building2, ChartColumnIncreasing, ClipboardPenLine, Paperclip, ScanSearch, MessageSquareText, FileCheck2, Menu, X, ChevronRight, ChevronLeft, LogOut, UserRound, Files, UploadCloud, Check, ArrowRight, Layers3, FileText, FileSpreadsheet, Image as ImageIcon, LockKeyhole, ShieldCheck, RefreshCw, Trash2, Pencil, History, Download, Plus, Info, CheckCircle2, Sparkles, Send, FileDown } from 'lucide-react';
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
const menu: Array<{
  head: string;
  items: Array<{
    id: Screen;
    name: string;
    icon: LucideIcon;
  }>;
}> = [{
  head: '대시보드',
  items: [{
    id: 'home',
    name: '기업 홈',
    icon: LayoutDashboard
  }]
}, {
  head: '기업정보',
  items: [{
    id: 'onboarding',
    name: '기업정보 등록 시작',
    icon: UploadCloud
  }, {
    id: 'extraction',
    name: '추출정보 확인',
    icon: ScanSearch
  }, {
    id: 'company',
    name: '기업 · 사업장 관리',
    icon: Building2
  }, {
    id: 'finance',
    name: '재무 · 사업이력',
    icon: ChartColumnIncreasing
  }]
}, {
  head: '개선과제 및 자료',
  items: [{
    id: 'needs',
    name: '개선요구 등록',
    icon: ClipboardPenLine
  }, {
    id: 'files',
    name: '첨부자료 관리',
    icon: Paperclip
  }, {
    id: 'review',
    name: '분석 결과 확인',
    icon: Sparkles
  }, {
    id: 'requests',
    name: '보완 요청함',
    icon: MessageSquareText
  }]
}, {
  head: '제안 및 승인',
  items: [{
    id: 'proposals',
    name: '받은 제안서',
    icon: FileCheck2
  }]
}];
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
const fields: Array<{
  key: CandidateKey;
  label: string;
  regex: RegExp;
}> = [{
  key: 'company',
  label: '기업명',
  regex: /(?:^|\n)\s*(?:기업명|상호명|상호|회사명)\s*[:：=,]\s*([^\r\n,]+)/i
}, {
  key: 'reg',
  label: '사업자등록번호',
  regex: /(?:^|\n)\s*(?:사업자등록번호|사업자번호|등록번호)\s*[:：=,]\s*([\d-]+)/i
}, {
  key: 'industry',
  label: '업종',
  regex: /(?:^|\n)\s*(?:업종|주업종)\s*[:：=,]\s*([^\r\n,]+)/i
}, {
  key: 'address',
  label: '사업장 소재지',
  regex: /(?:^|\n)\s*(?:사업장\s*소재지|사업장\s*주소|주소|소재지)\s*[:：=,]\s*([^\r\n]+)/i
}, {
  key: 'person',
  label: '담당자',
  regex: /(?:^|\n)\s*(?:담당자|담당자명)\s*[:：=,]\s*([^\r\n,]+)/i
}, {
  key: 'revenue',
  label: '매출액',
  regex: /(?:^|\n)\s*(?:매출액|연매출)\s*[:：=,]\s*([^\r\n,]+)/i
}, {
  key: 'employees',
  label: '직원수',
  regex: /(?:^|\n)\s*(?:직원수|근로자수|상시근로자수)\s*[:：=,]\s*([^\r\n,]+)/i
}];
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
const exampleText = '기업명: ㈜한빛정밀\n사업자등록번호: 123-45-67890\n업종: 금속가공 제조업\n사업장 소재지: 경기도 성남시 분당구\n담당자: 김담당\n매출액: 1800000000\n직원수: 42';
export const DATCOV02 = () => {
  const [loggedIn, setLoggedIn] = useState(() => new URLSearchParams(window.location.search).get('screen') !== null && new URLSearchParams(window.location.search).get('screen') !== 'login');
  const [loginId, setLoginId] = useState('');
  const [password, setPassword] = useState('');
  const [loginErr, setLoginErr] = useState('');
  const [page, setPage] = useState<Screen>(() => {const p=new URLSearchParams(window.location.search).get('screen');return menu.flatMap(g=>g.items).some(x=>x.id===p)?p as Screen:'home';});
  const [mobileMenu, setMobileMenu] = useState(false);
  const [data, setData] = useState<FieldData>(preset);
  const [saved, setSaved] = useState(false);
  const [problem, setProblem] = useState('재고 수량이 실제 수량과 다르고 입출고를 수기로 처리합니다. 생산실적과 불량 발생 현황을 체계적으로 관리하고 싶습니다.');
  const [goal, setGoal] = useState('재고·입출고 현황과 생산실적·품질정보를 통합적으로 확인하고 관리하고 싶습니다.');
  const [limits, setLimits] = useState('기존 ERP 연동 가능 여부와 현장 데이터 수집 방식 확인이 필요합니다.');
  const [needSaved, setNeedSaved] = useState(false);
  const [documents, setDocuments] = useState<Doc[]>([]);
  const [docCategory, setDocCategory] = useState('사업자등록증');
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [candidateSource, setCandidateSource] = useState('');
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
    setPage(p);
    const u=new URL(window.location.href);u.searchParams.set('screen',p);window.history.pushState({},'',u);
    setMobileMenu(false);
    setToaster('');
    scroller.current?.scrollTo(0, 0);
  };
  const update = (k: keyof FieldData, val: string) => {
    setData(x => ({
      ...x,
      [k]: val
    }));
    setSaved(false);
  };
  const logout = () => {
    setLoggedIn(false);
    setPassword('');
    setLoginErr('');
    setToaster('');
    setPage('home');
    const u=new URL(window.location.href);u.searchParams.set('screen','login');window.history.pushState({},'',u);
  };
  useEffect(()=>{const back=()=>{const p=new URLSearchParams(window.location.search).get('screen');setLoggedIn(!!p&&p!=='login');if(menu.flatMap(g=>g.items).some(x=>x.id===p))setPage(p as Screen);setMobileMenu(false);};window.addEventListener('popstate',back);return()=>window.removeEventListener('popstate',back);},[]);
  const doLogin=(ev:React.FormEvent)=>{ev.preventDefault();setPassword('');setLoginErr('');setLoggedIn(true);goto('home');};
  const extractFromText = (body: string, source: string): Candidate[] => {
    let txt = body;
    if (body.trim().startsWith('{')) try {
      const x = JSON.parse(body);
      txt = Object.entries(x).map(([k, v]) => k + ': ' + String(v)).join('\n');
    } catch {}
    return fields.flatMap(f => {
      const match = txt.match(f.regex);
      return match ? [{
        key: f.key,
        value: match[1].trim(),
        label: f.label,
        source,
        selected: true
      }] : [];
    });
  };
  const receive=async(fileList:FileList|null,toReplace:number|null=null)=>{
    if(!fileList?.length)return;
    for(const [j,f] of Array.from(fileList).slice(0,5).entries()){
      const old=toReplace!==null&&j===0?documents[toReplace]:undefined;
      const item:Doc={id:old?.id??Date.now()+j,name:f.name,size:(f.size/1024).toFixed(1)+' KB',type:f.type,category:docCategory,version:(old?.version??0)+1,status:'미리보기 · 미업로드',history:old?[...old.history,old.name+' · 미리보기']:[],file:f};
      setDocuments(prev=>old?prev.map((v,k)=>k===toReplace?item:v):[...prev,item]);
      setAudit(a=>['미리보기 목록 변경: '+f.name,...a]);
    }
    notify('파일명·크기 미리보기만 표시합니다. 업로드·파싱·서버 저장은 다음 단계에서 연결합니다.');
  };
  const onUpload = async (ev: React.ChangeEvent<HTMLInputElement>) => {
    await receive(ev.target.files);
    ev.target.value = '';
  };
  const onReplace = async (ev: React.ChangeEvent<HTMLInputElement>) => {
    await receive(ev.target.files, changing);
    ev.target.value = '';
    setChanging(null);
  };
  const prepareSample = () => {
    const from = '샘플 기업정보.txt · 사전 준비된 예시';
    setCandidates(extractFromText(exampleText, from));
    setCandidateSource(from);
    goto('extraction');
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
  const sampleDoc = () => downloadText('DATCO_기업정보_샘플.txt', exampleText);
  const progress=[false,false,false,false,false];
  const problems=[{title:'재고관리',desc:'미리보기 예시: 수량 불일치 및 현황 확인'},{title:'입출고 관리',desc:'미리보기 예시: 기록·흐름 관리'},{title:'생산실적',desc:'미리보기 예시: 현황 수집·추적'},{title:'품질관리',desc:'미리보기 예시: 불량정보 관리'}];
  if (!loggedIn) return <div className="flex h-[900px] min-h-[680px] w-full bg-[#F7F9FD] text-slate-800" style={{
    fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, Segoe UI, Noto Sans KR, sans-serif'
  }}>
  <div className="hidden w-[48%] flex-col justify-between overflow-hidden bg-[#113967] p-12 text-white lg:flex">
   <div className="flex items-center gap-3"><div className="grid h-11 w-11 place-items-center rounded-xl bg-white/20"><Layers3 size={23} /></div><div><b className="text-xl">DATCO ONE</b><p className="text-[11px] tracking-[.07em] text-blue-200">정부지원사업 운영관리</p></div></div>
   <div><p className="mb-5 text-[11px] font-semibold tracking-[.2em] text-blue-200">DATCO BUSINESS PLATFORM</p><h1 className="text-[39px] font-extrabold leading-[1.4] tracking-[-.05em]">기업의 가능성을<br />실질적인 성장으로<br />연결합니다.</h1><p className="mt-6 max-w-[390px] text-[14px] leading-8 text-blue-100/90">기업정보 등록부터 개선과제 분석, DATCO 솔루션 검토, 정부지원사업과 맞춤형 제안서까지.</p><div className="mt-10 flex flex-wrap gap-2">{['기업정보 등록', '문서 기반 정보확인', '서비스 제안서'].map((x, i) => <span key={x} className="rounded-lg border border-white/20 px-3 py-2 text-[11px] text-blue-100">{i + 1}. {x}</span>)}</div></div><p className="text-[11px] text-blue-200/80">DATCO · Business Portal</p>
  </div>
  <div className="flex flex-1 items-center justify-center px-5 py-10"><form onSubmit={doLogin} className="w-full max-w-[435px] rounded-[25px] border border-slate-100 bg-white p-8 shadow-[0_15px_65px_rgba(32,58,91,.07)] md:p-10">
   <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-blue-50 text-[#1767C7]"><LockKeyhole size={23} /></div><h2 className="text-[27px] font-extrabold text-slate-900">수요기업 로그인</h2><p className="mt-2 text-[13px] text-slate-500">기업 계정으로 로그인해 주세요.</p>
   <div className="mt-8 space-y-4"><Label name="아이디"><input className={I} value={loginId} onChange={e => setLoginId(e.target.value)} autoComplete="username" placeholder="아이디 또는 이메일" /></Label><Label name="비밀번호"><input className={I} type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password" placeholder="비밀번호를 입력해 주세요" /></Label></div>
   {loginErr && <p className="mt-3 text-[12px] text-rose-600" role="alert">{loginErr}</p>}
   <button type="submit" className={P + ' mt-7 w-full py-3.5'}>미리보기 시작 <ArrowRight size={16} /></button>
   <div className="mt-6 rounded-xl bg-slate-50 p-4 text-[11px] leading-6 text-slate-500"><p className="mb-1 font-semibold text-slate-700">개발 전용 화면 미리보기</p><p>실제 계정을 입력하지 마세요.</p><p>인증·권한·세션을 생성하지 않습니다.</p><p className="mt-2 text-slate-400">로그인 버튼은 수요기업 홈 미리보기로만 이동합니다.</p></div>
  </form></div>
 </div>;
  return <div className="flex h-[900px] min-h-[690px] w-full overflow-hidden bg-[#F7F9FC] text-slate-800" style={{
    fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, Segoe UI, Noto Sans KR, sans-serif'
  }}>
  {mobileMenu && <div className="fixed inset-0 z-40 bg-slate-900/40 lg:hidden" onClick={() => setMobileMenu(false)} />}
  <aside className={'fixed inset-y-0 left-0 z-50 flex w-[254px] shrink-0 flex-col border-r border-slate-200 bg-white transition-transform lg:static lg:translate-x-0 ' + (mobileMenu ? 'translate-x-0' : '-translate-x-full')}>
   <div className="flex h-[75px] items-center gap-3 border-b border-slate-100 px-5"><div className="grid h-9 w-9 place-items-center rounded-xl bg-[#1767C7] text-white"><Layers3 size={19} /></div><div><b className="text-[17px] tracking-tight">DATCO <span className="text-[#1767C7]">ONE</span></b><p className="text-[10px] text-slate-400">정부지원사업 운영관리</p></div><button className="ml-auto lg:hidden" onClick={() => setMobileMenu(false)} aria-label="메뉴 닫기"><X size={20} /></button></div>
   <div className="min-h-0 flex-1 overflow-y-auto px-3 py-5">{menu.map(g => <div key={g.head} className="mb-6"><p className="mb-2 px-3 text-[10px] font-bold tracking-[.12em] text-slate-400">{g.head}</p>{g.items.map(x => <button key={x.id} onClick={() => goto(x.id)} className={'my-0.5 flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-[12px] font-semibold transition-colors ' + (page === x.id ? 'bg-[#EAF3FF] text-[#1465BF]' : 'text-slate-600 hover:bg-slate-50')}><x.icon size={18} /><span className="flex-1">{x.name}</span>{page === x.id && <span className="h-1.5 w-1.5 rounded-full bg-blue-600" />}{x.id === 'requests' && !requestSent && <span className="rounded-full bg-amber-100 px-2 text-[10px] text-amber-700">1</span>}</button>)}</div>)}</div>
   <div className="m-3 rounded-xl border border-slate-100 bg-[#F7F9FC] p-4"><div className="flex items-center gap-2"><ShieldCheck className="text-[#1767C7]" size={17} /><span className="text-[12px] font-semibold">기업정보 보호</span></div><p className="mt-2 text-[11px] leading-6 text-slate-500">문서 추출 후보와 확정된 기업정보를 구분합니다.</p></div>
   <div className="flex items-center gap-3 border-t border-slate-100 px-5 py-4"><div className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-blue-50 text-blue-600"><UserRound size={18} /></div><div className="min-w-0 flex-1"><p className="text-[12px] font-bold">수요기업 사용자</p><p className="truncate text-[11px] text-slate-400">회사 담당자</p></div><button onClick={logout} className="rounded-lg p-2 text-slate-500 hover:bg-rose-50 hover:text-rose-600" title="로그아웃" aria-label="로그아웃"><LogOut size={19} /></button></div>
  </aside>
  <div className="flex min-w-0 flex-1 flex-col">
   <header className="flex h-[75px] shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4 md:px-8"><div className="flex items-center gap-3"><button className="rounded-lg p-2 text-slate-500 lg:hidden" onClick={() => setMobileMenu(true)} aria-label="메뉴 열기"><Menu size={20} /></button><span className="hidden text-[12px] text-slate-400 sm:block">수요기업 포털</span><ChevronRight size={15} className="hidden text-slate-300 sm:block" /><span className="text-[13px] font-bold">{menu.flatMap(x => x.items).find(x => x.id === page)?.name}</span></div><div className="flex items-center gap-3"><Chip color="blue">{data.company || '기업정보 입력 중'}</Chip><div className="grid h-8 w-8 place-items-center rounded-full bg-[#EAF3FF] text-[12px] font-bold text-[#1767C7]">기</div><button onClick={logout} className={S + ' hidden sm:inline-flex'}><LogOut size={15} /> 로그아웃</button></div></header>
   <main ref={scroller} className="min-h-0 flex-1 overflow-y-auto"><div className="mx-auto max-w-[1190px] px-4 pb-14 pt-7 md:px-8">
    {toaster && <div role="status" className="mb-5 flex items-center justify-between gap-3 rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-[12px] text-blue-800"><div className="flex items-center gap-2"><Info size={16} /><span>{toaster}</span></div><button onClick={() => setToaster('')} aria-label="알림 닫기"><X size={16} /></button></div>}


    {page === 'home' && <>
     <Header eyebrow="COMPANY DASHBOARD" title="기업 홈" sub="우리 기업의 업무 진행 현황과 다음 할 일을 확인하세요." />
     <Card className="relative overflow-hidden bg-[#123D70] p-7 text-white md:p-9"><div className="pointer-events-none absolute -right-20 -top-28 h-72 w-72 rounded-full border-[44px] border-white/5" /><p className="text-[11px] font-semibold tracking-[.2em] text-blue-200">WELCOME TO DATCO ONE</p><h2 className="mt-4 text-[25px] font-bold leading-[1.45]">{data.company || '우리 기업'}의 성장과 혁신을<br />함께 준비합니다.</h2><p className="mt-3 text-[12px] leading-6 text-blue-100">기업정보 및 개선과제를 등록하고 맞춤형 솔루션과 지원사업 제안서를 확인해 보세요.</p><button className="mt-6 inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3 text-[12px] font-bold text-blue-700" onClick={() => goto('onboarding')}>기업정보 등록 시작 <ArrowRight size={16} /></button></Card>
     <Card className="mt-5 p-6"><div className="mb-4 flex items-center justify-between"><h3 className="text-[15px] font-bold">업무 진행 단계</h3><span className="text-[12px] font-semibold text-blue-600">{progress.filter(Boolean).length} / 5</span></div><div className="mb-5 h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-blue-600" style={{
                  width: progress.filter(Boolean).length * 20 + '%'
                }} /></div><div className="grid gap-2 sm:grid-cols-5">{[{
                  t: '기업 등록',
                  s: 'company'
                }, {
                  t: '개선요구',
                  s: 'needs'
                }, {
                  t: '자료 제출',
                  s: 'files'
                }, {
                  t: '분석 확인',
                  s: 'review'
                }, {
                  t: '제안서 확인',
                  s: 'proposals'
                }].map((x, i) => <button key={x.t} onClick={() => goto(x.s as Screen)} className="flex items-center gap-2 rounded-xl bg-slate-50 px-3 py-4 text-left hover:bg-blue-50 sm:flex-col sm:items-start"><span className={'grid h-7 w-7 shrink-0 place-items-center rounded-full text-[11px] font-bold ' + (progress[i] ? 'bg-emerald-100 text-emerald-700' : 'bg-white text-slate-500')}>{progress[i] ? <Check size={15} /> : i + 1}</span><span className="text-[11px] font-semibold">{x.t}</span></button>)}</div></Card>
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
     <div className="grid gap-5 lg:grid-cols-2"><Card className="p-6 md:p-8"><div className="grid h-12 w-12 place-items-center rounded-xl bg-blue-50 text-blue-600"><UploadCloud size={25} /></div><h2 className="mt-4 text-[18px] font-bold">서류로 기업정보 가져오기</h2><p className="mt-3 min-h-[65px] text-[13px] leading-7 text-slate-500">기업 관련 서류를 업로드하면 추출할 수 있는 항목을 정리하고, 확인 후 입력란에 적용할 수 있습니다.</p><div className="mt-3 rounded-2xl border-2 border-dashed border-blue-200 bg-blue-50/30 p-5 text-center"><p className="text-[12px] font-bold">사업자등록증 · 회사 기본정보 · 재무자료</p><p className="mt-3 text-[11px] leading-6 text-slate-500">파일 선택은 이름·크기 미리보기만 제공합니다.<br />PDF·DOCX·XLSX·이미지 추출은 서버 파서 연결 대상입니다.</p><input ref={upload} className="hidden" type="file" multiple accept=".txt,.csv,.json,.pdf,.docx,.xlsx,.jpg,.jpeg,.png" onChange={onUpload} /><button onClick={() => upload.current?.click()} disabled={busy} className={P + ' mt-4'}>{busy ? '문서 처리 중' : '서류 선택'} <UploadCloud size={15} /></button></div><div className="mt-4 flex flex-wrap gap-3"><button onClick={sampleDoc} className="text-[12px] font-semibold text-blue-700 hover:underline"><Download size={14} className="mr-1 inline" /> 체험용 기업정보 문서 내려받기</button><button onClick={prepareSample} className="text-[12px] font-semibold text-blue-700 hover:underline">예시 추출 후보 열기 →</button></div></Card>
      <Card className="p-6 md:p-8"><div className="grid h-12 w-12 place-items-center rounded-xl bg-slate-100 text-slate-600"><Pencil size={24} /></div><h2 className="mt-4 text-[18px] font-bold">기업정보 직접 입력</h2><p className="mt-3 min-h-[65px] text-[13px] leading-7 text-slate-500">첨부자료가 없거나 추출할 수 없는 항목이 있다면 직접 입력하거나 누락된 내용을 보완할 수 있습니다.</p><div className="mt-3 space-y-4 rounded-xl bg-slate-50 p-5">{['기업명·사업자등록정보', '사업장·담당자·업종', '재무정보 및 지원사업 이력'].map(x => <div key={x} className="flex items-center gap-2 text-[12px] text-slate-600"><CheckCircle2 size={16} className="text-blue-600" />{x}</div>)}</div><button onClick={() => goto('company')} className={S + ' mt-5'}>직접 작성 <ArrowRight size={15} /></button></Card></div>
      <div className="mt-5 flex items-start gap-3 rounded-2xl border border-blue-100 bg-blue-50 p-5 text-[12px] leading-6 text-blue-800"><Info size={17} className="mt-1 shrink-0" />서류 추출값은 저장된 확정 정보가 아니라 후보입니다. 사용자가 검토·수정한 이후 기업정보에 반영합니다.</div>
    </>}


    {page === 'extraction' && <>
     <Header eyebrow="EXTRACTION / 02" title="추출된 기업정보 확인" sub="원본에서 가져온 정보의 값과 출처를 확인하고 기업정보 입력란에 반영하세요."><Chip color="blue">{candidates.length}개 후보</Chip></Header>
     <div className="grid gap-5 lg:grid-cols-[.85fr_1.55fr]"><Card className="p-6"><h3 className="text-[14px] font-bold">추출 원본</h3><div className="mt-4 flex gap-3 rounded-xl bg-slate-50 p-4"><FileIcon name={candidateSource || 'info.txt'} /><div><p className="break-all text-[12px] font-semibold">{candidateSource || '등록된 추출 원본이 없습니다.'}</p><p className="mt-1 text-[11px] text-slate-400">문서 정보의 추출 후보</p></div></div><div className="mt-5 rounded-xl bg-amber-50 p-4 text-[12px] leading-6 text-amber-800">추출값을 적용해도 DATCO의 최종 Fact 확정이 자동으로 이루어지는 것은 아닙니다.</div><button onClick={() => goto('onboarding')} className={S + ' mt-5 w-full'}><ChevronLeft size={15} /> 다른 서류 선택</button></Card>
     <Card className="p-6"><div className="mb-4 flex items-center justify-between"><h3 className="text-[14px] font-bold">항목별 정보 검토</h3><Chip color="amber">사용자 확인 필요</Chip></div>{candidates.length === 0 ? <div className="rounded-xl bg-slate-50 px-5 py-10 text-center"><p className="text-[13px] text-slate-500">추출된 항목이 없습니다.</p><button className={S + ' mt-3'} onClick={() => goto('company')}>직접 정보 입력</button></div> : <div className="space-y-3">{candidates.map((x, i) => <div key={x.key} className="flex gap-3 rounded-xl border border-slate-100 p-4"><input type="checkbox" aria-label={x.label + ' 적용'} checked={x.selected} onChange={e => setCandidates(a => a.map((v, j) => j === i ? {
                      ...v,
                      selected: e.target.checked
                    } : v))} className="mt-8 h-4 w-4 accent-blue-600" /><div className="min-w-0 flex-1"><Label name={x.label}><input className={I} value={x.value} onChange={e => setCandidates(a => a.map((v, j) => j === i ? {
                          ...v,
                          value: e.target.value
                        } : v))} /></Label><p className="mt-2 text-[11px] text-slate-400">출처: {x.source}</p></div></div>)}</div>}<div className="mt-6 flex flex-wrap justify-end gap-2"><button className={S} onClick={() => goto('company')}>직접 입력</button><button className={P} disabled={!candidates.length} onClick={applyCandidates}><Check size={15} /> 선택한 정보 적용</button></div></Card></div>
    </>}


    {page === 'company' && <>
     <Header eyebrow="COMPANY / 03" title="기업 · 사업장 관리" sub="문서에서 가져온 값을 수정하거나 직접 정보를 작성할 수 있습니다."><Chip color={saved ? 'green' : 'amber'}>{saved ? '입력 보관 완료' : '확인·저장 필요'}</Chip></Header>
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
                }, {
                  key: 'site',
                  label: '사업장명'
                }, {
                  key: 'address',
                  label: '사업장 소재지'
                }].map(f => <Label key={f.key} name={f.label}><input className={I} placeholder={f.label + ' 입력'} value={data[f.key as keyof FieldData]} onChange={e => update(f.key as keyof FieldData, e.target.value)} /></Label>)}</div><div className="mt-7 flex justify-end gap-2"><button className={P} onClick={() => {
                  if (!data.company.trim()) {
                    notify('기업명을 입력해 주세요.');
                    return;
                  }
                  notify('미연결: 기업정보 저장은 다음 단계에서 연결합니다. 실제 저장하지 않았습니다.');
                  notify('미연결: 실제 저장·분석·제출·승인은 수행하지 않았습니다. 다음 단계에서 연결합니다.');
                }}><Check size={15} /> 기업정보 저장</button><button className={S} onClick={() => goto('finance')}>재무정보 이동 <ArrowRight size={15} /></button></div></Card>
    </>}


    {page === 'finance' && <>
     <Header eyebrow="FINANCE / 04" title="재무 · 사업이력" sub="연도와 단위를 구분해 재무정보 및 기존 지원사업 수행이력을 관리합니다." />
     <Card className="p-6"><h3 className="mb-5 text-[15px] font-bold">재무정보</h3><div className="grid gap-4 sm:grid-cols-3"><Label name="기준 연도"><select className={I}><option>2025</option><option>2024</option><option>2023</option></select></Label><Label name="매출액 (원)"><input type="text" className={I} value={data.revenue} placeholder="금액 입력" onChange={e => update('revenue', e.target.value)} /></Label><Label name="상시근로자 수 (명)"><input type="text" className={I} value={data.employees} placeholder="인원 입력" onChange={e => update('employees', e.target.value)} /></Label></div><Sep /><div className="mt-6"><h3 className="text-[14px] font-bold">정부지원사업 수행이력</h3><div className="mt-3 rounded-xl border border-dashed border-slate-200 bg-slate-50 p-8 text-center text-[12px] leading-6 text-slate-500">등록된 수행이력이 없습니다.<br />실제 운영에서는 사업명·기간·지원기관·증빙을 등록합니다.</div></div><div className="mt-5 flex justify-end gap-2"><button className={P} onClick={() => {
                  notify('미연결: 서버 저장·분석·제출·승인은 다음 단계에서 연결합니다. 실제 처리하지 않았습니다.');
                  notify('미연결: 실제 저장·분석·제출·승인은 수행하지 않았습니다. 다음 단계에서 연결합니다.');
                }}><Check size={15} /> 저장</button><button className={S} onClick={() => goto('needs')}>개선요구 등록 <ArrowRight size={15} /></button></div></Card>
    </>}


    {page === 'needs' && <>
     <Header eyebrow="IMPROVEMENT / 05" title="개선요구 등록" sub="현재 문제와 희망하는 개선 방향을 자유롭게 작성하세요."><Chip color={needSaved ? 'green' : 'amber'}>{needSaved ? '요구사항 작성 완료' : '작성 중'}</Chip></Header>
     <div className="grid gap-5 lg:grid-cols-[1.6fr_.75fr]"><Card className="p-6"><div className="space-y-5"><Label name="현재 문제 (As-Is)"><textarea className={I + ' min-h-[150px] resize-y leading-6'} value={problem} onChange={e => {
                      setProblem(e.target.value);
                      setNeedSaved(false);
                    }} /></Label><Label name="희망 개선목표 (To-Be)"><textarea className={I + ' min-h-[130px] resize-y leading-6'} value={goal} onChange={e => {
                      setGoal(e.target.value);
                      setNeedSaved(false);
                    }} /></Label><Label name="적용 제약 및 확인 필요사항"><textarea className={I + ' min-h-[90px] resize-y'} value={limits} onChange={e => setLimits(e.target.value)} /></Label></div><div className="mt-6 flex flex-wrap justify-end gap-2"><button className={S} onClick={() => goto('files')}>관련자료 첨부 <Paperclip size={15} /></button><button className={P} onClick={() => {
                    if (!problem.trim() || !goal.trim()) return notify('현재 문제와 개선목표를 입력해 주세요.');
                    notify('미연결: 서버 저장·분석·제출·승인은 다음 단계에서 연결합니다. 실제 처리하지 않았습니다.');
                    notify('미연결: 실제 저장·분석·제출·승인은 수행하지 않았습니다. 다음 단계에서 연결합니다.');
                  }}><Check size={15} /> 개선요구 저장</button></div></Card><Card className="h-fit p-5"><div className="flex items-center gap-2 text-blue-600"><Sparkles size={20} /><h3 className="text-[14px] font-bold text-slate-800">작성 가이드</h3></div><div className="mt-4 space-y-4">{['어떤 문제가 반복되고 있나요?', '현재 어떤 방법으로 관리하나요?', '개선 후 무엇을 확인하고 싶나요?', '현재 시스템이나 예산 제약이 있나요?'].map((q, i) => <div className="flex items-start gap-3" key={q}><span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-blue-50 text-[11px] font-bold text-blue-700">{i + 1}</span><p className="text-[12px] leading-6 text-slate-500">{q}</p></div>)}</div></Card></div>
    </>}


    {page === 'files' && <>
     <Header eyebrow="DOCUMENTS / 06" title="첨부자료 관리" sub="자료 추가, 분류 변경, 파일 교체, 이력 확인을 한곳에서 관리합니다." />
     <Card className="p-5 md:p-7"><div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border-2 border-dashed border-blue-200 bg-blue-50/30 p-6"><div><h2 className="text-[15px] font-bold">기업 서류와 증빙자료 등록</h2><p className="mt-2 text-[12px] text-slate-500">TXT, CSV, JSON, PDF, DOCX, XLSX, JPG, PNG · 파일당 15MB 이하</p></div><div className="flex flex-wrap gap-2"><select aria-label="자료 분류" className={I + ' !w-auto'} value={docCategory} onChange={e => setDocCategory(e.target.value)}>{['사업자등록증', '재무자료', '기업소개서', '공정·현장자료', '지원사업 이력', '기타'].map(v => <option key={v}>{v}</option>)}</select><input ref={upload} type="file" multiple accept=".txt,.csv,.json,.pdf,.docx,.xlsx,.jpg,.jpeg,.png" onChange={onUpload} className="hidden" /><button className={P} disabled={busy} onClick={() => upload.current?.click()}><Plus size={16} /> 파일 추가</button></div></div>
      <div className="mb-4 mt-7 flex items-center justify-between"><h3 className="text-[15px] font-bold">등록된 자료 <span className="text-blue-600">{documents.length}</span></h3><button onClick={() => goto('onboarding')} className={S}>서류로 정보 가져오기 <ArrowRight size={15} /></button></div>
      <input type="file" ref={replace} accept=".txt,.csv,.json,.pdf,.docx,.xlsx,.jpg,.jpeg,.png" onChange={onReplace} className="hidden" />
      <div className="space-y-3">{documents.length === 0 ? <div className="rounded-xl border border-dashed border-slate-200 p-9 text-center text-[13px] text-slate-400">등록된 파일이 없습니다. 새 파일을 추가해 주세요.</div> : documents.map((doc, i) => <div key={doc.id} className="rounded-xl border border-slate-100 px-4 py-4"><div className="flex flex-wrap items-center gap-3"><FileIcon name={doc.name} /><div className="min-w-[175px] flex-1"><p className="break-all text-[12px] font-bold">{doc.name}</p><p className="mt-1 text-[11px] text-slate-400">{doc.size} · v{doc.version} · {doc.category}</p></div><Chip color={doc.status.includes('후보') ? 'green' : 'amber'}>{doc.status}</Chip><button className={S} onClick={() => {
                      setChanging(i);
                      replace.current?.click();
                    }}><RefreshCw size={15} /> 교체</button><button className={S} onClick={() => {
                      setDocuments(a => a.filter((_, idx) => idx !== i));
                      setAudit(a => ['자료 제외: ' + doc.name, ...a]);
                      notify('자료를 현재 목록에서 제외했습니다. 실제 저장소 파일은 변경되지 않습니다.');
                    }}><Trash2 size={15} /> 제외</button></div><div className="mt-3 flex flex-wrap items-center justify-between border-t border-slate-100 pt-3"><Label name="자료 유형"><select value={doc.category} onChange={e => {
                        setDocuments(a => a.map((x, idx) => idx === i ? {
                          ...x,
                          category: e.target.value
                        } : x));
                        setAudit(a => ['분류 변경: ' + doc.name, ...a]);
                      }} className={I + ' !w-[190px]'}>{['사업자등록증', '재무자료', '기업소개서', '공정·현장자료', '지원사업 이력', '기타'].map(x => <option key={x}>{x}</option>)}</select></Label><p className="text-[11px] text-slate-400">{doc.history.length ? '이전 버전: ' + doc.history.join(', ') : '등록된 변경 이력 없음'}</p></div></div>)}</div>
     </Card><Card className="mt-5 p-6"><div className="flex items-center gap-2"><History size={18} className="text-blue-600" /><h3 className="text-[14px] font-bold">자료 변경 이력</h3></div><div className="mt-3 space-y-2">{audit.length ? audit.slice(0, 8).map((a, i) => <p className="text-[12px] text-slate-500" key={i}>{a}</p>) : <p className="text-[12px] text-slate-400">변경 이력이 없습니다.</p>}</div></Card>
    </>}


    {page === 'review' && <>
     <Header eyebrow="ANALYSIS / 07" title="분석 결과 확인" sub="기업의 개선 요구를 항목별로 구조화하여 검토하고 입력값을 확인합니다."><Chip color="violet">미리보기 예시 · 분석 미연결</Chip></Header>
     <Card className="p-6"><div className="mb-5 flex items-center gap-2"><Sparkles size={19} className="text-blue-600" /><h3 className="text-[15px] font-bold">개선요구 항목 정리</h3></div><p className="rounded-xl bg-slate-50 p-4 text-[12px] leading-7 text-slate-600"><b className="text-slate-900">입력 원문</b><br />{problem}</p><div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{problems.map((x, i) => <div className="rounded-xl border border-slate-100 bg-white p-4" key={x.title}><p className="text-[10px] font-bold text-blue-600">문제 {i + 1}</p><h4 className="mt-3 text-[13px] font-bold">{x.title}</h4><p className="mt-2 text-[11px] leading-6 text-slate-500">{x.desc}</p></div>)}</div><p className="mt-5 text-[12px] leading-7"><b>개선목표:</b> {goal}</p><p className="mt-2 text-[11px] leading-6 text-amber-700">화면 디자인을 위한 고정 예시입니다. 입력 문장을 분석하지 않으며 실제 AI·사실확인 결과가 아닙니다.</p><button className={P + ' mt-5'} onClick={() => {
                notify('미연결: 서버 저장·분석·제출·승인은 다음 단계에서 연결합니다. 실제 처리하지 않았습니다.');
                notify('미연결: 실제 저장·분석·제출·승인은 수행하지 않았습니다. 다음 단계에서 연결합니다.');
              }}><Check size={15} /> 입력내용 확인</button></Card>
    </>}


    {page === 'requests' && <>
     <Header eyebrow="REQUESTS / 08" title="보완 요청함" sub="추가로 필요한 자료와 담당자 요청사항을 확인하고 보완할 수 있습니다." />
     <Card className="p-6"><div className="flex flex-wrap items-center justify-between gap-3"><div className="flex items-center gap-3"><div className="grid h-11 w-11 place-items-center rounded-xl bg-amber-50 text-amber-600"><MessageSquareText size={21} /></div><div><h3 className="text-[15px] font-bold">공정 운영자료 추가 요청</h3><p className="mt-1 text-[11px] text-slate-500">제1사업장 · 요청 내용 예시</p></div></div><Chip color={requestSent ? 'green' : 'amber'}>{requestSent ? '제출 완료' : '응답 필요'}</Chip></div><p className="mt-5 text-[12px] leading-7 text-slate-600">현재 재고 입출고 기록 방식과 생산 작업실적 관리 방법을 확인할 수 있는 자료를 등록해 주세요.</p><div className="mt-6 flex flex-wrap justify-end gap-2"><button className={S} onClick={() => goto('files')}><Paperclip size={15} /> 자료 등록</button><button className={P} onClick={() => {
                  notify('미연결: 서버 저장·분석·제출·승인은 다음 단계에서 연결합니다. 실제 처리하지 않았습니다.');
                  notify('미연결: 실제 저장·분석·제출·승인은 수행하지 않았습니다. 다음 단계에서 연결합니다.');
                }}><Send size={15} /> 보완 완료 표시</button></div></Card>
    </>}


    {page === 'proposals' && <>
     <Header eyebrow="PROPOSALS / 09" title={proposalOpen ? '제안서 상세 · 확인' : '받은 제안서'} sub="서비스 개선 방향, 정부지원사업 후보와 제안 범위를 확인하세요."><Chip color={decision === '확인' ? 'green' : 'amber'}>{decision === '미확인' ? '검토 대기' : decision}</Chip></Header>
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
       {proposalTab === 'response' && <div><h3 className="text-[15px] font-bold">제안서 확인 및 의견</h3><p className="mt-3 text-[12px] leading-7 text-slate-500">v1.0 제안 내용을 확인하고 의견을 남겨 주세요. 현재 동작은 화면 상태만 변경합니다.</p><textarea className={I + ' mt-5 min-h-[100px] resize-y'} value={opinion} onChange={e => setOpinion(e.target.value)} placeholder="검토 의견을 입력해 주세요." /><div className="mt-5 flex flex-wrap gap-2"><button className={P} onClick={() => setConfirm(true)}><Check size={15} /> 제안서 확인</button><button className={S} onClick={() => {
                        notify('미연결: 서버 저장·분석·제출·승인은 다음 단계에서 연결합니다. 실제 처리하지 않았습니다.');
                        notify('미연결: 실제 저장·분석·제출·승인은 수행하지 않았습니다. 다음 단계에서 연결합니다.');
                      }}><Pencil size={15} /> 수정 요청</button><button className={S} onClick={() => downloadText('DATCO_제안서_예시.txt', 'DATCO ONE 제안서\n기업: ' + (data.company || '㈜한빛정밀') + '\n개선문제: ' + problem + '\n개선목표: ' + goal + '\n참고: 검토용 예시 문서')}><FileDown size={15} /> 예시 TXT 다운로드</button></div></div>}
      </div></Card></>}
    </>}


    <nav aria-label="미리보기 화면 이동" className="mt-6 flex flex-wrap items-center gap-3"><button className={S} onClick={()=>window.history.back()}>이전 화면</button><button className={S} onClick={()=>goto('home')}>홈으로</button><button className={P} onClick={()=>{const list=menu.flatMap(g=>g.items);goto(list[(list.findIndex(x=>x.id===page)+1)%list.length].id);}}>다음 화면</button><span className="text-[11px] text-amber-700">미리보기 데이터 · 실제 업무 처리 없음</span></nav>
    <footer className="mt-9 flex flex-wrap justify-between gap-3 border-t border-slate-200 pt-5 text-[10px] leading-5 text-slate-400"><span>DATCO ONE · 수요기업 포털</span><span>화면 체험 환경의 입력값은 서버에 저장되지 않습니다. 실제 SSO·AI·DMP 연동은 별도 구축 대상입니다.</span></footer>
   </div></main>
  </div>
  {confirm && <div className="fixed inset-0 z-[80] grid place-items-center bg-slate-900/50 p-4"><div className="w-full max-w-[420px] rounded-3xl bg-white p-7 shadow-2xl" role="dialog" aria-modal="true" aria-label="제안서 확인"><div className="mb-3 grid h-12 w-12 place-items-center rounded-xl bg-blue-50 text-blue-600"><FileCheck2 size={25} /></div><h2 className="text-[19px] font-bold">제안서 v1.0을 확인하시겠습니까?</h2><p className="mt-3 text-[12px] leading-7 text-slate-500">이 동작은 화면의 확인 상태만 변경하며 DATCO 운영자에게 전송하거나 실제 승인 처리하지 않습니다.</p><div className="mt-6 flex justify-end gap-2"><button className={S} onClick={() => setConfirm(false)}>취소</button><button className={P} onClick={() => {
            notify('미연결: 서버 저장·분석·제출·승인은 다음 단계에서 연결합니다. 실제 처리하지 않았습니다.');
            setConfirm(false);
            notify('미연결: 실제 저장·분석·제출·승인은 수행하지 않았습니다. 다음 단계에서 연결합니다.');
          }}>확인</button></div></div></div>}
 </div>;
};
