# DATCO 정부지원사업 운영체계 - Project Baseline

## 1. 문서 지위와 적용 기준

이 문서는 프로젝트 최상위 제품/시스템 기준이다. AGENTS.md는 개발자의 행동규칙이며, Architecture, Data Model, State, Permission, 화면, Collector, Intelligence, Demo/Test 문서는 이 Baseline을 구체화한다.
세부문서가 Baseline과 충돌하면 임의로 해석하지 않고 충돌, 영향범위, 선택지를 보고한다. 중요한 목표/범위 변경은 사용자 승인 후 Baseline과 Decision Log에 반영하고 구현한다. 미확정 기술사항을 임의로 확정하지 않는다.
프로젝트 기준 Root는 이 문서의 상위 docs 디렉터리와 AGENTS.md, .gitignore를 포함하는 `dongalab`이다. 상위 Git Repository Root와 구분하며 파일을 임의로 이동하지 않는다.

## 2. 프로젝트 최종 목표

기업의 현황, 기업자료, 현장문제 및 개선요구를 파악하고 DATCO 서비스/Capability와 적합한 정부지원사업을 연결하는 **DATCO 정부지원사업 운영관리 웹 애플리케이션**을 구축한다.

공고 수집 → 공고/신청서식 분석 → 기업정보 확보 → 기업 개선과제 분석 → DATCO Capability 분석 → 정부지원사업 Matching → 부족정보 확인/요청 → 기업 응답 → DATCO 검토 → 제안 → 기업 확인/승인 → DATCO 추진확정 → Support Case 생성 → 신청준비 → 정부 공식포털 제출 → 접수결과/증빙 관리 → 평가 → 선정/미선정 → 협약 → 수행 → 검수 → 정산 → 사후관리를 하나의 업무 흐름으로 관리한다. 선정/미선정 이후의 분기는 Case Life Cycle에 따른다.

## 3. 1차 목표와 실제 동작 범위

1차 목표는 대표에게 실제 브라우저에서 처음부터 끝까지 시연 가능한 독립 실행형 Standalone Web Application이다. 단순 UI Mockup이나 화면 Prototype만으로 완료하지 않는다.

- Database Persistence, File Upload/Evidence, DATCO 사용자/기업 사용자, Role/Permission, Company Scope, State Transition.
- 기업정보 입력, 기업문서 분석후보, Company Fact 검증/확정, 개선과제 분석, DATCO Capability, Notice, Matching.
- Information Request와 기업 응답, Proposal Version, Approval, Proceed Confirmation, Support Case.
- Dynamic Application, Application Package, Task/Schedule/Evidence, Audit, Error/Retry.

이 기능들이 실제로 연결되어야 하며 브라우저 새로고침 후 상태와 데이터가 유지되어야 한다. API 장애에도 검증된 Snapshot/Seed로 대표 Demo를 완료할 수 있어야 한다.

## 4. 장기 목표: DATCO DMP 연동

1차 Standalone 구현을 폐기하지 않고 DATCO DMP의 정부지원사업 운영관리 Module로 연동 또는 탑재한다.
현재 연동 불가 영역은 Local/Demo Provider를 사용하되 Domain Logic에 고착시키지 않고 Adapter/Provider 교체가 가능해야 한다.
향후 재사용 대상은 SSO/Authentication, Company Master, Site/Contact, User/Role, File, Notification, DATCO Service Master이다.
AuthProvider, CompanyProvider, FileProvider, NotificationProvider, CapabilityProvider 등의 교체 경계를 고려한다. 실제 DMP API 구조가 확인되기 전 Contract를 임의 확정하지 않는다.

## 5. 대상 사용자

| 역할 | 주요 책임과 범위 |
| --- | --- |
| DATCO_ADMIN | 기준정보, DATCO Capability, 사용자/권한, 시스템 관리 |
| DATCO_OPERATOR | 기업/자료/개선과제/Notice 검토, MatchReview, Information Request, Proposal, Approval 요청, 추진확정, Case, Application Package, Task/Evidence, 공식 제출결과, 운영현황 |
| COMPANY_EDITOR | 자기 기업 Scope에서 기업정보 입력/확인, 문서/현장자료 업로드, 개선내용, Information Request 응답, 보완자료 제출 |
| COMPANY_APPROVER | 자기 기업 Scope에서 Proposal Version·책임범위 확인, 승인/재승인, 진행상태 확인 |

이는 역할 개념이며 상세 Permission은 향후 `05_PERMISSION_UI_MATRIX.md`에서 확정한다.

