# DATCO 정부지원사업 운영체계 - Demo Scenario

> 2026-10-30 MVP v1.0 범위 증분: 이번 사용자 명시 개발 지시의 완료 범위는 기업 개선요구 → 검토된 DATCO 서비스 단독/복합 구성 → 실제 지원사업 검토·3자 매칭 → 표준 제안서 DOCX/PDF 검토·수요기업 전달까지다. 아래 전주기 H01~H32·신청/선정 후 운영은 미래 확장과 과거 기준으로 보존한다. 기존 Role/State/Company Scope·CONFIRM/ACK/PROPOSABLE·승인·원본/Version Guard는 변경하지 않는다. 대표/조직의 별도 공식 승인 상태는 미확인이다. 세부 실행 계약과 신규 M01~M18 인수는 [MVP 개발 계약](mvp/MASTER_DEVELOPMENT_CONTRACT.md), [인수 기준](mvp/ACCEPTANCE.md)을 따른다.

## 1. 목적 / 기준 / 범위

개발 완료 후 실제 Browser에서 누가 어떤 자료·화면·Action으로 핵심 가치와 Domain 무결성을 증명할지 정의한다. 기준은 [AGENTS](../AGENTS.md) → [00 Baseline](00_PROJECT_BASELINE.md) → [01 Architecture](01_SYSTEM_ARCHITECTURE.md) → [02 E2E](02_E2E_SYSTEM_FLOW.md) → [03 Data](03_DATA_MODEL.md) → [04 State/Action](04_STATE_ACTION_MODEL.md) → [05 Permission](05_PERMISSION_UI_MATRIX.md) → [06 Collector](06_BIZINFO_COLLECTOR.md) → [07 Intelligence](07_INTELLIGENCE_DESIGN.md) → [08 Screen/Action](08_SCREEN_ACTION_SPEC.md) → 이 문서다.

Demo는 Production Domain 흐름의 역할·Scope·State·Version·Guard·Evidence·Audit를 그대로 사용한다. Demo 전용 승인/상태변경 API, DB 직접 상태조작, 권한 bypass, Candidate의 직접 Confirmed Seed, ApprovalDecision 직접 삽입, READY_TO_SUBMIT 직접 설정, 접수증 없이 신청완료, Live 실패를 조용히 성공으로 표시하는 경로는 금지한다.

Main Happy Path는 하나이며 공고 수집/원천 → 사람 검토 → 기업 Fact/Improvement → 3-way Match → 정보요청/검증 → 제안/기업승인 → 별도 Proceed/Case → Application/Package → 제출사실/증빙 → 공식결과 및 H26~32의 사후관리 완료까지 연결한다. 두 Company 격리, Refresh Persistence와 History도 증명한다. 선정 Main의 협약·수행·검수·정산·종료·사후관리는 필수다. 모든 Screen/ADMIN 기능/Task State 조합/공고/Format/OCR/Scheduler/DMP Integration을 전수 시연하지 않는다.

발표시간·날짜·발표자 대본, UI 디자인/Route/API, DB Script/Seed Code/실제 Fixture 파일, AI Provider/Stack/Cloud는 확정·생성하지 않는다. 새로운 Entity/State/Action/Guard/Role/Permission/Screen은 만들지 않는다. 아래 계획은 실제 Demo 성공 또는 구현 완료 보고가 아니다.

## 2. Actor / Company / Mode

O=DATCO_OPERATOR, E=Company A의 COMPANY_EDITOR, P=Company A의 지정 COMPANY_APPROVER다. ADMIN은 Capability 준비/승인된 운영 보조에만 선택적으로 사용하고 Main의 OPERATOR Action이나 기업승인을 대행하지 않는다. 인증된 별도 Account/허용 Role Context로 전환하며 Browser Role 값 조작·임의 회사 선택 기능은 없다. Login/Role Context는 08 Common Pattern이다.

Company A는 Main 대상, Company B는 교차기업 접근차단 대상이다. 동아테크놀로지(DongA Technology)를 A의 대표 Fixture로 사용할 수 있지만 기업명/ID/업종/조건/권한을 시스템에 하드코딩하지 않는다. 미확인 실제 기업 수치·개인정보를 사실처럼 만들지 않고 SYNTHETIC/SANITIZED/DEMO_ONLY 의미를 표시한다. 논리 Fixture ID는 실제 DB PK가 아니다.

Main Notice는 1개다. 제목/대상/기간/개요와 하나 이상의 의미있는 자격·과제조건, 분석 가능한 HTML/PDF·서류근거를 가진 입력을 선정한다. 현재 Probe 마스킹 Sample은 구조검증용이므로 이 요건을 충족했다고 가정하지 않는다.

Main의 재현 가능한 기준 실행은 **명시적 SNAPSHOT Mode**다. 제한된 LIVE 수집을 Source 연결 Proof로 보여줄 수 있으며 실제 사용 Notice/조건이 Fixture와 일관할 때 Main을 LIVE로 진행할 수 있다. LIVE는 실제 API, SNAPSHOT은 검증된 Sanitized Source → 동일 Raw/Parser/Normalize/Mapping/Notice/Version 경로다. 두 Mode/원 Source 시점/현재 Import 시점을 표시한다. Live 장애/시점변동이면 이유와 실패결과를 남기고 별도 Snapshot 요청을 실행하며 기존 실패를 성공으로 덮어쓰지 않는다.

## 3. Fixture Catalog / 준비와 생성 경계

Source Class는 LIVE_SOURCE, SANITIZED_SOURCE, SYNTHETIC_DEMO, SYSTEM_GENERATED_DURING_DEMO로 구분한다. 준비자료는 내용을 가진 입력이고, Demo에서 증명할 Decision/상태전이 결과는 실제 Action으로 생성한다. 실제 Secret/PII/바이너리를 이 문서에 넣지 않는다.

