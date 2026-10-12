# DATCO 정부지원사업 운영체계 - Test / Acceptance Specification

## 1. 목적 / 지위 / 현재 결과

Standalone Phase-1 구현 후 무엇을 어떻게 검증해야 완료로 인정할지 정의한다. 09 Checkpoint → Preconditions → Execution → Expected Result/Negative Assertion → Required Evidence → Pass/Fail로 연결한다.

**TEST SPECIFICATION DEFINED ≠ TEST EXECUTED ≠ TEST PASSED ≠ SYSTEM ACCEPTED.** 이번 문서의 모든 Test 결과는 **NOT_RUN**, 실제 SYSTEM ACCEPTANCE는 **NOT_TESTED**다. Test/Browser/외부 API/AI/OCR 실행, Test Code/Fixture/DB/UI/API 구현은 이번 작업에 포함하지 않는다. 문서상 검토는 실행 Test가 아니다.

기준은 [AGENTS](../AGENTS.md) → [00 Baseline](00_PROJECT_BASELINE.md) → [01 Architecture](01_SYSTEM_ARCHITECTURE.md) → [02 E2E](02_E2E_SYSTEM_FLOW.md) → [03 Data](03_DATA_MODEL.md) → [04 State/Action](04_STATE_ACTION_MODEL.md) → [05 Permission](05_PERMISSION_UI_MATRIX.md) → [06 Collector](06_BIZINFO_COLLECTOR.md) → [07 Intelligence](07_INTELLIGENCE_DESIGN.md) → [08 Screen](08_SCREEN_ACTION_SPEC.md) → [09 Demo](09_DEMO_SCENARIO.md) → 이 문서다. 실제 API 사실은 기존 [1차](../tools/bizinfo-probe/ANALYSIS.md)/[2차 Probe](../tools/bizinfo-probe/PHASE2_ANALYSIS.md)를 참고하며 Production 구현 통과 근거로 대체하지 않는다.

새로운 Entity/State/Action/Guard/Role/Permission/Screen/Business Policy를 추가하지 않는다. 승인된 Test 기술은 `11_DECISION_LOG.md`의 Decision-001을 따른다: pytest/FastAPI API Test/실제 PostgreSQL Integration/Playwright, Frontend Component는 Vitest/React Testing Library를 첫 Slice 필요범위에 적용한다. CI/Cloud/API Route/Assertion Code/Fixture 파일/Artifact 위치/배포 Pipeline은 미확정이다. 화면 표시만 그럴듯하고 Backend 저장/Guard가 틀리면 FAIL이다.

## 2. 결과 / Gate / Priority / Evidence

PASS는 Expected Result·Negative Assertion·필수 Evidence가 모두 확인된 경우, FAIL은 실행됐지만 기대/불변조건 위반, BLOCKED는 미구현 Prerequisite/외부 Dependency로 정상 수행 불가, NOT_RUN은 미실행이다. BLOCKED_EXTERNAL은 BLOCKED의 원인 의미이며 새 결과 enum이 아니다. Evidence가 부족하면 PASS 판정을 보류하고 원인을 기록한다. 이는 Test 관리 의미이지 Domain State가 아니다.

| Gate | 목적 |
| --- | --- |
| GATE-A | Core Environment / Persistence |
| GATE-B | Main Business E2E |
| GATE-C | Permission / Security |
| GATE-D | Version / Evidence / History |
| GATE-E | Failure / Recovery / External Dependency |
| GATE-F | Demo Readiness |

Priority는 MANDATORY/OPTIONAL만 사용한다. 아래 Case는 AC-EXT-01과 AC-UI-02를 제외하고 MANDATORY다. 해당 Case의 CONDITIONAL은 **실행 환경 조건**이며 별도 Priority가 아니다. 외부 기능을 Phase-1 필수범위에서 몰래 제외하거나 BLOCKED를 PASS로 바꾸지 않는다.

표의 Gate A~F는 위 Gate 약어다. O=DATCO_OPERATOR, E=A의 COMPANY_EDITOR, P=A의 지정 COMPANY_APPROVER, A=DATCO_ADMIN, S=승인된 System/Worker다. 모든 Precondition에는 격리 Dataset/인증·Scope/정확한 시작 State·Version이 적용된다. 여러 입력 변형을 명시한 행은 각 변형을 실행·기록해야 PASS다.

Evidence 약어는 다음 최소 확인을 뜻하며 Screenshot만으로 Backend 결과를 증명하지 않는다.

| 약어 | 필수 확인 의미 |
| --- | --- |
| D | 저장 Object/State/정확한 Version·Actor·Company/Case ID와 Backend 재조회 결과 |
| R | Action 후 Browser Refresh 또는 재로그인/새 조회 Context에서 같은 저장결과 |
| F | 실제 FileAsset/StorageReference/Source Location/검증·다운로드 및 관련 Review |
| J | Job/Attempt/Page/입력·결과·오류·처리범위/Mode |
| X | UI 접근/Action 표시와 직접 Backend 요청의 DENY·보호 데이터/변경 없음 |
| H | Audit/History/Lineage의 Actor/Action/Target Object·Version/Time/필요 이유 |
| L | Secret/PII를 노출하지 않는 Log·응답·Frontend/공유자료 확인 |

실제 실행기록에는 Test ID/Build·환경/Fixture 식별·Mode/실행자·시각/변형별 결과/안전한 Evidence 참조/차단사유를 남긴다. 자동 Test Report와 사람의 의미검토도 Evidence로 연결한다. SQL 직접 조작으로 정상 Flow를 만든 뒤 PASS 처리하지 않는다. SQL 조회도 기본 Proof가 아닌 보조이며 Browser+Backend 저장결과를 우선한다. 모든 조회 Click을 Audit 의무로 추가하지 않고 01/03/04의 중요 Action/다운로드 요구를 따른다.

## 3. 환경 / Fixture / 외부 Dependency

09의 FIX-* ID를 재사용하며 실제 PK는 고정하지 않는다. FIX-USER-OPERATOR/EDITOR-A/APPROVER-A, FIX-COMPANY-A/B, FIX-NOTICE-01/CONTENT-01, FIX-COMPANY-DOC-01, FIX-CAPABILITY-01, FIX-MISSING-INPUT-01, FIX-PROPOSAL-INPUT-01, FIX-APPLICATION-INPUT-01, FIX-EVIDENCE-RECEIPT-01/RESULT-01과 필요한 기존 Fixture를 사용한다. Company B의 Request/Approval/Case가 필요한 Negative 준비도 정상 Domain Action으로 생성하고 사전완료 Decision 직접 삽입으로 위장하지 않는다.

재현 기준은 Sanitized Snapshot/검증된 Fixture + 07의 공통 Input/Run/Structured Validation/Human Review 경로다. Fixture Adapter로 분석 후보를 재현할 수 있지만 Confirmed/Approval/Ready 직접 Seed는 금지한다. 의미있는 Source/증빙 대응관계와 Demo 표시를 사전 검증한다. Receipt/공식결과 Fixture도 Company/Notice/Submission/Snapshot/회차·공식근거 Guard를 만족해야 한다. 없으면 관련 Test BLOCKED다.

Live는 접근 가능한 환경에서 제한적 Integration으로 실제 인증/jsonArray/Page/pblancId/Raw·Normalize/Mapping·Secret 미노출을 검증한다. 현재 1423/712/713 같은 Probe 값은 Test 상수가 아니다. 외부 장애면 AC-COL-10을 BLOCKED로 기록하고 Live PASS라고 하지 않는다. Snapshot Demo는 별도로 가능하지만 필수 Live 능력을 검증하지 못한 구현을 완료 수용하지 않는다. 관련 Build/설정의 실제 Live PASS Evidence가 이미 유효하면 당일 장애와 구분해 보고한다.

Provider Integration과 Domain Acceptance도 별도다. 특정 AI 제품은 필수가 아니며 실제 외부 Provider를 채택하면 계약/Private Data 범위 확인 후 AC-EXT-01을 수행한다. Fixture Domain Test를 외부 Provider 정확도/연동 PASS로 오인하지 않는다. 실패 주입은 격리 Adapter/Fixture로 수행하고 고의 Key 변조·과호출·운영자료 훼손은 하지 않는다.

## 4. GATE-A — 환경 / AG-01 / Persistence

