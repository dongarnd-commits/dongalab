import { test, expect } from "@playwright/test";
test("real API and PostgreSQL readiness is visible", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "DATCO 업무 공간" })).toBeVisible();
  await expect(page.getByTestId("web-status")).toHaveText("READY");
  await expect(page.getByTestId("api-status")).toHaveText("READY");
  await expect(page.getByTestId("database-status")).toHaveText("READY");
  await page.reload();
  await expect(page.getByTestId("database-status")).toHaveText("READY");
});
