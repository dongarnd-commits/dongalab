# PR #8 Proposal 최종 기술 검수 — 2026-10-16

검수 기준: main `c029f420e946c404271cb6a047faf3bf6ca03e5e`, 시작 Head `1e1fda728dd2eb691d27cedb11d47d25a7cf5d35`. 기존 PR 변경 45개 전체를 확인했다. 소스/테스트/문서는 실제 내용과 Diff를 검수했고, 생성 API 타입/lockfile은 계약·의존성 및 자동 일치 검사 대상으로 구분했다. 제외 파일은 없다.

## 확정 결함과 최소 보완

| ID | 등급 | 재현·원인 | 보완·검증 |
|---|---|---|---|
| PR8-01 | P2 | 같은 Version DOCX/PDF의 재생성 시간이 다르면 ZIP/PDF 시간 메타데이터와 SHA256이 달라진다. 파일 저장 후 DB 실패가 반복되면 같은 내용의 미참조 blob이 증가할 수 있다 | DOCX Archive Entry timestamp 고정, PDF invariant 출력. 실제 업무 생성시각은 DB/Audit에 보존. 두 형식 시간 변경 재현 테스트 및 Commit 전/후 실패·동일 요청 재시도 검증 |
| PR8-02 | P2 (허용 입력의 출력 실패) | Feature 근거 150개를 한 PDF 표 행에 넣으면 페이지 높이를 초과해 ReportLab이 실패한다 | 근거를 개별 표 행으로 나눠 페이지 분할. 모든 150개 참조/목차/본문이 PDF에 남는지 검사. 원문/Manifest 내용은 변경하지 않음 |
| PR8-03 | P2 (화면 세션 분리) | 다른 탭에서 세션 변경 후 현재 세션 확인을 누르면 이전 항목별 검토 자료가 화면 상태에 남는다. 기존 Backend Scope 검사는 유지되지만 화면이 새 인증 주체의 자료처럼 보일 수 있다 | 세션 조회 전에 who/검토자료/의견/근거/편집 상태를 비움. 실제 Cookie 주체 전환 Browser 재현·회귀. 새 정책/권한은 추가하지 않음 |

초기 실패를 삭제·SKIP으로 전환하지 않았다. 재현 로그 및 격리 실행 증거는 Git 제외 Runtime에 보존한다. 새 Migration/DB Schema/Role/State/업무 Outcome은 추가하거나 변경하지 않았다.

## FROZEN 대조

- 03: Proposal Root/불변 Version/정확한 입력 Snapshot, 별도 Review/Approval/File 참조 유지. Manifest 외부 Company 참조는 신뢰 Provider 검증 대상이다.
- 04 §8: Request OPEN→CLOSED, DECIDED/SUPERSEDED, terminal Decision 하나, 새 Version에서 이전 승인 비승계 유지. Root에 별도 approval_status를 추가하지 않는다.
- 05 §7: Standalone 기본안의 Version당 지정 APPROVER 한 명/Request 한 개와 일치한다. ADMIN/OPERATOR의 기업 승인 대행과 EDITOR 승인은 차단한다. 복수 승인자는 후속 범위다.
- 08: 저장/새 Version/별도 내용 Review/승인요청/정확한 대상 확인/Private 다운로드를 기존 Guard로 연결한다.
- 10: Permission/Scope/현재성/불변성/멱등/동시성/실파일/오류 Rollback을 실제 테스트로 검증한다. 전체 전주기 Acceptance와 격리 Proposal 결과는 구분한다.
- 11 Decision-005 및 PROPOSAL_MATCH_REVIEW_POLICY: 사용자 명시 승인된 항목별 Completion만 적용한다. 실제 근거 없이 의견만 제출하거나 필수항목 누락/잘못된 Company·Version·digest·공고 Evidence를 제출하면 차단한다. MISMATCH/반대근거는 수동 체크로 해제하지 않는다. 원래 NEED_MORE_INFO와 과거 Review는 보존한다.
- 자격조건의 의미에 관한 사람 판단까지 문서 존재/digest 검사만으로 자동 보증하지 않는다. 범용 R07/문서 의미 분석/새 Provider 업무정책을 이번 보완에서 만들지 않는다. 실제 공급자·기업 자격의 업무 정확성은 해당 원문을 보는 DATCO 검토와 향후 권위 Provider 통합의 책임이다.

