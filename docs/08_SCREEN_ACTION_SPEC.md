# DATCO 정부지원사업 운영체계 - Screen / Action Specification

## 1. 목적 / 기준 / 불변조건

00~07의 Object/Version/State/Action/Guard/Permission을 실제 Browser의 표시 데이터·User Action·성공/실패 후 결과로 연결하는 최소 Screen Contract다. 기준은 [AGENTS](../AGENTS.md) → [00 Baseline](00_PROJECT_BASELINE.md) → [01 Architecture](01_SYSTEM_ARCHITECTURE.md) → [02 E2E](02_E2E_SYSTEM_FLOW.md) → [03 Data](03_DATA_MODEL.md) → [04 State/Action](04_STATE_ACTION_MODEL.md) → [05 Permission](05_PERMISSION_UI_MATRIX.md) → [06 Collector](06_BIZINFO_COLLECTOR.md) → [07 Intelligence](07_INTELLIGENCE_DESIGN.md) → 이 문서다.

화면은 Domain Source of Truth가 아니다. Backend에 저장된 Object/State/Version/Decision/Evidence를 조회한다. Proposal 조회 ≠ 승인, Portal 링크 클릭 ≠ 제출, 접수번호 입력 ≠ Evidence Verified, Candidate 표시 ≠ Confirmed Requirement다. Role + Scope + State + Version + Domain Guard로 Action 표시를 판단하며 Frontend 숨김/Disabled는 Backend Authorization을 대체하지 않는다.

DATCO Workspace와 Company Workspace는 같은 Backend Domain의 서로 다른 Projection이다. 회사별 Backend를 만들지 않는다. Draft/Submitted, Candidate/Confirmed, Ready/Submitted, Submission/Evidence Verified를 구분하고 현재 Version과 사용자가 보는 Version을 함께 식별한다.

실제 URL Route, Framework/Component Library/CSS/디자인 Token/Pixel Layout, API Endpoint/HTTP Status/DB Query, Responsive Breakpoint/Native UI는 확정하지 않는다. 새로운 State/Action/Role/Permission을 추가하지 않고 94 Entity CRUD 화면·88 Action별 화면·범용 Form Builder/Wizard를 만들지 않는다.

## 2. Screen Catalog / Role / Scope

05의 Screen Group 14개를 사용하며 Logical Screen은 23개다. ID는 Traceability용으로 물리 Route가 아니다. 관련 Object는 Workspace의 Tab/Section에서 함께 표현한다. Role 약어 A=DATCO_ADMIN, O=DATCO_OPERATOR, E=COMPANY_EDITOR, P=COMPANY_APPROVER다. Role별 조회·Action은 05를 따르며 Primary Role에 표시됐다고 전체 버튼을 허용하지 않는다.

| Screen ID | Screen Group | Screen Name | Primary Role | Purpose | Main Objects | Main Actions |
| --- | --- | --- | --- | --- | --- | --- |
| SCR-DASH-01 | Dashboard | 업무 Dashboard | A/O/E/P | 현재 사용자 할 일/진행현황 | Domain 조회/Notification | 원 객체로 이동/본인 알림 읽음 |
| SCR-NOTICE-01 | Notices | 공고 목록 | A/O | 수집된 공고 탐색 | Notice/NoticeVersion | 상세/수집현황 이동 |
| SCR-NOTICE-02 | Notices | 공고 상세·Analysis Review | O, A 조회 | 원천/후보/확정요건 구분 | NoticeVersion/Source/File/Run/Requirement | 분석요청/요건 확인/Source 보완 |
| SCR-COMPANY-01 | Companies / Fact / Intake | 기업 목록 | O | 허용 기업 선택 | Company/Site | Workspace 이동 |
| SCR-COMPANY-02 | Companies / Fact / Intake | Company Workspace | O/E/P | 기업 입력/자료/업무 연결 | Company/Site/Contact/Intake/Fact/Case | 허용 입력·Upload/검토·업무 이동 |
| SCR-FACT-01 | Companies / Fact / Intake | Fact Review | O | 기존값/후보/충돌 검토 | FactCandidate/FactVersion/FactConflict/Review | 신규·기존값 확인/충돌/보완/거절 |
| SCR-IMPROVE-01 | Improvement | Improvement Workspace | O/E/P | 과제 작성/제출/검토 | ImprovementVersion/Run/Candidate/Review | 기업 제출/운영자 확인·보완 |
| SCR-CAP-01 | Capability Catalog | Capability Catalog | A/O | 전역 서비스 기준 조회/관리 | CapabilityVersion/Evidence | ADMIN Version 발행 |
| SCR-MATCH-01 | Matching / Intelligence Review | Capability Assessment·Match Review | O | 3개 축 적합성과 제약 검토 | Assessment/MatchInputSnapshot/Candidate/Review | Assessment 검토/분석요청/MatchReview |
| SCR-REQUEST-01 | Information Requests | Request / Response Workspace | O/E/P | 부족정보 요청·응답·검증 | Request/ResponseVersion/Review/Evidence | 발송/응답제출/검증/보완 |
| SCR-PROPOSAL-01 | Proposals / Approval | Proposal 작성·상세 | O/E/P | 제안내용/Version/승인이력 | ProposalVersion/MatchReview/ApprovalRequest | 운영자 새 Version/승인요청 |
| SCR-APPROVAL-01 | Proposals / Approval | 기업 Approval | P, E 공개 조회 | 지정 제안 확인/결정 | ApprovalRequest/ProposalVersion/Decision | 승인/보완요청/거절 |
| SCR-PROCEED-01 | Cases / Progress / Result | Proceed / Case 생성 | O | 추진 Gate와 Case 생성 구분 | MatchReview/Proposal/Approval/Proceed | 추진확정/Case 생성 |
| SCR-CASE-01 | Cases / Progress / Result | Case Workspace / Progress | O/E/P | Case 단계·관련업무 집계 | SupportCase/Assignment/관련 Domain | 담당 변경/하위 업무 이동 |
| SCR-APP-01 | Application Input | Dynamic Application | O/E/P | 정의 기반 입력/후보/확인 | TemplateVersion/ApplicationVersion/ValueReview | 허용 입력/값확인/전체확인/새 수정본 |
| SCR-PACKAGE-01 | Package / Confirmation | Package / Readiness | O/E/P | 제출준비 체크리스트 | PackageVersion/Application/Approval/Snapshot | 보완요청/기업확인 요청/Ready 검토 |
| SCR-PACKAGE-02 | Package / Confirmation | 기업 Package 확인 | 지정 P | 고정 Package 입력/서류 확인 | PackageVersion/ApplicationVersion/확인기록 | 기업 Package 확인 |
| SCR-SUBMIT-01 | Cases / Progress / Result | 외부 제출 / Evidence | O/E/P | 제출사실·증빙·검증 관리 | SubmissionRecord/Evidence/Review/Snapshot | 실제 제출기록/증빙등록·검증·보완 |
| SCR-RESULT-01 | Cases / Progress / Result | Evaluation / Result | O/E/P | 공식 결과와 단계 분기 | EvaluationRecord/OfficialResultRecord/CaseStage | 평가시작/공식결과 확인/허용 단계진행 |
| SCR-TASK-01 | Tasks / Schedule | Task / Schedule | O/E/P | 기한·담당·선행·완료근거 | Task/Assignment/Dependency/Deadline/Evidence | 운영자 업무배정·상태전이·완료검토 |
| SCR-OPS-01 | Operations / Users / Recovery | Collector Operations | O, A 승인된 운영 조회 | 수집 요청/실행결과 관측 | CollectionJob/Page/Attempt/결과요약 | Manual Sync/Snapshot Mode 요청/Retry |
| SCR-ADMIN-01 | Operations / Users / Recovery | ADMIN Operations | A | 사용자·권한/운영관리 | Identity/Membership/복구·이동대상 | 승인된 데이터 이동/복구검증 |
| SCR-AUDIT-01 | Audit Explorer | Audit Explorer | A/O | 허용 감사·업무 이력 추적 | AuditRecord/Actor/Object/Version | 조회/관련 객체 이동 |

