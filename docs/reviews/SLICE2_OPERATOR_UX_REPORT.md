# Slice 2 운영자 업무 UX와 제출본 검토 이력

2026-10-28. 사용자 「운영자 중심 UX 및 검토 이력 통합 개선」 지시의 제한 범위. 기존 PR #16 / `feat/datco-slice2-improvement-analysis`, 시작 HEAD `9d691f0b0a671f207456eccfec9c841d946f7d45`.

## 업무 흐름

기존 기업 통합 업무 경유·파일별 제외·수동 실행·분석 이력 선택을 기본 동선에서 제거했다. 대시보드/개선요구 목록에서 과제별 최근 **SUBMIT Version**을 선택하면 요약 → Rule 결과 → 명시적 판단으로 진행한다. Draft v2가 있어도 제출 v1 내용·사업장 ordinal·직접 Evidence를 유지한다. 같은 기업의 다른 과제에 판단을 전파하지 않는다.

사이드바는 매번 기업/개선요구 목록으로 진입하며 `screen=workspace`도 기업자료 목록으로 안내한다. 검색·업무 표시 필터·20건 페이지를 제공한다. 정확한 상세는 URL과 뒤로가기로 유지한다. 기업자료 화면은 Version을 강제하지 않는다. 기업 공통 요청은 `request_scope=company`이며 특정 제출본 요청과 구분한다. 기업자료 그룹은 저장된 FINANCE/HISTORY 출처 매핑만 사용한다. 파일명·Parse 시도만으로 분류하지 않으며 BASIC 증빙의 확인 메타데이터가 없으면 미분류다.

## 분석 입력과 실행

새 Manifest의 `input_policy=submitted-review-v1`. 제출본문·직접 첨부·연결 Evidence·현재/직접 Fact·제출 당시 Site가 기본 입력이다. 현재 CompanyInputVersion은 제출 당시 정보라고 표시하지 않는다. 공통자료는 기본 `NOT_SELECTED`, 추가 선택만 허용하며 직접 근거 제외에는 Backend가 3~1000자 사유를 검증한다. `NOT_SELECTED`는 `EXCLUDED`와 다른 상태로 검사 범위에 보존되며 사유/Audit를 생성하지 않는다. 과거 Manifest는 변경하지 않는다.

인증된 운영자의 상세 진입이 보호된 POST `analysis-jobs`의 `mode=ENSURE`를 호출한다. GET/SUBMIT에서는 쓰지 않는다. 기존 Company 잠금과 logical fingerprint로 중복 탭·F5·재로그인 요청을 직렬화한다. 동일 입력의 진행/완료/실패 Job을 재사용한다. 실패는 명시적 retry만 가능하다. 새 Parse 발견과 미선택 공통파일 추가는 중복 자동 Job의 이유가 아니다. 포함된 파일·digest·Fact·CompanyInput·Site·Rule/input policy는 fingerprint에 고정하며 실제 선택 Parse/추출 검증/검사 위치는 기존 Manifest/Inspection에 보존한다. 새 제출본이 있으면 과거 제출본의 신규 자동 분석은 차단하고 기존 이력은 열람 가능하다. 수동 재분석은 기존 경로를 유지한다. Rule R01~R08과 외부 AI 금지는 유지한다.

## 최소 DB 변경 영향

Migration `ff30u0012026` (parent `fe29s0022026`)은 **새 테이블 한 개와 그 전용 함수·Trigger만** 추가한다. 기존 열·CHECK·계보 Trigger·InformationRequest 불변 함수·enum·소비 Provider는 변경하지 않는다. backfill이나 기존 이력 삭제가 없다.

`improvement_submission_reviews`는 Company/Root/SUBMIT Version/nullable Run·Job·Draft/Actor FK, ordinal, decision, note, analysis_limit, JSON basis, request_key/body_hash, created_at을 가진다. decision은 COMPLETED/NEEDS_CHECK/PREPARE_REQUEST. Run 또는 명시적 분석 한계가 필요하며 PREPARE_REQUEST는 초안 FK가 필요하다. Version+ordinal 및 Actor+key가 unique다. 전용 INSERT Trigger가 제출·회사·운영자 membership·Run typed context·Job/Attempt·초안 소유자를 검증한다. UPDATE/DELETE는 기존 불변 함수로 거부한다. 기존 CONFIRM/후보 Review를 재사용하지 않는다.

