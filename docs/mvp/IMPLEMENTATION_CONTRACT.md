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


## 1차 사용자 E2E 보완 계약 (2026-11-02)

- Rule은 improvement-rules-v4다. 같은 제출 Version의 as_is/problem, goal/to_be 별칭은 역할별로 묶되 원문 Evidence를 모두 유지한다. 다른 파일·검토답변·Version의 출처는 합치지 않는다.
- STRUCTURE의 content는 실제 인용문 발췌다. 필요한 기능의 이름은 detail.function_label, 도출은 claim_kind=INFERRED 및 derivation(method/id/matched_quotes)에 두고 Backend가 대응표와 실제 원문을 검증한다. 기존 literal CHECK/Trigger는 그대로다.
- 목표 수치와 현재 측정값을 분리하고, 이미 답변한 시스템·범위·미정 예산/일정을 반복 질문하지 않는다. 업무별 명시 표현으로 적용하며 R01~R08 외 범용 의미분석을 추가하지 않는다.
- 요약 내용의 일괄 검토는 운영자의 의견·명시 클릭으로 미검토 STRUCTURE마다 기존 append-only Review를 기록한다. 기존 제외/추가 확인 판단은 변경하지 않는다.
- 검토한 분석 내용을 공식 구조화 편집란으로 불러오는 동작은 저장/ACK/CONFIRM을 실행하지 않는다. 남은 확인사항과 자료 한계도 편집란에 남겨 사람이 검토한다. 필수 미해결 사항은 기존 Backend 확정 Guard가 차단한다.
- Composition 저장의 상태별 필수 범위와 공식 확정의 저장 Version 조건을 UI에도 표시한다. Guard/권한/업무 State는 변경하지 않는다.
- 파일 선택과 반응형 메뉴는 3포털의 공통 UI만 재사용한다. 업로드/추출/자료함/근거/Version의 기존 Backend를 유지한다.
- 수동 재인수 도구는 레이블이 검증된 동일 Repository의 합성 인수환경에서 네 합성 계정만 읽기 검증하여 새 DB에 적용한다. 회사/Review/분석/승인 이력은 복제하지 않는다. 8443/49355/49356 포트는 거부하며 재바인딩은 중지 상태·정확 nonce 확인을 요구한다.
- 이번 증분의 DB Schema/Migration/Trigger 변경은 없다. 기존 fg31m0012026을 새 작업 소유 DB에만 적용한다. 이전 8444 DB/파일/도구는 백업·실제 복원 검증 후 별도 보존한다.


## 2026-11-04 제출 텍스트 진술 근거 집중 보완 계약

사용자 승인 범위는 별도04 기반 개발 브랜치의 분석/구조화/정확한 제출 원문 연결 수정과 격리 합성 검증이다. 실제18445 사용자 TEST 제출/검토·8443/8444·원래DB/파일/계정/이력·PR17~20/main은 변경하지 않는다. 새 물리 Schema/API 경로/Role·외부AI·숫자/기간 해석 정책을 추가하지 않는다.

기존 analysis_basis(run/source_version/review_ids)를 그대로 사용한다. 동일 회사/Root/SiteVersion의 실제 제출 원문과 최신 저장 USE_FOR_REQUEST Review를 검증한 후 STRUCTURE 후보의 IMPROVEMENT field/quote를 다시 검증한다. 이를 기업 진술 출처로만 인정하고 Fact·공식파일 Proof는 생성하지 않는다. 유효 basis에 실제 진술 출처가0건인 file-only는 기존Evidence가 있어야 하며, invalid/stale basis는 파일로 대체해 우회하지 못한다. 운영자 재구조화는 이전 basis를 조용히 삭제하지 않고 재검증하며 회사의 새raw DRAFT는 basis/이전ACK를 승계하지 않는다.

구조화 저장·회사 exact ACK·공식 CONFIRM·Provider current_valid에서 같은 source/freshness를 재사용한다. 필수 구조화 값·missing 미해결 차단·회사ACK·운영자 의견·동시 ordinal/Review idempotency는 유지한다. stale basis의 새추천/구성은 차단하되 과거 Version/Run/Review/Proposal 및 basis없는 기존 파일 경로는 보존한다. 클라이언트가 선택만 한 검토나 미저장 의견은 서버 저장 Review를 대체하지 않는다.

기업명·업종 등 COMPANY_INPUT은 보조참조로 보존하지만 요구사항 출처를 단독 대체하지 않는다. SAVE/CONFIRM/Provider 및 UI는 실제 file-backed Evidence 또는 검증된 제출 진술을 필요로 한다. 같은 Scope 파일의 업무 내용 적절성은 운영자 검토·기업 ACK 대상이며, file_id가 있다는 이유로 의미적 관련성까지 자동 검증했다고 주장하지 않는다.