DATCO 주요 Screen은 A/O Projection이 있는 21개, Company 주요 Screen은 E/P Projection이 있는 13개다. 공유 Screen은 중복 집계되지만 Logical ID는 하나다. 기업은 자기 Company/Case의 공개된 데이터만 본다. P는 승인/확인에 필요한 정보 및 공개 진행상태를 조회하며 E의 편집권한을 자동 상속하지 않는다. A의 조회/운영관리는 O 업무 Action 자동 상속이 아니다.

기업에게 독립 Notices/Matching/Catalog/Audit Explorer 메뉴는 제공하지 않는다. 전달된 공고·Match 설명은 자기 Request/Proposal/Case의 공개 Projection에서 조회한다. 내부 Draft/Review Memo/분석 근거 전체는 자동 공개하지 않는다. Company Workspace의 기업 선택은 타기업 목록이 아닌 자기 Company Context다.

## 3. 공통 UI 상태 / 저장 / Version / 결과 계약

| UI Action 상태 | 적용 |
| --- | --- |
| HIDDEN | Role에 업무 Action 없음. 객체 조회 Scope가 없으면 객체/화면 자체 미노출 |
| VISIBLE_DISABLED | Role·객체 조회권한은 있으나 State/Version/Guard 미충족, 안전한 이유/복귀 경로 표시 |
| ENABLED | 현재 조건상 요청 가능. Backend가 실행 시 재검사 |

도메인적으로 해당되지 않는 Action은 표시하지 않는다. 특히 NOT_SELECTED Case에는 START_AGREEMENT를 숨긴다. 이 예외는 OPERATOR의 단계관리 권한을 확대하거나 Backend Guard를 생략하는 뜻이 아니다. 그 외 현재 업무상 필요한 Action만 표시하고 항상 모든 버튼을 나열하지 않는다.

| 공통 Screen 상태 의미 | 표시 / 처리 |
| --- | --- |
| LOADING | 조회/요청 진행, 저장 완료로 표시하지 않음 |
| EMPTY | 조회 성공/권한범위 내 항목 없음. 실패와 구분 |
| NORMAL | Backend 조회결과와 Action 가능조건 표시 |
| PARTIAL | 확보/추출/조회 범위·누락·실패항목과 복귀 경로 표시 |
| ERROR | 안전한 실패분류/재조회·보완 경로. 기존 확정결과를 실패로 덮어쓰지 않음 |
| ACCESS_DENIED | 보호 데이터/존재 여부 없이 접근거부. 타기업 화면 잔여정보 제거 |

이는 렌더링/조회 의미이며 새로운 Domain State로 저장하지 않는다. Analysis QUEUED/PROCESSING/SUCCEEDED/PARTIAL/FAILED 기술상태와 Candidate의 Review Required/Confirmed 업무의미를 별도로 표시한다.

Save Draft는 Submit/Confirm이 아니다. Improvement/Response/Application Draft 저장은 각각 SUBMIT_IMPROVEMENT/SUBMIT_INFORMATION_RESPONSE/CONFIRM_APPLICATION과 구분한다. 입력 저장의 명명된 Backend 계약이 없는 부분은 11절 AG-01을 따른다. 성공 확인 전 “저장됨”으로 표시하지 않는다.

Notice/Fact/Improvement/Proposal/Application/Package Version과 Snapshot의 보고 있는 ID·현재 적용 대상·Lock 여부를 보여준다. HISTORICAL/STALE/SUPERSEDED는 사용자 의미 표시이며 새 enum이 아니다. 과거자료는 허용범위에서 조회하고 04 Current Usability/Action별 Guard로 현재 사용을 판별한다. 오래된 Version을 무조건 삭제하거나 모든 역사적 조회를 막지 않는다.

편집 중 Backend 대상이 바뀌면 expected Version으로 요청하고 G-VERSION 실패 시 최신 대상 안내/재조회 경로를 제공한다. 미저장 입력은 자동 덮어쓰거나 다른 Version에 자동 제출하지 않는다. 화면 전환/새 Version 선택 시 미저장 변경을 알리고 저장·폐기 의미를 구분한다. 실제 동시성 기술은 Stack 결정 후 구현한다.

Action 성공 후 Toast만 보여주지 않고 저장된 State/Version/Decision/대상 ID를 재조회한다. 비동기 요청 성공은 Job QUEUED/요청 접수이며 결과성공이 아니다. 중복 클릭은 요청 Identity와 실행중 표시로 억제하고 Backend 04 idempotency를 따른다. 응답 유실은 업무 실패로 단정하지 않고 같은 요청 결과/현재 저장상태를 확인한다. 과거 성공 반환과 지금 사용가능 여부도 구분한다.

Permission/Scope 실패는 안전한 접근거부, Invalid State는 저장상태 재조회, Version 불일치는 최신 대상 확인, Missing Information/Evidence는 보완 화면, Validation은 입력 보완, Server/Job Failure는 실행결과/허용 Retry로 안내한다. Secret/타기업 존재/원문 Stack Trace를 표시하지 않는다. 아래 Screen별 실패 경로는 이 공통 처리와 함께 적용한다.

## 4. Dashboard / Notice / Company / Intelligence 화면 계약

