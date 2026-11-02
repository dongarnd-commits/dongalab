# DATCO 정부지원사업 운영체계 - Permission / UI Matrix

> 2026-10-30 MVP v1.0 범위 증분: 이번 사용자 명시 개발 지시의 완료 범위는 기업 개선요구 → 검토된 DATCO 서비스 단독/복합 구성 → 실제 지원사업 검토·3자 매칭 → 표준 제안서 DOCX/PDF 검토·수요기업 전달까지다. 아래 전주기 H01~H32·신청/선정 후 운영은 미래 확장과 과거 기준으로 보존한다. 기존 Role/State/Company Scope·CONFIRM/ACK/PROPOSABLE·승인·원본/Version Guard는 변경하지 않는다. 대표/조직의 별도 공식 승인 상태는 미확인이다. 세부 실행 계약과 신규 M01~M18 인수는 [MVP 개발 계약](mvp/MASTER_DEVELOPMENT_CONTRACT.md), [인수 기준](mvp/ACCEPTANCE.md)을 따른다.

## 1. 목적 / 적용 원칙

Role, Permission, Data Scope, Action Authorization, UI Visibility, Enabled / Disabled와 Backend Authorization의 구현 기준이다. 기준 우선순위는 [AGENTS](../AGENTS.md) → [00 Baseline](00_PROJECT_BASELINE.md) → [01 Architecture](01_SYSTEM_ARCHITECTURE.md) → [02 E2E](02_E2E_SYSTEM_FLOW.md) → [03 Data Model](03_DATA_MODEL.md) → [04 State / Action](04_STATE_ACTION_MODEL.md) → 이 문서다.

Role Permission은 **이 종류의 Action을 할 수 있는가**, Scope는 **어떤 객체에 대해 할 수 있는가**다. 실제 실행은 Permission + Company Scope + 필요한 Case/File Scope + State + Version + 추가 Domain Guard를 모두 만족해야 한다. 조회 허용은 편집/확정 권한을 뜻하지 않는다. 명시하지 않은 권한은 자동 허용하지 않는다.

실제 Auth Provider, JWT/Session, DMP SSO Contract, DB Permission Table, 정책엔진, API Route/HTTP Status, 조직 직급체계와 UI Layout/상세 Button Spec은 확정하지 않는다. 화면 상세는 후속 `08_SCREEN_ACTION_SPEC`에서 연결한다. 범용 RBAC/ABAC 엔진, 정책언어, 94 Entity CRUD 및 88 Action 전수 Role 조합은 만들지 않는다.

## 2. Role 책임

| Human Role | 책임 | 권한 경계 |
| --- | --- | --- |
| DATCO_ADMIN | 전역 기준정보/Capability Catalog, 사용자·권한 운영, 승인된 운영관리·복구 | 모든 OPERATOR Action을 자동 상속하지 않음. 기업 승인 대행 불가 |
| DATCO_OPERATOR | 기업/공고/Fact/Improvement 검토, MatchReview, Request/Proposal, Proceed, Case/Application/Package/Task, 제출 Metadata/Evidence/Result | 허용된 Company/Case 범위. 기업 응답·승인 Actor를 대신하지 않음 |
| COMPANY_EDITOR | 자기 기업 정보/자료/Improvement 입력, Request 응답·보완, 허용된 Application 입력 | 제출과 DATCO 검토/확정을 구분. Proposal 승인 불가 |
| COMPANY_APPROVER | 자기 기업의 지정 ApprovalRequest 대상 ProposalVersion 확인·승인·보완요청·거절, 관련 진행상태 확인 | Editor 편집권한 자동 상속 없음. Package 확인은 별도 지정 요건 필요 |

Role은 위 4개다. `ADMIN > OPERATOR > APPROVER > EDITOR` 같은 계층을 두지 않는다. 같은 사람이 추가 Role을 명시적으로 부여받더라도 각 Action의 실제 업무 Actor/Company/지정 요청 맥락을 검사하고 Audit한다. DATCO 자격만으로 기업 Decision을 생성할 수 없다.

## 3. Scope / 상속

| 개념 Scope | 대상 / 판정 |
| --- | --- |
| GLOBAL_DATCO | Government Notice/NoticeVersion/Source, DATCO Capability Catalog, 운영 Global Data. Global은 모든 사용자에게 공개라는 뜻이 아님 |
| COMPANY | Company/Site/Fact/Improvement, Request/Response, Proposal/Approval. 기업 Role은 신뢰된 Membership의 자기 Company만 접근 |
| CASE | SupportCase 및 Application/Package/Submission/Evaluation/Case Task. Case의 Company와 요청자의 Company 권한을 함께 검사 |
| ASSIGNMENT 기반 범위 | Case/Task 담당 관계. 기본은 업무책임 및 Dashboard 필터이며 보안 Scope와의 동일 여부는 OD-02 |
| FILE_EVIDENCE | 부모 Company/Case/Global Source 범위를 상속하고 파일 자체 공개범위도 함께 검사 |

