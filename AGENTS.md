# AGENTS.md
# DATCO 정부지원사업 운영체계 개발 규칙

## 1. 최우선 원칙

이 Repository의 개발자는 사람과 AI(Codex)를 포함하여
항상 Repository 내부의 기준문서를 우선한다.

작업 시작 전 반드시 다음 문서를 확인한다.

1. AGENTS.md
2. docs/00_PROJECT_BASELINE.md
3. 현재 작업과 관련된 docs 하위 설계문서

기준문서와 현재 코드가 충돌하는 경우
임의로 기준을 변경하거나 코드를 우선하지 않는다.

충돌사항, 원인, 가능한 선택지를 먼저 보고한다.


## 2. 프로젝트 목표

1차 목표는 브라우저에서 처음부터 끝까지
오류 없이 시연 가능한
DATCO 정부지원사업 운영관리 웹 애플리케이션을 구축하는 것이다.

최종 목표는 해당 시스템을
DATCO DMP 플랫폼의 정부지원사업 운영관리 모듈로
연동 또는 탑재하는 것이다.


## 3. 임의 변경 금지

다음 항목은 PM의 명시적인 결정 없이 임의 변경하지 않는다.

- 시스템 경계
- 핵심 Domain Entity
- State Machine
- Role / Permission 구조
- E2E 업무 Flow
- 외부 시스템 역할
- DMP Adapter 전략
- Demo Acceptance 기준
- Source of Truth
- API/Integration Contract

기준 변경이 필요한 경우 먼저 변경 이유와 영향범위를 보고한다.


## 4. 특정 기업 하드코딩 금지

동아테크놀로지는 대표 Demo 기업이다.

시스템 전체를 동아테크놀로지 전용으로 구현하지 않는다.

기업명, 기업 ID, 업종, 조건 등을 코드에 고정하지 않는다.

모든 기능은 다른 제조기업 및 비제조기업에도
동일한 데이터모델과 업무 Flow로 적용 가능해야 한다.


## 5. 정부지원사업 수집 원칙

기업마당 API 등 외부 공고 Source를 통해
정부지원사업 공고를 수집한다.

수집 영역과 운영관리 영역은 논리적으로 분리한다.

수집 영역의 주요 책임:

- 공고 확보
- 원문/첨부 확보
- Source 정보
- 구조화
- 중복방지
- 변경감지
- 버전관리
- 수집 Job / Retry

운영관리 영역의 주요 책임:

- 기업별 분석
- 개선과제
- DATCO Capability
- Matching
- 정보요청
- 제안
- 승인
- 추진확정
- Application Package
- Support Case
- Task / Schedule / Evidence

동일 공고를 불필요하게 여러 모듈에서 중복수집하지 않는다.


## 6. AI / 분석 결과 원칙

AI 또는 Rule Engine 분석결과는
자동으로 공식 사실이나 최종 업무판정으로 확정하지 않는다.

기본 원칙:

입력
→ 분석 후보
→ 근거 표시
→ 사람 검토
→ 확정

다음 항목은 원천과 버전을 추적할 수 있어야 한다.

- 기업 Fact
- 공고 Requirement
- 개선과제 분석
- DATCO Capability 분석
- Match 결과
- Proposal
- Approval
- Application Package


## 7. 권한 원칙

권한은 UI에서 버튼만 숨기는 방식으로 구현하지 않는다.

Backend/API에서도 반드시 검사한다.

최소 검증요소:

- Role
- Permission
- State
- Company Scope
- Case Scope

다른 기업의 데이터는 URL 또는 API를 직접 호출하더라도
접근할 수 없어야 한다.


## 8. State Machine 원칙

중요 업무객체는 단순 CRUD로 처리하지 않는다.

State와 Transition Condition을 정의한다.

버튼 클릭만으로 상태가 변경되지 않으며
다음 조건을 검사한다.

- 실행 권한
- 현재 State
- 필수 입력
- 필수 승인
- 필수 증빙

과거 상태와 이력을 임의로 덮어쓰지 않는다.


## 9. 승인 / 버전 원칙

