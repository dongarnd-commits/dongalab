"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import type { components } from "@/generated/api";
type Job = components["schemas"]["CollectionJobResponse"];
async function request<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch("/api/notice/collections" + path, {
    method: body === undefined ? "GET" : "POST", headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body), cache: "no-store",
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.reason ?? "Collection request failed");
  return data as T;
}
export default function Collection({ onSelectNotice }: { onSelectNotice: (id: string) => void }) {
  const [mode, setMode] = useState<"LIVE" | "SNAPSHOT">("SNAPSHOT");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const generation = useRef(0);
  const reload = useCallback(async () => {
    const current = ++generation.current;
    try {
      const result = await request<Job[]>("");
      if (current === generation.current) setJobs(result);
    } catch (e) { if (current === generation.current) setError(e instanceof Error ? e.message : "Collection history unavailable"); }
  }, []);
  useEffect(() => {
    const initial = setTimeout(() => { void reload(); }, 0);
    const interval = setInterval(() => { void reload(); }, 2000);
    return () => { clearTimeout(initial); clearInterval(interval); generation.current += 1; };
  }, [reload]);
  async function collect() {
    setPending(true); setError("");
    try {
      await request<Job>("", { mode, idempotency_key: crypto.randomUUID(), page_unit: 2, max_pages: 3 });
      await reload();
    } catch (e) { setError(e instanceof Error ? e.message : "Collection request failed"); }
    finally { setPending(false); }
  }
  async function retry(id: string) {
    try { await request("/" + id + "/retry", { idempotency_key: crypto.randomUUID() }); await reload(); }
    catch (e) { setError(e instanceof Error ? e.message : "Collection retry failed"); }
  }
  return <section aria-label="Bizinfo collection">
    <h2>Bizinfo Collection</h2>
    <label>Collection source <select value={mode} onChange={e => setMode(e.target.value as "LIVE" | "SNAPSHOT")}>
      <option value="SNAPSHOT">SANITIZED / DEMO snapshot</option><option value="LIVE">Live Bizinfo API</option>
    </select></label>
    <p>{mode === "SNAPSHOT" ? "Synthetic sanitized input; does not prove a successful Live collection." : "Bounded Live collection: at most 3 pages of 2 notices. A limit or acquisition failure remains Partial."}</p>
    <button disabled={pending} onClick={collect}>Request collection</button>
    {error && <p role="alert">{error}</p>}
    {jobs.slice(-20).reverse().map(job => {
      const attempts = job.attempts ?? [];
      const latest = attempts.at(-1);
      const records = latest?.pages.flatMap(page => page.records) ?? [];
      const counts = records.reduce<Record<string, number>>((result, record) => {
        result[record.outcome] = (result[record.outcome] ?? 0) + 1; return result;
      }, {});
      return <article key={job.id} data-testid="collection-job" data-job-id={job.id}>
        <h3>{String(job.payload.mode)} collection - {job.state}</h3>
        <p>Requested: {job.created_at} - Error: {job.error ?? "none"}</p>
        <p>Latest attempt: {latest?.ordinal ?? "waiting"} - Results: {JSON.stringify(counts)}</p>
        {["PARTIAL", "FAILED"].includes(job.state) && <button onClick={() => retry(job.id)}>Retry collection</button>}
        {attempts.map(attempt => <details key={attempt.id} open={attempt.id === latest?.id}>
          <summary>Attempt {attempt.ordinal}: {attempt.state} {attempt.error}</summary>
          {attempt.pages.map(page => <section key={page.id}>
            <p>Page {page.page_number}: {page.state} - Observed: {page.observed_count} - Reported total: {page.expected_total ?? "unknown"}</p>
            <p>{page.error} {page.warnings.join(", ")}</p>
            {page.records.map(record => <div key={record.id}>
              <p>{record.external_id ?? "Unidentified item"}: {record.outcome} {record.error}</p>
              <p>Notice version: {record.notice_version_id ?? "not imported"}</p>
              <p>Sources: {JSON.stringify(record.acquisitions)}</p>
              {record.notice_id && <button onClick={() => onSelectNotice(record.notice_id!)}>Review collected notice</button>}
            </div>)}
          </section>)}
        </details>)}
      </article>;
    })}
  </section>;
}
