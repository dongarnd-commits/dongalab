# DMP 기술자산 관리·자동 솔루션 조합 통합 계약 및 검증 보고

기준 2ee2640836ae1fa07bf4ccf0a34d03a4f27851e0, 2026-11-02 사용자 명시 통합 보완개발 지시.
이 문서는 구현 전 영향 계약과 이후 실제 검증 결과를 한 곳에 유지한다.
현재 상태: PR18 집중 보완 구현·로컬 자동 회귀 완료(출발 c62e2d3, 기존 완료 결과 보존). 소스 동결 후의 최신 HEAD CI·새 로컬 인수환경 실측 판정은 PR18/보호 RUNBOOK에서 확인한다. 실기업 평가·사용자 최종 인수·운영 배포는 대기다.

## 승인된 역할 및 보존
관리자는 전역 DMP 기술자산/제공검증/릴리스 정보를 관리하고, 시스템은 원천 기반 조합 초안을 생성하며,
운영자는 자기 Company Scope의 후보 적절성·해결범위·연계를 검토·수정한다.
기존 발행 Capability는 표준 제공범위 근거로 그대로 유지하며 고객별 초안을 관리자에게 강제하지 않는다.
새 Role/멤버십/승인 정책을 추가하지 않는다. 기업 계정은 전체 내부 기술자산을 조회·수정하지 못한다.
기존 ACK/CONFIRM/PROPOSABLE/내용검토/발송/기업 의사결정과 요청·답변·승인 불변 Trigger는 보존한다.
기존 전주기 H01~H32/Collector/DMP 외부 API는 재설계하지 않는다.

## 변경 영향과 확정 계약
1. 원본 feature_imports/dmp_features/dmp_feature_revisions/feature_import_members 및 strict649 digest 검증을 보존한다.
   신규 증분은 원본649 import로 가장하지 않는다. 기존 원본 Revision은 UPDATE/DELETE하지 않는다.
2. 전역 dmp_asset_nodes(kind SYSTEM/MODULE/FEATURE), append-only dmp_asset_versions를 추가한다.
   FEATURE는 기존 dmp_features에 typed FK, 버전은 정확 dmp_feature_revisions에 typed FK를 가진다.
   MODULE/FEATURE의 부모는 실제 asset node FK로 검증한다. node 현재 ordinal만 잠금/expected-version 검사 후 갱신한다.
   버전에는 역할/문제/업무/적용·제외·선행조건/릴리스/제공상태/검증근거/출처를 보존한다.
   의존·연계·대체는 dmp_asset_relations의 실제 대상 node FK로 추적하며 자동 연계 확정은 없다.
3. 아직 관리 등록되지 않은 원본 기능도 조회·추천한다. system/feature_group은 '원천 분류/미확인 모듈'이다.
   가상 분류를 검증된 DMP 모듈로 표시하지 않는다. 원본의 AVAILABLE을 현재 고객 납품가능 확정으로 승격하지 않는다.
   제공검증 상태는 NEEDS_CONFIRMATION/VERIFIED/UNAVAILABLE/RETIRED이고 VERIFIED는 비어있지 않은 근거가 필요하다.
4. dmp_solution_runs는 정확 Company/ImprovementVersion/기존 AnalysisRun/검토출처·asset catalog digest·규칙 Version을
   입력에 고정한 불변 생성 초안이다. 후보0건도 정상 저장한다. 동일 입력 digest/규칙은 중복 생성하지 않는다.
   기존 분석 Run/Candidate/Evidence/Review를 입력으로 재사용하며 가짜 Notice/SourceLocation/Job을 만들지 않는다.
5. 기존 Composition에 source_mode=CAPABILITY(기존 기본)/DMP_ASSET를 추가한다. CAPABILITY 경로는 기존 의미 그대로다.
   DMP_ASSET만 capability_version_ids=[]를 허용하며 asset_selections/asset_basis/asset_review_note와 Coverage가 필수다.
   기존 빈 Capability 연결 거부를 전역 완화하지 않는다. matching 링크 Trigger의 새 명시 모드만 검증 분기를 추가한다.
   composition_asset_features가 정확 기능 Revision 및 선택한 feature/system/module 관리 Version의 typed FK를 가진다.
   기존 CompositionVersion은 불변이고 새 수정은 새 Version이다. 자동 초안은 공식 Composition을 자동 저장하지 않는다.
6. asset_basis={recommendation_id,alternative_id}. asset_selections는 feature_revision_id, asset_version_id,
   system_version_id,module_version_id를 명시한다(원본 분류의 미등록 관리 Version은 null).
   Coverage의 capability_version_id는 새 자산 모드에서만 null이며 feature_revision_ids/역할/해결·미해결 범위/근거를 검증한다.
   asset_integrations는 from/to module-or-system 식별, 실제 확인 상태와 확인 조건을 분리한다.
   운영자가 수정·검토하여 저장한 actor/시각/의견·정확 추천 출처는 CompositionVersion과 Audit에 보존한다.
