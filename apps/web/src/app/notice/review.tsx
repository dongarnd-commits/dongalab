
"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import type { components } from "@/generated/api";
import Collection from "./collection";
import { Badge, Technical, acquisitionLabel, isDemoMode, officialUrl, dateLabel, errorLabel, kindLabel, modeLabel, provenance, record, reviewLabel, sourceLabel, sourceState, text, summaryText, stateLabel, type Version } from "./presentation";
type Summary = components["schemas"]["NoticeSummary"];
type Detail = components["schemas"]["NoticeDetail"];
type Candidate = components["schemas"]["CandidateResponse"];
type Actor = components["schemas"]["ActorResponse"];
type View = "list" | "collection" | "review";

async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch("/api/notice" + path, { method: body === undefined ? "GET" : "POST", headers: { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body), cache: "no-store" });
  const data = await response.json();
  if (!response.ok) throw new Error(data.reason ?? "REQUEST_FAILED");
  return data as T;
}
function Evidence({ candidate }: { candidate: Candidate }) {
  return <div className="evidence"><div className="section-heading"><strong>원문 근거</strong><Badge>{candidate.evidence.page ? "PDF " + candidate.evidence.page + "페이지" : "HTML 원문 구간"}</Badge></div><blockquote>{candidate.evidence.text}</blockquote><a className="source-link" href={"/api/notice/sources/" + candidate.evidence.source_id + "/download"}>원천자료 다운로드 ↗</a></div>;
}
function CandidateCard({ candidate, version, isCurrent, reload }: { candidate: Candidate; version: Version; isCurrent: boolean; reload: () => Promise<void> }) {
  const [official, setOfficial] = useState(false); const [note, setNote] = useState(""); const [resolution, setResolution] = useState("");
  const [error, setError] = useState(""); const [pending, setPending] = useState(false);
  const reviewed = candidate.reviews.length > 0;
  const conflict = !!version.runs.find(run => run.candidates.some(c => c.id === candidate.id))?.conflicts.length;
  async function act(confirm: boolean) {
    setPending(true); setError("");
    try {
      await api("/candidates/" + candidate.id + (confirm ? "/confirm" : "/more-source"), confirm ? {
        expected_version: version.id, official_verified: official, note, scope: "선택한 원문 항목에 한정", conflict_resolution: resolution,
      } : { expected_version: version.id, note });
      await reload();
    } catch (e) { setError(e instanceof Error ? e.message : "REVIEW_FAILED"); }
    finally { setPending(false); }
  }
  const reason = candidate.reason.startsWith("Direct source clause labelled") ? "원문에 명시된 항목을 추출한 후보입니다. 자동 판정이 아니므로 아래 근거를 직접 확인해 주세요." : candidate.reason;
  return <article data-testid="candidate" className="candidate-card">
    <div className="section-heading"><h4>{kindLabel[candidate.kind] ?? "요건 후보"}</h4><Badge tone={reviewed ? "success" : ""}>{reviewed ? "검토 기록 있음" : "검토 대기"}</Badge></div>
    {candidate.kind === "REQUIRED_DOCUMENT" && candidate.content.length > 800 ? <details className="candidate-content-full"><summary>제출서류 목록·조건 전체 보기</summary><p className="candidate-content">{candidate.content}</p></details> : <p className="candidate-content">{candidate.content}</p>}<p className="muted"><strong>추출 이유</strong> · {reason}</p>
    <Evidence candidate={candidate} />
    {reviewed ? <div className="review-record">{candidate.reviews.map((r, index) => {
      const review = record(r);
      return <div key={index}><strong>{review.outcome === "CONFIRM" ? "선택 요건 확정" : "자료 보완 요청"}</strong><p>{text(review.note, "검토 의견 없음")}</p><small className="muted">{dateLabel(review.created_at)}</small></div>;
    })}</div> : <div className="review-form">
      {conflict && <p className="warning">서로 다른 근거가 있습니다. 원문을 대조하고 충돌 해소 의견을 기록해야 확정할 수 있습니다.</p>}
      {!isCurrent && <p className="warning">이전 버전은 조회만 가능합니다. 최신 버전에서 다시 검토해 주세요.</p>}
      <label className="check-label"><input type="checkbox" checked={official} onChange={e => setOfficial(e.target.checked)} disabled={!isCurrent || pending} />{modeLabel(version.mode)} 원문을 읽고 해당 요건의 근거를 확인했습니다.</label>
      <label>검토 의견<textarea value={note} onChange={e => setNote(e.target.value)} disabled={!isCurrent || pending} placeholder="확인한 원문과 판단 근거를 기록하세요." /></label>
      {conflict && <label>충돌 해소 의견<textarea value={resolution} onChange={e => setResolution(e.target.value)} disabled={!isCurrent || pending} /></label>}
      <div className="actions"><button className="primary" disabled={pending || !isCurrent || !official || !note.trim() || (conflict && !resolution.trim())} onClick={() => act(true)}>선택 요건 확정</button><button disabled={pending || !isCurrent || !note.trim()} onClick={() => act(false)}>자료 보완 요청</button></div>
      {!official && isCurrent && <small className="muted">원문 확인 체크와 검토 의견을 입력하면 확정할 수 있습니다.</small>}
    </div>}
    {error && <p role="alert" className="warning">{errorLabel(error)}</p>}
    <Technical value={{ candidate, reason: candidate.reason, error: error || undefined }} />
  </article>;
}
function VersionPanel({ version, current, pending, requestAnalysis, retry, refresh }: { version: Version; current: boolean; pending: boolean; requestAnalysis: (v: Version) => Promise<void>; retry: (id: string) => Promise<void>; refresh: () => Promise<void> }) {
  const metadata = version.metadata;
  const originUrl = officialUrl(version);
  const running = version.jobs.some(j => ["QUEUED", "PROCESSING"].includes(j.state));
  return <>
    <div className="section-heading"><h3>공고 버전 {version.ordinal}</h3><div className="badges"><Badge tone={version.mode === "LIVE" ? "live" : "demo"}>{modeLabel(version.mode)}</Badge><Badge>{current ? "현재 버전" : "이전 버전 · 조회 전용"}</Badge></div></div>
    <dl className="notice-facts">
      <div><dt>담당 기관</dt><dd>{text(metadata.agency)}</dd></div><div><dt>수행 기관</dt><dd>{text(metadata.executing_agency)}</dd></div>
      <div><dt>접수 기간 · 원천 표기</dt><dd>{text(metadata.period_original, "기간 정보 없음")}</dd></div><div><dt>대상 분류 · API 제공값</dt><dd>{text(metadata.target)}</dd></div>
    </dl>
    <p>{originUrl ? <a className="source-link" href={originUrl} target="_blank" rel="noopener noreferrer">기업마당 공식 공고 열기 ↗</a> : <span className="muted">{isDemoMode(version.mode) ? "데모 자료는 실제 공식 공고가 아닙니다." : "공식 원천 URL이 확인되지 않았습니다."}</span>}</p><p className="notice-note">기간과 대상은 수집된 원천 정보입니다. 지원 자격이나 접수 가능 여부의 확정 판정이 아닙니다.</p>
    {(!!metadata.summary || !!metadata.application_method) && <div className="panel"><h4>사업 개요 및 신청 안내</h4>{!!metadata.summary && <p className="source-text" data-testid="notice-summary">{summaryText(metadata.summary)}</p>}{!!metadata.application_method && <p className="source-text">{summaryText(metadata.application_method)}</p>}</div>}
    <div className="section-heading"><h3>1. 원천자료 확인</h3><Badge tone={acquisitionLabel(version) === "자료 보완 필요" ? "warn" : ""}>{acquisitionLabel(version)}</Badge></div>
    <p className="muted">다운로드한 자료와 페이지 근거를 대조하세요. 자료 확보와 분석 성공은 별개의 결과입니다.</p>
    <div className="source-grid">{version.sources.map(source => {
      const p = provenance(source); const state = sourceState(source, version);
      return <article className="source-card" key={source.id}><div className="section-heading"><h4>{sourceLabel(source)}</h4><Badge tone={state.includes("미확보") ? "warn" : ""}>{state}</Badge></div>
        <p className="muted">{source.media_type === "application/pdf" ? "PDF 문서" : source.media_type === "text/html" ? "HTML 원문" : "형식 확인 필요"}</p>
        {!!p.error && <p className="muted">{errorLabel(p.error)}</p>}
        {!state.includes("미확보") && !state.includes("미확인") ? <a className="source-link" href={"/api/notice/sources/" + source.id + "/download"}>원천자료 다운로드 ↗</a> : <p className="muted">확보 근거를 확인한 뒤 자료를 열 수 있습니다.</p>}
        <Technical value={source} />
      </article>;
    })}</div>
    {!version.sources.length && <p className="warning">등록된 원천자료가 없습니다.</p>}
    <div className="section-heading"><h3>2. 분석 결과와 근거 검토</h3>{current && <button className="primary" disabled={pending || running} onClick={() => requestAnalysis(version)}>기본 요건 추출</button>}</div>
    <p className="notice-note">현재 기능은 명시된 항목을 찾는 규칙 기반 기본 요건 추출입니다. 일반 공고의 의미 분석이나 전체 지원요건 확인을 보장하지 않으며, OCR·HWP·ZIP 분석은 지원하지 않습니다.</p><p className="muted">{running ? "분석이 진행 중입니다. 결과가 저장되면 화면이 갱신됩니다." : "분석 결과는 후보입니다. 원천 근거 확인과 사람의 검토를 거쳐 선택 요건을 확정하세요."}</p>
    {version.jobs.length > 0 && <div className="job-list">{version.jobs.map(job => <div key={job.id} data-testid="job-state"><Badge tone={["PARTIAL", "FAILED"].includes(job.state) ? "warn" : ""}>{stateLabel(job.state)}</Badge>{job.error && <span className="muted">{errorLabel(job.error)}</span>}{["FAILED", "PARTIAL"].includes(job.state) && current && <button disabled={pending || running} onClick={() => retry(job.id)}>분석 재시도</button>}</div>)}</div>}
    {!version.runs.length && <div className="empty panel">저장된 분석 결과가 없습니다. 원천자료를 확인한 뒤 기본 요건 추출을 요청하세요.</div>}
    {version.runs.slice().reverse().map((run, index) => <details className="analysis-run" key={run.id} open={index === 0}><summary>{version.runs.length - index}번째 분석 · {index === 0 ? "최근 결과" : "이전 분석 기록"} · 후보 {run.candidates.length}개</summary><section>
      <div className="section-heading"><h4>{version.runs.length - index}번째 분석 · 후보 {run.candidates.length}개</h4><Badge>{index === 0 ? "최근 분석" : "이전 분석 기록"}</Badge></div>
      {run.missing.length > 0 && <div className="warning"><strong>자료 확보·추출·분석 범위 제한</strong><ul>{run.missing.map((m, i) => <li key={i}>{errorLabel(record(m).reason)}</li>)}</ul><p>확정 범위는 직접 검토한 항목에 한정됩니다. 전체 요건 확인 완료를 의미하지 않습니다.</p></div>}
      {run.conflicts.length > 0 && <div className="warning"><strong>근거 충돌 · 원문 대조 필요</strong>{run.conflicts.map((c, i) => { const conflict = record(c); return <div key={i}><p>{kindLabel[text(conflict.kind)] ?? "요건"}에서 서로 다른 값이 확인되었습니다.</p><ul>{Array.isArray(conflict.values) && conflict.values.map((v, j) => <li key={j}>{text(v)}</li>)}</ul></div>; })}</div>}
      {run.candidates.map(c => <CandidateCard key={c.id} candidate={c} version={version} isCurrent={current} reload={refresh} />)}
    </section></details>)}
    <h3>3. 확정한 선택 요건 이력</h3><p className="muted">검토 대상과 범위를 보존합니다. 이전 버전의 확정은 현재 버전에 자동 적용되지 않습니다.</p>
    <div data-testid="confirmed">{version.confirmed.length ? version.confirmed.slice().reverse().map((v, index) => <details className="confirmed-card" key={v.id} open={index === 0}><summary>선택 요건 묶음 {v.ordinal} · {v.current_valid ? "현재 유효" : "과거 확정 기록"}</summary><article>
      <div className="section-heading"><h4>선택 요건 묶음 {v.ordinal}</h4><Badge tone={v.current_valid ? "success" : ""}>{v.current_valid ? "현재 유효" : "과거 확정 기록"}</Badge></div>
      <p>확정 범위: {v.scope}</p><p>검토 의견: {text(record(v.review).note)}</p><p className="muted">{dateLabel(record(v.review).created_at)}</p>
      <ul>{v.items.map((item, index) => { const row = record(item); return <li key={index}><strong>{kindLabel[text(row.kind)] ?? "요건"}</strong> · {text(row.content)}</li>; })}</ul>
      <Technical value={v} />
    </article></details>) : <div className="empty panel">아직 사람이 확정한 요건이 없습니다.</div>}</div>
    <Technical value={{ version_id: version.id, metadata, jobs: version.jobs, runs: version.runs }} />
  </>;
}