Proposal, Approval, Application Package 등
중요 업무데이터는 Version 또는 Snapshot 기준으로 관리한다.

승인 이후 중요내용이 변경되면
기존 승인기록을 삭제하거나 덮어쓰지 않는다.

새 버전을 생성하고 필요 시 재승인을 요구한다.


## 10. 공식 정부포털 원칙

정부지원사업 공식 신청 사이트를 새로 구현하지 않는다.

실제 신청/제출은 DATCO 직원이 공식 정부포털에서 수행한다.

시스템에는 다음 결과와 증빙을 관리한다.

- 제출일시
- 제출자
- 제출 Version
- 접수번호
- 접수증 또는 공식 증빙

필수 공식 증빙이 없는 상태에서
신청완료로 처리하지 않는다.


## 11. DMP 연동 원칙

현재 DMP API/SSO 등을 사용할 수 없는 경우
Standalone Demo 기능으로 구현한다.

단 Domain Logic을 DMP 구현에 직접 종속시키지 않는다.

향후 다음 Provider를 교체 가능하게 설계한다.

- AuthProvider
- CompanyProvider
- FileProvider
- NotificationProvider
- CapabilityProvider

현재 Local/Demo 구현을
향후 DMP Provider로 교체할 수 있어야 한다.


## 12. Secret / 개인정보 보호

다음 값은 Git에 Commit하지 않는다.

- API Key
- Password
- Token
- .env 실제값
- 실제 기업 개인정보
- 민감한 원본 기업문서
- 운영용 인증정보

공유가 필요한 환경변수 구조는 `.env.example`에
값 없이 이름만 기록한다.


## 13. 개발 방식

한 번에 대규모 변경하지 않는다.

기본 개발순서:

기준 확인
→ 영향범위 확인
→ 작은 단위 구현
→ Test
→ 결과 검증
→ Commit
→ 다음 단계

기존 코드는 분석 없이 전면 재작성하지 않는다.

재사용 가능 여부를 먼저 확인한다.


## 14. 테스트 원칙

기능 추가 또는 수정 후 관련 테스트를 수행한다.

실패한 테스트를 무시하고 다음 단계로 진행하지 않는다.

대표 Demo E2E Flow가 깨지는 변경은 허용하지 않는다.

특히 다음을 검증한다.

- 기업 Scope
- Role / Permission
- State Transition
- 승인 Version
- 필수 증빙
- 중복수집
- 변경영향
- Retry
- 새로고침 후 데이터 유지


## 15. Codex 작업 규칙

Codex는 작업 시작 시 현재 Branch와 기준문서를 먼저 확인한다.

Codex는 다음 경우 임의 구현하지 않고 보고한다.

- 요구사항 불명확
- 기준문서 간 충돌
- 기준문서와 코드 충돌
- Schema 변경 필요
- 공통 Contract 변경 필요
- 다른 Module의 구조변경 필요

본인의 작업범위를 넘는 변경은 최소화한다.


## 16. 기준문서 변경

docs 아래 기준문서는 단순 참고문서가 아니다.

시스템 구현 기준이다.

개발 중 새로운 Architecture 또는 업무결정이 발생하면
관련 기준문서와 Decision Log를 함께 갱신한다.

코드만 변경하고 기준문서를 방치하지 않는다.

## 17. 기준문서 지위와 문서 체계

AGENTS.md는 사람 개발자와 Codex가 공통으로 따르는 최상위 개발 행동규칙이다.
작업 시작 전 이 파일을 가장 먼저 읽고, 이후 실제로 존재하는 Project Baseline과 관련 설계문서를 읽는다.
Repository 기준문서는 일시적인 채팅 지시보다 우선한다. 단, 사용자가 명시적으로 기준 변경을 승인하면 기준문서를 먼저 또는 함께 갱신한다.
요구사항이 불명확하거나 코드와 기준문서가 충돌하면 추측하여 구현하지 않고 충돌사항, 원인, 영향범위, 선택지를 먼저 보고한다.
확인되지 않은 외부 시스템/API 구조를 가정하지 않는다.

향후 문서 체계:

1. AGENTS.md
2. docs/00_PROJECT_BASELINE.md
3. docs/01_SYSTEM_ARCHITECTURE.md
4. docs/02_E2E_SYSTEM_FLOW.md
5. docs/03_DATA_MODEL.md
6. docs/04_STATE_ACTION_MODEL.md
7. docs/05_PERMISSION_UI_MATRIX.md
8. docs/06_BIZINFO_COLLECTOR.md
9. docs/07_INTELLIGENCE_DESIGN.md
10. docs/08_SCREEN_ACTION_SPEC.md
11. docs/09_DEMO_SCENARIO.md
12. docs/10_TEST_ACCEPTANCE.md
13. docs/11_DECISION_LOG.md

아직 없는 문서나 구현은 있다고 가정하지 않는다. 필요한 기준이 문서화되지 않았다면 `기준 미확정` 또는 `의사결정 필요`로 보고한다.

## 18. 전체 목표와 1차 시연 기준

최종 목표는 기업 현황, 기업자료, 현장문제, 개선요구를 파악하고 DATCO 서비스/Capability 및 적합한 정부지원사업을 연결하는 DATCO 정부지원사업 운영관리 웹 애플리케이션이다.

정부지원사업 공고 수집 → 공고/신청서식 분석 → 기업정보 확보 → 기업 개선과제 분석 → DATCO Capability 분석 → Matching → 부족정보 요청 → 기업 응답 → 제안 → 기업 확인/승인 → DATCO 추진확정 → Support Case → 신청준비 → 정부 공식포털 제출 → 접수결과/증빙 → 평가 → 선정/미선정 → 협약 → 수행 → 검수 → 정산 → 사후관리를 연결한다.

1차 목표는 실제 브라우저에서 E2E 시연 가능한 Standalone Web Application이다.
DB Persistence, File, Role/Permission, Company Scope, State Machine, Analysis, Information Request, Proposal Version, Approval, Application Package, Support Case, Task/Evidence, Audit, Error/Retry가 실제로 연결되어야 한다.
새로고침 후에도 상태가 유지되어야 한다. 단순 UI Mockup으로 완료하지 않는다.
장기 목표는 Standalone 구현을 폐기하지 않고 DATCO DMP의 운영관리 Module로 연동 또는 탑재하는 것이다.

## 19. 기업마당 API Collector 필수 개발범위

기업마당 API 기반 Collector 개발과 운영관리 시스템 연동은 이 Repository의 핵심 필수 개발범위이다. 별도 선행시스템으로 가정하지 않는다.

기업마당 API → Collector → Raw/Source provenance → Normalize → Notice → NoticeVersion → Notice/Form Analysis → Matching → Operations Web을 연결한다.

Collector는 다음 책임을 수용한다.

- 기업마당 API Connector와 API Key Backend 환경변수 관리
- Pagination, 수집 실행/수집일시, Raw Source 추적, 공고 정규화
- External ID / Internal ID 분리, 중복방지, Notice / NoticeVersion, 변경감지
- 원문/첨부 연결, 수집 Job, Logging, Retry, 수동 동기화, 향후 Scheduler
- Demo Snapshot fallback

실제 Field, Response 구조, 제약사항은 구현 전에 실제 API 문서/응답으로 확인하며 임의로 가정하지 않는다.
API Key는 Frontend, Source Code, Git에 노출하지 않는다.
Collector, Web, Intelligence가 동일 공고를 각각 다시 수집하지 않는다. 저장한 동일 Notice/NoticeVersion을 전체 공고 화면, 분석, Matching에서 재사용한다.
API 정보가 충분한 영역은 불필요하게 별도 Crawling하지 않는다.
다른 공공기관 Source는 Collector 전체 재작성 없이 Connector/Adapter로 확장 가능해야 한다.

## 20. 논리적 시스템 경계와 Architecture