| Test ID | Gate | Scenario / Purpose | Actor | Preconditions | Execution | Expected Result | Negative Assertion | Evidence | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AC-ENV-01 | A | 시작/영속 저장 연결 | O | 구현 Build/격리 DB | 시작·저장조회 | 정상 접근/실제 저장 가능 | 메모리 Mock만으로 성공 금지 | D/L | NOT_RUN |
| AC-ENV-02 | A | File Storage | E/O | A 입력파일 | 허용 Upload 후 재조회/다운로드 | 저장 Content/참조 일치 | URL만 확보성공 아님 | D/F/R | NOT_RUN |
| AC-ENV-03 | A/C | Role Context | A/O/E/P | 준비 Account/Membership | 각각 로그인·자기 Scope 조회 | 신뢰된 Role/Company Context | Browser Role 값 조작 무효 | D/X | NOT_RUN |
| AC-ENV-04 | A/D | 핵심 Refresh | O/E/P | 아래 8개 중요 지점 생성 | 각 Action 후 Refresh·재로그인 | 같은 State/Version/Decision | 화면 메모리만 유지 FAIL | D/R/F/H | NOT_RUN |
| AC-ENV-05 | A/F | Dataset 격리/Re-run | O, 준비 담당 | Demo 시작 Dataset | 승인된 격리 준비/Reset 후 재실행 | 09 Precondition 복원/이전실행 구분 | Production 삭제/Decision 위조 없음 | D/H/L | NOT_RUN |
| AC-ENV-06 | A/C | Secret 격리 | O/S | 가짜 Secret/설정 Fixture | Frontend·오류·Log/Raw 관찰 | Secret 미노출 | 실제 Key 출력·공유 금지 | L/J | NOT_RUN |
| AC-INPUT-01 | A/B/C/D | AG-01 저장/Upload | E/O/A | 해당 Role 허용 Draft·파일 | Company/Site/Contact, Intake, Improvement/Response/Application Draft, Proposal/Capability Draft를 해당 계약으로 저장·재조회; Scope/Version/입력·Upload 실패도 시도 | 저장/Validation/Lock/File Scope/Audit 범위가 계약과 일치 | Save≠Submit/Confirm, 타기업·Lock 본 덮어쓰기 금지 | D/R/F/X/H | NOT_RUN |

AC-INPUT-01은 명명된 새 04 Action이 아니다. 구현 전 Role/Scope/expected Version/Validation/Persistence/필요 Audit/Upload 계약을 명시해야 한다. AG-01 미구현이면 관련 Main E2E는 BLOCKED이고 전체 구현 수용 불가다. AG-02 사용자관리는 Main에서 Seed된 정상 Membership로 검증한다. 사용자관리 UI/API를 Phase-1에 포함하면 기존 관리책임의 세부 계약/Acceptance를 추가한 뒤 검증하며 새 관리 Action을 여기서 확정하지 않는다.

AC-ENV-04의 8개 지점은 Confirmed Requirement, Submitted Improvement, ApprovalDecision, ProceedDecision, SupportCase, READY_TO_SUBMIT Snapshot, Submission Evidence Review, Official Result다. File/Version/Actor 관계도 유지되어야 한다.

## 5. Collector / Notice Intelligence

| Test ID | Gate | Scenario / Purpose | Actor | Preconditions | Execution | Expected Result | Negative Assertion | Evidence | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AC-COL-01 | B | Snapshot 1 Page | O/S | FIX-NOTICE-01 | SNAPSHOT REQUEST_COLLECTION | Raw/Normalize/Notice 저장 | 완성 Notice 직접 Seed 금지 | D/J | NOT_RUN |
| AC-COL-02 | B/E | Page 종료 | O/S | 여러 Page/short/empty 및 total 변동 Fixture | 순회·종료/상한 관찰 | 빈 배열 정상, 건수·ID/불일치 범위 기록 | totCnt만으로 완전수집 선언 금지 | J/D | NOT_RUN |
| AC-COL-03 | B/D | Source+ID 중복 | S | 같은 Source+pblancId 동시 입력 | 중복/동시 import | 하나 Mapping/Notice | 제목 병합·중복 Root 금지 | D/J | NOT_RUN |
| AC-COL-04 | D | 동일 내용 재수집 | O/S | 저장 Notice | 조회수/total/수정신호만 변화 재수집 | 같은 업무 Version/새 수집이력 | 메타변화로 중복 Version 금지 | D/J/H | NOT_RUN |
| AC-COL-05 | B/D | 의미변경 Version | O/S | 기존/변경 내용 Fixture | 재수집·의미비교 | 새 Version/이전근거 보존/Impact 연결 | updtPnttm만 Version 취급 금지 | D/J/H | NOT_RUN |
| AC-COL-06 | B/D | 상세·첨부 확보 | S | API 제공 참조/Content | 관계·형식·Content 확보 검증 | SourceReference/FileAsset/상태 구분 | URL 임의조합·print 역할 확정 금지 | F/J/D | NOT_RUN |
| AC-COL-07 | E | 일부 Page/File 실패 | O/S | 성공+실패 입력 | 통제 실패 후 결과 확인 | PARTIAL/성공 Notice 유지/실패범위 | 실패 누락 후 전체 성공 금지 | J/D | NOT_RUN |
| AC-COL-08 | C | 수집 Secret Log | S | 가짜 인증URL/반사오류 Fixture | 요청·오류·Raw/Log 관찰 | crtfcKey 값 제거/차단 | 인증URL·Key Audit 복제 금지 | L/J/H | NOT_RUN |
| AC-COL-09 | B/E | Live/Snapshot 공통 Normalize | S | 동일 Raw의 두 Mode | 각각 정상 경로 처리 | 같은 업무내용/Mapping 정책, Mode 구분 | Snapshot 전용 Domain 우회 금지 | D/J | NOT_RUN |
| AC-COL-10 | E | 실제 Live Integration | O/S | 접근 가능한 Bizinfo/Backend Secret | 제한 LIVE REQUEST_COLLECTION | 실제 인증/배열/Page/ID/Raw/Notice 저장 | 외부 BLOCKED를 Live PASS로 기록 금지 | J/D/L | NOT_RUN |
| AC-NOTICE-01 | B | 후보 생성 | O/S | Notice/File/07 Adapter | REQUEST_NOTICE_REVIEW | 구조화 Candidate/Run | Confirmed 자동생성 없음 | D/J | NOT_RUN |
| AC-NOTICE-02 | B/D | 입력 Version | S | 정확한 NoticeVersion | Run/InputReference 재조회 | 사용 입력 고정 | Root 최신 포인터만 참조 금지 | D/J | NOT_RUN |
| AC-NOTICE-03 | D | Evidence/Location | O/S | 실제 HTML/PDF 근거 | 유효·허위 위치 출력 검증/원문 확인 | 유효 후보만 검토, Source 주장 일치 | 존재없는 Page/타자료 참조 금지 | D/F | NOT_RUN |
| AC-NOTICE-04 | B/D | 후보≠확정 | O/S | 높은 Confidence 후보 | 생성 후 상태 확인 | 미확정 Review 대기 | Confidence 자동 Confirm 금지 | D/J | NOT_RUN |
| AC-NOTICE-05 | B/D | Human Requirement | O | 유효 Candidate/공식근거 | CONFIRM_NOTICE_REQUIREMENT | Review/RequirementVersion/Actor 저장 | 부족근거·다른 Version 확인 금지 | D/F/H | NOT_RUN |
| AC-NOTICE-06 | B/D | API/PDF Conflict | O/S | 상충 기간/조건 | 분석·Review 조회 | 양쪽 근거/Conflict 보존 | 자동 덮어쓰기/날짜 상상 금지 | D/F | NOT_RUN |
| AC-NOTICE-07 | B/E | Partial Source | O/S | Metadata/HTML만 유효 | 분석·확인 시도 | 사용범위/누락 표시, 부분 Review 범위 | 전체요건 완전확정 표시 금지 | D/F/J | NOT_RUN |
| AC-NOTICE-08 | A/D | Requirement Refresh | O | 확인 완료 | Refresh/재조회 | 같은 Review/Version/근거 | 재분석 없이 다른 입력으로 재해석 금지 | D/R/F/H | NOT_RUN |

## 6. Company / Fact / Improvement / Matching / Request