| Fixture ID | Type | Source Class | Purpose | Must Exist Before Demo? | Generated During Demo? |
| --- | --- | --- | --- | --- | --- |
| FIX-USER-OPERATOR | Account/Role Context | SYNTHETIC_DEMO | 허용 A/B 업무 Operator | Y | N |
| FIX-USER-EDITOR-A | Account/Membership | SYNTHETIC_DEMO | A 입력/응답 | Y | N |
| FIX-USER-APPROVER-A | Account/Membership | SYNTHETIC_DEMO | A 지정 승인/Package 확인 | Y | N |
| FIX-USER-ADMIN | Account/Role Context | SYNTHETIC_DEMO | 선택적 기준정보 준비 | 선택 | N |
| FIX-COMPANY-A | Company/Site/Profile 입력 | SYNTHETIC_DEMO | 대표 제조기업 개선과제 | Y | 실제 입력은 Demo에서 가능 |
| FIX-COMPANY-B | Company/Private Source | SYNTHETIC_DEMO | A로부터 Company/File 차단 | Y | N |
| FIX-NOTICE-LIVE | Bizinfo 응답 | LIVE_SOURCE | 실제 수집 연결 Proof | N | LIVE 선택 시 수집 |
| FIX-NOTICE-01 | Raw JSON Snapshot | SANITIZED_SOURCE | Main Notice 조건/원천 | Y | Notice/Version은 Import 중 생성 |
| FIX-NOTICE-CONTENT-01 | HTML/PDF Source | SANITIZED_SOURCE | 본문·기간·서류/Evidence | Y | 확보/추출/Run은 실행 중 |
| FIX-COMPANY-DOC-01 | Company 입력문서 | SYNTHETIC_DEMO | Fact Candidate·기간/단위 검토 | Y | File/Intake/후보는 Upload 경로 |
| FIX-FACT-BASE-01 | 초기 Fact/근거 묶음 | SYNTHETIC_DEMO | 분석에 필요한 최소 기초정보 | Y, 선택 범위 | 별도 준비 Review 또는 Main Review |
| FIX-IMPROVEMENT-INPUT-01 | 과제 작성자료 | SYNTHETIC_DEMO | 현재공정/문제/목표/기능 | Y | 제출본/Review는 Demo 중 |
| FIX-CAPABILITY-01 | 준비된 CapabilityVersion/근거 | SYNTHETIC_DEMO | 실제 대응가능 조건/제외/범위 | Y | 필요 시 준비 단계 정상 발행 |
| FIX-MISSING-INPUT-01 | 부족정보 응답자료 | SYNTHETIC_DEMO | 자격 근거 1개 보완/Rematch | Y | Request/Response/검증은 Demo 중 |
| FIX-PROPOSAL-INPUT-01 | 제안 내용 입력자료 | SYNTHETIC_DEMO | 서비스/비용/부담/책임 일관성 | Y | Proposal/Approval은 Demo 중 |
| FIX-APPLICATION-INPUT-01 | 신청 값/계획/서류 | SYNTHETIC_DEMO | Template 정의에 맞는 입력 | Y | Application/확인값은 Demo 중 |
| FIX-EVIDENCE-RECEIPT-01 | 제출사실·접수 근거 입력 | SANITIZED_SOURCE | 해당 대상/제출과 연결된 증빙 | Y | Submission/Evidence Review는 Demo 중 |
| FIX-EVIDENCE-RESULT-01 | 공식 결과 근거 입력 | SANITIZED_SOURCE | Main SELECTED 결과 검토 | Y | OfficialResultRecord는 Demo 중 |
| FIX-EVIDENCE-NOT-SELECTED-01 | 미선정 근거 입력 | SANITIZED_SOURCE | 별도 예외 분기 | 예외 전 Y | 결과/분기는 정상 Action으로 생성 |
| FIX-ANALYSIS-ADAPTER-01 | 검증된 분석 재현 입력/출력 | SYNTHETIC_DEMO | 외부 AI 장애 대비/결정적 회귀 | Y, Mode 선택 | 공통 Input/Run/Validation 경로로 후보 생성 |
| FIX-RUNTIME-ANALYSIS | Run/Candidate/Review/확정결과 | SYSTEM_GENERATED_DURING_DEMO | 원천→분석→Human Proof | N | Y |
| FIX-RUNTIME-REQUEST | Request/Response/Review | SYSTEM_GENERATED_DURING_DEMO | 필요 정보 확보 | N | Y |
| FIX-RUNTIME-DECISIONS | MatchReview/Proposal/Approval/Proceed | SYSTEM_GENERATED_DURING_DEMO | Actor·Version별 판단 | N | Y |
| FIX-RUNTIME-CASE | Case/Application/Package/Snapshot | SYSTEM_GENERATED_DURING_DEMO | 추진 이후 실제 운영 | N | Y |
| FIX-RUNTIME-SUBMISSION | 제출기록/Evidence Review/Result | SYSTEM_GENERATED_DURING_DEMO | 제출과 공식근거 확인 분리 | N | Y |

초기 User/Company/Site/Capability와 일부 기초 Fact는 준비 가능하다. 초기 Confirmed Fact를 쓴다면 준비 단계의 정당한 Source/Review/Version을 가진 값만 사용하고 Main에서 확인을 증명할 Fact는 사전완료 Seed하지 않는다. Main Improvement는 아직 Submit 전, Proposal/Approval/Proceed/Case/Application/Package/Submission/Result는 없다. 분석후보/Decision을 사전에 완성한 데이터처럼 주입하지 않는다. Template은 필요 시 준비 가능하지만 Main 기본안은 확인된 Requirement/서식으로 04 확인 Action을 수행한다.

Fixture는 Company Fact 기간·단위/자격조건, Improvement→Capability 대응범위, Capability→Proposal 서비스, Requirement→Template, Proposal→ApprovalRequest 정확한 Version, Package→Application/승인, Receipt→제출 대상/시각, Result→Case/공식회차가 일관되어야 한다. 다만 자격근거 1개를 의도적으로 미확인으로 두며, 개선과제 확인에 필요한 정보는 충분하여 CONFIRM_IMPROVEMENT 이전의 Blocking을 억지로 무시하지 않는다.

## 4. Precondition / 실제 외부사실 구분