Company → Site 및 Company/Site 관련 Fact·Improvement는 동일 Company 소속이어야 한다. SupportCase → Company, Application/ApplicationPackage/Submission → SupportCase → Company 관계를 서버에서 따라간다. 요청의 `company_id`/`case_id`만 신뢰하지 않는다. ApprovalRequest → ProposalVersion → Proposal → Company도 동일하게 검사한다.

Company Private File은 소유 Company, 공고 Source File은 Global Notice Source, 접수증은 Case → Company 범위를 따른다. 타기업 Private File을 다른 Company Application/Package/Task에 연결할 수 없다. 여러 부모 참조가 있으면 모든 연결의 Scope가 양립해야 하며 공개 부모를 추가하여 Private 범위를 넓힐 수 없다.

DATCO 역할은 업무상 여러 기업에 접근할 수 있으나 인증된 권한 Context의 허용 Company/Case 범위를 검사한다. Operator Role 또는 Assignment가 있다는 이유만으로 모든 Company/Case 접근을 부여하지 않는다. 담당 변경은 새 담당자의 업무권한/Scope를 검사하고 기존 Case/Task와 Audit를 보존한다.

## 4. Role Capability Matrix

`VIEW`는 공개 허용된 조회, `OPERATE`는 업무 Action, `REVIEW`는 검토/확정, `OWN_SCOPE_EDIT`는 자기 기업의 허용 입력, `APPROVE`는 지정 승인, `ADMIN`은 해당 관리 기능, `NO_ACCESS`는 독립 접근 없음이다. 모든 셀에 3절 Scope와 5절 Action 제한이 적용된다. 일부 기업 조회는 업무용 공개 Projection에 한정한다.

| 업무 영역 | DATCO_ADMIN | DATCO_OPERATOR | COMPANY_EDITOR | COMPANY_APPROVER |
| --- | --- | --- | --- | --- |
| Dashboard | ADMIN | VIEW | VIEW | VIEW |
| Government Notice | VIEW | REVIEW | VIEW: 전달된 공고 | VIEW: 승인 관련 공고 |
| Company | ADMIN: 사용자/Membership | OPERATE | OWN_SCOPE_EDIT | VIEW: 승인 관련 정보 |
| Company Fact | NO_ACCESS | REVIEW | OWN_SCOPE_EDIT: 입력/근거 | VIEW: 공개 근거 |
| Improvement | NO_ACCESS | REVIEW | OWN_SCOPE_EDIT | VIEW: 제안 관련 내용 |
| Capability Catalog | ADMIN | VIEW/REVIEW: 적합성 분석 | NO_ACCESS | NO_ACCESS |
| Matching | NO_ACCESS | REVIEW | VIEW: 공유 결과 | VIEW: 제안 설명 |
| Information Request | NO_ACCESS | OPERATE/REVIEW | OWN_SCOPE_EDIT | VIEW: 승인 관련 요청 |
| Proposal | NO_ACCESS | OPERATE | VIEW: 전달 Version | VIEW: 지정 Version |
| Approval | NO_ACCESS | OPERATE: 요청/이력 | VIEW: 자기 기업 이력 | APPROVE |
| Proceed | NO_ACCESS | OPERATE | VIEW: 진행상태 | VIEW: 진행상태 |
| Support Case | NO_ACCESS | OPERATE | VIEW | VIEW |
| Dynamic Application | NO_ACCESS | OPERATE/REVIEW | OWN_SCOPE_EDIT: 허용 입력 | VIEW: 확인 대상 |
| Package | NO_ACCESS | OPERATE/REVIEW | OWN_SCOPE_EDIT: 허용 자료 | VIEW/CONFIRM: 지정 시 |
| Submission | NO_ACCESS | OPERATE/REVIEW | VIEW: 공개 제출현황 | VIEW: 공개 제출현황 |
| Evaluation/Result | NO_ACCESS | REVIEW | VIEW: 공개 진행/결과 | VIEW: 공개 진행/결과 |
| Task | NO_ACCESS | OPERATE | VIEW: 기업 공개 업무 | VIEW: 관련 진행상태 |
| File/Evidence | ADMIN: 승인된 운영 범위 | OPERATE/REVIEW | OWN_SCOPE_EDIT: 제출/공개 파일 | VIEW: 확인 대상 파일 |
| Audit | ADMIN | VIEW: 허용 업무 이력 | VIEW: 업무 UI 이력 | VIEW: 승인/업무 UI 이력 |
| Operations | ADMIN | OPERATE: 수집/업무 실행요청 | NO_ACCESS | NO_ACCESS |

기업의 내부 Capability Catalog 관리, MatchReview 변경, Proceed, Official Result 확정은 금지한다. 공고 독립 탐색은 OD-09이며 전달된 공고 원천 조회와 구분한다. ADMIN의 복구/감사 접근은 승인된 운영 목적·범위에 한정하며 일상 업무 편집권한을 의미하지 않는다.