| Test ID | Gate | Scenario / Purpose | Actor | Preconditions | Execution | Expected Result | Negative Assertion | Evidence | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AC-COMPANY-01 | B/C | 자기 기업 입력 | E | A Membership/AG-01 | A 조회·허용 입력 저장 | 자기 범위 저장/재조회 | DATCO 검토권한 자동부여 없음 | D/R/X | NOT_RUN |
| AC-COMPANY-02 | C | 타기업 Company | E/P | B Fixture | B 조회 직접 요청 | DENY/정보 미노출 | 이름·State 누설 없음 | X | NOT_RUN |
| AC-FACT-01 | B | 문서→후보 | E/S | FIX-COMPANY-DOC-01 | Upload/추출 경로 | FactCandidate/Source 연결 | File 확보≠추출성공 | D/F/J | NOT_RUN |
| AC-FACT-02 | B/D | 자동수정 금지 | S | 기존 Fact+새 후보 | 후보 생성 | 기존 Version 유지 | Master/Confirmed 자동 Update 없음 | D/H | NOT_RUN |
| AC-FACT-03 | B/D | 새값 확인 | O | 기간·단위/근거 충족 | CONFIRM_NEW_FACT_VALUE | FactReview/새 Version | Review 없이 새 확인값 금지 | D/F/H | NOT_RUN |
| AC-FACT-04 | D | 동일값 연결 | O | 같은 기간·단위·값 | CONFIRM_EXISTING_FACT_VALUE | 기존 Version 연결/Review | 동일값 중복확정 Version 금지 | D/H | NOT_RUN |
| AC-FACT-05 | D | Conflict 보존 | O | 기존/상이 후보 | RECORD_FACT_CONFLICT/Review | 양쪽 근거/충돌 보존 | 자동 덮어쓰기 금지 | D/F/H | NOT_RUN |
| AC-FACT-06 | B/D | 재무 기간/단위 | O/S | 다중 연도·단위 입력 | 추출·비교·Review | 값+기간+단위 유지 | 맥락 다른 값 합산/동일충돌 추정 금지 | D/F | NOT_RUN |
| AC-FACT-07 | C/D | Fact 근거권한 | E/O | A/B File 근거 | 허용/비허용 Evidence 조회 | 허용근거만 접근 | Fact 화면 통한 B File 우회 금지 | F/X | NOT_RUN |
| AC-IMP-01 | A/B | 과제 Draft | E | 작성자료/AG-01 | Draft 저장·재조회 | Draft 영속 | 저장만으로 SUBMITTED 아님 | D/R | NOT_RUN |
| AC-IMP-02 | B | 과제 제출 | E | 완전 Draft | SUBMIT_IMPROVEMENT | 제출 Version Lock/분석요청 | 제출만으로 CONFIRMED 아님 | D/J/H | NOT_RUN |
| AC-IMP-03 | A/D | Submitted Refresh | E | 제출 완료 | Refresh | 같은 제출본/첨부 | Draft로 임의 복귀 없음 | D/R/F | NOT_RUN |
| AC-IMP-04 | B | 분석 후보 | S/O | 제출본/Fact/File | 분석·REGISTER_IMPROVEMENT_CANDIDATE 결과 | 근거있는 후보/Review 대기 | 기업요구를 최종 서비스로 자동확정 금지 | D/F/J | NOT_RUN |
| AC-IMP-05 | B/D | 과제 확인 | O | Review/현재성·정보충족 | CONFIRM_IMPROVEMENT | 확인 Version/Review | Missing/근거 Guard 우회 금지 | D/F/H | NOT_RUN |
| AC-IMP-06 | C | 입력/확인 분리 | E/O | 제출 후보 | E 확인 시도/O 정상 확인 | E DENY/O 저장 | 기업 Actor의 DATCO Confirm 금지 | D/X | NOT_RUN |
| AC-IMP-07 | D | 보완 Version | O/E | 이전 확인/제출본 | REQUEST_IMPROVEMENT_REVISION, REVISE_IMPROVEMENT | 새 작업본/과거보존 | 기존 확정내용 덮어쓰기 없음 | D/H | NOT_RUN |
| AC-CAP-01 | B/C/D | ADMIN Catalog | A/E/P | 관리 Draft/근거 | A PUBLISH_CAPABILITY_VERSION, E/P 관리 시도 | A 불변 발행/기업 DENY | 과제 Assessment로 Catalog 변경 금지 | D/X/H | NOT_RUN |
| AC-CAP-02 | B/D | 과제 Assessment | O | 개선/Catalog 정확한 Version | REVIEW_CAPABILITY_ASSESSMENT | 검토 Record/적합 의미·근거 | FIT=승인 또는 Catalog 수정 아님 | D/F/H | NOT_RUN |
| AC-MATCH-01 | B/D | 입력 Snapshot | O/S | 확인 Fact/과제/검토 Catalog/요건 | REQUEST_MATCH_ANALYSIS | 정확한 MatchInputSnapshot | 미확인 현재 Root 조합만 사용 금지 | D/J | NOT_RUN |
| AC-MATCH-02 | B | 적합 축 분리 | O/S | 검증 Fixture | 결과 조회 | Eligibility/Task/Service Fit 구분 | 단일 유사도만 자격판정 금지 | D/F | NOT_RUN |
| AC-MATCH-03 | B | Missing 표시 | O/S | 부족근거 1개 | 분석 | Missing/근거·후속요청 후보 | 값 상상/자동 메시지 발송 금지 | D/J | NOT_RUN |
| AC-MATCH-04 | D | Opposing Evidence | O/S | 적합+반대근거 | 분석·Review 조회 | 반대근거 함께 보존 | 좋은 근거만 남기는 결과 금지 | D/F | NOT_RUN |
| AC-MATCH-05 | B | Unknown≠Fail | O/S | 필수 Fact 부재 | 분석 | NEED_MORE_INFO/Unknown 의미 | False/0/자동부적합 금지 | D/F | NOT_RUN |
| AC-MATCH-06 | B/D | Hard Conflict | O/S | 명시위반+높은 Semantic Fit | 분석·Review | Hard 제약/충돌 유지 | 유사도 점수로 상쇄 금지 | D/F | NOT_RUN |
| AC-MATCH-07 | B/D | FIT≠PROPOSABLE | O/S | FIT 후보 | Review 전 상태조회 | 아직 업무판정 없음 | 자동 제안·Proceed Gate 통과 금지 | D | NOT_RUN |
| AC-MATCH-08 | B/D | Human Review | O | 현재 근거/Blocking 해소 | REVIEW_MATCH | PROPOSABLE/검토자·입력 저장 | Fit 후보만으로 대체 금지 | D/F/H | NOT_RUN |
| AC-MATCH-09 | D | Stale Match | O | 입력 변경/이전 Snapshot | 기존 결과 사용 시도 | 현재성 Guard 차단 | 과거 Review 자동전용 없음 | D/X/H | NOT_RUN |
| AC-REQ-01 | B | 정보요청 발송 | O | A 대상/항목·이유·기한 | SEND_INFORMATION_REQUEST | WAITING_RESPONSE/발송본 고정 | Draft만으로 발송 표시 금지 | D/H | NOT_RUN |
| AC-REQ-02 | C | Request 공개범위 | E/P | A/B Request 정상 생성 | 자기/타기업 조회 | 허용 A 공개내용/B DENY | 내부 Review/타기업 존재 누설 없음 | D/X | NOT_RUN |
| AC-REQ-03 | B | 응답 Draft/Submit | E | 자기 Request/AG-01 | 저장 후 SUBMIT_INFORMATION_RESPONSE | 불변 ResponseVersion/REVIEW_REQUIRED | Draft 저장만 제출 아님 | D/R/F | NOT_RUN |
| AC-REQ-04 | B/D | Submitted≠Verified | E/O | 제출 완료 | 검토 전 조회 | 미검증 상태 | 자동 Fact Confirm/Verified 없음 | D | NOT_RUN |
| AC-REQ-05 | B/D | 응답검증 | O | 항목/공식근거 충족 | VERIFY_INFORMATION_RESPONSE | Review/VERIFIED | 기업이 검토결과 변경 금지 | D/F/H | NOT_RUN |
| AC-REQ-06 | B/D | 원 Fact 별도 확인 | O | 응답 근거/Fact 후보 | 필요한 FactReview Action | Fact 결과 명시 연결 | Verified 응답만으로 Master 덮어쓰기 금지 | D/F/H | NOT_RUN |
| AC-REQ-07 | B/D | Rematch | O/S | 새 확인 Fact | REQUEST_MATCH_ANALYSIS/REVIEW_MATCH | 새 현재 입력/검토 | 오래된 분석 현재결과 표시 금지 | D/J/H | NOT_RUN |
| AC-REQ-08 | D | 이전 Snapshot | O | Rematch 완료 | 과거 조회 | 예전 Snapshot/Review 보존 | 새 결과로 역사 삭제 금지 | D/H | NOT_RUN |

## 7. Proposal / Approval / Proceed / Case

