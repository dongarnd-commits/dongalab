# MVP v1 구현 계약과 변경 영향

2026-10-30. 본 문서는 구현된 계약의 설명이다. 최종 실행 결과는 ACCEPTANCE와 PROGRESS에 별도 기록한다. 사용자 인수·대표 승인·main Merge·HTTPS 배포를 선언하지 않는다.

## 공통 분석 경계

AnalysisRequest(provider 기본 RULE, mode MANUAL/ENSURE) → 개선요구 전용 ImprovementAnalysisProvider → StructuredAnalysisResult(improvement-result-v1) → 기존 Candidate/Evidence 검증 → 기존 append-only Review.
기존 company.analysis.AnalysisProvider는 단일 기업문서 추출의 별도 경계로 보존한다. 실행 엔진을 혼합하지 않는다.

GET /company/analysis/providers는 인증된 Operator만 조회한다. RULE AVAILABLE, GPT/GEMINI/CLAUDE/GROK은 모두 NOT_CONFIGURED다. 외부 어댑터·인증 시도·AI 네트워크 코드가 없다. 알려진 외부 provider POST는 409 ANALYSIS_PROVIDER_NOT_CONFIGURED로 Job 생성 전에 거부, 알 수 없는 이름은 422다. Worker도 다시 검사한다.
자동 진입은 ENSURE+RULE만 사용한다. 기존 오류 주입/원자성 회귀의 Worker analyze 지점은 RuleProvider 내부의 명시 로컬 함수 의존성으로 유지하며 외부 provider 실행 경로로 사용하지 않는다.

공통 결과에는 provider/version, 정확 company/ImprovementVersion/input_digest, current_state/problems/cause_candidates/goals/required_functions/scope_constraints/missing_information/domains, 근거 Candidate, diagnostics, limitations, 사람 검토 전 상태가 있다. 기존 Run/Evidence/Review를 재사용한다.

## 입력·자료·검토답변

- 정확 SUBMIT Version, 현재 CompanyInputVersion, 제출 당시 SiteVersion, 확정 FactVersion/Review/Evidence, 직접 첨부와 선택 공통자료, 제외 이유, File digest/Parse/Parser/검사위치를 기존 Manifest에 고정한다.
- VERIFIED로 사람 검토한 동일기업 답변만 reviewed_answers에 request/response/review ID, ordinal, message_digest로 고정한다. 정확 제출 Version용과 기업 공통 Request를 구분한다. Draft·미검토·타기업·다른 개선요구 답변은 제외한다.
- 실제 Worker가 검토답변 원문을 RESPONSE 근거로 연결한다. 원문을 Confirmed Fact로 자동 승격하지 않는다. 새 검증답변은 VERIFIED_ANSWER_CHANGED로 이전 Run 현재성을 제한한다.
- 읽지 못한 자료, 일부 검사, 미지원, 미선택, 의도적 제외, 직접 첨부를 기존 Rule별 검사범위와 함께 보존한다. 미검사=정보없음으로 판정하지 않는다.

## 제출 v1과 구조화 v2

실제 상태는 제출v1 분석 → Candidate USE_FOR_REQUEST Review → Operator 구조화v2 저장 → 회사 ACKNOWLEDGE v2 → Operator CONFIRM v2다.
구조화 시 선택한 optional analysis_basis={run_id, review_ids, source_version_id:v1}를 Backend가 정확 Root/Company/Site/원본 SUBMIT/최신 Run·Review·현재성으로 검증한다. Operator만 이 출처를 지정할 수 있다. 회사가 새 Draft를 만들 때는 기존 분석 metadata를 복제해 새 승인으로 오인하지 않는다.
추천·구성·제안서에는 분석입력 v1과 공식 구조화/확정 v2를 별도로 보존한다. 과거 결과는 조회 가능하지만 stale 근거로 새 업무를 진행할 수 없다. 회사 의사결정 시 내부 검증은 실제 역할/Scope로 수행하며 Operator로 위장하지 않는다.
USE_FOR_REQUEST는 검토 활용 기록이다. Fact 확정·개선요구 CONFIRM·제안 가능 판단·회사 제안 승인과 각각 별도다.