- Government Support Collector: 공고 확보, 정규화, 버전, 변경감지, 원천추적.
- Support Intelligence: Notice/Form Analyzer, Enterprise Document Analyzer, Company Improvement Analyzer, DATCO Capability Analyzer, Matching Engine, Application Template/Field Mapping, Change Impact Analyzer.
- Operations Web: DATCO Admin/Operator 및 Company User UI, Company/Fact, Improvement Workspace, Notice, Analysis/Match Review, Information Request, Proposal/Approval, Dynamic Application, Application Package, Support Case, Task/Schedule/Evidence, Dashboard, Audit.
- Government Official Portal: 실제 공식 신청/제출 사이트이며 우리 시스템에서 복제하지 않는다.
- DMP: 향후 SSO, Company, User, File, Notification, Service Master 연동 대상.

초기 구현은 Modular Monolith를 우선하며 불필요한 초기 Microservice 분리를 하지 않는다.
Collector, Intelligence, Operations, Integration, Shared/Core의 논리적 Module 경계를 유지한다.
향후 Collector Worker, Analysis Worker를 분리할 수 있어야 한다.
Stack 미확정 상태에서 임의 기술 선택이나 대규모 초기화를 하지 않는다.

## 21. Company Fact와 사람 검토

초기 기업정보 입력은 Demo/Seed, Manual Input, Document Extraction을 허용한다.
기업문서 분석결과는 Upload → Extract → Candidate → Source/Evidence 확인 → Human Review → Confirmed Company Fact 절차를 따른다.
Company Fact는 Source, Source File, Source Location, Reference Period/Date, Unit, Verification Status, Verified By, Version을 추적하며 충돌값을 자동 덮어쓰지 않는다.
AI/LLM/OCR/Rule Engine/Extraction 결과는 최종 업무 사실이 아니다.
Company Fact, Notice Requirement, Eligibility, Match, Proposal, Approval, Proceed Decision을 사람 확인 없이 자동확정하지 않는다. 분석 입력/결과/버전을 추적한다.

## 22. Improvement / Capability / Matching

기업 개선과제는 기업 기본정보와 별도의 Domain이다.
현황, 문제, 개선목표, 현장사진, Layout, 문서, Excel 등으로부터 개선/지원과제를 구조화할 수 있어야 한다.
Capability는 단순 MES/QMS 문자열 목록이 아니라 Service, Function, Solvable Problem, Target, Applicable Condition, Exclusion, Prerequisite, Scope, Evidence, Version을 수용한다.
Matching은 기업 개선/지원과제 × DATCO Capability × 정부지원사업 Notice를 연결한다.
자동 Match는 최종 추진결정이 아니다. FIT / PARTIAL_FIT / NEED_MORE_INFO / MISMATCH 등의 상태와 판단근거를 관리한다.
특정 기업의 Site, Support Program, DATCO Service, Workflow, Permission, UI Logic도 하드코딩하지 않는다.

## 23. Role / Action / State 보완

최소 Role 개념은 DATCO_ADMIN, DATCO_OPERATOR, COMPANY_EDITOR, COMPANY_APPROVER이며 정확한 Permission은 향후 Permission 문서에서 확정한다.
Action은 Permission + State + Data Scope로 판단한다.
권한이 없으면 버튼/Action을 숨기고, 권한이 있으나 현재 조건 미충족이면 Disabled와 불가 사유를 표시한다. Backend/API 검사도 반드시 수행한다.
Improvement, Analysis Job, Notice Analysis, Match, Information Request, Proposal, Approval, Application Package, Support Case, Task, Evidence는 State/Transition 개념을 사용한다.
승인은 누가 언제 어떤 Version을 승인했는지 Audit 가능해야 한다.

## 24. Dynamic Application과 변경영향

모든 공고를 하나의 고정 Form에 강제로 맞추지 않는다.
ApplicationTemplate, FormFieldDefinition, PlanSectionDefinition, RequiredDocumentDefinition, EvaluationCriterion, FieldMappingRule을 수용한다.
Confirmed Company Fact는 자동입력 후보로 재사용하고 없는 정보는 Information Request로 연결한다. 자동매핑도 사람의 확인을 거친다.
공식 제출 이후 평가/수행 상태를 관리하며 접수증 또는 승인된 공식증빙 없이는 최종 신청완료 처리하지 않는다.
수정공고, Company Fact, 재무정보, Capability, Proposal, 사업비, 기업부담 변경 시 영향받는 Match, Proposal, Approval, Application Package, Case, Task를 식별한다.
필요하면 Re-review/Reapproval을 발생시키며 기존 Version을 삭제하지 않는다.
DMP 실제 API 확인 전에는 임의로 DMP Contract를 확정하지 않는다.