새 이력은 권한 있는 운영자끼리 공유되며 초안의 소유권은 기존 계약을 따른다. 변경 의견은 다음 ordinal로 추가한다. 대시보드 표시는 Job/Run freshness/명시적 판단/실제 요청·응답 상태에서 계산한다. 신규 제출·새 Run·근거 변경은 재검토 대상으로 표시한다. 기존 제출 검토 완료를 새 Version에 복사하지 않는다. 열람과 분석 성공은 판단 기록을 만들지 않는다.

기존 데이터가 있는 상태의 upgrade는 단일 테이블 추가라 기존 내용을 변환하지 않는다. 테스트는 기존 Company/Request/Audit 행과 불변 함수가 동일함을 확인하고 전체 metadata 열과 비교한다. downgrade는 이력이 있으면 거부하며 이력 없는 합성 Schema에서만 왕복 검증한다. 실사용 DB는 본 작업에서 upgrade하지 않는다. HTTPS 적용에는 별도 승인과 복원 가능한 백업이 필요하다.

## API와 초안

- 기존 POST `/company/improvements/{vid}/analysis-jobs`: `common_file_ids`와 `mode=MANUAL|ENSURE` 추가, 기본은 MANUAL. 기존 수동 클라이언트도 권한/선택 토큰 검사를 받는다. **새 공통자료 기본값은 미선택**이다.
- GET `/company/improvements/{vid}/submission-reviews`: 읽기 전용 `{history, projection}`. 이력에 운영자 이름·시각·정확한 Run/Version 관계를 제공한다.
- POST 같은 경로: `idempotency_key, expected_ordinal, decision, note, run_id?, job_id?, draft_id?, analysis_limit`. Company 잠금·최신 Run/freshness·정확한 Scope·초안 소유권을 재검증한다. 충돌 409, 권한/Scope 403/404, 불충분 근거 422.

보완요청 작성은 후보의 최신 USE_FOR_REQUEST Review를 기존 영속 초안에 연결하고 PREPARE_REQUEST 전체 판단을 추가한다. 후보 EXCLUDE/NEEDS_CHECK는 포함하지 않는다. 편집·F5·재로그인·취소·Native dialog·응답 유실 확인·원자적 생성/발송은 기존 계약을 유지한다. 최종 확인 전 실제 InformationRequest는 생성하지 않는다. 검토 판단과 초안은 별도 append 작업이므로 네트워크 중단 시 초안만 저장될 수 있다. 동일 key 재시도와 영속 초안 목록에서 복구한다. 자동 발송은 없다.

## 구현과 테스트 파일

제품: `company/submission_review.py`, `infrastructure/submission_review_schema.py`, 새 Migration, 기존 analysis orchestration/worker/rules/operator projection/API, `operator-intake.tsx`, `operator-worklists.tsx`, `operator-materials.tsx`, `improvement-analysis.tsx`, 생성 API 타입.

테스트: 새 `test_operator_review.py`, `operator-review.spec.ts`, 기존 Rule/analysis/migration/탐색 E2E, 전체 frozen migration chain·CI 대상 목록. 보안·무결성 테스트를 삭제하지 않는다. 기존 테스트의 변경 근거는 통합 업무 메뉴 제거, 공통자료 명시 선택, 자동 실행, 중복 체크박스 제거, 자료 상세 접기, 사이드바 목록 초기화, 20건 페이지다. 원본 PDF digest·소수 금액·단위·과거 Version·권한·발송 취소·응답 유실·이중 클릭 검증을 유지한다.

## 검증 기록 및 제한

실제 로컬 실행 결과: Rule Unit **21 PASS**, 격리 PostgreSQL **27 PASS** (새 이력·동시 ENSURE·타 운영자 공유·실패 재시도·기존 Slice 2·Migration), 실제 API/Worker 브라우저 집중 **4 PASS**, lint/typecheck/production build 및 API 타입 일치 **PASS**. 최초 집중 실행에서는 테스트가 남긴 미완료 Job 간섭, 초안 화면 중복 React key를 발견했고 각각 테스트 격리와 제품 key를 수정한 뒤 재검증했다. 최종 전체 회귀 근거는 최신 HEAD GitHub CI이며 결과는 완료 보고에 별도 기록한다. 문서나 빌드 성공만으로 업무 인수를 주장하지 않는다.

실제 HTTPS 서비스·실사용 DB·기업자료·계정·원본 PDF는 변경하지 않았다. 운영 인수는 PENDING이며 이번 코드의 HTTPS 배포와 Migration 적용은 별도 승인이다. 목록 페이지 분할은 Frontend에서 수행하며 Backend 검색 인프라는 재설계하지 않았다. 분석은 제한된 Rule 후보이며 범용 AI 의미분석이 아니다.

