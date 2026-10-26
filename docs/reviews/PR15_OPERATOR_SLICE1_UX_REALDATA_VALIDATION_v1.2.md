# PR #15 운영자 Slice 1 UI·실제 자료 검증 v1.2

검증일: 2026-10-26. 사용자 통합 보완 v1.2 승인 범위에 따른 결과다. 사용자 직접 인수는 PENDING이며 Slice 2~5·전체 업무 완료를 의미하지 않는다.

## A. Git 및 변경 범위

- Branch: `feat/datco-operator-real-workflows`
- 시작 HEAD: `70d0857c92ecda8674f337159277ad56a8e0e4f4`
- 기준 main: `9a9c6eef3b0765894dd2d739d9fffaacdcc8d2f4`
- 기존 Draft PR: https://github.com/dongarnd-commits/dongalab/pull/15
- 로컬 기술 검증 완료. 이 구현 Commit을 Push한 뒤 CI 결과를 추가 기록한다.
- 기존 개발 브랜치·Stash 보존 확인, 백업·Private Storage 삭제 없음. 기존 업무/사용자 검수 DB Migration 및 운영 배포 미실행.
- 새로운 Branch/Worktree, Reset, Force Push, main Merge, Draft 해제는 수행하지 않는다.

변경 파일:

| 파일 | 변경 이유 |
| --- | --- |
| `apps/web/src/portal/operator-intake.tsx` | 실제 Intake/API 연결을 유지한 로고·아이콘·메뉴·상단바 복원, 접수 정렬, 제출 이력과 검토 근거 표시 |
| `apps/web/src/portal/operator-intake.css` | 기존 운영자 토큰/버튼 재사용, 검색·카드·긴 기업명·모바일 메뉴·금액 표시 |
| `apps/web/src/portal/operator-intake-records.tsx` | 원래 금액 정밀도·단위를 보존한 재무/수행이력/출처별 근거 표시 |
| `apps/web/tests/operator-intake.spec.ts` | 기존 실제 제출/PDF/Scope 검증에 긴 기업명·30자리 금액·근거 표시·모바일 선택 보존 추가 |
| `docs/08_SCREEN_ACTION_SPEC.md` | 승인된 화면 표시 기준 동기화 |
| `docs/10_TEST_ACCEPTANCE.md` | 합성 회귀와 실제 자료 읽기 전용 검증 기준 구분 |
| 이 보고서 | 결과·한계·사용자 검수 안내 |

Backend/API/생성 API 타입/Schema/Migration/Auth/Role/Permission/State는 이번 보완에서 변경하지 않는다. `next-env.d.ts` 등 도구 생성 변경은 Private에 보존 후 이번 실행에서 발생한 부분만 원래 내용으로 복원했다.

관련 기준: AGENTS.md, Project Baseline, System Architecture, Screen Action Spec, Test Acceptance, 기존 Slice 1 Backend Reuse Audit/Implementation Report.

## B. UI 보완

| 항목 | 구현 및 검증 범위 | 판정 |
| --- | --- | --- |
| 디자인 일관성 | 기존 Layers 로고·아이콘·선택 메뉴·상단바·버튼·색상·카드 재사용, 홍보 배너/Preview fixture 미사용 | PASS |
| 메뉴 | 5개 업무 영역, 대시보드 중복 제목 제거, 기존 12개 내부 화면 식별자 유지, 후속 업무 준비 중 | PASS |
| 업무 대시보드 | 실제 Company/제출 Root/제출 기록 수 유지, 검토 필요·최근 제출 우선 | PASS |
| 수요기업 목록 | 검색 크기·정렬·이름 줄바꿈·실제 접수 건수, 선택 후 업무 이동 | PASS |
| 기업 통합 업무 | 현재 기업정보와 정확한 제출 Version/사업장/첨부 구분, 현재 사업장 업종·공정 표시 | PASS |
| 재무정보 | 중복 연도 제거, 한국어 항목·명시 KRW 단위, 문자열 쉼표 표시, 30자리 금액 무손실, 미등록 0 생성 없음 | PASS |
| 수행이력 | 사업명·지원기관·수행기간·참여 역할, 긴 내용 펼치기, 실제 연결된 증빙만 링크 | PASS |
| 개선요구·제출 이력 | 기업 원문/As-Is/To-Be·선택 제약·정확한 제출 첨부, SUBMIT 기록을 제출 이력으로 표시 | PASS |
| 확인된 기업정보 | 별도 검토 완료 기록이 없다는 안내, 실제 Fact Review/원본 근거 유지 | PASS |
| 자료 근거 | 현재 입력값/서류 추출 후보/검토 기록 구분, 중복 요약 제거, 전체 Evidence는 항목별 펼치기로 보존 | PASS |

모르는 단위는 환산하지 않는다. 저장된 재무/통화/기간/원문은 변경하지 않는다. 현재 Profile에 없는 수행내용 전용 필드를 임의 생성하지 않는다. 별도 Snapshot FK가 없는 과거 기업 전체 Profile은 추정하지 않는다.

## C. 기능 보존 및 기술 회귀