별도 Demo Dataset, 정상 인증·Membership/권한, A/B·기초자료, Capability, 의미있는 Notice Source/File, 실제 DB Persistence/File Storage/다운로드, 07 Input Contract/분석 Validation/Review, 08 Screen과 AG-01 입력·Upload 계약이 구현·검증되어야 실행한다. P의 Proposal required approver set과 Package 확인 Actor를 명시 지정한다. 05의 미설정 요건을 자동 승인/확인으로 추정하지 않는다. LIVE 선택 시 Backend `.env` Key 존재를 값 노출 없이 확인한다.

외부 Government Portal을 재구현하거나 발표 중 실제 정부신청을 강제하지 않는다. **실제 제출을 했다면 실제 제출사실·공식증빙**, 격리 Demo라면 **표시된 Demo External Submission Fact와 검증된 대응 증빙 Fixture**를 사용한다. 실제 정부 제출/선정을 수행한 것처럼 설명하지 않는다. Sanitized 공식 근거는 원천·변형범위/대응관계를 기록하고 Demo의 대상 Company/Notice/Snapshot/제출 Metadata와 맞아야 한다.

일치하는 자료를 준비할 수 없다면 해당 제출/공식결과 Step은 미완료로 남긴다. 일반 샘플 PDF·파일명·접수번호만으로 공식성 확인을 통과시키지 않는다. Fixture라는 이유로 G-OFFICIAL/G-EVIDENCE/Company·Case·Version 검사를 생략하지 않는다. Synthetic 증빙으로 대체할 경우 실제 공식근거가 아닌 Demo 자료임을 명시하고 정상 검증 계약에 맞는 지원범위를 사전 확인해야 하며, 확인되지 않은 신뢰정책/예외 Guard를 새로 만들지 않는다.

## 5. DEMO-HAPPY-01 — 자유입력·수집부터 사후관리까지

Main Scenario는 하나다. 모든 행은 CORE이며 조회 보조 화면은 7절 SUPPORTING 기준으로 통합해 보여줄 수 있다. 같은 행의 여러 Backend Action은 **각각 별도 실행/결과 확인**이며 하나의 자동 완료 버튼이 아니다. 요청 후 Worker 결과를 기다리고 다음 업무 Gate를 검사한다. Actor는 인증 Context를 확인한 후 전환한다.

