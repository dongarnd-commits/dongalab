import { useState } from "react";

type Preparation = {can_create:false; policy_blockers:string[]; implementation_blockers:string[]; source_refs:Record<string,unknown>};
const labels:Record<string,string> = {
 MATCH_NOT_PROPOSABLE:"현재 담당자 검토가 제안 가능으로 확정되지 않았습니다.",
 MISSING_REQUIRED_INFORMATION:"기업·공급자격 및 서비스 범위의 필수정보 확인이 필요합니다.",
 STALE_INPUT_VERSION:"입력이 변경되었습니다. 재분석과 재검토가 필요합니다.",
 LEGACY_ANALYSIS_REQUIRES_REANALYSIS:"이전 미연결 분석은 재분석이 필요합니다.",
 PROPOSAL_PERSISTENCE_CONTRACT_PENDING:"제안서 저장·버전 물리계약 승인 대기",
 PROPOSAL_OUTPUT_FORMAT_PENDING:"제안서 파일 출력 형식 결정 대기",
};
export default function ProposalPreparation({load}:{load:()=>Promise<Preparation>}) {
 const [result,setResult]=useState<Preparation|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
 return <section aria-label="제안서 생성조건"><h3>제안서 작업</h3>
 <p>초안도 제안 가능 검토와 최신 입력·필수정보 확인이 필요합니다.</p>
 <button disabled={busy} onClick={async()=>{setBusy(true);setError("");setResult(null);try{setResult(await load());}catch(e){setError(e instanceof Error?e.message:"조회 실패");}finally{setBusy(false);}}}>제안서 생성조건 확인</button>
 {error&&<p role="alert">{error}</p>}{result&&<><p>제안서 생성이 차단되었습니다. 초안·저장본·출력 파일은 생성되지 않았습니다.</p>
 <ul>{[...result.policy_blockers,...result.implementation_blockers].map(reason=><li key={reason}>{labels[reason]??reason}</li>)}</ul>
 <details><summary>제안서 입력으로 검토할 원천 버전</summary><dl>{Object.entries(result.source_refs).map(([name,value])=><div key={name}><dt>{name}</dt><dd>{Array.isArray(value)?value.join(", "):String(value)}</dd></div>)}</dl></details></>}
 </section>;
}