| Test ID | Gate | Scenario / Purpose | Actor | Preconditions | Execution | Expected Result | Negative Assertion | Evidence | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AC-PROP-01 | B/D | 제안 생성 Gate | O | PROPOSABLE/미충족 변형 | CREATE_PROPOSAL_VERSION | 유효조건 v1 생성/미충족 차단 | FIT만으로 작성 Gate 통과 금지 | D/X/H | NOT_RUN |
| AC-PROP-02 | B/D | 승인요청 Lock | O | v1/지정요건 | REQUEST_APPROVAL | 정확한 v1 고정/OPEN | 내부 Draft 기업 자동공개 없음 | D/H/X | NOT_RUN |
| AC-APPROVAL-01 | B/C/D | 지정 승인자 | P | 자기 지정/미지정 요청 | APPROVE_PROPOSAL 각각 시도 | 지정 정확한 대상만 승인 | Role만으로 모든 요청 승인 금지 | D/X/H | NOT_RUN |
| AC-APPROVAL-02 | C | EDITOR 승인 금지 | E | A 요청 | 직접 APPROVE_PROPOSAL | DENY/변경없음 | 버튼 숨김만으로 검사 완료 금지 | X/D | NOT_RUN |
| AC-APPROVAL-03 | C | DATCO 대행 금지 | O/A | A 기업요청 | 기업 Approval 직접 시도 | 두 Role 모두 DENY | ADMIN 자동기업권한 없음 | X/D | NOT_RUN |
| AC-APPROVAL-04 | C | 타기업 승인 | P | B 요청 | B Decision 시도 | DENY/정보 미노출 | Company ID 조작 승인 금지 | X/D | NOT_RUN |
| AC-APPROVAL-05 | B/D | terminal Decision | P | OPEN 요청 | 승인 후 다른 Outcome 재시도 | CLOSED/하나 terminal Decision, 다른의미 차단 | CLOSED 결정 덮어쓰기 금지 | D/H/X | NOT_RUN |
| AC-APPROVAL-06 | A/D | 승인 Refresh | P/O | 정상 Decision | Refresh/재로그인 | Actor/Request/Version/Decision 유지 | 화면표시만 승인 아님 | D/R/H | NOT_RUN |
| AC-APPROVAL-07 | D | v2 역사보존 | O/P | v1 승인 | 중요변경 CREATE_PROPOSAL_VERSION | v2/이전 v1 Decision 보존 | 과거 승인 삭제 금지 | D/H | NOT_RUN |
| AC-APPROVAL-08 | D | v2 자동승인 없음 | O/P | v2 생성 | 승인/재승인 표시 조회 | v2 미승인/새 Request 필요 | v1 승인 전용 금지 | D/X | NOT_RUN |
| AC-APPROVAL-09 | D | v1로 v2 Proceed 금지 | O | v2 미승인 | CONFIRM_PROCEED 시도 | 차단/재승인 안내 | 오래 열린 v1 요청으로 우회 금지 | X/D/H | NOT_RUN |
| AC-PROCEED-01 | B/D | 추진 Negative | O | Match/Approval/정보·Impact 미충족 변형 | CONFIRM_PROCEED | 각 Gate 차단/보완 위치 | 승인만으로 자동추진 없음 | X/D | NOT_RUN |
| AC-PROCEED-02 | B/D | 추진 Positive | O | 정확한 현재 검토·승인조합 | CONFIRM_PROCEED | 불변 ProceedDecision | UI 상태 직접 Update 금지 | D/H | NOT_RUN |
| AC-PROCEED-03 | D | 별도 결정 | O/P | 승인·추진 완료 | 두 Record/Actor 조회 | Approval/Proceed 독립 연결 | 같은 Record로 혼동 금지 | D/H | NOT_RUN |
| AC-CASE-01 | B/D | Proceed 없는 Case | O | 유효 Proceed 없음 | CREATE_SUPPORT_CASE | 차단/Case 없음 | Match 후보로 Case 생성 금지 | X/D | NOT_RUN |
| AC-CASE-02 | B | Case 생성 | O | 유효 Proceed | CREATE_SUPPORT_CASE | APPLICATION_PREP/입력·담당 연결 | 입력 Company 불일치 금지 | D/H | NOT_RUN |
| AC-CASE-03 | D | Case 반복 | O | 생성한 Proceed | 같은 요청/같은 Proceed 재시도 | 기존 Case/최대 1개 | 중복 Case 금지, 다른 유효 Proceed의 정당한 복수건은 허용 | D/H | NOT_RUN |
| AC-CASE-04 | A/D | Case Refresh | O/E/P | Case 완료 | Refresh/공개 Progress 조회 | 같은 Case/단계/참조 | 집계 화면의 별도 상태 truth 없음 | D/R | NOT_RUN |
| AC-CASE-05 | C | B Case 거부 | E/P | B Case 정상 생성 | Direct URL/Backend 조회 | DENY | Company Scope 없이 Case ID 신뢰 금지 | X | NOT_RUN |

## 8. Application / Package / Submission / Result / Task

| Test ID | Gate | Scenario / Purpose | Actor | Preconditions | Execution | Expected Result | Negative Assertion | Evidence | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AC-APP-01 | B/D | Template 대상 | O | Requirement/Notice/Case | CONFIRM_APPLICATION_TEMPLATE/CREATE_APPLICATION_VERSION | 정확한 Definition/입력관계 | 무관 Template 사용 금지 | D/F/H | NOT_RUN |
| AC-APP-02 | B | Auto-fill 후보 | O | Fact Source 매핑 | 후보 조회 | Source/Version·미확인 표시 | 자동 Confirmed 없음 | D/F | NOT_RUN |
| AC-APP-03 | B/C | 기업 입력 분리 | E/O | 허용 항목/AG-01 | E 저장/O 검토전 조회 | 입력 출처·검토상태 별개 | E 입력만 DATCO Confirm 아님 | D/X | NOT_RUN |
| AC-APP-04 | B/D | 값 확인 | O | 후보/Template/Evidence | CONFIRM_APPLICATION_VALUE | ValueReview/확인값 저장 | 다른 Fact/Version 참조 금지 | D/F/H | NOT_RUN |
| AC-APP-05 | B/D | 필수값 누락 | O | 부족 Application | CONFIRM_APPLICATION | 차단/부족내용 | 전체 Confirm 우회 금지 | X/D | NOT_RUN |
| AC-APP-06 | B/D | 전체 확인 | O | Review/필수 값·계획·문서 완전 | REQUEST_APPLICATION_REVIEW/CONFIRM_APPLICATION | CONFIRMED/Version Lock | 후보 미확인 채 전체성공 금지 | D/F/H | NOT_RUN |
| AC-APP-07 | D | 수정본 역사 | O | 확인/검토 대상 | REVISE_APPLICATION | 새 본/이전 Version 보존 | 잠긴 내용 직접 변경 금지 | D/H | NOT_RUN |
| AC-APP-08 | D | Stale 신청 | O | Template/Application 변경 | 이전 대상 Confirm 시도 | Version Guard 차단/최신 안내 | 미저장입력 자동 덮어쓰기 금지 | X/D | NOT_RUN |
| AC-PKG-01 | B/D | 필수자료 Ready 차단 | O | 필수/조건부 자료 부족 | MARK_PACKAGE_READY | 차단/Checklist 사유 | 직접 READY_TO_SUBMIT 금지 | X/D | NOT_RUN |
| AC-PKG-02 | B | 기업확인 요청 | O | 검토된 고정 Application/자료 | REQUEST_COMPANY_CONFIRMATION | READY_FOR_CONFIRMATION/Version 고정 | 불완전 대상 확인요청 금지 | D/H | NOT_RUN |
| AC-PKG-03 | B/C/D | 지정 Package 확인 | P | 지정/미지정·미설정 변형 | CONFIRM_COMPANY_PACKAGE | 설정된 정확한 Actor/Version만 확인 | Role만으로 확인요건 추정 금지 | D/X/H | NOT_RUN |
| AC-PKG-04 | C | E 확인 금지 | E | 확인 요청 | 직접 CONFIRM_COMPANY_PACKAGE | DENY | 편집권한 자동확인 없음 | X/D | NOT_RUN |
| AC-PKG-05 | B/D | 기업확인≠Ready | O/P | COMPANY_CONFIRMED | DATCO 판단 전 조회 | 아직 Ready 아님 | 기업확인만 Snapshot 생성 금지 | D | NOT_RUN |
| AC-PKG-06 | B/D | 전체 Readiness | O | 정상 및 승인/정보/Impact/Template 부족 변형 | MARK_PACKAGE_READY 각각 실행 | 전부 충족 시만 Ready/미충족 차단 | 하나 Gate 누락도 통과 금지 | D/X/F/H | NOT_RUN |
| AC-PKG-07 | D | 불변 Snapshot | O | Ready 생성 | 입력·파일·승인 manifest 조회/후속 변경 | 당시 조합 고정 | current Root 참조로 역사내용 변동 금지 | D/F/H | NOT_RUN |
| AC-PKG-08 | A/D | Ready Refresh | O/P | Ready/Snapshot | Refresh | 동일 저장조합/표시 | 새조회에서 Snapshot 소실 금지 | D/R/F | NOT_RUN |
| AC-PKG-09 | D | 중요변경 후 Ready | O | 기존 Ready/적용 입력 중요변경 | INVALIDATE_PACKAGE_READY/이전 Ready 사용 시도 | 새 Version PREPARING/사용보류 | 과거 Snapshot 덮어쓰기/재사용 금지 | D/X/H | NOT_RUN |
| AC-SUB-01 | B/D | Ready 없는 정상 기록 | O | 유효 Ready 없음 | RECORD_EXTERNAL_SUBMISSION | 정상경로 차단 | Portal 클릭/번호로 Gate 우회 금지 | X/D | NOT_RUN |
| AC-SUB-02 | B | 제출사실 | O | 유효 Snapshot/대응 사실 | RECORD_EXTERNAL_SUBMISSION | PENDING_EVIDENCE/Case SUBMISSION | 기록만 VERIFIED 아님 | D/H | NOT_RUN |
| AC-SUB-03 | B | Portal 클릭 | O | 준비 화면 | 외부 링크만 이동 | 내부 제출결정 없음 | 링크 클릭으로 신청완료 금지 | D | NOT_RUN |
| AC-SUB-04 | B/D | 증빙 등록 | O | 제출/검증 File | REGISTER_SUBMISSION_EVIDENCE | REVIEW_REQUIRED/Evidence 연결 | URL만 증빙확보 아님 | D/F/H | NOT_RUN |
| AC-SUB-05 | B/D | 등록≠검증 | O | 등록 직후 | 상태 재조회 | 미검증 Review | 등록만 VERIFIED 금지 | D | NOT_RUN |
| AC-SUB-06 | B/D | 공식 증빙검증 | O | 대상·공식근거·필수증빙 일치 | VERIFY_SUBMISSION_EVIDENCE | Review VERIFY/필수충족 VERIFIED | 일반 PDF/번호만 검증 금지 | D/F/H | NOT_RUN |
| AC-SUB-07 | D | 증빙 대상 불일치 | O | 다른 Case/Snapshot/File 변형 | 등록·검증 시도 | 관계 불일치 차단 | 타기업/다른 제출 근거 연결 금지 | X/D/F | NOT_RUN |
| AC-SUB-08 | B/D | 미검증 평가금지 | O | PENDING_EVIDENCE/REVIEW_REQUIRED | START_EVALUATION | Disabled/Backend 차단 | 증빙없이 신청완료·평가 없음 | X/D | NOT_RUN |
| AC-SUB-09 | A/D | File/Review Refresh | O | VERIFIED | Refresh/다운로드/Review 재조회 | 파일·대상·Review 유지 | 표시만 남고 실제 File 누락 FAIL | D/R/F/H | NOT_RUN |
| AC-SUB-10 | D/E | 외부 성공/내부 실패 | O | 실제 사실/역사적 대상·실패 | RECONCILE_EXTERNAL_SUBMISSION | 사실보존/PENDING_EVIDENCE/Impact | 과거 Ready·승인 소급위조 금지 | D/F/H | NOT_RUN |
| AC-RESULT-01 | B | 평가 Positive | O | 제출 VERIFIED/선행충족 | START_EVALUATION | EVALUATION/평가회차 OPEN | State 임의설정 금지 | D/H | NOT_RUN |
| AC-RESULT-02 | B/D | 결과 근거부족 | O | 공식 Evidence 없음 | CONFIRM_OFFICIAL_RESULT | 차단/검토 보완 | 선정 결과 추정 저장 금지 | X/D | NOT_RUN |
| AC-RESULT-03 | B/D | SELECTED | O | 대응 공식근거/회차 | CONFIRM_OFFICIAL_RESULT | SELECTED Record/Review | Demo를 실제 선정으로 오표시 금지 | D/F/H | NOT_RUN |
| AC-RESULT-04 | D | 결과/Stage 분리 | O | 공식결과 저장 | 두 Object 조회 | Outcome과 RESULT_CONFIRMED Stage 구분 | SELECTED를 Stage enum으로 사용 금지 | D | NOT_RUN |
| AC-RESULT-05 | B/D | 선정 협약 Gate | O | SELECTED/선행충족·미충족 변형 | START_AGREEMENT | 충족 때만 AGREEMENT | 결과만으로 선행 자동완료 없음 | D/X/H | NOT_RUN |
| AC-RESULT-06 | B/D | NOT_SELECTED | O | 별도 정상 평가건/근거 | CONFIRM_OFFICIAL_RESULT | 미선정 결과/기록 | Main 선정기록 덮어쓰기 금지 | D/F/H | NOT_RUN |
| AC-RESULT-07 | C/D | 미선정 협약금지 | O | NOT_SELECTED | UI/직접 START_AGREEMENT | HIDDEN/Backend DENY | 숨김 우회로 Stage 전이 금지 | X/D | NOT_RUN |
| AC-RESULT-08 | B/D | 종료/재검토 | O | 별도 미선정 건/사유 | CLOSE_NOT_SELECTED 또는 RECONSIDER_NOT_SELECTED | 허용 종료/RECONSIDERATION | 근거없이 재평가/협약 진입 금지 | D/H/X | NOT_RUN |
| AC-RESULT-09 | D | 공식정정 History | O | 기존 결과/공식정정근거 | CORRECT_OFFICIAL_RESULT | 새 결과·supersedes/Impact | 과거 삭제·Stage 자동변경 금지 | D/F/H | NOT_RUN |
| AC-TASK-01 | B | Case 업무 | O | Case/업무·완료조건 | CREATE_TASK | 연결된 Task OPEN | Company/Case 불일치 금지 | D/H | NOT_RUN |
| AC-TASK-02 | C | 담당 Scope | O | 허용/비허용 새 담당 | ASSIGN_TASK | 허용만 Assignment/이력 | 담당변경으로 권한 확대 금지 | D/X/H | NOT_RUN |
| AC-TASK-03 | B/D | Dependency | O | 선행 미완료/완료·순환 변형 | SET_TASK_DEPENDENCY/START_TASK | 선행 Gate/순환차단 | Cross Case 자동허용 없음 | D/X/H | NOT_RUN |
| AC-TASK-04 | B/D | 완료근거 부족 | O | 완료요건/Evidence 부족 | REQUEST_TASK_COMPLETION/COMPLETE_TASK | 차단/보완 | 버튼클릭만 완료 금지 | X/D | NOT_RUN |
| AC-TASK-05 | B/D | 완료 Review | O | 진행·근거·선행 완전 | REQUEST_TASK_COMPLETION/COMPLETE_TASK | COMPLETION_REVIEW→COMPLETED/Review | 근거 미검토 자동완료 없음 | D/F/H | NOT_RUN |
| AC-TASK-06 | B | Derived Overdue | O | 기한 전/후 Fixture | 현재시각별 조회 | 기한초과 표시·Task State 유지 | Overdue 저장 State 추가 없음 | D | NOT_RUN |