## 6. 대표 Demo 기업과 재사용 원칙

동아테크놀로지를 대표 Demo 기업으로 사용한다. 확인되지 않은 기업정보는 DEMO/SEED로 명확히 표시한다.
동아테크놀로지 전용 시스템을 만들지 않는다. 기업명/ID/업종/Site/조건, 서비스, Workflow, Permission, UI Logic을 하드코딩하지 않는다.
Domain Model, DB, API, Workflow, UI는 다른 제조기업/비제조기업에서도 재사용하며 다른 기업을 등록해도 동일 Flow가 동작해야 한다.

## 7. 전체 시스템 경계

| 영역 | 책임 |
| --- | --- |
| Government Support Collector | 본 Repository 필수범위. 기업마당 API 및 향후 기관 Connector, 수집, Raw Source/Provenance, 정규화, External ID/내부 Notice, 중복방지, 변경감지, NoticeVersion, 원문/첨부, Job, Logging, Retry, 수동 동기화, 향후 Scheduler, Snapshot fallback |
| Support Intelligence | Notice/Application Form Analyzer, Enterprise Document Analyzer, Company Improvement Analyzer, DATCO Capability Analyzer, Matching Engine, Application Template/Field Mapping, Change Impact Analyzer. 결과는 검토 후보 |
| Operations Web Application | DATCO/기업 사용자용 Dashboard, Company Master/Fact Store, Enterprise Intake, Improvement Workspace, Notice Catalog, Analysis Review, Capability Catalog, Match Review, Information Request, Proposal/Approval, Dynamic Application, Application Package, Case, Task, Schedule, Evidence, Audit |
| Government Official Portal | 실제 공식 신청 사이트. DATCO 담당자가 제출하며 우리 시스템은 준비·결과·증빙을 관리 |
| DATCO DMP | 현재 미연동인 장기 Integration Target |

정부 공식포털을 우리 시스템에서 복제하지 않는다. Collector가 저장한 동일 Notice/NoticeVersion을 전체 공고, 분석, Matching에서 재사용하며 각 영역이 동일 공고를 중복수집하지 않는다.

## 8. 기업마당 API Collector 목표

기업마당 API는 주요 공고 Source 중 하나이다. Collector를 별도 선행시스템으로 가정하지 않으며 개발과 Web 연동은 핵심 필수범위이다.

기업마당 API → Connector → Raw Source → Normalize → Notice → NoticeVersion → Notice Analysis → Matching → Operations Web.

최소 요구사항은 실제 API 문서/Response 확인 후 구현, 임의 Field 가정 금지, Pagination, 수집시각, External Source ID/내부 ID 분리, 중복방지, 변경감지, Version, Attachment/Original URL, 실패 Logging, Retry, idempotent import이다.
동일 데이터를 재수집해도 중복 Notice를 생성하지 않는다. 변경은 Version과 원천으로 추적한다.
API Key는 Backend 환경변수로만 관리하며 Frontend, Source Code, Git에 노출하지 않는다.
API 정보가 충분한 영역을 불필요하게 Crawling하지 않는다. 다른 기관 Source는 전체 재작성 없이 Connector/Adapter로 추가할 수 있어야 한다.

## 9. Live API와 Demo Snapshot

실제 기업마당 API 연동은 반드시 구현한다. 동시에 외부 API/네트워크/기관 장애가 대표 Demo를 중단시키지 않도록 검증된 Sanitized Snapshot, Seed, Fixture를 지원한다.
Snapshot도 Normalize → Notice/NoticeVersion → Analysis → Match → 업무 Flow의 동일 Domain Logic을 통과한다. Collector 이후 로직을 우회하거나 화면에 가짜 결과만 넣는 Mock Demo로 대체하지 않는다.
Snapshot/Fixture는 민감정보를 제거하고 검증한 개발자산만 공유한다.

## 10. 기업정보 확보 전략

현재 DMP Company API를 사용할 수 없으므로 1차 시스템은 Demo/Seed, Manual Input, Document Extraction의 세 입력방식을 지원한다.
대상문서는 사업자등록증, 재무제표, 공장 관련 증빙, 회사소개서, 인증자료, 기타 기업증빙이다.
Upload → Extract → Candidate → Evidence 확인 → Human Review → Confirmed Company Fact를 따른다. 문서분석 결과로 공식 기업값을 자동 덮어쓰지 않는다.

## 11. Company Fact 기준