7. Matching/Proposal은 기존 Composition 참조를 재사용한다. 자산 조합의 정확 기능/역할/조건/연계/남은 범위를
   Match 입력 및 Proposal manifest/MVP16에 추가한다. 미검증 제공·연계·Coverage를 확정 사실로 승격하지 않는다.
   기존 서비스 기반 경로/11절 템플릿과 과거 문서/승인/계보는 변경하지 않는다.
8. 현재성은 정확 기업/제출·구조화/분석·검토와 자산 catalog digest/관리 Version/기능 Revision을 재검증한다.
   새 릴리스/중단/새 기능 등 카탈로그 변경은 이전 자산 초안의 재검토 사유다(보수적 전역 digest 기준).
   오래된 결과는 조회하되 새 저장/매칭/제안/발송·의사결정에 재사용하지 않는다.
   회사의 기존 제안 의사결정 경로는 전달된 manifest 참조만 내부 검사하며 내부 catalog 조회 권한을 부여하지 않는다.
9. Migration은 새 테이블·FK·append-only/관계 검증과 명시 asset mode의 matching 링크 검증만 추가한다.
   과거 Migration 파일/업무행/요청·답변·승인 Trigger를 수정하지 않는다. 새 자산 이력이 있으면 downgrade를 거부한다.
   작업 소유 격리 DB에서 upgrade/downgrade/기존 데이터·trigger 비교를 검증한다. 공유 DB에는 실행하지 않는다.

## API
기존 API/응답은 유지하고 새 명령만 추가한다. 모든 mutation은 trusted origin 및 기존 인증을 검사한다.
- GET /capability/assets: ADMIN/OPERATOR 전역 읽기; kind/system/module/q/status/page 필터와 실제 출처/버전/검증 상태.
- GET /capability/assets/{id}: 버전/원천/관계/이력.
- POST /capability/assets: ADMIN만 새 SYSTEM/MODULE/FEATURE 등록, idempotency_key, data, kind, parent_id.
- POST /capability/assets/{id}/versions: ADMIN만 expected_version+idempotency로 개정, 과거 버전 보존.
- POST /capability/improvements/{vid}/asset-solutions: OPERATOR+Company Scope+정확 확인 입력/현재 분석 검토 검사 후 생성.
- GET /capability/improvements/{vid}/asset-solutions 및 /capability/asset-solutions/{id}: 같은 Scope에서 영속 결과 조회.
- 기존 POST /capability/compositions 및 versions: 위 선택적 DMP_ASSET payload, 사람 검토 의견/근거 재검증.
오류는 기존 401/403/404/409/422를 유지한다. 충돌·stale·미확인·정상0후보를 구분한다.

## 엔진/UI
기존 제한된 업무 표현·명시 제외·원문 hit를 재사용하고 시스템 이름만으로 기능을 추천하지 않는다.
재고/생산/품질/인사·근태/회계/협업·문서를 검증한다. 기능을 만들어내거나 특정 기업/ID를 정답으로 고정하지 않는다.
단일 모듈, 동일 시스템의 복수 모듈, 교차 시스템 대안을 결정적으로 만들고 중복 기능집합은 제거한다.
각 대안은 실제 기능·원문근거·요구별 Coverage·역할·예상 연결 초안·미검증 연계·남은 사항을 미리 채운다.
운영자는 비교/추가·제외·교체/수정/명시 검토 후 저장한다. 빈칸부터 전부 작성하게 하지 않는다.
관리 UI는 원천 탐색과 기술자산 등록/개정을 우선하고 기존 표준 Capability 관리는 호환 메뉴로 분리한다.
기존 3포털 디자인/공통 메뉴·파일선택·계정/권한 관리 및 미구현 표시를 유지한다.

## 인수환경/실기업 데이터
기존 8444 실행 Worktree/DB/파일/계정/기록은 직접 개발하거나 재시작하지 않는다. 8443/공유 DB/Caddy도 불변이다.
개발·자동 E2E 및 새 합성 환경은 다른 Worktree/소유 DB/Role/파일/Session/port에서 수행한다.
실기업 검증은 별도 DB/Role/files/cookie/계정/접근기록/외부송신 차단과 보존·삭제·백업 정책이 필요하다.
현재 실제 자료·보안 정책·계정/네트워크 승인은 없으므로 REAL_DATA_EVALUATION_PENDING.
자료 검색·복제·실제 업로드·외부 AI 호출·임의 방화벽/신뢰 정책 변경은 실행하지 않는다.
보안 승인 전 실제자료 입력은 금지하고 loopback 준비/합성 sentinel로 경계만 검증한다.

## 검증 계획 / 실제 실행 결과
최초 계약 시 모두 NOT_RUN이었다. 실제 명령·실패 원인·해결·증거·HEAD·CI는 아래 재개 검증 기록으로 구분한다.
기존 전체 Unit/PG/Playwright63+freshUI3·Preview/Frontend 품질과 신규 자산/0발행추천/후속제안 E2E를 유지한다.
등록·이전Revision·잘못된role/FK·제공미확인/중단·기능없음·자료부족·타기업·stale·중복/재시도를 검증한다.
합성 자동검증과 실제자료 독립 평가/사용자 최종 인수를 구분한다.

