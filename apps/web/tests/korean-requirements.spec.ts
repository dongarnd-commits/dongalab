import { test, expect } from "@playwright/test";
import { spawn } from "node:child_process";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

test("stored real Korean documents traverse isolated Job, Evidence, Human Review and refresh", async ({ page, request }) => {
  test.setTimeout(120000);
  const runtime = resolve("../../storage/private/runtime/ko-browser");
  mkdirSync(runtime, { recursive: true });
  const child = spawn(resolve("../api/.venv/Scripts/python.exe"), ["tests/ko_browser_server.py", runtime], {
    cwd: resolve("../api"), env: { ...process.env, PYTHONPATH: ".", PYTHONIOENCODING: "utf-8", DATCO_TEST_STORED_KO: "1" }, windowsHide: true,
  });
  let buffer = "";
  let rolledBack = false;
  child.stdout.on("data", chunk => { if (String(chunk).includes("ISOLATED_SCHEMA_ROLLED_BACK")) rolledBack = true; });
  // Runtime-only generated credentials are consumed here; never logged or saved to Git.
  const ready = new Promise<{ port: number; username: string; password: string }>((resolveReady, reject) => {
    child.stdout.on("data", chunk => {
      buffer += String(chunk);
      const first = buffer.split(/\r?\n/).find(line => line.startsWith("{"));
      if (first) { try { resolveReady(JSON.parse(first)); } catch { /* Wait for complete line. */ } }
    });
    child.on("error", reject);
    child.on("exit", code => { if (!buffer.includes('"port"')) reject(new Error("Isolated Korean input server failed: " + code)); });
  });
  let base = "";
  try {
    const credentials = await ready;
    base = "http://127.0.0.1:" + credentials.port;
    await expect.poll(async () => { try { return (await request.get(base + "/health")).status(); } catch { return 0; } }).toBe(200);
    await page.route("**/api/notice**", async route => {
      const url = new URL(route.request().url());
      const response = await route.fetch({ url: base + url.pathname.replace(/^\/api/, "") + url.search });
      await route.fulfill({ response }); // Actual isolated FastAPI/PostgreSQL response, no candidate mocks.
    });
    await page.goto("/notice");
    await page.getByLabel("아이디", { exact: true }).fill(credentials.username);
    await page.getByLabel("비밀번호", { exact: true }).fill(credentials.password);
    await page.getByRole("button", { name: "로그인", exact: true }).click();
    await page.locator(".title-button").filter({ hasText: "에너지기술" }).click();
    const version = page.getByTestId("notice-version").last();
    await expect(version).toBeVisible();
    await expect(version.getByText("대상 분류 · API 제공값", { exact: true })).toBeVisible();
    await expect(version.getByTestId("candidate")).toHaveCount(0);
    await page.getByRole("button", { name: "기본 요건 추출", exact: true }).click();
    const candidate = version.getByTestId("candidate").filter({ hasText: "필수 제출서류" }).filter({ hasText: "PDF 15페이지" }).last();
    await expect(candidate).toBeVisible({ timeout: 30000 });
    await expect(page.getByTestId("notice-summary")).not.toContainText("<p");
    await expect(page.getByTestId("notice-summary")).not.toContainText("&nbsp;");
    const contents = candidate.locator(".candidate-content-full");
    await expect(contents).not.toHaveAttribute("open");
    await contents.locator("summary").click();
    await expect(candidate.locator(".candidate-content")).toBeVisible();
    expect(await candidate.locator(".candidate-content").evaluate(element => getComputedStyle(element).whiteSpace)).toBe("pre-wrap");
    await expect(candidate).toContainText("사업자등록증");
    await expect(candidate).toContainText("연구개발계획서");
    await expect(candidate.locator("blockquote")).toContainText("붙임2 제출 서류 사항");
    await expect(version).toContainText("명시된 한국어 절의 일부 요건만 분석했습니다");
    await expect(candidate.getByRole("button", { name: "선택 요건 확정" })).toBeDisabled();
    const download = page.waitForEvent("download");
    await candidate.getByRole("link", { name: "원천자료 다운로드 ↗" }).click();
    expect((await download).suggestedFilename()).toBe("notice-source");
    await candidate.getByRole("checkbox").check();
    await candidate.getByLabel("검토 의견", { exact: true }).fill("격리된 검증 사본의 실제 PDF 15페이지와 제출서류 조건을 확인했습니다.");
    await expect(candidate.getByLabel("충돌 해소 의견", { exact: true })).toHaveCount(0);
    const confirmedResponse = page.waitForResponse(r => r.url().endsWith("/confirm") && r.status() === 200);
    await candidate.getByRole("button", { name: "선택 요건 확정" }).click();
    const confirmed = await (await confirmedResponse).json();
    await expect(version.getByTestId("confirmed")).toContainText("사업자등록증");
    await page.reload();
    await expect(page.getByTestId("notice-version").last().getByTestId("confirmed")).toContainText("사업자등록증");
    const detail = await page.evaluate(async () => {
      const id = new URL(location.href).searchParams.get("notice");
      return (await fetch("/api/notice/" + id)).json();
    });
    expect(detail.versions[0].confirmed).toHaveLength(1);
    expect(detail.versions[0].confirmed[0].id).toBe(confirmed.id);
    expect(detail.versions[0].confirmed[0].review.outcome).toBe("CONFIRM");
    expect(detail.versions[0].jobs[0].state).toBe("PARTIAL");
    expect(detail.versions[0].runs[0].conflicts).toHaveLength(0);
    expect(detail.versions[0].runs[0].candidates.some((c: { kind: string; content: string }) => c.kind === "APPLICATION_PERIOD" && c.content.includes("18:00"))).toBeTruthy();
    expect(detail.versions[0].runs[0].provider_version).toBe("labelled-clauses-ko-v3");
  } finally {
    if (base) await request.post(base + "/__test/stop");
    await Promise.race([new Promise<void>(done => child.once("exit", () => done())), new Promise<void>(done => setTimeout(done, 10000))]);
    if (child.exitCode === null) child.kill();
  }
  expect(rolledBack).toBeTruthy();
});