현재값 하나만 저장하지 않고 Company, Site, Field, Value, Data Type, Unit, Reference Period, As-of Date, Source Type, Source File, Source Location, Verification Status, Verified By/At, Version, Validity를 추적한다.
이는 논리적 정보 요구사항이며 물리 Schema는 이후 확정한다. 충돌 Source 값은 자동 덮어쓰지 않고 Conflict로 표시하여 사람이 판단한다.

## 12. 기업 개선과제

기업 기본정보와 현재 문제/개선목표는 별도 Domain이다.
입력에는 현재 공정/업무/운영방식, 문제점, 개선요구, 목표, 지원사업으로 수행할 내용, 현장/설비사진, Layout, 도면, Excel, PDF, 보고서, Data Sample을 수용한다.
분석은 Current State, Problem, Root/Impact, Improvement Goal, Support Task, Required Function, Missing Information을 구조화한다.

## 13. DATCO Capability

MES/QMS/DMP Label만으로 Matching하지 않는다. Capability Catalog는 Service, Function, Solvable Problem, Target, Applicable Condition, Exclusion, Prerequisite, Scope, Evidence, Version을 표현한다.
기업과제에 대한 서비스 적합성을 근거와 함께 분석한다.

## 14. 핵심 3-way Matching

기업 개선/지원과제 × DATCO Capability × 정부지원사업 Notice의 3자 관계를 분석한다.
결과는 FIT, PARTIAL_FIT, NEED_MORE_INFO, MISMATCH의 의미를 표현하며 Eligibility, Task Fit, Service Fit, Missing Information, Conflict/Opposing Evidence, Reason을 근거로 관리한다.
자동 Match는 최종 추진확정이 아니며 DATCO 운영자의 MatchReview가 필요하다.

## 15. Information Request

기업에게 처음부터 모든 자료를 요구하지 않고 현재 분석/Match/신청준비에 부족한 정보만 요청한다.
DATCO Request → 기업 확인 → 임시저장 → 정보입력/파일 → 제출 → DATCO Review → Verified 또는 Revision Requested 흐름을 지원한다.
응답의 값, 0, 없음, 모름, 추후 제출, 해당 없음을 구분한다.

## 16. Proposal / Approval / Reapproval

Proposal은 Version으로 관리한다. Proposal v1 → 기업 승인 → 사업비/범위/기업부담 등 중요변경 → Proposal v2 → Reapproval 흐름을 지원한다.
Approval은 특정 Proposal Version/Snapshot에 연결한다. v1 승인기록을 삭제하거나 덮어쓰지 않는다.

## 17. 추진확정과 Support Case

Match 후보와 실제 추진건은 구분한다.
MatchReview → Company Confirmation → DATCO Proceed Confirmation → Support Case의 정상 흐름을 따른다.
필요한 확인/승인/추진확정 조건 충족 전에는 Support Case를 생성할 수 없다. 정확한 Guard와 Action은 향후 State/Action 문서에서 구체화한다.

## 18. Support Case Life Cycle

대표 흐름은 APPLICATION_PREP → SUBMISSION → EVALUATION → RESULT_CONFIRMED이다.

- 선정: SELECTED → AGREEMENT → EXECUTION → INSPECTION → SETTLEMENT → CLOSED.
- 미선정: NOT_SELECTED → CLOSED, 또는 필요 시 NOT_SELECTED → RECONSIDERATION.

미선정 Case는 자동으로 AGREEMENT로 이동하지 않는다. 재검토 이후 경로와 세부 Transition 조건은 향후 확정한다. 전체 업무의 사후관리까지 추적 가능해야 한다.

## 19. Dynamic Application

지원사업마다 신청필드, 사업계획서, 제출서류, 조건부 항목, 평가기준이 다르므로 모든 공고를 하나의 고정 Form에 강제로 맞추지 않는다.
ApplicationTemplate, FormFieldDefinition, PlanSectionDefinition, RequiredDocumentDefinition, EvaluationCriterion, FieldMappingRule 개념을 수용한다.
Confirmed Company Fact 등을 자동채움 후보로 재사용하고 Missing Data는 Information Request로 연결한다. 자동매핑 결과도 사람이 확인한다.

## 20. Application Package

지원사업별 실제 신청준비 상태를 관리한다. 예를 들어 사업자등록증/재무제표 준비완료, 납세증명 미제출, 사업계획서 작성중, 기업확인 승인대기를 구분한다.
필수조건을 충족하지 않으면 READY_TO_SUBMIT으로 전환할 수 없다. 준비상태와 제출 Version/Snapshot을 추적한다.

