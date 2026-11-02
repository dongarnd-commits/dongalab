/** Business-facing messages; server reason codes remain available on demand. */
const reasons:Record<string,string>={
 AVAILABILITY_EVIDENCE_REQUIRED:'제공 확인을 완료하려면 실제 확인 근거가 필요합니다.',
 RELATION_EVIDENCE_REQUIRED:'연계를 확인했다면 확인 근거를 남겨 주세요.',
 ASSET_ALREADY_MANAGED:'이미 관리 등록된 기능입니다. 상세에서 새 버전을 작성하세요.',
 ASSET_NOT_AVAILABLE:'제공 불가 또는 사용 중단된 기능은 구성에서 제외해 주세요.',
 ASSET_AVAILABILITY_UNVERIFIED:'제공이 확인되지 않은 기능은 해결 완료로 표시할 수 없습니다.',
 UNVERIFIED_ASSET_INTEGRATION:'등록된 연계 근거와 일치하지 않습니다. 근거를 확인하거나 미검증 초안으로 남겨 주세요.',
 ASSET_INTEGRATION_REVIEW_REQUIRED:'현재 선택한 구성에 필요한 연계가 빠졌습니다. 등록된 관계와 연결 범위를 다시 확인해 주세요.',
 ASSET_INTEGRATION_UNVERIFIED:'현재 선택한 구성의 연계가 미검증입니다. 확인 근거가 있어야 고객에게 제안할 수 있습니다.',
 ASSET_DEPENDENCY_MISSING:'선택한 기능에 필요한 선행 항목이 빠졌습니다. 구성을 보완해 주세요.',
 ASSET_DEPENDENCY_UNVERIFIED:'선택한 기능의 선행 조건이 아직 확인되지 않았습니다.',
 ASSET_SCOPE_REVIEW_REQUIRED:'요구별 해결 범위와 남은 확인사항을 검토해야 합니다.',
 ASSET_CATALOG_CHANGED:'기술자산 목록이나 제공 정보가 변경되었습니다. 새 추천을 생성해 주세요.',
 COMPANY_INPUT_CHANGED:'기업정보 또는 개선요구가 변경되었습니다. 현재 내용을 다시 확인해 주세요.',
 ANALYSIS_OR_REVIEW_CHANGED:'분석 결과나 검토 의견이 변경되었습니다. 최신 내용으로 다시 검토해 주세요.',
 SOLUTION_RULE_CHANGED:'추천 기준이 변경되었습니다. 새 추천을 생성해 주세요.',
 ANALYSIS_REVIEW_REQUIRED:'제출본의 분석 내용과 활용할 근거를 먼저 검토해 주세요.',
 MISSING_REQUIRED_INFORMATION:'필수 정보나 확인 근거가 부족합니다. 미해결 요구는 확인사항과 함께 남겨 주세요.',
 ASSET_PARENT_KIND_MISMATCH:'관리 등록된 올바른 상위 시스템·모듈을 선택해 주세요.',
 ACTION_NOT_AUTHORIZED:'이 업무를 실행할 권한이 없습니다.',
 OBJECT_NOT_FOUND:'선택 항목이 없거나 접근할 수 없습니다.',
 STALE_INPUT_VERSION:'입력 내용이 변경되었습니다. 현재 저장본을 다시 조회해 주세요.',
 INVALID_MEMBERSHIP_TARGET:'기업 접근권한을 부여할 수 없는 계정입니다.',
 INVALID_COVERAGE_STATUS:'해결 상태와 해결·미해결 범위가 일치하지 않습니다. 항목별 저장 조건을 확인해 주세요.',
 TARGET_VERSION_MISMATCH:'선택한 근거와 저장본이 일치하지 않습니다. 현재 내용을 다시 선택해 주세요.',
 REQUIRED_DATA_MISSING:'필수 입력을 확인해 주세요.',
 REQUIRED_EVIDENCE_MISSING:'필요한 확인 근거가 없습니다. 원문과 연결 자료를 확인해 주세요.',
 UNSUPPORTED_ASSET_DEMAND:'이 요구와 연결된 기능 근거가 없습니다. 다른 기능을 검토하거나 미해결로 남겨 주세요.',
 MATCH_NOT_PROPOSABLE:'항목별 근거 검토와 제안 가능 판단이 필요합니다.',
 LEGACY_ANALYSIS_REQUIRES_REANALYSIS:'현재 입력으로 다시 분석하고 근거를 검토해야 합니다.',
 STORAGE_UNAVAILABLE:'저장소에 연결하지 못했습니다. 저장 여부를 다시 조회한 후 재시도해 주세요.',
 ANALYSIS_PROVIDER_NOT_CONFIGURED:'선택한 분석 도구가 연결되지 않아 실행할 수 없습니다.',
};
export const portalReasonText=(code:string,fallback='요청을 처리하지 못했습니다. 저장 여부를 다시 확인하고 오류 정보를 담당자에게 알려 주세요.')=>reasons[code]??fallback;
export class PortalRequestError extends Error{
 constructor(readonly code:string){super(portalReasonText(code));this.name='PortalRequestError';}
}
export function PortalErrorMessage({error}:{error:string|Error}){
 return <div role="alert"><p>{error instanceof Error?error.message:error}</p>{error instanceof PortalRequestError&&<details><summary>담당자 확인용 오류 정보</summary><code>{error.code}</code></details>}</div>;
}
export function PortalReasonCodes({codes}:{codes:string[]}){
 return <details><summary>변경·차단 사유의 상세 기록</summary><ul>{codes.map((code,index)=><li key={index}><code>{code}</code></li>)}</ul></details>;
}
