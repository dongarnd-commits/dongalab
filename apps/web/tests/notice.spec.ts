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
  await page.getByLabel("Username", { exact: true }).fill(account.username);
  await page.getByLabel("Password", { exact: true }).fill(account.password);
  await page.getByRole("button", { name: "Login", exact: true }).click();
  await expect(page.getByText("Signed in: DATCO_OPERATOR")).toBeVisible();
  await page.getByLabel("Notice", { exact: true }).selectOption({ label: "DEMO/TEST normal notice" });
  const panel = page.getByTestId("notice-version").last();
  await expect(panel).toBeVisible();
  const oldCount = await panel.getByTestId("candidate").count();
  await page.getByRole("button", { name: "Request analysis", exact: true }).click();
  await expect.poll(() => panel.getByTestId("candidate").count(), { timeout: 20000 }).toBeGreaterThan(oldCount);
  const card = panel.getByTestId("candidate").filter({ hasText: "REQUIRED_DOCUMENT" }).filter({ has: page.getByRole("button", { name: "Confirm selected requirement" }) }).last();
  await expect(card).toContainText("PDF page 2");
  await expect(card.getByRole("button", { name: "Confirm selected requirement" })).toBeDisabled();
  const download = page.waitForEvent("download");
  await card.getByRole("link", { name: "Download source" }).click();
  expect((await download).suggestedFilename()).toBe("notice-source");
  await card.getByRole("checkbox").check();
  await card.getByLabel("Review note", { exact: true }).fill("Reviewed page 2 of the DEMO/TEST notice.");
  const confirmation = page.waitForResponse(response => response.url().endsWith("/confirm") && response.status() === 200);
  await card.getByRole("button", { name: "Confirm selected requirement" }).click();
  const result = await (await confirmation).json();
  await expect(panel.getByTestId("confirmed")).toContainText(result.id);
  await expect(panel.getByTestId("confirmed")).toContainText("Business registration certificate");
  const before = await panel.getByTestId("confirmed").innerText();
  await page.reload();
  await expect(page.getByText("Signed in: DATCO_OPERATOR")).toBeVisible();
  await page.getByLabel("Notice", { exact: true }).selectOption({ label: "DEMO/TEST normal notice" });
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
  await page.getByLabel("Username", { exact: true }).fill(account.username);
  await page.getByLabel("Password", { exact: true }).fill(account.password);
  await page.getByRole("button", { name: "Login", exact: true }).click();
  await expect(page.getByText("Signed in: DATCO_OPERATOR")).toBeVisible();
  const list = await (await page.request.get("/api/notice")).json();
  const a = list.find((n: { title: string }) => n.title === "DEMO/TEST normal notice");
  const b = list.find((n: { title: string }) => n.title === "DEMO/TEST partial notice");
  expect(a).toBeTruthy(); expect(b).toBeTruthy();
  // Display A first, then deliberately hold its next refresh response.
  await page.getByLabel("Notice", { exact: true }).selectOption(a.id);
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
  await page.getByLabel("Notice", { exact: true }).selectOption(b.id);
  await expect(page.getByTestId("notice-version")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Confirm selected requirement" })).toHaveCount(0);
  releaseB();
  await expect(page.getByTestId("notice-version").last()).toHaveAttribute("data-notice-id", b.id);
  release();
  await delivered;
  await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
  // A has been delivered; check again after a subsequent B polling response as well.
  await expect(page.getByLabel("Notice", { exact: true })).toHaveValue(b.id);
  await expect(page.getByTestId("notice-version").last()).toHaveAttribute("data-notice-id", b.id);
  await expect(page.getByTestId("notice-version").last()).not.toHaveAttribute("data-notice-id", a.id);
});
