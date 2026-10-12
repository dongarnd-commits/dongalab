"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import type { components } from "@/generated/api";
import Collection from "./collection";

type Summary = components["schemas"]["NoticeSummary"];
type Detail = components["schemas"]["NoticeDetail"];
type Version = components["schemas"]["VersionResponse"];
type Candidate = components["schemas"]["CandidateResponse"];
type Actor = components["schemas"]["ActorResponse"];

async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch("/api/notice" + path, {
    method: body === undefined ? "GET" : "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.reason ?? "Request failed");
  return data as T;
}

function CandidateCard({ candidate, version, isCurrent, reload }: { candidate: Candidate; version: Version; isCurrent: boolean; reload: () => Promise<void> }) {
  const [official, setOfficial] = useState(false);
  const [note, setNote] = useState("");
  const [resolution, setResolution] = useState("");
  const [error, setError] = useState("");
  const reviewed = candidate.reviews.length > 0;
  const conflict = version.runs.find(run => run.candidates.some(c => c.id === candidate.id))?.conflicts.length;
  async function confirm() {
    try {
      await api("/candidates/" + candidate.id + "/confirm", {
        expected_version: version.id, official_verified: official, note,
        scope: "Only the selected source clause", conflict_resolution: resolution,
      });
      await reload();
    } catch (e) { setError(e instanceof Error ? e.message : "Confirmation failed"); }
  }
  async function moreSource() {
    try {
      await api("/candidates/" + candidate.id + "/more-source", { expected_version: version.id, note });
      await reload();
    } catch (e) { setError(e instanceof Error ? e.message : "Review failed"); }
  }
  return <article data-testid="candidate" style={{ border: "1px solid #cbd5e1", padding: 16, margin: "16px 0" }}>
    <h3>{candidate.kind}</h3><p>{candidate.content}</p>
    <p>Reason: {candidate.reason}</p>
    <p>Evidence: {candidate.evidence.descriptor}</p><blockquote>{candidate.evidence.text}</blockquote>
    <a href={"/api/notice/sources/" + candidate.evidence.source_id + "/download"}>Download source</a>
    {reviewed ? <p>Review recorded: {JSON.stringify(candidate.reviews)}</p> : <>
      <p><label><input type="checkbox" checked={official} onChange={e => setOfficial(e.target.checked)} /> I reviewed the source and verified its basis for this clause within the displayed {version.mode} source context.</label></p>
      <p><label>Review note <input value={note} onChange={e => setNote(e.target.value)} /></label></p>
      {!!conflict && <p><label>Conflict resolution <input value={resolution} onChange={e => setResolution(e.target.value)} /></label></p>}
      <button disabled={!isCurrent || !official || !note.trim() || (!!conflict && !resolution.trim())} onClick={confirm}>Confirm selected requirement</button>
      <button disabled={!isCurrent || !note.trim()} onClick={moreSource}>Request more source review</button>
    </>}
    {error && <p role="alert">{error}</p>}
  </article>;
}

export default function Review() {
  const [actor, setActor] = useState<Actor | null>(null);
  const [username, setUsername] = useState("operator");
  const [password, setPassword] = useState("");
  const [notices, setNotices] = useState<Summary[]>([]);
  const [selected, setSelected] = useState("");
  const [detail, setDetail] = useState<Detail | null>(null);
  const [error, setError] = useState("");
  const selection = useRef("");
  const generation = useRef(0);
  function selectNotice(id: string) {
    selection.current = id;
    generation.current += 1;
    setDetail(null);
    setSelected(id);
    setError("");
  }
  const refresh = useCallback(async () => {
    const requestedId = selected;
    if (requestedId !== selection.current) return;
    const requestGeneration = ++generation.current;
    const isLatest = () => requestGeneration === generation.current && requestedId === selection.current;
    try {
      const who = await api<Actor>("/session");
      if (!isLatest()) return;
      setActor(who);
      const list = await api<Summary[]>("");
      if (!isLatest()) return;
      setNotices(list);
      if (requestedId) {
        const loaded = await api<Detail>("/" + requestedId);
        if (isLatest() && loaded.id === requestedId) setDetail(loaded);
      }
    } catch (e) { if (isLatest()) setError(e instanceof Error ? e.message : "Load failed"); }
  }, [selected]);
  useEffect(() => {
    const initial = setTimeout(() => { void refresh(); }, 0);
    return () => clearTimeout(initial);
  }, [refresh]);
  useEffect(() => {
    if (!actor || !selected) return;
    const timer = setInterval(() => { void refresh(); }, 1500);
    return () => clearInterval(timer);
  }, [actor, selected, refresh]);
  async function login(event: React.FormEvent) {
    event.preventDefault();
    try {
      setActor(await api<Actor>("/session", { username, password }));
      setPassword("");
      setError("");
      await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : "Login failed"); }
  }
  async function requestAnalysis(version: Version) {
    try {
      await api("/analysis", { expected_version: version.id, idempotency_key: crypto.randomUUID() });
      setError("");
      await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : "Analysis request failed"); }
  }
  async function retry(id: string) {
    try { await api("/jobs/" + id + "/retry", { idempotency_key: crypto.randomUUID() }); await refresh(); }
    catch (e) { setError(e instanceof Error ? e.message : "Retry failed"); }
  }
  return <main>
    <h1>Notice Requirement Review</h1>
    <p>Inputs include LIVE and SANITIZED/DEMO sources. Check each version mode and source provenance; candidates require human review.</p>
    {!actor ? <form onSubmit={login}>
      <p><label>Username <input value={username} onChange={e => setUsername(e.target.value)} autoComplete="username" /></label></p>
      <p><label>Password <input type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password" /></label></p>
      <button>Login</button>
    </form> : <>
      <p>Signed in: {actor.role}</p>
      {actor.role === "DATCO_OPERATOR" && <Collection onSelectNotice={selectNotice} />}
      <label htmlFor="notice-choice">Notice</label><select id="notice-choice" value={selected} onChange={e => selectNotice(e.target.value)}>
        <option value="">Select a notice</option>
        {notices.map(n => <option key={n.id} value={n.id}>{n.title}</option>)}
      </select>
      {detail?.id === selected && detail.versions.map(version => <section key={version.id} data-testid="notice-version" data-notice-id={detail.id}>
        <h2>Notice version {version.ordinal} - {version.mode}</h2>
        <p>Metadata: {JSON.stringify(version.metadata)}</p>
        {version.ordinal === detail.current_ordinal ? <button onClick={() => requestAnalysis(version)}>Request analysis</button> : <p>Historical input ? current confirmation unavailable.</p>}
        <ul>{version.sources.map(s => <li key={s.id}>{s.name}: {s.provenance}</li>)}</ul>
        <h3>Job execution</h3>
        {version.jobs.map(job => <p key={job.id} data-testid="job-state">{job.state} {job.error}
          {["FAILED", "PARTIAL"].includes(job.state) && version.ordinal === detail.current_ordinal && <button onClick={() => retry(job.id)}>Retry analysis</button>}
        </p>)}
        <h3>Requirement candidates ? awaiting human review</h3>
        {version.runs.map(run => <section key={run.id}>
          <p>Run: {run.id} - Input: {run.version_id} - {run.provider_version}</p>
          {run.missing.length > 0 && <p>Partial input / Missing sources: {JSON.stringify(run.missing)}</p>}
          {run.conflicts.length > 0 && <p>Conflicting evidence: {JSON.stringify(run.conflicts)}</p>}
          {run.candidates.map(c => <CandidateCard key={c.id} candidate={c} version={version} isCurrent={version.ordinal === detail.current_ordinal} reload={refresh} />)}
        </section>)}
        <h3>Confirmed Requirement History</h3>
        <div data-testid="confirmed">{version.confirmed.length ? version.confirmed.map(v => <section key={v.id}>
          <p>Requirement version {v.ordinal} - Scope: {v.scope}</p>
          <p>Review / Actor / Time: {JSON.stringify(v.review)}</p>
          <p>Confirmed items and evidence: {JSON.stringify(v.items)}</p>
        </section>) : <p>No confirmed requirement.</p>}</div>
      </section>)}
    </>}
    {error && <p role="alert">{error}</p>}
  </main>;
}
