"use client";
/**
 * DATCO ONE 관리자 포털 참조 UI · 별도 시연용 소스.
 * Actual DMP/SSO/API/DB/Provider operations are NOT performed here.
 * User, policy, approval, publish and permission changes are local examples ONLY.
 * Integrators must preserve and enforce existing repository FROZEN contracts on the server.
 */
import React, { useState } from "react";
import { Activity, AlertCircle, ArrowLeft, ArrowRight, BarChart3, BookOpen, Check, CheckCircle2, ChevronRight, ClipboardCheck, ClipboardList, Eye, FolderSearch, GitBranch, History, Info, Layers3, LayoutDashboard, Link2, LockKeyhole, LogOut, Menu, Plus, RefreshCw, Search, Send, Settings2, Shield, ShieldAlert, ShieldCheck, ShieldQuestion, Sparkles, UserRound, Users, Workflow, X } from "lucide-react";
import "./admin-portal.css";

type Page =
  | "dashboard" | "features" | "capabilities" | "publishing" | "notices"
  | "requirements" | "users" | "access" | "analysis" | "quality"
  | "integrations" | "audit";
type Tone = "neutral" | "info" | "success" | "warning" | "danger" | "purple";
type ReleaseState = "PUBLISHED" | "DRAFT" | "REVIEW_PENDING";
type ReviewState = "CANDIDATE" | "REVIEWED_SAMPLE" | "NEEDS_INFO";
type JobState = "SUCCESS" | "FAILED" | "BLOCKED";