### 최초 전체 CI에서 확인한 보완

`01afbef`의 전체 CI는 Unit/Frontend/PostgreSQL이 통과하고 E2E는 49 PASS/2 FAIL이었다. 빈 권한 범위의 명시적 안내를 복구하고, 제거된 통합 업무 메뉴에 따라 운영자 메뉴 수만 12→11로 수정했다(관리자 12 유지). 권한 검증 기대값은 유지한다. 역할·Context 집중 실행은 기존 Editor 테스트의 선행 기업 등록이 필요하므로 해당 W1 시나리오 2건도 포함한다. 이 과정에서 기본 대시보드에 Context query를 붙이는 로그인 URL 경쟁을 발견해, 기업·Version 선택이 없는 대시보드 URL은 정규 경로를 유지하도록 수정했다. 정확한 상세 Context와 잘못된 returnTo 차단은 유지한다. 최종 판정은 후속 Commit의 전체 CI와 완료 보고를 따른다.

보완 후 선행 W1 2건을 포함한 역할·Context 집중 E2E **19 PASS**. 이 실행은 전체 E2E 재실행 대신 변경 관련 시나리오만 선택하며, 전체 CI의 테스트 목록·보안 Guard·Skip 조건은 변경하지 않는다.

## 최종 인수 UX 보완 — 2026-10-29

사용자 최종 통합 개발 지시 기준 HEAD는 `41868c38234ccedc77b5b195a5b8a2f4af625cfb`다. 이번 변경은 Frontend와 관련 테스트·문서에 한정한다. Backend/API/Rule R01~R08/`improvement-rules-v2`/DB Schema/`ff30u0012026`/State/Permission/Immutable Trigger는 변경하지 않는다. 현재 HTTPS의 사용자 NEEDS_CHECK 이력·기업·계정·PDF는 접근·수정하지 않으며, 배포는 별도 승인이다.

### 화면과 선택

실제 Run에서 완료/활용 여부·부족정보·충돌·처리 한계를 집계하고 핵심 부족정보를 먼저 표시한다. STRUCTURE, 원문 Evidence, Rule/Parser/검사 범위, Run/후보 Review 이력은 기본 접기다. 처리 한계는 정보 부재와 별도로 표시하며 Rule 결과를 의미론적으로 재해석하거나 예시 기업 문구로 대체하지 않는다. 기존 요약과 반복되는 원문 구조화 결과는 펼쳤을 때만 보인다.

후보 행의 체크박스는 UI 선택만 변경한다. 새 후보는 기본 미선택이고 최신 USE_FOR_REQUEST가 있는 항목만 저장 상태를 반영한다. 선택 해제로 EXCLUDE를 자동 저장하지 않는다. 운영자가 작성한 공통 의견은 새로 저장할 선택 후보에만 적용한다. 기존 최신 Review는 그대로 재사용하고, 개별 질문/의견을 바꾼 경우 새 ordinal로 기록한다. 상세의 요청 활용/제외/추가 확인 기능도 유지한다. 검토 완료 버튼은 보조 강조이며 시스템이 판단을 선택하지 않는다.

### 순차 저장·초안·불확실성

기존 Candidate Review POST를 후보별로 순차 호출한다. 필수 note/expected_review_ordinal/idempotency_key 및 최신 Review/Company/Version/Run Guard는 그대로 Backend가 검사한다. 여러 호출은 원자적이지 않다. 실패 시 일부 저장 가능성을 안내하고 서버 상태를 재조회한다. 재시도는 이미 저장된 최신 Review를 재사용하며, 불확실한 요청은 정확한 기존 키·본문으로 확인한다. 서버 재조회가 실패하면 추가 POST를 보내지 않는다. 처리 중 다른 운영자가 최신 Review를 바꾸면 확인한 Review ID와 다름을 감지해 초안 진행을 중단한다.

동일 Run·정확한 선택 Review ID 집합·미발송·현재 유효성에 맞는 소유 초안이 있으면 편집된 내용과 Version을 보존해 이어 쓴다. 없을 때만 기존 Draft API를 호출한다. 초안 생성 응답 유실도 같은 키로 재조회/재시도한다. 요청 이유·선택 항목·기한과 정확한 제출 Version을 확인할 수 있으며 최종 요청문은 운영자가 편집한다. Native dialog·취소/포커스/Escape·중복 클릭·원자적 Send 계약은 유지한다. 분석 결과만으로 실제 InformationRequest를 생성·발송하지 않는다.

