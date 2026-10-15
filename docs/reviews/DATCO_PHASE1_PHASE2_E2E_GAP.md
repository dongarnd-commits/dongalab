# DATCO 1차 제안서 생산 연결 및 전주기 구현 Gap

- Date: 2026-10-16
- Status: **PROPOSED / IMPLEMENTATION_GAP_REVIEW**
- Branch: feat/datco-capability-catalog-v1
- HEAD: 1305954fb7c62b1692743c48d929517059ef7119
- 기준: AGENTS → 00 → 01 → 02~11, Decision-001~004, R07_REVIEWED_CONDITION_DESIGN.
- 이 문서는 결정 승인이나 동결 기준 변경이 아니다. 운영기준 v1.6/최종 전주기 MVP 목표를 축소하지 않는다.

## 1. 두 구현 마일스톤과 최종 수용

Phase 1은 기업 자유입력/확인 Fact·Evidence → DMP 기능/Capability → Composition → 공고 Matching/사람 검토 → 실제 제안서 생성·저장·검토·Version·파일 출력이다. Phase 2는 신청자료 재사용/부족자료 보완 → ApplicationPackage → 신청·평가·협약·수행·검수·정산·사후관리다. 두 단계는 기존 전주기 목표 안의 구현 순서다. 둘 다 완료하기 전 SYSTEM_ACCEPTANCE는 NOT_TESTED다. Test Fixture의 합성 기업/공고는 업무 사실이나 실제 제공자 통합을 뜻하지 않는다.

## 2. 실제 소스 기반 Preflight

`apps/api/app`, `apps/api/alembic/versions`, `apps/web/src`를 조사했다. 아래의 미구현 판정은 이 checkout 기준이며 다른 연구원 브랜치에 구현이 없다는 뜻은 아니다.

| 객체 | 실제 물리/API/UI | 판정/재사용 |
|---|---|---|
| Notice/NoticeVersion/Requirement/Evidence | notice_schema, Notice API/Worker, notice Web, ConfirmedNoticeReader | 구현됨. 공식 원문/검토/정확한 Version 재사용 |
| Feature/CapabilityVersion | capability_schema, inventory/catalog API/Web | 구현됨. 실제 649 원천 Revision/연결 보존 |
| CompositionVersion/Coverage | capability_schema, save_composition/composition, composer Web | 구현됨. 해결·미해결/조건/제외기능 및 Version 보존 |
| MatchInputSnapshot/Candidate/Review | capability_schema, prepare_match/match/review_match, matching Web | 구현됨. 공통 분석 계보 및 기존 Comparator 재사용 |
| Company/Site/Intake/Fact/Improvement | ImprovementReader/UnavailableImprovement만 있음 | 정상 Provider 미연결503. 다른 연구원 소유 Domain 재구현 금지 |
| Proposal/ProposalVersion | 논리설계만 있음; 테이블/Migration/API/UI 저장 구현 없음 | 새 물리/AG-01 저장 계약 승인 필요 |
| Proposal ApprovalRequest/Decision/Proceed | 논리설계만 있음 | 지정 기업 승인/요청 Lock/추진결정 미구현 |
| ApplicationPackage/SupportCase/Task/공식결과 | 논리설계만 있음 | 후속 Slice 미구현. Analysis Job은 업무 Task가 아님 |

Composition은 서비스 구성, Match는 비교/검토, Proposal은 고객에게 제안할 정확한 내용, ApplicationPackage는 신청문서 묶음, Case는 추진결정 이후 운영건이다. 기존 Composition JSON이나 Match Snapshot을 Proposal/Case로 재명명하지 않는다.

## 3. 확정된 기존 Guard와 이번 실제 구현

04 §4 G-PROPOSABLE 및 ACT-PROPOSAL-01, 05 §5 CREATE_PROPOSAL_VERSION, 10 AC-PROP-01은 **초안 생성에도** 현재 PROPOSABLE 검토/최신 입력/Blocking Missing Info 해소를 요구한다. 02 FLOW-14의 Draft 설명을 이 Guard의 예외로 해석하지 않는다. FIT는 업무 제안 가능 판단이 아니다.

