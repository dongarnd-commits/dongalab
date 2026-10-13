import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
function account() {
  const env = readFileSync("../../.env", "utf8");
  const value = (key: string) => env.split(/\r?\n/).find(line => line.startsWith(key + "="))?.slice(key.length + 1) ?? "";
  return { username: value("DEMO_OPERATOR_USER"), password: value("DEMO_OPERATOR_PASSWORD") };
}
test("Operator snapshot collection persists, deduplicates and enters existing human review", async ({ page }) => {
  const credentials = account();
  await page.route("**/api/notice/collections", async route => {
    if (route.request().method() === "POST" && route.request().postDataJSON().mode !== "SNAPSHOT") {
      await route.abort("blockedbyclient");
      throw new Error("Snapshot regression must not request Live collection");
    }
    await route.continue();
  });
  await page.goto("/notice");
  await page.getByLabel("아이디", { exact: true }).fill(credentials.username);
  await page.getByLabel("비밀번호", { exact: true }).fill(credentials.password);
  await page.getByRole("button", { name: "로그인", exact: true }).click();
  await page.locator(".demo-entry summary").click();
  await page.getByRole("button", { name: "테스트·시연 모드 열기", exact: true }).click();
  await page.getByRole("button", { name: "공고 수집관리", exact: true }).click();
  const panel = page.getByRole("region", { name: "기업마당 수집관리" });
  await expect(panel).toBeVisible();
  await panel.getByLabel("수집 원천").selectOption("SNAPSHOT");
  const request = page.waitForResponse(response => response.url().endsWith("/api/notice/collections") && response.request().method() === "POST" && response.status() === 200);
  await panel.getByRole("button", { name: "수집 요청", exact: true }).click();
  const job = await (await request).json();
  expect(job.payload.mode).toBe("SNAPSHOT");
  const article = panel.locator('[data-job-id="' + job.id + '"]');
  await expect(article).toContainText("처리 완료", { timeout: 25000 });
  await expect(article).toContainText("PBLN_DEMO_INGESTION_001");
  await expect(article).toContainText("확보");
  const before = await article.innerText();
  await page.reload();
  await page.getByRole("button", { name: "공고 수집관리", exact: true }).click();
  await expect(panel.locator('[data-job-id="' + job.id + '"]')).toHaveText(before, { useInnerText: true });
  const stored = await (await page.request.get("/api/notice/collections/" + job.id)).json();
  const record = stored.attempts.at(-1).pages[0].records[0];
  await panel.locator('[data-job-id="' + job.id + '"]').getByRole("button", { name: "수집 공고 검토" }).first().click();
  expect(new URL(page.url()).searchParams.get("notice")).toBe(record.notice_id);
  const version = page.getByTestId("notice-version").last();
  await expect(version).toContainText("데모 · Snapshot");
  await expect(version).toHaveAttribute("data-notice-id", record.notice_id);
  const previous = await version.getByTestId("candidate").count();
  await page.getByRole("button", { name: "기본 요건 추출", exact: true }).click();
  await expect.poll(() => version.getByTestId("candidate").count(), { timeout: 25000 }).toBeGreaterThan(previous);
  const candidate = version.getByTestId("candidate").filter({ hasText: "필수 제출서류" }).filter({ has: page.getByRole("button", { name: "선택 요건 확정" }) }).last();
  await expect(candidate).toContainText("PDF 2페이지");
  await expect(candidate.getByRole("button", { name: "선택 요건 확정" })).toBeDisabled();
  await candidate.getByRole("checkbox").check();
  await candidate.getByLabel("검토 의견", { exact: true }).fill("Reviewed actual page 2 of the SANITIZED/DEMO source.");
  const confirmed = page.waitForResponse(response => response.url().endsWith("/confirm") && response.status() === 200);
  await candidate.getByRole("button", { name: "선택 요건 확정" }).click();
  const requirement = await (await confirmed).json();
  await expect(version.getByTestId("confirmed")).toContainText(requirement.id);
  await page.getByRole("button", { name: "공고 수집관리", exact: true }).click();
  const again = page.waitForResponse(response => response.url().endsWith("/api/notice/collections") && response.request().method() === "POST" && response.status() === 200);
  await panel.getByRole("button", { name: "수집 요청", exact: true }).click();
  const repeated = await (await again).json();
  expect(repeated.payload.mode).toBe("SNAPSHOT");
  await expect(panel.locator('[data-job-id="' + repeated.id + '"]')).toContainText("변경 없음", { timeout: 25000 });
  const latest = await (await page.request.get("/api/notice/" + record.notice_id)).json();
  expect(latest.versions).toHaveLength(1);
  expect(latest.versions[0].confirmed.some((v: { id: string }) => v.id === requirement.id)).toBeTruthy();
});
test("unauthenticated browser cannot request or read collection using a spoofed role", async ({ request }) => {
  const headers = { "Origin": "http://localhost:3000", "X-Role": "DATCO_OPERATOR" };
  const result = await request.post("/api/notice/collections", { headers, data: { mode: "SNAPSHOT", idempotency_key: "spoofed-browser-role" } });
  expect(result.status()).toBe(401);
  expect((await result.json()).reason).toBe("AUTHENTICATION_REQUIRED");
  expect((await request.get("/api/notice/collections", { headers })).status()).toBe(401);
});
