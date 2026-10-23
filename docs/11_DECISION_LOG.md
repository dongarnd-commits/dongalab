# DATCO 정부지원사업 운영체계 - Decision Log

## 문서 역할

00~10 Design Baseline을 대체하지 않는 Decision / Governance Log다. 사용자 승인에 따른 중요 기술·구조 결정을 기록하고 변경 이유와 영향범위를 추적한다. 새로운 요구사항이나 추가 설계 Baseline을 만드는 문서가 아니다. 중요한 변경은 상위 기준과 영향범위를 확인하고 승인된 범위에서 관련 문서를 동기화한다.

## Decision-001 — Phase-1 Application Stack

- Status: **ACCEPTED**
- Date: **2026-10-12**
- Scope: **Standalone Phase-1**
- 승인 근거: 사용자의 Phase-1 기술 Stack 공식 확정 및 기준문서 동기화 요청.

### Decision

| 영역 | 승인된 결정 |
| --- | --- |
| Frontend | Next.js App Router / React / TypeScript |
| Node Package Manager | npm / package-lock.json |
| Backend | FastAPI / Python / Uvicorn / Pydantic 2.x 계열 |
| Backend 경계 | API/Presentation → Application Use Case → Domain/Ports → Infrastructure Adapter |
| Database | PostgreSQL |
| ORM / Driver | SQLAlchemy 2.x / Psycopg 3 계열 |
| DB Access | Phase-1은 Sync SQLAlchemy Session 우선. 외부 I/O 비동기화는 실제 필요에 따라 선택 |
| Migration | Alembic |
| API Contract | REST / FastAPI OpenAPI / OpenAPI 기반 생성 TypeScript Contract 방향 |
| Authentication | Backend-owned Server Session / opaque Session ID / HttpOnly Cookie / Local-Demo AuthProvider |
| File | Local Private FileProvider. Binary는 Private Storage, Metadata·Evidence/Domain 참조는 DB |
| Background Job | PostgreSQL-backed Persistent Job / Python Worker, 같은 Backend Application/Domain 코드 재사용 |
| Backend Test | pytest / FastAPI API Test / 실제 PostgreSQL Integration Test |
| Browser E2E | Playwright |
| Frontend Component Test | Vitest / React Testing Library, 첫 Slice에서 필요한 범위만 적용 |
| Development | Web/API/Worker Host 실행, PostgreSQL은 Docker Compose 개발환경 권고 |
| Monorepo 방향 | apps/web / apps/api, 기존 docs/tools 유지. 실제 Directory는 아직 생성하지 않음 |
| Architecture | Modular Monolith / Provider-Adapter, 기존 Domain Module·데이터 소유권 유지 |

Backend가 Actor/Role/Membership/Company·Case·File Scope 및 State/Version/Domain Guard를 검사한다. Local/Demo Auth가 업무 Guard를 우회하지 않는다. 향후 DMP SSO/Company/File/Notification/Capability Adapter로 교체하되 실제 계약·식별 매핑·이력/소유권을 검증한다.

Job/JobAttempt/Retry/Recovery/idempotency를 유지하며 초기 Redis/Celery/RabbitMQ는 사용하지 않는다. 처리량·분산 요구가 확인된 경우에만 실행 Adapter 변경을 검토한다. Python Worker는 같은 업무코드의 실행 경계이며 별도 Microservice로 업무를 분리하지 않는다. Worker 프로세스 시작 방식·운영 개수·선점/복구 실행 세부는 Skeleton/첫 Slice에서 구체화한다.

GraphQL은 Phase-1에 도입하지 않는다. PostgreSQL에 File Binary 전체를 저장하는 방식은 기본전략으로 사용하지 않는다. Docker는 개발환경 권고이며 Domain Architecture 자체가 아니다.

### Rationale

실제 DB Persistence를 사용하는 Standalone Demo, 복잡한 Version/Approval/Evidence/Audit, Collector·Document/Intelligence 처리와 Python의 연결성을 고려한 선택이다. SQLAlchemy/Pydantic의 책임 분리와 명시적 Transaction/Query로 업무 무결성을 구현한다. Monorepo·OpenAPI Contract·Migration·Backend/Browser Test로 연구원 협업 경계를 유지한다. Local Provider와 DB Job으로 Phase-1 운영 구성요소를 줄이고 DMP/외부 실행기 전환 경계를 보존한다.