## DB/Migration 영향

| 대상 | 증분 | 보존 |
|---|---|---|
| company_improvement_versions.data | optional analysis_basis | 기존 JSON/Version/State 덮어쓰기 없음 |
| improvement_analysis_manifests.data | provider, reviewed_answers | 기존 Run/Manifest 읽기 호환 |
| analysis_improvement_contexts.diagnostics | structured_result | 후보0건·기존 count/상태 제약 |
| Candidate Detail Evidence | RESPONSE 한정 검증 | 기존 인용/Source 위치/Scope 검증 |
| validate_improvement_lineage() | frozen migration fg31m0012026 함수 body 증분 | function language/security/search_path/proconfig 유지 |
| ck_mvp_structure_basis | Version INSERT/UPDATE deferred 검증 Trigger 추가 | 기존 요청·답변·승인 불변 Trigger 변경 없음 |
| Capability/Composition/Matching | 기존 JSON에 optional basis/integrations/coverage 설명 | 공통 테이블/Typed FK/계보 유지 |
| Proposal | 불변 manifest.template_version LEGACY_11/MVP_16 | 기존 11절/파일/승인/재승인 보존 |

새 Migration은 기존 행을 UPDATE/DELETE하지 않는다. 안전한 빈 새 계보에서는 downgrade/up 허용, 새 계보 이력이 존재하면 downgrade가 DDL 전에 거부된다. 공유 DB Migration은 미실행이며 실제 배포에는 별도 백업/원복 검토·승인이 필요하다.

## 업무 API와 화면

- GET /capability/improvements/{vid}/recommendations: 공식 확정 Company 맥락, 분석 basis, 요구와 근거, 발행 Capability/실제 FeatureRevision 후보, 미해결 요구, 제한. 후보는 제공/적합 자동확정이 아니다.
- 기존 Composition API: 선택한 실제 서비스, 역할/해결·부분·미해결 Coverage, 원천 Revision, 데이터/업무 연계 및 선행조건. 없는 AI Agent 서비스를 만들지 않는다.
- GET /notice/catalog: 저장된 최신 NoticeVersion 검색/기관/모드/페이지 Projection. LIVE와 합성 Snapshot, 관련성 탐색과 신청자격을 구분한다. 기존 Collector와 요건 검토·Matching·항목별 PROPOSABLE Gate 재사용.
- 기존 Proposal API: template_version=MVP_16을 명시 선택. 같은 검토 ProposalVersion DOCX/PDF 생성, 정확 Version 재검토/전달/기업 의사결정. 기존 LEGACY_11 기본 및 모든 Guard 유지.
- GET /admin/overview|access|connections: SQL whitelist Projection, 비밀번호/hash/세션/token 제외. 기존 ADMIN의 회사 접근권한 grant 재사용. 새 계정/Role 변경·삭제 정책 없음.

기존 3포털 Shell·메뉴·카드·Dialog를 사용한다. 기업·개선요구 Version을 URL로 고정하고 F5/재로그인 때 Backend 권한·현재성을 재검증한다. 새 업무 편집은 기존 미저장 경고에 연결한다. 제안 전달은 Native dialog 취소/Escape/포커스/배경 차단·최종 확인 전0건·중복 클릭1건을 검증한다. 화면 조회가 자동 발행·승인·발송을 실행하지 않는다.

## 테스트·관찰 한계

기존 전체 Unit/PG/Playwright와 신규 MVP 테스트를 유지한다. 합성 기업/공식 공개 공고/승인된 649 원천을 구분한다. 실제 고객자료는 Fixture로 사용하지 않는다.
2026-10-30 공식 기업마당 GET 1회, pageIndex1/pageUnit2, 2건·totCnt1460 관찰 성공. 이는 전체수집·모든 원문 첨부·자격·가동 보장이 아니다. 키는 기존 private 설정에서 메모리로만 읽고 미출력/미복사했다. 격리 개발 private proof: mvp-live/9195b24587134e4aa4c684ad12d49d65/result.json.