Task는 Main 필수 방문 화면이 아니어도 Phase-1 제품 Acceptance의 최소 기능이다. 모든 Task/Case State 조합을 전수 테스트하지 않는다.

## 9. Security / Version / Audit / Idempotency / Failure / File

| Test ID | Gate | Scenario / Purpose | Actor | Preconditions | Execution | Expected Result | Negative Assertion | Evidence | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AC-SEC-01 | C | B Company | E/P | A Context/B 기업 | Browser/Backend B 접근 | DENY | 이름·업무내용 누설 없음 | X | NOT_RUN |
| AC-SEC-02 | C | B Request | E/P | B 요청 정상 생성 | B 조회/응답 요청 | DENY/변경없음 | 요청내용·존재 누설 없음 | X/D | NOT_RUN |
| AC-SEC-03 | C | B Approval | P | B 승인요청 정상 생성 | B 조회/Decision | DENY | Role만으로 타기업 승인 금지 | X/D | NOT_RUN |
| AC-SEC-04 | C | B Case | E/P | B Case 정상 생성 | Case/Application/Package 접근 | DENY | Case에서 B 자료 유출 없음 | X | NOT_RUN |
| AC-SEC-05 | C | B Private File | E/P | B File | 직접 조회/다운로드 | DENY | 저장위치 안다고 허용 금지 | X/F | NOT_RUN |
| AC-SEC-06 | C | Deep Link | E/P | 허용/비허용 링크 | 직접 URL·알림 링크 접근 | 도착 시 재검사 | Frontend Route만 보안 아님 | X | NOT_RUN |
| AC-SEC-07 | C | 식별값 조작 | E/P/O | 정상 요청/Scope | company_id/case_id 변조 | 관계검사 DENY | 요청의 Scope 값 신뢰 금지 | X/D | NOT_RUN |
| AC-SEC-08 | C | E Approval | E | 자기 Proposal | 숨김버튼 우회/직접 승인 | DENY | Editor 승인기록 없음 | X/D | NOT_RUN |
| AC-SEC-09 | C | DATCO Approval | O/A | 기업 Request | 직접 기업 Decision | 두 Role DENY | Admin/Operator 대행 없음 | X/D | NOT_RUN |
| AC-SEC-10 | C | Frontend 우회 | E/P/O | 권한·State 미충족 Action | 직접 Backend 호출 | Backend 차단/변경없음 | ENABLED/요청값 신뢰 금지 | X/D | NOT_RUN |
| AC-SEC-11 | C | Secret 전체경계 | S/O | 가짜 Secret 반사 Fixture | Frontend/Log/Raw/Audit/Fixture 검사 | 비노출/안전한 오류 | 전체 인증URL/원문오류 없음 | L/J/H | NOT_RUN |
| AC-SEC-12 | C | Prompt Injection | S/O | 명령문 포함 Source | 추출/분석·출력검증 | 데이터로 처리/업무 Action 없음 | Approval/Proceed/권한변경 실행 금지 | D/J/L | NOT_RUN |
| AC-SEC-13 | C | P 편집 상속 없음 | P | 승인 Role만 부여 | E 입력 Command 직접 시도 | DENY/업무결정만 허용 | Approver→Editor 자동상속 금지 | X/D | NOT_RUN |
| AC-VER-01 | D | 현재 Version 표시 | O/E/P | 중요 Version 객체 | 현재 조회 | 보는 대상/현재 적용 대상 명시 | 다른 Version 표시 혼동 없음 | D | NOT_RUN |
| AC-VER-02 | D | 역사 조회 | O/P | 과거본/허용 공개범위 | Historical 조회 | 과거 내용/Actor/대상 보존 | 역사조회만 현재 사용가능 선언 금지 | D/H | NOT_RUN |
| AC-VER-03 | D | Stale Action | O/P | 오래 열린 대상/새 Version | 과거 expected Version 실행 | G-VERSION/현재성 차단 | 새 Version으로 자동 제출 금지 | X/D | NOT_RUN |
| AC-VER-04 | D | 승인 History | O/P | v1 승인→v2 | 이력 조회 | v1 Decision/Request 보존 | v2 자동승인·이력삭제 없음 | D/H | NOT_RUN |
| AC-VER-05 | D | Notice 변경 | O/S | 적용 Notice 새 Version | 변경 후 Proposal/Case 조회 | 원본 보존/적용영향 표시 | 모든 Case 자동덮어쓰기 없음 | D/H | NOT_RUN |
| AC-VER-06 | D | Impact/후속조치 | O/S | 실제 Lineage 변경 | CREATE_IMPACT_ASSESSMENT/RESOLVE_IMPACT_REVIEW/REGISTER_IMPACT_FOLLOWUP | 대상별 검토·실제 완료참조 | RESOLVED만 후속완료 아님, 복구 Action의 순환 Gate 없음 | D/H/X | NOT_RUN |
| AC-VER-07 | D | 재승인 Gate | O/P | 중요변경 후 미승인 | Proceed 차단→새 Request/승인·필요 후속완료→재시도 | 미해결 차단/충족 후 정상 | v1 승인으로 v2 진행 금지 | D/X/H | NOT_RUN |
| AC-VER-08 | D | Analysis 입력 오용 | O/S | 다른 입력 Version Run | 현재결과로 사용 시도 | 역사보존/현재사용 차단 | 오래된 분석을 새확정으로 표시 금지 | D/J/X | NOT_RUN |
| AC-AUDIT-01 | D | E2E Lineage/Audit | O/A | 정상 E2E 결과 | Result→증빙→Package→Case→Proceed→Approval→Proposal→Match→Review→Source 추적 | 해당 객체·Version·Actor·근거·시각 연결 | 전체 Payload 중복저장/Secret 노출로 대체 금지 | D/F/H/L | NOT_RUN |
| AC-IDEM-01 | D | 수집 요청 재전송 | O | 같은 Action Identity | REQUEST_COLLECTION 재전송 | 기존 요청/Job 결과 | 중복 Job, 실패를 새성공으로 위장 금지 | D/J | NOT_RUN |
| AC-IDEM-02 | D | Notice 재수집 | O/S | 동일 Source+ID/내용 | 재수집 | 같은 Root/업무 Version | 새 수집이력 자체는 허용 | D/J | NOT_RUN |
| AC-IDEM-03 | D | 승인 응답유실 | P | 성공 응답 유실 주입 | 동일 APPROVE_PROPOSAL 재전송, 다른 Outcome도 시도 | 같은 역사 Decision/다른의미 차단 | 현재 CLOSED라는 이유로 중복실행 금지 | D/H/X | NOT_RUN |
| AC-IDEM-04 | D | Case 재전송 | O | 유효 Proceed/응답유실 | CREATE_SUPPORT_CASE 반복 | 기존 한 Case | 정당한 새 Proceed의 복수 Case 차단 금지 | D/H | NOT_RUN |
| AC-IDEM-05 | D | Snapshot 재Import | O/S | 동일 Snapshot | 새 수집/같은 데이터 재Import | 같은 Mapping/내용 Version/이력 | 중복 Root/Version, 최신 자동후퇴 금지 | D/J | NOT_RUN |
| AC-FAIL-01 | E | Page 실패 | O/S | 성공 Page 후 실패 주입 | 수집/허용 Retry | PARTIAL/실패범위·Attempt 보존 | 정상 Notice 삭제 없음 | J/D | NOT_RUN |
| AC-FAIL-02 | E | 첨부 실패 | S | 목록 저장/파일 실패 | 확보 결과 재조회 | Notice 유지/Partial·재확보 사유 | File 확보성공 위장 없음 | D/J/F | NOT_RUN |
| AC-FAIL-03 | E | Invalid 분석출력 | S/O | 타입/ID/위치 잘못된 출력 | Validation·저장 시도 | 격리/FAILED 또는 유효범위 PARTIAL | Invalid Confirmed 생성 없음 | D/J | NOT_RUN |
| AC-FAIL-04 | E | Provider Timeout | S/O | 통제 Timeout | 실패/허용 Retry | 오류·새 Attempt/입력 검증 | 기존 Run 삭제/자동확정 금지 | J/D | NOT_RUN |
| AC-FAIL-05 | E | Live→Snapshot | O/S | Fixture Adapter Live 실패 | 실패확인→명시 SNAPSHOT REQUEST_COLLECTION | 별도 Mode/Job/같은 경로 | 실제 장애재현 성공으로 오인 금지 | J/D/L | NOT_RUN |
| AC-FAIL-06 | E | Worker 중단 | S/O | PROCESSING 중단 주입 | RECOVER_INTERRUPTED_JOB/허용 Retry | 실행소유/완료근거 대조·Attempt 보존 | 근거없이 SUCCEEDED 위장 금지 | J/D/H | NOT_RUN |
| AC-FAIL-07 | E/D | 제출 재조정 | O | 실제 외부사실/내부실패 | RECONCILE_EXTERNAL_SUBMISSION | 역사적 사실/대상/사유 보존 | 소급 승인/Ready·다른 Snapshot 위조 금지 | D/F/H | NOT_RUN |
| AC-FAIL-08 | E/D | 실행 중 입력변경 | S/O | 분석 중 새 Version | 완료/사용·재분석 | 과거 Run 보존/새 입력 별도 | stale 결과 현재 Confirm 오용 금지 | D/J/X | NOT_RUN |
| AC-FILE-01 | D | 공식 Source 확보 | S/O | 공식 URL/유효·불완전 Content | Host/Redirect/형식·Signature/저장 검증 | 안전하게 확보된 File만 성공 | Header/확장자만 성공 금지 | F/J/L | NOT_RUN |
| AC-FILE-02 | D | URL≠확보 | O/S | 참조만 존재 | Source/File 조회 | 미확보 상태/근거 한계 | URL만 FileAsset 성공 아님 | F/D | NOT_RUN |
| AC-FILE-03 | D | 확보≠추출 | S/O | 파일있음/추출실패 | 분석 입력/결과 조회 | 실패·미지원/Partial 표시 | 빈문서 완전분석 금지 | F/J/D | NOT_RUN |
| AC-FILE-04 | C/D | Private File Scope | E/P/O | A/B 파일 | 업로드·연결·조회 변형 | 부모+공개범위 검사 | 공개 부모로 Private 범위 확대 금지 | F/X/D | NOT_RUN |
| AC-FILE-05 | C | Evidence Viewer | E/P | 허용/비허용 근거 | Preview/다운로드 | Backend 재검사 | Viewer 직접URL bypass 금지 | F/X | NOT_RUN |
| AC-FILE-06 | C | Storage ID 조작 | E/P | B 저장 식별 | 직접 Storage URL/ID 접근 | DENY | 내용·존재 누설 없음 | X/F | NOT_RUN |
| AC-FILE-07 | D | 바이트변경 | S/O | 기존 파일/새 내용 | 재확보/연결 | 새 FileAsset/과거 Content 보존 | 같은 ID 덮어쓰기 금지 | F/D/H | NOT_RUN |
| AC-FILE-08 | D | Receipt 대상 | O | 제출/맞는·다른 Receipt | 등록/검토 | 대응 근거만 승인 | 파일명만으로 공식·대상 일치 추정 금지 | F/D/X | NOT_RUN |

