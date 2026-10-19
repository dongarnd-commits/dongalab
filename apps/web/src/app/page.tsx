import WorkspaceHome from "./_workspace/home";
import type { components } from "@/generated/api";
export const dynamic = "force-dynamic";
type Health = components["schemas"]["HealthResponse"];
async function readiness(path: string, service: Health["service"]): Promise<boolean> {
  try {
    const response = await fetch(new URL(path, process.env.API_ORIGIN ?? "http://127.0.0.1:8000"), { cache: "no-store", signal: AbortSignal.timeout(5000) });
    if (!response.ok) return false;
    const body: Health = await response.json();
    return body.status === "ready" && body.service === service;
  } catch { return false; }
}
export default async function Home() {
  const [api, database] = await Promise.all([readiness("/health", "api"), readiness("/health/db", "database")]);
  return <><WorkspaceHome/><section className="workspace-home" aria-label="실제 서비스 연결 상태"><h2>서비스 연결 상태</h2><dl><div><dt>Web</dt><dd data-testid="web-status">READY</dd></div><div><dt>API</dt><dd data-testid="api-status">{api?"READY":"NOT READY"}</dd></div><div><dt>Database</dt><dd data-testid="database-status">{database?"READY":"NOT READY"}</dd></div></dl>{(!api||!database)&&<p role="status">서비스 연결을 확인해 주세요.</p>}</section></>;
}
