
import type { ReactNode } from "react";
import type { components } from "@/generated/api";
export type Version = components["schemas"]["VersionResponse"];
export type Source = components["schemas"]["SourceResponse"];
export const kindLabel: Record<string, string> = {
  ELIGIBILITY_REQUIREMENT: "지원 자격", SUPPORT_SCOPE: "지원 내용", APPLICATION_PERIOD: "접수 기간",
  REQUIRED_DOCUMENT: "필수 제출서류", EVALUATION_CRITERION: "평가 기준", FORM_FIELD: "신청서 항목",
  PLAN_SECTION: "사업계획서 항목", CONDITIONAL_REQUIREMENT: "조건부 요건",
};
const labels: Record<string, string> = {
  QUEUED: "대기 중", PROCESSING: "처리 중", SUCCEEDED: "처리 완료", PARTIAL: "부분 완료", FAILED: "실패",
  ACQUIRED: "확보", NOT_PROVIDED: "제공되지 않음", RETAINED_UNOBSERVED: "이전 자료 참조",
  NEW: "신규", UNCHANGED: "변경 없음", NEW_VERSION: "변경", DUPLICATE: "중복 제외", CONFLICT: "내용 충돌",
};
export function stateLabel(value: string) { return labels[value] ?? "확인 필요"; }
export function isDemoMode(value: string) { return ["SNAPSHOT", "SANITIZED_SNAPSHOT", "DEMO_TEST"].includes(value); }
export function modeLabel(value: string) { return value === "LIVE" ? "실제 공고 · Live" : value === "SNAPSHOT" || value === "SANITIZED_SNAPSHOT" ? "데모 · Snapshot" : value === "DEMO_TEST" ? "데모 · 테스트" : "원천 미확인"; }
export function officialUrl(version: Version): string | undefined {
  if (version.mode !== "LIVE") return;
  try {
    const url = new URL(text(version.metadata.detail_url, ""));
    if (url.protocol !== "https:" || !["www.bizinfo.go.kr", "bizinfo.go.kr"].includes(url.hostname) || (url.port && url.port !== "443") || url.username || url.password || url.hash) return;
    if (url.searchParams.getAll("pblancId").length !== 1 || url.searchParams.get("pblancId") !== version.metadata.external_id) return;
    if (Array.from(url.searchParams.keys()).some(key => /key|token|password|secret/i.test(key))) return;
    return url.toString();
  } catch { return; }
}
export function text(value: unknown, fallback = "정보 없음"): string { return typeof value === "string" && value.trim() ? value : fallback; }
export function record(value: unknown): Record<string, unknown> { return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {}; }
export function provenance(source: Source) { try { return record(JSON.parse(source.provenance)); } catch { return {}; } }
export function dateLabel(value: unknown) {
  if (typeof value !== "string") return "시각 정보 없음";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "시각 확인 필요" : new Intl.DateTimeFormat("ko-KR", { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }).format(date);
}
export function sourceLabel(source: Source) {
  return ({ pblancUrl: "공고 상세 원문", flpthNm: "공고 첨부자료", printFlpthNm: "본문 출력 참조" } as Record<string, string>)[source.name] ?? (source.media_type === "text/html" ? "공고 HTML 원문" : source.media_type === "application/pdf" ? "PDF 자료" : "참조자료");
}
export function sourceState(source: Source, version: Version) {
  const p = provenance(source);
  if (p.retained_previous_file || (p.status === "RETAINED_UNOBSERVED" && p.content_hash)) return "이전 파일 보존";
  if (p.status === "FAILED") return "미확보";
  if (p.status === "ACQUIRED") return "확보";
  const run = version.runs.at(-1);
  const missing = run?.missing.find(m => record(m).source_id === source.id);
  if (missing) return record(missing).reason === "PARTIAL_PAGE_EXTRACTION" ? "일부 페이지 추출 제한" : "일부 미확보 / 추출 제한";
  if (run?.candidates.some(c => c.evidence.source_id === source.id)) return "분석 근거 확인";
  return "확보 상태 미확인";
}
export function acquisitionLabel(version?: Version) {
  if (!version) return "조회 필요";
  if (!version.sources.length) return "자료 미확보";
  const states = version.sources.map(source => sourceState(source, version));
  if (states.some(s => s.includes("미확보") || s.includes("이전 파일") || s.includes("추출 제한"))) return "자료 보완 필요";
  if (states.some(s => s.includes("미확인"))) return "확보 상태 확인 필요";
  return "자료 확보";
}
export function reviewLabel(version?: Version) {
  if (!version) return "조회 필요";
  const run = version.runs.at(-1);
  if (!run) return "미분석";
  if (run.candidates.some(c => !c.reviews.length)) return "검토 필요";
  if (run.candidates.some(c => c.reviews.some(r => record(r).outcome === "REQUEST_MORE_INFORMATION"))) return "자료 보완 요청";
  return version.confirmed.length ? "선택 요건 확정" : "검토 결과 확인";
}
const errors: Record<string, string> = {
  AUTHENTICATION_REQUIRED: "로그인이 필요합니다.", LOGIN_DENIED: "아이디 또는 비밀번호를 확인해 주세요.",
  ACTION_NOT_AUTHORIZED: "이 작업을 수행할 권한이 없습니다.", UNTRUSTED_ORIGIN: "허용된 로컬 주소에서 다시 접속해 주세요.",
  STALE_INPUT_VERSION: "공고가 변경되었습니다. 최신 버전을 선택해 다시 검토해 주세요.",
  REQUIRED_EVIDENCE_MISSING: "원천 근거를 확인할 수 없습니다. 자료를 보완한 뒤 검토해 주세요.",
  REQUIRED_DATA_MISSING: "필수 입력 또는 자료를 확인해 주세요.", OFFICIAL_SOURCE_NOT_VERIFIED: "원문 확인 항목에 체크해 주세요.",
  MISSING_REQUIRED_INFORMATION: "상충하는 근거에 대한 검토 의견이 필요합니다.",
  TRANSITION_NOT_ALLOWED: "현재 상태에서는 실행할 수 없습니다. 저장된 결과를 확인해 주세요.",
  STORAGE_UNAVAILABLE: "저장소에 연결할 수 없습니다. 잠시 후 다시 조회해 주세요.",
  SOURCE_NOT_ACQUIRED: "자료를 확보하지 못했습니다.", SOURCE_FORMAT_UNSUPPORTED: "현재 지원하지 않는 파일 형식입니다.",
  SOURCE_NOT_VALID_PDF: "유효한 PDF로 확인되지 않았습니다.", SOURCE_NEEDS_MANUAL_REVIEW: "자료를 직접 확인해야 합니다.",
  SOURCE_MISSING_OR_UNREADABLE: "자료가 미확보되었거나 읽을 수 없습니다.", PARTIAL_PAGE_EXTRACTION: "일부 페이지를 추출하지 못했습니다.",
  PAGE_LIMIT_REACHED: "요청한 페이지 상한에 도달했습니다. 전체 수집을 완료한 결과가 아닙니다.",
  BIZINFO_NETWORK_TIMEOUT: "기업마당 연결이 지연되거나 실패했습니다.", BIZINFO_KEY_NOT_CONFIGURED: "운영 환경의 기업마당 인증 설정을 확인해 주세요.",
  DETAIL_CHANGE_REQUIRES_REVIEW: "상세 원문 변경을 직접 검토해야 합니다.",
  NO_VALID_REQUIREMENT_CANDIDATE: "지원하는 형식의 요건 후보를 추출하지 못했습니다. 원문을 직접 확인해 주세요.",
  TOTAL_COUNT_CHANGED: "수집 중 원천의 전체 건수가 달라졌습니다.", UNIQUE_COUNT_MISMATCH: "원천 건수와 확인한 공고 수가 일치하지 않습니다.",
  SHORT_PAGE_OBSERVED: "요청 건수보다 적은 페이지를 확인했습니다.", REPEATED_PAGE_NO_PROGRESS: "같은 페이지가 반복되어 수집을 중단했습니다.",
};
export function errorLabel(value: unknown) { return typeof value === "string" && errors[value] ? errors[value] : "처리를 완료하지 못했거나 추가 확인이 필요합니다. 기술 상세정보에서 원인을 확인하세요."; }
export function Badge({ children, tone = "" }: { children: ReactNode; tone?: string }) { return <span className={"badge " + tone}>{children}</span>; }
export function Technical({ value }: { value: unknown }) { return <details className="technical"><summary>기술 상세정보</summary><pre>{JSON.stringify(value, null, 2)}</pre></details>; }
