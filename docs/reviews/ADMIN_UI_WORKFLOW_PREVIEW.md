# DATCO 관리자 포털 UI 정리 v0.2.1

## 현재 적용 기준

2026-10-20 사용자 승인 작업. 기존 feat/datco-admin-ui-preview-v01 / Draft PR #11 유지. 시작 HEAD 8ce5820d93399cebe9ac60dff18a3a781679af11.
이번 지시에 따라 이전 ‘명시적 예시 전환’ 방식은 일반 관리자 화면에서 제거한다. 아래 v0.2 기록은 변경 이력이며 현재 동작으로 해석하지 않는다.

- 최상단 대형 안내 배너 및 1개/전체/종료 전환 버튼 제거. 작은 헤더 ‘데이터 미연결’과 데이터 영역의 ‘데이터 연결 후 표시됩니다.’만 사용한다.
- 미리보기 시작 후 동일한 M-01~M-12 업무 컴포넌트를 표시한다. 빈 화면용 축약 레이아웃을 사용하지 않는다. Sidebar/Header/Card/검색/필터/목록/컬럼/상세/입력/검토/Version UI 유지.
- 일반 진입은 Fixture import 없이 빈 배열로 구성한다. 데이터 조회 결과로 오인되지 않도록 실제 조회 건수는 표시하지 않고 통계는 —로 둔다. 실제 데이터 없음/조회 0건/가짜 발행 완료를 주장하지 않는다.
- 미연결 저장·개정안·발행·검토·접근 요청 버튼은 화면에 보존하고 비활성화하며 이유를 제공한다. 가상 Version v0나 가상 공고를 기본 데이터로 표시하지 않는다.
- 원본 adminFixture.json은 보존한다. tests/admin-preview-fixture-entry.tsx만 이를 import하고 testData를 주입한다. 정상/0개/1개/여러 개 및 차단 시나리오를 그대로 검증한다.
- Runner만 고유 shadow 폴더에 /ui-preview/admin-fixture Route를 생성하고 build-admin-preview.mjs --test-fixture를 사용한다. 실제 app tree에는 이 Route가 없으며 일반 URL query로 Fixture를 켤 수 없다.
- 일반 및 Runner의 테스트 Route 모두 운영 NODE_ENV에서는 404. 실제 사용자 시연 서버는 테스트 Route/테스트 Entry를 복사하지 않고 별도 pinned runtime 소스를 사용한다.
- 기존 수요기업·운영자 미리보기, 로그인·세션, 업무 API/DB/Role/Permission/State/FROZEN/Private Storage 변경 없음.

관리자 테스트를 삭제·SKIP하지 않고 일반 미연결 화면 검증과 격리 Fixture 업무 검증으로 재구성한다. 이전/이후 대시보드와 일반 12개 화면 캡처를 runtime에 기록한다.
USER_ACCEPTANCE: PENDING / BACKEND_INTEGRATION: NOT_STARTED / PHASE1_FULL_E2E: NOT_COMPLETED / SYSTEM_ACCEPTANCE: NOT_TESTED.

v0.2.1 최종 검증 `85ca6fee-9f3`: 관리자 8/수요기업 5/운영자 6, 총 19 PASS / 0 FAIL / 0 SKIP. lint/typecheck/build 및 세 미리보기+격리 Fixture Route의 운영 404 PASS. 일반 재진입 시 Fixture 비노출 검증 PASS.
화면 바로가기는 활성 상태로 유지하고, 서버 데이터 처리만 비활성화한다. 테스트/일반 번들의 컴파일 출력 경로를 분리했다.
최초 `d292fa3e-193`에서 M-06 미연결 안내 누락 1건을 확인해 보완했으며 실패 증거를 보존했다. 중간 통과 이후 캐시 격리와 바로가기를 보완한 최종 소스로 위 결과를 다시 확인했다.

## v0.2 구현 이력 — 아래는 이전 버전 기록

# DATCO 관리자 포털 UI 미리보기 v0.2

## 작업 기준 및 범위

2026-10-20 사용자 실행명령. 기준 main `c41fc781269f91a11f36f66204fd83fa108f4c14`.
사용자 제공 `DATCO_관리자_Codex_전달패키지_v0.1/source/AdminPortal.tsx`, CSS, 가상 Fixture를 재사용한다. 관련 README/UI 명세/데이터계약/테스트 명세를 검토했다.
AGENTS → docs/00 Baseline → 01 Architecture 및 04/05/08/10의 State·Role·Permission·화면·검증 계약을 변경하지 않는다.
이번 명령의 UI 전용·빈 상태·명시적 예시 모드가 패키지 v0.1의 과거 로그인·연동 지시보다 우선한다.

## 구현 및 원본 대비 보완