| Step | Actor | Screen | User Action | Backend Action | Input / Precondition | Expected Result | Demo Proof |
| --- | --- | --- | --- | --- | --- | --- | --- |
| H01 | O | SCR-DASH-01 | Role/Company/Mode·시작상태 확인 | 조회 | 별도 Dataset/사전 결정 없음 | 초기 업무현황 | 로그인·허용 Context, Main Case 없음 |
| H02 | O | SCR-OPS-01 | LIVE 또는 명시적 SNAPSHOT 수집요청 | REQUEST_COLLECTION | Source/비밀 제외 조건/준비 Source | Job QUEUED→Worker 결과 | Mode/Job/Attempt/Page, 실패와 완료 구분 |
| H03 | O | SCR-NOTICE-01 | Main 공고 선택 | 조회 | H02 정상 저장 Notice | Notice/현재 NoticeVersion | Source+외부ID/내부 Notice 분리·원천 연결 |
| H04 | O | SCR-NOTICE-02 | Source/파일 확보·분석요청·후보검토·요건확인 | REQUEST_NOTICE_REVIEW, CONFIRM_NOTICE_REQUIREMENT | 정확한 Version/공식 Source·Location/분석완료 | RequirementVersion/AnalysisReview | Candidate≠Confirmed, 근거·확인자, Refresh 유지 |
| H05 | E | SCR-COMPANY-02 / SCR-IMPROVE-01 | 자기 기업자료 Upload/과제 Draft 저장·제출 | AG-01 입력 계약, SUBMIT_IMPROVEMENT | Company A/작성자료/필수 내용 | Intake/File, Submitted ImprovementVersion | 실제 저장·제출 Lock·Source, Refresh 후 Submitted 유지 |
| H06 | O | SCR-FACT-01 | Company Fact 후보/기간·단위·근거 확인 | CONFIRM_NEW_FACT_VALUE 또는 CONFIRM_EXISTING_FACT_VALUE | A 문서 추출후보/기존값 비교 | FactReview/정확한 FactVersion | AI 후보가 직접 Master 변경하지 않음 |
| H07 | O | SCR-IMPROVE-01 | 제출 과제 분석/Evidence 검토·확인 | CONFIRM_IMPROVEMENT | 제출 Version/기초 Fact/분석결과·부족정보 Gate | 확인된 ImprovementVersion/Review | 문제·목표·필요기능과 Source 연결 |
| H08 | O | SCR-MATCH-01 | 준비 Catalog에 대한 Assessment 검토, 초기 Match 요청 | REVIEW_CAPABILITY_ASSESSMENT, REQUEST_MATCH_ANALYSIS | 확인 과제/Catalog·Requirement·사용가능 Fact, 부족 자격근거 1개 | 검토된 Assessment/고정 Snapshot/NEED_MORE_INFO 후보 | Eligibility·Task/Service Fit·Missing·반대근거 구분 |
| H09 | O | SCR-REQUEST-01 | 부족근거 항목·이유·기한을 요청 | SEND_INFORMATION_REQUEST | A 대상/정보항목/Context/작성완료 | WAITING_RESPONSE | 필요한 정보만 발송·Actor/Audit |
| H10 | E | SCR-REQUEST-01 | 응답 Draft/자료 저장 후 제출 | AG-01 입력 계약, SUBMIT_INFORMATION_RESPONSE | 자기 Request/대응 근거 | 불변 ResponseVersion, Request REVIEW_REQUIRED | Submitted≠Verified, 제출자·Version |
| H11 | O | SCR-REQUEST-01 / SCR-FACT-01 | 응답검증/관련 Fact 확인 | VERIFY_INFORMATION_RESPONSE, 필요 시 CONFIRM_NEW_FACT_VALUE | 제출본/Evidence/공식요건 및 Fact Guard | Verified 응답/확인된 부족 Fact | 응답값 자동확정 금지, 실제 Review/Fact 연결 |
| H12 | O | SCR-MATCH-01 | 현재 입력으로 재분석·MatchReview | REQUEST_MATCH_ANALYSIS, REVIEW_MATCH | 새 Fact·검토입력/Blocking 해소 | 새 Snapshot/Candidate, Review PROPOSABLE | FIT≠PROPOSABLE, 예전 결과/부족근거 이력 보존 |
| H13 | O | SCR-PROPOSAL-01 | Proposal v1 생성·내용검토·승인요청 | CREATE_PROPOSAL_VERSION, REQUEST_APPROVAL | 현재 PROPOSABLE/정보충족/지정 P | v1 Lock/ApprovalRequest OPEN | 범위·비용·부담·책임·승인대상 Version |
| H14 | P | SCR-APPROVAL-01 | 지정 v1 확인·승인 | APPROVE_PROPOSAL | A/자기 지정 OPEN Request/정확한 v1 | 불변 Decision APPROVE, Request CLOSED | 승인 Actor/시각/Version, Refresh 후 결정 유지 |
| H15 | O | SCR-PROCEED-01 | 승인·Match·Impact Gate 확인 후 추진확정 | CONFIRM_PROCEED | 유효 v1 승인/현재 입력/Missing 없음 | 별도 ProceedDecision | Approval이 Proceed를 자동 생성하지 않음 |
| H16 | O | SCR-PROCEED-01 / SCR-CASE-01 | 추진건 Case 생성 | CREATE_SUPPORT_CASE | 유효 Proceed/동일 Proceed Case 없음 | Case APPLICATION_PREP | Case ID/입력·담당, Refresh 후 유지 |
| H17 | O | SCR-APP-01 | 확인요건으로 Template/신청본 준비·값검토·전체확인 | CONFIRM_APPLICATION_TEMPLATE, CREATE_APPLICATION_VERSION, REQUEST_APPLICATION_REVIEW, CONFIRM_APPLICATION_VALUE, CONFIRM_APPLICATION | 확인된 Requirement/서식/Case, Verified 자료·기업입력 근거/AG-01 | 검토된 Template/ApplicationVersion·ValueReview/CONFIRMED | Auto-fill Candidate/Source Fact/확인값 분리 |
| H18 | O | SCR-PACKAGE-01 | 입력·계획·필수/조건부서류 준비/기업확인 요청 | REQUEST_COMPANY_CONFIRMATION | 완전한 Application/자료/고정 대상 | READY_FOR_CONFIRMATION | Checklist, 아직 Ready/제출 아님 |
| H19 | 지정 P | SCR-PACKAGE-02 | Package/Application 대상 확인 | CONFIRM_COMPANY_PACKAGE | A Case/정확한 Version/지정 확인요건 | COMPANY_CONFIRMED/확인기록 | 기업 Actor/시각/대상, DATCO Ready와 분리 |
| H20 | O | SCR-PACKAGE-01 | 승인·정보·서류·Impact Readiness 확인 | MARK_PACKAGE_READY | Company Confirmation/현재 승인/전체 Guard | READY_TO_SUBMIT/불변 Snapshot | Snapshot 조합/자료·승인, Refresh 후 유지 |
| H21 | O | SCR-SUBMIT-01 | 실제 또는 표시된 Demo 외부제출 사실 기록 | RECORD_EXTERNAL_SUBMISSION | 사용한 유효 Ready Snapshot/대응 외부사실 Metadata | PENDING_EVIDENCE, Case SUBMISSION | Portal 클릭≠제출, 기록만으로 완료 아님 |
| H22 | O | SCR-SUBMIT-01 | 대응 Receipt 등록 후 공식근거 검토 | REGISTER_SUBMISSION_EVIDENCE, VERIFY_SUBMISSION_EVIDENCE | 실제 확보/검증된 대응 증빙/대상 일치 | REVIEW_REQUIRED→VERIFIED | 별도 등록/검토/Audit, Refresh 후 File·Review 유지 |
| H23 | O | SCR-RESULT-01 | 증빙 Gate 후 평가시작 | START_EVALUATION | 제출 VERIFIED/선행조건 | Case EVALUATION/평가회차 | 증빙확인 전 시작 불가 |
| H24 | O | SCR-RESULT-01 | 대응 공식 결과근거 검토·확인 | CONFIRM_OFFICIAL_RESULT | 정확한 대상·회차/결과 Evidence, Demo 표시 | Result SELECTED, Case RESULT_CONFIRMED | OfficialResultRecord와 Stage 분리·검토자/Source |
| H25 | O | SCR-CASE-01 | 진행/Version/Decision/Evidence/Timeline 추적 | 조회 | H01~24 저장결과 | 결과 확인 시점의 연결된 업무상태 | Source→Review→Proposal/Approval→Proceed→Case/제출/Result 일부 역추적 |

Main은 Missing→Request→Response→Verification→Rematch를 포함한다. Missing을 FAIL/숫자 추정으로 채우지 않고 현재 적용 Fact/Requirement로 판단하는 가치를 증명한다. 초기 Match는 부분입력 후보이며 PROPOSABLE Gate를 통과하지 않는다. H11 Verification과 원 Domain Fact 확정은 필요한 경우 별도 Action이다.

H17 기본은 O가 H10의 기업 제공/확인 자료와 Fact를 신청입력에 사용하여 Role 전환을 줄인다. 기업이 직접 작성해야 하는 추가 항목이 실제 Fixture에 있다면 E의 SCR-APP-01 허용 입력을 거친 후 O 확인을 수행한다. 이는 새 Scenario/권한이 아니며 P에게 E 편집권한을 자동 부여하지 않는다.

Main은 SELECTED의 RESULT_CONFIRMED 이후 §12 H26~32까지 필수다. 기존 근거/선행조건을 충족하는 정상 Action으로 수행하며 모든 Task State 조합을 순회할 필요는 없다. Role 전환은 O→E→O→E→O→P→O→P→O 순서이며 각 전환을 인증된 계정으로 확인한다.

## 6. 핵심 Exception Scenario 5개

예외는 Main과 별도 격리된 실행/Branch 데이터로 수행하거나 적절한 Main Checkpoint에서 확인한다. Main에서 증명한 Missing 흐름은 DEMO-EX-03으로 다시 시연하지 않고 H08~12를 참조한다. 이미 끝난 결과/Case를 수동으로 되돌려 예외를 만들지 않는다.