| Screen | 주요 Projection / 정보 | 성공 후 표시·Handoff | 실패/미완료 복귀 |
| --- | --- | --- | --- |
| SCR-DASH-01 | 오늘 업무, Review 대기, Missing Info, 응답/승인 대기, 기한임박/Overdue, Case, Impact, 증빙대기. Role별 허용 목록 | Card/Row에서 원 객체로 이동. 별도 Dashboard status 수정 없음 | 조회 실패와 EMPTY 구분, 권한 없는 Card 제거 |
| SCR-NOTICE-01 | 제목/기관/기간/현재 NoticeVersion/Source/분석·검토 요약/변경영향 | 선택한 Notice Detail, 수집은 SCR-OPS-01로 이동 | 부분수집 범위/미처리 표시, 수집성공≠요건확인 |
| SCR-NOTICE-02 | 기본정보/기간원문·파싱정보/대상·분야, API Metadata/HTML 확보/첨부·File 확보, 07 후보 8종, Source·Location·Reason·Quality, Confirmed Requirement | 확인된 RequirementVersion/Review 재조회, Template 작성에 전달 | Source 보완/분석실패·Partial/기간Conflict 표시. 부족근거를 Confirmed로 표시 금지 |
| SCR-COMPANY-01 | 허용 Company/Site/업무현황, 다른 기업은 Scope 밖 | SCR-COMPANY-02 해당 Context | Role/Scope 실패 시 기업 존재 미노출 |
| SCR-COMPANY-02 | 기본정보/Site/Contact, Intake·Upload, 공개 Confirmed Fact, 내부 Candidate·Conflict(O만), Improvement/Request/Case 연결 | 입력저장/실제 File 확보를 재조회, 검토는 SCR-FACT-01/업무별 Workspace | Upload/입력 실패 보존, 자료 제공≠Fact 확인 |
| SCR-FACT-01 | Fact Meaning/기존값·신규값/기간·단위/Source·Evidence/기존 Version/Conflict | FactReview와 새 또는 기존 FactVersion 연결, Conflict·부족정보 보존 | 단위·기간·기업 불일치/근거누락 → 원천/Request 보완 |
| SCR-IMPROVE-01 | E: 현재업무·공정/문제/목표/희망범위/설비·시스템/서술·첨부 Draft. O: 제출본/후보/근거/Missing. P: 제안 관련 공개 내용 | E 제출본 Lock·분석요청 상태, O 확인 Version/Review 또는 Revision Required | Draft 저장실패/Partial 분석 구분, 보완은 새 작업본/Version |
| SCR-CAP-01 | Service/Function/Problem/Target/조건·제외·선행/Scope/Version/Evidence | A 발행된 불변 Version 재조회. O는 SCR-MATCH-01 과제 Assessment에 연결 | 필수내용/근거누락 → 관리 Draft 보완. 기업 접근 없음 |
| SCR-MATCH-01 | Company·Improvement × Capability × Notice, Assessment·Snapshot, Eligibility/Task Fit/Service Fit/Missing/Conflict/Opposing Evidence/Reason, 입력 현재성 | Assessment Review와 MatchReview disposition 재조회. 추가정보→Request, PROPOSABLE→Proposal | Stale→현재 입력 재분석, Hard Conflict/근거부족 유지, FIT를 PROPOSABLE로 표시 금지 |

SCR-NOTICE-02/FACT/IMPROVE/MATCH의 Review는 Candidate 의미·정확한 입력 Version·Source·Evidence Location·Reason·Quality/Confidence·Missing/Conflict/Opposing Evidence·이전 확인값을 제공한다. Source를 확보했는지/추출했는지/분석했는지/사람이 확인했는지 별도로 보여준다. 높은 Confidence로 확인 버튼의 Domain Guard를 우회하지 않는다.

## 5. Request / Proposal / Approval / Proceed / Case

| Screen | 주요 Projection / 정보 | 성공 후 표시·Handoff | 실패/미완료 복귀 |
| --- | --- | --- | --- |
| SCR-REQUEST-01 | O: 항목/이유/기한/Context/회사/Draft·응답상태/ResponseVersion/Evidence/Review. E: 자기 요청/답변·파일/Draft/보완요청. P: 승인 관련 공개 요청 | 발송→WAITING_RESPONSE, 기업 제출→SUBMITTED/REVIEW_REQUIRED, 검증→VERIFIED, 보완→REVISION_REQUESTED/새 응답본 | 누락항목·자료 보완/저장상태 재조회. 응답 제출≠DATCO Verified |
| SCR-PROPOSAL-01 | Match 근거/지원과제/서비스·비용·기업부담·책임/ProposalVersion/History/Approval | 새 Version과 승인요청 재조회, 요청된 Version Lock/기업 전달범위 표시 | PROPOSABLE/정보·현재성 부족→Match/Request. 내부 Draft 기업 자동공개 없음 |
| SCR-APPROVAL-01 | 자기 Company/지정 ApprovalRequest/정확한 ProposalVersion·범위·비용·책임·공개근거/과거결정 | Decision 저장/Request CLOSED/현재 승인유효성 재조회. Revision은 O의 새 Version/Request 필요 | 다른 Company·미지정 Actor는 접근/Action 거부. Superseded·Version 불일치→현재 지정 요청 확인 |
| SCR-PROCEED-01 | MatchReview/Missing Info/ProposalVersion/현재 승인/재승인/Impact/Blocking Checklist | CONFIRM_PROCEED의 Decision과 CREATE_SUPPORT_CASE의 Case를 각각 재조회, 생성 후 SCR-CASE-01 | 미승인·Stale·Impact→해당 원 객체. 동일 Proceed 중복 Case는 기존결과 확인 |
| SCR-CASE-01 | Company/Site/적용 Notice·Proposal·Approval/Stage/담당/Application/Package/Submission/Result/Task/Timeline | 담당변경 이력 재조회, 관련 화면으로 객체·Version Context 전달 | 새 담당 Scope 불일치 차단. 조회 집계는 다른 Domain 데이터 복제저장 없음 |

COMPANY_EDITOR는 공개된 자기 Proposal/이력만 조회하고 승인버튼은 없다. COMPANY_APPROVER는 지정 Request/Version의 승인·보완요청·거절을 수행한다. DATCO는 승인 상태를 보고 요청할 수 있지만 기업 Approval을 대행하지 않는다. 기업의 Revision/Reject와 DATCO Proceed는 다른 결정이며 Approval 완료만으로 Case를 자동 생성하지 않는다.

Case Stage는 APPLICATION_PREP/SUBMISSION/EVALUATION/RESULT_CONFIRMED/AGREEMENT/EXECUTION/INSPECTION/SETTLEMENT/RECONSIDERATION/CLOSED를 사용한다. OfficialResultRecord SELECTED/NOT_SELECTED와 다른 표시 영역이다. Stage를 UI Dropdown으로 직접 수정하지 않고 기존 Action으로 전이한다.

## 6. Application / Package / Submission / Result / Task