## 5. 핵심 Action Permission Matrix

04에서 선별한 Human Action 35개다. `Y`는 Role 차원의 허용이며 Scope/Guard 충족을 전제한다. `N`은 해당 Role 자격으로 실행 불가, `C`는 명시적 지정 요건이 있는 경우만 허용이다. 조건 열은 권한 구분에 필요한 요약이며 **04의 From State / 전체 Guard / Version / Audit를 그대로 적용**한다. COMPANY/CASE는 3절의 허용 범위다.

| Action | ADMIN | OPERATOR | EDITOR | APPROVER | Scope | 추가 조건 |
| --- | --- | --- | --- | --- | --- | --- |
| REQUEST_COLLECTION | N | Y | N | N | GLOBAL_DATCO | 검증된 입력/수집 실행요청; Secret 미노출 |
| REQUEST_MATCH_ANALYSIS | N | Y | N | N | COMPANY | 대상 입력 Version/분석범위 일치 |
| CONFIRM_NEW_FACT_VALUE | N | Y | N | N | COMPANY | Evidence/충돌검토, Candidate 자동확정 금지 |
| SUBMIT_IMPROVEMENT | N | N | Y | N | COMPANY | 자기 기업 입력 완전성/제출 Version 고정 |
| CONFIRM_IMPROVEMENT | N | Y | N | N | COMPANY | Human Review/현재 근거/부족정보 해소 |
| SEND_INFORMATION_REQUEST | N | Y | N | N | COMPANY/CASE | 대상·항목·사유·기한, 기업 공개 가능한 내용 |
| SUBMIT_INFORMATION_RESPONSE | N | N | Y | N | COMPANY/CASE | 자기 Request, 응답 가능 State/항목/File |
| VERIFY_INFORMATION_RESPONSE | N | Y | N | N | COMPANY/CASE | 제출본 Version/Evidence/필수항목 검토 |
| REVIEW_MATCH | N | Y | N | N | COMPANY | 현재 입력/근거; PROPOSABLE 추가 Gate |
| CREATE_PROPOSAL_VERSION | N | Y | N | N | COMPANY | PROPOSABLE/현재 입력/부족정보 해소 |
| REQUEST_APPROVAL | N | Y | N | N | COMPANY | 정확한 Version 고정/지정 기업 승인자 집합 |
| APPROVE_PROPOSAL | N | N | N | Y | COMPANY | 지정 Request/Version/Actor, OPEN/현재성/Impact |
| REQUEST_PROPOSAL_REVISION | N | N | N | Y | COMPANY | 지정 OPEN Request/Version/판단사유 |
| REJECT_PROPOSAL | N | N | N | Y | COMPANY | 지정 OPEN Request/Version/판단사유 |
| CONFIRM_PROCEED | N | Y | N | N | COMPANY | 현재 승인/MatchReview/Version/Impact 전부 충족 |
| CREATE_SUPPORT_CASE | N | Y | N | N | COMPANY→CASE | 유효 Proceed, 동일 Proceed당 최대 1 Case |
| CHANGE_CASE_ASSIGNEE | N | Y | N | N | CASE | 새 담당 Role/Company/Case 범위, Assignment Audit |
| CONFIRM_APPLICATION_VALUE | N | Y | N | N | CASE | Template/Version/Evidence; 기업 입력≠확정 |
| CONFIRM_APPLICATION | N | Y | N | N | CASE | 필수 확인값/문서/계획/현재 Template |
| REQUEST_COMPANY_CONFIRMATION | N | Y | N | N | CASE | 검토된 자료/완전한 대상 Package·ApplicationVersion |
| CONFIRM_COMPANY_PACKAGE | N | N | N | C | CASE | OD-05 기본안에 따라 지정된 확인 Actor/정확한 Version |
| MARK_PACKAGE_READY | N | Y | N | N | CASE | 기업확인/승인/자료/Template/Impact 전체 Readiness |
| RECORD_EXTERNAL_SUBMISSION | N | Y | N | N | CASE | 실제 외부제출 Metadata/유효 Ready Snapshot |
| REGISTER_SUBMISSION_EVIDENCE | N | Y | N | N | CASE/FILE_EVIDENCE | 해당 제출/공식 근거파일/Version; 검증완료 아님 |
| VERIFY_SUBMISSION_EVIDENCE | N | Y | N | N | CASE/FILE_EVIDENCE | 공식근거 Human Review, 필수 Evidence 전체 |
| START_EVALUATION | N | Y | N | N | CASE | 제출증빙 VERIFIED/단계 선행조건 |
| CONFIRM_OFFICIAL_RESULT | N | Y | N | N | CASE | 공식 결과 근거/Version/Human Review |
| CREATE_TASK | N | Y | N | N | COMPANY/CASE | 업무 대상/완료조건/Scope 명시 |
| ASSIGN_TASK | N | Y | N | N | COMPANY/CASE | 새 담당자 권한/공개범위 검증 |
| COMPLETE_TASK | N | Y | N | N | COMPANY/CASE | COMPLETION_REVIEW/완료근거/필수 선행업무 |
| RESOLVE_IMPACT_REVIEW | N | Y | N | N | COMPANY/CASE | 대상별 검토/조치 결정; 후속조치 완료와 별개 |
| PUBLISH_CAPABILITY_VERSION | Y | N | N | N | GLOBAL_DATCO | 관리권한/검토근거/불변 Version |
| VERIFY_OPERATIONAL_RECOVERY | Y | N | N | N | 승인된 운영 범위 | Domain/Version/File/Evidence/Audit 정합성 |
| IMPORT_OR_EXPORT_DOMAIN_DATA | Y | N | N | N | 승인된 대상 범위 | Domain 검증/공개범위/Guard, 업무 Gate 우회 금지 |
| CONFIRM_NOTICE_REQUIREMENT | N | Y | N | N | GLOBAL_DATCO | 공식 Source/Evidence/Version/Human Review |