### Explicitly Deferred

- 정확한 Python Minor/Patch, Next.js/React Package, PostgreSQL Major/Patch 및 기타 Package Version. Skeleton 단계의 공식 지원·호환성 확인 후 고정.
- AI/LLM Provider, OCR Product, HWP/HWPX 전체 처리, 전체 Document/PDF Library 표준.
- PDF Text Extraction은 **DECIDE_AT_FIRST_SLICE**. pypdf 우선 평가 후보이며 실제 Fixture의 Text/Page Location/Encoding/Table/Scan 한계를 검증한 뒤 결정.
- Scheduler 제품/자동수집 주기, API Rate Limit/오류응답/Retry·운영수치.
- Redis/Celery 등 실행 Adapter, S3-compatible Adapter의 향후 필요성. 초기 도입하지 않음.
- Cloud/CI/Production Hosting·Deployment 세부, Backup 주기/보존기간/SLA/성능·동시사용자·Production Worker 수.
- 실제 DMP API/SSO/Company/File Contract와 데이터 이관·소유권 매핑.
- 전체 Physical Schema, Table/Column Naming/ID/Index/Partition/Lock/Transaction/Constraint/Junction 구현 세부.

AI/LLM은 AnalysisProvider Port → Phase-1 Fixture/Deterministic Adapter → 향후 실제 LLM Adapter 경계를 유지한다. 입력 → AnalysisRun → Candidate → Reason/Evidence/Source Location → Human Review → Confirm을 통과하고 Vendor나 Demo Mode로 확정 Gate를 우회하지 않는다. OCR은 실제 Scan 문서 필요를 확인한 뒤 선택한다.

### Rejected / Deferred Alternatives

| 대안 | 이번 결정의 이유 |
| --- | --- |
| Next.js + NestJS | 유효 대안이나 Phase-1은 Python Intelligence/Document 처리 통합성을 우선 |
| SQLModel | 유효 대안이나 복잡한 Version/Transaction/Query와 DTO 분리의 명시성을 위해 SQLAlchemy 선택 |
| Celery + Redis | 현재 처리량/분산 요구 근거가 부족하여 초기 도입 보류 |
| S3-compatible Storage | 단일 Demo 환경에서 선도입 필요성이 부족하여 Local Private FileProvider 우선 |

### Impact

Repository/Application Skeleton, 개발환경, Persistence/Migration, API Contract, Test 도구, FileProvider와 Job 실행 구현에 적용한다. 기존 업무 Architecture·Domain Workflow·Entity·State/Action/Guard·Permission·E2E·Screen·Demo·Acceptance 요구는 변경하지 않는다.

PostgreSQL 확정은 03의 94 Logical Entity를 94 Physical Table로 자동 생성하라는 뜻이 아니다. Vertical Slice → 필요한 Object/관계 → Table/Column/Constraint → Alembic Migration → PostgreSQL Integration Test 순서로 구현하며 Seed/Fixture 준비는 Migration과 구분한다.

첫 Slice는 기존 Notice HTML/PDF → Requirement Candidate → Evidence/Source Location → DATCO Human Review → Confirmed Requirement다. Local Auth/Private File/DB Job/Worker/공통 분석 Validation/Test 경로를 준비하고 Redis/Celery/S3/실제 AI Vendor를 선행조건으로 만들지 않는다.

이 Decision은 **문서상 기술 승인**이다. Application 설치/환경설정/DB/Schema/Migration/Skeleton은 아직 생성하지 않으며, Stack 승인 ≠ Test PASS다. 10의 모든 AC-*는 NOT_RUN, SYSTEM ACCEPTANCE는 NOT_TESTED다. 다음은 개발환경 확인/준비 → Skeleton → 첫 Slice의 Physical Schema/AG-01 계약 구체화다.

## Decision-002 — 전주기 MVP 목표 및 최소 문서 동기화

