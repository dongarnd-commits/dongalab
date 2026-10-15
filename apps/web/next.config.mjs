const isolatedDir=process.env.DATCO_TEST_DIST_DIR;
if(isolatedDir&&!/^\.next\/datco-e2e-[a-f0-9]{12}$/.test(isolatedDir))throw new Error("Invalid isolated Next.js directory");
const config={ ...(isolatedDir?{distDir:isolatedDir,typescript:{tsconfigPath:isolatedDir.replace("datco-e2e-","datco-config-")+"/tsconfig.json"}}:{}) };
export default config;