| Scenario | Actor / Screen | 준비·시도 / 기존 Action | Expected Result / Proof | 복귀 / 범위 |
| --- | --- | --- | --- | --- |
| DEMO-EX-01 Cross-company | A의 E 또는 P / SCR-COMPANY-02와 Evidence Common Pattern | B의 Company와 Private File Deep Link 직접 접근. 10에서 Request/Approval/Case API까지 확장 | ACCESS_DENIED/Backend DENY, B 이름·State·File 존재·내용 누설 없음 | A Context로 복귀. 화면 숨김만으로 차단 완료 주장 금지 |
| DEMO-EX-02 Stale/Reapproval | O/P / SCR-PROPOSAL-01, SCR-APPROVAL-01, SCR-PROCEED-01 | 정상 v1 승인까지 실행한 별도 건에서 비용/범위 중요변경→CREATE_PROPOSAL_VERSION v2. 오래 열린 v1 요청 시도/현재 Proceed 검사. 새 REQUEST_APPROVAL→P APPROVE_PROPOSAL | v1 Decision 보존, v2 자동승인 없음, 이전 승인요청/Version 오용 차단, REAPPROVAL_REQUIRED/Proceed Disabled·Backend 차단. v2 승인/Impact 후속조건 충족 후 Proceed 가능 | 새 현재 대상·Review/Impact를 실제 경로로 해결. 과거 기록 삭제 없음 |
| DEMO-EX-04 Evidence 미검증 | O / SCR-SUBMIT-01, SCR-RESULT-01 | H21 후 Receipt 미등록/PENDING_EVIDENCE 또는 등록 후 REVIEW_REQUIRED에서 START_EVALUATION 검사 | Disabled/Backend 차단, 증빙확인 전 신청완료/EVALUATION 없음 | H22 검증 후 Gate 충족. Main의 해당 Checkpoint에서 보여주며 별도 완성자료 Seed 안 함 |
| DEMO-EX-05 NOT_SELECTED | O / SCR-RESULT-01, SCR-CASE-01 | 별도 정상 경로의 평가건에 대응 미선정 Evidence로 CONFIRM_OFFICIAL_RESULT. 협약 경로 확인 | Outcome NOT_SELECTED/Stage RESULT_CONFIRMED, START_AGREEMENT HIDDEN·직접 요청 차단 | CLOSE_NOT_SELECTED 또는 조건 있는 RECONSIDER_NOT_SELECTED. Main SELECTED 기록 덮어쓰기 없음 |
| DEMO-EX-06 Live/Snapshot | O / SCR-OPS-01, SCR-NOTICE-02 | 실제 LIVE 실패 또는 불안정/시점변동을 알린 뒤 명시적 SNAPSHOT REQUEST_COLLECTION | LIVE 실패/선택 사유 유지, 새 SNAPSHOT Mode/Job, 동일 Raw/Normalize/Notice 경로로 진행 | Demo에 장애를 유발하려고 실제 Key 변조/고의 과호출하지 않음. 실패 주입은 10 통제된 Test |

LIVE가 정상일 때 EX-06의 실제 장애 복구를 수행했다고 주장하지 않는다. 명시적 Mode 선택 경로는 설명/확인 가능하며 강제 장애재현은 통제된 Fixture/Adapter Test로 넘긴다. 외부 AI 장애도 07의 명시된 Fixture Adapter→공통 Input/Run/Validation/Review 경로를 사용하고 재현 Mode/한계를 표시한다. 실패를 숨기는 완성 Candidate/Confirmed 직접 주입은 없다.

OPTIONAL 보조 Proof는 Metadata/HTML은 확보하고 첨부 실패인 Partial 입력이다. Missing Source/제한 Candidate/미확정 범위를 보여주고 전체 Requirement Confirmed를 선언하지 않는다. 핵심 5개 예외에 추가 필수 Scenario로 늘리지 않는다.

## 7. Demo Screen Coverage / Screen Traceability

08 Critical Set 19개를 모두 따로 방문하도록 강제하지 않는다. MUST_SHOW는 업무결정·입력·근거와 수행·사후관리 Task를 확인할 17개, SUPPORTING은 조회가 통합돼도 되는 2개다. Login/Role Context/Evidence Viewer는 공통 Pattern으로 확인한다.

| Screen ID | Coverage | Main Step / 제외·통합 이유 |
| --- | --- | --- |
| SCR-DASH-01 | SUPPORTING | H01 시작 Context, 업무 원화면에서 상태 확인 가능 |
| SCR-OPS-01 | MUST_SHOW | H02/EX-06 Mode·Job·수집 Proof |
| SCR-NOTICE-01 | SUPPORTING | H03 탐색, Detail 진입과 저장 Notice 확인으로 통합 가능 |
| SCR-NOTICE-02 | MUST_SHOW | H04 Source/Version/분석·Review |
| SCR-COMPANY-02 | MUST_SHOW | H05 기업/자료/Scope |
| SCR-FACT-01 | MUST_SHOW | H06/11 후보·기간·단위·확인 |
| SCR-IMPROVE-01 | MUST_SHOW | H05/07 제출·검토 |
| SCR-MATCH-01 | MUST_SHOW | H08/12 Assessment/Snapshot/부족·Review |
| SCR-REQUEST-01 | MUST_SHOW | H09~11 실제 요청·응답·검증 |
| SCR-PROPOSAL-01 | MUST_SHOW | H13/EX-02 제안 Version |
| SCR-APPROVAL-01 | MUST_SHOW | H14/EX-02 지정 Actor 승인 |
| SCR-PROCEED-01 | MUST_SHOW | H15/16 별도 Decision·Case 생성 |
| SCR-CASE-01 | MUST_SHOW | H16/25 집계·History |
| SCR-APP-01 | MUST_SHOW | H17 후보값/확인값·Template |
| SCR-PACKAGE-01 | MUST_SHOW | H18/20 Readiness/Snapshot |
| SCR-PACKAGE-02 | MUST_SHOW | H19 지정 기업확인 |
| SCR-SUBMIT-01 | MUST_SHOW | H21/22 제출사실/등록·검증 |
| SCR-RESULT-01 | MUST_SHOW | H23/24 평가 Gate/공식결과 |
| SCR-TASK-01 | MUST_SHOW | 수행·사후관리 Task 담당·진척·완료검토·완료 이력 |

