import { defineConfig, devices } from "@playwright/test";
const baseURL=process.env.DATCO_E2E_BASE_URL;
if(!process.env.DATCO_TEST_NONCE||!baseURL||process.env.DATCO_E2E_SERVER_READY!=="1")throw new Error("ISOLATION_REQUIRED: use apps/api/tests/isolated_run.py");
export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  use: { baseURL },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  // The guarded runner owns a fresh API/Worker/Web; no existing development server reuse.
});