표에 없는 Action은 해당 업무 책임과 04를 확인해 명시적으로 허용해야 하며, 이름의 유사성이나 VIEW로 자동 부여하지 않는다. Request 보완요청/검토는 OPERATOR, 응답 Draft/보완제출은 EDITOR 책임이다. Application 입력과 Package 자료제출은 EDITOR의 허용된 항목만으로 제한하고 DATCO 확정 Action과 분리한다.

`START_JOB`, `COMPLETE_JOB`, `FAIL_JOB`, `CREATE_NOTICE_VERSION`, `DELIVER_NOTIFICATION` 등은 System/Worker 실행이다. 별도 Human Role을 추가하지 않으며 사용자는 허용된 실행요청을 보낸다. Worker는 요청/대상 Scope 및 실행 입력을 검증하고 지정 Domain 경로를 통과한다. Human API로 Worker 성공/업무확정을 임의 선언할 수 없다. 알림 읽음은 본인 Recipient만 가능하고 업무 State를 바꾸지 않는다.

## 6. UI Visibility / 조회 공개범위

| UI 상태 | 판정 | 표현 |
| --- | --- | --- |
| HIDDEN | Role에 해당 Action 없음 | 버튼/메뉴 숨김 |
| VISIBLE_DISABLED | Action 권한과 객체 조회권한은 있으나 State/Version/추가 Guard 미충족 | 차단사유 표시 |
| ENABLED | Role + Scope + 현재 Guard 기준 요청 가능 | Backend 재검사 전제로 요청 |

객체 조회 Scope가 없으면 객체/화면/검색결과/파일 자체를 노출하지 않는다. 타기업 객체를 Disabled로 보여주거나 개수·존재 여부를 차단사유로 누설하지 않는다. Frontend 숨김, Disabled, Route 차단은 Backend 보안을 대체하지 않는다.

| 04 Blocking Reason 예 | 사용자 설명 예 |
| --- | --- |
| APPROVAL_VERSION_MISMATCH | 현재 제안 Version에 맞는 승인이 필요합니다 |
| REAPPROVAL_REQUIRED | 중요변경에 대한 재승인이 필요합니다 |
| REQUIRED_DOCUMENT_MISSING | 필수자료를 보완해야 합니다 |
| MISSING_REQUIRED_INFORMATION | 필요한 정보를 확인해야 합니다 |
| UNRESOLVED_CHANGE_IMPACT | 변경영향 검토와 필요한 후속조치를 완료해야 합니다 |
| PREREQUISITE_NOT_COMPLETED | 선행업무를 완료해야 합니다 |

기업은 실제 ApprovalRequest로 전달된 ProposalVersion을 조회한다. EDITOR는 자기 기업에 전달된 Version을 읽을 수 있지만 승인할 수 없고, APPROVER는 지정 요청/대상 Version을 판단한다. DATCO 내부 Draft는 자동 공개하지 않는다. 별도 공유 Action/시점은 08의 명시적 공개정책으로 연결하며 현재 정의되지 않은 공유 Action을 가정하지 않는다.

Matching/Intelligence 공개는 `DATCO_INTERNAL`(내부 Reason/Opposing Evidence/Review Memo), `COMPANY_SHAREABLE`(기업에 전달할 설명), `COMPANY_INPUT_REQUIRED`(응답에 필요한 항목/근거)을 구분한다. 이는 공개범위 개념이며 새 State/Role/물리 필드가 아니다. 상세 필드는 07/08에서 정한다. 기업에게 내부 분석 전체를 기본 공개하지 않는다.

## 7. Navigation Matrix

화면군 14개다. `FULL`은 해당 관리기능, `WORK`는 허용 업무, `OWN_COMPANY`는 자기 기업에 공개된 업무, `APPROVAL_ONLY`는 지정 확인/승인 대상, `NONE`은 독립 메뉴 없음이다. FULL/WORK도 Scope 제한을 받는다. 화면 접근만으로 모든 버튼을 허용하지 않는다.