현 `review_match`는 필수 기업·공급자격/서비스 검토가 불완전하여 PROPOSABLE 요청을 MISSING_REQUIRED_INFORMATION으로 거절한다. 정상 Company Provider도 미연결이다. 합성 Fixture 결과를 FIT/PROPOSABLE로 직접 Update하여 정상 제안서 시나리오를 만들지 않는다. 따라서 이번에 저장 가능한 제안서 초안/검토/Version/파일 생성은 구현·실행하지 않는다.

독립적으로 가능한 부분은 실제 코드로 연결했다.

- `app/capability/proposal.py`: 기존 match()의 Operator/Company/Provider/Evidence/현재성 검사를 거친 생성조건 조회. 오래된 입력/legacy/현재 업무 검토/필수정보 차단 이유와 정확한 원천 Version 참조 반환.
- `GET /capability/matches/{candidate_id}/proposal-preparation`: 인증된 읽기 전용 API. `can_create=false`이며 정책 차단과 물리/출력 미구현을 분리한다. DB 쓰기나 Proposal 자동생성 없음.
- Matching Web의 제안서 작업 → 생성조건 확인: 현재 서버 검사와 원천 Version 참조/불가 사유 표시. 작성/승인/출력 버튼을 가짜로 만들지 않는다.
- OpenAPI 기반 생성 TypeScript 동기화. 전용 실제 API/DB 테스트 및 기존 F1~4 브라우저 시나리오에 생성조건 검증 추가.

이 조회는 Proposal Draft/제안서 미리보기/파일 출력이 아니다. 저장 기능 미구현 때문에 정책이 허용되는 미래 입력이라도 can_create=true를 반환하지 않는다. 조회 결과는 차후 생성 Action의 재검증을 대신할 수 없다.

## 4. 제안서 15개 내용의 Source Mapping / 미구현 범위

| 제안내용 | 실제 원천 / 부족사항 |
|---|---|
| 기업/개선과제/입력 원문 | Snapshot.company + exact ImprovementVersion, 정상 Provider 필요 |
| 확인 Fact/Evidence | Snapshot.comparison.facts + context의 참조. 실제 FactReview/Scope/파일은 Provider 계약 확인 필요 |
| 해결안/실제 DMP 기능/Capability | exact CapabilityVersion + links → FeatureRevision. 새 문구로 성능/효과 보증 금지 |
| Composition/요구별 해결/부분·미해결/조건 | exact CompositionVersion.data.coverage/conditions/unresolved 및 Capability conditions/prerequisites/exclusions |
| 추천 공고/매칭 이유/기업·공급자격/부족정보 | Snapshot.notice의 NoticeVersion/RequirementVersion, Candidate.data 및 정확한 현재 MatchReview. 차단 상태에서는 추천/적격으로 승격 금지 |
| 작성/검토/제안 Version | Proposal/Version/Review 물리관계 미구현. 기존 MatchReview를 제안서 검토로 위장 금지 |

금액·사업비·효과·선정확률을 추정하지 않는다. 빈 비용은 0이 아닌 확인 필요다. 현재 참조 조회에서 존재하지 않는 회사명/작성자/ProposalVersion을 발명하지 않는다.

## 5. 최소 물리·저장 계약 승인 요청안 (미적용)

근거: AGENTS §2의 DB/API/핵심 Domain 변경 통제, 08 AG-01 및 10 AC-INPUT-01. Decision-003의 명시 물리 승인은 Capability/Composition/Matching에 한정됐으며 Proposal 계약은 확정되지 않았다. 이번 사용자 지시도 별도 승인이 필요한 물리 계약은 제안 후 해당 부분만 유보하도록 했다.

다음은 제안이지 승인 완료가 아니다. 기존 Migration/Schema/Decision은 변경하지 않는다.

