import ModuleLinks from "../_workspace/module-links";
import Workspace from "./workspace";
import "../notice/operator.css";
import "./workspace.css";
export const metadata = { title: "DATCO 역량·서비스 조합" };
export default async function Page({searchParams}:{searchParams:Promise<{view?:string;composition?:string;improvement?:string;candidate?:string}>}) { const p=await searchParams; return <><ModuleLinks module="capability"/><Workspace initialView={p.view} initialComposition={p.composition} initialImprovement={p.improvement} initialCandidate={p.candidate}/></>; }