분류: 승인된 업무 계약은 APPROVED_AND_CONSISTENT, README 테스트 수는 DOCUMENT_SYNC_ONLY, 위 세 건은 IMPLEMENTATION_DEFECT의 최소 보완이다. 기업 문서 분석·자료보완/범용 R07/Phase2/실제 업무 DB 배포는 OUT_OF_SCOPE이며 별도 정책·배포 승인이 필요하다. 이번 검수에서 FROZEN 계약의 의미를 변경하지 않았다.

## 파일 저장/DB 실패와 미참조 파일

실패 주입은 파일 저장 후 API Session.commit 직전과 실제 commit 직후 응답 유실을 구분한다. 전자는 DB File/Receipt Rollback, 후자는 DB에 정확한 한 File/Receipt가 남고 클라이언트는 실패 응답을 받는다. 동일 요청 재시도는 같은 파일을 다시 연결하거나 이미 Commit된 결과를 반환해야 한다. 타기업 및 아직 공유하지 않은 기업 승인자의 다운로드는 거부한다.

미참조 Private blob 자체는 파일시스템과 DB를 하나의 원자 Transaction으로 묶지 않는 현재 저장소의 P2 운영 과제다. DB File id 없이 공개 다운로드할 경로가 없고, 동일 Version/내용/폰트/Renderer 환경의 반복 실패는 한 blob으로 수렴하도록 보완했다. 재시도하지 않은 작업의 blob은 남을 수 있다.

탐지/안전한 복구 절차:

1. 쓰기가 진행 중인지 확인하고 일관된 읽기 전용 DB Snapshot과 Private 파일의 이름/SHA256 목록을 취득한다. 실제 원문이나 인증값을 보고서/Git에 출력하지 않는다.
2. 기존 Notice Source, Proposal File 및 Company/Evidence Provider 등 같은 저장소의 **모든** 권위 있는 참조 집합과 대조해 미참조 후보를 만든다. Proposal File 테이블 하나만 비교하여 삭제 대상으로 판단하면 안 된다. Provider 미연결/참조 불완전/동시 쓰기가 있으면 판정 보류한다.
3. 실패한 동일 export 요청의 정상 재시도를 우선한다. 정상 재시도 후 같은 digest의 File 참조가 복구되면 후보에서 제외한다. Commit 후 응답만 유실된 경우 기존 Receipt를 재사용한다.
4. 계속 미참조인 파일은 저장소 경계/진행 작업/모든 참조를 다시 확인하고 별도 승인된 보존·격리·삭제 정책에 따라 처리한다. 현재 PR에는 자동 삭제/보존기간/GC 정책을 임의 추가하지 않았다. 이번 작업에서 기존 Private 파일을 삭제하지 않았다.

이는 무단 접근·잘못된 성공·DB 참조 손상이 없는지 테스트로 확인해야 하는 조건부 P2 운영 판정이다. 업무 DB Migration/운영 GC/보존기간 승인은 Merge와 별개다.

## 이번 검증 범위

문서 Unit 8건, Proposal DB/API 30건(Commit 전/후 실패 4건, 거부/수정요청 2건, 부분 DDL 실패/재시도 1건 추가), 기존 공개 Notice/Matching Integration 및 실제 Browser 회귀를 실행한다. 최종 Commit에서 비공개 실제 649건의 전체 Backend/Integration/Playwright Runner와 lint/build/API 타입을 다시 실행하고, 최신 원격 Head의 CI 네 Job을 확인한 실제 결과를 PR 본문과 비공개 완료보고에 기록한다. 이전 PASS를 이번 실행 결과로 재사용하지 않는다.

