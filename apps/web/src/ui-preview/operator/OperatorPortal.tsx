"use client";

/**
 * DATCO ONE — 운영자 업무 포털 UI 참조 구현.
 * THIS IS A DESIGN/INTERACTION REFERENCE, NOT A PRODUCTION AUTHORIZATION OR DATA STORE.
 * All fixtures are fictional. Changes live only in React component state.
 * Existing backend FROZEN policies/Role/Scope/Guard must govern integration.
 */
import React, { useMemo, useState } from "react";
import { AlertCircle, ArrowRight, BriefcaseBusiness, Building2, CalendarClock, Check, CheckCircle2, ChevronDown, ChevronRight, ClipboardCheck, ClipboardList, Download, FileCheck2, FileClock, FileSearch, FileText, FileWarning, FolderOpen, Layers3, LayoutDashboard, LockKeyhole, LogOut, Menu, MessageSquareText, Plus, RefreshCw, Search, Send, ShieldCheck, Sparkles, Workflow, X } from "lucide-react";
import fixture from "./operatorFixture.json";
import "./operator-portal.css";

type Page =
  | "dashboard" | "companies" | "workspace" | "facts" | "improvement"
  | "recommendations" | "compositions" | "grants" | "matching" | "requests"
  | "proposals" | "delivery";
