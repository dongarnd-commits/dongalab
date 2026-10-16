import Workspace from "./workspace";
import "../notice/operator.css";
import "../capability/workspace.css";
export const metadata={title:"DATCO 맞춤형 제안서"};
export default async function Page({searchParams}:{searchParams:Promise<{candidate?:string;proposal?:string}>}){const p=await searchParams;return <Workspace initialCandidate={p.candidate??""} initialProposal={p.proposal??""}/>;}