| Screen | 주요 Projection / 정보 | 성공 후 표시·Handoff | 실패/미완료 복귀 |
| --- | --- | --- | --- |
| SCR-APP-01 | 정확한 TemplateVersion Definition의 Fields/Plan Sections/Required Documents. Auto-fill Candidate/Company Input/DATCO Input/Confirmed, Fact·Source Version/Evidence/Review 표시 | ValueReview/확인값 및 Application 상태·Lock 재조회. 수정은 새 ApplicationVersion | Template/Source Version 불일치/필수값 부족→최신 대상 검토/Request. 기업 입력≠Confirmed |
| SCR-PACKAGE-01 | Application/계획/필수·조건부서류, Company Confirmation/Proposal Approval/Missing Info/Impact/Readiness 사유/PackageVersion/Snapshot | 각 단계와 최종 READY_TO_SUBMIT/Snapshot 재조회, SCR-SUBMIT-01 연결 | 부족자료→Request/Application, 중요변경→새 PackageVersion/PREPARING, 이전 Snapshot 보존 |
| SCR-PACKAGE-02 | 지정 확인자의 자기 Case, 고정 PackageVersion/ApplicationVersion/주요입력·서류/Proposal/확인 책임 | Company Confirmation의 Actor/대상 Version/시각/결정 표시, DATCO Ready는 별도 | 05 OD-05 지정요건 미설정/Version 변경→Disabled/확인요청 재검토. E 자동확인 없음 |
| SCR-SUBMIT-01 | 유효 Ready Snapshot/외부 Portal 참조/실제 제출 Metadata·접수정보/증빙확보·Review/미등록·보완사유 | 기록→PENDING_EVIDENCE, 등록→REVIEW_REQUIRED, 검증→VERIFIED 재조회. 평가 Gate는 별도 | 증빙 없음/공식성·Snapshot 불일치→보완. 실제 제출은 보존하고 내부실패는 재조정 |
| SCR-RESULT-01 | 평가회차/공식근거/결과기록·Outcome/Case Stage/후속 Task | 평가시작·공식결과·허용 단계전이를 각각 재조회 | 증빙/선행 미충족→원업무. NOT_SELECTED는 협약 버튼 숨김, 종료/재검토만 조건부 제공 |
| SCR-TASK-01 | Task/담당/내부 due date·공식 Deadline/Dependency/완료조건/Evidence/State/History | Assignment/State/검토/완료기록 재조회, 해당 Case/근거 연결 | 선행 미완료·순환/Scope·근거 부족→조건 보완. 기업은 공개 업무/진행 조회 |

Package Lifecycle은 PREPARING → WAITING_INPUT → 보완후 PREPARING → READY_FOR_CONFIRMATION → COMPANY_CONFIRMED → READY_TO_SUBMIT 의미를 적용한다. Company Confirmation은 지정 P의 확인, MARK_PACKAGE_READY는 O의 최종 Readiness이며 서로 대신하지 않는다. 기간·서류·Template·기업확인·정확한 Proposal 승인·Impact를 Checklist에서 구분한다.

Portal 링크는 외부업무 이동이며 제출완료 버튼이 아니다. RECORD_EXTERNAL_SUBMISSION은 실제 외부제출 사실을 입력하는 별도 Action이다. REGISTER_SUBMISSION_EVIDENCE와 VERIFY_SUBMISSION_EVIDENCE를 분리하고 같은 O가 수행하더라도 별도 기록을 남긴다. 증빙 없이 신청완료/EVALUATION Gate를 통과하지 않는다. 외부 제출 성공/내부 실패는 RECONCILE_EXTERNAL_SUBMISSION으로 역사적 대상/사유를 확인하며 소급 Ready/승인 성공으로 표시하지 않는다.

선정 이후 AGREEMENT/EXECUTION/INSPECTION/SETTLEMENT/CLOSED는 04의 공식근거/선행조건 Action으로 진행한다. 미선정은 CLOSE_NOT_SELECTED/RECONSIDER_NOT_SELECTED, 공식 재평가 경로가 확인되면 RETURN_TO_EVALUATION으로 연결한다. 공식 결과 정정은 CORRECT_OFFICIAL_RESULT로 새 결과를 보존하며 Stage 자동변경이 아니다.

Task의 CREATE_TASK/ASSIGN_TASK/START_TASK/WAIT_TASK/BLOCK_TASK/RESUME_TASK/REQUEST_TASK_COMPLETION/COMPLETE_TASK/REJECT_TASK_COMPLETION/SET_TASK_DEPENDENCY/CHANGE_TASK_DUE_DATE는 현재 State·권한에 필요한 항목만 제공한다. TASK_OVERDUE/DEADLINE_APPROACHING은 시간 기반 Derived 표시이고 Domain State처럼 저장하지 않는다. Cross Case Dependency는 05 OD-08을 따라 자동허용하지 않는다.

## 7. Operations / Audit / Evidence / Impact 공통 Pattern

| Screen | 주요 Projection / 정보 | 성공 후 표시·Handoff | 실패/미완료 복귀 |
| --- | --- | --- | --- |
| SCR-OPS-01 | Source/LIVE·SNAPSHOT/시각/Page/Raw·unique ID/신규 Notice·Version/변경없음/Partial·Failed/Detail·Attachment/Attempt | 요청 QUEUED와 실제 Job 결과 분리, 저장 Notice/실패 대상 연결 | Retry 조건/입력/현재성 확인. 인증구성 실패는 Secret 없이 안내, Empty≠Error |
| SCR-ADMIN-01 | 사용자/Membership 운영범위, 승인된 이동/복구 대상/검증결과 | IMPORT_OR_EXPORT_DOMAIN_DATA/VERIFY_OPERATIONAL_RECOVERY 결과와 Audit 재조회 | 미승인 요청·Scope/Version/File/Audit 불일치→운영 검토. 관리 입력은 AG-02 |
| SCR-AUDIT-01 | Actor/Action/Object/Version/Time/Reason, A 승인된 감사범위/O 허용 업무이력 | 관련 Object/Version으로 이동 | 기업 전체 Explorer 없음, Secret/민감 Raw/타기업 정보 미노출 |

Evidence Viewer는 별도 Screen Group/Role이 아닌 공통 Pattern이다. Source Name/File/Version/Page·Section·Location/허용 Extract/Original Source Link를 표시하고 Backend File Scope를 통과해 Preview/다운로드한다. 직접 Storage URL로 권한을 우회하지 않는다. 접근 불가·미확보·미지원 Preview는 구분하고 파일 존재만으로 Evidence 검토완료라고 표시하지 않는다.

Impact는 관련 Notice/Match/Proposal/Case/Package 화면 Section으로 표시한다. 변경 전후·영향대상·이유·필요 후속조치를 보여주고 RESOLVE_IMPACT_REVIEW와 실제 REGISTER_IMPACT_FOLLOWUP을 구분한다. 관련 Run/Request/Approval/Task 화면으로 이동하며 단순 경고 제거/상태 직접 Update는 없다.

Worker START_JOB/COMPLETE_JOB/FAIL_JOB, Normalize/Parser 내부 단계, Notice import·Version 생성 내부처리, Notification 전달 내부에는 별도 Human 버튼을 만들지 않는다. Operations의 기술적 요약으로 관측한다. 사용자는 기존 요청/허용 Retry를 보낼 뿐 실행성공을 임의 선언하지 않는다.

## 8. Screen → User Action → 04 Action Traceability