1. `proposals`: UUID PK, company_id(권위 있는 외부 Company 참조), match_review_id(실제 MatchReview FK), current_ordinal, created_by(Actor FK), created_at. company_id는 브라우저 입력으로 결정하지 않는다.
2. `proposal_versions`: UUID PK, proposal_id FK, ordinal, match_snapshot_id FK, composition_version_id FK, notice_version_id FK, requirement_version_id FK, match_review_id FK, exact input_manifest JSONB, content JSONB, authored_by FK, created_at; UNIQUE(proposal_id,ordinal). 입력 manifest에는 Improvement/Fact/Evidence/Capability Version들과 확인 근거를 고정한다. 존재하지 않는 외부 Company/Fact 테이블에 가짜 FK를 만들지 않는다.
3. 저장 Command 제안: POST /proposals(현재 검토 기반 생성), POST /proposals/{id}/versions(expected_version 기반 새 수정본), GET /proposals/{id}, GET /proposals/{id}/versions/{version_id}. Operator+trusted Company Scope, 기존 Guard 매 실행 재검사, 기존 advisory lock/receipt 멱등성, Actor/Action/Object/Version Audit, 단일 Transaction. 발송 후 불변본 수정 금지. 단순 내부 수정도 새 불변 Version을 만드는 보수적 구현안을 승인받는다. current 포인터 변경으로 과거 승인을 전용하지 않는다.
4. 기존 논리 ApprovalRequest/Decision의 물리화는 별도 명세 확정 후 연결한다. Request는 정확한 ProposalVersion/지정 COMPANY_APPROVER와 OPEN/CLOSED 및 closureReason, terminal Decision은 1개. 새 Version 생성 시 이전 OPEN Request SUPERSEDED, Decision 불변. DATCO의 기업 승인 대행 불가. 실제 저장구조 없는 승인요청 API를 선행 노출하지 않는다.
5. 제안서 자체의 DATCO 검토 저장(논리상 review 필수) 대상/기록 위치를 확정해야 한다. MatchReview는 매칭 검토이며 제안내용 검토와 같지 않다. Proposal Review에 새 State/Action을 임의 추가하지 않는다.
6. 문서 출력: 저장된 특정 Version/입력 manifest만 렌더링하고 파일 해시/미디어 타입/Private File 메타데이터/작성자/버전/출력시각을 기록한다. Company 및 공개된 Version Scope로 다운로드를 재검사한다. **PDF/DOCX/HWP 등 승인된 제안서 출력 표준은 이 checkout에서 확인되지 않았다.** HTML 화면이나 Notice 원문 PDF Viewer를 출력 규격으로 전용하지 않는다. 포맷·템플릿 필수항목·폰트/한글·출력시점·권한·버전 연결을 별도 결정한다.

### 요청할 정확한 결정

- **승인 요청 P-01:** “기존 03/04/05의 Proposal 의미와 Guard를 유지하며 위 Proposal/ProposalVersion 최소 물리관계·AG-01 저장/새 Version 계약의 구현 및 관련 기준문서 증분 동기화를 승인한다.” 외부 Company/Fact 계약을 발명하는 승인은 포함하지 않는다.
- **결정 요청 P-02:** “제안내용 DATCO 검토 기록과 기존 ApprovalRequest/Decision의 최소 물리·API 계약을 확정한다. 지정 COMPANY_APPROVER/현재 Version/Lock/과거 승인 보존을 유지한다.”
- **결정 요청 P-03:** “제안서 출력 포맷 및 최소 템플릿/Private 파일 Version 연결/다운로드 정책을 지정한다.” 포맷 선택 전 임의 표준 출력 개발 금지.
- **선행조건 P-04:** 권위 있는 Company/Improvement/Fact/Evidence Provider 계약과 자격·서비스 필수조건의 완전한 사람 검토 경로를 확정한다. 기존 PROPOSABLE 차단을 단순 제거하는 승인은 요청하지 않는다. 미확인 내부 초안을 원한다면 별도 정책 변경안으로 04/05/10의 영향과 명시 승인을 먼저 받아야 한다. 이번 요청은 그 예외를 승인하지 않았다.