### 저장 후 복귀

COMPLETED/NEEDS_CHECK는 저장 성공과 서버 상태 조회 이후 원래 대시보드/개선요구 목록으로 복귀한다. 직접 상세 URL 또는 유효한 출처가 없으면 개선요구 목록으로 간다. 선택한 기업·Version·로그인 Actor와 함께 허용된 두 목록 경로 및 검색/필터/페이지/스크롤만 URL에 보존한다. 임의 외부 return URL이나 다른 Actor의 Context는 사용하지 않는다. 기존 로그인 returnTo 계약을 바꾸지 않아 F5/재로그인에서도 정확한 Context를 유지한다. 목록은 페이지 범위를 현재 결과 수에 맞춰 제한한다.

복귀 안내는 실제 기업·제출 ordinal·서버의 현재 업무 표시로 생성한다. 상태 필터에서 해당 행이 사라져도 성공 안내를 유지한다. 409/권한/네트워크 오류는 자동 이동하지 않는다. 저장됐지만 응답이 유실된 경우 해당 Actor·Version·요청 키의 이력을 조회하고 명시적인 확인 후 복귀를 제공한다. 발송은 기존 Delivery 성공을 서버에서 확인했을 때만 자동 복귀한다. 발송/조회 결과 불확실 시 새 발송을 막고 상태 확인을 요구한다. 수동 요청은 접힌 보조 기능이며 기존 기업 응답·운영자 재검토 경로는 유지한다.

### 검증 범위

`operator-review-unit.mjs`는 확인된 POST의 후속 GET 실패, 응답 유실/명시적 재조회, 409, 동일 키·본문 유지, 재조회 실패 시 쓰기 차단, Actor가 다른 복귀 출처와 선택 Review 재사용을 검증한다. 실제 API/Worker/격리 PostgreSQL E2E는 선택 후보만 저장, 중간 실패·재시도, 개별 질문, 영속 초안/F5, 발송 결과 불확실/확인 후 복귀, 필터에서 사라지는 행의 성공 안내와 페이지/F5/재로그인, 미지원 직접 자료를 포함한다. 기존 테스트는 접기·자동 복귀·보조 수동 요청 경로 기대값만 변경하며 보안/무결성 검증을 유지한다. 실행 결과는 완료 보고와 최신 HEAD CI로 별도 확인한다. 실제 기업 상세 자동 분석·검토 저장·실사용 발송 및 HTTPS 업데이트는 수행하지 않는다.
### 최종 UX 집중 검증 실행 결과

- UI 흐름 Unit: 6 PASS. 요청 키·정확한 재시도 본문·응답 유실 조회·409·Actor별 복귀 Context를 검증했다.
- 격리 PostgreSQL Slice 2: 27 PASS. 실제 검수 DB를 사용하지 않았으며 소유한 임시 DB·Role을 정리했다.
- 신규 Playwright 인수 시나리오: 최종 집중 실행 4 PASS. 부분 Review 저장 후 복구, 영속 초안 수정·F5, 최종 발송 취소·발송 후 조회 실패·Delivery 재확인, 판단 409·응답 유실, 검색·필터·6페이지·재로그인 복귀, 직접 근거 미처리 표시를 검증했다.
- 직전 Slice 1·2 집중 실행에서 기존 회귀 4개는 모두 통과했다. 당시 신규 테스트의 오류 주입이 저장 전 GET에 소진된 실패 1건은 POST 전용 주입으로 수정한 뒤 위 신규 4개 실행으로 확인했다. 초기 합성자료/선택자 기대값 오류와 로그인 완료 대기 누락도 바로잡았다.
- 재로그인 직후 초기 조회가 끝나기 전 판단 저장을 누를 수 있는 실제 UI 경합을 발견했다. 입력·이력 로딩 Guard와 저장 전 정확한 Run·Review ordinal 재확인을 추가해 해결했다. 서버 Guard는 완화하지 않았다.
- 전체 회귀의 최종 판정은 해당 Commit의 GitHub CI 결과를 따른다. HTTPS 배포 및 실제 데이터 인수는 이번 실행에 포함하지 않았다.
- Frontend ESLint·TypeScript·고유 출력 디렉터리의 production build PASS. 생성된 Next 타입 참조는 원복했고 임시 실행파일은 Commit 대상에서 제외했다.