아래는 핵심 Action 선별표다. 쉼표로 묶은 Action도 각각 별도 요청·결과이며 동시에 실행하는 단일 버튼을 뜻하지 않는다. 모든 행은 04의 전체 From State/Guard/Audit/idempotency와 05 Permission을 적용한다. O/A의 Scope도 허용범위이며 모든 회사 접근을 뜻하지 않는다. 05에 명시하지 않은 세부 편집·운영 권한은 자동 상속하지 않는다.

| Screen ID | User Action | 04 Action | Role | Scope | UI State Source |
| --- | --- | --- | --- | --- | --- |
| SCR-OPS-01 | 수집/명시적 Snapshot 요청 | REQUEST_COLLECTION | O | GLOBAL_DATCO | Source·Mode·입력/05·06 |
| SCR-OPS-01 | 실패 수집 재시도 | RETRY_JOB | O | 허용 수집 Job | FAILED/PARTIAL·현재 입력/06 권한 |
| SCR-NOTICE-02 | 분석 요청/요건 확인/자료 보완 | REQUEST_NOTICE_REVIEW, CONFIRM_NOTICE_REQUIREMENT, REQUEST_MORE_SOURCE_REVIEW | O | GLOBAL_DATCO | Source 확보·공식근거·입력 Version/Review |
| SCR-FACT-01 | 새값/기존값 확인 | CONFIRM_NEW_FACT_VALUE, CONFIRM_EXISTING_FACT_VALUE | O | COMPANY | 기간·단위·Evidence/기존값 비교 |
| SCR-FACT-01 | 충돌/부족정보/거절 | RECORD_FACT_CONFLICT, REQUEST_FACT_INFORMATION, REJECT_FACT_CANDIDATE | O | COMPANY | 해당 후보·Version·사유 |
| SCR-IMPROVE-01 | 제출/새 보완본 | SUBMIT_IMPROVEMENT, REVISE_IMPROVEMENT | E | 자기 COMPANY | Draft 완전성/대상 Version·수정가능 범위 |
| SCR-IMPROVE-01 | 확인/보완요청 | CONFIRM_IMPROVEMENT, REQUEST_IMPROVEMENT_REVISION | O | COMPANY | REVIEW_REQUIRED·근거·현재 입력 |
| SCR-CAP-01 | Catalog Version 발행 | PUBLISH_CAPABILITY_VERSION | A | GLOBAL_DATCO | 관리권한/완전성·Evidence |
| SCR-MATCH-01 | Assessment 검토/재평가 | REVIEW_CAPABILITY_ASSESSMENT, REASSESS_CAPABILITY | O | COMPANY | 과제·Catalog Version/현재성·근거 |
| SCR-MATCH-01 | Match 분석/Review | REQUEST_MATCH_ANALYSIS, REVIEW_MATCH | O | COMPANY | Snapshot·현재성·근거·Missing/Review disposition |
| SCR-REQUEST-01 | 요청 발송/응답 검증/보완요청 | SEND_INFORMATION_REQUEST, VERIFY_INFORMATION_RESPONSE, REQUEST_RESPONSE_REVISION | O | COMPANY/필요 CASE | 항목·기한·대상/제출본 Version·Evidence |
| SCR-REQUEST-01 | 기업 응답제출/보완본 열기 | SUBMIT_INFORMATION_RESPONSE, OPEN_RESPONSE_REVISION | E | 자기 COMPANY/CASE | 자기 Request·응답가능 State·항목/File |
| SCR-PROPOSAL-01 | 새 제안 Version/승인요청 | CREATE_PROPOSAL_VERSION, REQUEST_APPROVAL | O | COMPANY | PROPOSABLE·정보·현재성·지정 승인요건 |
| SCR-APPROVAL-01 | 승인/보완/거절 | APPROVE_PROPOSAL, REQUEST_PROPOSAL_REVISION, REJECT_PROPOSAL | 지정 P | 자기 COMPANY | 정확한 Request·Version·Actor/OPEN·사유 |
| SCR-PROCEED-01 | 추진확정 | CONFIRM_PROCEED | O | COMPANY | 현재 Match/승인조합·Missing·Impact |
| SCR-PROCEED-01 | Case 생성 | CREATE_SUPPORT_CASE | O | COMPANY→CASE | 유효 Proceed·동일 Proceed 중복 Guard |
| SCR-CASE-01 | 담당 이관 | CHANGE_CASE_ASSIGNEE | O | CASE | 새 담당 권한·Scope |
| SCR-APP-01 | Template 확인/신청본 준비 | CONFIRM_APPLICATION_TEMPLATE, CREATE_APPLICATION_VERSION, REQUEST_APPLICATION_REVIEW | O | CASE, Template 허용 맥락 | Requirement·Template·NoticeVersion/완전성 |
| SCR-APP-01 | 후보값 확인/전체확인/새 수정본 | CONFIRM_APPLICATION_VALUE, CONFIRM_APPLICATION, REVISE_APPLICATION | O | CASE | 정확한 Version/Template·Evidence·필수내용 |
| SCR-PACKAGE-01 | 부족자료 요청/준비 재개 | REQUEST_PACKAGE_INFORMATION, RESUME_PACKAGE_PREPARATION | O | CASE | PREPARING/WAITING_INPUT·대상 부족/수신자료 |
| SCR-PACKAGE-01 | 기업 확인요청 | REQUEST_COMPANY_CONFIRMATION | O | CASE | 검토된 자료·완전한 고정 대상 |
| SCR-PACKAGE-02 | 기업 Package 확인 | CONFIRM_COMPANY_PACKAGE | 지정 P | 자기 CASE | READY_FOR_CONFIRMATION·정확한 대상·05 OD-05 설정 |
| SCR-PACKAGE-01 | Ready 확정/중요변경 반영 | MARK_PACKAGE_READY, INVALIDATE_PACKAGE_READY | O | CASE | Readiness 전체/중요변경 근거·새 본 |
| SCR-SUBMIT-01 | 실제 제출기록 | RECORD_EXTERNAL_SUBMISSION | O | CASE | 실제 Metadata·유효 Ready Snapshot |
| SCR-SUBMIT-01 | 증빙 등록/검증/보완 | REGISTER_SUBMISSION_EVIDENCE, VERIFY_SUBMISSION_EVIDENCE, REQUEST_SUBMISSION_EVIDENCE_REVISION | O | CASE/FILE_EVIDENCE | 실제 File·공식근거·대상 Snapshot/Review |
| SCR-SUBMIT-01 | 외부사실/내부실패 재조정 | RECONCILE_EXTERNAL_SUBMISSION | O | CASE | 역사적 대상·사유·실제 사실, 소급 Ready 아님 |
| SCR-RESULT-01 | 평가시작/공식 결과확인 | START_EVALUATION, CONFIRM_OFFICIAL_RESULT | O | CASE | 제출 VERIFIED·선행/공식 Evidence·Version |
| SCR-RESULT-01 | 결과 정정/선정 협약 | CORRECT_OFFICIAL_RESULT, START_AGREEMENT | O | CASE | 정정 공식근거/협약은 SELECTED·선행조건 |
| SCR-RESULT-01 | 미선정 종료/재검토/재평가 | CLOSE_NOT_SELECTED, RECONSIDER_NOT_SELECTED, RETURN_TO_EVALUATION | O | CASE | NOT_SELECTED·사유/공식 재평가 근거 |
| SCR-RESULT-01 | 수행/검수/정산/종료 | START_EXECUTION, START_INSPECTION, START_SETTLEMENT, CLOSE_CASE | O | CASE | 현재 Stage·완료근거·선행조건/Impact |
| SCR-TASK-01 | 생성/배정/진행 | CREATE_TASK, ASSIGN_TASK, START_TASK | O | COMPANY/CASE | 업무·새 담당 Scope/선행조건 |
| SCR-TASK-01 | 대기/차단/재개 | WAIT_TASK, BLOCK_TASK, RESUME_TASK | O | COMPANY/CASE | 허용 State·사유/제약해소 |
| SCR-TASK-01 | 완료요청/완료검토/보완 | REQUEST_TASK_COMPLETION, COMPLETE_TASK, REJECT_TASK_COMPLETION | O | COMPANY/CASE | 진행/COMPLETION_REVIEW·근거·필수 선행 |
| SCR-TASK-01 | 선행연결/기한변경 | SET_TASK_DEPENDENCY, CHANGE_TASK_DUE_DATE | O | COMPANY/CASE | 순환·Scope/기한종류·권한·사유 |
| SCR-CASE-01 | 영향검토/실제 후속완료 연결 | RESOLVE_IMPACT_REVIEW, REGISTER_IMPACT_FOLLOWUP | O | 영향대상 COMPANY/CASE | 대상별 결정·근거/실제 완료 Version |
| SCR-ADMIN-01 | 승인된 데이터 이동/복구검증 | IMPORT_OR_EXPORT_DOMAIN_DATA, VERIFY_OPERATIONAL_RECOVERY | A | 승인된 운영범위 | Domain Guard·정합성·Audit |
| SCR-DASH-01 | 본인 알림 읽음 | ACKNOWLEDGE_NOTIFICATION | A/O/E/P | 본인 Recipient | 수신자 일치, 원업무 변경 없음 |