Main 표가 Step/Screen/Actor/04 Action/Expected Domain Result의 Traceability Matrix를 겸한다. Stage/결정이 다른 화면을 단순 목록으로 대체하지 않는다. 전체 Catalog 관리/기업목록/ADMIN 운영/전체 Audit Explorer는 Main 필수가 아니다. 승인 Actor/근거·이력은 각 업무 화면에서 확인한다.

## 8. E2E Traceability / Checkpoint Handoff

| Demo Scenario / Step | 02 E2E Flow |
| --- | --- |
| H02~04 | FLOW-01~06 수집/Pagination/Notice/변경/Source/Analysis Review |
| H05~07 | FLOW-07~10 기업/Fact/Improvement 제출·분석 |
| H08/12 | FLOW-11 Capability Assessment, FLOW-12 MatchReview |
| H09~11 | FLOW-13 Request/Response/검증 |
| H13~15 / EX-02 | FLOW-14~17 Proposal/Approval/Reapproval/Proceed |
| H16 | FLOW-18 Case 생성 |
| H17~22 | FLOW-19~21 Application/Package/Submission Evidence |
| H23~25 / EX-05 | FLOW-22 평가/결과/분기 |
| 선택적 Task Proof | FLOW-23 Task/Schedule |
| EX-02 | FLOW-25 실제 변경영향·후속조치 |
| EX-01 | FLOW-27 Company/File/직접접근 차단 |
| H02 / EX-06 | FLOW-26 실패/Retry, FLOW-29 Snapshot Import |
| H25 및 아래 Checkpoint | FLOW-30 파생 진행현황, FLOW-32 Source/Evidence/Version/Audit Lineage |

09는 **무엇을 확인하는가**를 정의한다. 정식 Pass/Fail Procedure/모든 Test Assertion은 10에서 작성한다. Browser + Backend 저장결과로 증명하며 SQL 직접 확인을 기본 Demo Proof로 쓰지 않는다.

| Checkpoint | Scenario Step | Proof | 10 Acceptance Handoff |
| --- | --- | --- | --- |
| CHK-01 Source/Notice 저장 | H02~04 | Raw/Source+External ID/NoticeVersion/확보 파일·Mode | 수집/정규화/중복·Source 관계 검증 |
| CHK-02 Candidate/Human Review | H04 | Candidate 근거·Location/Reviewer/RequirementVersion, Refresh 유지 | Schema/Evidence/공식근거/부분입력 Guard |
| CHK-03 Company 입력·Fact·과제 | H05~07 | A File/Fact 기간·단위·Review/Submitted→Confirmed, Refresh | 입력저장·추출후보·Conflict/Company Scope |
| CHK-04 Missing/Request/Rematch | H08~12 | Unknown→Request→Response→Verified→새 Snapshot/PROPOSABLE | Missing≠Fail, FIT≠Review, 현재 입력 관계 |
| CHK-05 정확한 기업 승인 | H13~14 | 지정 A/P/Request/v1/Decision, Refresh 후 유지 | E/DATCO 승인거부·지정 Actor/Version 검사 |
| CHK-06 Proceed/Case 분리 | H15~16 | Approval·Proceed·Case의 서로 다른 Record/입력, Refresh | Proceed Gate/동일 Proceed 중복/idempotency |
| CHK-07 Application 확인 | H17 | Template/Requirement/Value Source/후보·확인값 | Template/Version/값·문서 검토 Gate |
| CHK-08 기업확인/Ready | H18~20 | 지정 P 확인기록 vs O Readiness/불변 Snapshot, Refresh | 확인요건·승인·필수자료·Impact/Lock 검사 |
| CHK-09 제출/증빙검증 | H21~22 / EX-04 | PENDING_EVIDENCE→REVIEW_REQUIRED→VERIFIED, File·Review Refresh | 등록≠검증/공식증빙/제출 Snapshot/Evaluation Gate |
| CHK-10 공식 결과/Stage | H23~24 / EX-05 | 평가회차/Result Evidence/SELECTED 또는 NOT_SELECTED, Case Stage | 공식근거/결과 분기·미선정 협약금지 |
| CHK-11 타기업 접근거부 | EX-01 | A의 B Company/File DENY, 보호정보 미노출 | Company/Request/Approval/Case/File 직접 URL/API 확장 |
| CHK-12 Version/재승인 | EX-02 | v1 역사보존/v2 미승인/Proceed 차단/새 승인 후 조건충족 | stale·reapproval·Impact 후속조치/현재 사용가능성 |
| CHK-13 외부장애/Mode | EX-06 | LIVE 실패/전환사유·새 SNAPSHOT Job·동일 경로 | 장애주입/명시적 fallback/Raw·Normalize 동등성 |
| CHK-14 History/Persistence | H25 및 H04/05/14/16/20/22 | Actor/Action/Object/Version/Evidence/시간, 재조회·Refresh 후 동일 저장결과 | Persistence/File/Version/Decision/Audit 원천역추적 |

Notice/Improvement/Proposal/Application/Package Version은 읽고 있는 대상과 현재 적용 대상을 표시한다. EX-02만 핵심 Version 변경을 실제 증명하며 모든 Version을 변경할 필요는 없다. H04/05/14/16/20/22의 새로고침은 화면 메모리가 아닌 영속 결과를 확인하고 File·Review 연결도 보존되는지 본다. 전체 Audit 검색 대신 H25에서 한 건의 Source→분석→Review→Proposal/Decision→Case/제출 일부 Lineage를 보여준다.

## 9. 실패 / Reset / Re-run / Implementation Prerequisite