| Screen Group | ADMIN | OPERATOR | EDITOR | APPROVER |
| --- | --- | --- | --- | --- |
| Dashboard | FULL | WORK | OWN_COMPANY | OWN_COMPANY |
| Notices | WORK | WORK | NONE | NONE |
| Companies / Fact / Intake | NONE | WORK | OWN_COMPANY | APPROVAL_ONLY |
| Improvement | NONE | WORK | OWN_COMPANY | APPROVAL_ONLY |
| Capability Catalog | FULL | WORK | NONE | NONE |
| Matching / Intelligence Review | NONE | WORK | NONE | NONE |
| Information Requests | NONE | WORK | OWN_COMPANY | APPROVAL_ONLY |
| Proposals / Approval | NONE | WORK | OWN_COMPANY | APPROVAL_ONLY |
| Cases / Progress / Result | NONE | WORK | OWN_COMPANY | OWN_COMPANY |
| Application Input | NONE | WORK | OWN_COMPANY | APPROVAL_ONLY |
| Package / Confirmation | NONE | WORK | OWN_COMPANY | APPROVAL_ONLY |
| Tasks / Schedule | NONE | WORK | OWN_COMPANY | OWN_COMPANY |
| Operations / Users / Recovery | FULL | WORK: 수집/실행현황 | NONE | NONE |
| Audit Explorer | FULL | WORK: 허용 업무 이력 | NONE | NONE |

기업의 전달된 공고/Match 설명은 Request·Proposal·Case의 공개 Projection에서 볼 수 있다. 기업 Tasks는 공개된 업무/진행상태 조회이며 CREATE/ASSIGN/COMPLETE 권한을 뜻하지 않는다. Admin의 Membership 관리는 Operations/Users에서 수행하고 Company 업무 조회를 자동 확대하지 않는다.

## 8. File / Evidence / Audit

파일 조회·업로드·다운로드·연결은 부모 객체 접근권한과 파일 자체 공개범위를 Backend에서 검사한다. Storage Key/URL을 안다는 이유로 접근을 허용하지 않는다. Company 사업자등록증은 COMPANY PRIVATE, 공고 첨부는 GLOBAL NOTICE SOURCE, Submission Receipt는 CASE PRIVATE의 관련 기업 공개범위를 따른다. 내부 Review Memo와 타기업 File은 기업 UI에 노출하지 않는다.

EDITOR는 자기 기업의 허용 입력/Request/Application 자료를 제출할 수 있다. 이는 공식 Submission Evidence 등록/검증 권한이 아니다. APPROVER는 지정 승인/확인 대상의 공개 근거만 조회한다. DATCO의 운영 복구 접근도 승인된 Scope를 검사하고 Audit한다.

전체 Audit Explorer는 ADMIN 관리권한, OPERATOR는 허용 업무 이력 범위다. 기업은 전체 내부 Audit를 조회하지 않고 자기 응답/요청/승인/진행 이력을 업무 UI로 제공받는다. 민감 원문/Secret을 Audit Payload에 무조건 복제하지 않는다. 다운로드와 중요한 Action은 01/04의 Audit 요구를 따른다.

## 9. Approval / Package / Submission 책임 경계

Approval Actor 후보는 자기 Company의 **COMPANY_APPROVER**다. 특정 ApprovalRequest/ProposalVersion/지정 Actor를 검사한다. EDITOR의 Proposal 승인, DATCO ADMIN/OPERATOR의 기업 Approval 대행은 금지한다. 신규 Version은 이전 승인을 자동 상속하지 않는다. 1차 Standalone 기본안은 Version당 지정 APPROVER 1명/Request 1개로 APPROVE / REVISION_REQUEST / REJECT를 시연한다. 실제 승인자 요건을 명시 설정하고, 미설정이면 승인완료를 추정하지 않는다. 복수 승인자는 별도 Request/Decision 및 필요 집합으로 확장하며 필수 구현으로 확대하지 않는다.

승인자 역할/퇴사/조직변경이 발생하면 현재 요청에 대한 실행권한을 재검사한다. 과거 Decision은 보존하고, 현재 업무에서 사용할 수 있는지는 현재 승인요건으로 판별한다. 기존 결정의 효력 변경 세부는 OD-03이며 계정 변경만으로 과거 기록을 삭제하거나 새 승인으로 만들지 않는다.

OPERATOR가 Request Draft/Send/Review/Revision Request를 수행하고 EDITOR가 자기 Request의 Response Draft/Submit/Revision Response를 수행한다. DATCO가 기업 Actor 대신 응답을 Submit했다고 기록하거나 기업이 DATCO Review 결과를 변경할 수 없다.

