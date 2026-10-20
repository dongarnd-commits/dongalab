import {createRoot} from "react-dom/client";
import AdminPortal,{type AdminPreviewData} from "../src/ui-preview/admin/AdminPortal";
import fixture from "../src/ui-preview/admin/adminFixture.json";
const data=structuredClone(fixture) as AdminPreviewData;
const count=new URLSearchParams(location.search).get("count");
if(count==="0"||count==="1")for(const key of ["features","capabilities","notices","users","companies","aiRuns","qualityIssues","integrations","audit"] as const)data[key]=data[key].slice(0,Number(count)) as never;
createRoot(document.getElementById("root")!).render(<AdminPortal testData={data}/>);
