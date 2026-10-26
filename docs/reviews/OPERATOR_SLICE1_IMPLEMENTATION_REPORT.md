# 운영자 Slice 1 구현·검증 보고서

기준 main: `9a9c6eef3b0765894dd2d739d9fffaacdcc8d2f4` (PR #14 병합). 작업 브랜치: `feat/datco-operator-real-workflows`. 사용자 명령 v1.0에 따라 Slice 0와 Slice 1만 구현한다. 사용자 인수와 후속 Slice는 별도다.

## A. 기존 기능 재사용

[Backend 재사용 감사](OPERATOR_BACKEND_REUSE_AUDIT_v1.md)를 참조한다. Company/Site/Profile/재무/수행이력/File/Evidence/불변 ImprovementVersion·SUBMIT/Company Access 및 보완 요청 Panel/API를 재사용했다. Capability/Notice/Matching/Proposal Backend를 중복 구현하지 않았다.

## B. 구현 범위

- 실제 `/portal/operator`를 공통 로그인·세션 및 기존 DATCO_OPERATOR Role로 실행한다. Preview 경로는 실제 업무 원천으로 사용하지 않는다.
- 5개 업무 그룹 안에 기존 12개 하위 업무 경로을 유지하고, 기업 통합 업무에서 현재 기업정보·사업장·재무·수행이력·접수 개선요구·관련 PDF를 함께 확인한다. 후속 메뉴는 준비 중으로 표시한다.
- 신규 읽기 API: `GET /company/operator/intake`, `GET /company/operator/intake/{company_id}?version_id=`. 기존 Role/Membership/Scope 검사만 재사용한다. 접수 Root 수와 SUBMIT 기록 수를 구분하여 실제 집계한다.
- SUBMIT Review가 없는 DRAFT Version은 접수 목록/상세 선택에서 제외한다. 과거 제출 이력이 있는 현재 DRAFT Root에서는 이전 제출 Version을 계속 제공하고 새 미제출 Version 요청은 404다.
- 정확한 제출 Version과 그 Version의 site_ordinal·첨부 Evidence/File을 읽는다. 후속 기업 수정으로 과거 제출본을 덮어쓰지 않는다. Company·선택 Version·메뉴는 URL에 유지하여 F5/재로그인 후 재검증한다.
- 기존 SUBMIT에는 CompanyInputVersion Snapshot FK가 없다. 현재 기업정보·재무·이력/현재 파일 목록과 제출 당시 개선요구·사업장·첨부를 분리 표시하며, 과거 기업정보를 시각으로 추정하거나 새 Snapshot을 만들지 않는다.
- 기존 보완 요청 작성/응답/검토 API와 Panel은 유지한다. 새 운영자 의견 저장 계약·AI 분석·자동 요청·추천·매칭·제안서 작성은 추가하지 않았다.
- 신규 DB Schema/Migration, Role/Permission/State/Assignment, 기존 Company Provider·navigation·승인 Guard의 변경은 없다. 원본·Evidence·Version·Review를 삭제하거나 재연결하지 않는다.

주요 변경 파일: `apps/api/app/company/operator_intake.py`, `apps/api/app/api/company.py`, `apps/api/tests/test_operator_intake.py`, `apps/api/tests/ci_run.py`, `apps/web/src/portal/operator-intake.tsx`, `operator-intake.css`, `operator.tsx`, 생성 API Type, 실제 E2E·Context 회귀 및 08/10/11 문서.

## C. 실행 검증

아래는 최종 실행 결과다. 초기 실패는 Private 로그에 보존하며 최종 PASS와 구분한다.

| 검증 | 결과 | 근거 |
|---|---|---|
| 접수 읽기 API 실제 격리 PostgreSQL | PASS | 새 접수 테스트 2개, DRAFT/제출/후속 초안/과거 사업장·Role·Scope·집계·원본 |
| 전체 Backend | PASS | 372 passed / 1 skipped, 새 격리 DB. 기존 stored Korean Live 원문 opt-in 테스트 1건 SKIP |
| Backend Unit | PASS | 137 passed |
| 기존 사용자 검수 자료 보존 | PASS | 기존 DB 읽기 전용 확인: 보존 원본 3개 SHA/digest 및 기존 제출 Version·SUBMIT Review 유지, Migration 없음 |
| 실제 검수환경 브라우저 | PASS | 운영자 로그인·실제 집계 1/1/1·정확한 제출본·PDF SHA256·F5·타기업404·모바일 넘침 없음 |
| lint/typecheck/build/API Type | PASS | 최종 Production build, 세 역할 Preview의 lint/typecheck, API_TYPES_MATCH |
| 전체 Playwright | PASS | 최종 47 passed (11.9m), 수요기업·Notice·Capability/Proposal·세션/Scope·접수/원본 E2E |
| 3개 역할 Preview | PASS | 운영자/수요기업/관리자 각각 실제 Preview 테스트·lint/typecheck/build 및 Production Preview 404 |
| GitHub CI | NOT_TESTED | Commit/Push·Draft PR 후 최신 HEAD로 확인 |

Private 실행 증거: `storage/private/runtime/operator-slice1/`. 새 사용자 검수 DB: `datco_test_da53a042a07f`, Migration head `fd18e0012026`. 새 DB에만 기존 승인 Migration 적용. 기존 업무·기존 사용자 검수 DB Migration은 실행하지 않았다.

초기 실행 중 로컬 검수 스크립트 경로·인코딩·테스트 lint와 Next 명시적 재시도 문제를 수정했다. 동시 컴파일/브라우저 실행의 메모리 부족은 이번 작업 소유 프로세스만 정리하고 순차 검증으로 전환했다. 새 E2E가 기존 빈 계정을 재사용한 문제는 전용 실제 Role 계정 3개로 분리했다. 기존 조회의 ECONNRESET에는 HTTP 오류를 재시도하지 않는 maxRetries=2만 적용했다. 구형 운영자 Context 기대는 새 접수 계약으로 갱신하되 기존 API 호환 검증을 유지했다. 초기 실패 로그는 Private 경로에 보존하며 최종 회귀 결과와 구분한다. 자료 메뉴명 변경에 따른 기존 등록 회귀의 기대값을 동기화했고, 선택 기업이 없는 운영자 홈은 기존 기본 URL을 유지하도록 정리했다. 최종 전체 E2E는 47개 모두 통과했다. Next 업그레이드 권고는 남으며 버전 변경은 수행하지 않았다.

## D. 다음 Slice 준비 상태

- Slice 2: 기존 로컬 추출·수동 검토·보완 요청/응답 이력 재사용 가능. AI 의미분석 Provider/모델/자료전송·비용·보존 정책은 미승인이다. 키워드 검색을 AI 분석으로 표시하지 않는다.
- Slice 3: 원천 기능 재고와 관리자 발행 CapabilityVersion·후보검색·Composition API 존재. 실제 추천은 발행 Catalog로 제한하며 649개 원천 기능 자체를 제공 가능한 솔루션으로 확정하지 않는다. 신포털 연결은 후속 범위다.
- Slice 4: 기존 기업마당 Collector/NoticeVersion/분석/고정 Snapshot/Matching·UNKNOWN 의미 재사용. 현재 실시간 API 접근과 범용 한국어 조건 해석·최대3개 자동추천의 완료는 주장하지 않는다.
- Slice 5: 기존 ProposalVersion·Manifest·내용검토·승인/기록모드·Private DOCX/PDF·inbox 재사용 가능. 현재 11개 Backend 내용항목과 사용자 9개 장 구조의 매핑은 후속 설계 대상이다. 기존 승인·근거·현재성 Guard는 유지한다.
- Snapshot 확대/새 운영자 의견 저장·Assignment 정책을 필요로 하는 변경은 별도 영향·결정 대상이다. 외부 AI에 기업 원문을 전송하지 않았다.

## E. Git 및 보호

시작 HEAD/main: `9a9c6eef3b0765894dd2d739d9fffaacdcc8d2f4`. 최종 Commit·Push·Draft PR·CI·Working Tree는 최종 검증 후 아래에 기록한다. 기존 브랜치·Stash·백업·Private Storage는 보존한다. main Merge, Draft 해제, 운영 배포·업무 DB Migration·물리 삭제·Next 업그레이드는 실행하지 않는다.

## F. 사용자 검수

새 격리환경 로그인: http://localhost:49356/login

운영자 홈: http://localhost:49356/portal/operator

실제 DATCO_OPERATOR 계정: `MANUAL_operator_da53a042a07f`.

비밀번호 안내는 Git 제외 로컬 파일 `storage/private/runtime/operator-slice1/credentials.private.txt`에만 보관한다. 합성 기업 `TEST Operator Slice1 isolated validation`에는 기존 관리자 API로 Company Access를 부여했으며 B 기업에는 부여하지 않았다. 모든 자료는 TEST이며 실제 고객정보·PDF를 복사하지 않았다.

시크릿 창에서 로그인 → 업무 대시보드의 실제 집계/접수 항목 → 제출 내용 검토 → 기업·사업장·3개년 재무·수행이력 → As-Is/To-Be와 제출 당시 사업장 → PDF 원본 다운로드 → F5 → 권한 없는 기업 차단 순서로 검수한다. 홈 캡처를 공유한 뒤 화면별 사용자 검수를 진행한다. 기존 환경 localhost:58936은 이번 검수의 새 주소가 아니다.

OPERATOR_BACKEND_AUDIT: PASS

OPERATOR_SLICE1_FUNCTIONAL: PASS

OPERATOR_SLICE1_E2E: PASS

OPERATOR_SLICE1_CI: NOT_TESTED

OPERATOR_USER_ACCEPTANCE: PENDING

OPERATOR_FULL_WORKFLOW: NOT_TESTED

SYSTEM_ACCEPTANCE: NOT_TESTED