Package 준비/자료검토/기업확인 요청/Readiness는 OPERATOR 책임이다. 기업의 입력·자료제출과 Company Confirmation을 분리한다. 최소 기본안은 지정 COMPANY_APPROVER가 정확한 Package/ApplicationVersion을 확인하도록 하는 것이며 OD-05에서 최종 책임을 확정한다. 확인 요건/Actor가 미설정이면 Action을 차단한다. EDITOR에게 자동 확인권한을 부여하지 않는다. `MARK_PACKAGE_READY`는 별도 DATCO 판단이며 확인/승인/자료/변경영향 Gate를 모두 검사하여 Snapshot을 고정한다.

외부 공식 Portal 실제 제출은 OPERATOR 책임이다. 내부 `RECORD_EXTERNAL_SUBMISSION`은 실제 사실/Metadata, `REGISTER_SUBMISSION_EVIDENCE`는 근거 연결, `VERIFY_SUBMISSION_EVIDENCE`는 공식 근거 Human Review다. 등록만으로 VERIFIED/신청완료가 되지 않는다. 별도 사용자 분리 요구가 확인되지 않았으므로 최소 기본안은 같은 OPERATOR가 별도 Action으로 등록·검증 가능하며 기록/근거를 보존한다(OD-04). 공식 결과 확정도 OPERATOR의 공식근거 검토를 요구한다. 외부 제출 성공/내부 기록 실패는 04의 재조정 경로를 사용하고 소급 승인·준비완료로 위장하지 않는다.

## 10. Backend Enforcement / UI 연결

개념 순서는 Authentication → Object 존재/접근가능성 → Role/Permission → Company Scope → Case/File Scope → 현재 State → Version → 추가 Domain Guard → Action 실행이다. 접근가능성 확인에는 신뢰된 Scope를 사용하고 타기업 존재 여부를 응답 상세로 노출하지 않는다. 조회/목록/검색/다운로드/직접 URL/API에도 적용한다. Browser가 보낸 Role/Company/State와 UI ENABLED를 신뢰하지 않는다.

04의 `G-AUTH`, `G-COMPANY`, `G-CASE`, `G-FILE`을 재사용하며 `G-STATE`, `G-VERSION` 및 해당 Domain Guard를 검사한다. 최종 검사와 변경/감사 저장의 일관성은 Backend에서 보장한다. Guard 실패를 임의 Update로 우회하지 않는다. Idempotency는 04대로 **현재 권한/Scope → 같은 Action Identity/대상/의미의 기존 성공 조회 → 역사적 결과 반환 또는 신규 State/Version/Guard 검사**를 따른다. 과거 성공 반환과 현재 사용가능 여부는 별개다.

아래 Permission 이름은 논리 후보이며 API 상수가 아니다. UI 열의 실행 가능은 항상 현재 Guard 충족을 전제한다.

| Action | Backend Permission 후보 | Scope | UI |
| --- | --- | --- | --- |
| APPROVE_PROPOSAL | COMPANY_APPROVE | 자기 Company + 지정 Request/Version/Actor | 지정 APPROVER만 ENABLED 후보 |
| SUBMIT_INFORMATION_RESPONSE | COMPANY_RESPONSE_SUBMIT | 자기 Company + 응답 대상 Request | EDITOR만 ENABLED 후보 |
| REVIEW_MATCH | DATCO_MATCH_REVIEW | 허용 Company/현재 Match | OPERATOR만 ENABLED 후보 |
| CONFIRM_PROCEED | DATCO_PROCEED | 허용 Company/정확한 승인조합 | OPERATOR, 승인/Impact 부족 시 Disabled |
| CONFIRM_COMPANY_PACKAGE | COMPANY_PACKAGE_CONFIRM | 자기 Case/정확한 Version/지정 확인자 | 지정 APPROVER, 미설정 시 Disabled |
| MARK_PACKAGE_READY | DATCO_PACKAGE_READINESS | 허용 Case/Company/현재 Package | OPERATOR, 자료/승인 부족 시 Disabled |
| VERIFY_SUBMISSION_EVIDENCE | DATCO_SUBMISSION_VERIFY | 허용 Case/Submission/File | OPERATOR, 공식근거 부족 시 Disabled |
| PUBLISH_CAPABILITY_VERSION | CAPABILITY_MANAGE | Global Catalog | ADMIN만 ENABLED 후보 |
| IMPORT_OR_EXPORT_DOMAIN_DATA | DOMAIN_DATA_OPERATE | 승인된 대상/공개범위 | ADMIN, 미승인 요청은 Disabled |

핵심 금지: 기업의 타기업 접근, 권한 없는 File 접근/연결, EDITOR 승인, 기업 MatchReview 변경/Proceed/Official Result 확정, DATCO의 기업 Approval 대행, Frontend만의 보안, State/Version Guard 우회, Demo bypass.

## 11. Demo / DMP

Demo/Seed도 실제 Role/Scope/Guard/Version/Audit 경로를 통과한다. 권한검사 생략, 특정 `company_id` 하드코딩, 승인 자동완료, 숨겨진 Admin bypass를 두지 않는다. 시연 기업 승인 이력은 실제 지정 기업 승인 Actor로 남긴다. 최소 Demo는 EDITOR 입력/응답 → OPERATOR 검토/제안/요청 → 지정 APPROVER 결정 → OPERATOR Proceed/Case/Package/제출증빙 경로다.