06의 Human 수집 요청과 07의 Candidate 생성 Worker는 분리한다. Worker REGISTER_IMPROVEMENT_CANDIDATE 등의 결과 연결은 사람이 후보 저장을 조작하는 버튼이 아니다. E의 REVISE_IMPROVEMENT는 자기 입력 수정 책임, O의 검토보완은 별도 요청 Action이며 Confirmed 본을 직접 덮어쓰지 않는다. Request Package Information과 SEND_INFORMATION_REQUEST도 초안/대상 연결과 실제 발송의 저장결과를 구분한다.

## 9. Blocking Reason / 복귀 Handoff / Deep Link

| 04 Reason | 사용자 설명 예 | 복귀 대상 |
| --- | --- | --- |
| APPROVAL_VERSION_MISMATCH | 현재 제안 Version에 대한 승인이 필요합니다 | Proposal/지정 ApprovalRequest |
| REAPPROVAL_REQUIRED | 중요변경에 대한 재승인이 필요합니다 | 새 ProposalVersion/Approval |
| REQUIRED_DOCUMENT_MISSING | 필수 제출자료가 누락되었습니다 | Application/Request/Package |
| MISSING_REQUIRED_INFORMATION | 확인이 필요한 정보가 있습니다 | Request/Fact/Match |
| UNRESOLVED_CHANGE_IMPACT | 변경영향 검토와 필요한 후속조치를 완료해야 합니다 | 관련 Impact/Run/Review/Approval/Task |
| PREREQUISITE_NOT_COMPLETED | 선행업무를 먼저 완료해야 합니다 | Task/Case 선행업무 |
| TARGET_VERSION_MISMATCH / STALE_INPUT_VERSION | 보고 있는 대상 또는 입력이 변경되었습니다 | 최신 적용 대상 선택/재검토 |
| SUBMISSION_EVIDENCE_NOT_VERIFIED | 공식 제출증빙 확인이 필요합니다 | Submission/Evidence Review |

이유는 사용자가 조회할 수 있는 업무정보만 설명한다. 타기업 존재/ID/보안설정은 이유로 노출하지 않는다. 화면 이동은 Source 화면/대상 Object/Version/Company·Case Context를 유지하고 도착 화면에서 다시 접근검사한다. Notification 클릭은 Request/Approval/Task/Impact/Case 원 객체로 이동하며 읽음 자체가 업무결정은 아니다.

Direct URL/Deep Link/검색/파일 다운로드도 Backend에서 Company/Case/File Scope를 검사한다. 타기업 식별값을 입력해도 객체/파일/이력은 DENY이며 Frontend Route Protection만으로 해결하지 않는다. 로그인/Role Context는 공통 진입 Pattern이고 새 Group/임의 Role 전환 기능이 아니다. 실제 인증 Provider와 별개로 Backend가 허용한 현재 사용자/회사/Role Context를 표시한다.

## 10. Screen → E2E / 사용자 Journey / Demo 전달

| Screen / Group | 주요 E2E Flow |
| --- | --- |
| SCR-OPS-01 / SCR-NOTICE-01 | FLOW-01~05 수집/Pagination/Notice/Version/Source, FLOW-26 Retry, FLOW-29 Snapshot |
| SCR-NOTICE-02 | FLOW-06 공고분석/Review, FLOW-32 근거 추적 |
| SCR-COMPANY-01/02 / SCR-FACT-01 | FLOW-07 기업/자료, FLOW-08 Fact 검토 |
| SCR-IMPROVE-01 | FLOW-09~10 과제 제출/분석·확인 |
| SCR-CAP-01 / SCR-MATCH-01 | FLOW-11 Catalog/Assessment, FLOW-12 MatchReview |
| SCR-REQUEST-01 | FLOW-13 요청/응답/보완/검증 |
| SCR-PROPOSAL-01 / SCR-APPROVAL-01 / SCR-PROCEED-01 | FLOW-14~17 제안/승인/재승인/추진 |
| SCR-CASE-01 | FLOW-18 Case/담당, FLOW-25 Impact/후속조치 |
| SCR-APP-01 / SCR-PACKAGE-01/02 / SCR-SUBMIT-01 | FLOW-19~21 Application/Readiness/실제 제출·증빙 |
| SCR-RESULT-01 | FLOW-22 평가/공식결과/선정·미선정 분기 |
| SCR-TASK-01 | FLOW-23 업무/기한/선행/완료근거 |
| SCR-DASH-01 | FLOW-24 알림, FLOW-30 파생 Dashboard |
| SCR-ADMIN-01 / SCR-AUDIT-01 | FLOW-28 복구, FLOW-29 승인된 이동, FLOW-32 Audit/Lineage |
| 모든 보호 화면 / Evidence Pattern | FLOW-27 타기업 차단, FLOW-31 Provider 전환 후 내부 권한·History 유지 |

