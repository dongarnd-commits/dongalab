# MVP v1 자동 인수 근거

실제 검증한 기능/fixture HEAD: 4bfdc2d4a4f0ba07e9ca27a5e0e2dbf65a2eacf1. 이후 인수문서 Commit은 기능 코드가 같다. 2026-10-30. 사용자 인수·main Merge·HTTPS 배포는 미실행이다. H01~H32 전체 완료를 주장하지 않는다.
로컬 전체 Backend/브라우저 정상·예외 자동검증을 완료했다. 사용자 인수 진행 전 원격 Draft PR의 정확 최신 HEAD 필수 CI와 3포털 Preview 성공도 확인한다. 최종 원격 상태의 원천은 PR Checks다.

| ID | 구현한 정상 흐름 | 핵심 예외·보존 | 실제 자동검증 근거 |
|---|---|---|---|
| M01 | 기업 로그인·기업/사업장 등록 | Role/Scope·중복·F5/재로그인 | company_workflow, registration_api, 기존 company/registration E2E, fresh MVP E2E PASS |
| M02 | 자료·원본/Evidence·기업ACK/OP Fact | 타기업·digest·부분/실패·Fact 자동확정 금지 | company_v14/마이그레이션·새 fresh FileFact E2E PASS |
| M03 | 개선요구·정확한 제출 | Draft≠Submitted·원본/Version 불변 | Slice1/2 기존 PG + mvp_analysis_lineage PASS |
| M04 | Rule 구조화·원인후보·검토 | 숫자/원인 날조 금지·원문 일치 | Rule 집중58, 업무 Gold6, PG 실제Worker, fresh E2E PASS |
| M05 | 보완요청·영속초안·응답·검토 | 미검사≠정보부재·검증답변 중복 질문 방어 | improvement_analysis/operator_review + mvp_analysis_lineage, 기존 request E2E |
| M06 | 실제 서비스/FeatureRevision | 미발행·미제공/가짜 서비스 차단 | 승인된649 원천649/10시스템/88분류 실제 로컬 PG + capability 회귀 PASS |
| M07 | 단독·복합 추천 후보 | 근태≠급여·부분제외·일반키워드 과다추천 방어 | 고정23Gold15/23→23/23 + 복합/미제공 요구2 PASS |
| M08 | Composition 역할·연계·Coverage | 해결/부분/미해결·정확 Revision·원천근거 | mvp_solution_pipeline/analysis_lineage PASS |
| M09 | 저장 공고 검색·원천/기간 구분 | LIVE/SNAPSHOT/DEMO 구분·허위 공고 금지 | catalog PG + 미분석 공고 UI/Worker 실제검토 E2E PASS, 별도 공식API GET1회2건 LIVE |
| M10 | 원문 요건·조건 Human Review | UNKNOWN/일부 검토≠전체 자격 확인 | confirmed_notice_reader/matching_comparison + 새 notice review E2E PASS |
| M11 | 3자 Match·항목별 PROPOSABLE | 타기업·과거 입력·불완전 Proof 차단 | 기존matching_integrity + 단일기업 전체 계보 PG/새 매칭UI E2E PASS |
| M12 | MVP_16 표준 초안 | MatchReview/Company ACK·Fact Proof Guard | mvp_proposal_documents/solution_pipeline/전체 계보 PG PASS |
| M13 | 제안내용 검토·새 Version | LEGACY_11·승인·파일/과거 Version 보존 | 기존proposal_production + 명시11→16 전환 PG PASS |
| M14 | 동일 검토Version DOCX/PDF | 한글·본문/제목/출처·digest·권한·생성실패Retry | 5장A4 실물검토, 문서 Unit/PG + 새 브라우저 파일 SHA검증 PASS |
| M15 | 지정 회사 전달·다운로드 | Native취소/Escape/포커스/배경차단·최종전0건·이중클릭1건 | 기존approval PG + 새proposal browser E2E PASS |
| M16 | 회사 수정요청·이력·재로그인 | 새 Version 자동승인 금지·정확 전달본 불변 | 기존proposal_production + 전체 계보 PG/기업portal E2E PASS |
| M17 | Admin4영역 실제연결 | Secret/hash/세션 제외·기존grant·권한상속 금지 | admin PG7/notice PG2 + 새Admin E2E PASS |
| M18 | Rule만 실행·외부4개 미설정 | UI DOM/키보드·직접API·Worker 이중 거부 | provider Unit/PG, fresh E2E 4종409/Job0증가 PASS |

## 실제 실행 결과