최종 순차 실행 결과는 아래 표에 갱신한다. 이번 수정의 자동화 fixture는 모두 합성이며 실제 기업자료는 CI로 전송하지 않는다.

| 검증 | 결과 |
| --- | --- |
| Backend Unit | PASS — 137건 |
| 전체 Backend/PostgreSQL | PASS — 372 PASS / 기존 opt-in 1 SKIP |
| 실제 PostgreSQL·Private Storage Playwright 전체 | PASS — 47건 |
| lint/typecheck/production build/API 타입 | 모두 PASS, API_TYPES_MATCH |
| 운영자·수요기업·관리자 Preview | 모두 최종 PASS (관리자 build 알림 재실행 포함) |
| 기존 합성 사용자 검수환경 | 실제 로그인·조회·F5·원본 해시·모바일 폭·타기업 직접 URL/API 차단 PASS |

보존 대상은 실제 API 연결, DATCO_OPERATOR/Company Access, 미제출 DRAFT 제외, 제출 Version/site_ordinal/Evidence/File, 원본 다운로드, F5·재로그인 및 기존 수요기업·관리자 회귀다. 선택적 보완 요청은 기존 Panel/API를 재사용하며 자동 분석·신규 요청 Workflow를 개발하지 않는다.

초기 집중 E2E는 수행이력 이름이 숨겨진 근거에도 존재하여 텍스트 선택자가 중복된 실패를 기록했다. 수행이력 제목을 정확히 선택하도록 수정한 후 전체 회귀 47건을 다시 수행해 모두 통과했다. 실제 자료 첫 브라우저 시도는 초기 렌더 대기시간 부족으로 실패했고 충분한 대기시간을 적용한 재검증은 PASS다. 집중 E2E 실패 로그와 실제 자료 브라우저 시도 상태를 Private에 보존했다.

기존 SKIP은 저장된 한국어 Live 원문 검증의 opt-in(`DATCO_TEST_STORED_KO=1`) 항목이며 이번 변경으로 추가한 SKIP은 없다. 관리자 Preview는 브라우저·lint·typecheck 통과 후 Next 버전 알림이 build를 두 번 종료시켰다. 동일 shadow/동일 build 명령의 세 번째 실행은 0으로 완료됐고 production의 모든 Preview/fixture 경로 404도 통과했다. 처음 실패한 report와 최종 report-final.json을 모두 보존했으며 Next/package 버전이나 제품 코드를 변경해 우회하지 않았다.

## D. 동아테크놀로지 실제 자료

### 위치와 기존 승인 범위

| 항목 | 읽기 전용 확인 결과 |
| --- | --- |
| 원천 DB | `datco_test_4c55593f248e` — 기존 PR #14 사용자 검수 DB |
| 현재 기본 검수 DB | `datco_test_da53a042a07f` — 별도의 합성 검수 DB |
| Company ID/기존 계정 범위 | Git 제외 Private inventory에 최소 메타데이터로 보관 |
| 현재 Profile/CompanyInputVersion | 존재, 운영자 Projection과 원천 상세 응답의 전체 inputs 일치 |
| 사업장 | 1건, 실제 저장된 Site/Version 유지 |
| 재무 | 2023/2024/2025 존재, 원천 입력과 조회 응답 일치 |
| 수행이력 | 1건 존재 |
| 제출된 개선요구 Version | 설비·점검·고장 관련 요구 존재, SUBMIT 기록이 있는 Version 1건 확인 |
| PDF 원본 | 5개, 기존 File ID·Evidence 참조 및 SHA-256 모두 일치 |
| 기존 접근권한 | 실제 DATCO_OPERATOR 1개 계정에 이미 부여된 Company Access 사용 |
| 타기업 파일 | 기존 Scope 밖 원본 15개 접근 404 확인 |
| 기존 DB Migration | 미실행. 원천 revision `fc07d0012026` 유지 |
| 자료 복사·새 권한 | 미실행·불필요 |

기업 이름이 같다는 이유로 다른 DB의 자료를 동일 자료라고 판단하지 않았다. 기존 v1.4.2 DB에서도 조사했으나 이번 이름 조건에 해당하는 실제 기업을 확인하지 못했으며 합성 자료로 대체하지 않았다.

### 실제 실행 방법과 판정

기존 승인된 운영자/Company Scope로 READ ONLY 트랜잭션에서 Backend 원천/접수 Projection·파일 해시를 대조했다. 이어 기존 로그인 경로로 같은 운영자 세션을 발급하고, 원천 DB 연결에 `default_transaction_read_only=on`을 강제한 임시 현재 코드 API/Web에서 실제 `/portal/operator`를 조회했다. 세션은 기존 인증을 거쳤으며 Role/Company Access 우회는 없다. 임시 서버는 검증 후 종료했고 기존 서버는 유지했다. 추가로 기존 Editor 계정의 실제 수요기업 화면과 API를 같은 Company ID로 조회해 기본정보·3개년 재무·수행이력을 운영자 화면과 대조했다. 대조 전후 원천의 Company/Input/Site/File/Evidence/Candidate/Fact/Improvement 전체 응답이 불변임을 확인했다. 기존 업무 객체를 저장/수정/재제출하지 않았다. 정상 로그인에 따른 세션/인증 감사 생성은 기존 인증 경로의 동작이다.