## 10. Full E2E / Demo / 운영성 / 조건부 검증

| Test ID | Gate | Scenario / Purpose | Actor | Preconditions | Execution | Expected Result | Negative Assertion | Evidence | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AC-E2E-01 | B/F | Full Snapshot E2E | O/E/P | 09 Precondition/AG-01/의미있는 Fixture | 09 H01~25를 정상 Action으로 실행 | CHK-01~10/14의 연결된 저장결과 | 중간 Decision/Ready Seed·Guard 우회 없음 | D/R/F/J/H | NOT_RUN |
| AC-DEMO-01 | F | Demo 재현/예외 | O/E/P | 정상 Dataset/필수 Screen·계정 | Main Re-run 및 EX-01/02/04/05/06의 통제 검증 | Checkpoint/권한·재승인·증빙·미선정·Mode 재현 | 실제 LIVE 실패가 없는데 장애 Test PASS 주장 금지 | D/R/X/F/J/H | NOT_RUN |
| AC-UI-01 | A/E | 기본 운영성/오류 의미 | O/E/P | 큰 Job/차단·실패 입력 | Job 진행·timeout/실패·차단복귀 확인 | 무한대기 없이 기술상태/원인·보완경로 | Secret/타기업 존재/Stack Trace 없음 | J/D/X/L | NOT_RUN |
| AC-UI-02 | F | 추가 Browser/접근성 | O/E/P | 실제 추가 요구 확정 시 | 합의된 환경/범위로 실행 | 요구범위 결과 기록 | 임의 Version/WCAG/Breakpoint 요구 생성 금지 | D/Report | NOT_RUN |
| AC-EXT-01 | E | 채택 AI Provider Integration | S/O | 실제 Provider 선택/계약·보안범위 | 제한된 실제 입력/출력·변환 검증 | Adapter/Schema/Scope/품질·실패 확인 | Fixture Test를 Provider PASS로 기록 금지 | J/D/F/L | NOT_RUN |