### 구현 중 교차검토로 고정한 세부 버전 계약
- 부모 node만 참조하면 부모 릴리스 변경 후 기존 제공검증이 승격될 수 있으므로 asset_versions.parent_version_id도 정확 FK로 고정한다.
- 관계는 target_node_id와 target_version_id를 함께 고정하고 변경 대상 버전에서는 effective verified=false로 표시한다.
- data.relations의 원래 검증 선언/근거는 보존하며 조회용 current_valid/effective 상태와 구분한다.
- VERIFIED 연계를 Composition에서 사용하려면 정확 조건·근거·대상 Version이 현재 등록 관계와 일치해야 한다.
- 조합 선택은 해당 생성 Run의 실제 후보에 한정하고 Coverage의 demand별 허용 기능·원문 Evidence를 Backend가 재검증한다.
- 이 보수적 부모/전체 Catalog 현재성은 이름·설명만 변경돼도 재검토를 요구할 수 있으며 과거 기록은 변경하지 않는다.

- 기술자산 조합의 정식 제안은 구체적 자산 항목을 지원하는 기존 MVP_16을 명시 사용한다.
  CAPABILITY의 기존 LEGACY_11 기본은 보존하고 새 자산 Match의 LEGACY_11 요청만 명시 거부한다.
- 자동 대안에 포함된 연계를 삭제하는 행위만으로 연계 검토가 완료되지 않는다. 남아 있는 선택 모듈의
  원래 연계/등록 의존성은 승격 시 재검증하며 미검증·빠진 의존성은 명시 차단한다.
  독립 제공 구성을 위한 별도 연계면제 정책은 추가하지 않는다(보수적 한계).

- 합법적인 기존 개선요구 원문(최대 20,000자)을 자동 Coverage에서 잘라 근거로 오인하지 않도록,
  새 DMP_ASSET Coverage.requirement는 20,000자까지 허용한다. 기존 CAPABILITY의 5,000자 제한은
  mode validator로 유지한다. 자동 표시명/역할만 API 표시 한도에 맞추며 원문·선택 자산 전체 정보는 보존한다.

### 2026-11-02 재개 시 실패 원인과 수정

- 원본 보존: 변경44파일 및 기존 실패 로그는 ignored `storage/private/resume-backup-20261102-150110`에 보호 복사했다. Branch/HEAD 일치와 임시 쓰기·읽기·삭제 1회 성공을 확인했다.
- Migration 메타데이터 실패2: 과거 스키마에서 현재 ORM과 비교하기 전에 실제 후속 fg31/gh02 Migration까지 실행하도록 보존된 chain 수정을 재검증했다. 과거 Migration이나 비교 대상 테이블을 제외하지 않았다.
- Pipeline 승인 요청503: 테스트 ORM의 schema_translate_map만으로는 기존 unqualified 승인 Trigger의 조회 스키마가 바뀌지 않았다. 테스트 소유 Session의 모든 트랜잭션에 동일 search_path를 적용해 해결했다. 제품 승인 Trigger와 Role/Scope 정책은 변경하지 않았다. 합성 실패 시 SQLSTATE/고정 오류명만 출력하며 SQL 매개변수는 출력하지 않는다.
- 단일 모듈 UI 실패: 분석 검토 원문의 '입력 중복'은 공유 검색의 일반적인 '입력/중복' 제거로 검색어가 사라졌다. `asset-solutions-v2`는 구체적인 '입력 중복/중복 입력'만 보존하며 실제 등록된 기능명·설명·업무·문제 원문에 해당 전체 표현이 있을 때 후보를 연결한다. 일반 '중복 개선', 근거 없는 재고 조회에는 연결하지 않는다. 최종 해결 상태는 여전히 사람 검토 대상이다.
- 추천 이력 API는 최신순이므로 URL 지정이 없는 초기 화면도 첫 번째 최신 결과를 선택한다. 과거 Version/Run은 그대로 조회한다.
- Backend Unit 최종367 PASS, 자산 검색 집중43 PASS, 신규 격리 Pipeline11 PASS. 최종 전체PG/Frontend/Playwright 결과는 아래와 같다. 원격 최신 HEAD 판정은 PR Checks를 참조한다.

### 최종 순차 검증

| 단계 | 실제 실행 | 결과·근거 |
| --- | --- | --- |
| Backend | pytest -m 'not integration' (로컬 OCR, 새 소유 basetemp) | 367 PASS, final-unit.xml |
| PostgreSQL | tests/slice2_local.py full | 309 PASS / 1 SKIP / 0 FAIL, 813.20초, ci/d42cc92e73dc/integration.xml; alembic upgrade/check 및 DB·Role 정리 성공 |
| Frontend | verify_api_types.py, npm run lint, tsc --noEmit, node --test tests/operator-review-unit.mjs, npm run build | API_TYPES_MATCH / lint·tsc·build PASS / 검토 Unit9 PASS; runtime/dmp-assets/final-*.log |
| Playwright | 소유 DB/API/Worker/Web의 신규 전체 UI 및 기존 전체 회귀 | 총68 PASS / FAIL0 / SKIP0: 신규 자산 전체 UI1 (2.0분, ci/208e05926e45); 전체64 (12.4분, ci/e4cee315caa8); 기존 빈 데이터 전체 UI3 (2.0분, ci/0ba4b33f977a) |
| Git/원격 | 대상 Feature Branch Commit·Push·Draft PR·최신 HEAD Checks | 로컬 결과 동결 후 실행. PR 본문/최신 HEAD Checks 및 완료 보고가 원격 판정 원천 |