type FactStatus = "PENDING" | "CONFIRMED" | "REJECTED";
type Elig = "MATCH" | "UNKNOWN" | "MISMATCH";
type MatchStatus = "PROPOSABLE" | "BLOCKED" | "MISMATCH" | "REVIEW_REQUIRED";
type Fact = { id: string; label: string; value: string; period: string; evidenceId: string; source: string; status: FactStatus; actor: string | null; version: number };
type Document = { id: string; name: string; type: string; size: string; submittedBy: string; submittedAt: string; source: string; excerpt: string; version: number; privacy: string; status: string };
type Capability = { id: string; title: string; version: string; features: string[]; coverage: string[]; limitations: string[]; reason: string; source: string };
type Composition = { id: string; title: string; capabilityIds: string[]; coverage: string; unresolved: string[]; note: string };
type Criterion = { name: string; state: Elig; reason: string };
type Grant = { id: string; title: string; organization: string; period: string; rationale: string; eligibility: Criterion[]; source: string };
type Improvement = { id: string; version: number; title: string; asis: string; tobe: string; constraints: string; problems: string[]; reviewed: boolean };
type Proposal = { id: string; version: number; title: string; body: string; reviewed: boolean; deliveredVersion: number | null; recipient: string };
type Company = {
  id: string; name: string; siteId: string; site: string; industry: string; address: string; companyUser: string; businessNo: string;
  stage: string; owner: string; lastUpdated: string; requestCount: number;
  improvement: Improvement; documents: Document[]; facts: Fact[];
  capabilities: Capability[]; compositions: Composition[]; grants: Grant[];
  matching: { status: MatchStatus; criteria: Criterion[]; reviewNote: string }; proposal: Proposal;
};
type Log = { id: string; companyId: string; at: string; text: string; type: string };
type SupplementRequest = { id: string; companyId: string; text: string; status: "작성" | "보완 대기" | "화면상 완료"; at: string };
type Tone = "slate" | "blue" | "green" | "amber" | "red" | "purple";
const COMPANIES = fixture.companies as unknown as Company[];
const links: Array<{ section: string; pages: Array<{ id: Page; name: string; Icon: typeof LayoutDashboard }> }> = [
  { section: "업무 시작", pages: [
    { id: "dashboard", name: "업무 대시보드", Icon: LayoutDashboard },
    { id: "companies", name: "수요기업 목록", Icon: Building2 },
    { id: "workspace", name: "기업 통합 업무", Icon: Layers3 },
  ] },
  { section: "기업·문제 검토", pages: [
    { id: "facts", name: "기업자료·Fact 검토", Icon: FileSearch },
    { id: "improvement", name: "개선요구 검토", Icon: ClipboardList },
  ] },
  { section: "추천·매칭", pages: [
    { id: "recommendations", name: "DATCO 서비스 추천", Icon: Sparkles },
    { id: "compositions", name: "서비스 조합 검토", Icon: Workflow },
    { id: "grants", name: "정부지원사업 추천", Icon: BriefcaseBusiness },
    { id: "matching", name: "매칭·자격 검토", Icon: ClipboardCheck },
    { id: "requests", name: "보완자료 요청", Icon: MessageSquareText },
  ] },
  { section: "제안·전달", pages: [
    { id: "proposals", name: "맞춤형 제안서", Icon: FileCheck2 },
    { id: "delivery", name: "전달·검토 이력", Icon: FileClock },
  ] },
];
const quickStages: Array<{ name: string; page: Page }> = [
  { name: "기업자료", page: "facts" },
  { name: "개선요구", page: "improvement" },
  { name: "서비스 추천", page: "recommendations" },
  { name: "사업 매칭", page: "matching" },
  { name: "제안서", page: "proposals" },
];
const statusTone: Record<Elig, Tone> = { MATCH: "green", UNKNOWN: "amber", MISMATCH: "red" };
const statusName: Record<Elig, string> = { MATCH: "충족 후보", UNKNOWN: "확인 필요", MISMATCH: "불일치" };
const factName: Record<FactStatus, string> = { PENDING: "근거 검토 대기", CONFIRMED: "확인됨", REJECTED: "보완 필요" };
const today = () => new Date().toLocaleString("ko-KR", { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
const idGen = (prefix: string) => `${prefix}-${Date.now()}-${Math.floor(Math.random() * 999)}`;

function Pill({ children, tone = "slate" }: { children: React.ReactNode; tone?: Tone }) {
  return <span className={`op-pill op-pill-${tone}`}>{children}</span>;
}
function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <section className={`op-card ${className}`}>{children}</section>;
}
function Heading({ eyebrow, title, desc, right }: { eyebrow: string; title: string; desc: string; right?: React.ReactNode }) {
  return <div className="op-heading"><div><div className="op-eyebrow">{eyebrow}</div><h1>{title}</h1><p>{desc}</p></div>{right}</div>;
}
function Empty({ title, detail }: { title: string; detail?: string }) {
  return <div className="op-empty"><FolderOpen size={26} /><strong>{title}</strong>{detail && <span>{detail}</span>}</div>;
}
function Meta({ label, value }: { label: string; value: React.ReactNode }) {
  return <div className="op-meta"><span>{label}</span><strong>{value}</strong></div>;
}
function Explain({ children, kind = "info" }: { children: React.ReactNode; kind?: "info" | "warning" }) {
  return <div className={`op-explain op-explain-${kind}`}><AlertCircle size={16} />{children}</div>;
}
function SectionTitle({ title, sub, action }: { title: string; sub?: string; action?: React.ReactNode }) {
  return <div className="op-section-head"><div><h2>{title}</h2>{sub && <p>{sub}</p>}</div>{action}</div>;
}

export default function OperatorPortal() {
  const [signedIn, setSignedIn] = useState(false);
  const [page, setPage] = useState<Page>("dashboard");
  const [mobileNav, setMobileNav] = useState(false);
  const [records, setRecords] = useState<Company[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [query, setQuery] = useState("");
  const [companyFilter, setCompanyFilter] = useState("전체");
  const [selectedEvidence, setSelectedEvidence] = useState<Document | null>(null);
  const [toast, setToast] = useState("");
  const [audit, setAudit] = useState<Log[]>([]);
  const [requests, setRequests] = useState<SupplementRequest[]>([]);
  const [requestReturn, setRequestReturn] = useState<Page>("workspace");
  const [siteIndex, setSiteIndex] = useState(0);
  const [taskIndex, setTaskIndex] = useState(0);
  const [contextRecords, setContextRecords] = useState<Record<string, Company>>({});
  const [newRequest, setNewRequest] = useState("사업장·지원자격 확인에 필요한 추가자료를 제출해 주세요.");
  const [selectedCapabilities, setSelectedCapabilities] = useState<Record<string, string[]>>({ "COMP-001": ["CAP-INV", "CAP-PROD", "CAP-QUAL"], "COMP-002": ["CAP-MAINT"] });
  const [selectedComposition, setSelectedComposition] = useState<Record<string, string>>({ "COMP-002": "COMP-C" });
  const [selectedGrant, setSelectedGrant] = useState<Record<string, string>>({ "COMP-002": "GR-003" });
  const [editedImprovement, setEditedImprovement] = useState<Record<string, string>>({});
  const [proposalEditor, setProposalEditor] = useState<Record<string, string>>({});
  const [showLogout, setShowLogout] = useState(false);
  const baseCompany = records.find((r) => r.id === selectedId) ?? records[0];
  const contextKey = `${baseCompany?.id ?? "empty"}:${siteIndex}:${taskIndex}`;
  const current = contextRecords[contextKey] ?? (baseCompany ? contextExample(baseCompany, siteIndex, taskIndex) : EMPTY_COMPANY);
  const pendingFacts = current.facts.filter((f) => f.status !== "CONFIRMED");
  const eligibilityBlockers = current.matching.criteria.filter((e) => e.state !== "MATCH");
  const safeToPropose = current.matching.status === "PROPOSABLE" && pendingFacts.length === 0 && eligibilityBlockers.length === 0;
  const chosenComp = current.compositions.find((x) => x.id === selectedComposition[contextKey]) ?? null;
  const chosenGrant = current.grants.find((x) => x.id === selectedGrant[contextKey]) ?? null;
  const proposalText = proposalEditor[contextKey] ?? current.proposal.body;
  const currentRequests = requests.filter((x) => x.companyId === contextKey);
  const currentAudit = audit.filter((x) => x.companyId === contextKey);
  const dashboardCounts = useMemo(() => ({
    companies: records.length,
    facts: records.reduce((acc, company) => acc + company.facts.filter((f) => f.status !== "CONFIRMED").length, 0),
    blocked: records.filter((x) => x.matching.status !== "PROPOSABLE").length,
    proposals: records.filter((x) => x.proposal.version > 0).length,
  }), [records]);
  const companiesFiltered = useMemo(() => records.filter((x) => {
    const term = query.trim().toLowerCase();
    const ok = !term || [x.name, x.industry, x.improvement.title, x.site].some((v) => v.toLowerCase().includes(term));
    return ok && (companyFilter === "전체" || x.stage === companyFilter);
  }), [query, records, companyFilter]);

  const notify = (message: string) => setToast(message);
  const navigate = (next: Page) => { setPage(next); setToast(""); setMobileNav(false); setShowLogout(false); };
  const chooseCompany = (companyId: string, next: Page = "workspace") => { setSelectedId(companyId); setSiteIndex(0); setTaskIndex(0); setSelectedEvidence(null); setNewRequest(""); navigate(next); };
  const updateCompany = (fn: (c: Company) => Company) => setContextRecords((prev) => ({ ...prev, [contextKey]: fn(current) }));
  const logAction = (type: string, text: string) => setAudit((prev) => [{ id: idGen("LOG"), companyId: contextKey, at: today(), type, text }, ...prev]);
  const logOut = () => { setSignedIn(false); setShowLogout(false); clearExamples(); };
  const openRequest = () => { setRequestReturn(page); navigate("requests"); };
  const reviewFact = (id: string, status: FactStatus) => {
    updateCompany((c) => ({ ...c, facts: c.facts.map((f) => f.id === id ? { ...f, status, actor: "DATCO 운영자 · 화면 검토 예시" } : f) }));
    logAction("Fact 검토", `${id} → ${factName[status]} (로컬 화면 시뮬레이션)`);
    notify("Fact 검토 결과가 화면에 반영됐습니다. 실제 FactVersion 확정·권한 처리는 연동되지 않았습니다.");
  };
  const saveImprovement = () => {
    const tobe = editedImprovement[contextKey] ?? current.improvement.tobe;
    updateCompany((c) => ({ ...c, improvement: { ...c.improvement, tobe, reviewed: true } }));
    logAction("개선요구", `개선요구 검토 예시 저장 (${current.improvement.id})`);
    notify("개선요구 검토 결과를 화면에 반영했습니다. 실제 ImprovementVersion 승인은 별도입니다.");
  };
  const toggleCapability = (id: string) => setSelectedCapabilities((prev) => {
    const items = prev[current.id] ?? [];
    return { ...prev, [contextKey]: items.includes(id) ? items.filter((x) => x !== id) : [...items, id] };
  });
  const selectComposition = (id: string) => {
    setSelectedComposition((prev) => ({ ...prev, [contextKey]: id }));
    logAction("서비스 조합", `${id} 선택 예시 (최종 CompositionVersion 발행 아님)`);
    notify("서비스 조합 후보를 선택했습니다. 운영 계약의 검토·발행 절차는 아직 연결되지 않았습니다.");
  };
  const requestSupplement = () => {
    if (!newRequest.trim()) { notify("요청할 자료나 확인사항을 입력해 주세요."); return; }
    setRequests((prev) => [{ id: idGen("REQ"), companyId: contextKey, text: newRequest.trim(), status: "작성", at: today() }, ...prev]);
    logAction("자료 보완", "기업 보완 요청 문안 작성 (외부 전송 없음)");
    notify("자료보완 요청이 시연 화면의 요청함에 작성되었습니다. 수요기업에게 전송되지 않았습니다.");
  };
  const reviewMatch = () => {
    if (pendingFacts.length > 0 || eligibilityBlockers.length > 0) {
      logAction("매칭 검토", "미확인 또는 불일치 조건으로 제안 가능 전환 차단");
      notify("Fact·공고조건에 확인되지 않은 항목이 남아 있어 제안 가능 상태로 변경하지 않았습니다.");
      return;
    }
    if (current.matching.status !== "PROPOSABLE") {
      notify("기존 FROZEN MatchReview 계약을 확인하지 않고 화면에서 PROPOSABLE로 변경할 수 없습니다.");
      return;
    }
    logAction("매칭 검토", "사전 검증된 제안 가능 결과 재확인 (예시)");
    notify("가상 시나리오에서 사전 검증된 MatchReview 결과를 확인했습니다.");
  };
  const createProposal = () => {
    if (!safeToPropose) { notify("매칭이 제안 가능 상태가 아니므로 제안서를 생성하지 않았습니다."); return; }
    const comp = chosenComp?.title ?? current.compositions[0]?.title ?? "검토된 솔루션";
    const grant = chosenGrant?.title ?? current.grants[0]?.title ?? "지원사업 검토 필요";
    const body = `1. 기업 현황\n${current.name} / ${current.site}\n\n2. 현재 문제 (As-Is)\n${current.improvement.asis}\n\n3. 개선목표 (To-Be)\n${current.improvement.tobe}\n\n4. DATCO 서비스 구성\n${comp}\n\n5. 정부지원사업 검토\n${grant}\n\n6. 전제조건\n${current.improvement.constraints}\n\n※ 모든 내용은 가상 데이터 기반이며 실제 공고·서비스 검토가 아닙니다.`;
    updateCompany((c) => ({ ...c, proposal: { ...c.proposal, version: c.proposal.version + 1, body, reviewed: false, deliveredVersion: null } }));
    setProposalEditor((p) => ({ ...p, [contextKey]: body }));
    logAction("제안서", "가상 데이터로 신규 제안서 버전 생성 (실제 Proposal API 미연동)");
    notify("제안서 초안을 새 버전으로 생성했습니다. 내용 검토 후 전달할 수 있습니다.");
  };
  const saveProposal = () => {
    if (!current.proposal.version) { notify("먼저 제안서 초안을 생성해 주세요."); return; }
    if (!safeToPropose) { notify("제안 가능 조건이 충족되지 않습니다. 문서를 저장하지 않았습니다."); return; }
    updateCompany((c) => ({ ...c, proposal: { ...c.proposal, version: c.proposal.version + 1, body: proposalText, reviewed: false, deliveredVersion: null } }));
    logAction("제안서", "제안서 수정 저장: 새 버전 생성, 이전 검토·전달 현재성 무효화 예시");
    notify("새 ProposalVersion을 생성했습니다. 변경된 버전은 재검토가 필요합니다.");
  };
  const reviewProposal = () => {
    if (!safeToPropose || current.proposal.version < 1) { notify("매칭 검토 및 제안서 생성 이후에만 내용 검토할 수 있습니다."); return; }
    updateCompany((c) => ({ ...c, proposal: { ...c.proposal, reviewed: true } }));
    logAction("제안서", `제안서 v${current.proposal.version} 내용 검토 표시 (화면상)`);
    notify("현재 버전의 제안서 내용 검토 결과를 화면에 반영했습니다.");
  };
  const recordDelivery = () => {
    if (!safeToPropose || current.proposal.version === 0 || !current.proposal.reviewed) {
      notify("제안 가능 MatchReview 및 현 버전의 내용 검토가 필요합니다."); return;
    }
    updateCompany((c) => ({ ...c, proposal: { ...c.proposal, deliveredVersion: c.proposal.version } }));
    logAction("전달 시나리오", `제안서 v${current.proposal.version} → ${current.proposal.recipient} (화면상 전달 이력, 실제 전송 없음)`);
    notify("화면에 전달 시나리오를 기록했습니다. 실제 수요기업 포털이나 외부 채널로 전송하지 않았습니다.");
  };
  const downloadProposal = () => {
    if (current.proposal.version < 1) { notify("생성된 제안서가 없습니다."); return; }
    const text = `DATCO ONE | 제안서 v${current.proposal.version} (가상 자료)\n회사: ${current.name}\n\n${current.proposal.body}`;
    const blob = new Blob(["\ufeff", text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob); const anchor = document.createElement("a"); anchor.href = url; anchor.download = `DATCO_제안서_${current.id}_v${current.proposal.version}_예시.txt`;
    anchor.click(); URL.revokeObjectURL(url);
    notify("텍스트 기반 예시 파일을 생성했습니다. 실제 DOCX/PDF는 기존 Proposal 엔진 연동이 필요합니다.");
  };
  const clearExamples = () => {
    setRecords([]); setSelectedId(""); setContextRecords({}); setAudit([]); setRequests([]);
    setSelectedCapabilities({}); setSelectedComposition({}); setSelectedGrant({});
    setEditedImprovement({}); setProposalEditor({}); setSelectedEvidence(null); setNewRequest("");
    setSiteIndex(0); setTaskIndex(0); setQuery(""); setCompanyFilter("전체"); navigate("dashboard");
  };
  const loadExamples = (count: number) => { clearExamples(); const examples = structuredClone(COMPANIES.slice(0,count)); setRecords(examples); setSelectedId(examples[0]?.id ?? ""); };
  if (!signedIn) return <div className="datco-operator op-login"><div className="op-login-brand"><div className="op-logo"><Layers3 size={25}/><strong>DATCO ONE</strong></div><div className="op-brand-message"><h1>기업의 문제부터<br/>실행 가능한 제안까지.</h1><p>운영자 업무 포털 · 개발 전용 화면 미리보기</p></div></div><div className="op-login-pane"><div className="op-login-card"><h2>운영자 UI 미리보기</h2><p>실제 로그인·인증 없이 화면만 시연합니다.</p><button className="op-btn op-btn-primary" onClick={() => setSignedIn(true)}>미리보기 진입 <ArrowRight size={16}/></button></div></div></div>;

  return (
    <div className="datco-operator op-shell">
      {mobileNav && <div className="op-mobile-overlay" onClick={() => setMobileNav(false)} />}
      <aside className={`op-sidebar ${mobileNav ? "open" : ""}`}>
        <div className="op-side-logo"><div className="op-logo-mark"><Layers3 size={20}/></div><div><strong>DATCO <em>ONE</em></strong><span>운영자 업무 포털</span></div><button onClick={() => setMobileNav(false)} className="op-close-side" aria-label="메뉴 닫기"><X size={17}/></button></div>
        <nav aria-label="운영자 업무 메뉴" className="op-side-nav">{links.map((section) => <div key={section.section} className="op-menu-section"><div className="op-menu-head">{section.section}</div>{section.pages.map(({ id, name, Icon }) => <button key={id} type="button" className={`op-menu-item ${page === id ? "active" : ""}`} onClick={() => navigate(id)}><Icon size={17}/><span>{name}</span>{page === id && <span className="op-nav-dot"/>}</button>)}</div>)}</nav>
        <div className="op-side-bottom"><div className="op-security"><ShieldCheck size={18}/><div><strong>검토 기반 운영</strong><span>권한·원본·버전 확인</span></div></div><div className="op-user"><div className="op-avatar">운</div><div><strong>DATCO 운영자</strong><span>업무 검토 계정</span></div><button type="button" aria-label="로그아웃" title="로그아웃" onClick={() => setShowLogout(true)}><LogOut size={17}/></button></div></div>
      </aside>
      <div className="op-app-body">
        <header className="op-topbar"><div className="op-top-left"><button className="op-menu-toggle" aria-label="메뉴 열기" onClick={() => setMobileNav(true)}><Menu size={20}/></button><span>운영자 포털</span><ChevronRight size={14}/><b>{links.flatMap((s) => s.pages).find((p) => p.id === page)?.name}</b></div><div className="op-top-right"><div className="op-company-context"><Building2 size={15}/><select aria-label="업무 대상 기업 변경" value={selectedId} onChange={(e) => chooseCompany(e.target.value, "workspace")}>{records.map((c) => <option value={c.id} key={c.id}>{c.name}</option>)}</select><ChevronDown size={14}/></div><span className="op-top-sep"/><button aria-label="로그아웃" className="op-top-logout" onClick={() => setShowLogout(true)}><LogOut size={16}/><span>로그아웃</span></button></div></header>
        <main className="op-main"><div className="op-preview-controls" role="region" aria-label="미리보기 제어"><strong>{records.length ? "예시 화면 보기 · 가상 데이터" : "빈 데이터 · 실제 DB 미연결"}</strong><button className="op-btn op-btn-outline" onClick={() => loadExamples(1)}>예시 화면 보기 · 기업 1개</button><button className="op-btn op-btn-outline" onClick={() => loadExamples(3)}>예시 화면 보기 · 여러 기업</button><button className="op-btn op-btn-outline" onClick={clearExamples}>예시 종료</button></div>
          <div className="op-content">
            {baseCompany && <div className="op-context-selectors"><label>사업장<select aria-label="사업장 선택" value={siteIndex} onChange={e=>{setSiteIndex(Number(e.target.value));setTaskIndex(0);setSelectedEvidence(null);setNewRequest("");}}><option value={0}>{baseCompany.site}</option><option value={1}>제2사업장 (가상 예시)</option></select></label><label>개선과제<select aria-label="개선과제 선택" value={taskIndex} onChange={e=>{setTaskIndex(Number(e.target.value));setSelectedEvidence(null);setNewRequest("");}}><option value={0}>{siteIndex === 0 ? baseCompany.improvement.title : "제2사업장 작업기록 개선 (예시)"}</option><option value={1}>자료 통합·조회 개선 (예시)</option></select></label><span>선택한 기업·사업장·과제의 시연 맥락</span></div>}
            {!records.length && <Empty title="등록된 수요기업이 없습니다" detail="실제 DB 미연결 상태입니다. 예시 화면 보기에서 업무 동선을 시연할 수 있습니다."/>}

            {records.length > 0 && ["facts","improvement","matching"].includes(page) && <button className="op-btn op-btn-outline" onClick={openRequest}>보완자료 요청으로 이동</button>}
            {toast && <div className="op-toast" role="status"><InfoIcon/><span>{toast}</span><button onClick={() => setToast("")} aria-label="메시지 닫기"><X size={15}/></button></div>}
            {records.length > 0 && page !== "dashboard" && page !== "companies" && <div className="op-context-bar"><span className="op-context-symbol"><Building2 size={17}/></span><div><strong>{current.name}</strong><span>{current.site} · {current.improvement.title}</span></div><Pill tone={current.matching.status === "PROPOSABLE" ? "green" : current.matching.status === "MISMATCH" ? "red" : "amber"}>{current.stage}</Pill><button className="op-btn op-btn-ghost" onClick={() => navigate("workspace")}>업무 전체 보기 <ArrowRight size={14}/></button></div>}

            {page === "dashboard" && <>
              <Heading eyebrow="OPERATIONS OVERVIEW" title="업무 대시보드" desc="담당 기업과 검토 대기 업무를 확인하고 다음 단계로 이동합니다." right={<button className="op-btn op-btn-outline" onClick={clearExamples}><RefreshCw size={15}/> 예시 종료 · 빈 상태</button>}/>
              <div className="op-hero"><div><span className="op-hero-eyebrow">DATCO COMPANY WORKSPACE</span><h2>기업별 개선과제를<br/>하나의 업무 흐름으로.</h2><p>제출자료의 근거 검토부터 솔루션 추천, 지원사업 검토, 맞춤형 제안서까지 연결합니다.</p><button className="op-btn op-btn-light" onClick={() => navigate("companies")}>수요기업 목록 열기 <ArrowRight size={16}/></button></div><div className="op-hero-decor"><div className="op-hero-ring"/><div className="op-hero-mini"><Layers3 size={26}/><span>COMPANY</span><strong>WORKFLOW</strong></div></div></div>
              <div className="op-metrics">{[
                { title: "관리 기업", count: dashboardCounts.companies, Icon: Building2, type: "blue", suffix: "개" },
                { title: "Fact 검토 대상", count: dashboardCounts.facts, Icon: FileSearch, type: "amber", suffix: "건" },
                { title: "매칭 확인 필요", count: dashboardCounts.blocked, Icon: AlertCircle, type: "purple", suffix: "개 기업" },
                { title: "작성된 제안서", count: dashboardCounts.proposals, Icon: FileCheck2, type: "green", suffix: "건" },
              ].map(({ title, count, Icon, type, suffix }) => <Card key={title} className="op-metric"><div className={`op-metric-icon op-metric-${type}`}><Icon size={20}/></div><span>{title}</span><div><strong>{count}</strong><small>{suffix}</small></div></Card>)}</div>
              <div className="op-dash-grid"><Card className="op-pad"><SectionTitle title="기업별 진행현황" sub="기업을 선택하면 전체 업무를 확인할 수 있습니다." action={<button className="op-link" onClick={() => navigate("companies")}>전체 보기 <ArrowRight size={15}/></button>}/><div className="op-company-list">{records.map((company) => <button onClick={() => chooseCompany(company.id)} className="op-company-mini" key={company.id}><div className="op-company-letter">{company.name.replace("㈜", "").charAt(0)}</div><div className="op-company-mini-main"><strong>{company.name}</strong><span>{company.industry} · {company.improvement.title}</span></div><Pill tone={company.matching.status === "PROPOSABLE" ? "green" : company.matching.status === "MISMATCH" ? "red" : "amber"}>{company.stage}</Pill><ChevronRight size={16}/></button>)}</div></Card><Card className="op-pad"><SectionTitle title="우선 검토할 업무" sub="자료 부족·검토 대기·제안 검토의 예시입니다."/><div className="op-task-list">{records.length > 0 && <><button onClick={() => chooseCompany(records[0].id, "facts")}><div className="op-task-icon op-task-amber"><FileWarning size={19}/></div><div><strong>{records[0]?.name} · Fact 검토</strong><span>매출액 및 사업장 증빙 확인 필요</span></div><ChevronRight size={16}/></button><button onClick={() => chooseCompany(records[0].id, "matching")}><div className="op-task-icon op-task-blue"><ClipboardCheck size={19}/></div><div><strong>{records[0]?.name} · 매칭 조건</strong><span>신청자격 미확인 항목 2건</span></div><ChevronRight size={16}/></button><button onClick={() => chooseCompany(records[1]?.id ?? records[0].id, "proposals")}><div className="op-task-icon op-task-green"><FileCheck2 size={19}/></div><div><strong>{(records[1] ?? records[0])?.name} · 제안서 검토</strong><span>제안 가능한 사전 검증 예시</span></div><ChevronRight size={16}/></button></>}</div></Card></div>
            </>}

            {page === "companies" && <>
              <Heading eyebrow="COMPANIES / O-02" title="수요기업 목록" desc="기업·사업장·개선과제를 검색하고 담당 업무로 이동합니다." right={<Pill tone="blue">총 {records.length}개 기업</Pill>}/>
              <Card className="op-pad"><div className="op-filter-bar"><div className="op-search"><Search size={18}/><input placeholder="기업명, 업종, 개선과제 검색" value={query} onChange={(e) => setQuery(e.target.value)}/></div><select aria-label="진행상태 필터" value={companyFilter} onChange={(e) => setCompanyFilter(e.target.value)}><option>전체</option>{[...new Set(records.map((c) => c.stage))].map((s) => <option key={s}>{s}</option>)}</select></div><div className="op-table-wrap"><table className="op-table"><thead><tr><th>기업 / 사업장</th><th>개선과제</th><th>업종</th><th>진행 단계</th><th>다음 작업</th></tr></thead><tbody>{companiesFiltered.map((c) => <tr key={c.id}><td><button className="op-company-cell" onClick={() => chooseCompany(c.id)}><strong>{c.name}</strong><span>{c.site}</span></button></td><td>{c.improvement.title}</td><td>{c.industry}</td><td><Pill tone={c.matching.status === "PROPOSABLE" ? "green" : c.matching.status === "MISMATCH" ? "red" : "amber"}>{c.stage}</Pill></td><td><button className="op-btn op-btn-outline op-btn-small" onClick={() => chooseCompany(c.id)}>상세 보기 <ArrowRight size={14}/></button></td></tr>)}</tbody></table></div>{companiesFiltered.length === 0 && <Empty title="검색 결과가 없습니다" detail="검색어나 필터를 변경하세요."/>}</Card>
            </>}

            {records.length > 0 && page === "workspace" && <>
              <Heading eyebrow="COMPANY WORKSPACE / O-03" title="기업 통합 업무" desc="기업의 현재 상태, 제출자료, 검토 결과와 다음 업무를 연결합니다." right={<Pill tone="blue">{current.id} · 내부 참조</Pill>}/>
              <div className="op-workflow">{quickStages.map((s, i) => <button onClick={() => navigate(s.page)} className="op-stage" key={s.page}><span>{i + 1}</span><strong>{s.name}</strong><ChevronRight size={15}/></button>)}</div>
              <div className="op-two-cols"><Card className="op-pad"><SectionTitle title="기업 기본정보"/><div className="op-details-grid"><Meta label="기업명" value={current.name}/><Meta label="업종" value={current.industry}/><Meta label="사업장" value={current.site}/><Meta label="소재지" value={current.address}/><Meta label="담당자" value={current.companyUser}/><Meta label="제출자료" value={`${current.documents.length}건`}/></div><SectionTitle title="개선과제"/><div className="op-feature-box"><b>{current.improvement.title}</b><p>{current.improvement.asis}</p><div className="op-inline-meta">ImprovementVersion v{current.improvement.version} · {current.improvement.id}</div></div><button className="op-btn op-btn-outline" onClick={() => navigate("improvement")}>개선요구 검토 <ArrowRight size={15}/></button></Card><Card className="op-pad"><SectionTitle title="다음 업무 안내" sub="시연 데이터에 근거한 권장 동선입니다."/>{pendingFacts.length > 0 && <div className="op-next-item"><AlertCircle size={18}/><div><b>Fact 확인 필요</b><p>{pendingFacts.length}개 항목의 근거를 검토해야 합니다.</p></div><button onClick={() => navigate("facts")}>이동</button></div>}{eligibilityBlockers.length > 0 && <div className="op-next-item"><AlertCircle size={18}/><div><b>매칭 보완 필요</b><p>{eligibilityBlockers.length}개 미확인·불일치 조건이 있습니다.</p></div><button onClick={() => navigate("matching")}>이동</button></div>}{safeToPropose && <div className="op-next-item success"><CheckCircle2 size={18}/><div><b>제안서 업무 진행 가능</b><p>사전 검증된 가상 MatchReview 조건을 충족합니다.</p></div><button onClick={() => navigate("proposals")}>이동</button></div>}<div className="op-summary-grid"><div><span>검토할 Fact</span><strong>{pendingFacts.length}</strong></div><div><span>서비스 후보</span><strong>{current.capabilities.length}</strong></div><div><span>공고 후보</span><strong>{current.grants.length}</strong></div><div><span>제안서 버전</span><strong>{current.proposal.version || "미작성"}</strong></div></div></Card></div>
            </>}

            {records.length > 0 && page === "facts" && <>
              <Heading eyebrow="DATA REVIEW / O-04" title="기업자료 · Fact 검토" desc="문서 근거와 추출값을 비교하고, 미확인·충돌 항목을 구분합니다." right={<Pill tone="amber">검토 대상 {pendingFacts.length}건</Pill>}/>
              <Explain kind="warning">기업의 확인, DATCO 근거 검토, 최종 FactVersion 확정은 별개입니다. 버튼은 화면상 검토 상태만 변경합니다.</Explain>
              <div className="op-two-cols op-doc-cols"><Card className="op-pad"><SectionTitle title="제출 자료" sub="문서 원본 내용은 샘플 발췌문으로 표시합니다."/><div className="op-doc-list">{current.documents.map((doc) => <button key={doc.id} onClick={() => setSelectedEvidence(doc)} className="op-doc-item"><div className="op-file-icon"><FileText size={19}/></div><div><b>{doc.name}</b><span>{doc.type} · v{doc.version} · {doc.source}</span><span>자료 설명: {doc.excerpt}</span><span>관련 사업장: {current.site} · 개선과제: {current.improvement.title} · 제출: {doc.submittedBy}</span></div><ChevronRight size={15}/></button>)}</div></Card><Card className="op-pad"><SectionTitle title="검토할 기업 사실" sub="Fact의 기간·단위·Evidence 출처를 확인하세요."/><div className="op-fact-list">{current.facts.map((fact) => <div className="op-fact-row" key={fact.id}><div className="op-fact-head"><strong>{fact.label}</strong><Pill tone={fact.status === "CONFIRMED" ? "green" : fact.status === "REJECTED" ? "red" : "amber"}>{factName[fact.status]}</Pill></div><p className="op-fact-value">{fact.value}</p><p className="op-fact-source">{fact.source} · 기준: {fact.period} · Version {fact.version}</p><div className="op-fact-actions"><button className="op-btn op-btn-outline op-btn-small" onClick={() => setSelectedEvidence(current.documents.find((x) => x.id === fact.evidenceId) ?? null)}><FileSearch size={14}/> 근거 확인</button><button className="op-btn op-btn-outline op-btn-small" onClick={() => reviewFact(fact.id, "CONFIRMED")}>검토 확인</button><button className="op-btn op-btn-soft-red op-btn-small" onClick={() => reviewFact(fact.id, "REJECTED")}>보완 필요</button></div></div>)}</div></Card></div>
            </>}

            {records.length > 0 && page === "improvement" && <>
              <Heading eyebrow="IMPROVEMENT / O-05" title="개선요구 분석 · 검토" desc="기업 원문과 As-Is·To-Be 분석 내용을 비교하고 검토 이력을 보존합니다." right={<Pill tone={current.improvement.reviewed ? "green" : "amber"}>{current.improvement.reviewed ? "검토 표시됨" : "검토 대기"}</Pill>}/>
              <div className="op-two-cols"><Card className="op-pad"><SectionTitle title="기업 제출 원문"/><div className="op-quote">{current.improvement.asis}</div><div className="op-note-pair"><Meta label="개선과제" value={current.improvement.title}/><Meta label="근거 버전" value={`ImprovementVersion v${current.improvement.version}`}/></div><SectionTitle title="구조화된 문제"/><div className="op-chip-wrap">{current.improvement.problems.map((problem, i) => <span className="op-problem-tag" key={problem}><span>{String(i + 1).padStart(2, "0")}</span>{problem}</span>)}</div></Card><Card className="op-pad"><SectionTitle title="개선목표 · 제약조건 검토"/><label className="op-form-label">To-Be 개선목표<textarea value={editedImprovement[contextKey] ?? current.improvement.tobe} onChange={(e) => setEditedImprovement((p) => ({ ...p, [contextKey]: e.target.value }))} rows={6}/></label><label className="op-form-label">제약조건<textarea value={current.improvement.constraints} readOnly rows={4}/></label><Explain>AI 후보와 운영자의 검토 결과를 구분하고, 수정 시 기존 승인된 Version을 덮어쓰지 않습니다.</Explain><div className="op-actions-row"><button className="op-btn op-btn-primary" onClick={saveImprovement}><Check size={15}/> 검토 결과 표시</button><button className="op-btn op-btn-outline" onClick={() => navigate("recommendations")}>서비스 추천 검토 <ArrowRight size={15}/></button></div></Card></div>
            </>}

            {records.length > 0 && page === "recommendations" && <>
              <Heading eyebrow="SOLUTION RECOMMENDATION / O-06" title="DATCO 서비스 추천" desc="개선문제와 실제 해결범위를 구분하며 Capability 후보를 확인합니다." right={<Pill tone="purple">가상 DMP Catalog 후보</Pill>}/>
              <Explain kind="warning">후보는 시연용 가상 카탈로그입니다. 키워드 일치만으로 실제 서비스 제공 가능 여부나 AI 자동 추천 완료를 주장하지 않습니다.</Explain>
              <Card className="op-pad"><SectionTitle title="기업 개선문제" sub="현재 ImprovementVersion에서 가져온 검토 대상입니다."/><div className="op-chip-wrap">{current.improvement.problems.map((p) => <Pill key={p} tone="blue">{p}</Pill>)}</div></Card>
              <div className="op-reco-grid">{current.capabilities.map((cap) => <Card key={cap.id} className="op-pad op-reco-card"><div className="op-reco-head"><div className="op-reco-symbol"><Sparkles size={22}/></div><Pill tone="blue">{cap.version}</Pill></div><h3>{cap.title}</h3><p>{cap.reason}</p><div className="op-feature-meta"><span>대응 문제</span>{cap.coverage.map((p) => <strong key={p}>{p}</strong>)}</div><div className="op-warning-line"><AlertCircle size={15}/>{cap.limitations.join(" · ")}</div><div className="op-reco-bottom"><small>{cap.features.join(" · ")}</small><button className={`op-btn op-btn-small ${(selectedCapabilities[contextKey] ?? []).includes(cap.id) ? "op-btn-primary" : "op-btn-outline"}`} onClick={() => toggleCapability(cap.id)}>{(selectedCapabilities[contextKey] ?? []).includes(cap.id) ? <Check size={14}/> : <Plus size={14}/>}{(selectedCapabilities[contextKey] ?? []).includes(cap.id) ? "검토 선택됨" : "후보 선택"}</button></div></Card>)}</div><div className="op-actions-row op-spaced"><span>선택한 Capability {(selectedCapabilities[contextKey] ?? []).length}건 · 실제 DMP 카탈로그 연동 전</span><button className="op-btn op-btn-primary" onClick={() => navigate("compositions")}>서비스 조합 비교 <ArrowRight size={15}/></button></div>
            </>}

            {records.length > 0 && page === "compositions" && <>
              <Heading eyebrow="SOLUTION COMPOSITION / O-07" title="서비스 조합 검토" desc="추천 후보를 조합 단위로 비교하고 해결·미해결 범위를 검토합니다." right={<Pill tone="blue">{chosenComp ? `선택: ${chosenComp.id}` : "조합 선택 필요"}</Pill>}/>
              <div className="op-comp-grid">{current.compositions.map((comp) => <Card className={`op-pad op-comp-card ${chosenComp?.id === comp.id ? "selected" : ""}`} key={comp.id}><div className="op-comp-top"><Pill tone="blue">조합 후보</Pill><strong>{comp.coverage}</strong></div><h3>{comp.title}</h3><p>{comp.note}</p><div className="op-subhead">포함 서비스</div><div className="op-chip-wrap">{comp.capabilityIds.map((id) => <Pill key={id}>{current.capabilities.find((x) => x.id === id)?.title ?? id}</Pill>)}</div><div className="op-subhead">미해결·확인사항</div><ul>{comp.unresolved.map((x) => <li key={x}>{x}</li>)}</ul><div className="op-comp-actions"><button className={chosenComp?.id === comp.id ? "op-btn op-btn-primary" : "op-btn op-btn-outline"} onClick={() => selectComposition(comp.id)}>{chosenComp?.id === comp.id ? "검토 후보 선택됨" : "이 조합 검토"} <Check size={15}/></button></div></Card>)}</div><Explain>이 화면의 조합 선택은 검토 후보 표시입니다. 기존 CompositionVersion 발행, Coverage 검증, 승인 Guard는 연결 후 서버에서 시행해야 합니다.</Explain><div className="op-actions-row op-right"><button onClick={() => navigate("grants")} className="op-btn op-btn-primary">정부지원사업 후보 검토 <ArrowRight size={15}/></button></div>
            </>}

            {records.length > 0 && page === "grants" && <>
              <Heading eyebrow="GRANT PROGRAMS / O-08" title="정부지원사업 추천" desc="기업의 사실·개선과제·서비스 조합을 바탕으로 공고 후보와 조건을 비교합니다." right={<Pill tone="amber">가상 후보 · 공식 공고 아님</Pill>}/>
              <Explain kind="warning">모든 공고는 가상입니다. 신청기간·자격·지원금액·선정 가능성을 공식 사실로 해석하면 안 됩니다.</Explain>
              <div className="op-grant-grid">{current.grants.map((grant) => <Card key={grant.id} className={`op-pad op-grant ${chosenGrant?.id === grant.id ? "selected" : ""}`}><div className="op-grant-top"><Pill tone="amber">가상 공고</Pill><span>{grant.organization}</span></div><h3>{grant.title}</h3><p>{grant.rationale}</p><div className="op-grant-period"><CalendarClock size={15}/>{grant.period}</div><div className="op-criteria">{grant.eligibility.map((c) => <div key={c.name}><div><b>{c.name}</b><Pill tone={statusTone[c.state]}>{statusName[c.state]}</Pill></div><span>{c.reason}</span></div>)}</div><button className={chosenGrant?.id === grant.id ? "op-btn op-btn-primary" : "op-btn op-btn-outline"} onClick={() => { setSelectedGrant((p) => ({ ...p, [contextKey]: grant.id })); logAction("공고 후보", `가상 공고 후보 ${grant.id} 검토 대상으로 선택`); notify("가상 지원사업 검토 후보를 선택했습니다. 실제 자격은 확정되지 않았습니다."); }}>{chosenGrant?.id === grant.id ? "검토 대상 선택됨" : "이 후보 검토"} <ArrowRight size={15}/></button></Card>)}</div><div className="op-actions-row op-right"><button onClick={() => navigate("matching")} className="op-btn op-btn-primary">자격·매칭 검토 <ArrowRight size={15}/></button></div>
            </>}

            {records.length > 0 && page === "matching" && <>
              <Heading eyebrow="ELIGIBILITY REVIEW / O-09" title="매칭 · 신청자격 검토" desc="조건별 충족·충돌·미확인을 구분하고 제안서 생성 가능성을 검토합니다." right={<Pill tone={safeToPropose ? "green" : current.matching.status === "MISMATCH" ? "red" : "amber"}>{safeToPropose ? "제안 가능 예시" : current.matching.status === "MISMATCH" ? "조건 불일치" : "제안 전 확인 필요"}</Pill>}/>
              <div className="op-three-way"><Card className="op-pad"><h2>수요기업 개선요구</h2><p>{current.improvement.title}</p><p>{current.improvement.tobe}</p></Card><Card className="op-pad"><h2>DATCO 솔루션 조합안</h2><p>{chosenComp?.title ?? "검토 후보 선택 필요"}</p><p>{chosenComp?.coverage}</p><p>{chosenComp?.unresolved.join(" · ")}</p></Card><Card className="op-pad"><h2>정부지원사업 후보</h2><p>{chosenGrant?.title ?? "가상 공고 후보 선택 필요"}</p></Card></div><div className="op-two-cols"><Card className="op-pad"><SectionTitle title="조건별 검토" sub="기존 Fact와 공고조건을 비교한 가상 데이터입니다."/><div className="op-match-list">{current.matching.criteria.map((item) => <div key={item.name}><div className="op-match-item-head"><strong>{item.name}</strong><Pill tone={statusTone[item.state]}>{statusName[item.state]}</Pill></div><p>{item.reason}</p></div>)}</div><div className="op-match-summary"><b>현재 MatchReview</b><span>{current.matching.status}</span><p>{current.matching.reviewNote}</p></div></Card><Card className="op-pad"><SectionTitle title="제안서 진행 가능 여부"/><div className={`op-gate-card ${safeToPropose ? "allowed" : "blocked"}`}><div>{safeToPropose ? <CheckCircle2 size={27}/> : <LockKeyhole size={27}/>}</div><h3>{safeToPropose ? "시연용 제안 가능 조건 충족" : "제안서 생성 차단"}</h3><p>{safeToPropose ? "확인된 가상 데이터와 사전 검토된 MatchReview를 사용합니다." : "Fact 또는 공고조건의 미확인·불일치가 남아 있습니다."}</p></div><div className="op-gate-stats"><Meta label="확인 필요 Fact" value={`${pendingFacts.length}건`}/><Meta label="미확인/불일치 조건" value={`${eligibilityBlockers.length}건`}/></div><div className="op-actions-row"><button className="op-btn op-btn-outline" onClick={reviewMatch}>검토 결과 확인</button><button className="op-btn op-btn-primary" onClick={() => safeToPropose ? navigate("proposals") : openRequest()}>{safeToPropose ? "제안서로 이동" : "부족정보 보완"}<ArrowRight size={15}/></button></div></Card></div>
            </>}

            {records.length > 0 && page === "requests" && <>
              <button className="op-btn op-btn-outline" onClick={() => navigate(requestReturn)}>검토하던 화면으로 돌아가기</button><Heading eyebrow="SUPPLEMENT REQUEST / O-10" title="보완자료 요청" desc="검토 중 부족한 기업정보나 추가자료를 요청하고 응답 상황을 추적합니다."/>
              <div className="op-two-cols"><Card className="op-pad"><SectionTitle title="추가 확인사항 요청 작성" sub="실제 수요기업에게 발송하지 않고 화면에만 작성합니다."/><label className="op-form-label">수요기업에 요청할 내용<textarea rows={7} value={newRequest} onChange={(e) => setNewRequest(e.target.value)}/></label><div className="op-actions-row"><button className="op-btn op-btn-primary" onClick={requestSupplement}><Plus size={16}/> 보완 요청 작성</button></div><Explain kind="warning">보완 요청을 작성하는 것과 실제 수요기업 포털로 전달되는 것은 다릅니다. 현재는 화면상 작성입니다.</Explain></Card><Card className="op-pad"><SectionTitle title="요청 이력" sub={`${currentRequests.length}건의 가상 요청·작성 기록`}/><div className="op-request-list">{currentRequests.length ? currentRequests.map((req) => <div key={req.id}><div className="op-request-line"><b>{req.id}</b><Pill tone={req.status === "화면상 완료" ? "green" : "amber"}>{req.status}</Pill></div><p>{req.text}</p><small>{req.at}</small>{req.status === "작성" && <button className="op-btn op-btn-outline op-btn-small" onClick={() => { setRequests((a) => a.map((x) => x.id === req.id ? { ...x, status: "보완 대기" } : x)); logAction("보완 요청", `${req.id} 화면상 요청대기로 변경, 실제 전송 없음`); }}>요청 대기 표시</button>}</div>) : <Empty title="요청 이력이 없습니다"/>}</div></Card></div>
            </>}

            {records.length > 0 && page === "proposals" && <>
              <Heading eyebrow="PROPOSAL WORKSPACE / O-11" title="맞춤형 제안서 관리" desc="검토된 입력 정보를 바탕으로 제안서를 생성·편집하고 정확한 버전으로 이력을 유지합니다." right={<Pill tone={current.proposal.reviewed ? "green" : "amber"}>{current.proposal.version ? `ProposalVersion v${current.proposal.version}` : "미작성"}</Pill>}/>
              {!safeToPropose && <Explain kind="warning">현재 기업은 미확인 Fact 또는 신청자격으로 인해 제안서 신규 생성·검토가 차단됩니다. 기존 PROPOSABLE Guard를 우회하지 않습니다.</Explain>}
              <div className="op-two-cols op-proposal-cols"><Card className="op-pad"><SectionTitle title="제안서 본문 편집" sub="수정 저장 시 새 버전이 생성되며 기존 검토는 자동 승계되지 않습니다." action={<Pill tone="blue">{current.proposal.id}</Pill>}/><label className="op-form-label">제안서 제목<input type="text" readOnly value={current.proposal.title}/></label><label className="op-form-label">제안 내용<textarea value={proposalText} onChange={(e) => setProposalEditor((p) => ({ ...p, [contextKey]: e.target.value }))} rows={18} placeholder="제안 가능 조건이 충족되면 초안을 생성할 수 있습니다."/></label><div className="op-actions-row"><button onClick={createProposal} disabled={!safeToPropose} className="op-btn op-btn-outline"><Plus size={16}/> 새 초안 생성</button><button onClick={saveProposal} disabled={!safeToPropose || current.proposal.version === 0} className="op-btn op-btn-primary"><Check size={16}/> 새 버전 저장</button></div></Card><Card className="op-pad"><SectionTitle title="제안서 검토·승인 이력" sub="현재 화면은 기존 P-01~P-05 Provider를 호출하지 않습니다."/><div className="op-details-grid"><Meta label="현재 버전" value={current.proposal.version ? `v${current.proposal.version}` : "없음"}/><Meta label="내용 검토" value={current.proposal.reviewed ? "현재 버전 검토됨" : "검토 필요"}/><Meta label="전달 기록" value={current.proposal.deliveredVersion ? `v${current.proposal.deliveredVersion}` : "미전달"}/><Meta label="수신자" value={current.proposal.recipient}/></div><Explain>내용 변경 후에는 과거 ProposalVersion·Review·승인을 현재 버전에 자동 승계할 수 없습니다.</Explain><div className="op-button-stack"><button className="op-btn op-btn-primary" disabled={!safeToPropose || current.proposal.version === 0} onClick={reviewProposal}><ClipboardCheck size={16}/> 현 버전 내용 검토 표시</button><button className="op-btn op-btn-outline" disabled={current.proposal.version === 0} onClick={downloadProposal}><Download size={16}/> 텍스트 예시 다운로드</button><button className="op-btn op-btn-outline" onClick={() => navigate("delivery")}>전달·회신 이력 보기 <ArrowRight size={16}/></button></div></Card></div>
            </>}

            {records.length > 0 && page === "delivery" && <>
              <Heading eyebrow="DELIVERY HISTORY / O-12" title="제안서 전달·검토 이력" desc="어떤 ProposalVersion이 누구에게 전달됐는지 추적하고, 변경 후 재검토 여부를 확인합니다." right={<Pill tone="blue">외부 전송 미연동</Pill>}/>
              <div className="op-two-cols"><Card className="op-pad"><SectionTitle title="제안서 전달 조건"/><div className="op-details-grid"><Meta label="제안서" value={current.proposal.title}/><Meta label="현재 버전" value={current.proposal.version ? `v${current.proposal.version}` : "없음"}/><Meta label="기업 수신자" value={current.proposal.recipient}/><Meta label="현재 버전 검토" value={current.proposal.reviewed ? "완료 예시" : "필요"}/></div><div className="op-actions-row"><button className="op-btn op-btn-primary" onClick={recordDelivery} disabled={!safeToPropose || !current.proposal.reviewed || !current.proposal.version}><Send size={16}/> 화면상 전달 이력 기록</button></div><Explain kind="warning">버튼은 실제 DMP/기업 포털이나 이메일에 전달하지 않습니다. 정확한 버전과 수신자의 시연 로그만 생성합니다.</Explain></Card><Card className="op-pad"><SectionTitle title="업무·검토·전달 로그" sub="화면에서 발생한 작업을 로컬 기록으로 표시합니다."/><div className="op-history">{currentAudit.length ? currentAudit.map((a) => <div key={a.id} className="op-history-item"><span className="op-history-dot"/><div><div className="op-history-title"><b>{a.type}</b><small>{a.at}</small></div><p>{a.text}</p></div></div>) : <Empty title="이력이 없습니다"/>}</div></Card></div>
            </>}
            <footer className="op-footer"><span>DATCO ONE · 운영자 업무 포털</span><span>표시된 기업·지원사업·추천 결과는 시연 데이터입니다. 운영 인증·DMP·DB·AI·문서 전송은 연결되지 않았습니다.</span></footer>
          </div>
        </main>
      </div>
      {selectedEvidence && <div className="op-modal-mask" role="presentation" onClick={() => setSelectedEvidence(null)}><div className="op-modal" role="dialog" aria-modal="true" aria-label="증빙자료 확인" onClick={(e) => e.stopPropagation()}><div className="op-modal-top"><div><span>DOCUMENT EVIDENCE</span><h3>제출자료 근거 확인</h3></div><button aria-label="닫기" onClick={() => setSelectedEvidence(null)}><X size={20}/></button></div><div className="op-modal-content"><Meta label="파일명" value={selectedEvidence.name}/><Meta label="원본 위치" value={selectedEvidence.source}/><Meta label="문서 버전" value={`v${selectedEvidence.version}`}/><Meta label="업로드 일자" value={selectedEvidence.submittedAt}/><div className="op-evidence-quote"><span>문서 내용 발췌 (시연 Fixture)</span><p>{selectedEvidence.excerpt}</p></div><Explain>원본 파일 자체가 아니라 Fixture에 저장된 발췌문입니다. 실제 File Store·Private File API 미연동입니다.</Explain></div><div className="op-actions-row op-right"><button className="op-btn op-btn-primary" onClick={() => setSelectedEvidence(null)}>확인</button></div></div></div>}
      {showLogout && <div className="op-modal-mask" role="presentation" onClick={() => setShowLogout(false)}><div className="op-confirm" role="dialog" aria-modal="true" aria-label="로그아웃 확인" onClick={(e) => e.stopPropagation()}><div className="op-confirm-icon"><LogOut size={23}/></div><h3>로그아웃하시겠습니까?</h3><p>화면 체험 세션을 종료하고 로그인 화면으로 이동합니다. 입력한 시연 데이터는 같은 페이지 실행 중 메모리에만 보존됩니다.</p><div className="op-actions-row op-right"><button className="op-btn op-btn-outline" onClick={() => setShowLogout(false)}>취소</button><button className="op-btn op-btn-primary" onClick={logOut}>로그아웃</button></div></div></div>}
    </div>
  );
}

function InfoIcon() { return <AlertCircle size={17} aria-hidden="true"/>; }

// Additional contexts are explicitly fictional, not company submissions or extracted facts.
function contextExample(company: Company, site: number, task: number): Company {
  if (!site && !task) return company;
  return { ...company, siteId: `${company.siteId}-${site}`, site: site ? "제2사업장 (가상 예시)" : company.site,
    improvement: { ...company.improvement, id: `${company.improvement.id}-${site}-${task}`, title: task ? "자료 통합·조회 개선 (예시)" : "제2사업장 작업기록 개선 (예시)", asis: "이 작업 맥락의 자료가 분산되어 있습니다. (가상 원문)", tobe: "작업별 기록을 통합 조회합니다. (가상 목표)", problems: ["자료 조회 지연 (예시)"], reviewed: false },
    documents: [], facts: [], capabilities: [], compositions: [], grants: [], matching: { status: "REVIEW_REQUIRED", criteria: [{name:"자료 확인",state:"UNKNOWN",reason:"이 사업장·과제의 자료 미확인"}], reviewNote:"다른 사업장·과제의 검토를 승계하지 않습니다." }, proposal:{...company.proposal,version:0,body:"",reviewed:false,deliveredVersion:null} };
}
const EMPTY_COMPANY: Company = { id:"",name:"",siteId:"",site:"",industry:"",address:"",companyUser:"",businessNo:"",stage:"",owner:"",lastUpdated:"",requestCount:0, improvement:{id:"",version:0,title:"",asis:"",tobe:"",constraints:"",problems:[],reviewed:false},documents:[],facts:[],capabilities:[],compositions:[],grants:[],matching:{status:"BLOCKED",criteria:[],reviewNote:""},proposal:{id:"",version:0,title:"",body:"",reviewed:false,deliveredVersion:null,recipient:""}};
