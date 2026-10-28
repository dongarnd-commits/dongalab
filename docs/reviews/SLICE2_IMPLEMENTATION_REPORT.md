# DATCO ONE Slice 2 구현·검증 보고

기준 main: `3fe9216c1565741f6ff2ebd8b128e280fa7f8efd`. 개발 Worktree: `dongalab-main`. Branch: `feat/datco-slice2-improvement-analysis`.

## A. 구현 범위

정확한 SUBMIT 제출본과 사업장 Version, 분석 요청 당시 기업 입력·확인 Fact·실제 근거, 직접 Evidence 및 동일 기업/사업장 공통자료를 불변 Manifest로 고정한다. 현재 자료를 자동 탐색하고 지원하는 PDF/DOCX/XLSX/TXT를 기본 포함하며 제외할 수 있다. 이미지·과거·교체·취소 자료의 본문 검사 제외와 한계를 표시한다. 원문 파일명으로 내용이나 기간을 확정하지 않는다.

PostgreSQL Job/Attempt 및 production Worker에서 기존 추출 재사용 또는 로컬 추출/OCR, R01~R08 규칙, 검증된 Candidate/Evidence/검사범위 저장을 수행한다. 동시 요청은 Company 잠금 및 영속 요청 receipt로 멱등 처리한다. Attempt owner/lease/최신 ordinal을 재검사하고 오래된 Worker 게시를 차단한다. 실패한 출력은 저장 그래프를 rollback한 후 제한된 Attempt 오류로 기록한다.

운영자는 후보를 요청 활용/제외/추가 확인으로 검토하고 불변 이력을 남긴다. 별도 영속 요청 초안은 Version 및 정확한 Candidate/Review 관계를 보존한다. F5/재로그인 후 동일 운영자가 다시 열 수 있으며 최종 확인·취소와 편집을 제공한다. 최종 발송은 기존 InformationRequest 생성·발송을 하나의 트랜잭션으로 호출하고 Delivery를 유일하게 저장한다. 발송 후 기존 요청 목록을 갱신한다.

미구현/제외: 외부 AI, 범용 자연어 의미분석, 이미지 이해, 자동 Fact/Improvement CONFIRM, 자동 발송, 자동 Matching/Proposal, 과거 기업정보 Snapshot 복원, 운영 배포. 기존 Company Provider의 확정/현재성 Guard는 변경하지 않는다.

## B. 변경 파일

| 구분 | 파일 |
|---|---|
| Backend | `apps/api/app/company/improvement_analysis.py`, `improvement_rules.py`, `improvement_worker.py`, `apps/api/app/api/improvement_analysis.py`, `apps/api/app/main.py`, `apps/api/app/worker.py` |
| DB | `apps/api/app/infrastructure/improvement_schema.py`, `improvement_constraints.py`, `company_schema.py`, `apps/api/alembic/versions/fe29s0022026_improvement_analysis.py` |
| Frontend | `apps/web/src/portal/improvement-analysis.tsx`, `operator-intake.tsx`, `operator-intake.css`, `company-requests.tsx`, `apps/web/src/generated/api.d.ts` |
| 테스트/하네스 | `apps/api/tests/test_improvement_analysis.py`, `test_improvement_migration.py`, `test_improvement_rules.py`, `slice2_local.py`, `slice2_quality.py`, `ci_run.py`, `isolated_worker.py`, `test_analysis_migration.py`, `v14_migration_chain.py`, `apps/web/tests/improvement-analysis.spec.ts`, `.github/workflows/datco-ci.yml` |
| 기준문서 | `docs/03_DATA_MODEL.md`, `04_STATE_ACTION_MODEL.md`, `05_PERMISSION_UI_MATRIX.md`, `07_INTELLIGENCE_DESIGN.md`, `08_SCREEN_ACTION_SPEC.md`, `10_TEST_ACCEPTANCE.md`, `11_DECISION_LOG.md`, 본 보고서 및 `SLICE2_IMPLEMENTATION_CONTRACT.md` |

Next가 생성한 `next-env.d.ts`의 임시 출력 경로는 제품 변경에서 제외한다. 실제 Secret·기업자료·로컬 Corpus·실행 Artifact는 Git에 포함하지 않는다.

## C. Migration 및 기존 계약 보존

새 additive revision `fe29s0022026`, parent `fd18e0012026`. 기존 Migration 파일은 수정하지 않았다. 공통 Review context에 nullable typed FK를 추가하고 개선요구 종류에 한해 Job/Run/Candidate/Review CHECK 및 공통 계보 검사를 확장했다. 후보 0건 허용은 개선요구 종류에 한정한다.

새 테이블은 11개다. 요청 receipt, Manifest, typed 입력, Run context, 검사 결과, 후보 상세, 검토, 요청 초안 Root/Version/선택 Review/Delivery 각각의 책임을 분리했다. 후보의 Evidence/Rule/검사 관계는 검증되는 제한 JSON과 실제 FK의 조합이며 임의 target graph를 만들지 않았다. 공고 SourceLocation은 변경하지 않는다.

기존 `company_information_requests`의 열·본문 불변 Trigger·State 전이는 변경하지 않았다. 과거 합성 기업·발송 요청이 존재하는 격리 schema에서 Migration 전후 행과 `guard_company_information_request` 함수 정의가 동일함을 검증한다. 빈 증분은 안전한 downgrade/upgrade를 검증하며 새 이력이 있으면 파괴적 downgrade를 거부한다.

실행 범위는 매번 새로 생성한 작업 소유 PostgreSQL 컨테이너·nonce DB/Role 및 그 안의 합성자료다. 실사용 검수 DB에는 적용하지 않았다. 하네스는 실제 DB/Role identity를 검증하고 자신이 생성한 자원만 정리한다.