DMP User / Role / Company Mapping → 내부 UserIdentity / Membership / Permission Context로 Adapter에서 변환한다. 03의 CompanyMembership 및 Provider 식별 매핑을 사용하고 Domain Permission 의미/Company·Case 격리/과거 Actor·Version·Evidence 참조를 유지한다. 실제 DMP Role 명칭, Claim/API/Token/SSO 계약은 추정하지 않는다. 교체 시 데이터 소유권/이관과 권한 의미를 실제 계약으로 검증한다.

## 12. Permission Validation A~P

아래는 **문서상 정합성 검토**다. 실제 Auth/API/UI 구현의 실행 테스트가 아니며 후속 10 검증에서 직접 URL/API/파일 접근 및 정상·실패 Action을 재현해야 한다.

| 검증 | 문서 근거 | 결과 |
| --- | --- | --- |
| A EDITOR 자기 기업만 | 3절 Company/Case 관계, Backend Scope | 충족 |
| B EDITOR Proposal 승인 불가 | 5절 Approval 3 Action N | 충족 |
| C APPROVER 정확한 자기 Request | 지정 Company/Request/Version/Actor | 충족 |
| D APPROVER MatchReview 변경 불가 | REVIEW_MATCH N | 충족 |
| E OPERATOR 기업 승인 대행 불가 | Approval 요청과 Decision 분리 | 충족 |
| F OPERATOR Proceed/Case 가능 | CONFIRM_PROCEED/CREATE_SUPPORT_CASE Y + Guard | 충족 |
| G 기업 Capability 관리 불가 | Catalog NO_ACCESS/Publish N | 충족 |
| H 타기업 Private File 차단 | 부모 Scope + 파일 공개범위/연결검사 | 충족 |
| I Global Source/Private 구분 | 3/8절 Source와 Company/Case 파일 구분 | 충족 |
| J Case/Application/Package Company 유지 | Case→Company 서버 관계검사 | 충족 |
| K UI가 Backend 대체 불가 | 6/10절 모든 보호 접근 재검사 | 충족 |
| L 내부 Draft 자동공개 금지 | 실제 전달된 Version만 기업 조회 | 충족 |
| M 기업확인/DATCO Ready 분리 | 별도 Actor/Action/Version/Readiness | 충족: OD-05 지정 필요 |
| N Evidence 등록/검증 분리 | Register≠Verify≠공식 결과 | 충족 |
| O Demo 동일 Permission 경로 | 11절 bypass 금지 | 충족 |
| P DMP 의미 유지 | 내부 Permission Context/Adapter 교체 | 정의: 실제 계약 검증 후 구현 |

04의 핵심 Approval/Proceed/Case/Request/Application/Package/Submission/Result/Task Action 이름·실행주체·Guard를 교차검토했다. System/Worker Action과 Human Matrix를 분리했으며 상위문서의 State/Entity/Flow를 변경하지 않는다.

## 13. Open Decision / 최소 기본안

아래 기본안은 1차 Standalone 설계의 최소 출발점이다. 미확정 조직/외부계약을 영구 정책으로 확정하지 않는다. 지정 요건이 필요한 Action은 실제 설정 없이 성공 처리하지 않는다.

| ID | 미확정 사항 | 최소 기본안 / 후속 확인 |
| --- | --- | --- |
| OD-01 | ADMIN의 OPERATOR 권한 상속 | 자동 상속 없음. 필요 시 OPERATOR 별도 명시 부여; 사용자/권한 운영정책 확인 |
| OD-02 | Assignment가 보안 Scope인가 | 업무책임/기본 Dashboard 필터. 허용 Company/Case Scope는 별도 검사; 전체 Case 자동허용 금지 |
| OD-03 | 복수 승인자/역할변경 시 기존 Decision 효력 | 지정 APPROVER 1명/Version 기본안. 복수 필요집합 및 역할변경 후 효력은 실제 요구 확인, 과거기록 보존 |
| OD-04 | Evidence 등록·검증자 분리 의무 | 동일 OPERATOR의 별도 등록/검토 Action 허용 기본안. 실제 내부통제 요구 시 분리 |
| OD-05 | Package Company Confirmation Actor | 지정 COMPANY_APPROVER 권장. 자기 Case/정확한 Version/지정요건 검사; EDITOR 자동권한 없음. 최종 책임은 업무정책 확인 |
| OD-06 | DMP Role/Company Mapping | Local Permission Context 유지, 실제 계약 확인 후 Adapter 매핑 |
| OD-07 | Notification 관리/재전송 권한 | 본인 Recipient 읽음과 System 전달만 기본. 전체 관리·재전송 Human 권한은 별도 확인 |
| OD-08 | Cross Case Task/Dependency 권한 | 동일 Case 또는 명시된 Company 업무 기본. Cross Case 생성·연결 자동허용 없음; 필요 시 양쪽 Case/Company 권한·순환검사 정책 확인 |
| OD-09 | 기업의 독립 공고 탐색/별도 Proposal 공유 시점 | 전달된 업무의 공고/Version만 조회. 독립 탐색/별도 공유 Action은 08 제품요구 확인 |