## 25. 보안과 다중 연구원 Git 협업

DB Drop, 대량 Delete, Migration Reset, 대량 File Delete, force push, Git History Rewrite, Production Data 변경은 사용자의 명시적 승인 없이 수행하지 않는다.
작업 시작 전 Current Branch를 확인한다. 기능개발은 특별한 지시가 없으면 Feature Branch를 기본으로 하며 main에서 장기간 직접 작업하지 않는다.
담당 Module 외 변경을 최소화한다.
DB Schema, Common Types, Shared, Contracts, Auth, Workflow, API Contract, Architecture 변경 전에는 영향범위를 보고한다.
Merge Conflict를 무시하거나 다른 사람의 작업을 덮어쓰지 않는다.

## 26. 개발 절차와 검증 보완

기준문서 확인 → 기존 구현 분석 → 영향범위 확인 → 작은 단위 구현 → Test → 검증 → 변경내용 보고 → 승인된 경우 Commit → 다음 작업 순서로 진행한다.
기존 구현은 그대로 재사용, Adapter 연결, 일부 수정 후 재사용, 신규 개발 중 적합한 방법을 먼저 판단한다. 불필요한 Refactor를 하지 않는다.
변경 후 관련 Test를 실행하고 실패를 숨기거나 무시하지 않는다.
기존 테스트 기준에 DB Persistence, Version, Approval, Evidence, Change Detection, Audit 검증을 포함한다.
Architecture, State/Action, Permission 변경은 관련 문서를 함께 갱신하고 중요한 새 결정은 Decision Log에 기록한다. 없는 문서는 승인된 작업범위에서만 생성한다.

## 27. 대표 Demo와 Snapshot 보호

1차 완료판단은 기능 숫자가 아니라 E2E Demo 성공 여부이다.

기업마당 API/Snapshot → Collector → Notice/NoticeVersion → 전체 공고 → 기업 선택 → 기업자료 → Company Fact → Improvement → DATCO Capability → Matching → Missing Information → Information Request → 기업 응답 → DATCO Review → Proposal → Approval → Proceed Confirmation → Support Case → Dynamic Application → Application Package → 공식 제출결과 → Receipt Evidence → 신청완료를 검증한다.

수정공고는 재검토, 승인 후 중요변경은 재승인, 접수증 없음은 완료 차단, 기업 Scope 위반은 접근 차단, Analysis 실패는 Retry를 검증한다.
Live API 기능은 실제로 구현하고, 동시에 민감정보가 제거된 검증된 Snapshot/Fixture/Seed로 외부 네트워크/API 장애 시에도 동일 Domain Logic을 통해 Demo를 완료할 수 있어야 한다.
화면만 가짜로 연결하는 Mock Demo로 대체하지 않는다. 새 기능이 대표 Demo를 깨뜨리면 완료로 판단하지 않는다.

## 28. Codex 완료 보고와 실행 제한

완료 보고에는 변경한 파일, 구현 내용, 변경 이유, 관련 기준문서, 실행한 Test와 결과, 남은 Issue, Risk, 필요한 의사결정을 포함한다.
사용자가 명시적으로 요청하지 않으면 git add, git commit, git push, branch merge, force operation을 수행하지 않는다. 기존 개발순서의 Commit은 자동 실행 권한을 의미하지 않는다.
Repository Baseline Step 02의 허용 변경은 사용자가 지정한 dongalab/AGENTS.md 보완뿐이다.
이번 Step에서는 다른 파일/폴더 생성·수정·삭제, docs/README/Source/package/Docker/DB/Schema/.env 생성, Framework 초기화, 패키지 설치, 기업마당 API 호출, Git add/commit/push, Branch 변경, GitHub 설정 변경을 하지 않는다.