PostgreSQL SKIP은 DATCO_TEST_STORED_KO=1과 저장된 실제 공고 원문이 필요한 기존 opt-in 테스트다. 실제 기업자료·외부 AI는 사용하지 않았다. 최초 재개 PG는 320 PASS/1 FAIL/1 SKIP이었고 실패는 위 Fixture search_path 수정으로 해결했으며 초기 로그와 XML은 보존한다.

별도 Shadow의 포털 Preview는 Admin20/Operator11/Company5, 총36 PASS이며 각 lint/typecheck/build 및 production Preview404 검사도 PASS다. 근거는 runtime/admin-visual-preview/dba98470-538, operator-visual-preview/799e4d5b-367, company-visual-preview/f237e0a2-839/report.json이다.

모든 최종 소유 테스트 DB/Role/컨테이너 및 API/Worker/Web/Preview 프로세스는 각 runner가 정리했다. 기존 main과 원 개발 Worktree는 clean임을 읽기 확인했다. 8443/8444 Listener는 조회 당시 관찰되지 않았고 해당 서비스 시작·중지·재시작은 수행하지 않았다. 기존 DB·볼륨·백업을 변경하지 않았다. 임시 Next.js nonce 타입 경로는 Commit 전 원래 표준 생성 경로로 정리했다.

### 최신 HEAD CI에서 발견한 시각 입력 회귀

최초 Push c7c31d4의 CI41402991396은 Backend/PostgreSQL/Frontend/3포털 Preview 6개 Job SUCCESS였으나 기존 Playwright 제안 승인근거 테스트에서 63 PASS/1 FAIL이었다. `2026-11-02T07:04:00`을 datetime-local에 입력할 때 Chromium은 초00을 생략한 표준 값을 반환하고 Playwright가 원래 문자열과 다르다고 Malformed value를 반환했다. 실패 로그는 ignored runtime/dmp-assets/ci-playwright-41402991396.log로 보존했다.

테스트 helper가 초00만 표준 분 단위 표현으로 정규화하며 실제 승인 시각은 바꾸지 않는다. 실제 Chromium에서 초00/정각/일반 초의 동일 시각 보존을 검증하는 회귀를 추가했다. `slice2_local.py proposal-e2e`의 제안서/승인 업무 포함3 PASS(52.5초), TypeScript/대상 ESLint PASS. 제품 코드·State·승인 시각의 Backend Guard 변경은 없다. 기존 로컬68 PASS와 후속 집중3 PASS는 중복 시나리오가 있으므로 합산하지 않는다. 최신 원격 전체 회귀는 신규 경계값을 포함한65개 및 빈 데이터UI3/자산UI1을 실행한다. 최종 원격 결과는 PR18 최신 HEAD Checks를 참조한다.

### 주요 변경 파일과 책임

| 영역 | 파일·책임 |
| --- | --- |
| 자산 관리·생성 | app/capability/asset_catalog.py, asset_solutions.py, asset_composition.py — 실제 원천/관리 이력, 제한 검색·조합, 저장/현재성/승격 Guard |
| 영속성·API | gh02a0012026_dmp_assets.py, infrastructure/dmp_asset_schema.py·dmp_asset_constraints.py, api/dmp_assets.py·asset_solutions.py — 추가형 테이블·typed FK·불변성·권한 API |
| 기존 흐름 연결 | capability/application.py·proposal.py, proposal/application.py·policy.py·mvp_template.py, api/capability.py, main.py·alembic/env.py — 자산 모드 명시 분기와 기존 매칭·제안/기업 전달 계약 보존 |
| 포털 | portal/dmp-assets.tsx·asset-solution-review.tsx·admin-live.tsx·operator-mvp.tsx 및 기존 회사/업무목록 공통 이동, generated/api.d.ts — 관리 등록/이력과 근거 검토·조합 편집·업무 연결 |
| 검증·문서 | 자산 검색/Catalog/Pipeline/Migration/브라우저 신규 테스트, 기존 Migration chain·포털 진입 테스트·CI, Baseline·Architecture·Decision Log·본 계약·PROGRESS — 회귀·검증 근거와 기준 동기화 |

### 사람이 검증할 항목

1. 실제 DMP 기능·릴리스·부모/관계의 제공 근거와 적용/제외조건을 담당자가 확인한다. 합성 테스트의 VERIFIED는 실제 납품 검증이 아니다.
2. 별도 인수환경에서 실제 업무 요구에 대한 추천의 누락·과다, 요구별 해결범위·미해결 사항, 16절 DOCX/PDF 내용·문서 표현과 기업 전달 절차를 확인한다.
3. 실제 기업자료 평가는 승인된 별도 격리·보안/보존 정책 후 진행한다. 이번 실행은 REAL_DATA_EVALUATION_PENDING이며 사용자 최종 인수·main 병합·공유 DB Migration·8443/8444 운영 반영은 수행하지 않는다.