상위문서와 충돌한 항목은 없다. Open Decision은 권한을 무제한 확대하는 근거가 아니다. **06_BIZINFO_COLLECTOR 상세설계 착수 가능: YES.** 수집 요청 Human 권한/Global Source 경계와 Worker 분리가 정의되어 있고 남은 조직·공개정책은 Collector 상세설계를 막지 않는다.


## Proposal P01-P05 승인된 구현 증분 — 2026-10-16

P01-P05 구현은 기존 O의 생성/작성/내용검토/승인요청과 지정 P의 Version별 APPROVE/REVISION_REQUEST/REJECT를 적용한다. 운영 Company Provider 미연결은 503으로 차단한다. 내부 MatchReview Memo/전체 Manifest는 기업 Projection/출력에 자동 공개하지 않는다. 기업은 지정 승인 대상과 공개 제안내용·근거 식별자만 조회한다.


## W1 승인된 구현 증분 — 2026-10-19 / Decision-006

새 Role은 없다. COMPANY_EDITOR는 새 Company 등록 시 자기 Membership만 만들 수 있고 기존 타기업에 자체 가입할 수 없다. DATCO_ADMIN은 기존 계정에 명시적 Company Membership만 부여한다. 이 최소 물리 구현은 ADMIN의 Operator/기업 승인권한 상속을 의미하지 않는다. DATCO_OPERATOR의 조회·분석·Fact/Improvement Review는 해당 Company Membership이 필요하다. COMPANY_APPROVER는 Editor 권한을 상속하지 않는다. 파일 다운로드에서도 서버 인증·Company Scope·digest를 검사한다. Membership 회수·수명주기·복수 승인자 운영정책은 이번 구현에 추가하지 않는다.

## PR14 v1.4 명시 승인된 제한 예외 (2026-10-22)

이 절은 상단 COMPANY_EDITOR의 일반 Proposal 승인 불가 원칙에 대한 명시적·제한적 증분이다. [사용자 승인](reviews/PR14_V14_CONTRACT_APPROVAL.md) D에 따라 COMPANY_RECORDED_AUTHORIZATION 요청의 정확히 지정된 같은 기업 COMPANY_EDITOR만 그 ProposalVersion의 내부 승인 근거를 기록·전송할 수 있다. 일반 Membership만으로 승인자 권한을 주지 않으며 DIRECT_APPROVER 요청에는 기존 지정 COMPANY_APPROVER만 결정한다. DATCO_ADMIN/OPERATOR의 기업 승인 대행은 계속 금지한다. 승인권자와 시스템 기록자는 구분하며 후자의 근거 기록은 전자의 전자서명이 아니다.

기업 공개 조회는 실제 발송된 같은 Company의 정확한 ProposalVersion/문서에 한한다. 미발송 Draft, 내부 Review/전체 Manifest/비공개 기업 Fact 원문을 공개하지 않는다. Editor 공개 조회와 승인 근거 기록 권한을 구분하며 지정되지 않은 Editor의 승인/수정요청은 차단한다. File 교체·취소는 같은 Company Editor의 현재 등록에만 적용하고, 원본/Evidence/과거 승인·제출 참조는 계속 보존한다. 보완 요청 발송·검증은 Scoped Operator, 응답은 같은 Company Editor다. 자동 Company Access 부여는 없다.


## Slice 2 승인된 로컬 분석·영속 요청 초안 — 2026-10-28

새 Role은 없다. 분석 입력/Job/결과/검토는 DATCO_OPERATOR와 기존 Company Membership을 요구한다. 자료는 해당 기업의 공통자료 또는 선택 사업장으로 제한한다. 분석 초안은 생성 운영자만 조회·수정·발송한다. 기업에는 내부 후보·검토·미발송 초안을 공개하지 않는다. 최종 발송 후 기존 정보요청·응답·검토 권한을 유지한다.


## Slice 2 운영자 UX·제출본 검토 이력 — 2026-10-28

submission-reviews GET/POST는 기존 DATCO_OPERATOR+Company membership만 허용한다. 권한 있는 운영자는 같은 제출본 이력을 공유한다. POST는 정확한 제출 Version·최신 Run·Job Attempt·소유 Draft와 expected ordinal/idempotency를 검사한다. 초안 소유권 및 최종 발송 Guard는 유지한다. 신규 Role/Permission은 없다.

상세 계약·변경 영향·실행 검증 구분: [운영자 UX 구현 보고](reviews/SLICE2_OPERATOR_UX_REPORT.md).