AC-UI-02/AC-EXT-01은 OPTIONAL/조건부 확장검증이다. 선택된 Provider가 실제 기능 완성에 필요하면 해당 기능의 실행 준비조건을 별도로 충족해야 하며, 미검증 외부전송/정확도를 승인했다고 주장하지 않는다. DMP 실제 운영 연동·전국기관·모든 Format·Production Scale/HA·고급 AI 전체는 Phase-1 완료조건이 아니다.

## 11. 09 Checkpoint / E2E / Role Coverage

| Demo Checkpoint | Acceptance Test IDs | Acceptance Proof |
| --- | --- | --- |
| CHK-01 | AC-COL-01~06, AC-FILE-01~03 | 원천/Mode/Notice·Version/확보 상태 |
| CHK-02 | AC-NOTICE-01~08 | Input/Candidate/Evidence/공식 Human Review/Refresh |
| CHK-03 | AC-INPUT-01, AC-COMPANY-01, AC-FACT-01~07, AC-IMP-01~07 | 회사 입력/Fact·과제 Version/충돌·확인 |
| CHK-04 | AC-MATCH-01~09, AC-REQ-01~08 | Missing→요청→검증→현재 Snapshot/Review |
| CHK-05 | AC-PROP-01~02, AC-APPROVAL-01~09 | 지정 Actor/Request/Version/Decision·금지권한 |
| CHK-06 | AC-PROCEED-01~03, AC-CASE-01~05 | 승인/추진/Case 분리·Gate/중복·Refresh |
| CHK-07 | AC-APP-01~08, AC-INPUT-01 | Template·값 Source/확인·Lock |
| CHK-08 | AC-PKG-01~09 | 지정 기업확인/전체 Readiness/불변 Snapshot |
| CHK-09 | AC-SUB-01~10, AC-FILE-08 | 실제사실/등록·검증/제출대상/평가차단 |
| CHK-10 | AC-RESULT-01~09 | 공식 결과·Stage/선정·미선정·정정 |
| CHK-11 | AC-SEC-01~10, AC-FILE-04~06 | Company/Request/Approval/Case/File 직접 DENY |
| CHK-12 | AC-VER-01~08, AC-APPROVAL-07~09 | 역사보존/Stale/재승인/Impact 후속조건 |
| CHK-13 | AC-COL-09~10, AC-FAIL-05, AC-DEMO-01 | 공통 Normalize/Mode, 실제 Live 여부 별도 |
| CHK-14 | AC-ENV-04, AC-AUDIT-01, AC-IDEM-01~05, AC-FILE-07 | 영속성/Actor·Version·근거/역추적·중복없음 |

| E2E Flow | Acceptance Test IDs | Coverage |
| --- | --- | --- |
| FLOW-01~05 | AC-COL-01~10, AC-FILE-01~03/07 | 수집/Pagination/Mapping/Version/Source 내부 Integration |
| FLOW-06 | AC-NOTICE-01~08 | 후보/요건 검토 |
| FLOW-07~10 | AC-INPUT-01, AC-COMPANY-01~02, AC-FACT-01~07, AC-IMP-01~07 | 기업/자료/Fact/과제 |
| FLOW-11~13 | AC-CAP-01~02, AC-MATCH-01~09, AC-REQ-01~08 | Catalog/Assessment/Match/요청 |
| FLOW-14~17 | AC-PROP-01~02, AC-APPROVAL-01~09, AC-PROCEED-01~03 | 제안/승인/재승인/추진 |
| FLOW-18~21 | AC-CASE-01~05, AC-APP-01~08, AC-PKG-01~09, AC-SUB-01~10 | Case/신청/준비/제출 |
| FLOW-22~23 | AC-RESULT-01~09, AC-TASK-01~06 | 공식결과/대표 단계·업무/선행·완료 |
| FLOW-24/30 | AC-UI-01, AC-E2E-01, AC-DEMO-01 | 알림·Dashboard는 파생조회/원객체 이동, 읽음≠결정 |
| FLOW-25~27 | AC-VER-01~08, AC-FAIL-01~08, AC-SEC-01~13 | 영향/실패·Retry/Scope |
| FLOW-28 | AC-ENV-02/04, AC-AUDIT-01, AC-FILE-07 | 복구 정합성 범위는 아래 설명 적용 |
| FLOW-29 | AC-COL-01/09, AC-IDEM-05, AC-ENV-05 | Snapshot/재Import·Dataset 격리 |
| FLOW-31 | AC-ENV-03, AC-FILE-04~07, AC-AUDIT-01 | 내부 Permission/ID/History 경계, 실제 DMP 연동은 미검증 |
| FLOW-32 | AC-AUDIT-01, AC-E2E-01 | 원천→결정→제출·결과 Lineage |

복구/승인된 Import·Export의 실제 운영 Use Case도 Phase-1에 포함되므로 AC-OPS-01/02로 아래 검증한다. DMP 교체 경계 Test는 실제 DMP SSO/API Integration 완료를 의미하지 않는다.

| Test ID | Gate | Scenario / Purpose | Actor | Preconditions | Execution | Expected Result | Negative Assertion | Evidence | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AC-OPS-01 | A/D/E | 복구 정합성 | A | 격리된 DB/File/Version/Audit 복구대상·정상/누락 변형 | 승인된 복구 후 VERIFY_OPERATIONAL_RECOVERY | 실제 File/참조·Decision·Audit 일치 검증, 불일치 보류 | 복구누락을 업무완료로 위장 금지 | D/R/F/H | NOT_RUN |
| AC-OPS-02 | C/D/E | 승인된 Import/Export | A | 승인 요청/허용 대상·공개범위 | IMPORT_OR_EXPORT_DOMAIN_DATA 및 미승인/타범위 시도 | 해당 Domain 검증·Scope·Version/idempotency·Audit | 분석/승인/Ready Gate 우회·Private 공유 금지 | D/X/J/H/L | NOT_RUN |
| AC-NOTIFY-01 | B/C/E | 알림/원객체 연결 | O/E/P/S | 정상 업무 Event/허용 Recipient·전달실패 변형 | 원업무 Action 후 알림·대상 이동/ACKNOWLEDGE_NOTIFICATION, 전달실패 조회 | 권한 있는 원객체로 이동/본인 읽음/전달이력 | 읽음≠업무결정, 전달실패로 기존 Decision 삭제/rollback 없음 | D/X/J/H | NOT_RUN |

FLOW-28은 AC-OPS-01, FLOW-29의 일반 업무이동은 AC-OPS-02, FLOW-24의 수신·전달실패 경계는 AC-NOTIFY-01이 추가 담당한다. 세 Case는 MANDATORY이며 Collector Snapshot와 ADMIN 업무 Import를 구분한다.

| Role | Positive | Negative |
| --- | --- | --- |
| DATCO_ADMIN | AC-CAP-01/AC-OPS-01~02 관리·복구 | AC-APPROVAL-03/AC-SEC-09 기업승인 불가 |
| DATCO_OPERATOR | AC-NOTICE-05/AC-PROCEED-02 Review/추진 | AC-APPROVAL-03 기업승인 불가 |
| COMPANY_EDITOR | AC-COMPANY-01/AC-REQ-03 자기 입력·응답 | AC-APPROVAL-02/AC-PKG-04 승인·확인 불가 |
| COMPANY_APPROVER | AC-APPROVAL-01/AC-PKG-03 지정결정 | AC-APPROVAL-04/AC-SEC-13 타기업·일반편집 불가 |

## 12. Pass/Fail / DEMO_READY / 구현 수용 Gate

각 Case는 정의된 입력 변형을 실행하고 기대 저장결과·불가행위의 미발생·필수 Evidence를 확인해야 PASS다. 단순 UI Toast/높은 Confidence/잘 보이는 화면/기존 Probe 관찰만으로 PASS가 아니다. Security/Version/공식증빙 오류를 “Demo이므로 허용”하지 않는다.

**DEMO_READY**는 09 Main/필수 예외의 재현, MUST_SHOW 16 Screen/정상 Role Account, 의미·관계 검증된 Snapshot Dataset, AG-01 저장·Upload 구현, CHK-01~12/14의 필수 Proof와 명시적 Mode/외부사실·Demo 구분을 요구한다. AC-E2E-01/AC-DEMO-01 및 이 Proof에 매핑된 결정적 기능·권한·History Case가 PASS여야 한다. CHK-13의 통제 fallback/공통 경로는 PASS, 실제 Live 결과는 별도 보고한다. 당일 외부장애로 AC-COL-10이 BLOCKED여도 Snapshot Demo 준비도는 별도 판단할 수 있다. Mandatory Security/Version/Evidence FAIL이나 Demo bypass가 있으면 DEMO_READY 불가다.