## 21. 공식 신청 결과와 Evidence

정부포털 자동제출은 1차 필수범위가 아니다. DATCO 담당자가 공식포털에서 제출한다.
시스템은 제출일시, 제출자, 제출 Version, 접수번호, 접수증, Evidence를 등록하고 이후 평가/수행을 관리한다.
접수증 또는 승인된 필수 공식증빙 없이는 최종 신청완료로 변경할 수 없다.

## 22. Role / Permission / State / Scope

Action 가능 여부는 Permission + State + Data Scope로 판단한다. 권한 없음은 Action 숨김, 권한 있음/조건 미충족은 Disabled와 불가 사유 표시를 적용한다.
Backend/API도 Role/Permission/Company Scope 및 필요한 Case Scope를 검증한다. 기업 사용자는 다른 기업의 URL/API를 직접 호출해도 데이터를 볼 수 없어야 한다.
중요 객체는 단순 CRUD가 아니라 State/Transition을 사용하고 Current State, Permission, Required Data, Required Approval, Required Evidence를 검사한다. 상세 Matrix는 이후 별도 문서에서 확정한다.

## 23. Human-in-the-loop

AI/LLM/OCR/Rule 분석결과는 공식 사실이나 최종 업무결정이 아니다.
Input → Candidate → Reason/Evidence → Human Review → Confirm 원칙을 적용한다.
Company Fact, Notice Requirement, Eligibility, Match, Proposal 판단, Approval, Proceed Decision을 사람 확인 없이 자동확정하지 않는다. 분석 Source, 입력/결과와 Version을 추적한다.

## 24. Version / History / Audit

공고, Fact, Proposal, Approval, Application Package 등 중요 객체의 과거 이력을 보존하며 단순 Update로 덮어쓰지 않는다.
누가, 언제, 무엇을, 어떤 Version에서, 어떻게 변경했는지 Audit할 수 있어야 한다. 승인이 어떤 Version에 대한 것인지 보존한다.

## 25. 변경 영향관리

Notice 수정, Deadline, Company Fact, Financial Data, DATCO Capability, Proposal, 사업비, 기업부담 변경의 후속 영향을 식별한다.
Match, Proposal, Approval, Application Package, Support Case, Task를 영향 대상으로 추적하고 필요 시 Re-review/Reapproval을 생성한다. 기존 Version과 승인 이력은 보존한다.

## 26. 오류와 비동기 Analysis Job

긴 분석은 비동기 처리를 고려한다. 대표 상태는 QUEUED → PROCESSING → REVIEW_REQUIRED → CONFIRMED이며 실패는 FAILED → 오류표시 → Retry 흐름을 지원한다.
입력 Version, 분석 Version, 오류, 시도횟수, 결과를 추적한다. Retry도 사람 검토를 우회하지 않는다.
초기 DB 기반 Job Queue도 가능한 선택지이며 구체 기술은 Architecture에서 확정한다.

## 27. 논리적 Source of Truth

| 정보 | 논리적 기준 원천 |
| --- | --- |
| 정부지원사업 원천/수집 | Collector / Notice. 외부 Source와 provenance 연결 |
| Confirmed Company Fact | Operations Domain |
| Improvement / Match / Proposal / Approval / Case / Task | Operations Domain |
| 공식 신청/접수 사실 | 외부 정부 공식포털이 공식 원천. 시스템은 Evidence/Receipt 연결 관리 |
| 향후 Company Master / Auth / File | DMP 연동 이후 역할 변경 가능 |

Intelligence는 분석 후보를 제공한다. 실제 세부 데이터 소유권은 Architecture/Data Model 단계에서 확정한다.

## 28. Non-Goals

1차 필수범위에 포함하지 않는 사항:

- 정부 공식포털 재구현 및 완전 자동제출.
- 전국 모든 정부기관 Connector 완성.
- 완전 자동 적격/선정 판단 및 사람 확인 없는 자동승인.
- 실제 API 없는 상태의 가짜 DMP Contract 구현.
- 불필요한 Microservice 분해와 Kubernetes 등 대규모 운영플랫폼.
- 자동계약/결제 기능.

향후 확장 가능성은 유지한다.

## 29. 대표 Demo E2E

대표기업은 동아테크놀로지이며 확인되지 않은 정보는 DEMO로 표시한다.

