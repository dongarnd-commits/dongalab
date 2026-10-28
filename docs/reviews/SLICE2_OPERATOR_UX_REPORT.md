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
