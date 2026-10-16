
import { test, expect, type Page } from "@playwright/test";
import { isolatedAccount } from "./isolated-account";

async function login(page: Page) {
  const account=isolatedAccount();
  await page.goto("/notice");
  await page.getByLabel("아이디", { exact: true }).fill(account.username);
  await page.getByLabel("비밀번호", { exact: true }).fill(account.password);
  await page.getByRole("button", { name: "로그인", exact: true }).click();
  await expect(page.getByRole("heading", { name: "지원사업 공고", exact: true })).toBeVisible();
}
async function catalog(page: Page) {
  const response = await page.request.get("/api/notice");
  expect(response.ok()).toBeTruthy();
  const notices = await response.json();
  return Promise.all(notices.map(async (n: { id: string }) => {
    const detail = await page.request.get("/api/notice/" + n.id);
    expect(detail.ok()).toBeTruthy();
    return detail.json();
  }));
}
async function enterDemo(page: Page) {
  await page.locator(".demo-entry summary").click();
  await page.getByRole("button", { name: "테스트·시연 모드 열기", exact: true }).click();
  await expect(page.locator(".demo-context")).toBeVisible();
}

test("normal catalog shows only stored Live notices and opens official source without collection", async ({ page }) => {
  await login(page);
  const records = await catalog(page);
  const lives = records.filter(d => d.versions.some((v: { ordinal: number; mode: string }) => v.ordinal === d.current_ordinal && v.mode === "LIVE"));
  await expect(page.locator(".notice-table tbody tr")).toHaveCount(lives.length);
  await expect(page.getByLabel("공고 선택", { exact: true })).toHaveCount(0);
  await expect(page.getByLabel("자료 원천", { exact: true })).toHaveCount(0);
  await expect(page.locator(".notice-table thead")).not.toContainText("자료 확보");
  await expect(page.locator(".notice-table tbody")).not.toContainText("DEMO/");
  await expect(page.locator(".notice-table tbody")).not.toContainText("Snapshot");
  if (!lives.length) {
    await expect(page.getByText("현재 저장된 실제 공고가 없습니다.", { exact: false })).toBeVisible();
    return;
  }
  const live = lives[0];
  await expect(page.locator(".notice-table tbody")).toContainText("공식 모집 상태 미확인");
  await page.getByLabel("공고 검색").fill("해당되는 공고가 없는 검색어");
  await expect(page.locator(".notice-table tbody tr")).toHaveCount(0);
  await page.getByLabel("공고 검색").fill("");
  await page.screenshot({ path: "../../storage/private/runtime/notice-ui-final-catalog.png", fullPage: true });
  await page.locator(".title-button").filter({ hasText: live.title }).click();
  const panel = page.getByTestId("notice-version").last();
  await expect(panel).toHaveAttribute("data-notice-id", live.id);
  expect(new URL(page.url()).searchParams.get("notice")).toBe(live.id);
  await expect(panel.getByRole("link", { name: "기업마당 공식 공고 열기 ↗" })).toHaveAttribute("href", /^https:\/\/(www\.)?bizinfo\.go\.kr\//);
  await expect(panel.getByText("규칙 기반 기본 요건 추출", { exact: false })).toBeVisible();
  await expect(panel.getByRole("button", { name: "기본 요건 추출", exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByTestId("notice-version").last()).toHaveAttribute("data-notice-id", live.id);
  await page.screenshot({ path: "../../storage/private/runtime/notice-ui-final-live-detail.png", fullPage: true });
});

test("explicit demo list preserves source review, history, back and refresh on mobile", async ({ page }) => {
  await login(page);
  await enterDemo(page);
  const records = await catalog(page);
  const demo = records.filter(d => d.versions.some((v: { ordinal: number; mode: string }) => v.ordinal === d.current_ordinal && ["DEMO_TEST", "SANITIZED_SNAPSHOT"].includes(v.mode)));
  await expect(page.locator(".notice-table tbody tr")).toHaveCount(demo.length);
  const normal = demo.find(d => d.title === "DEMO/TEST normal notice");
  expect(normal).toBeTruthy();
  await page.getByLabel("공고 검색").fill(normal.title);
  await expect(page.locator(".notice-table tbody tr")).toHaveCount(1);
  await page.getByLabel("공고 검색").fill("");
  await page.locator(".title-button").filter({ hasText: normal.title }).click();
  const panel = page.getByTestId("notice-version").last();
  await expect(panel).toHaveAttribute("data-notice-id", normal.id);
  await expect(panel.getByRole("heading", { name: "1. 원천자료 확인" })).toBeVisible();
  await expect(panel.locator(".analysis-run[open]").getByText("원문 근거", { exact: true }).first()).toBeVisible();
  const visibleText = await page.locator("body").innerText();
  expect(visibleText).not.toMatch(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i);
  expect(visibleText).not.toContain("source_comparisons");
  await page.goBack();
  await expect(page.locator(".notice-table")).toBeVisible();
  await page.goForward();
  await expect(panel).toHaveAttribute("data-notice-id", normal.id);
  await page.reload();
  await expect(panel).toHaveAttribute("data-notice-id", normal.id);
  await expect(page.locator(".demo-context")).toBeVisible();
  await expect(page.getByLabel("공고 선택")).toHaveCount(0);
  const technical = panel.locator("details.technical").first();
  await technical.locator("summary").click();
  await expect(technical.locator("pre")).toBeVisible();
  await technical.locator("summary").click();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await expect(page.getByRole("button", { name: "공고 목록", exact: true })).toBeVisible();
  await page.screenshot({ path: "../../storage/private/runtime/notice-ui-final-mobile.png", fullPage: true });
});

test("operations tools retain actual PARTIAL history and gate Snapshot by explicit test context", async ({ page }) => {
  await login(page);
  await page.getByRole("button", { name: "공고 수집관리", exact: true }).click();
  const panel = page.getByRole("region", { name: "기업마당 수집관리" });
  await expect(panel).toBeVisible();
  await expect(panel.getByLabel("수집 원천")).toHaveCount(0);
  await expect(panel).toContainText("실제 기업마당 API · Live 수집");
  const jobs = await (await page.request.get("/api/notice/collections")).json();
  const partial = jobs.find((j: { state: string; payload: { mode: string } }) => j.state === "PARTIAL" && j.payload.mode === "LIVE");
  if (partial) {
    const entry = panel.locator('[data-job-id="' + partial.id + '"]');
    await expect(entry).toContainText("부분 완료");
    await expect(entry).toContainText("미확보 자료");
  }
  await page.screenshot({ path: "../../storage/private/runtime/notice-ui-final-tools.png", fullPage: true });
  await enterDemo(page);
  await page.getByRole("button", { name: "공고 수집관리", exact: true }).click();
  await expect(panel.getByLabel("수집 원천")).toHaveValue("SNAPSHOT");
  await expect(panel).toContainText("검증된 합성 데모 입력");
  await page.reload();
  await expect(page.locator(".demo-context")).toBeVisible();
  await expect(panel.getByLabel("수집 원천")).toHaveValue("SNAPSHOT");
  await page.getByRole("button", { name: "실제 공고 업무로 돌아가기", exact: true }).click();
  await expect(page.locator(".demo-context")).toHaveCount(0);
  await page.getByRole("button", { name: "공고 수집관리", exact: true }).click();
  await expect(panel.getByLabel("수집 원천")).toHaveCount(0);
});

test("demo deep link needs explicit context and does not masquerade as Live", async ({ page }) => {
  await login(page);
  const records = await catalog(page);
  const demo = records.find(d => d.versions.some((v: { mode: string }) => v.mode === "SANITIZED_SNAPSHOT"));
  expect(demo).toBeTruthy();
  await page.goto("/notice?view=review&notice=" + demo.id);
  await expect(page.getByText("이 공고는 Live 원천으로 확인되지 않았습니다.", { exact: false })).toBeVisible();
  await expect(page.getByTestId("notice-version")).toHaveCount(0);
  await page.getByRole("button", { name: "테스트·시연 모드로 열기" }).click();
  await expect(page.getByTestId("notice-version").last()).toHaveAttribute("data-notice-id", demo.id);
  await expect(page.getByTestId("notice-version").last()).toContainText("데모 · Snapshot");
});

test("a URL or test-context flag cannot bypass backend session permission", async ({ page, request }) => {
  const id = "00000000-0000-0000-0000-000000000000";
  await page.goto("/notice?view=review&notice=" + id + "&context=demo");
  await expect(page.getByRole("button", { name: "로그인", exact: true })).toBeVisible();
  await expect(page.getByTestId("notice-version")).toHaveCount(0);
  expect((await request.get("/api/notice/" + id, { headers: { "X-Role": "DATCO_OPERATOR" } })).status()).toBe(401);
  expect((await request.post("/api/notice/collections", { headers: { Origin: process.env.WEB_ORIGIN!, "X-Role": "DATCO_OPERATOR" }, data: { mode: "SNAPSHOT", idempotency_key: "url-context-is-not-permission" } })).status()).toBe(401);
});
