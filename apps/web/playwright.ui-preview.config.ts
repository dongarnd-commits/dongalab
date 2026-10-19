import {defineConfig,devices} from "@playwright/test";
const baseURL=process.env.DATCO_UI_PREVIEW_ORIGIN;
if(!baseURL||!/^http:\/\/(127\.0\.0\.1|localhost):[0-9]+$/.test(baseURL))throw Error("Owned UI preview runner required");
export default defineConfig({testDir:"./tests",testMatch:"company-visual-preview.spec.ts",workers:1,use:{baseURL},projects:[{name:"chromium",use:{...devices["Desktop Chrome"],viewport:{width:1440,height:936}}}]});