## 6. 1차 시나리오와 실행 한계

| ID | 이번 실행대상 | Proposal 생성/검토/Version/출력 |
|---|---|---|
| P1-A 정상 의도 | 합성 요구→실제 DMP Revision→조합→확정 TEST 공고→HOLD→실제 API 생성조건 조회 | 필요한 정보/PROPOSABLE 불충족으로 BLOCKED. 정상 제안서 E2E PASS 아님 |
| P1-B 부분 해결 | 부분 범위/미해결 원천 및 Snapshot 보존, 생성 차단 | 저장 Proposal에서의 범위 재현은 NOT_TESTED |
| P1-C 정보 부족 | 기존 NEED_MORE_INFO 및 필수정보 차단 조회 | BLOCKED_POLICY |
| P1-D 명확 충돌 | 검토된 TEST Fact/Condition 비교 MISMATCH를 제안 가능으로 승격 안 함 | BLOCKED_POLICY |
| P1-E Version | 조합 새 Version 후 과거 Snapshot/Review 보존 및 생성조건 stale | ProposalVersion 이력 자체는 NOT_TESTED |
| P1-F 권한 | 미인증401/Admin·기업403/타기업404/정상 Provider503 | 저장·발송·파일 권한은 API 미구현으로 NOT_TESTED |

실제 Proposal row나 출력 파일이 생성되지 않았다. 기존 API/DB Guard 검증을 Proposal Persistence/Version/파일 성공으로 보고하지 않는다. Fixture 기반 상류 Slice와 실제 기업 Provider 통합 판정도 분리한다.

## 7. Phase 2: DB/API/UI 구현 Gap

| 흐름 | 기존 설계 | 이 checkout 구현 | 재사용/추가 필요 |
|---|---|---|---|
| 기존 자료 × 공고 신청요건 | 02 FLOW-19, 03 Template/Field/Document Definition, 07 매핑 후보 | Notice 요건/Evidence는 있음; 기업자료 소비·RequiredDocument 구조화·매핑 없음 | ConfirmedNoticeReader/FileProvider 재사용, Fact Provider 연계, 유형·유효기간/충돌/해당없음 근거 검토 |
| 부족·만료·불일치 식별 | 07 Missing/Conflict, 04 Request/Readiness | Comparator의 제한된 코드 비교/UNKNOWN만 있음 | 기존 값 재사용과 현재성 검증, 정책 확인 없는 자동 누락 판정 금지 |
| 부족자료 요청/기업 보완 | 02 FLOW-13, 03 Request/Response/Context, 04 State/05권한 | DB/API/UI 없음 | 정확한 Item/Version/기한/공개 Projection, 응답 Version 및 DATCO 재검토; 기업 전체 재입력 강제 금지 |
| Application/Package | 02 FLOW-19/20, 03 §13, 04 §10, 08 해당 화면 | DB/API/UI 없음 | 제안과 분리, TemplateVersion/Field/RequiredDocument, 값/문서별 Source Fact/Evidence/확인 및 불변 제출 Snapshot |
| Proposal 승인→Proceed→Case | 03 §12, 04 §8/9 | DB/API/UI 없음 | 정확한 ProposalVersion 기업 승인/별도 Proceed/Case 유일 Proceed 검증 |
| 신청/접수증 | 02 FLOW-21, 04 Readiness/Submission | DB/API/UI 없음 | 외부 수동 제출 사실+파일/공식 근거 검토, DEMO 명시, 미검증시 평가 차단 |
| 평가/선정/미선정/협약 | 02 FLOW-22, 04 Case Stage | DB/API/UI 없음 | OfficialResult/Evidence/Review 이력, 미선정→협약 금지 |
| 수행/결과물/검수/정산/종료 | 03 Case/Task/Deliverable, 04 Stage/Task | DB/API/UI 없음 | 사업별 완료조건·필수 증빙/Task 선후행/회사·Case Scope |
| 사후관리 | 09 H26~32, 10 AC-MVP-05 | DB/API/UI 없음 | CLOSED 유지하며 후속 Task 생성/완료 검토, 동일 Case/Evidence 추적 |
| 변경영향/권한/이력 | 03 Version/Impact, 04/05 | Notice/Capability/Match/R04만 구현 | Package/Proposal/Case 후속 영향 및 권한 파일 조회. 단순 UI 숨김 금지 |