기업마당 API 또는 검증 Snapshot → Collector → Notice/NoticeVersion → 전체 공고 조회 → 동아테크놀로지 선택 → 기업문서 업로드 → 기업정보 Candidate → Human Review → Company Fact → 개선과제 입력/자료 → Improvement Analysis → DATCO Capability Analysis → 3-way Matching → Missing Information → 기업 Information Request → 기업 사용자 응답 → DATCO Review → Proposal v1 → 기업 승인 → Proceed Confirmation → Support Case → Dynamic Application → Fact Mapping → Application Package → 공식포털 제출결과 입력 → 접수증 → 신청완료.

외부 제출결과와 증빙의 Demo 자료는 실제 제출 사실과 구분하여 표시한다.

## 30. 필수 예외 Demo

| 예외 | 기대 동작 |
| --- | --- |
| 수정공고 | Notice Version 변경 → 영향업무 확인 → Re-review |
| 승인 후 중요내용 변경 | Proposal v1 승인 → 중요변경 → v2 → Reapproval Required. 기존 승인 보존 |
| 접수증 없음 | 최종 신청완료 차단 |
| 기업 Scope 위반 | 다른 기업 데이터 접근 차단 |
| Analysis Failure | FAILED → 오류표시 → Retry |
| Duplicate Collection | 동일 공고 재수집 시 중복 Notice 생성 금지 |

## 31. 1차 Demo 완료 판단

Browser UI, DB Persistence, 새로고침 후 상태 유지, Collector, 중복방지, Notice Version, Company Scope, Role/Permission, File, Human Review, State Transition, Information Request, Version, Approval, Evidence, Retry, Audit, 정상/예외 E2E가 실제로 동작해야 한다.
화면에 기능이 존재하는 것만으로 완료하지 않는다. 대표 Demo가 논리적 오류 없이 처음부터 끝까지 완료되어야 하며 새 기능이 이를 깨뜨리면 완료로 판단하지 않는다.

## 32. Architecture 기본방향

초기 기본방향은 Modular Monolith이다. Collector, Intelligence, Operations, Integration, Shared/Core의 논리적 Module 경계를 유지한다.
처음부터 불필요한 Microservice로 분리하지 않으며 향후 Collector Worker/Analysis Worker 등을 독립시킬 수 있어야 한다.
구체 Framework, DB, ORM, AI Model은 이 문서에서 확정하지 않는다.

## 33. 향후 기준문서와 변경관리

이후 다음 문서를 순차적으로 작성하며 현재 존재한다고 가정하지 않는다.

1. docs/01_SYSTEM_ARCHITECTURE.md
2. docs/02_E2E_SYSTEM_FLOW.md
3. docs/03_DATA_MODEL.md
4. docs/04_STATE_ACTION_MODEL.md
5. docs/05_PERMISSION_UI_MATRIX.md
6. docs/06_BIZINFO_COLLECTOR.md
7. docs/07_INTELLIGENCE_DESIGN.md
8. docs/08_SCREEN_ACTION_SPEC.md
9. docs/09_DEMO_SCENARIO.md
10. docs/10_TEST_ACCEPTANCE.md
11. docs/11_DECISION_LOG.md

각 문서는 Baseline을 구체화한다. Baseline을 임의 변경하지 않는다. 중요한 구현결정은 관련 기준문서와 동기화하며 필요한 결정은 승인 후 Decision Log에 기록한다.

## 34. 현재 미확정 사항

Frontend Framework, Backend Framework, DB, ORM, File Storage, Queue, AI/LLM Provider, OCR, Deployment 방식, 실제 DMP API Contract, 상세 Permission Matrix, 기업마당 실제 API Field Mapping은 미확정이다.
향후 관련 기준문서 작성과 실제 API/환경 확인 후 결정한다. 현재 단계에서 임의 선택하거나 외부 시스템 구조를 추정하여 확정하지 않는다.

## 35. 보안과 협업 기준

API Key, Password, Token, 실제 .env, 기업 개인정보, 민감 원본문서, 운영 인증정보는 Git에 포함하지 않는다. 공유 환경변수 Template에는 실제 Secret을 넣지 않는다.
실제 Private 자료와 Sanitized Demo 자산을 구분하며 사용자 권한과 기업 Scope를 검증한다.
작업 전 Branch와 실제 파일 상태를 확인하고 공통 Schema/Contract/Auth/Workflow/Architecture 변경은 영향범위를 먼저 보고한다. 다른 연구원 작업을 덮어쓰지 않는다.
기능개발은 특별한 지시가 없으면 Feature Branch를 기본으로 한다. Git add/commit/push/merge 및 파괴적 작업은 AGENTS.md의 명시적 승인 규칙을 따른다.