- Status: **ACCEPTED — 사용자 지시의 문서 변경 범위에 한정**
- Date: **2026-10-13**
- 승인 근거: 사용자의 「DATCO 전주기 MVP 기준문서 최소 동기화」 명시적 승인. AGENTS §1/00의 승인 후 동기화 규칙에 따른 동결 기준 변경 이력이다.
- Scope: 00/08/09/10/11의 자유입력·서비스/공고 매칭·비성공 결과·전주기 필수 Demo/Acceptance 명확화.

### 승인된 문서 결정 및 영향

업무 분야/Capability 분류 제한 없는 자유서술, 선택적 사진/자료, 원문·수정 Version·후보·확인 결과 분리를 요구한다. 확인된 실제 DATCO 서비스/조합·조건·Evidence 우선, 합성 역량 DEMO 표시, 미매칭·부분 적합·정보부족은 기존 후보/Review로 보존한다. 서비스 적합과 공고 적격을 독립 검토하며 허위 추천·근거 없는 자동 제안 생성을 금지한다.

더미 기업 데이터는 허용하지만 Web/API/PostgreSQL/파일/권한/Version/State/Task/Evidence/Audit는 실제 동작해야 한다. 선정 Case의 협약·수행·검수·정산·종료·사후관리 Task 완료까지 필수 Demo를 확장하고 성공/서비스 미매칭/공고 미매칭/정보부족/승인 후 변경/타기업 접근을 검증한다. 가상 외부 결과는 DEMO 표시한다. 09 H26~32/CHK-15 및 10 AC-MVP-01~06을 증분 추가한다.

01~07의 Architecture/Data/State/Permission/Provider/API, 기존 Decision-001·승인이력 및 향후 DMP 경계는 유지한다. 새로운 State/권한/승인 절차·코드 개발·정부 포털 자동제출·실제 DMP 연동·OCR/LLM/Embedding·Git 반영은 이번 승인에 포함하지 않는다. 사용자 문서 승인은 기업/대표의 업무 승인·공식 접수/선정·구현 완료·Test PASS가 아니다. 기존 개별 검증 번호와 NOT_RUN/NOT_TESTED 판정은 보존한다.

### PENDING / 구현 전 확인

- 별도 최종 신청 승인 필요 여부 및 기존 CONFIRM_APPLICATION/CONFIRM_COMPANY_PACKAGE/MARK_PACKAGE_READY 외 Actor·횟수·재확인 정책: **PENDING**. 제안 승인과 신청 문서 확인을 분리하고 05의 기존 권한/Open Decision 유지.
- 사업별 협약·수행·검수·정산·사후관리 Task/Evidence·완료조건 및 의미 있는 Demo 자료 준비: **PENDING**. 미정 조건을 충족으로 추정하거나 단계 스킵하지 않음.
- 실제 DATCO 자료/확인 상태, 기업 입력 AG-01 Slice 계약 및 실제 구현 충족: **확인 필요**. 다른 연구원의 Company/Site/Intake/Fact/Improvement 코드나 Feature Branch를 변경/재작성하지 않음.

## Decision-003 — Capability Catalog 개발 재개 및 최소 논리 계약 확장

- Status: **ACCEPTED — 사용자 명시 승인 범위에 한정**
- Date: **2026-10-14**
- 근거: 「DATCO Capability Catalog 3단계 개발 재개 — 승인된 데이터 계약 적용 및 실제 기능 구현」의 사용자 승인.
- 승인 범위: Feature Root/Revision/Import, Feature–CapabilityVersion, 기업별 Composition/Version·복수 구성·Coverage, Matching의 정확한 조합 Version 참조 및 해당 물리 구현·API·Web·테스트.

기존 Architecture/State/Permission/Approval/Proposal/Case 정책은 유지한다. 기능 ID는 원천의 명시적 해시 규칙을 검증한다. 실제 649개 원천은 로컬 입력으로 보존하고 Git에서 제외한다. 신규 논리 관계는 03의 승인 확장 절과 동기화한다. 과거 Decision-001/002 및 승인·Version·Evidence 이력을 변경하지 않는다.