type Feature = { id: string; name: string; category: string; description: string; revision: string; capabilityId: string; catalogReady: boolean; source: string; evidence: string; updatedAt: string };
type Capability = { id: string; title: string; description: string; category: string; version: number; releaseState: ReleaseState; featureIds: string[]; conditions: string[]; coverage: string[]; limitations: string[]; evidence: string | null; publishedAt: string | null; changeHistory: string[]; authorizationHint: string };
type Requirement = { id: string; title: string; value: string; comparator: string; status: "CANDIDATE" | "REVIEWED_SAMPLE"; evidence: string };
type Notice = { id: string; title: string; agency: string; round: string; region: string; version: number; reviewStatus: ReviewState; from: string; to: string; official: boolean; source: string; sourceType: string; requirements: Requirement[]; history: string[] };
type User = { id: string; name: string; email: string; role: string; status: string; scopeCompanyIds: string[]; lastSeen: string; notes: string };
type Company = { id: string; name: string; stage: string; siteId: string };
type AIRun = { id: string; companyId: string; task: string; mode: string; engine: string; status: JobState; startedAt: string; durationMs: number; evidence: string; attempt: number; note: string };
type QualityIssue = { id: string; entityType: string; targetId: string; issue: string; kind: string; status: string; owner: string; next: string };
type Integration = { id: string; name: string; category: string; status: string; desc: string; prerequisites: string[]; owner: string };
type Audit = { id: string; actor: string; action: string; target: string; at: string; detail: string; source: string };
type AccessRequest = { id: string; userId: string; companyId: string; intent: string; status: "승인 전 요청"; at: string };
type Fixture = {
  schemaVersion: string; dataNature: string; admin: { id: string; displayName: string; roleLabel: string };
  features: Feature[]; capabilities: Capability[]; notices: Notice[]; users: User[]; companies: Company[];
  aiRuns: AIRun[]; qualityIssues: QualityIssue[]; integrations: Integration[]; audit: Audit[];
};
export type AdminPreviewData = Fixture;
const Availability = React.createContext({connected:true,available:true,page:"dashboard" as Page});
const NAV: { section: string; items: { page: Page; name: string; icon: React.ComponentType<{ size?: number }> }[] }[] = [
  { section: "시스템 현황", items: [
    { page: "dashboard", name: "관리 대시보드", icon: LayoutDashboard },
    { page: "features", name: "DMP 기능 목록", icon: Layers3 },
    { page: "capabilities", name: "Capability 관리", icon: Workflow },
    { page: "publishing", name: "서비스 버전·발행", icon: GitBranch },
  ] },
  { section: "기준정보 관리", items: [
    { page: "notices", name: "정부지원사업 공고", icon: BookOpen },
    { page: "requirements", name: "공고 분석·요건 검토", icon: ClipboardCheck },
  ] },
  { section: "사용자 및 AI", items: [
    { page: "users", name: "사용자·계정", icon: Users },
    { page: "access", name: "권한·기업 접근범위", icon: ShieldCheck },
    { page: "analysis", name: "AI 분석 운영", icon: Sparkles },
  ] },
  { section: "운영 및 기록", items: [
    { page: "quality", name: "데이터 품질", icon: BarChart3 },
    { page: "integrations", name: "DMP·외부 연동", icon: Link2 },
    { page: "audit", name: "감사·변경 이력", icon: History },
  ] },
];
const NAME = Object.fromEntries(NAV.flatMap(section => section.items).map(item => [item.page, item.name])) as Record<Page, string>;
const capLabel: Record<ReleaseState, string> = { PUBLISHED: "발행 표시", DRAFT: "초안", REVIEW_PENDING: "검토 대기" };
const capTone: Record<ReleaseState, Tone> = { PUBLISHED: "success", DRAFT: "neutral", REVIEW_PENDING: "warning" };
const noticeLabel: Record<ReviewState, string> = { CANDIDATE: "추출 후보", REVIEWED_SAMPLE: "예시 검토", NEEDS_INFO: "정보 보완 필요" };
const noticeTone: Record<ReviewState, Tone> = { CANDIDATE: "warning", REVIEWED_SAMPLE: "info", NEEDS_INFO: "danger" };
const jobLabel: Record<JobState, string> = { SUCCESS: "처리됨", FAILED: "실패", BLOCKED: "정책 차단" };
const jobTone: Record<JobState, Tone> = { SUCCESS: "success", FAILED: "danger", BLOCKED: "warning" };
const time = () => new Date().toLocaleString("ko-KR", { year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit" });
const uid = (prefix: string) => `${prefix}-${Math.floor(Date.now() / 1000)}-${Math.floor(Math.random() * 1000)}`;
const deepClone = <T,>(value: T): T => JSON.parse(JSON.stringify(value)) as T;

function Pill({ children, tone = "neutral" }: { children: React.ReactNode; tone?: Tone }) { const {connected}=React.useContext(Availability); return <span className={`da-pill da-pill-${connected?tone:"neutral"}`}>{connected?children:"연결 대기"}</span>; }
function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) { return <section className={`da-card ${className}`}>{children}</section>; }
function PageTitle({ kicker, title, detail, actions }: { kicker: string; title: string; detail: string; actions?: React.ReactNode }) {
  const {connected,page}=React.useContext(Availability);
  return <div className="da-heading"><div><div className="da-kicker">{kicker}</div><h1>{title}</h1><p>{connected?detail:PURPOSES[page]}</p></div>{actions}</div>;
}
function Label({ children, name, hint }: { children: React.ReactNode; name: string; hint?: string }) {
  const {available}=React.useContext(Availability);
  return <label className="da-label"><span>{name}</span>{React.isValidElement(children) ? React.cloneElement(children as React.ReactElement<{"aria-label"?:string;disabled?:boolean}>, {"aria-label":name,disabled:!available}) : children}{hint && <small>{hint}</small>}</label>;
}
function SectionHead({ title, subtitle, right }: { title: string; subtitle?: string; right?: React.ReactNode }) {
  const {connected}=React.useContext(Availability);
  return <div className="da-section-head"><div><h2>{title}</h2>{connected ? subtitle && <p>{subtitle}</p> : <p>데이터 연결 후 표시됩니다.</p>}</div>{right}</div>;
}
function InfoLine({ label, value }: { label: string; value: React.ReactNode }) { const {connected}=React.useContext(Availability); return <div className="da-info-line"><span>{label}</span><strong>{connected?value:"—"}</strong></div>; }
function Alert({ children, warning = false }: { children: React.ReactNode; warning?: boolean }) { const {connected}=React.useContext(Availability); if(!connected)return null; return <div className={`da-alert ${warning ? "da-alert-warning" : ""}`}><Info size={17} />{children}</div>; }
function Empty({ children }: { children: React.ReactNode }) { const {connected}=React.useContext(Availability); return <div className="da-empty"><FolderSearch size={27}/><p>{connected?children:"데이터 연결 후 표시됩니다."}</p></div>; }
function SafeAction({ children, onClick, disabled = false, kind = "outline", navigation = false }: {children: React.ReactNode; onClick?: () => void; disabled?: boolean; navigation?: boolean; kind?: "outline" | "primary" | "ghost" | "danger" }) {
 const {available}=React.useContext(Availability);
 return <button type="button" className={`da-btn da-btn-${kind}`} disabled={disabled||(!available&&!navigation)} title={!available&&!navigation?"데이터 연결과 대상 선택이 필요합니다.":undefined} onClick={available||navigation?onClick:undefined}>{children}</button>;
}
function AdminWorkspace({sample, isTest, onLogout}: {sample: Fixture; isTest: boolean; onLogout: ()=>void}) {
 const navigation = usePreviewNavigation();
 const page = navigation.page;
 const [drawer, setDrawer] = useState(false);
 const [toast, setToast] = useState("");
 const [features] = useState<Feature[]>(() => deepClone(sample.features));
 const [capabilities, setCapabilities] = useState<Capability[]>(() => deepClone(sample.capabilities));
 const [notices, setNotices] = useState<Notice[]>(() => deepClone(sample.notices));
 const [users] = useState<User[]>(() => deepClone(sample.users));
 const [jobs] = useState<AIRun[]>(() => deepClone(sample.aiRuns));
 const [issues] = useState<QualityIssue[]>(() => deepClone(sample.qualityIssues));
 const [integrations] = useState<Integration[]>(() => deepClone(sample.integrations));
 const [audit, setAudit] = useState<Audit[]>(() => deepClone(sample.audit));
 const [accessRequests, setAccessRequests] = useState<AccessRequest[]>([]);
 const [selectedFeatureId, setSelectedFeatureId] = useState("FEAT-INV-001");
 const [selectedCapId, setSelectedCapId] = useState("CAP-INV");
 const [selectedNoticeId, setSelectedNoticeId] = useState("NOTICE-S01");
 const [selectedUserId, setSelectedUserId] = useState("USER-OP-001");
 const [selectedJobId, setSelectedJobId] = useState("RUN-S02");
 const [selectedIssueId, setSelectedIssueId] = useState("DQ-S01");
 const [selectedIntegrationId, setSelectedIntegrationId] = useState("INT-SSO");
 const [search, setSearch] = useState("");
 const [featureFilter, setFeatureFilter] = useState("전체");
 const [capFilter, setCapFilter] = useState("전체");
 const [jobFilter, setJobFilter] = useState("전체");
 const [auditFilter, setAuditFilter] = useState("");
 const [draftDescription, setDraftDescription] = useState(sample.capabilities[0]?.description ?? "");
 const [draftFeatureIds, setDraftFeatureIds] = useState<string[]>(sample.capabilities[0]?.featureIds ?? []);
 const [memoDrafts, setMemoDrafts] = useState<Record<string,string>>({});
 const memoKey = page === "quality" ? `quality:${selectedIssueId}` : `notice:${selectedNoticeId}`;
 const reviewNote = memoDrafts[memoKey] ?? "";
 const setReviewNote = (text:string) => setMemoDrafts(prev=>({...prev,[memoKey]:text}));
 const [savedReviewNotes, setSavedReviewNotes] = useState<Record<string, string>>({});
 const [accessCompany, setAccessCompany] = useState("COMP-001");
 const [accessIntent, setAccessIntent] = useState("조회 접근 검토 요청");
 const [showPublishConfirm, setShowPublishConfirm] = useState(false);
 const [integrationDiagnostic, setIntegrationDiagnostic] = useState<string | null>(null);
 const [showAuditDetails, setShowAuditDetails] = useState<string | null>(null);
 const selectedFeature = features.find(f => f.id === selectedFeatureId) ?? features[0] ?? BLANK.feature;
 const selectedCap = capabilities.find(c => c.id === selectedCapId) ?? capabilities[0] ?? BLANK.cap;
 const selectedNotice = notices.find(n => n.id === selectedNoticeId) ?? notices[0] ?? BLANK.notice;
 const selectedUser = users.find(u => u.id === selectedUserId) ?? users[0] ?? BLANK.user;
 const selectedJob = jobs.find(j => j.id === selectedJobId) ?? jobs[0] ?? BLANK.job;
 const selectedIssue = issues.find(i => i.id === selectedIssueId) ?? issues[0] ?? BLANK.issue;
 const selectedIntegration = integrations.find(i => i.id === selectedIntegrationId) ?? integrations[0] ?? BLANK.integration;
 const titleOfCompany = (id: string) => sample.companies.find(c => c.id === id)?.name ?? id;
 const go = (newPage: Page) => { navigation.go(newPage); setDrawer(false); setToast(""); setSearch(""); window.scrollTo?.({top:0,behavior:"auto"}); };
 const log = (action: string, target: string, detail: string) => setAudit(prev => [{ id: uid("UIAUD"), actor: "화면 체험 관리자", action, target, at: time(), detail, source: "LOCAL_UI_ONLY" }, ...prev]);
 const show = (txt: string) => setToast(txt);
 const logout = onLogout;
 const selectedCapGuard = (cap: Capability): string[] => {
  const reasons: string[] = [];
  if (!cap.evidence) reasons.push("서비스 근거자료가 확인되지 않았습니다.");
  if (cap.featureIds.length === 0) reasons.push("연결된 기능이 없습니다.");
  const unresolved = cap.featureIds.map(fid=>features.find(f=>f.id===fid)).filter(f=>!f || !f.catalogReady);
  if(unresolved.length > 0) reasons.push(`검증되지 않은 DMP 기능이 ${unresolved.length}개 있습니다.`);
  if(cap.conditions.length === 0) reasons.push("적용 전제조건이 누락되었습니다.");
  if(cap.releaseState==="PUBLISHED") reasons.push("이미 시연 발행된 버전입니다. 수정은 신규 개정안에서 해야 합니다.");
  return reasons;
 };

 const selectCap = (id: string) => { const cap=capabilities.find(c=>c.id===id); setSelectedCapId(id); if(cap){setDraftDescription(cap.description);setDraftFeatureIds([...cap.featureIds]);} };
 const guardReasons = selectedCapGuard(selectedCap);
 const newRevision = () => {
   const next:Capability = {...deepClone(selectedCap), id:uid(`${selectedCap.id}-WORK-${selectedCap.version+1}`),version:selectedCap.version+1,releaseState:"DRAFT",publishedAt:null,changeHistory:[...selectedCap.changeHistory,`v${selectedCap.version+1} 개정안 생성(화면)`]};
   setCapabilities(prev=>[...prev,next]);selectCap(next.id);
   setDraftDescription(next.description);setDraftFeatureIds(next.featureIds);
   log("CAPABILITY_DRAFT_CREATED",next.id,`${selectedCap.id}의 신규 개정안을 화면에서 생성`);
   show("원본 발행 버전은 유지하면서 새 개정안을 화면에 생성했습니다.");
 };
 const saveDraft = () => {
   if(selectedCap.releaseState==="PUBLISHED") return show("발행된 버전은 직접 변경할 수 없습니다. '개정안 생성'을 선택하세요.");
   setCapabilities(prev=>prev.map(c=>c.id===selectedCap.id?{...c,description:draftDescription.trim() || c.description,featureIds:draftFeatureIds,changeHistory:[...c.changeHistory,`v${c.version} 초안 편집(화면)`]}:c));
   log("CAPABILITY_DRAFT_EDITED",selectedCap.id,"근거와 권한 검증 전인 화면의 개정안 저장");show("개정안 변경이 화면 상태에 반영되었습니다. 실제 DB는 변경하지 않았습니다.");
 };
 const publishSample = () => {
  const cap = capabilities.find(c=>c.id===selectedCap.id) ?? selectedCap;
  const guards = selectedCapGuard(cap);
  setShowPublishConfirm(false);
  if(guards.length){ show("발행 조건 미충족: "+guards.join(" / "));return; }
  setCapabilities(prev=>prev.map(c=>c.id===cap.id?{...c,releaseState:"PUBLISHED",publishedAt:"화면 처리: "+time(),changeHistory:[...c.changeHistory,`v${c.version} 화면상의 발행 상태 변경`]}:c));
  log("SAMPLE_CAPABILITY_PUBLISH",cap.id,"UI에서만 발행 표시. 서버 권한/승인 검증과 무관");
  show("해당 버전을 화면에서만 '발행 표시'로 변경했습니다. 실제 서비스 발행은 수행되지 않았습니다.");
 };
 const markRequirement = (rid:string)=>{
  if(!reviewNote.trim()) return show("검토 메모를 먼저 입력하세요. 공고를 공식 승인하는 동작이 아닙니다.");
  setNotices(prev=>prev.map(n=>n.id!==selectedNotice.id?n:{...n,requirements:n.requirements.map(req=>req.id===rid?{...req,status:"REVIEWED_SAMPLE"}:req)}));
  log("NOTICE_REQUIREMENT_REVIEW_SAMPLE",rid,"가상 요건 검토 메모: "+reviewNote.trim());
  show("공고 요건에 '예시 검토' 표시를 남겼습니다. 실제 공식 공고·정책을 확정하지 않았습니다.");
 };
 const submitAccess = () => {
  if(selectedUser.role==="DATCO_ADMIN") return show("관리자 본인에게 임의로 기업 업무권한을 추가할 수 없습니다.");
  if(accessRequests.some(r=>r.userId===selectedUser.id&&r.companyId===accessCompany&&r.intent===accessIntent)) return show("동일 내용의 접근 검토 요청이 이미 존재합니다.");
  const request:AccessRequest={id:uid("ACCREQ"),userId:selectedUser.id,companyId:accessCompany,intent:accessIntent,status:"승인 전 요청",at:time()};
  setAccessRequests(prev=>[request,...prev]);
  log("ACCESS_CHANGE_REQUEST",selectedUser.id,`${titleOfCompany(accessCompany)} - ${accessIntent}; 실제 권한 미부여`);
  show("접근권한 변경 검토 요청을 화면에 기록했습니다. 실제 접근권한은 변경되지 않았습니다.");
 };
 const saveMemo = ()=>{ if(!reviewNote.trim())return show("검토 메모를 입력하세요.");setSavedReviewNotes(prev=>({...prev,[selectedIssue.id]:reviewNote.trim()}));log("QUALITY_NOTE_SAVED",selectedIssue.id,reviewNote.trim());show("검토 메모를 화면 상태에 보관했습니다. 품질 이슈의 해결 상태는 변경하지 않았습니다."); };
 const auditFiltered = audit.filter(a=>[a.target,a.detail,a.actor,a.action,a.at].some(v=>v.toLowerCase().includes(auditFilter.toLowerCase())));
 const featureFiltered = features.filter(f=>(featureFilter==="전체"||f.category===featureFilter)&&[f.id,f.name,f.category,f.description].some(v=>v.toLowerCase().includes(search.toLowerCase())));
 const capFiltered = capabilities.filter(c=>(capFilter==="전체"||c.releaseState===capFilter)&&[c.id,c.title,c.description].some(v=>v.toLowerCase().includes(search.toLowerCase())));
 const noticeFiltered = notices.filter(n=>[n.title,n.agency,n.source].some(v=>v.toLowerCase().includes(search.toLowerCase())));
 const jobFiltered = jobs.filter(j=>jobFilter==="전체"||j.status===jobFilter);
 const publishedCount = capabilities.filter(c=>c.releaseState==="PUBLISHED").length;
 const unreviewedNotice = notices.filter(n=>n.reviewStatus!=="REVIEWED_SAMPLE").length;
 const attentionCount = issues.filter(i=>i.status==="OPEN").length;
 const mainPage = NAV.flatMap(g=>g.items).find(v=>v.page===page);

 return <div className="datco-admin da-layout">
  {drawer&&<div className="da-mobile-overlay" onClick={()=>setDrawer(false)}/>}
  <aside className={`da-sidebar ${drawer?"da-sidebar-open":""}`}>
   <div className="da-side-brand"><div className="da-logo-icon"><Layers3 size={20}/></div><div className="da-logo-text"><strong>DATCO <em>ONE</em></strong><span>시스템 관리 포털</span></div><button aria-label="메뉴 닫기" className="da-mobile-close" onClick={()=>setDrawer(false)}><X size={19}/></button></div>
   <nav aria-label="관리자 메뉴" className="da-side-nav">{NAV.map(section=><div className="da-nav-group" key={section.section}><span className="da-nav-group-title">{section.section}</span>{section.items.map(v=><button key={v.page} className={`da-nav-item ${page===v.page?"active":""}`} onClick={()=>go(v.page)}><v.icon size={18}/><span>{v.name}</span>{page===v.page&&<span className="da-active-mark"/>}</button>)}</div>)}</nav>
   <div className="da-side-end"><div className="da-secure-notice"><Shield size={17}/><span>원천 데이터와 승인 권한 보호</span></div><div className="da-profile"><div className="da-avatar">관</div><div><strong>DATCO 관리자</strong><span>시스템 관리</span></div><button title="로그아웃" aria-label="로그아웃" onClick={logout}><LogOut size={19}/></button></div></div>
  </aside>
  <div className="da-app-content"><header className="da-topbar"><div className="da-crumb"><button className="da-menu-toggle" onClick={()=>setDrawer(true)} aria-label="메뉴 열기"><Menu size={20}/></button><span>시스템 관리자</span><ChevronRight size={15}/><strong>{mainPage?.name}</strong></div><div className="da-top-actions"><span className="da-subtle-origin">{isTest?"격리 테스트 자료":"데이터 미연결"}</span><div className="da-header-avatar">관</div><button onClick={logout} className="da-btn da-btn-outline da-top-logout"><LogOut size={15}/> 로그아웃</button></div></header>
   <main className="da-main"><div className="da-inner">
     <div className="da-preview-navigation"><SafeAction onClick={navigation.back} disabled={!navigation.canBack}><ArrowLeft size={15}/> 이전 화면</SafeAction><SafeAction navigation onClick={()=>go("dashboard")}>관리 홈</SafeAction></div>
     <Availability.Provider value={{connected:isTest,available:isTest&&Boolean(features.length+capabilities.length+notices.length+users.length+jobs.length+issues.length+integrations.length),page}}>
     {toast&&<div className="da-toast" role="status"><Info size={16}/><span>{toast}</span><button onClick={()=>setToast("")} aria-label="알림 닫기"><X size={16}/></button></div>}

     {page==="dashboard"&&<>
       <PageTitle kicker="ADMINISTRATION OVERVIEW" title="관리 대시보드" detail="서비스 기준정보, 공고 요건, 사용자 권한 및 AI 운영 상태를 확인합니다." actions={<Pill tone="info">예시 자료 기준 현황</Pill>}/>
       <div className="da-hero"><div><span>SYSTEM ADMINISTRATION</span><h2>운영의 기준을 한곳에서 관리합니다.</h2><p>DMP 서비스 기준과 정부지원사업 데이터, 사용자 권한 및 분석 품질을 연결하는 통합 관리자 업무공간입니다.</p><SafeAction navigation kind="primary" onClick={()=>go("capabilities")}>서비스 관리 바로가기 <ArrowRight size={16}/></SafeAction></div><div className="da-hero-decoration"><Settings2 size={110}/></div></div>
       <div className="da-kpi-grid">
         {[{name:"샘플 DMP 기능",value:features.length,unit:"건",detail:"실제 649개 원천 미연동",Icon:Layers3,target:"features" as Page},{name:"Capability",value:capabilities.length,unit:"건",detail:`화면상 발행 표시 ${publishedCount}건`,Icon:Workflow,target:"capabilities" as Page},{name:"가상 정부공고",value:notices.length,unit:"건",detail:`예시 검토 미완료 ${unreviewedNotice}건`,Icon:BookOpen,target:"notices" as Page},{name:"데이터 확인 항목",value:attentionCount,unit:"건",detail:"근거·버전·정책 확인 필요",Icon:ShieldAlert,target:"quality" as Page}].map(k=><button className="da-kpi" key={k.name} onClick={()=>go(k.target)}><div className="da-kpi-top"><span>{isTest?k.name:k.name.replace("샘플 ","").replace("가상 ","")}</span><k.Icon size={19}/></div><div className="da-kpi-main"><strong>{isTest?k.value:"—"}</strong><span>{k.unit}</span></div><small>{isTest?k.detail:"데이터 연결 후 표시됩니다."}</small></button>)}
       </div>
       <div className="da-columns"><Card className="da-pad"><SectionHead title="관리자 확인 업무" subtitle="클릭하면 해당 검토 화면으로 이동합니다."/><div className="da-task-list">
         {[{title:"서비스 발행 검토",detail:"검증 안 된 Feature 포함 여부 및 근거 확인",target:"publishing" as Page,tag:"검토"},{title:"지원사업 요건 추출 확인",detail:"공고 원문과 후보 조건의 출처 검토",target:"requirements" as Page,tag:"원천"},{title:"기업 접근 요청 검토",detail:"사용자별 Company Scope와 권한 분리",target:"access" as Page,tag:"권한"},{title:"AI 실행 오류 확인",detail:"외부 AI 승인/파서 지원 상태 구분",target:"analysis" as Page,tag:"운영"}].map(row=><button key={row.title} className="da-task" onClick={()=>go(row.target)}><span className="da-task-check"><ClipboardList size={17}/></span><span><strong>{row.title}</strong><small>{row.detail}</small></span><Pill tone="warning">{row.tag}</Pill><ChevronRight size={16}/></button>)}
       </div></Card>
       <Card className="da-pad"><SectionHead title="최근 활동" subtitle="화면 기록과 초기 예시 기록을 함께 표시합니다."/><div className="da-activity-list">{audit.slice(0,5).map(a=><div key={a.id} className="da-activity"><span className="da-timeline-dot"/><div><strong>{a.detail}</strong><small>{a.at} · {a.source==="LOCAL_UI_ONLY"?"화면 조작":"준비된 예시"}</small></div></div>)}</div><SafeAction navigation onClick={()=>go("audit")}>변경 이력 전체 보기 <ArrowRight size={15}/></SafeAction></Card></div>
       <Alert>대시보드 수치는 이 패키지의 가상 Fixture 레코드를 집계한 값입니다. DATCO 실제 서비스, DMP 기능 649개 및 공식 정부사업 실적이 아닙니다.</Alert>
     </>}

     {page==="features"&&<>
       <PageTitle kicker="DMP FEATURE INVENTORY / M-02" title="DMP 기능 목록" detail="DMP 기능의 명칭·분류·근거 및 Capability 연계를 관리하는 기준정보 화면입니다." actions={<Pill tone="info">샘플 {features.length}건 / 실제 DMP 미연동</Pill>}/>
       <div className="da-split"><Card className="da-pad"><SectionHead title="기능 검색 및 목록" subtitle="실제 기능 데이터가 아닌 설명용 레코드입니다."/>
         <div className="da-filter-row"><div className="da-search"><Search size={17}/><input aria-label="기능 검색" placeholder="기능명, 코드, 분류 검색" value={search} onChange={e=>setSearch(e.target.value)}/></div><select value={featureFilter} onChange={e=>setFeatureFilter(e.target.value)} aria-label="기능 분류"><option>전체</option>{Array.from(new Set(features.map(x=>x.category))).map(v=><option key={v}>{v}</option>)}</select></div>
         <div className="da-table-wrap"><table className="da-table"><thead><tr><th>기능 / FeatureRevision</th><th>분류</th><th>검증 상태</th></tr></thead><tbody>{featureFiltered.map(f=><tr key={f.id} tabIndex={0} role="button" aria-label={f.name+" 상세 열기"} onKeyDown={e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();setSelectedFeatureId(f.id)}}} className={selectedFeature.id===f.id?"selected":""} onClick={()=>setSelectedFeatureId(f.id)}><td><b>{f.name}</b><small>{f.id} · r{f.revision}</small></td><td>{f.category}</td><td><Pill tone={f.catalogReady?"success":"warning"}>{f.catalogReady?"샘플 확인":"검증 필요"}</Pill></td></tr>)}</tbody></table>{!featureFiltered.length&&<Empty>검색 조건에 맞는 기능이 없습니다.</Empty>}</div>
       </Card><Card className="da-pad"><SectionHead title="Feature 상세" subtitle="선택된 기준정보를 확인합니다."/><div className="da-detail-header"><div className="da-square-icon"><Layers3 size={21}/></div><div><strong>{selectedFeature.name}</strong><small>{selectedFeature.id}</small></div></div><div className="da-info-grid"><InfoLine label="카테고리" value={selectedFeature.category}/><InfoLine label="Revision" value={selectedFeature.revision}/><InfoLine label="연결된 Capability" value={selectedFeature.capabilityId}/><InfoLine label="원천 구분" value="SAMPLE_ONLY"/><InfoLine label="기능 설명" value={selectedFeature.description}/><InfoLine label="근거" value={selectedFeature.evidence}/></div><Alert warning>실제 DMP Feature Inventory 동기화·원천 검증 전에는 649개 기능을 가져왔거나 발행했다고 표시하지 않습니다.</Alert><SafeAction onClick={()=>{selectCap(selectedFeature.capabilityId);go("capabilities")}}>연결된 서비스 보기 <ArrowRight size={15}/></SafeAction></Card></div>
     </>}

     {page==="capabilities"&&<>
       <PageTitle kicker="CAPABILITY CATALOG / M-03" title="DATCO Capability 관리" detail="서비스 해결범위와 실제 Feature 연결을 확인하고, 발행 버전을 보존하면서 개정안을 관리합니다." actions={<SafeAction kind="primary" onClick={newRevision}><Plus size={16}/> 선택한 서비스의 개정안 생성</SafeAction>}/>
       <div className="da-split"><Card className="da-pad"><SectionHead title="서비스 Catalog" subtitle="목록에서 서비스를 선택하세요."/>
         <div className="da-filter-row"><div className="da-search"><Search size={17}/><input placeholder="서비스명·식별자" aria-label="서비스 검색" value={search} onChange={e=>setSearch(e.target.value)}/></div><select aria-label="서비스 상태" value={capFilter} onChange={e=>setCapFilter(e.target.value)}><option value="전체">전체 상태</option><option value="PUBLISHED">발행 표시</option><option value="DRAFT">초안</option><option value="REVIEW_PENDING">검토 대기</option></select></div>
         <div className="da-item-stack">{capFiltered.map(c=><button key={c.id} className={`da-select-item ${selectedCap.id===c.id?"active":""}`} onClick={()=>{selectCap(c.id);setDraftDescription(c.description);setDraftFeatureIds(c.featureIds)}}><div className="da-select-main"><strong>{c.title}</strong><small>{c.id} · v{c.version}</small></div><Pill tone={capTone[c.releaseState]}>{capLabel[c.releaseState]}</Pill><ChevronRight size={15}/></button>)}{!capFiltered.length&&<Empty>검색 결과가 없습니다.</Empty>}</div>
       </Card><Card className="da-pad"><SectionHead title="서비스 상세·해결범위" subtitle="기존 발행 버전은 직접 수정하지 않습니다." right={<Pill tone={capTone[selectedCap.releaseState]}>{capLabel[selectedCap.releaseState]}</Pill>}/>
         <div className="da-detail-header"><div className="da-square-icon"><Workflow size={21}/></div><div><strong>{selectedCap.title}</strong><small>{isTest?`${selectedCap.id} · v${selectedCap.version} · ${selectedCap.category}`:"대상 연결 대기"}</small></div></div>
         <Label name="서비스 설명"><textarea value={selectedCap.releaseState==="PUBLISHED"?selectedCap.description:draftDescription} readOnly={selectedCap.releaseState==="PUBLISHED"} onChange={e=>setDraftDescription(e.target.value)} rows={3}/></Label>
         <p className="da-field-title">포함된 Feature</p><div className="da-check-collection">{features.filter(f=>selectedCap.featureIds.includes(f.id)||(selectedCap.releaseState!=="PUBLISHED"&&f.catalogReady)).map(f=><label className="da-check-line" key={f.id}><input disabled={selectedCap.releaseState==="PUBLISHED"} type="checkbox" checked={selectedCap.releaseState==="PUBLISHED"?selectedCap.featureIds.includes(f.id):draftFeatureIds.includes(f.id)} onChange={e=>setDraftFeatureIds(arr=>e.target.checked?[...new Set([...arr,f.id])]:arr.filter(id=>id!==f.id))}/><span>{f.name} <small>({f.id})</small></span>{!f.catalogReady&&<Pill tone="warning">검증 필요</Pill>}</label>)}</div>
         <div className="da-info-grid"><InfoLine label="해결 대상" value={selectedCap.coverage.join(" · ")}/><InfoLine label="적용 조건" value={selectedCap.conditions.join(" · ")}/><InfoLine label="제외·제약" value={selectedCap.limitations.join(" · ")}/><InfoLine label="근거 문서" value={selectedCap.evidence||"근거 미확인"}/></div>
         <div className="da-action-row"><SafeAction navigation onClick={()=>go("publishing")}>버전·발행 확인 <ArrowRight size={15}/></SafeAction><SafeAction kind="primary" disabled={selectedCap.releaseState==="PUBLISHED"} onClick={saveDraft}><Check size={15}/> 개정안 내용 저장 (화면)</SafeAction></div>
       </Card></div>
     </>}

     {page==="publishing"&&<>
       <PageTitle kicker="PUBLISH & VERSION / M-04" title="서비스 버전·발행 관리" detail="서비스 근거·적용조건·Feature 검증 여부를 확인한 뒤, 기존 계약에 따른 발행을 검토합니다."/>
       <div className="da-split"><Card className="da-pad"><SectionHead title="검토 대상 서비스" subtitle="버전과 상태는 가상 자료 기준입니다."/><div className="da-item-stack">{capabilities.map(c=><button key={c.id} className={`da-select-item ${selectedCap.id===c.id?"active":""}`} onClick={()=>selectCap(c.id)}><div className="da-select-main"><strong>{c.title}</strong><small>{c.id} · v{c.version}</small></div><Pill tone={capTone[c.releaseState]}>{capLabel[c.releaseState]}</Pill></button>)}</div></Card>
       <Card className="da-pad"><SectionHead title="발행 검토" subtitle="발행 Guard는 최종적으로 서버의 승인된 계약을 따릅니다." right={<Pill tone={capTone[selectedCap.releaseState]}>v{selectedCap.version} · {capLabel[selectedCap.releaseState]}</Pill>}/>
         <div className="da-info-grid"><InfoLine label="대상 서비스" value={selectedCap.title}/><InfoLine label="연결 기능" value={`${selectedCap.featureIds.length}건`}/><InfoLine label="자료 증빙" value={selectedCap.evidence??"근거 없음"}/><InfoLine label="기존 발행 일자" value={selectedCap.publishedAt??"발행 전"}/></div>
         <div className="da-gate-list"><strong>사전 검토 항목</strong>{[{label:"서비스 근거 존재",ok:!!selectedCap.evidence},{label:"검증된 기능만 포함",ok:selectedCap.featureIds.length>0&&selectedCap.featureIds.every(id=>features.find(f=>f.id===id)?.catalogReady)},{label:"전제조건 명시",ok:selectedCap.conditions.length>0},{label:"기존 발행 버전 재발행 방지",ok:selectedCap.releaseState!=="PUBLISHED"}].map(v=><div key={v.label} className="da-gate-row"><span>{!isTest?<Info size={17}/>:v.ok?<CheckCircle2 size={17} className="da-ok"/>:<AlertCircle size={17} className="da-bad"/>}{v.label}</span><Pill tone={v.ok?"success":"warning"}>{v.ok?"확인":"미충족"}</Pill></div>)}</div>
         {guardReasons.length?<Alert warning>{guardReasons.join(" ")}</Alert>:<Alert>화면 예시상 기본 조건을 충족했습니다. 실제 서비스 발행 전 승인된 Role·Permission 및 FROZEN Guard를 서버에서 확인해야 합니다.</Alert>}
         <div className="da-action-row"><SafeAction onClick={newRevision}>신규 개정안 생성 <Plus size={15}/></SafeAction><SafeAction kind="primary" disabled={guardReasons.length>0} onClick={()=>setShowPublishConfirm(true)}>발행 상태 시뮬레이션 <ArrowRight size={15}/></SafeAction></div>
         <div className="da-history"><h3>버전·변경 이력</h3>{selectedCap.changeHistory.map((v,i)=><p key={i}><History size={13}/>{v}</p>)}</div>
       </Card></div>
     </>}

     {page==="notices"&&<>
       <PageTitle kicker="NOTICE MANAGEMENT / M-05" title="정부지원사업 공고 관리" detail="공고 원천, 지원기간, 개정·검토 상태를 확인합니다. 이 화면의 공고는 모두 가상입니다." actions={<Pill tone="warning">공식 공고와 구분 필요</Pill>}/>
       <div className="da-split"><Card className="da-pad"><SectionHead title="공고 목록" subtitle="공고명을 선택하여 상세내용을 확인합니다."/><div className="da-search"><Search size={17}/><input aria-label="공고 검색" value={search} onChange={e=>setSearch(e.target.value)} placeholder="공고명·기관 검색"/></div><div className="da-item-stack">{noticeFiltered.map(n=><button key={n.id} onClick={()=>setSelectedNoticeId(n.id)} className={`da-select-item ${selectedNotice.id===n.id?"active":""}`}><div className="da-select-main"><strong>{n.title}</strong><small>{n.agency} · v{n.version}</small></div><Pill tone={noticeTone[n.reviewStatus]}>{noticeLabel[n.reviewStatus]}</Pill></button>)}{!noticeFiltered.length&&<Empty>검색 조건에 맞는 공고가 없습니다.</Empty>}</div></Card>
       <Card className="da-pad"><SectionHead title="공고 상세" subtitle="가상 기관·공고를 공식 모집정보로 사용하지 않습니다."/><div className="da-detail-header"><div className="da-square-icon"><BookOpen size={21}/></div><div><strong>{selectedNotice.title}</strong><small>{selectedNotice.id}</small></div></div><div className="da-info-grid"><InfoLine label="공고기관" value={selectedNotice.agency}/><InfoLine label="공고 버전" value={`v${selectedNotice.version}`}/><InfoLine label="모집기간 예시" value={`${selectedNotice.from} ~ ${selectedNotice.to}`}/><InfoLine label="지원 지역" value={selectedNotice.region}/><InfoLine label="원천" value={selectedNotice.source}/><InfoLine label="공식 여부" value={<Pill tone="warning">공식 공고 아님</Pill>}/></div><div className="da-mini-list"><h3>요건 후보</h3>{selectedNotice.requirements.map(req=><div key={req.id}><strong>{req.title}</strong><span>{req.value}</span><Pill tone={req.status==="CANDIDATE"?"warning":"info"}>{req.status==="CANDIDATE"?"후보":"예시 검토"}</Pill></div>)}</div><div className="da-history"><h3>공고 Version 이력</h3>{selectedNotice.history.map((h,i)=><p key={i}>{h}</p>)}</div><div className="da-action-row"><SafeAction navigation kind="primary" onClick={()=>go("requirements")}>공고 요건 검토 <ArrowRight size={15}/></SafeAction></div></Card></div>
     </>}

     {page==="requirements"&&<>
       <PageTitle kicker="NOTICE REQUIREMENTS / M-06" title="공고 분석·요건 검토" detail="공고 원문 근거와 구조화된 지원자격 후보를 비교하고 검토 의견을 남깁니다."/>
       <Card className="da-pad"><div className="da-filter-row"><Label name="검토 공고"><select value={selectedNotice.id} onChange={e=>setSelectedNoticeId(e.target.value)}>{notices.map(n=><option value={n.id} key={n.id}>{n.title}</option>)}</select></Label><div className="da-source-warning"><ShieldQuestion size={18}/><span>{isTest?"모두 가상 공고입니다. 자격조건을 공식 확정하지 않습니다.":"데이터 연결 후 표시됩니다."}</span></div></div><div className="da-table-wrap"><table className="da-table"><thead><tr><th>조건 후보</th><th>비교규칙 유형</th><th>근거</th><th>검토</th></tr></thead><tbody>{selectedNotice.requirements.map(req=><tr key={req.id}><td><b>{req.title}</b><small>{req.value}</small></td><td>{req.comparator}</td><td>{req.evidence}</td><td><Pill tone={req.status==="CANDIDATE"?"warning":"info"}>{req.status==="CANDIDATE"?"추출 후보":"예시 검토"}</Pill></td></tr>)}</tbody></table></div><Label name="검토 메모"><textarea value={reviewNote} onChange={e=>setReviewNote(e.target.value)} placeholder={isTest?"가상 공고의 원문 근거와 미확인 조건 등을 기록하세요.":"검토할 공고 연결 후 입력할 수 있습니다."} rows={3}/></Label><div className="da-action-row">{!selectedNotice.requirements.length&&<SafeAction disabled>요건 검토</SafeAction>}{selectedNotice.requirements.filter(r=>r.status==="CANDIDATE").map(r=><SafeAction key={r.id} onClick={()=>markRequirement(r.id)}><Check size={15}/>{r.title} 예시 검토</SafeAction>)}</div><Alert warning>요건 비교 결과와 운영자의 검토 메모는 신청자격 확정 또는 정부기관 승인과 다릅니다. R-07 비교불가 조건은 자동 충족 처리하지 않습니다.</Alert></Card>
     </>}

     {page==="users"&&<>
       <PageTitle kicker="USER MANAGEMENT / M-07" title="사용자·계정 관리" detail="수요기업·운영자·관리자 계정을 구분해 확인하고 실제 권한 변경은 별도 승인 절차로 분리합니다."/>
       <div className="da-split"><Card className="da-pad"><SectionHead title="사용자 목록" subtitle="설명용 계정만 포함됩니다."/><div className="da-item-stack">{users.map(u=><button key={u.id} onClick={()=>setSelectedUserId(u.id)} className={`da-select-item ${selectedUser.id===u.id?"active":""}`}><div className="da-avatar-small"><UserRound size={16}/></div><div className="da-select-main"><strong>{u.name}</strong><small>{u.email}</small></div><Pill tone="info">{u.role.replaceAll("_"," ")}</Pill></button>)}</div></Card><Card className="da-pad"><SectionHead title="계정 상세" subtitle="실제 DMP SSO/권한 저장소는 연결되어 있지 않습니다."/><div className="da-detail-header"><div className="da-square-icon"><Users size={21}/></div><div><strong>{selectedUser.name}</strong><small>{selectedUser.id}</small></div></div><div className="da-info-grid"><InfoLine label="이메일" value={selectedUser.email}/><InfoLine label="역할 구분" value={selectedUser.role}/><InfoLine label="활성 상태" value={selectedUser.status}/><InfoLine label="최근 접속(예시)" value={selectedUser.lastSeen}/><InfoLine label="기업 접근 범위" value={selectedUser.scopeCompanyIds.length?selectedUser.scopeCompanyIds.map(titleOfCompany).join(", "):"별도 기업 지정 없음"}/><InfoLine label="운영 설명" value={selectedUser.notes}/></div><Alert>관리자라는 이유만으로 Fact 확인, MatchReview, Proposal 승인권한이 자동 부여되지는 않습니다.</Alert><SafeAction navigation kind="primary" onClick={()=>go("access")}>접근범위 확인 <ArrowRight size={15}/></SafeAction></Card></div>
     </>}

     {page==="access"&&<>
       <PageTitle kicker="ACCESS CONTROL / M-08" title="권한·기업 접근범위" detail="Role·Permission·Company Scope를 구분해 확인하고, 권한 변경은 요청으로만 기록합니다."/>
       <div className="da-columns"><Card className="da-pad"><SectionHead title={isTest?"현재 예시 접근 현황":"기업 접근 현황"} subtitle="운영환경의 실제 권한이 아닙니다."/><div className="da-table-wrap"><table className="da-table"><thead><tr><th>계정</th><th>역할</th><th>기업 접근범위</th></tr></thead><tbody>{users.map(u=><tr key={u.id} tabIndex={0} role="button" aria-label={u.name+" 접근범위 선택"} onKeyDown={e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();setSelectedUserId(u.id)}}} onClick={()=>setSelectedUserId(u.id)} className={selectedUser.id===u.id?"selected":""}><td><b>{u.name}</b><small>{u.id}</small></td><td>{u.role}</td><td>{u.scopeCompanyIds.length?u.scopeCompanyIds.map(titleOfCompany).join(" · "):"별도 기업 없음"}</td></tr>)}</tbody></table></div></Card><Card className="da-pad"><SectionHead title="접근 검토 요청" subtitle="직접 권한 부여 없이 업무 요청만 보존합니다."/>
         <Label name="대상 사용자"><select value={selectedUser.id} onChange={e=>setSelectedUserId(e.target.value)}>{users.map(u=><option key={u.id} value={u.id}>{u.name} ({u.role})</option>)}</select></Label>
         <Label name="검토 대상 기업"><select value={accessCompany} onChange={e=>setAccessCompany(e.target.value)}>{sample.companies.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></Label>
         <Label name="요청 사유"><textarea value={accessIntent} onChange={e=>setAccessIntent(e.target.value)} rows={3}/></Label><SafeAction kind="primary" onClick={submitAccess} disabled={selectedUser.role==="DATCO_ADMIN"}><Send size={15}/> 접근 검토 요청 기록</SafeAction>
         <div className="da-mini-list"><h3>이번 세션에 작성된 요청</h3>{accessRequests.length===0?<p className="da-mini-empty">{isTest?"작성된 요청 없음":"요청 이력 연결 대기"}</p>:accessRequests.map(r=><div key={r.id}><strong>{users.find(u=>u.id===r.userId)?.name}</strong><span>{titleOfCompany(r.companyId)} · {r.intent}</span><Pill tone="warning">승인 전</Pill></div>)}</div><Alert warning>요청 버튼은 회사 사용자·운영자의 조회 권한을 변경하지 않습니다. 실제 변경은 기존 승인된 Membership/Permission 계약과 서버 검증에 따릅니다.</Alert></Card></div>
     </>}

     {page==="analysis"&&<>
       <PageTitle kicker="AI & PARSER OPERATIONS / M-09" title="AI 분석 운영관리" detail="문서 파싱, 규칙 기반 추출, 실제 AI, 수동 검토와 미지원 처리를 구분해 확인합니다." actions={<Pill tone="warning">외부 AI 실연동 없음</Pill>}/>
       <div className="da-filter-row da-filter-top"><div className="da-filter-label"><Activity size={17}/> 실행 이력 {isTest?`${jobs.length}건`:"—"}</div><select value={jobFilter} onChange={e=>setJobFilter(e.target.value)}><option value="전체">전체 결과</option><option value="SUCCESS">처리됨</option><option value="FAILED">실패</option><option value="BLOCKED">정책 차단</option></select></div>
       <div className="da-split"><Card className="da-pad"><SectionHead title="분석·파싱 실행 목록" subtitle="실행 레코드는 예시 데이터입니다."/><div className="da-item-stack">{jobFiltered.map(j=><button key={j.id} onClick={()=>setSelectedJobId(j.id)} className={`da-select-item ${selectedJob.id===j.id?"active":""}`}><div className="da-select-main"><strong>{j.task}</strong><small>{titleOfCompany(j.companyId)} · {j.startedAt}</small></div><Pill tone={jobTone[j.status]}>{jobLabel[j.status]}</Pill></button>)}{!jobFiltered.length&&<Empty>해당 결과의 실행 기록이 없습니다.</Empty>}</div></Card><Card className="da-pad"><SectionHead title="실행 상세" subtitle="분석 방식과 차단 사유를 구분합니다."/>
         <div className="da-detail-header"><div className="da-square-icon"><Sparkles size={21}/></div><div><strong>{selectedJob.task}</strong><small>{selectedJob.id}</small></div></div><div className="da-info-grid"><InfoLine label="처리 방식" value={selectedJob.mode}/><InfoLine label="Engine / Provider" value={selectedJob.engine}/><InfoLine label="결과" value={<Pill tone={jobTone[selectedJob.status]}>{jobLabel[selectedJob.status]}</Pill>}/><InfoLine label="시도 횟수" value={selectedJob.attempt}/><InfoLine label="입력 근거" value={selectedJob.evidence}/><InfoLine label="설명" value={selectedJob.note}/></div>
         <Alert warning>실제 승인된 AI Provider가 없으면 모델 추론 성공으로 표시하지 않습니다. 이미지·스캔 OCR 미지원은 수동 검토로 연결합니다.</Alert>
         <SafeAction onClick={()=>{log("AI_RETRY_INSPECTION",selectedJob.id,"재시도 조건 검토(호출 없음)");show("재시도 조건을 확인했습니다. 승인된 Provider·모델이 없으므로 외부 AI를 호출하지 않았습니다.")}}><RefreshCw size={15}/> 재시도 가능 여부 점검</SafeAction>
       </Card></div>
     </>}

     {page==="quality"&&<>
       <PageTitle kicker="DATA QUALITY / M-10" title="데이터 품질·처리 현황" detail="근거 누락, 미지원 분석, 버전 현재성 및 비교 불가능한 조건을 별도로 관리합니다."/>
       <div className="da-split"><Card className="da-pad"><SectionHead title="확인 필요 데이터" subtitle="미확인은 자동으로 위험 또는 실패 판정이 아닙니다."/><div className="da-item-stack">{issues.map(i=><button key={i.id} onClick={()=>{setSelectedIssueId(i.id)}} className={`da-select-item ${selectedIssue.id===i.id?"active":""}`}><div className="da-select-main"><strong>{i.issue}</strong><small>{i.targetId} · {i.kind}</small></div><Pill tone="warning">확인 필요</Pill></button>)}</div></Card><Card className="da-pad"><SectionHead title="품질 항목 상세" subtitle="담당과 보완 근거는 실제 운영에서 확정해야 합니다."/><div className="da-detail-header"><div className="da-square-icon"><ShieldAlert size={21}/></div><div><strong>{selectedIssue.issue}</strong><small>{selectedIssue.id}</small></div></div><div className="da-info-grid"><InfoLine label="대상 객체" value={selectedIssue.entityType}/><InfoLine label="식별자" value={selectedIssue.targetId}/><InfoLine label="확인 유형" value={selectedIssue.kind}/><InfoLine label="담당" value={selectedIssue.owner}/><InfoLine label="권장 보완" value={selectedIssue.next}/></div><p className="da-saved-quality">{isTest?`저장된 화면 메모: ${savedReviewNotes[selectedIssue.id] ?? "없음"}`:"검토 메모 연결 대기"}</p><Label name="검토 메모"><textarea rows={4} value={reviewNote} onChange={e=>setReviewNote(e.target.value)} placeholder="확인한 사실 또는 추가 검토사항을 적어주세요."/></Label><SafeAction kind="primary" onClick={saveMemo}><Check size={15}/> 메모 저장 (화면)</SafeAction><Alert>근거 확인 없이 품질 문제를 해결 완료로 처리하지 않습니다. 해당 상태는 현재 예시 그대로 유지됩니다.</Alert></Card></div>
     </>}

     {page==="integrations"&&<>
       <PageTitle kicker="SYSTEM INTEGRATIONS / M-11" title="DMP 및 외부 연동관리" detail="향후 실제 DMP SSO, 기능 Catalog, AI Provider 및 자료 저장소 연결에 필요한 인터페이스를 확인합니다." actions={<Pill tone="warning">실제 연결 수행 안 함</Pill>}/>
       <div className="da-split"><Card className="da-pad"><SectionHead title="연동 대상" subtitle="운영 상태가 아니라 개발 인계 현황입니다."/><div className="da-item-stack">{integrations.map(it=><button key={it.id} onClick={()=>{setSelectedIntegrationId(it.id);setIntegrationDiagnostic(null)}} className={`da-select-item ${selectedIntegration.id===it.id?"active":""}`}><div className="da-select-main"><strong>{it.name}</strong><small>{it.category} · {it.id}</small></div><Pill tone="warning">{it.status==="BLOCKED_BY_POLICY"?"정책 확인":"미연결"}</Pill></button>)}</div></Card><Card className="da-pad"><SectionHead title="연동 상세" subtitle="확인 대상과 인계 전제조건을 표시합니다."/><div className="da-detail-header"><div className="da-square-icon"><Link2 size={21}/></div><div><strong>{selectedIntegration.name}</strong><small>{selectedIntegration.desc}</small></div></div><div className="da-info-grid"><InfoLine label="연동 상태" value={selectedIntegration.status}/><InfoLine label="관리 책임" value={selectedIntegration.owner}/></div><div className="da-checklist"><h3>필요한 확인사항</h3>{selectedIntegration.prerequisites.map(p=><div key={p}><AlertCircle size={16}/><span>{p}</span></div>)}</div><div className="da-action-row"><SafeAction onClick={()=>{setIntegrationDiagnostic(selectedIntegration.id);log("INTEGRATION_CHECKLIST_OPEN",selectedIntegration.id,"연동 선행조건 표시(외부 연결 없음)")}}><Eye size={15}/> 연동 준비사항 확인</SafeAction></div>{integrationDiagnostic===selectedIntegration.id&&<Alert warning>연동 준비사항만 표시했습니다. 실제 서버, SSO, DMP API 또는 외부 AI에 연결하지 않았습니다.</Alert>}</Card></div>
     </>}

     {page==="audit"&&<>
       <PageTitle kicker="AUDIT & HISTORY / M-12" title="감사·변경 이력" detail="기준정보 조회, 시연 변경 요청과 중요 행위를 원천·시각·대상과 함께 확인합니다."/>
       <Card className="da-pad"><div className="da-section-head"><div><h2>작업 이력 {isTest?`${audit.length}건`:""}</h2><p>화면 상호작용은 실제 서버 감사 로그가 아닙니다.</p></div><div className="da-search"><Search size={16}/><input aria-label="감사 이력 검색" value={auditFilter} placeholder="대상·행위·내용 검색" onChange={e=>setAuditFilter(e.target.value)}/></div></div><div className="da-table-wrap"><table className="da-table"><thead><tr><th>발생 시각</th><th>행위</th><th>대상</th><th>주체·출처</th></tr></thead><tbody>{auditFiltered.map(a=><React.Fragment key={a.id}><tr tabIndex={0} role="button" aria-label={a.action+" 이력 상세"} onKeyDown={e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();setShowAuditDetails(showAuditDetails===a.id?null:a.id)}}} onClick={()=>setShowAuditDetails(showAuditDetails===a.id?null:a.id)}><td>{a.at}</td><td><b>{a.action}</b><small>{a.detail}</small></td><td>{a.target}</td><td>{a.actor}<small>{a.source==="LOCAL_UI_ONLY"?"프런트 로컬 상태":"가상 Fixture"}</small></td></tr>{showAuditDetails===a.id&&<tr><td colSpan={4} className="da-audit-expanded">행위 상세: {a.detail} · 기록 ID: {a.id}</td></tr>}</React.Fragment>)}</tbody></table>{auditFiltered.length===0&&<Empty>조건에 맞는 기록이 없습니다.</Empty>}</div></Card>
       <Alert>운영환경에서는 서버 인증 Actor, 대상 Company Scope, 시간, 이전/새 Version, 요청 ID 등 검증된 Audit 계약으로 기록해야 합니다. 이 목록은 이를 대신하지 않습니다.</Alert>
     </>}

     </Availability.Provider>
     <footer className="da-footer"><span>DATCO ONE · 관리자 포털 기준 화면</span><span>데이터 연결 전 · 저장·발행·권한 변경 미연결</span></footer>
   </div></main></div>
  {showPublishConfirm&&<div className="da-modal-mask" role="presentation"><div className="da-modal" role="dialog" aria-modal="true" aria-label="가상 발행 상태 확인"><div className="da-modal-icon"><ShieldQuestion size={23}/></div><h2>서비스 버전의 화면상 발행 상태를 변경할까요?</h2><p><b>{selectedCap.title} v{selectedCap.version}</b>에 대한 예시 처리입니다. 실제 발행 API·권한검증·승인 기록은 수행하지 않습니다.</p><div className="da-action-row da-align-right"><SafeAction onClick={()=>setShowPublishConfirm(false)}>취소</SafeAction><SafeAction kind="primary" onClick={publishSample}>화면에만 반영</SafeAction></div></div></div>}
 </div>;
}