이 표의 “설계 있음”은 구현 완료가 아니다. R07 범용 자동 추출/AST는 상세설계만 승인됐으며 이번에 구현하지 않는다. 기존 Normal Auth/Private File/Job/Audit 패턴을 재사용하되 업무 Task/Approval 의미를 Job/Notice Review로 대체하지 않는다.

## 8. 다음 Slice와 완료조건

1. P-01~04 결정 후 Proposal 저장/불변 Version/정확한 원천 manifest/제안 검토/지정 승인/출력. P1-A~F 실제 API·PG·Web·파일, 재로그인/새로고침, 이전 승인 보존을 실행해야 완료다. 원천 변경 시 새 Version과 재검토가 필요하다.
2. Information Request + Fact 재사용/응답 검증: 확인된 자료는 재사용, 부족분만 기업 요청, 응답 제출≠검증≠Fact 확정. AC-REQ-01~08/AC-INPUT-01 실제 실행.
3. Application/Package + Readiness/외부 제출: RequiredDocument/File/확인/기업확인·정확한 승인 Version 고정, 부족 시 차단. AC-APP/PKG/SUB 및 DEMO/공식 구분 실행.
4. Case 공식결과~사후관리: 동일 Case로 Stage/Task/Evidence/공식근거/권한/완료 검토, 미선정 분기와 H26~32, AC-MVP-05/06 실행. 단계 스킵이나 가짜 완료 불가.

다른 연구원은 Company/Site/Membership/Intake/Fact/Improvement의 실제 read-only Scope/Version/Evidence 계약을 제공한다. 본 작업은 그 소스/브랜치를 변경하지 않았다. 사업별 자료 요구/완료조건, 지정 Package 확인자 및 별도 최종 신청 승인 정책은 Decision-002/05의 미확정 사항을 유지한다.

## 9. 기준문서 동기화 판단

00/01/02/03/04/05/07/08/09/10/11은 이미 Proposal→승인→Case→신청→사후관리를 정의한다. 목표/Flow 재작성이나 운영기준 변경이 필요하지 않다. 이번 읽기 전용 생성조건 조회는 기존 Guard의 조회이며 새 업무 Action/State/Role을 추가하지 않는다. AG-01/새 물리계약과 출력 결정 승인 시 관련 03/08/10 및 Decision Log를 먼저 또는 함께 증분 갱신한다. Decision-001~004를 수정/승인 전용하지 않는다.

## 10. 실행 검증 기록

실행 결과는 최종 검증 후 아래에 추가한다. 이전 193/117/20 PASS를 이번 신규 기능 PASS로 전용하지 않는다. Phase 2는 NOT_TESTED이며 Proposal 생성·저장·검토·Version·파일 출력도 미구현/차단 판정을 유지한다.

### 단계별 기능 판정 (상류 격리 검증과 Proposal 완료 구분)