| 검증 | 결과 | 증거/범위 |
|---|---|---|
| Backend 전체 Unit | 246 PASS | storage/private/runtime/mvp-unit.xml |
| PostgreSQL 전체 Integration | 292 PASS / 기존1 SKIP | ci/a89f824e7b85/integration.xml, 새 nonce DB/Role/Container 정리 확인 |
| 최신 MVP 집중 PG | 29 PASS | ci/523142efb06d/integration.xml; 하나의 실제 Domain 계보로 제안 전달까지 검증 |
| Frontend lint/TypeScript/Production Build | PASS | 최종 FINAL_FRONTEND_QUALITY_PASS; dev와 build는 같은 Worktree에서 순차 실행 |
| 기존 검토 명령 Unit | 9 PASS | node --test tests/operator-review-unit.mjs |
| API 생성 타입 일치 | PASS | mvp-final-types, API_TYPES_MATCH |
| 기존 3포털 UI Preview | 20 PASS | admin-visual-preview/654cab71-3d3/report.json + production preview404 |
| 신규 MVP 브라우저 | 5 PASS | mvp-analysis-handoff, mvp-notice-review, mvp-portals, 1.7분 |
| 최종 전체 Playwright | 63 PASS / FAIL0 / SKIP0 | 기존58+신규5, 17.6분, ci/61521bb969f0, 자기 DB/Role/프로세스/Container 정리 확인 |
| GitHub 정확 HEAD CI | 원격 결과는 PR Checks 참조 | 이 문서 Commit 후 통합 Draft PR의 필수4개+포털 Preview3개 확인. 인수 전 Draft/main Merge 금지 |

기존 opt-in SKIP1은 격리환경에 없는 실제 공개 공고 원문을 사용하는 선택 검증이다. 실제 고객자료를 복제하여 SKIP을 없애지 않았다. 합성 PDF·OCR·실제 Worker·원문/Version/Role/오류 검증은 별도로 실행했다.

## 정상·예외 증빙

- test_mvp_analysis_lineage.py::test_reviewed_analysis_basis_reaches_notice_match_mvp_documents_and_company_revision: 파일근거 Fact/회사ACK → 제출v1 Rule/USE → 구조화v2 ACK/CONFIRM → Composition/실제원문요건/MatchReview → MVP16 문서/지정회사 전달/수정요청. 결과 Decision을 seed하지 않는다.
- mvp-analysis-handoff.spec.ts: 합성 계정만 준비하고 기업·사업장·파일·제출·원문후보 ACK·OP Fact·분석·검토·구조화·회사ACK·OP CONFIRM을 실제 API/UI로 수행. v1 원문/digest 보존과 v1/v2 명시연결을 확인한다.
- mvp-notice-review.spec.ts: 원문 입력만 있는 공고의 Run/요건0건 → 실제 분석 Job/Worker → 원문근거 → 별도 Human Review/선택 RequirementVersion. 관련성/부분검토를 전체 자격으로 표시하지 않는다.
- mvp-portals.spec.ts: Admin whitelist/grant/미설정, 메뉴별 현재/과거 Context, Match 필수검토/16절 문서/최종전0건/Native발송창/회사수정요청.
- 기존 Slice1/2·Capability·Matching·Proposal·권한·파일·Request 불변 Trigger 회귀를 보존했다. 최초 발견한 오류는 PROGRESS에 남겼으며 실패를 삭제/완화하지 않았다.

## LIVE와 합성 구분

2026-10-30T03:34:08Z 공식 기업마당 pageIndex1/pageUnit2 GET1회: HTTP 성공, 관찰2건, 응답 totCnt1460. 전체수집·모든 원문첨부·공식 자격·장기 가동 성공의 증거가 아니다. 격리 개발 private proof mvp-live/9195b24587134e4aa4c684ad12d49d65/result.json.
업무 E2E는 합성 기업/DEMO·Sanitized 원문을 명시 사용했다. 실제 고객자료/실제 검수 DB/계정을 Fixture로 사용하지 않았다.

## 한계와 다음 승인

Rule/추천은 제한된 표현·동의어·숫자 맥락과 발행 Catalog 근거를 쓰며 범용 AI 의미분석이 아니다. 미지원/미검사 문서, 복잡한 부정/예외, 인과·예산·일정·통합 실현성·사업 자격은 사람 확인이 필요하다.
GPT/GEMINI/CLAUDE/GROK 4개는 NOT_CONFIGURED다. 실제 공급자 자격/전송/비용/보존/OAuth는 별도 결정이며 이번 MVP 통과 선행조건이 아니다.
실제 발행 서비스의 사업적 제공범위, 조직 공식 승인, 사용자 통합 인수, main Merge와 공유DB 백업/복원/Migration·HTTPS 적용은 별도다. 기존 공동 검수 URL은 기존판 그대로다.
사용자 절차는 USER_ACCEPTANCE_GUIDE.md를 따른다.