DATCO 연결성 Journey: Dashboard → Collector Sync → Notice List/Detail Review → Company/Fact → Improvement Review → Capability Assessment/Matching → Request/Response 검토 → Proposal → 기업 Approval 상태 → Proceed → Case → Application → Package → Submission/Evidence → Evaluation/Result. 기업 승인은 지정 Company Actor 화면에서 별도로 수행한다.

EDITOR Journey: Dashboard → 자기 Company/자료 → Improvement Draft/Submit → Requests Draft/Submit·보완 → 허용 Application 입력 → Case Progress. APPROVER Journey: Dashboard → 지정 ApprovalRequest/ProposalVersion → 승인/보완/거절 → 필요 시 지정 Package 확인 → Case Progress. 이는 화면 연결성 검증이며 정확한 09 Demo Script가 아니다.

09에 전달할 **Demo Critical Screen Set은 19개**다: SCR-DASH-01, SCR-OPS-01, SCR-NOTICE-01/02, SCR-COMPANY-02, SCR-FACT-01, SCR-IMPROVE-01, SCR-MATCH-01, SCR-REQUEST-01, SCR-PROPOSAL-01, SCR-APPROVAL-01, SCR-PROCEED-01, SCR-CASE-01, SCR-APP-01, SCR-PACKAGE-01/02, SCR-SUBMIT-01, SCR-RESULT-01, SCR-TASK-01. Login/Role Context와 Evidence Viewer는 공통 Pattern으로 함께 확인한다. 준비된 Capability Catalog 조회는 Matching에 연결하고 Catalog 관리/ADMIN 운영/전체 Audit는 기본 Critical Set에서 제외하되 09 필요범위로 확장할 수 있다.

Demo/Seed도 같은 Screen/Role/Scope/Guard/Version/Audit를 사용한다. LIVE/SNAPSHOT/Fixture Mode와 실제 업무사실을 구분한다. Demo 전용 승인버튼/권한 bypass/DB 직접 상태조작/완성 분석결과 직접 주입 UI를 만들지 않는다. 시연순서·의미있는 Sanitized Fixture/정상·예외 범위는 09, 실행 Acceptance는 10에서 확정한 뒤 Stack/Skeleton/실제 구현으로 전환한다.

## 11. Action Gap Candidate / Open Decision

04는 중요한 Workflow Action Catalog이며 모든 Draft CRUD/파일/사용자 운영 Command가 명명되어 있지는 않다. 아래는 **추가 검토 후보**이고 새로운 Action을 확정/생성하지 않는다. 이미 03/05에서 허용한 입력·관리 책임을 Submit/Confirm 버튼으로 대체하지 않는다.

| Gap | 화면 / 빠진 명명 계약 | 기존 근거 / 처리 경계 |
| --- | --- | --- |
| AG-01 | Company/Site/Contact 입력, Intake/File Upload, Improvement/Response/Application/Proposal/Capability Draft 저장의 세부 Backend Command | 03 데이터·Draft/파일관계, 05 입력·관리권한. 명명된 04 Action 연결은 아직 없음. 구현 전 해당 저장/Upload 계약·Version Lock·권한·Audit 범위를 명시하고 필요 시 기준 변경 절차 적용. 업무 Submit/Confirm과 분리 |
| AG-02 | ADMIN 사용자/Membership 운영의 세부 Backend Command | 05 ADMIN 관리책임, 03 Identity/Membership. 실제 권한변경 계약/검사·Audit는 구현 전 확정. Role/Permission 확대를 UI 편집만으로 수행하지 않음 |

두 Gap은 입력/관리 Command 구체화 대상이며 09의 기존 E2E/Screen 정의를 막는 구조적 단절이 아니다. 실제 해당 기능 구현 전 해결해야 하며 API가 이미 존재한다고 가정하지 않는다. 05의 Package 확인자/Assignment/복수승인 등 미확정 정책은 그대로 유지한다. 이 문서는 지정 P 확인 기본안을 사용하지만 요건이 미설정이면 Disabled이고 EDITOR에게 자동권한을 주지 않는다.

| Open Decision | 후속 범위 |
| --- | --- |
| OD-01 실제 URL Route | Stack/구현 |
| OD-02 Navigation 세부 메뉴명 | 기존 14 Group 내 구현 |
| OD-03 Component Library | Stack/구현 |
| OD-04 상세 Layout | 화면 계약 내 구현 |
| OD-05 Desktop Responsive 세부 | UI 구현 |
| OD-06 Table Column 폭 | UI 구현 |
| OD-07 Modal vs Page | UI 구현 |
| OD-08 전체 Toast 문구 | 저장·실패 의미 유지하며 구현 |
| OD-09 실제 Form Widget | Template Definition/입력 타입에 따라 구현 |
| OD-10 File Preview Library | 권한·파일지원 범위 검증 후 구현 |
| OD-11 Chart 종류 | 실제 Dashboard 필요 시 구현 |
| OD-12 고급 Search/Filter | 기본 Scope 조회 유지, 필요 확인 |

핵심 Action을 수행할 Screen/Role/Object/Version/Backend 연결 및 후보·확정/승인·추진·Case/Package·Submission·Evidence 경계는 Open으로 넘기지 않는다. Field-level 디자인 전문서/Wireframe/모든 문구·Responsive 조합을 추가하지 않는다.

## 12. Validation A~Z / 완료 판단

아래는 문서상 교차검토이며 실제 Browser/API/권한 테스트 완료가 아니다. 실행 검증은 10 Acceptance에서 구체화한다.

| 검증 | 근거 | 결과 |
| --- | --- | --- |
| A DATCO/Company 역할 분리 | 2절 Catalog/Projection | 충족 |
| B Backend Source of Truth | 1/3절 저장결과 재조회 | 충족 |
| C UI가 Guard 대체 불가 | 3/9절 Backend 재검사 | 충족 |
| D Notice 후보/확정 구분 | SCR-NOTICE-02 | 충족 |
| E Fact 후보/충돌/확정 구분 | SCR-FACT-01 | 충족 |
| F Improvement Draft/Submit/Review | SCR-IMPROVE-01 | 충족 |
| G FIT/PROPOSABLE 분리 | SCR-MATCH-01 | 충족 |
| H 응답 제출/Verified 분리 | SCR-REQUEST-01 | 충족 |
| I Draft/기업 전달 Version | SCR-PROPOSAL-01 | 충족 |
| J EDITOR Approval 없음 | SCR-APPROVAL-01/05 | 충족 |
| K APPROVER 정확한 Version | 지정 Request/Actor/Version | 충족 |
| L Approval/Proceed 분리 | SCR-APPROVAL/PROCEED | 충족 |
| M Proceed/Case 생성 분리 | 별도 Action/결과 | 충족 |
| N Application 후보/확인값 | SCR-APP-01 | 충족 |
| O 기업확인/DATCO Ready 분리 | SCR-PACKAGE-01/02 | 충족 |
| P READY_TO_SUBMIT/실제 제출 | SCR-PACKAGE/SUBMIT | 충족 |
| Q Evidence 등록/검증 분리 | SCR-SUBMIT-01 | 충족 |
| R 공식 결과/Stage 분리 | SCR-RESULT/CASE | 충족 |
| S NOT_SELECTED 협약 숨김 | 3/6절 START_AGREEMENT 제한 | 충족 |
| T Overdue Derived | SCR-TASK-01 | 충족 |
| U Historical Version 식별 | 3절 Version 표시 | 충족 |
| V Stale Action 차단 | Action별 G-VERSION/G-FRESH/Current Usability | 충족 |
| W Partial/Failed≠Confirmed | 3/4절 기술·업무상태 분리 | 충족 |
| X 타기업 Direct URL 차단 | 9절 Backend Scope | 충족 |
| Y Demo 동일 권한/Guard | 10절 bypass 금지 | 충족 |
| Z Demo Screen Set 확보 | 19개 Critical Set/공통 Pattern | 충족 |