## PR18 집중 검증·사용성 마무리·실기업 인수 준비

출발 HEAD는 c62e2d3b5f04ba0cce3211e1e5cda7e438fb5dc6이며 변경 없이 clean 상태에서 재개했다. 아래는 이전 자동검증 기록에 추가한 집중 보완이다. 새 전체 개발이나 기존 구현 초기화가 아니다. PR18은 PR17의 HEAD2ee2640에서 이어진 통합 결과를 포함한다. 두 PR의 자동 병합·종료, main 변경은 하지 않는다.

### 최종 선택 구성이 바뀌는 연계 위험

실제 소유 PostgreSQL/API 시험에서 **결함이 재현**됐다. 단독 대안의 원래 integrations가 비어 있을 때 같은 생성 Run의 다른 모듈 기능을 추가하거나 타 시스템 모듈로 교체하면, 최종 선택에 등록된 INTEGRATION이 없어도 검토 문구와 Coverage만 바꿔 PROPOSABLE200 → MVP16 → PDF → 기업 검토 요청200까지 진행됐다. 원래 대안의 연계 쌍만 검사한 것이 원인이다.

| 경로 | 수정 전 | 최소 수정 후 집중 시험 |
| --- | --- | --- |
| 같은 시스템의 다른 모듈 추가 | 누락 연계로 고객 전달200 | 초안 저장200, 제안 가능 판정409 ASSET_INTEGRATION_REVIEW_REQUIRED |
| 연계를 명시적으로 UNVERIFIED 저장 | 제안 가능 단계로 넘어갈 위험 | 초안 저장200, 승격409 ASSET_INTEGRATION_UNVERIFIED |
| 추가한 모듈을 타 시스템 모듈로 교체 | 최종 등록 연계 없이 고객 전달200 | 새 최종 선택의 알려진 연계 누락을409로 차단 |
| 정확한 등록 Version·조건·근거로 보완 | 기존 정상 경로 | PROPOSABLE·PDF·전달·승인자 다운로드200 유지 |

promotion_blockers는 최종 선택 모듈 쌍에 실제 등록된 인터페이스 선택지를 확인한다. 같은 쌍의 여러 방향/인터페이스를 전부 강제하지 않으며, 기존 대안에서 남은 필수 연계와 DEPENDENCY 검사는 유지한다. validate의 정확한 관계/근거/Version 검사도 유지한다. Schema·API·Role·업무 State를 추가하지 않는다.

등록되지 않은 모듈 쌍은 현재 자료만으로 독립 구성인지 필요한 연계의 누락인지 판정할 수 없다. 여기에 새 all-pairs 연결 의무나 독립 구성 면제 정책을 만들지 않았다. 실제 제공 담당자가 선택 구성의 필요 관계·근거를 확인하고, 구조화된 독립 구성 승격 정책이 필요하면 별도로 결정해야 한다. 이 미확정을 '독립 제공 검증 완료'로 해석하면 안 된다.

보호 근거: dmp-selection-risk/pre-fix-add-same-system.log, pre-fix-replace-other-system.log(의도한 red2건, nonce34bf6fa5e954/e5482b8caacd); 수정 후5 PASS/96.22초, ci/b588543f7b33/integration.xml. 기존 정확 연계/의존성 Guard도 포함한다. 실제 UI 추가·미검증·타 시스템 교체의 초안 저장과 승격 차단은 ci/2bf586ec64c7/browser-results의 synthetic-selection-change-risk.json에 별도 기록했다.

### 실제 원천649개와 합성 시험의 범위

| 자료/시험 | 확인한 것 | 확인하지 않은 것 |
| --- | --- | --- |
| 새 전체 UI의 원래 합성 원천2개 | 0발행 서비스 상태의 실제 역할/API/Worker/DB/파일/제안 E2E | 원래649개 전체의 검색 품질·실제 납품 |
| UI 위험 확장 | 위2개에 명시적 합성 관리 기능2개를 추가해 선택/교체 Guard 검증 | 원본649의 설명·제공 근거를 수정하거나 대체하지 않음 |
| Backend 위험 Fixture의 합성 기능3개 | 등록 연계가 있는 변경 구성의 성공/차단 경로 | 실제 기업/실제 공급 계약 |
| 원본649 독립 시험 | 정확 원본 import, 원문 hit·제외·답변 있음·미지원·0건·복수 분류, 실제 API/Worker 생성·초안 저장·재조회·idempotency·typed FK·원천 불변 | 추천 정답률·사업 적합성·현재 납품 확약 |

원본 SHA256은 **28b1967ed77360d0fcc6d5525f6d7395fd899865b2e01e358402edc347d1d368**로 변경되지 않았다. 649개/시스템10개/시스템×기능그룹 분류88개(서로 다른 그룹명81개)다. 이 분류88개를 검증된 배포 모듈88개라고 부르지 않는다.