기업 입력·Membership의 권위 있는 제공자가 없는 경우 기존 Company Scope 검사를 우회하지 않으며 테스트용 기업 Context를 정상 실행에 넣지 않는다. 기존 Notice 분석기는 유지하고 확정 요건 소비 Adapter를 재사용한다. 미확정 자격판정·점수산식·선정확률·새 공식 승인 정책은 승인 범위 밖이며 후보/근거·Human Review만 구현한다. 실제 Proposal/Case 전체, DMP 실서비스 연동·정부 포털 자동제출·LLM/Vector DB 도입은 포함하지 않는다.

실제 기업 제공자 연결과 자격·부분적합 집계정책은 PENDING이다. 문서 승인·구현·개별 테스트는 전체 SYSTEM ACCEPTANCE 완료를 의미하지 않는다. 이번 지시는 Commit/Push/Merge/PR 생성을 허용하지 않는다.

## Decision-004 — 공통 Typed 분석 계보 구현 및 범용 조건 자동화 상세설계

- Status: **ACCEPTED — R-04 구현 / R-07 상세설계에 한정**
- Date: **2026-10-14**
- 근거: 사용자의 「DATCO R-04 공통 분석 계보 구현 + R-07 자동화 기반 범용 정부지원사업 조건 매칭 상세설계」 최종 통합 명령의 명시적 승인 및 보완 조건.

기존 공통 AnalysisRun/Candidate/Review에 Notice/CapabilityAssessment/SupportMatching typed 관계를 구현한다. Assessment의 입력은 ImprovementVersion × CapabilityVersion이며 CompositionVersion은 실제 조합에 연결될 때만 선택적으로 참조한다. 재분석은 새 불변 Run/후보를 생성하고 과거 Review를 보존한다. Notice 필수 Version/Attempt, 공식 검토 유일성, Source/Evidence/이력을 보호한다. 동기 분석에 가짜 Job/NoticeVersion/SourceLocation을 만들지 않는다. 기존 미연결 Capability/Matching 이력은 legacy로 보존하고 가짜 계보로 보정하지 않는다.

공통 물리 관계/FK/Check/Index/필요한 deferred 무결성, 새 Alembic Migration, 서비스/API/계보 조회/최소 UI/생성 타입/격리 테스트 및 docs/03·07 동기화를 승인한다. 기존 Migration은 수정하지 않는다. 실제 존재하는 DB 대상만 FK로 연결하며 외부 Improvement/Fact는 권위 있는 Provider가 Scope/Version/Evidence를 검증한다. 동일 입력 재요청은 멱등 처리하고 실제 재평가·재검토는 별도 이력으로 기록한다.

R-07의 자동 증빙 추출·공고 구조화·범용 Condition AST·지역/업종/기간/예외·3값 논리·Human Review/DTO/Provider/UI/Test는 **상세설계만 승인**한다. 운영용 R-07 Migration/자동 판정정책/새 업무 State·Role·Permission/OCR·LLM Provider 구현은 승인하지 않는다. 기존 Comparator를 유지한다. 다른 연구원 Provider 통합은 대기하며 정상 환경의 503 차단을 유지한다.

Decision-001~003, 기존 Architecture/업무 상태·권한·Human Review·공식 승인 Guard를 보존한다. 운영 DB 적용·데이터 삭제·Git Stage/Commit/Push/Merge/PR은 승인 범위 밖이다. 문서 승인과 개별 회귀 PASS는 SYSTEM ACCEPTANCE 완료가 아니다.


## Decision-005 — Proposal P01-P05 구현 및 항목별 검토 Gate

Decision-005 — 사용자 명시 승인: P01-P05 실제 Proposal Root/불변 Version/Manifest/내용 Review/지정 기업 승인/실제 DOCX·PDF 출력 및 시스템 선행 파악→항목별 사람 확인 Gate를 구현한다. 세부 검토 기준은 docs/reviews/PROPOSAL_MATCH_REVIEW_POLICY.md. 기존 Role/State/Outcome/Architecture/공식 승인 의미를 유지한다. 실제 Company Provider 미연결은 차단하고 합성 격리 검증과 구분한다. 범용 R07 엔진·기업문서 추출기·Phase2/Case/Package·main Merge는 승인 범위 밖이다. 출력은 OOXML DOCX 및 ReportLab 임베디드 한글 TTF PDF, 기존 Private File Provider를 사용한다. 사용자 승인 지시: 기존 VSCode Proposal 브랜치에서 구현·검증·Commit/Push·Draft PR; 기존 Stash/외부 백업은 보존한다.