function usePreviewNavigation(){
 const [page,setPage]=useState<Page>("dashboard");
 const [history,setHistory]=useState<Page[]>([]);
 return {page,canBack:history.length>0,go:(next:Page)=>{if(next!==page){setHistory(h=>[...h,page]);setPage(next);}},back:()=>{const prev=history.at(-1);if(prev){setPage(prev);setHistory(h=>h.slice(0,-1));}}};
}
const PURPOSES:Record<Page,string>={dashboard:"기준정보 현황과 확인 필요 업무",features:"DMP 기능 검색·Revision 및 근거 확인",capabilities:"서비스·Feature 연결·해결범위와 개정안",publishing:"발행조건·차단 사유·Version 이력",notices:"공고 검색·원문·Version",requirements:"Requirement·Evidence·Comparator 검토",users:"계정별 역할과 상세정보",access:"기업 Scope·Membership·변경 검토 요청",analysis:"분석 방식·실행 이력·오류·정책 차단",quality:"근거 누락·Version 충돌·검토 의견",integrations:"SSO·DMP·AI·공고·File Storage 준비사항",audit:"Actor·Action·Target·시각·변경내역 조회"};
const BLANK = {
 feature:{id:"",name:"기능 선택",category:"",description:"",revision:"",capabilityId:"",catalogReady:false,source:"",evidence:"",updatedAt:""} as Feature,
 cap:{id:"",title:"서비스 선택",description:"",category:"",version:0,releaseState:"DRAFT",featureIds:[],conditions:[],coverage:[],limitations:[],evidence:null,publishedAt:null,changeHistory:[],authorizationHint:""} as Capability,
 notice:{id:"",title:"공고 선택",agency:"",round:"",region:"",version:0,reviewStatus:"CANDIDATE",from:"",to:"",official:false,source:"",sourceType:"",requirements:[],history:[]} as Notice,
 user:{id:"",name:"사용자 선택",email:"",role:"",status:"",scopeCompanyIds:[],lastSeen:"",notes:""} as User,
 job:{id:"",companyId:"",task:"분석 실행 선택",mode:"",engine:"",status:"BLOCKED",startedAt:"",durationMs:0,evidence:"",attempt:0,note:""} as AIRun,
 issue:{id:"",entityType:"",targetId:"",issue:"품질 항목 선택",kind:"",status:"",owner:"",next:""} as QualityIssue,
 integration:{id:"",name:"연동 대상 선택",category:"",status:"",desc:"",prerequisites:[],owner:""} as Integration,
};
const DISCONNECTED:Fixture={schemaVersion:"",dataNature:"",admin:{id:"",displayName:"",roleLabel:""},features:[],capabilities:[],notices:[],users:[],companies:[],aiRuns:[],qualityIssues:[],integrations:[],audit:[]};
export default function AdminPortal({testData}:{testData?:AdminPreviewData}){
 const [started,setStarted]=useState(false);
 const logout=()=>setStarted(false);
 if(!started)return <div className="datco-admin da-auth-layout"><div className="da-brand-side"><div className="da-auth-logo"><Layers3 size={24}/><strong>DATCO ONE</strong></div><div className="da-brand-hero"><small>SYSTEM ADMINISTRATION PORTAL</small><h1>더 정확한 기준,<br/>더 신뢰할 수 있는 운영.</h1><p>기준정보·사용자 접근범위·분석품질을 검토하는 관리자 화면</p></div></div><main className="da-login-stage"><div className="da-login-card"><div className="da-login-icon"><LockKeyhole size={24}/></div><h2>관리자 UI 미리보기</h2><p>실제 로그인·인증 없이 화면을 확인합니다.</p><SafeAction kind="primary" onClick={()=>setStarted(true)}>미리보기 시작 <ArrowRight size={16}/></SafeAction></div></main></div>;
 return <AdminWorkspace sample={testData??DISCONNECTED} isTest={testData!==undefined} onLogout={logout}/>;
}
