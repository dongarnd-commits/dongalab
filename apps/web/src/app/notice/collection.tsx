
"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import type { components } from "@/generated/api";
import { Badge, Technical, dateLabel, errorLabel, modeLabel, record, stateLabel, text } from "./presentation";
type Job = components["schemas"]["CollectionJobResponse"];
async function request<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch("/api/notice/collections" + path, {
    method: body === undefined ? "GET" : "POST", headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body), cache: "no-store",
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.reason ?? "COLLECTION_FAILED");
  return data as T;
}
export default function Collection({ onSelectNotice, demoContext }: { onSelectNotice: (id: string) => void; demoContext: boolean }) {
  const [mode, setMode] = useState<"LIVE" | "SNAPSHOT">(demoContext ? "SNAPSHOT" : "LIVE");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [historyLimit, setHistoryLimit] = useState(20);
  const [titles, setTitles] = useState<Record<string, string>>({});
  const [pending, setPending] = useState("");
  const [error, setError] = useState("");
  const generation = useRef(0);
  const reload = useCallback(async () => {
    const current = ++generation.current;
    try {
      const result = await request<Job[]>("");
      const response = await fetch("/api/notice", { cache: "no-store" });
      const notices = await response.json();
      if (!response.ok) throw new Error(notices.reason ?? "COLLECTION_FAILED");
      if (current === generation.current) {
        setJobs(result);
        setTitles(Object.fromEntries((notices as components["schemas"]["NoticeSummary"][]).map(n => [n.id, n.title])));
      }
    } catch (e) { if (current === generation.current) setError(e instanceof Error ? e.message : "COLLECTION_FAILED"); }
  }, []);
  useEffect(() => {
    const initial = setTimeout(() => { void reload(); }, 0);
    const interval = setInterval(() => { void reload(); }, 2500);
    return () => { clearTimeout(initial); clearInterval(interval); generation.current += 1; };
  }, [reload]);
  async function collect() {
    setPending("collection"); setError("");
    try { await request<Job>("", { mode: demoContext ? mode : "LIVE", idempotency_key: crypto.randomUUID(), page_unit: 2, max_pages: 3 }); await reload(); }
    catch (e) { setError(e instanceof Error ? e.message : "COLLECTION_FAILED"); }
    finally { setPending(""); }
  }
  async function retry(id: string) {
    setPending(id); setError("");
    try { await request("/" + id + "/retry", { idempotency_key: crypto.randomUUID() }); await reload(); }
    catch (e) { setError(e instanceof Error ? e.message : "COLLECTION_FAILED"); }
    finally { setPending(""); }
  }
  const visibleJobs = jobs.filter(job => demoContext || job.payload.mode === "LIVE");
  return <section aria-label="기업마당 수집관리">
    <div className="section-heading"><div><p className="eyebrow">운영 도구 · 공고 입력 관리</p><h2>기업마당 수집관리</h2><p className="muted">수집 결과와 자료 확보 범위를 확인한 뒤 공고 검토로 이동하세요.</p></div></div>
    <div className="panel collection-request">
      {demoContext ? <label>수집 원천<select aria-label="수집 원천" value={mode} onChange={e => setMode(e.target.value as "LIVE" | "SNAPSHOT")}>
        <option value="SNAPSHOT">데모 자료 · Snapshot</option><option value="LIVE">실제 기업마당 API · Live</option>
      </select></label> : <div><strong>실제 기업마당 API · Live 수집</strong><p className="muted">승인된 운영자 계정으로 요청합니다.</p></div>}
      <p className="muted">{mode === "SNAPSHOT" ? "검증된 합성 데모 입력입니다. 실제 공고나 Live 수집 성공을 의미하지 않습니다." : "실제 기업마당에 요청합니다. 최대 3페이지 · 페이지당 2건이며, 상한 도달 또는 자료 확보 실패는 부분 완료로 기록됩니다."}</p>
      <button className="primary" disabled={!!pending} onClick={collect}>{pending === "collection" ? "수집 요청 중…" : "수집 요청"}</button>
    </div>
    <p className="notice-note">수집 완료는 요건 확정이 아닙니다. 미지원 ZIP·HWP 자료는 미확보로 남으며, Snapshot으로 자동 전환하지 않습니다.</p>
    {error && <div role="alert" className="warning">{errorLabel(error)}<Technical value={{ reason: error }} /></div>}
    <div className="section-heading"><h3>최근 수집 이력</h3><span className="muted">최근 {Math.min(historyLimit, visibleJobs.length)}개 요청</span></div>
    {!visibleJobs.length && <div className="empty panel">저장된 수집 이력이 없습니다. 원천을 선택해 첫 수집을 요청하세요.</div>}
    {visibleJobs.slice(-historyLimit).reverse().map(job => {
      const attempts = job.attempts ?? []; const latest = attempts.at(-1);
      const records = latest?.pages.flatMap(page => page.records) ?? [];
      const counts = records.reduce<Record<string, number>>((result, row) => { result[row.outcome] = (result[row.outcome] ?? 0) + 1; return result; }, {});
      const failedFiles = records.flatMap(row => row.acquisitions).filter(a => a.status === "FAILED").length;
      return <article className="panel collection-job" key={job.id} data-testid="collection-job" data-job-id={job.id}>
        <div className="section-heading"><h3>{modeLabel(text(job.payload.mode))}</h3><Badge tone={job.state === "PARTIAL" || job.state === "FAILED" ? "warn" : job.state === "SUCCEEDED" ? "success" : ""}>{stateLabel(job.state)}</Badge></div>
        <p className="muted">{dateLabel(job.created_at)} · {latest ? latest.ordinal + "번째 실행" : "실행 대기"}</p>
        <div className="result-counts">{[["NEW", "신규"], ["UNCHANGED", "변경 없음"], ["NEW_VERSION", "변경"], ["FAILED", "실패"], ["CONFLICT", "충돌"], ["DUPLICATE", "중복 제외"]].map(([key, label]) => <span key={key}>{label} <strong>{counts[key] ?? 0}건</strong></span>)}</div>
        {!!failedFiles && <p className="warning">미확보 자료 {failedFiles}개 · 목록 저장과 파일 확보는 별개의 결과입니다.</p>}
        {job.state === "PARTIAL" && <p className="warning">일부만 처리되었습니다. 누락 자료와 미수집 범위를 확인하세요.</p>}
        {job.error && <p className="muted">{errorLabel(job.error)}</p>}
        {["PARTIAL", "FAILED"].includes(job.state) && <button disabled={!!pending} onClick={() => retry(job.id)}>수집 재시도</button>}
        <details className="collection-results" open>
          <summary>공고별 처리 결과 · {records.length}건</summary>
          {records.map(row => <div key={row.id} className="collection-record">
            <h4>{row.notice_id ? titles[row.notice_id] ?? "공고 제목 조회 중" : "공고 연결 실패"}</h4><div className="section-heading"><Badge tone={["FAILED", "CONFLICT"].includes(row.outcome) ? "warn" : ""}>{stateLabel(row.outcome)}</Badge>{row.notice_id && <button onClick={() => onSelectNotice(row.notice_id!)}>수집 공고 검토</button>}</div>
            {row.error && <p className="muted">{errorLabel(row.error)}</p>}
            <ul className="acquisition-list">{row.acquisitions.map((a, index) => <li key={index}>{({ pblancUrl: "상세 원문", flpthNm: "첨부자료", printFlpthNm: "본문 출력 참조" } as Record<string, string>)[text(a.field)] ?? "참조자료"} <Badge tone={a.status === "FAILED" ? "warn" : ""}>{stateLabel(text(a.status))}</Badge>{!!a.error && <span className="muted"> · {errorLabel(a.error)}</span>}</li>)}</ul>
          </div>)}
        </details>
        <details className="attempt-history"><summary>실행 이력 · {attempts.length}회</summary>{attempts.map(attempt => <div key={attempt.id}><p>{attempt.ordinal}번째 실행 · {stateLabel(attempt.state)}</p>{attempt.pages.map(page => <p key={page.id} className="muted">{page.page_number}페이지 · 관찰 {page.observed_count}건 · 원천 보고 전체 건수 {page.expected_total ?? "미제공"} · {stateLabel(page.state)}{page.error ? " · " + errorLabel(page.error) : ""}{page.warnings.map(w => " · " + errorLabel(w)).join("")}</p>)}</div>)}</details>
        <Technical value={record(job)} />
      </article>;
    })}
    {visibleJobs.length > historyLimit && <button onClick={() => setHistoryLimit(value => value + 20)}>이전 수집 이력 더 보기</button>}
  </section>;
}