export default function Review() {
  const [actor, setActor] = useState<Actor | null>(null); const [username, setUsername] = useState(""); const [password, setPassword] = useState("");
  const [notices, setNotices] = useState<Summary[]>([]); const [catalog, setCatalog] = useState<Record<string, Detail>>({});
  const [selected, setSelected] = useState(""); const [detail, setDetail] = useState<Detail | null>(null);
  const [view, setView] = useState<View>("list"); const [search, setSearch] = useState(""); const [mode, setMode] = useState("LIVE"); const [demoContext, setDemoContext] = useState(false); const [catalogReady, setCatalogReady] = useState(false); const [reviewFilter, setReviewFilter] = useState("");
  const [error, setError] = useState(""); const [loading, setLoading] = useState(false); const [pending, setPending] = useState(false);
  const selection = useRef(""); const generation = useRef(0); const catalogRef = useRef<Record<string, Detail>>({});
  function navigate(nextView: View, id = selection.current, demo = demoContext) {
    const url = new URL(window.location.href);
    url.searchParams.set("view", nextView);
    if (id) url.searchParams.set("notice", id); else url.searchParams.delete("notice");
    if (demo) url.searchParams.set("context", "demo"); else url.searchParams.delete("context");
    if (url.search !== window.location.search) window.history.pushState(null, "", url.pathname + url.search);
    if (id !== selection.current) {
      selection.current = id; generation.current += 1; setDetail(null);
    }
    setSelected(id); setView(nextView); setError("");
    if (demo !== demoContext) setMode(demo ? "DEMO" : "LIVE");
    setDemoContext(demo);
  }
  function selectNotice(id: string) { navigate("review", id); }
  useEffect(() => {
    function syncLocation() {
      const params = new URLSearchParams(window.location.search);
      const candidate = params.get("notice") ?? "";
      const id = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(candidate) ? candidate : "";
      const target = params.get("view");
      const demo = params.get("context") === "demo";
      if (id !== selection.current) {
        selection.current = id; generation.current += 1; setDetail(null);
      }
      setSelected(id); setView(target === "review" || target === "collection" ? target : "list");
      setDemoContext(demo); setMode(demo ? "DEMO" : "LIVE"); setError("");
    }
    const initial = setTimeout(syncLocation, 0);
    window.addEventListener("popstate", syncLocation);
    return () => { clearTimeout(initial); window.removeEventListener("popstate", syncLocation); };
  }, []);
  const refresh = useCallback(async (reloadCatalog = false) => {
    const requestedId = selected; if (requestedId !== selection.current) return;
    const requestGeneration = ++generation.current;
    const isLatest = () => requestGeneration === generation.current && requestedId === selection.current;
    try {
      const who = await api<Actor>("/session"); if (!isLatest()) return; setActor(who);
      if (who.role !== "DATCO_OPERATOR") return;
      const list = await api<Summary[]>(""); if (!isLatest()) return; setNotices(list);
      const needed = list.filter(n => reloadCatalog || n.id === requestedId || !catalogRef.current[n.id] || catalogRef.current[n.id].current_ordinal !== n.current_ordinal);
      const loaded = await Promise.allSettled(needed.map(n => api<Detail>("/" + n.id)));
      if (!isLatest()) return;
      const next = { ...catalogRef.current }; let failure = false;
      loaded.forEach((result, index) => { if (result.status === "fulfilled" && result.value.id === needed[index].id) next[result.value.id] = result.value; else failure = true; });
      catalogRef.current = next; setCatalog(next); setCatalogReady(true);
      if (requestedId && loaded.some(r => r.status === "fulfilled" && r.value.id === requestedId)) setDetail(next[requestedId]);
      if (failure) setError("CATALOG_PARTIAL"); else setError("");
    } catch (e) { if (isLatest()) { const reason = e instanceof Error ? e.message : "LOAD_FAILED"; if (reason === "AUTHENTICATION_REQUIRED") { setActor(null); setDetail(null); setCatalogReady(false); setNotices([]); setCatalog({}); catalogRef.current = {}; } else setError(reason); } }
  }, [selected]);
  useEffect(() => { const initial = setTimeout(() => { void refresh(); }, 0); return () => clearTimeout(initial); }, [refresh]);
  useEffect(() => { if (!actor || !selected) return; const timer = setInterval(() => { void refresh(); }, 2000); return () => clearInterval(timer); }, [actor, selected, refresh]);
  async function login(event: React.FormEvent) { event.preventDefault(); setPending(true); try { setActor(await api<Actor>("/session", { username, password })); setPassword(""); setError(""); await refresh(); } catch (e) { setError(e instanceof Error ? e.message : "LOGIN_DENIED"); } finally { setPending(false); } }
  async function requestAnalysis(version: Version) { setPending(true); try { await api("/analysis", { expected_version: version.id, idempotency_key: crypto.randomUUID() }); await refresh(); } catch (e) { setError(e instanceof Error ? e.message : "ANALYSIS_FAILED"); } finally { setPending(false); } }
  async function retry(id: string) { setPending(true); try { await api("/jobs/" + id + "/retry", { idempotency_key: crypto.randomUUID() }); await refresh(); } catch (e) { setError(e instanceof Error ? e.message : "RETRY_FAILED"); } finally { setPending(false); } }
  async function reloadList() { setLoading(true); await refresh(true); setLoading(false); }
  const latest = (id: string) => catalog[id]?.versions.find(v => v.ordinal === catalog[id].current_ordinal);
  const liveCount = notices.filter(n => latest(n.id)?.mode === "LIVE").length;
  const canShowDetail = detail?.id === selected && (demoContext || detail.versions.find(v => v.ordinal === detail.current_ordinal)?.mode === "LIVE");
  const filtered = notices.filter(n => {
    const version = latest(n.id); const term = search.trim().toLocaleLowerCase();
    return (!term || (n.title + " " + text(version?.metadata.agency, "")).toLocaleLowerCase().includes(term)) && (demoContext ? (!mode || (mode === "LIVE" ? version?.mode === "LIVE" : !!version && isDemoMode(version.mode))) : version?.mode === "LIVE") && (!reviewFilter || reviewLabel(version) === reviewFilter);
  });
  return <div className="operator-app">
    <aside className="operator-sidebar"><a className="brand" href="/notice">DATCO<span>정부지원사업 운영관리</span></a><p className="sidebar-caption">공고 업무</p>
      <nav aria-label="공고 업무 메뉴"><button className={view === "list" ? "active" : ""} aria-current={view === "list" ? "page" : undefined} onClick={() => navigate("list")}>공고 목록</button><button className={view === "review" ? "active" : ""} aria-current={view === "review" ? "page" : undefined} onClick={() => navigate("review")}>공고 상세·요건 검토</button></nav>
      {actor?.role === "DATCO_OPERATOR" && <><p className="sidebar-caption">운영 도구</p><nav aria-label="운영 도구"><button className={view === "collection" ? "active" : ""} aria-current={view === "collection" ? "page" : undefined} onClick={() => navigate("collection")}>공고 수집관리</button></nav><details className="demo-entry"><summary>테스트·시연</summary><button onClick={() => navigate("list", "", true)}>테스트·시연 모드 열기</button></details></>}
      <div className="sidebar-footer">원천 근거 → 분석 후보<br />사람 검토 → 선택 요건 확정</div></aside>
    <div className="operator-body"><header className="operator-topbar"><span>정부지원사업 운영관리</span><Badge>{actor?.role === "DATCO_OPERATOR" ? "DATCO 운영자" : "로컬 업무 환경"}</Badge></header>
      <main className="operator-main">
        {!actor ? <div className="login-layout"><div><p className="eyebrow">DATCO OPERATIONS</p><h1>공고를 읽고,<br />근거로 검토하세요.</h1><p className="muted">수집된 지원사업 공고와 원천자료를 확인하고<br />검토한 요건을 업무 기록으로 남깁니다.</p></div><form className="panel login-card" onSubmit={login}><h2>운영자 로그인</h2><p className="muted">설정된 로컬 운영자 계정을 사용하세요.</p><label>아이디<input value={username} onChange={e => setUsername(e.target.value)} autoComplete="username" required /></label><label>비밀번호<input type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password" required /></label><button className="primary" disabled={pending}>{pending ? "로그인 중…" : "로그인"}</button></form></div> : actor.role !== "DATCO_OPERATOR" ? <div className="warning">공고 운영 화면에 접근할 권한이 없습니다. 운영자 계정으로 접속해 주세요.</div> : <>
          {demoContext && <div className="warning demo-context"><strong>테스트·시연 모드</strong><p>합성 Demo/TEST 자료와 Snapshot 기능을 조회합니다. 실제 공고 업무와 구분되며 Backend의 운영자 권한 검증은 그대로 적용됩니다.</p><button onClick={() => navigate("list", "", false)}>실제 공고 업무로 돌아가기</button></div>}
          <div hidden={view !== "list"}>
            <div className="section-heading"><div><p className="eyebrow">NOTICE CATALOG</p><h1>지원사업 공고</h1><p className="muted">저장된 실제 공고의 사업 내용·접수기간·요건 검토 진행을 확인하세요.</p></div><button disabled={loading} onClick={reloadList}>{loading ? "조회 중…" : "목록 새로고침"}</button></div>
            <div className="catalog-filters"><label className="search-field">공고 검색<input type="search" value={search} onChange={e => setSearch(e.target.value)} placeholder="사업명 또는 기관 검색" /></label>{demoContext && <label>자료 원천<select aria-label="자료 원천" value={mode} onChange={e => setMode(e.target.value)}><option value="">전체 원천</option><option value="LIVE">실제 공고 · Live</option><option value="DEMO">데모 자료</option></select></label>}<label>검토 진행<select aria-label="검토 진행" value={reviewFilter} onChange={e => setReviewFilter(e.target.value)}><option value="">전체 상태</option>{["미분석", "검토 필요", "자료 보완 요청", "선택 요건 확정", "조회 필요"].map(s => <option key={s}>{s}</option>)}</select></label></div>
            {catalogReady ? <p className="list-count">조회 결과 <strong>{filtered.length}건</strong> <span className="muted">/ {demoContext ? "저장된 전체 자료 " + notices.length : "저장된 실제 공고 " + liveCount}건</span></p> : <p className="list-count">공고 원천 정보를 조회 중입니다.</p>}
            <div className="table-scroll panel"><table className="notice-table"><thead><tr><th>사업명 / 원천</th><th>담당 기관</th><th>접수 기간</th><th>지원 분야 / 대상 분류</th><th>검토 진행</th><th><span className="sr-only">공고 상세</span></th></tr></thead><tbody>{filtered.map(n => { const v = latest(n.id); return <tr key={n.id}><td><button className="title-button" onClick={() => selectNotice(n.id)}>{n.title}</button><div className="row-subline"><Badge tone={v?.mode === "LIVE" ? "live" : "demo"}>{v ? modeLabel(v.mode) : "원천 조회 필요"}</Badge><span className="muted">버전 {n.current_ordinal}</span></div></td><td>{text(v?.metadata.agency)}</td><td>{text(v?.metadata.period_original, "기간 정보 없음")}<p className="muted">공식 모집 상태 미확인</p></td><td>{text(v?.metadata.major_category)}<p className="muted">대상 분류: {text(v?.metadata.target, "대상 정보 없음")}</p></td><td><Badge>{reviewLabel(v)}</Badge></td><td><button aria-label={n.title + " 상세 보기"} onClick={() => selectNotice(n.id)}>상세 보기</button></td></tr>; })}</tbody></table>{!filtered.length && <div className="empty">{!catalogReady ? "공고 원천 정보를 조회 중입니다." : error === "CATALOG_PARTIAL" ? "일부 공고 원천을 확인하지 못했습니다. 목록을 다시 조회해 주세요." : !demoContext && !liveCount ? "현재 저장된 실제 공고가 없습니다. 운영 도구의 공고 수집관리에서 입력할 수 있습니다." : "조건에 맞는 공고가 없습니다. 검색 조건을 바꾸어 확인하세요."}</div>}</div>
            <p className="notice-note">저장된 공고만 표시합니다. 기업마당 전체 건수나 전체 수집 완료를 의미하지 않습니다. Live 수집 여부와 공식 모집 중 여부는 별개이며, 제공되지 않은 기관·기간·상태는 미확인으로 표시합니다.</p>
          </div>
          {view === "collection" && <Collection key={demoContext ? "demo" : "live"} demoContext={demoContext} onSelectNotice={selectNotice} />}
          <div hidden={view !== "review"}>
            <div className="section-heading"><div><p className="eyebrow">SOURCE & HUMAN REVIEW</p><h1>공고 분석·검토</h1><p className="muted">공고 버전과 원문을 확인하고, 근거가 있는 항목만 확정하세요.</p></div><button onClick={() => navigate("list")}>공고 목록으로</button></div>
            {!selected && <div className="empty panel">공고 목록에서 사업명을 클릭해 검토할 공고를 선택하세요.</div>}
            {selected && detail?.id !== selected && <div className="empty panel" role="status">선택한 공고를 불러오는 중입니다.</div>}
            {detail?.id === selected && !canShowDetail && <div className="warning">이 공고는 Live 원천으로 확인되지 않았습니다. 일반 업무에서는 실제 공고를 조회합니다.<button onClick={() => navigate("review", selected, true)}>테스트·시연 모드로 열기</button></div>}
            {canShowDetail && detail && <><h2 className="notice-title">{detail.title}</h2>{detail.versions.map(version => {
              const current = version.ordinal === detail.current_ordinal;
              const content = <section data-testid="notice-version" data-notice-id={detail.id} className="version-panel"><VersionPanel version={version} current={current} pending={pending} requestAnalysis={requestAnalysis} retry={retry} refresh={refresh} /></section>;
              return current ? <div key={version.id}>{content}</div> : <details key={version.id} className="version-history"><summary>이전 버전 {version.ordinal} · {modeLabel(version.mode)} · 확정 기록 {version.confirmed.length}개</summary>{content}</details>;
            })}</>}
          </div>
        </>}
        {error && <div role="alert" className="warning">{error === "CATALOG_PARTIAL" ? "일부 공고 상세를 조회하지 못했습니다. 목록 새로고침으로 다시 확인해 주세요." : errorLabel(error)}<Technical value={{ reason: error }} /></div>}
      </main>
    </div>
  </div>;
}