## Decision-006 — W1 기업 입력·Fact·Improvement 및 Company 공통 계보 증분

사용자는 W1 실제 Company/Site DB·API·UI, Private 파일/기존 파서, 출처 후보·기업 사실확인·운영자 Fact 검토, 불변 Fact/ImprovementVersion, 실제 Company Provider 연결, 격리 회귀 및 기존 Draft PR #9 Commit/Push를 명시 승인했다. 외부 AI 미승인은 수동/규칙 기반 경로를 중단하는 이유가 아니며 실호출 완료로 표시할 수 없다.

기존 R04 미승인 스키마 금지로 자동 승인 검토가 최초 공통 증분 실행을 거절한 뒤, 사용자가 reviews/W1_COMMON_LINEAGE_APPROVAL_REQUEST.md 범위의 공통 계보 증분 구현을 명시 승인했다. Company FK 2개·typed context·COMPANY_FACT_EXTRACTION 분기·불변/Scope 무결성·새 Migration/회귀 및 관련 문서를 승인 범위로 한다. 이전 Migration/Decision은 변경하지 않는다. 기존 State/Role/Notice·Matching·Proposal Guard와 공용 DB는 유지한다.

W2 자동 추천/W3 신규 Proposal 연계, R07 범용 조건 엔진, OCR·외부 AI 전송, 공용 업무 DB Migration, main Merge는 승인 범위 밖이다. 과거 Decision의 Company Provider 미연결 차단은 미구성 환경에 적용하며 이번에 연결한 실제 Provider도 현재성/Scope를 충족해야 한다. 미참조 Private 파일 보존·삭제정책 P2와 외부 AI Provider/모델/전송·비용·보존 승인은 후속 의사결정이다. 사용자 UI 수용은 주말 이후 실사용 검수 대기다.


## Decision-007 — W0 역할별 UI·네비게이션 및 실제 로그아웃

사용자는 기존 PR #9/W1을 유지하며 W0 실제 공통 Shell·역할별 홈/메뉴·이름 기반 업무 진입·현재 맥락/단계 이동·로그아웃·격리 브라우저 회귀·Commit/Push 및 기존 Draft PR 업데이트를 명시 승인했다. 기존 화면/API/DB를 재사용한다. 화면 Inventory와 최소 API 영향은 reviews/W0_UI_NAVIGATION_IMPLEMENTATION.md에 기록한다.

기존 인증에 서버 로그아웃이 없음을 확인하여 해당 세션의 expires_at 만료/동일 Cookie 삭제/LOGOUT Audit만 추가한다. 인증 방식·8시간 수명·Role/Permission/Schema/업무 State/승인 Guard는 변경하지 않는다. 홈·이름 선택용 GET /workspace는 실제 Membership 및 기존 Projection에서 허용된 요약만 읽는 최소 API이며 권한 확대나 새 업무 결정을 만들지 않는다.

미구현 자동 추천·D~F·관리 전용 기능은 준비 중으로 구분한다. 기존 Capability/Matching/Proposal과 W1 데이터를 삭제·재작성하지 않는다. 사용자 실사용 수용은 PENDING이고 전체 Phase1 완료·SYSTEM ACCEPTANCE를 주장하지 않는다. 공용 DB Migration/업무 데이터 변경·새 Worktree·main Commit/Push/Merge·force 작업은 포함하지 않는다.


## Decision-008 — PR14 최초 기업등록·로컬 한글 OCR 승인 증분 — 2026-10-21

사용자는 PR14의 C02/C03 서류 우선 최초 등록, 직접 입력, 실제 한글 OCR, 사용자 확인/수정, 사업자번호 정규화·체크디지트 및 기존 Company 등록/원본/Evidence 보존을 명시 지시했다. 과거 W1의 OCR 미승인 기록은 당시 범위로 보존하며, 이번 증분은 로컬 Tesseract/PDFium Adapter에 한정한다. 외부 OCR/AI 전송은 승인하지 않았다. 상세 영향은 reviews/PR14_INITIAL_REGISTRATION_OCR.md.

