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