Bizinfo LIVE/AI Provider/File Preview 실패를 숨기지 않는다. 안전한 원인·현재 Mode·미완료 범위를 표시하고 허용 Retry/명시적 Snapshot 또는 분석 Fixture Adapter로 복귀한다. File Preview 실패는 확보 File/다운로드/Source Location 검토와 구분하며 원문을 확인할 수 없으면 검토 완료로 위장하지 않는다. Guard 실패는 요구자료/승인/현재 Version을 정상 경로로 보완한다.

동일 Action 재클릭/응답 유실은 04 idempotency와 저장결과 확인을 사용한다. 오류/Attempt/기존 성공기록을 지우지 않는다. Re-run은 별도 Demo Dataset/준비 Reset으로 시작 Precondition을 복원하는 개념이며 Reset SQL/API/Seed Script나 새 Domain Action을 여기서 만들지 않는다. Production 삭제와 혼동하지 않고 파괴적 Reset은 승인된 격리 Demo 범위에서만 후속 구현한다. Snapshot 재Import는 중복 Root/동일 Version을 만들지 않으며 Dataset과 Source Mode를 기록한다.

| 08 Gap | Demo 처리 | 완료 전 필요한 확인 |
| --- | --- | --- |
| AG-01 Draft/Upload Command | **IMPLEMENTATION_PREREQUISITE**. H05/10/17의 저장·Upload를 실제 구현하며 Submit/Confirm으로 대체하지 않음 | 세부 Command/Role·Scope/Version Lock/Validation/Audit 계약과 실패·영속성 Test |
| AG-02 User/Membership Command | Main은 준비된 Account/Role Seed 사용, ADMIN 사용자관리 시연 필수 아님 | 준비된 Membership/승인자 Context 검증. 해당 관리기능 구현 시 별도 계약 확정 |

두 Gap을 새 Action으로 확정하지 않는다. 현재 필요한 State/Screen/권한·Version/업무 Action 연결에 **새로운 구조적 Demo Blocking Gap Candidate는 없음**이다. 다만 AG-01 미구현, 일치하는 의미있는 Source/Receipt/Result Fixture 부족, 승인/확인 요건 미설정은 **실제 Demo 실행 전 해결할 준비조건**이다. 이번 문서 작성은 그것들이 이미 준비됐다는 뜻이 아니다.

## 10. Open Decision / 종료조건 / Critical Proof

| ID | 미확정 | 이 문서의 최소 기준 |
| --- | --- | --- |
| OD-01 | 발표시간 | CORE 우선, 실제 시간은 미설정 |
| OD-02 | 발표자/역할별 조작 담당 | 인증된 Account 전환 유지 |
| OD-03 | 실제 발표 LIVE/SNAPSHOT 선택 | 재현 기준은 SNAPSHOT, LIVE는 시점/자료 검증 후 명시 선택 |
| OD-04 | 정확한 Bizinfo Notice | 의미있는 자격·기간·개요·서류근거 1개 선정 |
| OD-05 | 실제 Sanitized HTML/Attachment 선정 | 실제 Content·Role/Location·완전성 검증 |
| OD-06 | Result 후 Agreement 클릭 여부 | Decision-002로 협약부터 사후관리 완료까지 필수. 단계별 근거/완료조건은 실행 전 확인 |
| OD-07 | Reset 구현 방식 | 격리 Dataset/Precondition 복원, 운영 삭제와 분리 |
| OD-08 | 실제 Fixture 파일 형식/식별 매핑 | 03 Object/Source/Version 일관성 유지 |
| OD-09 | AI Provider/Fixture Adapter 실행 방식 | 공통 Input/Run/Validation/Review, Mode·한계 표시 |
| OD-10 | Navigation 미세순서 | Main 업무 의존순서/Actor/Action을 변경하지 않음 |

Information Request를 Main에 포함하는 선택은 확정했고 Open으로 남기지 않는다. 실제 자료/도구 선택이 달라져도 Scope·Version·Human Decision·증빙 검증은 동일하다.

Main 종료는 Notice 확인/기업과제/MatchReview/Request 검증/Proposal/기업 Approval/Proceed/Case/Application/기업확인/READY_TO_SUBMIT/제출기록/증빙 VERIFIED/공식 Result 및 H26~32의 사후관리 완료까지 **저장된 연결**이 이어진 때다. Snapshot/Fixture 기반이면 실제 외부 제출·선정을 완료한 것으로 말하지 않는다. 예외·Persistence/History Proof는 Checkpoint로 확인한다. 아직 구현하지 않은 화면 또는 준비되지 않은 Step은 완료한 것처럼 보고하지 않는다.

Critical Proof는 Source(외부 원천→Notice/Version), Intelligence(Source→Candidate→Evidence→Human), Company(입력/Fact/Improvement/Scope), Matching(3축/Missing/Opposing Evidence), Decision(정확한 Proposal Approval→별도 Proceed), Operations(Case→Application→Package→Submission→Result→협약→수행→검수→정산→종료→사후관리 Task), Security(Cross-company DENY), History(Version/Evidence/Audit/Refresh)다.

## 11. Validation A~Z / 10 착수 판단

문서상 정합성 검토이며 실제 Browser/API/DB/Fixture Test 또는 Demo를 실행한 결과가 아니다.

| 검증 | 근거 | 결과 |
| --- | --- | --- |
| A Production Domain 경로 | 1/5절 기존 Action | 충족 |
| B 권한/Scope/Guard 유지 | Actor Context/모든 Step/예외 | 충족 |
| C DongA 하드코딩 없음 | Company A 논리 Fixture | 충족 |
| D Company B Fixture | Catalog/EX-01 | 정의 |
| E LIVE/SNAPSHOT 구분 | 2절/H02/EX-06 | 충족 |
| F 동일 Collector/Normalize | 2절/CHK-13 | 충족 |
| G Notice Source/Version | H02~04/CHK-01 | 연결 |
| H Candidate/Human 분리 | H04/06/07 | 충족 |
| I Missing 자동추정 금지 | H08~12 | 충족 |
| J Request/Response Proof | H09~11/CHK-04 | 연결 |
| K FIT/PROPOSABLE 분리 | H08/12 | 충족 |
| L 정확한 Proposal 승인 | H13/14 | 충족 |
| M EDITOR 승인 금지 | P만 Approval Actor/CHK-05 | 유지 |
| N Approval/Proceed 분리 | H14/15 | 충족 |
| O Proceed/Case 분리 | H15/16 | 충족 |
| P Application 후보/확인 | H17/CHK-07 | 연결 |
| Q 기업확인/Ready 분리 | H19/20 | 충족 |
| R Ready/외부제출 분리 | H20/21 | 충족 |
| S 증빙등록/검증 분리 | H22/EX-04 | 충족 |
| T Result/Stage 분리 | H24/EX-05 | 충족 |
| U 미선정 협약금지 | EX-05/CHK-10 | 연결 |
| V Stale/Reapproval | EX-02/CHK-12 | 연결 |
| W Refresh Persistence | H04/05/14/16/20/22/CHK-14 | 정의 |
| X Version/Evidence/Audit | H25/CHK-14 | 연결 |
| Y AG-01/02 새 Action 없음 | 9절 Prerequisite/Seed 책임 | 충족 |
| Z 10용 Checkpoint | CHK-01~15 | 준비 |

