import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

function localAccount() {
  // Read only this test runner's private local account values; never log them.
  const content = readFileSync("../../.env", "utf8");
  const value = (key: string) => content.split(/\r?\n/).find(line => line.startsWith(key + "="))?.slice(key.length + 1) ?? "";
  return { username: value("DEMO_OPERATOR_USER"), password: value("DEMO_OPERATOR_PASSWORD") };
}

test("operator reviews actual Worker candidate, evidence and persistent confirmation", async ({ page }) => {
  const account = localAccount();
  expect(account.password.length).toBeGreaterThan(0);
  await page.goto("/notice");
  await page.getByLabel("아이디", { exact: true }).fill(account.username);
  await page.getByLabel("비밀번호", { exact: true }).fill(account.password);
  await page.getByRole("button", { name: "로그인", exact: true }).click();
  await expect(page.getByText("DATCO 운영자")).toBeVisible();
  if (!new URL(page.url()).searchParams.has("context")) {
    await page.locator(".demo-entry summary").click();
    await page.getByRole("button", { name: "테스트·시연 모드 열기", exact: true }).click();
  }
  await page.getByRole("button", { name: "공고 목록", exact: true }).click();
  await page.locator(".title-button").filter({ hasText: "DEMO/TEST normal notice" }).click();
  const panel = page.getByTestId("notice-version").last();
  await expect(panel).toBeVisible();
  const oldCount = await panel.getByTestId("candidate").count();
  await page.getByRole("button", { name: "기본 요건 추출", exact: true }).click();
  await expect.poll(() => panel.getByTestId("candidate").count(), { timeout: 20000 }).toBeGreaterThan(oldCount);
  const card = panel.getByTestId("candidate").filter({ hasText: "필수 제출서류" }).filter({ has: page.getByRole("button", { name: "선택 요건 확정" }) }).last();
  await expect(card).toContainText("PDF 2페이지");
  await expect(card.getByRole("button", { name: "선택 요건 확정" })).toBeDisabled();
  const download = page.waitForEvent("download");
  await card.getByRole("link", { name: "원천자료 다운로드 ↗" }).click();
  expect((await download).suggestedFilename()).toBe("notice-source");
  await card.getByRole("checkbox").check();
  await card.getByLabel("검토 의견", { exact: true }).fill("Reviewed page 2 of the DEMO/TEST notice.");
  const confirmation = page.waitForResponse(response => response.url().endsWith("/confirm") && response.status() === 200);
  await card.getByRole("button", { name: "선택 요건 확정" }).click();
  const result = await (await confirmation).json();
  await expect(panel.getByTestId("confirmed")).toContainText(result.id);
  await expect(panel.getByTestId("confirmed")).toContainText("Business registration certificate");
  const before = await panel.getByTestId("confirmed").innerText();
  await page.reload();
  await expect(page.getByText("DATCO 운영자")).toBeVisible();
  if (!new URL(page.url()).searchParams.has("context")) {
    await page.locator(".demo-entry summary").click();
    await page.getByRole("button", { name: "테스트·시연 모드 열기", exact: true }).click();
  }
  await page.getByRole("button", { name: "공고 목록", exact: true }).click();
  await page.locator(".title-button").filter({ hasText: "DEMO/TEST normal notice" }).click();
  await expect(panel.getByTestId("confirmed")).toHaveText(before, { useInnerText: true });
});

test("browser cannot manufacture Operator permission or access private source", async ({ request }) => {
  const response = await request.get("/api/notice", { headers: { "X-Role": "DATCO_OPERATOR" } });
  expect(response.status()).toBe(401);
  const file = await request.get("/api/notice/sources/00000000-0000-0000-0000-000000000000/download");
  expect(file.status()).toBe(401);
});


test("notice selection ignores delayed A after B and hides old actions immediately", async ({ page }) => {
  const account = localAccount();
  await page.goto("/notice");
  await page.getByLabel("아이디", { exact: true }).fill(account.username);
  await page.getByLabel("비밀번호", { exact: true }).fill(account.password);
  await page.getByRole("button", { name: "로그인", exact: true }).click();
  await expect(page.getByText("DATCO 운영자")).toBeVisible();
  if (!new URL(page.url()).searchParams.has("context")) {
    await page.locator(".demo-entry summary").click();
    await page.getByRole("button", { name: "테스트·시연 모드 열기", exact: true }).click();
  }
  const list = await (await page.request.get("/api/notice")).json();
  const a = list.find((n: { title: string }) => n.title === "DEMO/TEST normal notice");
  const b = list.find((n: { title: string }) => n.title === "DEMO/TEST partial notice");
  expect(a).toBeTruthy(); expect(b).toBeTruthy();
  // Display A first, then deliberately hold its next refresh response.
  await page.locator(".title-button").filter({ hasText: a.title }).click();
  await expect(page.getByTestId("notice-version").last()).toBeVisible();
  let release!: () => void;
  let started!: () => void;
  let finished!: () => void;
  const delayed = new Promise<void>(resolve => { release = resolve; });
  const requested = new Promise<void>(resolve => { started = resolve; });
  const delivered = new Promise<void>(resolve => { finished = resolve; });
  let releaseB!: () => void;
  const pendingB = new Promise<void>(resolve => { releaseB = resolve; });
  let heldA = false;
  let heldB = false;
  // One persistent handler avoids changing route registration while A is in flight.
  await page.route("**/api/notice/*", async route => {
    const url = route.request().url();
    if (url.endsWith("/" + a.id) && !heldA) {
      heldA = true;
      const response = await route.fetch();
      started();
      await delayed;
      await route.fulfill({ response });
      finished();
    } else if (url.endsWith("/" + b.id) && !heldB) {
      heldB = true;
      const response = await route.fetch();
      await pendingB;
      await route.fulfill({ response });
    } else {
      await route.continue();
    }
  });
  await requested;
  await page.getByRole("button", { name: "공고 목록", exact: true }).click();
  await page.locator(".title-button").filter({ hasText: b.title }).click();
  await expect(page.getByTestId("notice-version")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "선택 요건 확정" })).toHaveCount(0);
  releaseB();
  await expect(page.getByTestId("notice-version").last()).toHaveAttribute("data-notice-id", b.id);
  release();
  await delivered;
  await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
  // A has been delivered; check again after a subsequent B polling response as well.
  expect(new URL(page.url()).searchParams.get("notice")).toBe(b.id);
  await expect(page.getByTestId("notice-version").last()).toHaveAttribute("data-notice-id", b.id);
  await expect(page.getByTestId("notice-version").last()).not.toHaveAttribute("data-notice-id", a.id);
});