| 실제 자료 항목 | 결과 |
| --- | --- |
| 기존 운영자 인증·조회 권한 | PASS |
| 기존 수요기업 화면/수요기업 API와 운영자 응답·화면 대조 | PASS |
| 3개년 재무 및 수행이력의 수요기업 화면/저장값/운영자 응답·화면 | PASS |
| 정확한 제출 Version·As-Is·To-Be·F5 | PASS |
| File/Evidence 참조·원본 5개 다운로드 해시 | PASS |
| 타기업 원본 접근 거부 | PASS (읽기 전용 Backend 검증) |
| 최초 이후 다수 수정·재제출 이력 | NOT_TESTED — 발견된 제출 Version은 1건, 이력을 추가 생성하지 않음 |
| 모든 원본 PDF 항목의 OCR·수치 재판독 | NOT_TESTED — 이번 범위는 저장값의 연계와 원본 무결성, 추출 재실행 아님 |

DONGATECH_OPERATOR_REALDATA_E2E는 **PARTIAL**로 판정한다. 현재 존재하는 자료의 실제 브라우저 조회/원본 무결성은 PASS지만 요청에 언급된 여러 재제출 이력은 발견되지 않았고 모든 PDF의 수치를 새로 재판독하지 않았다. 합성 회귀 PASS를 이 범위의 PASS로 대신하지 않는다.

### 자료 보호와 승인

전체 기업 상세 응답을 별도 JSON으로 저장하려던 초기 조사 명령은 자동 승인 검토가 복제·보관 승인 범위 초과로 거부했다. 실행하지 않고, 건수·연도·기존 권한·해시 일치만 기록하는 안전한 조사로 축소해 승인·완료했다. 원본 응답·PDF·실제 기업 스크린샷은 새 검증 폴더/Git/CI로 복제하지 않았다. 비밀번호·사업자등록번호·재무 상세값·문서 전문은 공개 보고서에 포함하지 않았다.

이번 검증은 기존 승인된 범위로 가능했으므로 추가 복사/권한 승인안은 필요하지 않다. 실제 기업 쓰기·새 제출·Migration·원본 복사·새 계정 접근 확대·외부 AI 전송은 계속 별도 승인 대상이다.

Private 결과: `storage/private/runtime/operator-slice1-v12/inventory.private.json`, `realdata-readonly.json`, `realdata-browser.json`. 전체 기업 응답을 저장한 사본은 없다.

## E. 사용자 검수환경

- 로그인: http://localhost:49356/login
- 운영자 홈: http://localhost:49356/portal/operator
- 계정: `MANUAL_operator_da53a042a07f` / 실제 Role `DATCO_OPERATOR`
- 비밀번호: `C:\Users\PC\Desktop\정부지원사업운영체제 구축\dongalab\storage\private\runtime\operator-slice1\credentials.private.txt`
- DB: `datco_test_da53a042a07f` / 기존 head `fd18e0012026`, 이번 보완에 신규 Migration 없음
- 표시자료: 개인정보 없는 기존 합성 검수기업. 동아테크놀로지 실제 자료와 혼합하지 않았다.
- 실제 자료 검증은 별도 기존 원천 DB의 임시 읽기 전용 서버에서 자동 대조했으며, 종료된 임시 주소를 사용자 접속 주소로 제공하지 않는다.

검수 순서:

1. 로그인 후 DATCO 운영자 홈의 로고·메뉴·실제 1/1/1 집계를 확인하고 홈 화면을 캡처한다.
2. 수요기업 목록에서 검색·기업 자료 조회, 다른 메뉴 이동 시 선택 유지를 확인한다.
3. 현재 기업정보·사업장·재무 단위·수행이력과 제출 당시 개선요구/원본을 구분해 확인한다.
4. 제출 이력·자료 근거·확인된 기업정보를 펼치고 원본 다운로드를 확인한다.
5. F5·재로그인·작은 화면 메뉴를 확인한 후 보완 의견을 공유한다.

후속 자동 분석·추천·조합·매칭·제안서는 준비 중이다. 사용자 인수 전에 Merge/Draft 해제/Slice 2 개발을 진행하지 않는다.

## F. 최종 판정

| 항목 | 판정 |
| --- | --- |
| PR15_SLICE1_UX | PASS |
| PR15_SLICE1_FUNCTIONAL_REGRESSION | PASS |
| PR15_SLICE1_CI | PENDING — Push 후 확인 |
| DONGATECH_DATA_INVENTORY | PASS |
| DONGATECH_OPERATOR_REALDATA_E2E | PARTIAL |
| DONGATECH_DATA_COPY_REQUIRED | NO |
| DATA_ACCESS_POLICY | APPROVED_EXISTING_SCOPE |
| OPERATOR_USER_ACCEPTANCE | PENDING |
| OPERATOR_FULL_WORKFLOW | NOT_TESTED |
| SYSTEM_ACCEPTANCE | NOT_TESTED |