02 E2E, 04 State/Action/Guard, 05 Actor/Scope, 06 Mode/Raw/Normalize, 07 Candidate/Evidence/Human Review, 08 기존 Screen과 교차검토했다. 상위문서와 구조적 충돌은 발견하지 않았다. 발표 대본/클릭좌표/전체 Acceptance Assertion/새 Demo Domain을 추가하지 않는다.

**10_TEST_ACCEPTANCE 설계 착수 가능: YES.** Main 순서·예외·Fixture 요건·화면/Action·Checkpoint가 연결돼 있다. 다음은 10 → 00~10 설계 Baseline 확정 → Stack → Skeleton → 실제 Vertical Slice/통합 Test/Demo이며 이번 작업에서 Fixture/Seed/Source/UI/API/DB를 생성하거나 외부 API/AI/OCR을 호출하지 않는다.

## 12. 전주기 필수 시연 및 비성공 결과 (Decision-002)

H05에서 기업 로그인/Company Context를 확인하고 카테고리 선택 없이 자유서술·선택적 사진/자료를 실제 저장·제출한다. 원문·수정 Version과 구조화 후보를 구분한다. H07~12는 확인된 Capability의 서비스 조합·조건/범위와 공고 적합성을 독립 검토한다. 합성 역량은 DEMO 표시한다. H14 제안 승인과 H17~20 Application 확인/기업 Package 확인/Ready는 별개다.

아래 CORE Step은 H25 다음 같은 Company/Case로 수행한다. 단계별 Task/Evidence/완료조건은 확인된 사업조건 또는 명시적 Demo Fixture 조건으로 준비한다. 자료가 부족하면 BLOCKED이며 Guard를 완화하지 않는다. 입력 자료만 준비하고 Stage/Task 완료결과는 Seed하지 않는다. 가상 협약·산출물·검수·정산 자료는 SYNTHETIC_DEMO로 표시한다. 접수/결과의 공식성 계약과 의미 있는 Fixture 대응관계는 §4를 유지하며 일반 샘플로 검증을 우회하지 않는다.

| Step | Actor / Screen | 기존 Action 및 필수 Proof |
| --- | --- | --- |
| H26 | O / SCR-RESULT-01, SCR-CASE-01 | SELECTED·협약 근거/선행조건 충족 후 START_AGREEMENT, AGREEMENT 이력 |
| H27 | O / SCR-CASE-01, SCR-TASK-01 | 협약조건 충족 후 START_EXECUTION. CREATE_TASK/ASSIGN_TASK/START_TASK로 수행계획·담당·기한·진척 저장, 필요한 완료요청/검토 |
| H28 | O / SCR-CASE-01, SCR-TASK-01 | 수행 Task·산출 근거 충족 후 START_INSPECTION. 산출물 파일·검수 Task/Evidence/검토 연결 |
| H29 | O / SCR-CASE-01, SCR-TASK-01 | 검수조건 충족 후 START_SETTLEMENT. 정산자료·선행 Task/검토 저장 |
| H30 | O / SCR-CASE-01 | 정산/종료 Task·근거 충족 후 CLOSE_CASE. CLOSED/종료 이력·사후관리 연결 |
| H31 | O / SCR-TASK-01 | CLOSED Case 사후관리 CREATE_TASK/ASSIGN_TASK/START_TASK → REQUEST_TASK_COMPLETION → COMPLETE_TASK. 완료조건·검토·Evidence/이력 보존, Case CLOSED 유지 |
| H32 | O/E/P / 허용 Workspace | 새로고침·재로그인 후 원문/사진→입력 Version→매칭 근거→제안/승인→신청/증빙→Stage→사후관리 완료의 연결 조회 |

CHK-15를 추가하여 H26~32의 저장·파일·선행조건·완료 Review·CLOSED 유지·재로그인 이력을 확인한다. 기존 CHK-01~14/예외는 보존한다.

| 필수 Scenario | 기대 결과 / 연결 |
| --- | --- |
| SCENARIO-A | 자유입력→서비스 조합→공고 적합 검토→제안/기업 승인→H16~32 전주기 완료, CHK-01~15 |
| SCENARIO-B | Catalog 밖 요구 정상 저장·Capability 미매칭 사유/Review 보존. 허위 서비스·근거 없는 자동 제안 없음, AC-MVP-02 |
| SCENARIO-C | 서비스 적합이나 공고 부적합/미확인. 허위 공고 추천·적격 판정 없이 사유/확인업무 보존, AC-MVP-03 |
| SCENARIO-D | 모호·부족 원문 보존→추가정보 요청/응답→사람 검토. Unknown을 FIT로 변경하지 않음, AC-MVP-04 |
| SCENARIO-E | 승인 후 중요변경의 과거 승인·새 Version/Impact·재승인 Guard, DEMO-EX-02 |
| SCENARIO-F | 타기업 자료/파일/제안/승인 직접 접근 서버 DENY, DEMO-EX-01 |

필수 범위 승인은 구현 완료·대표 승인·공식 제출/선정·Test PASS가 아니다. 별도 최종 신청 승인 정책은 결정 대기이며 기존 Action을 유지한다.