설명649개와 원본의 제공 주장 AVAILABLE649개, availability_basis=USER_CONFIRMED_2026-10-14가 존재한다. 이것을 '제공 근거가 전혀 없음'으로 보고하지 않는다. 다만 정확한 관리 릴리스·부모 릴리스·현재 고객 범위의 제공 검증·등록된 의존/연계 대상·조건·근거는 원본 필드에 없고 관리 Version0건이다. 현재 투영은 NEEDS_CONFIRMATION649개이며 자동 VERIFIED는0개다.

관찰한 후보/대안 수는 물류47/8, 명시 제외15/5, 완전 미지원0/0, 불량 현황과 미지원 원인 규명6/3(부분/한계 유지), 0건 요구0/0, 이미 범위·도구·측정값이 있는 요구47/8이다. 숫자를 정답률 Gold로 사용하지 않는다. 시험은 실제 기능 원문과 근거가 연결되고 제외된 업무가 빠지며, 이미 답변한 R04/R05를 반복 요구하지 않는지를 구분한다.

독립 PG는 **2 PASS/FAIL0/SKIP0**, 20.26초, nonce87eaeef67582다. 공개 CI에 Private 원본을 복사하거나 합성2개로 대체하지 않는다. 해당 시험은 승인 원본이 없는 독립 실행에서는 명시 실패하며, 공개 CI는 기존 합성 회귀 범위를 실행한다. 원본을 가진 로컬 전체PG와 전용 asset-649-integration에서 실행한다.

보호 요약: dmp-assets/649-pg-proof/source-649-operation-scope.json. 추가 확인 목록은 source-649-review-requirements.csv(649행)에 원본에서 확인되는 설명/과거 제공 주장과 부족한 릴리스/범위/연계를 구분했다. 이것은 649개 전체 재입력·전수 사람 검토 요구가 아니다. 인수환경에서 원래 목록을 재사용하고 실제 추천·선택된 일부만 제공 담당자가 확인한다.

### 용어·조작과 실제 수작업

| 실제 합성 UI 측정 항목 | 변경 전 | 변경 후 |
| --- | --- | --- |
| 여러 연도 재무 저장 범위 안내 | 없음 | 이번 저장에 포함되는 모든 연도·기존 이력 보존 안내 |
| 재무 편집 취소 조작 | 2개 | 1개와 Escape 유지 |
| 선택2기능의 설명 확인 | 펼치기3회·닫기1회 | 기본 요약 표, 추가 펼치기0회 |
| '양성 업무 표현' 기본 노출 | 있음 | 업무 표현으로 안내, 원래 상세 근거는 펼침에 보존 |
| 모순된 해결/제공 검증 상태 옵션 | 8개 행에 혼합 표현 | 해결범위 확인과 실제 제공 상태 분리 |
| 기술 상세를 여닫는 관찰 클릭 | 6 | 2 |
| 관찰 input/change 이벤트 | 50/44 | 50/44, 감소 확인 안 됨 |

측정은 동일 합성 사례의 전후 비교이며 시간 절감이나 전체 사람 행동 수로 일반화하지 않는다. input/change는 중복 이벤트일 수 있어 합산하지 않는다. 시험은 8개 역할·8개 설명을 자발적으로 덮어썼고 이는 PARTIAL 초안 저장의 필수 입력이 아니다. 현재 Run·선택·유효한 Coverage·검토 의견·명시 확인은 필요하다. 고객 제안 단계에는 여전히 해결범위8개 판단, 제공·필요 연계 확인과 실제 미해결 해소가 필요하다. Version별 검토 의견은 감사 근거라 생략하지 않는다.

내부 오류·현재성 코드는 기본 업무 문구로 안내하며 '담당자 확인용 오류 정보' 또는 변경 상세에서 보존한다. 근거 부족·미저장·제공 불가·미검증 연계는 숨기지 않는다. 실수로 아무 API 재조회도 하지 않던 관리자 Preview용 새로고침은 실제 로그인 화면에서 감췄고, 실제 관리자 API 새로고침은 유지한다. 홈의 중복 이동도 정리했다.

변경 전 실제 브라우저: ci/70e341cd953b, 변경 후: ci/2bf586ec64c7(1 PASS/2.9분). 최종 ci/ac49c6518730도1 PASS/2.6분이며 input50/change44/click2와44개 편집 컨트롤이 같았다. 선택 기능 요약 캡처를 직접 확인했고, ASSET_CATALOG_CHANGED의 기본 업무 안내/상세 코드 보존을 확인했다. 전체65개 회귀는 실제 동시 수정409의 한국어 안내와 STALE_INPUT_VERSION 상세 보존도 통과했다. synthetic-usability-observation.json과 포털 캡처는 보호 보관한다.

### 집중 보완의 최종 로컬 회귀 — CI/실기업 인수와 별도