- `/ui-preview/admin`: 기존 company/operator와 동일한 독립 esbuild Route Handler 방식. 개발 환경에서만 HTML/번들을 제공하며 운영에서는 번들 생성 전에 404.
- 하드코딩 아이디·암호 검증 제거. ‘미리보기 시작’으로만 진입한다. 기존 W0 로그인/세션은 변경하지 않는다.
- 기본은 빈 목록·미연결 안내. 메뉴 12개와 화면의 목적은 확인 가능하다. 예시를 선택해야 가상 Fixture를 화면에 표시한다.
- ‘1개 목록’은 각 관리 목록의 첫 레코드만 표시하는 빈도/레이아웃 검사 모드다. 일부 참조 기능이 없어 발행조건이 미충족일 수 있다. 실제 원천의 일부를 가져온 것이 아니다.
- ‘전체’는 원본 12 Feature/6 Capability/3 공고 등을 사용한다. 종료/새로고침 시 UI 상태를 초기화한다.
- 원본 네이비/블루 디자인, Sidebar/Header/Card/Table/입력/검토/상세를 유지한다. 공고 검색·Version 이력 및 이전/홈 이동을 보완했다.
- 원본의 선택한 서비스→편집 상태 동기화 Effect는 명시적 선택 Action으로 옮겨 Next/React lint와 호환시켰다. 신규 개정안 ID는 중복되지 않게 발급한다.
- 공고/품질 검토 메모는 대상별로 분리하고 품질 메모의 화면 저장 결과를 표시한다. 감사 검색은 시각도 포함한다.
- 발행 버전의 직접 편집 금지, 근거/기능/조건 미충족 차단, 실제 Scope를 바꾸지 않는 승인 전 접근 요청, 외부 AI 호출 없는 점검 등 원본의 화면 시뮬레이션을 유지한다.

## 화면별 동작

| ID | 화면 | 시연 Action |
|---|---|---|
| M-01 | 관리 대시보드 | 예시 건수·확인업무·최근활동 및 바로가기 |
| M-02 | DMP 기능 | 검색·분류·선택·Revision/근거·연결 서비스 이동 |
| M-03 | Capability | 선택·해결범위·Feature·발행 원본 보호·신규 개정안·편집 |
| M-04 | 서비스 버전·발행 | 조건·차단사유·확인창·화면 발행 표시·Version 이력 |
| M-05 | 정부지원사업 공고 | 검색·선택·가상 원문 출처·기간·Version·요건 이동 |
| M-06 | 공고요건 | Evidence·Comparator·대상별 메모·예시 검토 표시 |
| M-07 | 사용자·계정 | 역할·계정·현재 Scope·접근범위 화면 이동 |
| M-08 | 접근범위 | 사용자/기업 선택·승인 전 요청·중복 차단·실제 Scope 유지 |
| M-09 | AI 분석 운영 | 방식/결과 구분·실패/차단사유·호출 없는 재시도 조건 점검 |
| M-10 | 데이터 품질 | 근거/Version 문제·메모·미해결 상태 유지 |
| M-11 | 외부 연동 | 미연결 상태·선행조건·준비사항 확인 (접속 없음) |
| M-12 | 감사·변경 이력 | Actor/Action/Target/시각 검색·상세·LOCAL_UI_ONLY 구분 |

## 검증 경계

`node apps/web/run-admin-preview-tests.mjs`는 고유 ignored runtime 폴더에 소스를 복사하고 별도 Next 포트와 node_modules 연결을 사용한다. Git Worktree가 아니다.
API_ORIGIN은 127.0.0.1:1이며 DB/API/Worker를 시작하지 않는다. CSP connect-src none, form-action none으로 외부 통신·폼 제출을 막는다.
관리자 8개 Playwright 시나리오, 수요기업 5개 및 운영자 6개 회귀를 실행한다. lint/typecheck/build 후 세 미리보기의 운영 404를 확인한다.
원본 QA는 참고 자료일 뿐이며, 실제 실행 결과는 runtime report/log/스크린샷 및 새 HEAD의 CI 결과를 따른다.
원본 T-A00/N-A01/N-A11의 가상 계정 인증 테스트는 이번 지시에 따라 미리보기 진입·종료와 운영 404 검증으로 대체한다. 실제 인증·보안 통합 검증으로 보고하지 않는다.

## 후속 개발과 미연결 항목

실제 관리자 API/DB, 실제 DMP 649개 Feature, Capability 발행, 공식 Notice/Requirement, 실제 Role/Membership 변경, 실제 AI 실행, 서버 Audit, DMP SSO는 이 화면에 연결하지 않는다.
관리자는 Operator/기업 승인자의 업무 권한을 자동 상속하지 않는다. 기존 공고 검토·발행·권한 Action은 관련 서버 계약으로 재검증해야 한다.
기존 사용자 입력·Fact·Matching·Proposal·승인정책·단일 계정/구두/서면 승인정책을 이번 UI에서 확정하지 않는다.
사용자 UI 승인 후 별도 명령으로 실제 API·Provider 계약과 연결하며, 세 포털의 Fixture는 실시간 공유 데이터가 아니다.
USER_ACCEPTANCE: PENDING / BACKEND_INTEGRATION: NOT_STARTED / PHASE1_FULL_E2E: NOT_COMPLETED / SYSTEM_ACCEPTANCE: NOT_TESTED.

원본 Fixture의 COMPANY_USER는 실제 Role 추가가 아닌 가상 분류다. 실제 연동 시 기존 COMPANY_EDITOR 등 승인된 4개 Role과의 매핑을 확인해야 하며 이번에는 Auth 계약을 변경하지 않았다.

## 로컬 실제 실행 결과

최종 `f98cac1e-2ef`: Playwright 19 PASS / 0 FAIL / 0 SKIP (관리자 8 / 기업 5 / 운영자 6), lint/typecheck/build PASS, 세 미리보기 운영 404 PASS. DB/API/Worker 시작 없음.
최초 `96c671bb-906`: 16 PASS / 3 FAIL (원본 Label 접근성 이름 문제). 보완 후 `d3b4a8fa-190`: 18 PASS / 1 FAIL (테스트 innerText/textContent 공백 비교 불일치). 동일 innerText 전후 비교로 고친 후 최종 재검증 통과. 실패 로그·스크린샷은 runtime에 보존했다.