**BASELINE_IMPLEMENTATION_ACCEPTED**는 모든 MANDATORY Case가 실행되고 PASS, MANDATORY FAIL/BLOCKED/NOT_RUN 0, Security/Scope·Version/Approval/Proceed·Package/Submission/Evidence 위반 0, 핵심 Persistence PASS, CHK-01~14 Coverage/Evidence 완료, AG-01 구현·검증 완료, Main/필수 예외 재현, Secret 노출·Demo 우회 없음일 때만 판정한다. Phase-1의 실제 Bizinfo 기능도 AC-COL-10으로 검증돼야 한다. BLOCKED_EXTERNAL을 필수항목 면제/PASS로 취급하지 않으며 실행 가능 시 재검증한다.

DEMO_READY ≠ 전체 Production 운영승인, BASELINE_IMPLEMENTATION_ACCEPTED ≠ DMP Production Go-Live Approved다. 실제 DMP 계약/Company·File API, Production Backup 정책/SLA·대규모 부하·보안진단·개인정보/AI 계약·전국기관 운영은 별도 범위다. 이번 문서에서 수치/제품/새 규정을 추정하지 않는다.

## 13. 실행 순서 / 자동화 / 최소 운영성

구현 후 Environment/Persistence → Fixture/Snapshot → Collector → Notice/Intelligence → Company/Improvement → Matching/Request → Proposal/Approval → Proceed/Case → Application/Package → Submission/Evidence → Result/Task → Security Negative → Version/Reapproval → Failure/Recovery → Full E2E → Demo Re-run → Gate 판정 순서로 수행한다. 관련 Negative·보안검사는 해당 Slice 개발 중에도 실행하고 마지막까지 미루지 않는다. CI 제품/실제 Pipeline은 Decision-001의 Open Decision으로 유지하며 실제 구현·협업·배포 환경 확인 후 결정한다.

Permission/Scope/State/Version/Persistence/idempotency/Schema/API·Domain 결과는 자동화 적합하다. Evidence가 주장을 뒷받침하는지, PDF 위치를 실제 읽을 수 있는지, Matching Reason과 Source가 맞는지, Fixture의 기간·단위/조건·증빙이 일관되는지는 사람 의미검토가 필요하다. 같은 자연어 문장 출력 자체를 Acceptance로 요구하지 않는다.

화면 무한대기/Job 상태 관측불가/외부 timeout 불가/큰 작업이 UI 요청을 영구 Block하는 문제는 AC-UI-01로 확인한다. 성능·동시사용자·Production SLA 수치는 실제 요구 전 확정하지 않는다. Browser Web의 핵심 E2E 가능성을 검증하고 임의 지원 Browser Version/WCAG Level/모바일 Breakpoint를 구조적 Blocker로 만들지 않는다. 오류의 정확한 문구보다 차단 이유/보완 위치/Secret·타기업정보·Stack Trace 없음의 의미를 검증한다.

## 14. Gap / Open Decision / Validation

**새 Acceptance Blocking Gap: 없음.** 기존 Action/State/Screen·Checkpoint로 수용기준을 정의할 수 있다. AG-01 미구현, 승인·확인 설정 미정, 의미있는 대응 Fixture 부족은 실행 Prerequisite이며 실제 해당 Test를 BLOCKED로 남긴다. 아직 구현/Test가 없다는 사실을 설계 구조적 누락 또는 PASS로 바꾸지 않는다. AG-02는 Main 준비계정으로 대응하고 관리 UI 포함 시 별도 계약·검증이 필요하다.

| Open Decision | 후속 확인 |
| --- | --- |
| OD-01 Test Framework | Decision-001: Backend pytest/FastAPI API Test 확정. Vitest/React Testing Library 사용방향 확정, Component 세부범위는 첫 Slice |
| OD-02 Browser Automation | Decision-001: Playwright 확정, 핵심 E2E/Negative의 실행구현은 후속 |
| OD-03 CI | 실제 Pipeline |
| OD-04 Test DB | Decision-001: 실제 PostgreSQL Integration 방향 확정. DB 준비/격리·실행 세부는 구현 단계 |
| OD-05 Fixture Loader | 기존 FIX-*·정상 Input 경로 |
| OD-06 Demo Reset | 승인된 격리 준비/재현 |
| OD-07 Live Integration 실행시점 | 접근 가능 환경·제한적 호출 |
| OD-08 실제 AI Provider Integration | 선택/계약·보안·출력 품질 |
| OD-09 Performance 수치 | 실제 요구/측정 후 |
| OD-10 Screenshot/Artifact 저장방식 | Secret 제외 Evidence 참조 |
| OD-11 운영 Browser 범위 | 실제 사용자 요구 |

아래는 **문서 검토 결과**이며 위 AC-*의 NOT_RUN을 PASS로 바꾸지 않는다.

| Validation | 근거 | 검토결과 |
| --- | --- | --- |
| A Spec/실행/수용 분리 | 1/12절 | 정의됨 |
| B 기본 NOT_RUN | 모든 AC 표 | 정의됨 |
| C CHK-01~14 매핑 | 11절 | 연결 |
| D 결정적 Snapshot E2E | AC-E2E-01 | 정의됨 |
| E Live/Fixture 구분 | AC-COL-10/AC-EXT-01 | 정의됨 |
| F Collector 중복 | AC-COL-03~04/AC-IDEM | 정의됨 |
| G Candidate/Human | AC-NOTICE/FACT/IMP | 정의됨 |
| H Scope Positive/Negative | AC-COMPANY/SEC | 정의됨 |
| I AG-01 필수 구현 | AC-INPUT-01 | 정의됨 |
| J Fact Conflict/기간·단위 | AC-FACT-05~06 | 정의됨 |
| K Missing→Rematch | AC-MATCH/REQ | 정의됨 |
| L FIT≠PROPOSABLE | AC-MATCH-07~08 | 정의됨 |
| M 정확한 승인 Version | AC-PROP/APPROVAL | 정의됨 |
| N E/DATCO 승인금지 | AC-APPROVAL-02~04/SEC | 정의됨 |
| O 승인/추진/Case 분리 | AC-PROCEED/CASE | 정의됨 |
| P Application 후보/확인 | AC-APP-02~06 | 정의됨 |
| Q 기업확인/Ready | AC-PKG-03~06 | 정의됨 |
| R Ready/Submission | AC-SUB-01~03 | 정의됨 |
| S Register/Verify | AC-SUB-04~06 | 정의됨 |
| T 미검증 평가차단 | AC-SUB-08 | 정의됨 |
| U 미선정 협약금지 | AC-RESULT-07 | 정의됨 |
| V Stale/Reapproval | AC-VER/APPROVAL | 정의됨 |
| W Persistence | AC-ENV-04/각 Refresh Case | 정의됨 |
| X Direct URL/API/File | AC-SEC/FILE | 정의됨 |
| Y 복구 History 보존 | AC-FAIL/OPS/IDEM | 정의됨 |
| Z Stack/Skeleton 전환 | 15절 | 설계상 가능 |

02 Flow, 03 Object/Version·File·Lineage, 04 State/Guard/idempotency, 05 Role/Scope, 06 Collector/Mode, 07 Input/Candidate/Human, 08 Screen/Gap, 09 Main/예외/Checkpoint와 교차검토했다. 상위문서와 구조적 충돌은 발견하지 않았다. 88 Action×모든 State 조합/모든 Entity CRUD/새 업무정책/임의 SLA 및 승인된 범위 외 Test Framework를 추가하지 않는다.

## 15. 00~10 Baseline 완료 판단 / 다음 단계

**DESIGN BASELINE: READY.** Standalone Phase-1을 시작할 기능·State/Action·권한·화면·Demo·Acceptance 경계가 정의됐다. **실제 SYSTEM ACCEPTANCE: NOT_TESTED.** 모든 AC-*는 NOT_RUN이며 DEMO_READY/BASELINE_IMPLEMENTATION_ACCEPTED가 달성됐다고 판정하지 않는다.

00~10 Baseline 동결 후 Phase-1 Stack은 Decision-001로 승인되었다. 다음은 개발환경 확인/준비 → Repository/Application Skeleton → 첫 Vertical Slice의 Physical Schema/AG-01 계약 구체화 → 구현/Test 실행 → 09 Demo 재현 → Evidence 기반 Acceptance 판정이다. Git 작업은 별도 사용자 지시 없이 수행하지 않는다. Stack 승인은 실제 Test PASS가 아니다.

구현 전 해당 Slice의 AG-01 저장·Upload/권한·Version 계약, 선택한 Stack/Adapter, 실제 의미있는 Sanitized Fixture/공식근거 대응관계, 지정 승인/Package 확인요건을 구체화해야 한다. 외부전송 Adapter는 실제 계약/보안범위를 확인하고 미확정 Provider/Rate/Retry 수치를 추정하지 않는다. 이 준비사항은 설계 동결을 막는 새로운 구조적 Blocker가 아니다.

**승인된 Phase-1 Stack으로 개발환경 확인/준비 및 Skeleton 단계 진행 가능한가: YES. 실제 시스템 Acceptance가 완료됐는가: NO — NOT_TESTED.**
