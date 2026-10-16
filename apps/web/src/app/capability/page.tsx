import Workspace from "./workspace";
import "../notice/operator.css";
import "./workspace.css";
export const metadata = { title: "DATCO 역량·서비스 조합" };
export default async function Page({searchParams}:{searchParams:Promise<{view?:string;composition?:string}>}) { const p=await searchParams; return <Workspace initialView={p.view} initialComposition={p.composition}/>; }
