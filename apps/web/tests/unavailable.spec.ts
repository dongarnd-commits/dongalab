import { test, expect } from "@playwright/test";
test("unavailable API is shown honestly", async ({ page }) => {
  test.skip(process.env.SKELETON_TEST_UNAVAILABLE !== "1", "Run after stopping the local API.");
  await page.goto("/");
  await expect(page.getByTestId("web-status")).toHaveText("READY");
  await expect(page.getByTestId("api-status")).toHaveText("NOT READY");
  await expect(page.getByTestId("database-status")).toHaveText("NOT READY");
  await expect(page.getByRole("status")).toBeVisible();
});