| 단계 | 실제 결과·보호 근거 |
| --- | --- |
| Backend 전체 Unit | 374 PASS/FAIL0, focused-final-unit.xml. 이후 준비 도구 보완 집중36 PASS/FAIL0, manual-tools-freeze.xml |
| 전체 PostgreSQL | 314 PASS/기존 저장 실제 공고 opt-in1 SKIP/FAIL0,14분13초, ci/e61124331711/integration.xml. 신규649개2건과 선택 변경3건은 SKIP 없이 포함 |
| 실제649개 독립 시험 | 별도2 PASS/FAIL0/SKIP0,87eaeef67582. 전체PG와 중복이므로 합산하지 않음 |
| Frontend | API 타입 일치, 전체ESLint, TypeScript, 검토 Unit9 PASS, production build PASS. focused-frontend.log |
| 실제 업무 Playwright | 전체65 PASS/10.6분(111a6617a62c), 빈 데이터3 PASS/1.8분(4b330f4d1c55), 자산 전체UI1 PASS/2.6분(ac49c6518730). 총69 PASS/FAIL0/SKIP0 |
| 포털 Preview | Admin20/Operator11/Company5, 총36 PASS. 각 lint/typecheck/build/production404 PASS. 332fe60b-cc0/27781a48-f26/b08fa233-59c |

모든 무거운 로컬 검증은 Backend→PostgreSQL→Frontend→Playwright→포털 Preview 순서로 진행했다. 새 실제자료는 사용하지 않았다. 이전 실패는 보호 보관하고 기대값/Guard 완화나 실패 SKIP으로 숨기지 않았다. 보완 내용은 Decision-MVP-006에 기록했다. 최신 원격 CI는 소스 동결 후 같은 HEAD의7개 Job을 확인하고 PR18 본문에 실행 링크와 결과를 기록한다. 인수환경도 같은 HEAD에서만 생성/실행하고 실제 상태를 보호 RUNBOOK과 preflight proof에 기록한다. 이 실행 기록은 기술 담당자가 유지하며 사용자에게 기술 재검증을 요청하지 않는다.

### 의존성 보안 경고의 조사 범위

2026-11-02 Lockfile을 바꾸지 않은 npm audit 전체 결과는 moderate18건이며, 단일 minimatch 권고가18개 의존 패키지에 전파 표시된 것이다. 설치/Lockfile의3.1.5·5.1.9·10.2.6은 ESLint/플러그인 및 openapi-typescript→Redocly의 개발 의존성이다. npm audit --omit=dev는0건이다. 이는 알려진 권고 조회 결과이며 안전 보장 선언이 아니다.

[공식 권고 GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249)는 <11.0.1을 영향 범위로,11.0.1을 패치로 표시하고 공격자가 glob 패턴을 제어하는 증폭을 설명한다. 검사한10.2.6 기본 최적화는1이고 TS-estree 호출은 dot:true였으며 해당 호출에서 optimizationLevel>=2는 확인하지 못했다. 영향 범위를 취소하는 근거로 삼지는 않는다.

제품 src에서 ESLint/openapi-typescript/minimatch 호출은 발견하지 못했다. 검사한 기업 업로드 경로는 digest64자리 저장소를 사용하며 lint/glob/typegen 호출 경로는 발견하지 못했다. 일반 포털은 빌드된 자산을 읽으며 개발 Preview는 production에서 실행 분기 전에404다. 현재 타입 생성은 로컬 app.openapi()이며 검사한 $ref597개는 모두 내부다. 개발/CI에 악성 glob·설정·외부 스키마가 도입될 때 가용성 위험이 남는다. 신뢰한 저장소/로컬 스키마·격리/시간제한 CI·production/loopback 실행을 유지한다. 침투시험이나 모든 공급망 위험의 검증은 아니다.