| 기능 | 판정 | 한계 |
|---|---|---|
| FEATURE_TO_CAPABILITY | PASS_ISOLATED | 실제 649 원천 Revision, 합성 Capability 검증 |
| CAPABILITY_TO_COMPOSITION | PASS_ISOLATED | TEST 기업 Context, 실제 저장/조회/Version |
| COMPOSITION_TO_NOTICE_MATCH | PASS_ISOLATED_LIMITED | TEST 공고 조건의 기존 Comparator 범위. R07 범용 엔진 아님 |
| MATCH_REVIEW_GUARD | PASS | 자동 PROPOSABLE 없음, 실제 HOLD/부족정보 Guard |
| MATCH_TO_PROPOSAL | BLOCKED_POLICY_AND_CONTRACT | 생성조건 조회만 구현; 제안서 생성 미구현 |
| PROPOSAL_PERSISTENCE | NOT_IMPLEMENTED | P-01 승인 필요 |
| PROPOSAL_VERSION | NOT_IMPLEMENTED | 과거 Match/Composition 보존은 Proposal 이력 증거가 아님 |
| PROPOSAL_DOCUMENT_OUTPUT | NOT_IMPLEMENTED | P-03 형식/파일 연결 결정 필요 |
| PROPOSAL_AUTHORIZATION | PARTIAL | 생성조건 조회의401/403/404/503 검증; 저장·공개·승인·다운로드 권한은 NOT_TESTED |

PHASE1_INTEGRATED_E2E는 PENDING_PROVIDER이며 정책·저장계약도 미충족이다. PHASE1_ISOLATED_E2E 전체는 BLOCKED다. 상류/차단 테스트 성공으로 제안서 생산 성공을 주장하지 않는다.

### 2026-10-16 최종 실행 결과

| 검사 | 실제 결과 | Evidence |
|---|---|---|
| 전체 Backend | 199 PASS / 0 FAIL / 1 SKIP | test-isolation/4fc9e8734426/backend.xml |
| Integration | 123 PASS / 0 FAIL / 1 SKIP / 76 deselected | 같은 실행 integration.xml |
| 신규 Proposal 생성조건 API/DB | 6 PASS (위 집계에 포함) | test_proposal_preparation.py |
| 전체 Playwright | 20 PASS / 0 FAIL / 1 SKIP | test-isolation/8f3b65cd22ba/playwright.log |
| F1~4 생성조건 브라우저 | 4 PASS (위 집계에 포함) | capability-scenarios.spec.ts |
| lint / build / API 타입 비교 | 모두 exit 0 | 8f3b65cd22ba의 개별 로그 |
| Migration 적용/모델 일치 | PASS, 새 Migration 없음 | 4fc9e8734426 migration/migration-check |
| 공용 DB 무변경/테스트 정리 | 두 Runner 모두 changed_tables=[], cleanup=true | 두 report.json |

Evidence 경로 Root는 `storage/private/runtime/test-isolation/`이며 Git 제외다. Backend/Integration SKIP은 저장된 실제 한국어 원문 테스트의 opt-in 미설정이다. 브라우저에서는 저장된 실제 한국어 원문 격리 검증이 통과했다. Playwright SKIP은 API를 의도적으로 중단해야 하는 기존 장애 안내 시나리오로, 이번 정상 API 실행에서는 미실행이다. 테스트 PASS를 제안서 파일 생성이나 전체 E2E 성공으로 해석하지 않는다.

R04_REGRESSION=PASS, R07_COMPARATOR_REGRESSION=PASS. PROPOSAL_IMPLEMENTATION=PARTIAL_READ_ONLY_GUARD, PROPOSAL_DOCUMENT_GENERATION=NOT_IMPLEMENTED, PROPOSAL_VERSION_HISTORY=NOT_IMPLEMENTED. PHASE1_ISOLATED_E2E=BLOCKED, PHASE1_INTEGRATED_E2E=PENDING_PROVIDER(정책/저장계약도 미충족), PHASE2_IMPLEMENTATION_GAP=DOCUMENTED, PHASE2_E2E=NOT_TESTED. TEST_ISOLATION/PUBLIC_DB_INTEGRITY/FROZEN_COMPLIANCE/ARCHITECTURE_PRESERVED/RESEARCHER_SCOPE_PRESERVED=PASS. CAPABILITY_PR_READY=CONDITIONAL(기존 Provider/Proposal 계약 미완료, Git 작업 미수행), SYSTEM_ACCEPTANCE=NOT_TESTED. APPROVAL_REQUIRED=P-01~04. NEXT_DEVELOPMENT_SLICE=계약/Provider 확인 후 Proposal 저장·검토·불변 Version·지정 승인·출력.