등록 전에는 기존 COMPANY_EDITOR 등록 권한으로 원문을 메모리 분석하며 Company/영속 File/공유 토큰을 만들지 않는다. 최종 사용자 확인 후 기존 Company/Membership Guard와 Private 파일/불변 Evidence를 재사용한다. 여러 서버 명령의 부분 실패는 회사 생성/문서 보존/추출 완료를 분리해 표시한다. 기업 ACK와 최종 Fact 확정은 계속 분리한다. DB Schema/Migration/Role/업무 State/Approval Guard/Assignment는 변경하지 않는다. 기존 저장 사업자번호나 과거 Version을 소급 수정하지 않는다. 실사용 인수는 PENDING이다.

## Decision — PR14 v1.4 기업 실사용 저장·보완·승인 근거 (2026-10-22)

Status: ACCEPTED. 사용자가 PR14_V14_CONTRACT_APPROVAL.md의 A~C 증분과 D 별도 승인 모드를 각각 명시 승인했다. 기존 상세 계약을 전면 재설계하지 않고 03/04/05/08/10의 해당 증분을 적용한다. 신규 Role enum·외부 AI·Matching 엔진·과거 원본 삭제는 포함하지 않는다. 기존 COMPANY_APPROVER 직접 승인 경로와 새로운 정확한 지정 Editor의 기업 내부 승인 근거 기록 경로를 구분하고, 실제 승인권자/기록자를 분리한다. Migration은 새 격리 검증 환경에서 수행하며 기존 사용자 자료가 있는 업무/체험 DB의 Migration은 별도 승인 대상이다. 범위·안전 정책·검증은 [승인안](reviews/PR14_V14_CONTRACT_APPROVAL.md)을 참조한다.

## Decision — PR14 v1.4.2 파일 재등록 최소 DB 증분 A (2026-10-23)

Status: ACCEPTED (LIMITED). 사용자가 동일 PDF 재등록의 새 유효 File ID/독립 이력, 기존 UNIQUE 최소 변경, 새 Migration 및 Backend·격리 회귀를 명시 승인했다. 활성 Company/digest 중복은 DB Guard와 기존 Company 잠금으로 제한하고 취소·교체 이력과 공유 원본·Evidence·Version·Snapshot은 유지한다. 새 State/Role/Permission은 없다. 기존 업무·사용자 검수 DB Migration, 운영 배포, 영구 삭제, 백업 파기, Next.js 업그레이드 및 PR Merge/Draft 해제는 제외한다. 물리 삭제는 POLICY_BLOCKED이며 별도 정책 승인이 필요하다. [상세 승인 범위 및 DDL](reviews/PR14_V142_FILE_REGISTRATION_APPROVAL.md).

## Decision — PR14 v1.4.3 단일 작성 중 첨부의 교체 (2026-10-23)

Status: ACCEPTED (LIMITED). 사용자 직접 검수 요청은 C07 교체와 단일 DRAFT 개선요구의 현재 첨부를 일치시키는 보완이다. 기존 계약의 불변 행 재연결 금지는 유지하고, 명시적 교체 확인 후 MANUAL_REVIEW 첨부 Evidence와 기존 save_improvement의 새 Version을 같은 트랜잭션으로 생성한다. 업무 내용·DRAFT·과거 제출 참조는 보존하며 자동 Fact 확인·Analysis 근거 전환·새 상태/권한·Schema 변경은 없다. 공유 업무나 분석 근거의 일괄 변경은 차단한다. 현재 SUBMITTED의 Version/State는 교체로 변경하지 않는다.

사용자가 지정한 격리 DB의 정확한 단일 불일치 테스트 건만 기존 replacement lineage와 Version Guard로 복구하고 기존 테스트 Editor의 실제 제출을 검증한다. 광범위한 backfill, 업무 DB Migration, 원본 삭제, 운영자 화면 신규 개발, main Merge/Draft 해제는 포함하지 않는다. 상세 계약은 `reviews/PR14_V14_CONTRACT_APPROVAL.md`의 v1.4.3 절, 검증은 `10_TEST_ACCEPTANCE.md`를 따른다.