ESLint9.39.5는 [공식 지원 정책](https://eslint.org/version-support/)상 2026-08-06 EOL이다. 현재 import/react/jsx-a11y 플러그인 peer 범위는9까지이고 minimatch3에 의존하며 Redocly는5.1.9를 고정한다. 단독 ESLint10 상향이나 전역 minimatch11 override가 호환된다고 단정할 수 없어 force 업데이트를 하지 않았다. 별도 도구체인 호환 업그레이드와 audit/lint/API타입/build/Preview 검증이 남는다. 보호 감사 원문은 dependency-audit-all.json·dependency-audit-production.json이다.

### 별도 지속형 로컬 인수 준비

기존 manual_acceptance 도구에 --preparation 모드를 추가했다. 127.0.0.1의 새 HTTPS 포트만 허용하고8443/8444 및 기존 공유 서비스 포트를 거부한다. 기존 LAN 도구/환경은 전환하지 않는다. 전용 DB/Role/레이블 볼륨, files, 쿠키 namespace, Web build distDir, 계정과 감사 이력을 분리한다.

준비 모드는 정확 해시의649개만 import하고 공고0·기업0·분석/Review/조합/Proposal0건에서 시작한다. 추천 정답·기업별 분석을 준비하지 않는다. 환경 확인은 비민감 TEST sentinel만 사용하며 이후 보이는 TEST 점검 기업은 실제 동아테크놀로지가 아니다. 실제 계정은 만들지 않고 격리 시험 역할4개만 준비한다.

실행 전 Commit/내용 clean 검증, Web gateway의 nonce/HEAD, API/Worker의 HEAD/DB/Role/files 식별, TLS 공개 CA, 역할 로그인·F5·로그아웃, Scope·다운로드 차단, 원래 쿠키 거부, production Preview404, 비민감 자료의 중지/재개 후 digest 유지, 로그/Git의 sentinel·암호·세션 값 비노출을 자동 preflight로 확인한다. 로컬 HTTP 점검은 호스트 Proxy를 상속하지 않고 자식 환경에서 Live/AI 키를 제거한다. 외부 AI4종 NOT_CONFIGURED를 확인한다. 시스템 방화벽·인증서 신뢰·기존 서비스/DB/볼륨/계정/백업은 변경하지 않는다.

**실제 실행 주소·Commit·환경 식별과 준비 판정은 보호 manual-acceptance/<nonce>/RUNBOOK.md 및 evidence/preflight-*.json·browser-*.json, PR18 최종 본문을 원천으로 확인한다.** 소스/문서에 자격정보를 넣지 않는다. 사용자용 절차는 [USER_ACCEPTANCE_GUIDE.md](USER_ACCEPTANCE_GUIDE.md) 하나로 정리했으며, 사람에게 기술 점검을 반복 요청하지 않는다.

55d1e5f의 최초 새 환경60fd6287627e에서 API/DB/Worker/파일 검사는 통과했으나 브라우저 로그아웃 탐색 대기가 ERR_ABORTED로 실패했다. 네 역할의 실제 로그아웃401은 별도 비민감 진단으로 확인했다. 같은 URL 조건을 기존 회귀의 toHaveURL assertion으로 확인하도록 점검 도구만 보완했다. 업무 Guard/기대값을 바꾸지 않았다. 이 최초 환경·DB·실패 근거는 중지 보존하고 보완 커밋과 일치하는 새 환경의 원본 preflight를 실행한다. 보호 preflight-failure.txt와 진단 사본은 실제자료를 포함하지 않는다.

### 실제자료 입력 전 한 번에 결정할 항목 — 제안값, 아직 미승인

| 항목 | 제안값 | 현재 상태 |
| --- | --- | --- |
| 자료 범위/입력 | 사용자가 선정한 등록·재무 필요한2개 연도·문제/목표1건과 최소 샘플. 개인식별·계좌·서명 등 불필요한 민감항목은 마스킹. 사용자가 제품에 직접 입력 | 원본 검색·복제·업로드·Codex 열람 미실행 |
| 접근자/계정 | 지정 DATCO 담당/관리자와 회사 담당자, 필요한 승인자만 개별 계정·회사 Scope. 실제 인명/역할과 고유 자격은 사용자 확인 후 생성 | 격리 TEST4역할만 있음. 실제 계정/추가 권한 생성 보류 |
| 접속/전송 | 해당 PC loopback만, 외부 AI/유료 호출 없음. 실제 원문을 Codex 대화·도구·시험 Fixture로 보내지 않음 | 새 LAN/방화벽/신뢰 등록 없음. 외부망 전면 차단을 했다는 의미는 아님 |
| 보존 | 평가 시작 후 최대30일, 평가 종료 후7일 내 정리 검토. 원래 회사 원본은 소유자가 별도로 보존 | 기간/책임자 미확정, 자동 삭제 없음 |
| 저장/백업 | 장치/저장소 암호화 상태를 보안 담당자가 확인한 뒤 보호된 로컬 백업1본, 동일 승인 기간. 실제자료 백업·보관 위치 승인 | 도구 경로 ACL은 제한하지만 DB/파일 자체의 별도 암호화를 보장하지 않음. 실제자료 백업 미생성 |
| 삭제/복구 | STOP은 보존. 삭제는 승인 후 소유 DB·파일·백업 목록을 각각 확인해 별도 수행. 현재 CLEANUP은 DB 볼륨만 제거하고 입력/증빙은 남김 | 실제자료 삭제·기존 백업 변경 미실행 |
| 공식 공고/정식 제안 | 사용자가 선정한 실제 공식 공고·원문·기간·자격 근거가 필요. 필요 시 정식 수집 연결은 별도 승인 | 새 준비 환경 공고0, DEMO로 실기업 인수 통과 금지 |
| 등록 관계 없는 구성 | 제공 담당자가 선택 모듈의 실제 연계 필요/독립 범위와 근거를 확인. 구조화된 면제 정책이 필요하면 별도 결정 | 자동 독립 제공 확정/새 all-pairs 정책 없음 |

인수환경 준비, 실기업 독립 평가, 최종 인수는 서로 다른 상태다. 실제자료 미입력·개별 접근/보존/보안 정책 미승인으로 실기업 평가는 대기다. 공식 공고나 자격이 없으면 매칭/정식 제안·실기업 DOCX/PDF 내용 인수는 정확한 이유와 함께 보류한다. 합성 E2E나 DEMO 문서로 이 보류를 대체하지 않는다.