02의 주요 Flow, 04 Action 이름/From·Guard·저장결과, 05 Role/Scope·14 Navigation Group, 07 Review 정보와 교차검토했다. 상위문서와 구조적 충돌은 발견하지 않았다. 기존 Workflow 외 입력·관리 계약은 AG-01/02로 명시했고 새 Action/State/Role/Permission을 생성하지 않았다.

**09_DEMO_SCENARIO 설계 착수 가능: YES.** 핵심 E2E의 화면/Actor/Version/Action/결과·실패복귀가 연결돼 있다. 다음은 09 → 10 → 00~10 설계 Baseline 확정 → Stack/Skeleton/실제 Vertical Slice 순서이며 이번 문서에서 UI/API/DB 구현을 수행하지 않는다.

## 13. 자유입력·매칭 결과 및 전주기 동선 (Decision-002)

기존 Screen/Action/Role/Scope 및 AG-01 계약을 재사용한다. DATCO 업무 검토는 O, Catalog 발행은 A의 기존 책임이며 새 API/권한을 확정하지 않는다.

| 동선 | 기존 화면 및 표시·검증 |
| --- | --- |
| 기업 입력 | 인증된 E가 SCR-COMPANY-02 → SCR-IMPROVE-01에서 Company/Site 연결 자유서술 저장·제출. 카테고리 미선택·Catalog 밖 요구도 등록 가능. 보조정보는 선택 사항 |
| 사진·자료·원문 | 위 Workspace의 AG-01 Upload로 선택적 첨부, 파일 보안/Scope 유지. 원문·수정 Version·제출본·첨부를 구조화 후보/확인 결과와 구분. 업로드 자체를 사진 AI 확인으로 표시하지 않음 |
| 검토·보완 | O의 SCR-FACT-01/SCR-IMPROVE-01 → 기존 보완 Action 또는 SCR-REQUEST-01의 요청/응답/검증 |
| 서비스·3자 매칭 | SCR-CAP-01 → SCR-MATCH-01. 실제 CapabilityVersion/Assessment·복수 조합·조건/범위/Evidence와 해결/미해결 범위 표시. 서비스 적합과 공고 적격을 별도 표시 |
| 비성공 결과 | 미매칭 원문/사유/Review 보존. 기존 후보 의미 및 HOLD/EXCLUDE/REQUEST_MORE_INFO 등 해당 검토결과 표시. 추가정보 요청/검토 연결, 근거 없는 추천·제안 생성 없이 기존 Guard 적용 |
| 제안·승인 | SCR-PROPOSAL-01 → 지정 P의 SCR-APPROVAL-01. 수정요청·새 Version·재승인 및 과거 승인 보존, E/O의 승인 대행 없음 |
| 신청·제출 확인 | SCR-PROCEED-01 → SCR-CASE-01 → SCR-APP-01 → SCR-PACKAGE-01/02 → SCR-SUBMIT-01. 제안 승인·Application 확인·기업 Package 확인·Ready·제출/증빙 검증 구분 |
| 결과·사후관리 | SCR-RESULT-01/SCR-CASE-01 ↔ SCR-TASK-01. 선정 Case 협약·수행·검수·정산·종료 및 CLOSED Case 사후관리 Task 생성·배정·진행·완료검토·완료 이력. Case 자동 재개 없음 |

기업은 자기 Scope의 공개 Projection만 조회한다. 가상 외부 결과는 DEMO로 표시한다. 별도 최종 신청 승인 정책은 PENDING이며 기존 정의 이상의 State/권한을 만들지 않는다. AG-01 등 실제 구현 여부는 별도 확인한다.


## Proposal P01-P05 승인된 구현 증분 — 2026-10-16

Proposal AG-01: O가 expected Version과 내용을 제출하면 Root 잠금/현재 입력 Guard/권한을 확인해 새 Version·Audit를 원자 저장한다. 내용 Review는 MatchReview와 별개다. 승인요청은 현재 Version/내용 확인/지정 기업 승인자를 고정하며 새 Version에서 이전 OPEN Request를 SUPERSEDED 처리한다. Private 출력은 정확한 내용 검토본과 Version을 고정하고 서버 다운로드 Scope/digest를 검사한다.


## W1 승인된 구현 증분 — 2026-10-19 / Decision-006

실제 독립 업무 페이지는 /company 하나이며 기존 인증을 사용한다. 기업명 목록/검색/선택→기본·재무·이력/사업장/제출자료·분석/후보·Fact 검토/개선과제 탭을 제공한다. URL은 선택 Company·탭을 유지하고 새로고침 시 세션/권한을 재검사한다. 일반 사용자의 UUID 직접 입력은 필요 없다. 원본 다운로드·원문 위치·후보값·작성자/검토자/시각·과거 Version을 표시한다. 파일명은 업로드 URL 대신 헤더로 전달한다.

E는 입력·업로드·후보 사실확인·개선과제 제출/구조화본 확인, O는 허용 기업의 근거검토·Fact Review·수동 구조화/확정, ADMIN은 기존 계정에 Company 접근관계 부여를 수행한다. P의 제안서 승인 화면은 기존 /proposal이며 이번 W1에서 새 승인 동선을 개발하지 않는다. 실제 AI·자동 추천·기업문서 자동확정 화면은 제공하지 않는다.


## W0 승인된 UI Foundation 증분 — 2026-10-19 / Decision-007

사용자의 W0 명령에 따라 기존 5개 페이지를 공통 Shell·역할별 홈에 연결하고 /login을 추가했다. 실제 6개 라우트/탭·Actor·Action/API/DB·이전/다음·오류 Inventory는 reviews/W0_UI_NAVIGATION_IMPLEMENTATION.md다. 회사·사업장·과제는 이름 선택과 검증된 URL 맥락으로 전달한다. UUID 직접 조회는 고급 영역이다. 자동 추천·D~F·미구현 관리 기능은 준비 중으로 표시하며 기존 Guard를 우회하는 완료 화면을 제공하지 않는다. 기업 Editor에게 승인자 제안 메뉴를 부여하지 않는다.