실제 Company Provider는 미연결로 503 차단을 유지한다. PHASE1_FULL_E2E=NOT_COMPLETED, PHASE2_FULL_E2E/SYSTEM_ACCEPTANCE=NOT_TESTED. Review 승인/Draft 해제/main Merge는 이번 작업에서 수행하지 않는다.

집중 회귀 실제 결과: 문서 Unit 8 PASS, 기존 공개 Integration 161 PASS/1 SKIP(Proposal 30건 포함), 공개 Browser 5 PASS. 신규 부분 Migration 실패·재시도 및 Commit 전/후 실패 검증도 통과했다. 최신 Commit 전체 회귀 결과는 PR/완료보고에 별도 기록한다.

## 기존 변경파일별 검수 목록 (45개)

| 파일 | 검수 방식 |
|---|---|
| `.github/workflows/datco-ci.yml` | 실제 내용·Diff·연결 Guard 검수 |
| `README.md` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/api/alembic/env.py` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/api/alembic/versions/e863p0012026_proposal_production.py` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/api/app/api/capability.py` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/api/app/api/proposal.py` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/api/app/capability/application.py` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/api/app/capability/lineage.py` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/api/app/capability/proposal.py` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/api/app/infrastructure/proposal_constraints.py` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/api/app/infrastructure/proposal_schema.py` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/api/app/main.py` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/api/app/proposal/__init__.py` | 의존성/생성 계약 및 자동 검증 |
| `apps/api/app/proposal/application.py` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/api/app/proposal/documents.py` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/api/app/proposal/policy.py` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/api/pyproject.toml` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/api/tests/ci_run.py` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/api/tests/committed_capability_fixture.py` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/api/tests/isolated_run.py` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/api/tests/isolated_server.py` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/api/tests/isolated_worker.py` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/api/tests/lineage_test_support.py` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/api/tests/proposal_browser_setup.py` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/api/tests/proposal_fixture.py` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/api/tests/test_proposal_documents.py` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/api/tests/test_proposal_preparation.py` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/api/tests/test_proposal_production.py` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/api/uv.lock` | 의존성/생성 계약 및 자동 검증 |
| `apps/web/src/app/api/proposal/[[...path]]/route.ts` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/web/src/app/capability/proposal-preparation.tsx` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/web/src/app/capability/workspace.tsx` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/web/src/app/proposal/page.tsx` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/web/src/app/proposal/workspace.tsx` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/web/src/generated/api.d.ts` | 의존성/생성 계약 및 자동 검증 |
| `apps/web/tests/capability-scenarios.spec.ts` | 실제 내용·Diff·연결 Guard 검수 |
| `apps/web/tests/proposal.spec.ts` | 실제 내용·Diff·연결 Guard 검수 |
| `docs/03_DATA_MODEL.md` | 실제 내용·Diff·연결 Guard 검수 |
| `docs/04_STATE_ACTION_MODEL.md` | 실제 내용·Diff·연결 Guard 검수 |
| `docs/05_PERMISSION_UI_MATRIX.md` | 실제 내용·Diff·연결 Guard 검수 |
| `docs/08_SCREEN_ACTION_SPEC.md` | 실제 내용·Diff·연결 Guard 검수 |
| `docs/10_TEST_ACCEPTANCE.md` | 실제 내용·Diff·연결 Guard 검수 |
| `docs/11_DECISION_LOG.md` | 실제 내용·Diff·연결 Guard 검수 |
| `docs/reviews/DATCO_PHASE1_PHASE2_E2E_GAP.md` | 실제 내용·Diff·연결 Guard 검수 |
| `docs/reviews/PROPOSAL_MATCH_REVIEW_POLICY.md` | 실제 내용·Diff·연결 Guard 검수 |