## D. Rule 및 문서 처리 한계

- R01/R03: 구조화 입력과 명시 라벨의 현황·문제·목표·필요 기능을 직접 인용한다. 원인이나 수치를 추론해 추가하지 않는다.
- R02/R04~R07: 제출본에 측정·적용 범위·설비/시스템·예산·일정의 적용조건이 명시된 경우만 질문 후보를 만든다. 공통문서에 단어가 있다는 이유만으로 과제의 필수항목을 만들지 않는다.
- R08: 동일한 명시 비교 맥락을 가진 제한된 라벨 값의 차이를 검토 후보로 제공한다. 범용 기간·단위·의미 동등성 판단은 하지 않는다.
- PDF는 pypdf 텍스트/페이지 추출을 재사용한다. 스캔/혼합 PDF는 기존 로컬 PDFium/Tesseract 어댑터를 사용하며 10페이지·시간·픽셀 제한 및 OCR 불확실성을 보존한다. 모든 PDF 표·도면을 이해했다고 표시하지 않는다.
- 미추출·미지원·미검사 자료가 있으면 처리 한계를 기록하고 해당 검토 범위에서 누락 판단을 보류한다. 부족정보에 가짜 인용문을 만들지 않는다. 직접 수동 근거와 확인 Fact도 출처·Version을 구분한다.

## E. 입력·근거·검토·초안 연결 증거

통합 테스트가 실제 FK로 `SUBMIT Version → Manifest → Job/Attempt/Run → Parse/검사/Evidence → Candidate → 공통 Review/typed 검토 → 초안 Version/선택 Review → 기존 InformationRequest/Delivery`를 검증한다. 합성 실행 ID 묶음은 Git 제외 `storage/private/runtime/slice2/evidence.json`에 보존한다.

새 Draft는 이전 제출 내용을 대체하지 않는다. 새 SUBMIT 및 사용한 입력/Fact/근거/자료 변경은 현재 활용을 차단한다. 신규 공통자료·신규 Fact는 관련성 재검토 안내이며 무조건 전체 결과를 폐기하지 않는다. 검토가 바뀐 초안은 최신 검토를 다시 연결해야 발송할 수 있다. Version/Review/Attempt의 최신성은 생성시각만이 아니라 ordinal로 판단한다.

## F. 실행 검증

| 검증 | 실제 실행 결과 |
|---|---|
| 전체 Backend Unit | 148 passed, DB 접속 불가 placeholder 및 실제 로컬 한글 OCR |
| 전체 PostgreSQL Integration 최종 회귀 | 247 passed / 기존 stored Korean Live opt-in 1 skipped, 새 격리 DB 단독 실행 |
| Slice 2·Migration·권한 전용 검증 | 12 passed, 별도 새 격리 DB |
| API Type 일치 | API_TYPES_MATCH |
| lint·TypeScript | PASS |
| Production build | PASS, 로컬 고유 Next 출력 디렉터리의 webpack build |
| 전체 Playwright | 50 passed (15.2m), 실제 API·Worker·PostgreSQL. 최종 단일 작성폼 변경 후 Slice 1·2 집중 E2E도 3 passed |

이는 문서상 설계 판단과 구분한 실제 실행 결과다. 초기 실패는 숨기지 않는다. 첫 회귀에서 Windows OCR 실행환경 누락과 별도 로컬 Corpus 누락이 있었고 테스트용 기존 OCR 이미지/무시된 자산을 연결해 해결했다. 이후 테스트 Web 시작 시 Windows Turbopack 파일 잠금으로 한 차례 실패하여 고유 nonce 디렉터리·프로세스로 재실행했다. 빌드·브라우저와 동시에 실행한 회귀에서 기존 OCR 테스트 1건이 OCR_TIMEOUT으로 실패하여, 다른 무거운 작업을 종료한 뒤 전체 회귀를 단독 재실행해 247 passed를 확인했다. 테스트 제한시간 완화·제거·신규 SKIP은 없다. 기존 stored Korean Live opt-in 테스트는 원래 정책을 유지한다.

Private 로그와 XML: `storage/private/runtime/slice2/`, `storage/private/runtime/ci/`. 로컬 테스트 자산과 원문은 외부 AI에 전송하지 않았다.

## G. 회귀 및 인수

Slice 1의 정확한 접수/원본/F5·Scope, Company Fact 확인·충돌·기업 ACK, Notice 공식 Review, Capability/Matching 계보·Snapshot·현재성, Proposal Version/승인/문서 생성을 유지한다. 신규 E2E는 실제 Worker와 PDF digest, 제출 v1/Draft v2 분리, 근거 검토, 초안 편집·F5·재로그인, 최종 확인 전 요청 0건, 발송 취소, 이중 클릭 후 요청 1건을 검증한다. Backend는 발송 중 실패 시 요청 생성도 rollback함을 검증한다.

## H. GitHub

전용 Feature Branch만 사용한다. 최종 구현 Commit SHA·Draft PR URL·최신 CI 결과는 완료 채팅 및 PR Checks에 기록한다. main Merge·Draft 해제·HTTPS 적용은 수행하지 않는다.

## I. 남은 범위와 의사결정

사용자 인수: PENDING. 로컬 Rule의 제한된 라벨/적용조건 범위를 넘어서는 의미분석, 복잡한 표·도면·이미지 지원, 대용량 성능·운영 배치 검증은 완료로 주장하지 않는다. 외부 AI Provider/모델/전송·비용·보존 정책, 향후 자동 분석 실행 정책, 실사용 DB Migration·배포는 별도 승인 대상이다.
