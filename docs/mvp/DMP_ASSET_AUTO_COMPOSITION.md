# DMP 기술자산 관리·자동 솔루션 조합 통합 계약 및 검증 보고

기준 2ee2640836ae1fa07bf4ccf0a34d03a4f27851e0, 2026-11-02 사용자 명시 통합 보완개발 지시.
이 문서는 구현 전 영향 계약과 이후 실제 검증 결과를 한 곳에 유지한다.

> **2026-11-04 현재 상태: 04 코드 적용 후 포털 검증 실패, 사용자 검수 보류.** 기존 725는 정상 종료했고 현재 18445의 API·Worker·Web·Gateway는04다. 고정 불변 Web 실행물에 세 포털 번들6개가 빠져 수요기업 포털503을 재현했다. 이전9b 산출물도 동일 누락이 있어 복귀는 실행하지 않았다. 아래 이전의 “미적용/준비 완료/복귀 가능” 기록은 준비 당시의 관측이며, 현재 사용 가능 판정은 이 문서 끝의 실제 적용 결과가 우선한다. 원래 data-owner의 보존 문서2개는 수정하지 않았다.

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

### 사용자 단일 결정표 — 실제자료·서비스 전환은 아직 미승인

현재까지 확인된 기술 사실과 제안값을 구분한다. 아래의 ‘확인 완료’는 명시된 조사 범위의 확인이며 사용자 승인이나 실기업 평가 완료를 뜻하지 않는다. 실제자료 보호 조사는 이전 preflight/보호 보고서의 결과를 재사용했으며 원문·비밀번호·키는 조회하지 않았다.

| 항목 | 구분·현재 확인 범위 | 한 번에 결정할 제안값·최소 후속 조치 |
| --- | --- | --- |
| 적용 버전·시점 | **사용자 결정 필요**. 제품은 PR20 `04dfea4ee9d2521ba632c430c2218463df5df63c`로 고정, 기존18445는725 유지. 별도 owner adapter·불변04 Web 실행물과 검증된 이전9b 호환 복귀 경로를 준비했다. 적용 승인은 여전히 PENDING이며 아래 집중시험 근거와 중단조건을 함께 본다 | 입력·업로드·작업을 멈출 전환 창과 담당자를 한 번 결정한다. 정확 owner/plan digest·제품04·복귀9b8d0e0·승인 action/유효기간을 결합한 별도 적용 결정 후 기술 담당자가 실행한다. 문서2개·원본 manifest/HEAD·DB/files/계정/TLS는 유지한다. 실제자료 승인은 이 결정과 별개다 |
| 평가 자료·입력 | **사용자 결정 필요**, 실제자료 미사용은 **확인 완료** | 사용자가 고른 최소 자료와 문제·목표1건. 필요한 개인식별·계좌·서명 외 민감항목을 가린 평가용 사본을 사용자가 제품에 직접 입력한다. Codex 대화·도구 출력·Git·CI Fixture에는 전달하지 않는다 |
| 재무자료 | **사용자 결정 필요**.2개 연도를 필수로 하는 평가 정책은 없음 | 평가에 필요한 연도만 선택한다. 불필요한 연도/전체 자료의 재입력을 요구하지 않는다 |
| 실제 검수자·접근범위 | **사용자 결정 필요 / 기술 조치 필요**. 기존 TEST 역할은 시험용이며 개인 계정으로 자동 전환하지 않음 | 회사 담당자·DATCO 운영자·필요 승인자·자산 관리자 실명/역할과 회사 Scope를 지정한다. 승인 후 개인별 고유 자격 발급/만료·회수 방법을 정한다. 새 Role·관리자의 기업 승인 권한 확대는 이번 범위에 없음 |
| 저장 보호·암호화 | 경로/ACL/암호화 부재는 **확인 완료**, 장치 암호화는 **기술 조치 필요**. 기존 nonce의 DB는 전용 Docker named volume의 `/var/lib/postgresql/data`, 파일은 보호 runtime의 `files`, 추출문/후보/분석/생성 문서·Audit는 DB/파일에 저장된다. DB/파일 자체 앱 암호화는 없고 SHA/비밀번호 hash는 저장 암호화가 아님. runtime ACL은 PC/SYSTEM, Docker VHDX에는 CodexSandboxUsers 읽기 권한도 있었음. BitLocker는 관리자 조회 거절로 미확인 | 보안 담당자가 실제 DB 디스크·파일·파생 결과·백업의 장치 암호화 상태/접근자를 확인한다. 상태/방식만 기록하고 키·원문은 조회하지 않는다. 미확인을 암호화 완료로 바꾸거나 시스템 권한/보안 설정을 임의 변경하지 않는다 |
| 접속·외부 전송 | loopback·제품 외부AI4종 NOT_CONFIGURED/Rule 경로는 기존 점검에서 **확인 완료**. 외부망 전체 차단은 미확인 | 해당 PC 로컬 전용을 우선한다. 원문을 Codex/외부AI로 보내지 않는다. Docker 진단/registry, 브라우저·Windows·클라우드 동기화/일반 telemetry까지 전면 차단됐다고 단정하지 않는다. 실제자료 보관 경로의 동기화·접근 범위를 보안 담당자가 확인한다 |
| 보존 책임·기간 | **사용자 결정 필요 / 기술 조치 필요**. 자동 만료·전체 파생자료 정리 기능은 없음 | 책임자1명을 정하고 `min(평가 시작+30일, 평가 종료+7일)`까지 정리한다. 연장·예외는 별도 결정한다. 평가 회차/대상 목록을 보호 경로에 기록한다 |
| 평가용 백업 | **사용자 결정 필요 / 기술 조치 필요**. 실제자료 백업 미생성; 기존 백업은 열람/변경하지 않음 | 필요성·보호 상태를 확인한 평가용 백업1본만, 본 자료와 같은 보존정책 적용. DB/files/버전 메타데이터의 일관성·ACL/암호화·복구 시험 임시본 정리를 확인한 뒤 생성한다 |
| 정리·삭제 대상 | STOP/CLEANUP 의미는 **확인 완료**. 실제자료 선택 정리 절차는 **기술 조치 필요 / 사용자 결정 필요** | 회사가 보유한 원래 원본은 제외하고 평가용 업로드 사본·추출문/정정/후보·분석/추천·생성 DOCX/PDF·다운로드·캡처/증빙·로그의 사본·백업/복구 임시본을 목록화한다. STOP은 전부 보존한다. 기존 CLEANUP은 nonce DB/container/volume만 제거하고 files/입력·증빙/보호 로그는 남기므로 전체 정리로 사용하지 않는다. 승인 전 실제 삭제는 하지 않는다 |
| 공식 공고·정식 제안(B) | **사용자 결정 필요 / 기술 조치 필요**. 이전 준비 점검의 공고0 상태에서는 B 차단. 실제 공고를 이번 작업에서 조회하거나 DEMO로 대체하지 않음 | 사용자가 실제 공식 공고를 선정한다. 확인된 기존 진입은 운영자의 기업마당 LIVE 수집 `/notice/collections`이며 독립 수동 공고 업로드 기능은 확인되지 않았다. 필요한 key 소유자·조회범위·안전한 API/Worker 주입을 승인 후 준비한다. 운영 .env 복제·새 수집원·API키 임의 사용은 하지 않는다. 자격/매칭/승인·전달 Guard 유지 |
| 제공 근거·남은 정책 | **사용자 결정 필요**, 추천된 항목의 제공/릴리스/필요 연계 근거는 사람 확인 | 실제 추천·선택된 기능에 필요한 근거만 제공 담당자가 검토한다.649개 전수 재입력/전수 사람 검토는 요구하지 않는다. 관계 없는 독립 제공·연계 면제, 공고 없는/상담용 제안, 복수 승인·수행없음 확정·공식 본사 표지는 임의 구현하지 않는다 |

승인 이후의 최소 순서는 저장 보호·개인 접근 범위/보존·정리 책임 확인 → 호환 이전 실행물을 포함한 단일 적용/복귀안 확정 → 승인된 실행 전환 → 사용자 직접 입력 순이다. 개발 완료·자동검증 완료·독립 전환 시험·기존 인수환경 적용·실기업 평가·최종 인수는 서로 다른 상태다.

실기업 평가는 우선 **A: 실제자료 추출·정정·요구 분석·DMP 추천·구성 검토**로 한정한다. 입력자료·코드·룰/Parser·DMP Version을 고정하고 최초 자동 결과를 보호 보존한 다음 사람이 수정한다. 수정 전 오류·수정 내용과 판단 항목을 함께 남긴다. 평가 중 코드가 바뀌면 이전 결과를 보존하고 새로운 회차로 구분한다. 측정하지 않은 시간·입력량 감소는 주장하지 않는다. **B: 공식 공고·요건 검토·매칭·정식 DOCX/PDF·기업 전달**은 실제 공고/자격/기존 제안정책이 충족될 때 별도로 진행한다. A 통과나 합성 E2E를 B/최종 인수로 승격하지 않는다.

사람의 최소 확인은 세 묶음이다: 실제 회사 자료와 문제·목표의 일치, 추천·선택된 DMP 제공 근거/해결범위 적절성, 고객 관점 사용성과 최종 DOCX/PDF 내용(B 조건 충족 후). 반복 기술시험·649개 전체 검토를 사용자에게 넘기지 않는다. 해당 PC의 기존 접속·안전 중지/재개 안내는 원래 Worktree의 `storage/private/runtime/manual-acceptance/9ca49b473812/RUNBOOK.md`, 시험 자격 안내는 같은 보호 경로의 `CREDENTIALS.txt`에 유지한다. 자격 내용은 보고서·Git·CI에 복사하지 않는다. 사용자용 인수 안내 문서는 기존 `USER_ACCEPTANCE_GUIDE.md` 하나를 유지하며 원래 보존 중인 사본은 이번 작업에서 변경하지 않는다.
### 2026-11-03 수요기업 포털 UX 증분 — 사용자 검수환경과 분리

기준725987f4a375d4f77028e35361e4fcdb05aac4ee에서 별도 Worktree `dongalab-company-ux-20261103`, Branch `fix/company-portal-ux-20261103`로 분리했다. 기존 인수환경9ca49b473812 / https://127.0.0.1:18445에는 배포하지 않았다. 기존 Worktree HEAD/Branch와 미커밋 문서2개는 그대로다. main·PR17/18 병합·자동배포를 하지 않으며 PR18은 Draft로 둔다.

실제 Supervisor/API/Worker/Web/Gateway의 Windows CurrentDirectory 필드만 읽어 기존 root/API/API/Web/root를 확인했다. 기존 API venv는 다른 기존 Worktree의 junction이어서 함께 보호했다. 새 venv/node_modules는 별도 일반 디렉터리다. source/build/distDir/시험파일/계정·쿠키·임시DB/Role/포트·로그는 개발용으로 분리했다. 개발 PostgreSQL은 소유 label, loopback 임의 포트, CPU1/메모리512MB/tmpfs로 제한했다. 무거운 시험은 순차 실행하고 자기 시험 자원만 정리했다. Docker 재시작·WSL 종료·기존 컨테이너 조작은 하지 않았다.

검수환경에서는 익명 GET /login의 공개 환경식별과 프로세스·경로 메타데이터만 확인했다. 로그인·Playwright·기업자료 조회/주입·Migration·seed·로그아웃을 하지 않았다. 인수 자격/세션을 개발에 복제하지 않았다. 기존 문서2개의 SHA256 일치와 원래 dirty 상태를 확인했으며 START 차단을 clean/reset으로 숨기지 않았다. 보호 근거는 새 Worktree storage/private/runtime/company-ux/isolation.json이다.

| 화면 | 보완/기존 보호/남은 사항 | 검증 대상 |
| --- | --- | --- |
| A 홈 | 실제 기업명·현재 상태·과거 제출 이력 구분. 정적5단계와 바로가기를 진행률로 표시하지 않는다. 요청/제안서0건·오류·조회 중 구분 | 제출 후 새 DRAFT: 현재DRAFT1/SUBMITTED0, 과거제출1. 계정 제안 범위와 회사 공동 요청 범위 구분 |
| B 기업·사업장 | industry 원문은 상세에서 보존, 업태/종목 호환 유지. 필수/선택·재조회 확인·실제 사업장명/주소 | 미저장 재조회 취소/수락·저장본 증가 없음. 별도 본사flag가 없어 추정하지 않음 |
| C 재무 | 단일/기존 입력의 다중연도 안내 제거. PDF에서 받아들인 연도만 저장범위 표시. 기본5항목 우선, 선택금액 빈값null/실제0 구분 | 이전 버전에서 선택금액 입력 후 삭제 시422 관찰. 작성 기준 ordinal의 Profile에서 재무 collection만 반영, 다른 연도/수행이력/이전Version 보존 및409 |
| C 단위·닫기 | Backend의 상세금액 원/KRW 계약 표시, 다른 단위는 상세입력만 제한하고 기존값 보존. 실제 변경/PDF 초안에만 닫기 확인/F5 경고 | 기존 단위 매출의 편집·저장 보존, 자동환산 없음, 미저장 닫기 취소/수락 |
| D 수행이력 | 정부지원사업 수행이력 제목, 사업명/기관 우선, 날짜 필수·역전 안내. 미등록과 수행없음 확인 구분 | 실제 저장/재조회/재무 보존. 수행없음 확정 기능은 기존 계약에 없어 정책 미해결로 남김 |
| E 개선요구 | 작성 중 중복 신규 버튼 제거, 필수/선택·제출 불가 사유·실제 해제 시 안내. 닫기 확인/내부 이동 초안 보존 | 첨부 없는 DRAFT 저장, 미저장 복원. 허용 형식/개수/크기와 분석 차이. 기존 제출/Version Guard 유지 |
| F 자료함 | 파일 선택 취소와 자료 등록 해제 구분, 선택 후 명시 교체 적용. 파싱 시도와 저장된 실제 연결 구분 | 원본바이트/Evidence/과거 제출 보존, 교체 실패/응답 유실 후 재시도·재로그인·재제출. 새 업로드/재연결 기능 없음 |
| G 요청·제안 | 회사 공동 요청과 내 계정 전달본 범위 구분. 조회 실패≠0건, 기존 역할/방식/현재 전달본 조건에서만 승인근거 입력 | 실제 답변/운영자 검토·전달본 본문/다운로드/승인근거. 권한/최종 전달 Guard 유지 |

공통 업로드·모달·전역 내비게이션 구현은 바꾸지 않았다. 기존 FileSelection을 보완답변 편집 영역에서 재사용하므로 운영자 보완답변 검토와 관리자/운영자 실제 화면도 회귀한다. Schema·Role·State·추천 엔진을 바꾸지 않았다. 시간·입력량 감소를 측정하지 않았으므로 감소 수치를 주장하지 않는다. 화면별 Gap은 GAP_MATRIX의 같은 날짜 절에서 이어 관리한다.

#### 기존 주소·계정·자료를 유지하는 향후 일괄 적용/복구안 — 미실행

사용자 검수 종료 후 정확한 보완 Commit·적용 시점을 한 번 결정한다. 기존 문서2개·725987f 실행 source/build/설정 식별과 새 Commit의 별도 build/deps, 데이터 소유권과 복구 경로를 먼저 고정한다. 같은 API/Schema 계약을 사용하므로 Migration/seed/DB초기화·비밀번호 발급·재입력 없이 기존 DB/볼륨/files/권한/이력을 유지하는 실행 전환이 목표다. 주소18445·인증서·계정·비밀번호를 유지한다. 최소 Web 교체의 짧은 중단이 필요하며 API/Worker 버전 일치 전환이나 재로그인 필요 여부도 적용안에 명시한다.

현재 lifecycle 도구는 root/HEAD/clean source를 검사하며 별도 실행 source-root 전환 명령을 제공하지 않는다. 따라서 임의 manifest 수정으로 버전을 맞췄다고 하지 않는다. 적용 전 별도 실행 root/정확한 HEAD/build와 기존 데이터 소유 root를 구분하는 보호 전환 수단을 준비·검증해야 한다. 기존 미커밋 문서는 정확한 바이트로 보존·통합할 대상이며 Guard의 임의 예외로 제외하지 않는다. 이 조건이 충족되기 전에 기존 RUNNING 환경을 정지하지 않는다.

복귀는 이전725987f 실행물과 정확한 설정/Guard 검사로 코드 실행만 되돌린다. 보완 이후 정상 저장된 업무자료를 과거 DB로 되감지 않는다. 자기 소유 실행 프로세스만 대상으로 하며 Docker/WSL 전체 재시작·DB/볼륨 삭제·자료 재입력은 복구안이 아니다. 실제자료 사용·개인 계정·공고 없는 제안 정책은 이 UX 적용 결정과 별개다.

#### UX 증분의 실행 근거와 변경 전후 관찰

| 검증 | 확인 결과·보호 위치 |
| --- | --- |
| Backend 전체 Unit |374 PASS/FAIL0, unit-final.log/xml. 승인 기술목록649개의 동일 SHA256만 독립 개발 ignored 경로로 재사용. 새 기술원천 검증을 대신한 합성 정답·기업자료는 없음 |
| 관련 PostgreSQL/HTTP |40 PASS/FAIL0, ci/e6bb777bbd12/integration.xml. 일회용 DB의 Migration/check, 동시 Profile409·권한·교체 실패 rollback·제출 원본/Evidence 보존·등록 OCR |
| Frontend |API_TYPES_MATCH, ESLint/TypeScript·검토 Unit9 PASS, 최종 production build. company-ux 아래 api-types/frontend-* 로그 |
| 실제 API/DB/Worker/UI |최종 제품 소스의 ci/575d9207d183에서26 PASS/조회지연 시험1 FAIL. 시험의 route 해제 순서만 수정 후 ci/6441a2e4b98d의 동일1건 PASS(7.7초). 서로 다른27개 사례를 확인했으며 단일 실행27 PASS라고 표기하지 않는다. 실제 저장/문서/파일·역할 경로는 Mock으로 대체하지 않음 |
| 운영자·관리자 영향 |위 회귀에 관리자 요약/카탈로그/접근부여·외부상태, 운영자 기업자료/요구 검토/보완답변·매칭/문서/전달,3역할 로그인/F5/로그아웃·계정교체/세션폐기/다운로드 차단 포함 |
| 원격 전체 회귀 |새 증분 PR의 정확한 최신 HEAD Checks가 원천. 기존 PR18/725987f의7개 성공과 이번 브랜치 결과를 혼동하지 않음. main대상 외 기존 feature branch대상 PR에도 필수 DATCO CI가 실행되게 base filter만 추가, 시험 목록/Guard 유지 |

변경 전 관찰은 개발 Worktree의 제품9파일을 보호 복사한 뒤725987f의 정확한 원본 바이트로 별도 합성 환경을 실행했다. 종료 후9파일 수정 바이트의 SHA256 일치까지 확인해 복원했다. 현재 검수 Worktree를 checkout/수정하거나 인수환경에서 Playwright를 실행하지 않았다. 이전/이후 관찰에서 같은 종류의 합성 회사 자료(재무2023/2024·수행이력1건)를 사용했다. 별도 실행이므로 기업 ID/임의 TEST 이름은 다르며 실제 기업 평가가 아니다.

| 실제 관찰 항목 | 이전725987f | 보완 제품 |
| --- | --- | --- |
| 홈의 조회 기업명 heading / 정적5단계 |0 /1 |1 /0 |
| 기존 업종 일반 노출 |보임 |상세에서 열람 |
| 단일 신규 연도: 저장 범위/행 선택 UI |각1개 |각0개 |
| 선택금액 입력 후 지운 저장 |422 / Profile1본 |200 / 새 Profile2본, 기존2023·2024와 수행이력1건 유지 |
| 작성 중 중복 신규 버튼 / 첨부 없는 해제 안내 |각1개 |각0개 |

이 표는 관찰 수치이며 업무 시간·입력량 감소 측정이 아니다. 원본 화면8개와 관찰 JSON은 보호 ci/d88f80099e0e/browser-results(전), ci/575d9207d183/browser-results(후)에 보관했다. 01-home.png/03-finance-single.png/04-history.png/05-need-draft.png 등을 실제 이미지로 확인했다. 미저장 모달·좁은 화면·파일교체·운영자 보완 검토 캡처도 같은 실행 산출물에 있다.

정적 검토에서 추가 확인한 PDF 선택 유실 경로와 기업 조회상태 혼동은 새 브라우저 사례에서 검증했다. 잘못된 새 PDF는 기존 선택을 먼저 지우지 않으며 입력 전환 취소 시 초안을 유지한다. 기업 조회 중/503·정상0건·복수기업 미선택도 구분한다. 기존 연계/제안 Guard·Schema/Role/State는 바꾸지 않았다.

실패를 SKIP이나 저장 기대값 완화로 없애지 않았다. 초기 Unit의 비공개 기술목록 누락은 동일 해시 원본의 재사용으로, OCR2건은 기존 Tesseract 실행 이미지 선택으로 해결했다. UI 최초16 PASS/5 FAIL(ci/c1a8de0cf967),23 PASS/2 FAIL(ci/a0b7b75eb1f3),26 PASS/1 FAIL과 최종 해당1 PASS의 로그·오류문맥을 보호 보관했다. 원인은 새 확인 대화상자/업무 문구 선택자·집중 시험의 선행 기업등록 의존·지연 시험의 route 해제 순서였다. 실제 바이트/Version/Evidence/409/권한 기대는 유지·추가했다.

남은 의사결정은 수행없음 확정 계약·공식 본사 표지·실자료 사용/계정 정책 및 적용 시점이다. 별도 계약 없이 가짜 이력·본사 여부·공고 없는 제안·새 Role을 만들지 않았다. 현재18445와 문서2개의 기존 START 차단은 이 수정 적용과 별개이며 사용자 검수 종료/단일 적용 결정 전에는 실행 전환하지 않는다.

#### 최신 전체 CI의 추가 발견과 후속 수정

9ea5df4의 원격 Public E2E는70 PASS/5 FAIL(8.3분), 다른6개 Job은 SUCCESS였다. 이 결과를 전체 성공으로 보고하지 않았다. 보호 사본은 company-ux/ci-9ea-failed.log(SHA256 f952bf9b048feb3fa54388caa7c5ad6f400c2eec8ca21ed626016964b945ec56)이며 원격 실행41559310452/job125666085848도 보존한다.

- 3건은 보완요청의 변경된 업무 문구와 FileSelection 추가 상태를 너무 넓게 찾던 선택자였다. 정확한 빈 상태/차단 문구와 답변 영역의 직접 자식 저장상태를 검사하도록 수정했다. 저장횟수/파일바이트/404/Version 기대는 유지했다.
- Stage B/C의 초기 목록 불일치는 신규 UX 시험이 기존 handoff editor를 공유해서 생겼다. 새 UX 전용 합성 ux_editor를 별도 생성하고 기존 초기 목록[] 검사는 유지했다. 실제 인수 계정에는 손대지 않았다.
- Stage A의 사업장 추가 실패는 실제 UX 결함이었다. 저장한 JSONB와 편집 객체의 키 순서 차이를 변경으로 판단해 불필요한 미저장 확인이 떴다. 별도 df64bde9308d에서 저장 후 추가 시 확인창이 뜨는 것을1 FAIL로 재현했다. 사업장4필드의 값으로 비교하고 성공 응답의 정확한 저장값/ordinal을 편집본에 반영하는 최소 수정으로 해결했다. Backend/API/Schema/State/동시수정 Guard 변경은 없다.

수정 후 신규 UX11개와 기존 운영자 접수2·handoff3·보완요청3, 총19개 관련 실제 브라우저 사례가 한 번의 격리 실행에서19 PASS/FAIL0(2.2분)였다. 저장 직후 다음 사업장 추가,2개 사업장/재무/이력/재로그인, 기업→운영자 동일 Version/파일바이트,409·응답 유실·첨부 재시도/이전 Evidence도 포함한다. followup.log/해당 ci browser-results에 근거를 보존했다. 앞선27개와 중복되므로 숫자를 합산하지 않는다. 이어 최종 lint/TypeScript/production build를 다시 확인하고 새 HEAD의 전체 CI를 PR19 Checks에서 확정한다. 이전 커밋의6개 성공을 새 HEAD 전체 성공으로 대신하지 않는다.

최종 후속 소스에서 lint·TypeScript·production build도 PASS였다. 실행하지 못했던 별도 전체 경로는 순차 실행하여 reacceptance-full-ui3 PASS/1.8분(ci/c75aa6691255), dmp-auto-solution-full-ui1 PASS/2.7분을 확인했다. 재무 여러 PDF·16절 DOCX/PDF·기업 수정 요청·세 포털 좁은 화면/키보드·파일 선택 취소/거부가 포함된다. 사업장 요약과 전달본 문구를 현재 화면에 맞춘 선택자만 정렬했으며 실제 사이트1건·승인/파일/Version/의사결정 상태 기대는 보존했다. 최종 관련19개 근거는 ci/6a9786e3c639다. 새로운 전체 인수환경 생성·사용자 계정 변경·실제 기업자료 사용·18445 적용은 하지 않았다.

0829121의 원격 전체 UI는75 PASS/1 FAIL(7.8분), 다른6개 Job은 SUCCESS였다. 남은 실패는 mvp-portals의 회사 수정요청 성공 검사에서 서버 처리 상태와 제안서 재조회 상태가 동시에 보일 때 광역 role=status가2개가 된 선택자 문제였다. 제품 코드를 바꾸지 않고 정확한 성공 메시지를 필터링하여 해당 실제 문서 전달/기업 수정요청1건을 재실행해1 PASS(26.5초) 확인했다. 실제 REVISION_REQUEST·파일2개·정확한 Version 기대는 그대로다. ci-082-failed.log(SHA256 20d7a2af671a8a9d6a8606e3ba19937d3826e47b8cc63d8024e3a57722f1e077)와 mvp-status-final.log를 보존한다. 최신 전체 합격 여부는 이 시험 보완 커밋의 PR19 Checks/본문으로 확정하며 이전6개 성공을 재사용해 최신7개 성공이라고 하지 않는다.

### PR19 이후 후속 범위와 공통 영향 — 구현 전

출발 PR19의 정확 HEAD는0b6f56a88131a10fdc9c4cb16ed7658250275b03이며 원격과 일치한다. 별도 dongalab-quality-20261103 / fix/portal-analysis-quality-20261103에서만 진행한다. 완료 기준은 GAP_MATRIX의 Q01~Q06으로 고정했다. 기존 A–G 결과·문서2개·PR17/18/19/main·18445/8443/8444와 기존 데이터/실행물을 보존한다. 실제자료 평가·배포 완료를 목표에 섞지 않는다.

구현 전 공통 영향은 다음과 같이 제한한다. 세 포털 공통 UI/로그아웃은 기존 인증/세션 API와 Role/Scope를 유지한 클라이언트의 실제 미저장/처리 중 상태·확인 경로를 우선 재사용한다. 진행 결과 불명/로그아웃 실패를 숨기지 않는다. 추천/OCR/Parser는 기존 Source/Evidence/Review/Manifest·규칙 버전 경계를 유지하며 사람 확인/제공·필수 연계/제안 Guard를 바꾸지 않는다. Excel 갱신은 기존 import·원천 Revision·관리 자산/Version을 먼저 대조하고, 새 저장/API/Schema가 필요한 경우 정확한 변경·범위를 이 문서에 추가한 뒤 구현한다. 승인되지 않은 관계/제공 정책은 만들지 않는다.

전환 수단은 실행 코드 식별과 데이터 소유를 분리하는 최소 lifecycle 증분만 허용한다. 새 합성 환경에서 검증하며 현재 인수환경의 START·manifest를 수정해 버전을 맞추거나 중지하지 않는다. 새 코드의 정상 저장자료를 옛 DB로 되감지 않는 복귀와 DB 호환성 검증을 완료조건으로 둔다. 구체 구조/API 영향은 기존 도구 조사 후 확정한다.

### Q04·Q06 상세 계약 — 구현 전 영향 기록

Q04는 관리자 전용 `POST /capability/asset-imports/preview`(XLSX binary·X-Upload-Name·20MB), `POST …/apply`(파일/Parser/Catalog/Preview digest·선택 행·명시 연결 또는 NEW·Idempotency), `GET …/{sha}/original`을 추가한다. safe OOXML과 제한된 표 헤더, 명시된 세로 병합 분류만 지원한다. 기존 PrivateFiles·업로드 Audit·원천 imports/features/revisions/members를 재사용하며 물리 Schema와 관리 부모·제공 VERIFIED·업무 권한은 변경하지 않는다. Metadata의 optional workbook_provenance와 생성 API 타입만 확장한다. 내용 동일 시 Import/Revision/Catalog는 변경하지 않고 새 업로드 위치는 Audit로 보존한다. 파일 SHA와 부분 선택 적용 batch digest는 구분한다. 누락 행 자동 삭제·중단은 하지 않는다. 원래 649 JSON의 엄격 검증과 해시는 유지한다.

Q06은 기존 START/manifest를 고쳐 통과시키지 않고 별도 선택형 release 도구를 추가한다. 원래 data-owner manifest는 변경하지 않고 실행 Worktree/Commit/빌드 해시를 별도 immutable release 기록으로 고정한다. 동일 Git 저장소, clean source, 소유 label·loopback, DB migration/schema와 의존성 잠금의 호환성을 시작 전에 확인한다. API·Worker·Web은 새 실행 root, DB·파일·TLS·세션 namespace·계정은 동일 data-owner를 사용한다. 실패 시 같은 DB/파일 위에서 이전 실행물을 재시작하며 DB를 과거 백업으로 되돌리지 않는다. 준비/build 검사는 서비스 중지 전에 수행한다. 기존 비선택 환경의 START는 그대로이며 release 선택 환경만 별도 도구로 안내한다. 18445·8443·8444와 기존 환경은 이 작업에서 등록·중지·적용하지 않는다. 실제 적용 전 보존 문서와 데이터 소유권·전환 승인을 별도로 확인한다.
Q04 증분 등록의 목록 영향: 기본 `/capability/features`는 모든 원천 root의 최신 Revision을 보여주는 현재 목록으로 명확히 한다. `import_id` 명시 조회는 과거 등록 batch의 고정 member Snapshot을 그대로 유지한다. 최근 등록 batch metadata와 전체 현재 목록 건수를 구분한다. 기존 원천의 member를 새 Excel batch에 억지로 추가하지 않으므로 원문에 없는 파일 위치·제공 근거를 새 출처로 만들지 않는다. 물리 DB/역할/과거 Snapshot 변경은 없다.

Q05 독립 holdout 최초 회차(24건)는 원본 PR19 9통과/15불일치, 1차 보완 12통과/12불일치로 원결과를 보존했다. 이 수치를 실기업 정확도로 해석하지 않는다. 업무 적용조건이 없어서 질문하지 않는 NOT_APPLICABLE을 FOUND로 기대한 3사례(4개 진단 assertion), TXT의 줄별 Location을 단일 Location으로 기대한 1건은 평가 계약 오류로 따로 분류한다. 넓은 자유문장 숫자/기간 문법 5건은 지원되지 않아 실패로 남긴다. 같은 문장의 긍정 요구에 다른 업무의 제외를 전파하는 결함과 후반의 명시 미정 예산 반복질문은 새 회차로 수정한다. 1차 입력·정답·제품별 결과는 덮어쓰지 않으며 이후 회차는 미사용 독립평가가 아니라 이미 노출된 회귀자료다.

Q02 실제 브라우저 추가 재현: 원천 SYSTEM/MODULE의 source-system:<24hex>/source-module:<24hex> 식별자를 기존 Web proxy가 colon 때문에400으로 차단했다. 기존 Backend 읽기 계약을 맞추기 위해 GET /capability/assets/{id}의 정확한 두 원천 ID 형식만 예외 허용하고 경로 구성요소를 encode한다. POST·다른 경로·임의 colon·권한/Scope 계약은 유지한다. 목록 조건 변경 중 과거 결과를 현재 결과처럼 클릭하지 않도록 현재 조회 조건의 응답만 목록으로 표시한다. 새 inventory 기본 범위의 관리기능 rawroot1 증가와 과거 import Snapshot 불변을 각각 시험한다.

Q06 JSON 자료 호환성 추가 재현: f49dbd8 및 기존 725 계열의 엄격한 Metadata DTO에는 workbook_provenance가 없으므로 새 Excel 등록 후 과거 코드의 목록 응답이 실패할 수 있다. 물리 Schema·lock 동일만으로 복귀 호환이라고 판단하지 않는다. 실제 환경/DB를 읽지 않고 과거 Git 코드와 합성 Metadata로 extra_forbidden을 재현했다. 도구는 source별 합성 Metadata roundtrip reader·해당 writer format을 기록하고 양방향 호환이 확인되지 않으면 중지 전 전환을 거부한다. 리허설은 새 호환 baseline Commit에서 생성하며 실제 기존725 코드로 무조건 복귀 가능하다고 주장하지 않는다. 실제18445 적용은 호환되는 이전 실행물 확보와 기존 START/owner 계약 정합화까지 확인한 뒤 별도 결정해야 한다. 운영 DB Migration·자료 변경·기존 manifest 수정은 하지 않는다.

### 후속 집중 검증 기록 — 실자료·실환경 적용과 분리

Q01/Q02/Q03은 정확한 과거 제출 Version·당시 사업장·메뉴 목적·상태/차단 해결 위치, 보완요청 선택에서 작성폼 연결, 실제 dirty/busy/uncertain에 따른 공통 종료를 보완했다. 저장된 분석 검토가 이미 재조회됐는데 이전 dirty 상태가 작성폼 이동을 막던 race도 재현·수정했다. 원천 상세의 proxy400과 화면 밖 결과를 별도로 재현했고 즉시 보이는 결과·처리/오류·원천/관리 이력 구분·종류별 소속 안내·짧은 행 요약으로 수정했다. 기본 행에서 줄인 설명과 식별자는 상세에 보존한다. Preview는 인증 API/쿠키 없이 같은 dirty 종료 확인을 공유하며, 반영본 유지·미반영 폐기는 별도로 검증한다.

Q04는 20MB 이하 XLSX, 최대5000행·20000셀·확장64MB·ZIP2000항목 제한을 사용한다. 첫 행의 system/시스템, feature_group/기능그룹/모듈, name/기능명/기능, description/기능설명/설명과 optional feature_id/원천기능ID를 지원한다. 분류 두 열의 명시 세로 병합만 상속한다. 중복/빈 시트명·중복 헤더는 거부하고, 수식·도형·이미지·묵시적 빈칸 상속·그 밖의 계층은 성공으로 집계하지 않는다. 명확한 신규·변경은 묶음 검토, 예외는 업무명 선택으로 연결하며 다른 ID는 상세에서 입력한다. 원본·셀 위치와 선택한 정확 Revision을 Audit에 보존한다. NOOP는 import/revision/catalog digest를 바꾸지 않는다. 신규 관리 FEATURE가 rawroot1개를 만드는 기존 경로 때문에 CURRENT_CATALOG는1건 늘 수 있지만 원본 import_id 전체 Snapshot과 기존 Revision은 완전히 일치함을 검사한다.

검증 구분:

- Backend 전체 unit 406 PASS(당시 소스). 후속 workbook pure6, 평가도구/분석39, release/기존도구80 PASS는 겹치는 사례가 있어 합산하지 않는다. 최종 전체는 최신 PR CI로 확정한다.
- 로컬 PostgreSQL 전체 첫 실행은284 PASS/4 FAIL/28 ERROR/기존 실제공고 opt-in1 SKIP. 512MB tmpfs 시험컨테이너 OOM2건을 Docker 이벤트로 확인했다. 1GB 재실행은309 PASS/3 FAIL/4 ERROR/동일1 SKIP였고 PostgreSQL signal9·OOMKilled=true를 보존했다. 성공으로 처리하지 않았다. 메모리 DB자료를 새 소유 디스크 볼륨으로 분리하고512MB/CPU1 한도로 실패7건+최종 workbook2건을 재실행해9 PASS(50.32초)를 확인했다. 같은 사례의 재실행을 더해 단일 전체 합격으로 보고하지 않는다. 기존 DB/볼륨은 변경하지 않았으며 새 시험 디스크 볼륨도 삭제하지 않았다.
- 원래649개 승인 JSON은 SHA256 28b1967ed77360d0fcc6d5525f6d7395fd899865b2e01e358402edc347d1d368 그대로2개 원천 전체 투영·탐색/제외·답변/0건·Worker 조합 생성·저장/재조회 시험을 통과했다. 기능 설명이나 제공 근거를 바꾸지 않았다. 전체UI의 합성 원천기능2개 및 별도 합성2행 Excel 시험과 구분하며 실제 Excel 원본의 경로·해시나 실기업 추천 정답을 검증했다고 하지 않는다. 실제 제공/릴리스/연계 증거가 없는 항목은 NEEDS_CONFIRMATION으로 남긴다.
- API 타입 일치, ESLint, TypeScript, 검토 unit9, production build PASS. 이후 UI 수정은 타입검사와 실제 Chromium으로 확인했으며 최종 빌드는 최종 source/CI에서 다시 식별한다.
- 집중 Chromium 초기6 PASS/6 FAIL: 원천proxy400 제품결함, 저장 후 이동 dirty race 제품결함, CURRENT_CATALOG 계약과 다른 옛 immutable 기대1건, 실제 보호 history가 없는 뒤로가기 시험준비3건으로 구분했다. 불변성/세션 차단 기대는 강화했고 timeout/기대값 완화나 SKIP으로 숨기지 않았다. 수정 후 동일12건12 PASS(1.1분): 실제 Web/API/Worker/PG, source SYSTEM/MODULE/FEATURE GET200, 관리 자산 이력, 명시 원본 Snapshot 전부 불변, 반영 응답 유실/중복0, 과거 제출 Version·당시 사업장·6메뉴/F5, 요청 작성, clean3역할·실제dirty·처리중·불명·실패·revoked cookie·다중탭·뒤로가기/F5/직접URL 차단을 포함한다. 지연/503 위치 시험만 명시적 UI 응답 제어이고 정상 저장 성공은 실제 Backend다.

Q05 품질 결과는 고정 개발29사례에서 원래17/29→1차29/29(내용27·정상거절2), 최초 미사용 합성 holdout24에서는9/24→12/24였다. 원래 결과·gold는 그대로 보존했다. 정정 회차는 H07/H08/H09의 적용조건 없는 진단 강제3사례(4 assertion), H24의 TXT 줄별 Location1사례를 평가 계약 오류로 명시하고 같은 입력을 유지했다. 이 이미 노출된24사례의 같은 정정 기준에서는 원본13/24→1차16/24→최종19/24, 최종 내용16/21·정상거절3·미지원 자유문장 숫자/기간5실패(10 assertion)다. +4의 gold 정정과 +3의 실제 후속 코드 개선을 섞지 않는다. 처리 예외0, 불리한 사례 삭제0. 버전은 improvement-rules-v6 / asset-solutions-v4 / published-solutions-v4다. 최초 source는0b6f56a,1차는fa5af07,후속품질은55ca6f5에 보존했다. 고정 합성 JSON은 .gitattributes -text로 원래 바이트 SHA를 Git에서도 확인했다. 이는 유한한 합성 회귀이며 OCR/실기업 정확도·운영자 수정 시간·입력량 감소를 측정한 결과가 아니다.

재사용한 경로는 사업자등록 전용 PDF/OCR·재무 NTS section/code/label/단위/기간·일반 첨부 parser, 원문/Evidence/Review/Manifest·회사 ACK·운영자 CONFIRM·제공/필수연계·정식제안/전달 Guard다. 새 OCR/외부AI나 관계 면제 정책을 만들지 않았다. FACT evidence는 원문 value quote를 유지하고 불변 Fact의 period/unit/currency만 추가한다. 추천은 원문 역할과 명시 제외를 유지하며, 실제 등록 기능 인용으로 업무/해결범위·제외/미확인을 설명한다. 자동 초안 이후 사람은 실제 적합 범위/예외·제공/릴리스·필요 연계·최종 문안을 판단해야 한다. 화면/규칙이 미리 채운 항목 수를 실제 수작업 감소로 주장하지 않는다.

Q06 실행 검증은 다음 고정소스의 신생 비민감 owner에서만 수행한다. reader/writer v2계약이 없는 기존725/18445,8443,8444는 도구에서 거부한다. 실제 기존 인수환경은 익명 login200·기존HEAD725·원래문서2개 해시/프로세스 경로만 확인하며 로그인·업무자료 조회·변경은 하지 않았다. 기존 START/manifest/보존 문서를 삭제하거나 고쳐 가드를 우회하지 않았다. 독립 실전환·새저장·복귀·실패복귀의 완료 여부/정확 소스·중단 관측은 이어지는 검증 기록과 최신 PR 본문으로 확정한다.

#### Q06 빌드 무결성 재현과 최소 보완 계약 — 실행 전

독립 비민감 owner `2002c1fabb87`의 두 시험 회차는 통과하지 않았다. 첫 회차는 파일별 조상경로 검사를 반복하는 해시 계산이 시작 제한시간을 넘겼다. 경로별 링크 검사를 유지한 O(N) 구현으로 바꿨으며 기존 정규 해시 계산과 결과가 같음을 검사했다. 두 번째 회차는 원래 기록된 Next 빌드와 실행 후 빌드의 해시가 달라 `RELEASE_BUILD_CHANGED`로 중지 전에 거부됐다. 실제 원인은 Next.js가 로그인 응답을 만들며 `server/route-cache/APP_PAGE` 6개 파일을 생성한 것이었다. 원래 release 기록·owner manifest·실패 로그는 그대로 보존했고 동일 DB·파일은 STOPPED 상태로 남겼다.

최소 보완은 v3 release에서 검증된 빌드 원본과 실행 복사본을 분리하는 것이다. fresh `--build` 뒤 `.next` 산출물·생성된 public 파일·package/config의 파일별 manifest와 전체 해시를 owner 보호 경로 `release-artifacts`에 고정한다. 시작할 때마다 `executions`의 새 실행 폴더로 링크 없이 복사하고 초기 바이트 일치를 검사한다. Next는 그 실행 폴더에서만 캐시를 갱신한다. 원본의 route-cache를 무결성 검사에서 제외하거나 예전 기록의 해시를 고쳐 통과시키지 않는다. `.env`, 키, node_modules는 복사하지 않는다. API/Worker의 코드 경로와 Web의 실행 복사본·원본 Commit/산출물 식별을 구분해 기록한다.

v2 기록은 불변 owner anchor 검증에만 재사용한다. 손상되거나 실행 중 변한 옛 산출물은 일반 시작·전환으로 허용하지 않는다. 별도 `recover`는 같은 owner가 STOPPED이고 cleanup·PID·port 정리가 확인된 경우, 원래 owner의 정확한 source/HEAD·lock·Schema·자료형 호환성과 fresh v3 빌드를 검사한 뒤 새 baseline 선택을 만든다. 이전 선택은 사용할 수 없는 과거 기록으로 보존한다. 이 경로도 DB·파일·계정·TLS를 교체하거나 Migration·Seed·초기화하지 않는다. 실제18445의 등록/적용 승인을 뜻하지 않으며 동일 합성 owner에서만 복구·전환·후속 저장·복귀·시작 실패 복구를 이어서 검증한다.
Preview a4ada3c CI의 원결과는 Company SUCCESS, Operator11 PASS/2 FAIL, Admin21 PASS/2 FAIL이다. Admin 자체 사례는 통과했으며 실패2개는 Admin harness가 같이 실행한 같은 Operator 사례였다. 예시·기업·사업장·과제 초기화 때 요청 문안만 지우고 비교 기준을 남겨 clean 상태를 dirty로 판단하던 실제 결함은6454ca3에서 두 값을 함께 초기화하도록 수정했다. 이미 존재하는 textarea의 정확 label 선택자가 중첩 자식 텍스트 때문에 실패한1건은 정확한 textbox 역할/접근성 이름으로 정정했다. 기존 dirty/계속 작성/폐기/재진입·API0/쿠키0 기대와 timeout은 유지하고 맥락 전환 검증을 추가했다. TypeScript/관련 ESLint PASS이며 수정 후 Preview 성공은 이어지는 최신 CI로만 확정한다.
a4ada3c의 DATCO CI는 Backend438 PASS/1 SKIP/5 integration deselected, PostgreSQL326 PASS/기존 실제공고 opt-in1 SKIP, Frontend 타입/lint/unit9/build SUCCESS였다. Backend SKIP은 CI에 비공개649 원본을 넣지 않는 기존 optional-source 검사이고 실제649 검증은 위 로컬 원본 시험과 구분한다. Public E2E는80 PASS/7 FAIL(16.6분)로 전체 합격이 아니다. 새 세션6사례·운영자 집중3사례는 통과했고, 남은7경로는 기존 기업 선택/정확 제출 맥락 유지와 옛 UI 기대·시험 준비의 충돌을 대조해 최소 수정한다. 이 원결과와 보호 원로그는 남기고 최신 HEAD의 전체 CI를 별도로 확정한다. 의존성 설치 경고18 moderate도 계속 표시됐으며, 앞선 개발 도구 minimatch 조사/production audit0의 범위를 넘어 안전하다고 선언하지 않는다. 무조건 force 업데이트는 하지 않는다.
v3 정식 복구 전에 자체 소스의 Web 복사본만 별도 비민감 보호 경로에서 점검하던 중 Windows 긴 경로의 파일 쓰기가 `FileNotFoundError`로 실패했다. deep server/app segment 파일에서 발생했으며 Node·DB·release 전환은 아직 시작하지 않았다. 이 실패도 보존하고 시스템 long-path 정책/권한을 바꾸지 않은 파일 I/O 보완과 실제260자 초과 경로 회귀를 먼저 확인한다. 기존 owner·원본 산출물·계정/TLS·자료는 변경하지 않았다.
a4ada3c의 Public E2E 실패7건은 d27aa88의 test-only 보완으로 동결했다. 현재 기업·제출 Version을 유지하는 메뉴 이동을 먼저 검증한 뒤 기존 수요기업 목록으로 명시 재선택하며, 보완답변 검토의 실제 요청목록 복귀는 POST200·빈 context·VERIFIED와 정확 Version/메모로 확인한다. Catalog의 CURRENT_CATALOG/현재 등록 건수 문구와 요청목록 검색·필터 복원도 기존 업무 경로로 검증한다. 원본bytes·Scope·저장 결과 기대는 유지하며 독립 소스 대조/TypeScript/대상 ESLint를 통과했다. 수정 후 실제 재실행은 최신 전체 CI 결과로 구분한다. 원로그 SHA256은8edbe95d6ddee777064c875e5a040afb42b4f37756329cb3fecf30b09cddc55a다.
Windows I/O 보완 후 동일 비민감 소스의 full manifest snapshot→새 execution copy→source Next 절대 실행파일+NODE_PATH→익명 `/login`200을 실제 확인했고 자기 Node 종료도 확인했다(runtime-copy-proof-71fbd75b94a7). 이 보조 점검은 DB·계정·release 선택 없이 모듈 탐색/복사본 기동만 검증한 것이며 정식 전환의 fresh build 증거로 대체하지 않는다. 파일 경로·owner 식별·manifest 항목과 해시는 일반 경로로 유지하고 확장 namespace는 Windows 파일 I/O에만 적용한다. 시스템 설정/권한 변경·링크·의존성 복제는 없으며 원래 route-cache까지 전체 파일 검사를 유지한다. 이어 같은2002c1fabb87의 fresh 빌드·guarded recover·전환·새 저장·복귀·실패복귀를 수행한다.
#### Q06 최종 동일 환경 실행 결과와 적용 판정

원래 실패 회차d2a876874a67→a6d5b0f3d32b의 summary 바이트 해시와 불변 enrollment/초기 record를 확인하고 같은 합성 owner2002c1fabb87 / https://127.0.0.1:19451에서 재개했다. 새 DB·볼륨·계정·인수환경을 만들지 않았다. 정식 회차18f6ca8bbe75는 **PASS**이며 source `917cb924d39357c3ca5fc8c465bcf454daba2bde`, 불변 launcher `997d5a0a37f0c7fda6ab670ddb2afd96af8b111a`, 호환 이전 source `9b8d0e0f9eb79aaaa2b973f7e3455df78b8a046e`를 각각 고정했다. 의도한 API 시작 실패 source `a0f5d53c91861f23776fb7be009982efaeaac0da`는 로컬 시험용이며 Push 대상이 아니다. build는 중지 전에 fresh 수행했고 고정2048MB V8 제한은 해당 시험 build에만 적용했다. 런타임까지 같은 제한이라고 주장하지 않는다.

| 단계 | CLI 전체 시간(초) | 마지막200→연속3회 정상응답 중 첫200 간격(초) |
| --- | ---: | ---: |
| 새 source 전환 |61.369|31.915|
| 같은 현재 DB에서 이전 source 복귀 |66.296|38.055|
| 의도한 시작 실패 후 이전 source 자동 복구 |111.313|81.414|

1초 간격·요청 timeout2초의 HTTPS 익명 `/login` 상태/공개 nonce·HEAD 관측이다. 명령 시간에는 중지 전 검사가 포함되며 공백은 표본 오차가 있는 관측값이다. 실제18445의 중단 시간이나 SLA로 일반화하지 않는다. source별 API/Worker의 HEAD·DB·Role·files와 Web의 실제 cwd/실행 복사본·원본 artifact/build ID가 일치했다. snapshot의 route-cache·public까지 full manifest가 유지됐으며 새 실행 폴더의 캐시만 변했다.

원래 manifest·계정 안내 파일·공개 TLS CA·gateway 설정의 해시와 URL/쿠키 namespace를 유지했고 네 역할의 기존 세션을 전환·복귀·실패 복구 동안 그대로 검증했다. 첫 source에서 만든 합성 회사/사업장/첨부1건과 새 source에서 만든 추가1건, 합성 XLSX 기능1개가 복귀·자동 복구 뒤에도 유지됐다. 현재 목록650건과 명시한 원래 import649건 전체 Snapshot, XLSX 원본 SHA·provenance·200 응답을 모두 확인했다. 업무 테이블별 내용 해시와 물리 Schema 지문도 동일했다. Migration/seed/초기화/과거 DB 복원은0이며 원문을 출력하지 않았다.

추가로 정식 PASS 후 DB 컨테이너까지 STOPPED임을 확인한 뒤 동일 container ID/volume을 정상 start했다. owned-stop-resume-e29ee3c010a5도 **PASS**다. 새 인증4역할, 저장된2회사/2사업장/2첨부와 원본바이트, 현재650/원래649 Snapshot·Excel 원본/Metadata·업무 내용/Schema 해시를 재검증했다. 이전 쿠키를 읽거나 복원하지 않았고 새 인증 세션 증가는 업무 내용 비교와 구분했다. 다시 정상 STOP했고 같은 볼륨·파일·계정/CA·불변 산출물을 보존했다. 시험 URL19451은 최종 중지 상태이며 실제 인수 주소가 아니다. 소유 디스크 시험 볼륨이나 실패 자료는 삭제하지 않았다.

Windows 파일 I/O 관련 순수 회귀는103 PASS/0 SKIP이며 실제260자 초과 경로·artifact root·sidecar·복사·기록 identity·기존 junction/link 차단과 fixed build 옵션/실패 시 next-env 원복을 포함한다. 초기 timeout, build 변이 차단, 긴 경로 복사 실패를 없었던 일로 만들지 않고 앞선 보호 로그와 새 회차를 구분했다. 추가 private checker의 소스/합성 guard 검토는 실제 실행 PASS와 별도다.

**PR20 완료 당시(아래 후속 인계 준비 전) 실제18445 적용은 미실행이며 당시 수단으로 바로 실행할 수 없었다.** 도구는 보호 포트18445/8443/8444를 거부하고 기존725에는 opt-in owner 계약과 새 workbook JSON reader가 없다. 현재725를 새 자료의 무조건적인 fallback으로 사용하지 않는다. 실제 적용 전 단일 결정표의 정확 Commit/시각과 함께, 호환 이전 실행물·원래 data-owner/START 계약을 보존 문서2개·manifest 변경 없이 정합화할 별도 검토 가능한 절차를 확정해야 한다. 이 조건이 없으면 적용을 보류한다. 일반 START·manifest·HEAD·상태 파일을 고치거나 문서를 지워 가드를 우회하지 않는다. 새 source에서 저장한 자료를 옛 DB로 되감는 복귀는 허용하지 않는다.

실제 기존 검수환경은 최종 격리 점검에서 익명 login200(31ms), 공개 nonce9ca49b473812/HEAD725987f4a375d4f77028e35361e4fcdb05aac4ee, 알려진5프로세스의 기존 cwd, 보존 문서2개 SHA 일치를 확인했다. 원래 dirty 상태도 유지했다. 기존 DB 내용·기업자료·계정/세션을 열거나 자동 로그인/주입하지 않았으므로 이 점검을 현재 실기업 자료의 전수 보존 검증이라고 부르지 않는다. Docker/WSL 재시작·기존8443/8444·백업·보안/권한 설정 변경은 하지 않았다. 보호 근거는 quality-20261103/isolation.json이다.

#### 후속 Git·전체 회귀와 남은 상태

구분 가능한 구현 근거는 분석/원문 계보fa5af07·55ca6f5, Excel24e6975, 포털01acb2a·3c02b84, Preview6454ca3, 전환f49dbd8·9b8d0e0·a4ada3c·daa4af7·997d5a0, 회귀 준비d27aa88이다. 변경 영역은 `apps/api/app/capability/{workbook_import,input,application,asset_solutions}.py`·`apps/api/app/api/{capability,asset_imports,asset_solutions}.py`와 기존 분석/Worker 경로, Web portal/common session·UI·proxy 및 생성 API 타입, `apps/api/tests/acceptance_release.py`와 대응 시험·고정 합성 품질 자료다. Source/Evidence/Version/Review·기업 ACK·운영자 CONFIRM·제공/필수 연계·정식 제안/전달 Guard, Role/Company Scope·물리 Schema는 유지했다. 외부AI/새 OCR·연계 면제·공고 없는 제안 정책은 추가하지 않았다.

후속 시험 준비·보고서 수정에서도 실행 제품·lock·Schema·전환 도구가 정식 source917과 동일함을 검사한다. 최신 CI의 시험 준비 수정은 제품 실행 코드 변경과 구분한다. 별도 Feature Branch `fix/portal-analysis-quality-20261103`의 [Draft PR20](https://github.com/dongarnd-commits/dongalab/pull/20)은 PR19/0b6f56a88131a10fdc9c4cb16ed7658250275b03을 base로 하며 PR17→18→19의 포함 관계를 유지한다. 기존 PR17/18/19는 open Draft/미병합, main10d3d8b0f0142b0d6cbb992acb07bb34ed40c049를 유지한 원격 메타데이터도 확인했다. 보호 로그·원본649·실자료·계정·실행 비밀은 Git/CI에 넣지 않는다. 정확 최종 HEAD와 최신 전체7개 Job의 완료 결과는 같은 PR 본문/Checks에 기록한다. 예전 성공이나 로컬 부분 실행을 최신 전체 성공으로 대신하지 않는다.

남은 항목은 단일 결정표의 실제 적용/저장 보호·개인 접근/보존·정리/공고 조건, 제공 담당자의 실제 추천 범위·릴리스/연계 근거, 실기업에서만 확인할 수 있는 추출/추천 품질과 고객 문안이다. 유한한 합성 회귀의 자유문장 숫자/기간5실패, 개발 도구 minimatch18 moderate/ESLint EOL과 호환 업그레이드 대기, BitLocker 미확인·자동 만료/완전 정리 부재도 남긴다. 개발 범위 구현/자동검증, 합성 전환 검증, 기존 환경 적용, A 실기업 평가, B 정식 제안·최종 인수는 서로 구분하며 범위를 늘리는 새 기능은 시작하지 않는다.
28cddc5의 최신 CI는 Backend456 PASS/기존 optional-source1 SKIP/5 integration deselected, PostgreSQL326 PASS/기존 실제공고 opt-in1 SKIP, Frontend 타입/lint/unit9/build, 세 Preview6/13/23 PASS였다. Preview 수는 각 harness가 포함 실행한 중복이 있어 합산하지 않는다. Public 기본 전체87 PASS(6.5분) 뒤 Fresh UI는2 PASS/1 FAIL(52.4초), 뒤 자동조합 전달은 선행 실패로 **미실행**이었다. 전체 합격이 아니다. 실패는 reacceptance-full-ui:119에서 선택 기업·제출본을 유지하는 메뉴를 전역 요청목록으로 가정한 준비였고 자동조합:174에도 같은 가정이 있었다. 두 경로는 정확cid/v1 또는 실제 발송 origin으로 이미 복귀한 빈cid/vid를 엄격히 확인하고 기존 UI의 검토목록 복귀→요청목록·명시 재조회로 진입하도록 test-only helper를 공유한다. 제품 state를 강제로 초기화하거나 API로 건너뛰지 않는다. DMP Full UI의 관리 편집 후 원본 보호2곳도 기본 CURRENT_CATALOG 대신 정확 import_id의 IMPORT 전체 Snapshot 비교로 정정했다. 현재 목록의 명시 편집 Revision과 불변 원본을 섞지 않는다. 실제 원래649의 설명을 시험 정답에 맞춰 바꾼 것이 아니다. 원로그 SHA256은ec7ed195e89db28e4051933241d3a2006a3008a29635ddcb9cc2dba19f829437이며 수정 후 두 관련 전체 경로를 순차 검증하고 최신 HEAD CI로 최종 확정한다. 기존 timeout·상태/권한/파일바이트·Version·최종 전달 기대는 유지한다.
b47725a의 test-only 준비를 적용한 뒤 같은 관련 경로를 순차 실행해 Fresh 전체3 PASS/1.9분(ci/1회 신규 독립 시험의 reacceptance-quality-full-final.log), 자동 DMP 전체1 PASS/2.7분(ci/fe3211409ddc, asset-solutions-quality-full-final.log)을 확인했다. 전자는 등록/OCR·재무·요구/답변·단독/복합·공고/매칭·16절 DOCX/PDF·기업 수정 요청, 후자는0발행 Catalog·관리자 제공 확인·자동 추천/구성·실제 전달과 이후 선택변경 연계 Guard를 포함한다. 테스트 상태/timeout·파일/Version 기대를 완화하지 않았다. 두 임시 DB는 소유 label/CPU1·512MB 디스크 볼륨으로 분리했으며 자기 컨테이너만 종료·정리하고 시험 볼륨은 보존했다. 검증 중 기존18445의 익명200 응답도 계속 확인했다. 시험이 만든 이 Worktree의 next-env 타입 경로만 Git 원본으로 복원했으며 기존 인수 source/build/deps는 변경하지 않았다.

최신 합성 사용성 관찰은 별도 실제 사람 평가와 구분한다. 선택한 기능2개/해결범위8행에서 기능 설명을 읽기 위한 펼침·닫힘0회, 기본 양성업무 용어0·혼합 완료옵션0, 재무 저장범위 안내 있음·취소 control1개, 변경 사유는 업무 문구를 먼저 표시하고 raw code는 상세에 보존했다. 선택구성 재조회 후 저장까지의 시험 스크립트는8행의 역할·설명·제외/미해결·추가확인·상태와 공통4항목, 총44종 control을 명시 수정/선택했다. 관찰된 DOM input50/change44/click2는 Playwright 이벤트이며 사람의 입력 횟수나 최소 조작 수가 아니다. 공통 검토 의견은1회지만 행별 범위/예외·제공근거 판단은 남는다. 기능 요약 표시·근거 펼침 감소와 실제 운영자의 수정·판단 시간 감소를 동일시하지 않는다. screenshot3포털·선택기능 요약과 synthetic-usability-observation.json을 같은 보호 산출물에서 확인했다. 실제 최소 수정량·시간/입력량 감소·추천 적합성은 사용자가 승인한 A 평가에서 측정할 항목이며 이번 합성 결과로 통과시키지 않는다.
### 2026-11-03 초기 legacy 인계 검토 계약 — 최종 복귀 실행물은 아래9b로 대체

제품 검수 기준은 PR20/04dfea4ee9d2521ba632c430c2218463df5df63c로 고정한다. 기능/UI/룰/추천/OCR/Parser·물리 Schema·의존성은 변경하지 않고 미지원5건을 유지한다. 별도 fix/acceptance-handover-20261103 Worktree에서 기존 v3 산출물/hash/호환 검사를 재사용하는 제한된 legacy owner adapter만 준비한다. 주 에이전트가 도구·집중시험·기존2보고서의 유일한 수정 담당이다. 보조2개는 읽기 전용으로725 데이터 reader와 START/소유권 경합을 각각 조사했고 파일/공통 타입/Migration/의존성 병렬 쓰기·권한 확대·설치는 하지 않는다.

725의 새 workbook_provenance 거절은 strict Metadata의 자료형 문제다. START 문제는 별도로, 데이터 owner root와 실행 source가 결합되고 외부 lease를 모르는 guard0이며 dirty 검사가 supervisor 정리 구문 밖에 있어 STARTING이 남을 수 있다. 한 필드만 backport해도 latest-import 목록·원본 경로·룰Version 차이는 남으므로 이를 완전 호환 복귀라고 하지 않는다. 초기안은 제품04 재기동을 recovery slot으로 두었으나, 이전 버전 복귀와 구분하기 위해 최종안에서는 기존 검증된9b 실행물로 대체했다. 아래 최종 결과와 단일 결정표를 따른다. 이는 새 자료를 읽는04 재실행 복구이며725 기능/화면으로의 코드 downgrade가 아니다.725 원본 START를 새 자료 이후 fallback으로 사용하지 않는다.

입력 계약: clean 제품04 source/lock/Schema/hash와 독립 불변 artifact, 정확한 legacy root/nonce/725HEAD·원래 manifest hash·보존문서2개 hash·공개 TLS CA/서버 인증서·Caddy template/hash·DBcontainerID/label/mount volume/loopback ports·files/cookie namespace·알려진 process/listener 소유권, plan digest에 결합한 별도 명시 적용 승인이다. 현재는 원본 비밀번호/키/계정 파일 값·기업 원문을 조회하지 않고 비민감 technical projection/hash와 공개 응답만 조사한다. 현재 task를 실제 적용 승인으로 만들거나 실제 승인 receipt를 생성하지 않는다.

출력 계약: owner 원본과 분리된 불변 plan/artifact/승인 template·외부 lifecycle state/selection/events, 실제04/recovery 실행물의 지문, 동일 현재 DB/files 위의 전환·실패 복구 근거와 정확 중지 조건이다. 전역 PROTECTED를 지우거나 allow-protected boolean으로 열지 않는다. 실제9ca/18445는 정확한 owner+승인 digest의 별도 경로만 검증하고8443/8444는 계속 거부한다. 기존 manifest/HEAD/state를 위장·덮어써 통과시키지 않는다. 승인 뒤 정상 stop.request를 보낼 때에만 기존 supervisor가 자연스럽게 STOPPED를 기록하며 새 state는 외부 경로에 둔다. 원래 DB/volume·계정·비밀번호·권한·TLS/files·문서2개는 유지한다.

정상 old START 경합은 별도 lease 파일만으로 막지 못한다. Windows의 일시적인 파일 공유 fence를 지원되는 기존 entrypoint와 STOPPED state에 적용·검증해 내용/ACL을 바꾸지 않고 동시 legacy START를 거부한다. fence 획득 불가·불명 PID/타 listener·진행 중 작업·기록/자료형/산출물 불일치·만료/없는 승인에서는 중지/기동0으로 거부한다. controller 중단/재부팅 뒤 lease는 명시 reconciliation 전 재시작하지 않는다. 임시 fence를 영구 old START 계약 변경으로 주장하지 않는다. 자동 재부팅 서비스/계정관리/자동삭제 체계는 개발하지 않는다.

비민감 시험은 이미 보존된2002 환경의 자료만 명시 복제하고 원본9ca DB/파일을 복제·열람하지 않는다. 복제 nonce/DBrole/ports만 분리하며 신규 기업 원문·추천 정답·공고·검수자료를 추가하지 않는다. 초기 복제와 전환 중 DB restore를 구분하고 전환/복귀는 항상 같은 현재 DB를 사용한다. 실제18445/8443/8444에는 fence·stop·start·쓰기·배포를 수행하지 않는다. 이미 성공한 제품 전체 시험/CI는 재사용하고 새 owner adapter·fence·승인·호환 복구·자료보존 영향만 집중 검증한다.
### 2026-11-03 제품04 고정 후 인계·호환 복귀 준비 결과

제품 검수 기준과 PR20 HEAD는 `04dfea4ee9d2521ba632c430c2218463df5df63c` 그대로다. 제품 기능/UI/룰/추천/OCR/Parser·Schema·lock에는 변경이 없다. 합성 품질5건·미지원 범위·외부AI/공고/제안 Guard를 그대로 유지한다. 이번 수정은 별도 `fix/acceptance-handover-20261103` 브랜치의 Windows owner adapter·집중시험과 기존 두 문서 동기화다. PR20이나 기존 PR17/18/19·main을 병합·종료하거나 검수환경에 배포하지 않았다. 보조2명은 읽기 전용 계약·안전 검토만 수행했고 주 에이전트가 모든 파일 수정·시험·통합을 맡았다.

#### 두 문제의 구분

| 구분 | 원인·확인 범위 | 처리·제한 |
| --- | --- | --- |
| 725 workbook 읽기 | 725의 strict `Metadata`는 새 정상 저장 JSON의 `workbook_provenance`를 거부한다. 실제9ca의 읽기 전용 count에서는 해당 필드가 있는 import0건이며 실제 원문/metadata 내용은 읽지 않았다. 보존된 비민감2002 자료 복제본에서는 기존725의 실제 HTTP500을 재현했다 | 제품04 reader로 현재650·지정 원본649·workbook1과 원본 다운로드를 확인한다. 물리 Schema/Alembic은 동일하다. 단일 필드 backport만으로725의 최신 import 목록 의미·workbook 원본 경로·룰Version 차이까지 해소됐다고 주장하지 않는다 |
| START/data-owner | 725는 실행 source=data owner를 전제하는 guard0이고 외부 lease를 모른다. dirty 검사가 supervisor 정리 구문 밖이어서 STARTING 잔류도 가능하다. v3는 guard1 enrollment를 요구하고18445를 명시적으로 보호한다 | 기존 v3 `PROTECTED`와 enrollment 조건을 유지한다. 정확9ca/기존 root/18445/725 소유권과 별도 승인에만 한정한 외부 adapter를 사용한다. 원본 manifest/HEAD/state를 새 버전으로 위장하지 않는다. 실제 기존 START를 실행하거나 문서2개를 clean/reset하지 않았다 |

#### 정확한 실행물과 적용 경계

- 제품 source: `dongalab-quality-20261103`, clean HEAD04. 불변 Web artifact manifest SHA256은 `1567ef9885660e77b7d967ac42f9e17e614d2d438b2ade7bb3786d42a371b74e`, fresh dist는 `.next/datco-e2e-df5fcdcbb0d0`이다. source/Schema/lock·설치된 Python/Node 의존성 tree·interpreter hash를 재검사하고 매번 별도 실행 복사본을 만든다.
- 고정 launcher: `dongalab-handover-launcher-20261103-owner`, control Commit `e98ca192fa16e553b6a1ba9c57157fb82815f183`. API·Worker·Web·Gateway를 같은 owner의 DB/files/TLS/cookie로 결합하며 실행 state/events/worker-ready/파생 gateway/실행 복사본만 외부 보호 경로에 둔다. 실제9ca용 plan은 그 경로의 `storage/private/runtime/handover-20261103/owner-9ca49b473812/plan.json`이며 digest는 `25349069cc052869cf11b78974ac62e044c74e4cc4138a16d29aaa910d78d897`다.
- TARGET은 제품04, RECOVERY는 **기존 검증된 이전 버전 `9b8d0e0f9eb79aaaa2b973f7e3455df78b8a046e`**다. 이전 artifact SHA256은 `46a879b490e463eb282b2160e4e48d9d6cdf9f8be9eb2a6be4dfe114f748eb38`다. 기존2002 release/artifact·의존성을 재해시하고 새 owner plan에 다시 결합했으며2002의 owner 계약/DB/계정은 재사용하지 않았다.04→04 재기동 시험과 이전 버전 복귀를 구분한다.725 코드 복귀와 과거 DB 되감기는 제외한다. 두 버전의 Backend bytes·lock·Schema와 workbook reader 계약은 같아야 하며 다른 head 조합은 거부한다.
- 실제 owner에 생성한 것은 외부 계획·불변 artifact 사본·`PENDING_USER_DECISION` 양식뿐이다. 실제 승인 receipt·활성 lease는 생성하지 않았고 실제 activate/stop/start/resume·fence·로그인·자료 입력·Migration·seed·삭제는 수행하지 않았다.

승인된 전환은 (1) 정확 승인/소스/실행물/DBURL·역할·loopback 대상/owner/PID 생성시각·cwd·listener/자료 경로/문서·계정·TLS 해시/미종료 작업0을 정지 전에 재확인하고, (2) legacy entrypoint에 임시 읽기 fence를 잡은 뒤 기존 supervisor의 정상 `stop.request`로만 정지하며, (3) 자연스럽게 기록된 기존 STOPPED state를 읽기 공유 fence로 보호하고 외부 lease를 만든 뒤04를 기동한다. DB container/volume은 계속 같은 것을 사용한다. 기존 state는725의 과거 종료 기록으로 남고 현재 실행04는 외부 state와 API·Worker·공개 헤더·Web artifact로 식별한다. 일반 v3 보호 포트를 삭제하거나 기존 환경이 guard1인 척하지 않는다.

새 정상 STOP은 **새 실행 프로세스만** 종료하고 DB/volume/files/accounts/TLS/이력을 남긴다. 기존 원본 RUNBOOK·CREDENTIALS는 주소·시험계정 안내/과거 lifecycle 근거로 보존하며, 인계 후 기존 START/STOP/CLEANUP을 섞어 사용하지 않는다. 새 경로의 recover/stop은 같은 plan에 결합한 별도 승인 action과 소유 custodian을 확인한다. 원자료·비밀번호·키·DBURL은 plan/stdout/Git에 남기지 않는다. 실행 bootstrap만 승인 뒤 기존 DB 접속 설정을 내부 소비하고, child stdout/stderr는 버리며 lifecycle 오류는 고정 코드/클래스만 보존한다.

#### 집중 검증과 보존 근거

집중 단위시험은 Windows에서 **114 PASS/0 SKIP**다(신규47·기존 release67). projection의 비밀값 미보관·중복/잘못된 JSON·승인/시간/nonce/제품 binding·승인 전 무변경·잘못된 DBURL의 정지 전 차단·파일 fence·생성 전 자식 등록·Job 종료·강제 custodian 종료·미확인 cleanup의 재개 거부를 포함한다. Windows 전용 OS 시험은 다른 OS에서는 적용 불가로 명시하며 이 Windows 실행의 실패를 SKIP으로 바꾸지 않았다. 최종114건에는 이전 버전 binding·동일04 재기동을 이전 버전 복귀로 오인하지 않는 검사·각 source의 정확 HEAD 검사, PID 재사용 구분과 포트를 열지 않은 Python 손자 프로세스의 추적·종료도 포함한다. 최종 이전9b 복귀 7경로의 결과는 아래와 같다.

전체 제품 CI는 고정04의 기존 성공 근거를 재사용했고 GitHub에서 동일 HEAD·열린 Draft/미병합과4개 workflow 성공을 다시 확인했다. [DATCO CI](https://github.com/dongarnd-commits/dongalab/actions/runs/41590876064)의 Backend456/PG326/Frontend 타입·lint·unit9·build, Public87→Fresh3→DMP1 및 Preview6/13/23은 앞선 최종 결과를 유지한다. 이번 전환 도구 변경 때문에 전체 제품 시험/전체PG/전체Playwright를 다시 실행하지 않았다. 새 준비 브랜치의 전체CI 성공을 주장하지 않는다.

시험은 원래2002 비민감 자료의 정지된 volume을 읽기 전용으로 복제한 독립 nonce만 사용했다. 신규 회사·자료·공고·추천 정답은 주입하지 않았다. 정상 fixture 생성 중 의존성 사본 경로 제한·누락된 시작 설정, 최초 adapter 시험 중 TARGET binding·Windows venv launcher 자식 계층 오류가 드러났고 실패 로그와 원래 회차를 보존했다. 수정된 회차는 새 독립 복제본과 고정 launcher에서 수행한다. 시험용 DB 이름/접속 Role만 새 nonce로 격리했으며 실제9ca나 원본2002의 DB/계정/볼륨/파일은 변경하지 않았다.

#### 실제 전환의 중단 조건과 남는 제한

승인 없음/만료·digest/HEAD/실행물/의존성/Schema·owner/volume/경로/문서/계정/TLS 불일치, 알 수 없는 PID/listener, 진행 중 입력·업로드·작업 또는 queued/processing/attempts, 정지·자식/자손 정리·포트 해제 미확인은 **적용 중지**다. 시작 실패 뒤에는 자식/Job ActiveProcesses0·포트 해제를 확인한 경우에만 같은 현재 DB 위의 이전9b RECOVERY를 시작한다. 과거 DB 복원·오류 숨김·state 조작으로 통과시키지 않는다.

임시 fence는 실행 중의 정상 legacy START 충돌만 막으며 재부팅 후 영구 OS 차단을 제공하지 않는다. custodian 강제 종료/재부팅 또는 FAILED cleanupFalse·증거 누락 상태의 일반 resume은 **차단**한다. 이때 기술 담당자의 별도 정합 확인 전에는 old START·DB복원·임의 상태 변경으로 재개하지 않는다. 이번 범위에서는 상주 서비스·영구 ACL·자동 crash/reboot 복구 체계를 만들지 않았다. 이는 정확한 남은 운영 제한이며 일반 정상 stop/resume·시작 실패 후 호환 복귀와 구분한다.

주소 `https://127.0.0.1:18445/login`·인증서·시험계정·Role/CompanyScope·DB/volume/files/이력·원래 문서2개 보존은 계획과 복제 시험에서 확인한 범위로 보고한다. 실제 업무 row/파일 원문·계정 비밀번호·인증서 개인키는 조사하지 않았으므로 실제 자료 전수 무결성이나 실제 개인 로그인 완료를 주장하지 않는다. 실제 원래 문서2개 SHA는 각각 `cf50dae8b641bda48b6601c7736826d31f4891c0fd67b2b616e7c125c0177988`, `48d3386ef1300449f1b95791586d24a7405fd9e0d84044f55d3e571f87ed5036`다.

사람이 결정할 것은 기존 단일 결정표의 **적용 창·실자료 범위·개별 접근자/회사Scope·보호 상태 확인·보존/백업/정리 책임**이다. 저장 암호화/BitLocker·Docker VHDX 접근·전체 외부 전송 차단 미확인, 자동 만료/완전 정리 부재는 해결됐다고 바꾸지 않는다. 실자료 사용 승인 후 사용자가 직접 입력하는 A(추출/정정/분석/DMP추천/구성 검토)부터 평가한다. 공식 공고·자격이 없는 B(매칭/정식 DOCX·PDF/전달)는 기존 Guard로 계속 보류한다. 실기업 평가·최종 인수는 아직 하지 않았다.

이전9b와04의 Web 차이는 원천 분류 상세 GET 경로, 카탈로그 응답과 현재 필터의 결합, 분석 검토/보완요청 이동의 미저장 동기화 및 운영자 Preview의4파일이다. 이를 이번 작업에서 수정하지 않았다. 이전 버전은 데이터 호환 복구용이며 제품04의 UI와 같다고 주장하지 않는다. 복귀 중에는 신규 입력·실기업 평가를 보류하고 정상 STOP→승인된 resume으로04를 재적용한다.04 복귀 후에도 코드·입력·DMP Version과 평가 회차를 명시한다. 기존649/정상 workbook 자료·계정·Scope·이력을 과거 DB로 되돌리지 않는다.

#### 최종 집중시험 확정·보호 상태

최종 비민감 복제 `ac0084c00da0`의 **7경로 PASS**:725→04 정상 인계,04→이전9b 복귀, API/Worker/Web 각각의 시작 실패→9b 복구,9b에서04 재적용, custodian 강제 종료→UNCLEAN 일반 재개 차단이다. 원래2002 자료만 복제했고 신규 회사·문서·공고·추천 정답을 추가하지 않았다. 현재650·지정 원래649·workbook1의 전체 페이지, provenance와 XLSX 원본 SHA/다운로드200, 회사2·사업장2·파일2, 기존 네 역할의 동일 세션/권한과 회사 Scope를 확인했다. 같은 현재 DB의 업무 row/count/hash·감사 이력·파일 bytes·원본 manifest/accounts/CA/Caddyfile·보존 문서2개·Schema를 각 경로 전후 비교해 유지했다. 세션 저장소는 정상 로그인 기록이며 기존 네 cookie를 이어 썼다. 이전9b의2002 owner를9ca owner인 척 사용하지 않았다.

전환·복귀 실행 경로의 고정 Commit은 `1dc4b5c8881ede84e046f34165002c519047a3dc`였다. 마지막 읽기 전용 조사에서 실제9ca의 Worker base Python1·Windows console host4가 기존6개 소유권 목록에 빠졌음을 확인해 최종 `e98ca192fa16e553b6a1ba9c57157fb82815f183`에서 정지 전 소유권 검사만 강화했다. 최종 계획은11개 전체를 결합하며, 새 자손·허용되지 않은 실행물·PID 재사용·실행물 hash 변경을 정지 전에 거부한다. 이 변경 영향은 신규2개 단위시험(모형/실제 비리스너 손자)·실제9ca11개 읽기 전용 binding·종료 후 자체 app/관찰 명령0 확인으로 검증했다. 제품 bootstrap/전환·복귀 경로 자체는 동일하고 전체 제품 시험/PG/Playwright를 다시 반복하지 않았다.

초기 시험 실패는 유지했다. 첫 adapter 회차의 슬롯/Windows launcher 계약 오류,04 재기동 회차의 통합 준비 대기170초 초과, 후속 재로그인4건 때문에 감사 전체 동일 비교가 실패한 기록은 각각 보존했다. 기존 감사12건 hash와 후속 LOGIN만 정확8건 추가된 사실도 별도 확인했다. 최종 이전9b 회차는 새 독립 평가이며 같은 네 세션으로7경로를 통과했다. 준비/의존성 전체 hash 확인을 포함한 후속 시험 대기는240초로 구분했으며 API70초·Worker30초·Gateway20초 준비 Guard나 데이터/권한 기대는 변경하지 않았다. 초기170초 기준 충족이나 실제18445 복구 SLA를 주장하지 않는다.

보호 근거는 새 개발 Worktree의 `storage/private/runtime/handover-20261103/previous-compatible-handover-summary.json`(최종7경로), `full-owner-graph-proof.json`(실제11개·변경0), `final-compatible-resource-state.json` 및 앞선 실패 JSON/로그다. 코드·고정 환경·DMP/입력 버전과 각 실패/후속 회차를 구분했고 보호 로그·실행물·원본649·실자료는 Git/CI에 넣지 않았다. 최종 자체 app/observer 명령은0이며 세 복제 DB는 정상 중지하고 volume/files/계정/이력을 보존했다. 강제중단 시험의 외부 lease는 과거 RUNNING 기록을 고쳐 속이지 않고 UNCLEAN으로 판정해 재개 차단을 확인했다.

실제9ca에는 최종 `plan.json`·두 artifact·PENDING 양식만 외부 보호 경로에 준비했다. 실제 승인 receipt/활성 lease·stop.request는 생성하지 않았고18445/8443/8444·원래 DB/volume/files/계정/비밀번호·백업·문서2개는 변경하지 않았다. 실제 접속은 여전히725의 익명 login200이며 실제자료/키/비밀번호 원문이나 실제 개인 로그인을 조사하지 않았다. 사람은 기존 단일 결정표에서 적용 창과 실제자료·개별 접근·보존/보호/백업·정리 조건만 결정한다. 기술 준비, 실제 적용, A 실기업 평가, B 공식 제안과 최종 인수는 모두 별개다.


### 2026-11-04 실제 18445 적용 결과 — 포털 검증 실패

#### 승인·실행과 정확한 버전

사용자는 고정04 적용 1회를 승인했고, 사전검사에서 Caddy 자동 갱신으로 공개 leaf 인증서 지문만 변경된 사실을 확인한 뒤 새 계획에 대해 “새 계획으로 이번 1회 전환 승인”이라고 별도 결정했다. 기존 계획253490…은 수정하지 않았다. 기존 e98 도구로 별도 후보 계획을 생성해 owner.certificate_sha256 한 필드만 달라졌음을 검사했고, 실제 사용한 계획 digest는 `63d252eb9161d981b732cd71b3cdbf163095df7a6e9796995ea1a0db03182cc2`다. CA·제품·복귀 제품·제어·DB·파일·계정은 동일했다. 정확 계획/action/시각/유효기간 receipt를 발급했고 검사 생략이나 자체 사용자 인증은 하지 않았다. 실제자료 승인은 제외했다.

2026-11-04 08:19:04 KST 기존 supervisor의 정상 종료 절차로725와 당시 확인된11개 프로세스·자손을 종료했다. 소유권·포트 해제·임시 fence를 확인하고 기존 DB 위에서 한 번만 기동했다. 현재 제품은 `04dfea4ee9d2521ba632c430c2218463df5df63c`, 제어는 `e98ca192fa16e553b6a1ba9c57157fb82815f183`, Web artifact manifest SHA256은 `1567ef9885660e77b7d967ac42f9e17e614d2d438b2ade7bb3786d42a371b74e`, Web 실행 식별은 `e4b11f4b1dfe4360a33634786a3bd605`다. 원래 manifest/HEAD를04로 바꾸지 않았고, 원래 상태는 supervisor가 자연스럽게 기록한 STOPPED725이며 현재 RUNNING04는 외부 상태·공개 응답·API/Worker로 구분했다.

#### 실제 통과·실패·미실행

| 항목 | 실제 결과 |
| --- | --- |
| URL·기본 기동 | https://127.0.0.1:18445/login HTTP200. API·Worker·Web·Gateway의04/nonce/기존DB 식별 일치. 이것만으로 포털 사용 가능이라고 판단하지 않는다 |
| 브라우저 로그인 | 기존 수요기업 편집 TEST 계정 인증 후 /portal/company에서503. LOGIN 감사1건 추가. 브라우저 종료 전 API 로그아웃 정리 요청은 했으나 LOGOUT 감사가 없으므로 로그아웃 완료로 인정하지 않는다 |
| 네 역할·Scope·공통 로그아웃 | 첫 포털 진입 실패로 나머지3역할 및 네 역할 전체 접근/로그아웃 검증 미완료. 기존 계정·역할·Scope 설정 bytes/DB 행 보존은 별도 확인 |
| 관리자 상세·운영자 보완요청·세 포털 새로고침 | 실제 변경 환경에서 미완료. 원래 소스 시험이나 준비 회차로 대체 합격하지 않는다 |
| 기존 자료 | local_sessions 제외 모든 기존 업무 테이블 count/서버 내부 row hash 동일. 기존 audit prefix hash 동일, 추가는 LOGIN1건. 기존 파일1개 bytes hash 동일. DB container/volume·Schema·계정 설정·원래 manifest·문서2개·승인된 TLS 동일. 원문/키/비밀번호 출력 없이 검증 |
| DMP | 기존649 원천·원본 Snapshot 관련 테이블 전체 hash 보존. 관리자 UI 재조회는 미완료이며 실제 제공 근거를 새로 검증했다는 뜻이 아니다 |
| 잔류 작업 | 최종 queued/processing/attempts 모두0. 신규 회사·공고·업무자료 생성0. 브라우저 문맥은 종료했으나 TEST 세션 로그아웃은 미확인 |

실패 원인은 제품 UI 변경이 아니라 **불변 실행물의 런타임 포털 번들 누락**이다. 제품04 `apps/web/src/portal/server.ts`는 실행 cwd의 `.role-portals/{company,operator,admin}/portal.js`와 `portal.css`를 읽는다. 반면 고정 `snapshot_web`은 package/config·Next dist·public만 포함해 소스 빌드에 존재하는6개 파일을 제품04와 복귀9b의 불변 산출물 모두에서 제외했다. 제품·복귀 artifact 각각440개 파일 manifest에 해당6개가 없고 실제 실행 복사본에도 없다. source directory에서 성공한 종전 제품 CI와 복제 경로의 자료/API 검증은 이 분리 실행물의 세 포털 사용 가능을 보증하지 못했다. 사전검증에서 이를 놓친 검증 누락이며 “호환 복귀 실행물 준비 완료” 판단 중 포털 가용성 부분을 철회한다.

복귀 대상 `9b8d0e0f9eb79aaaa2b973f7e3455df78b8a046e`의 고정 artifact SHA256 `46a879b490e463eb282b2160e4e48d9d6cdf9f8be9eb2a6be4dfe114f748eb38`도 같은 누락이 확인돼 **recover는 실행하지 않았다**. 현재04의 기본 서비스는 RUNNING이지만 사용자 검수 목표는 달성하지 못했다. 정상 복귀라고 보고하거나725로 되돌리지 않았고, 과거DB 복원·프로세스 강제 종료·추가 전환·수동 번들 복사·symlink·manifest/hash/state 변경·보호 Guard 우회는 하지 않았다.8443/8444·PR17~20·main·기존 백업에는 변경 작업을 하지 않았다.

#### 다음 조치와 제한

현재 고정 실행물과 e98 계획만으로 세 포털 검수를 열 수 없다. 최소 보완 대상은 이미 생성된6개 포털 런타임 파일의 제품/복귀 불변 산출물 포함, 필수 파일 누락 차단, 완성된 두 산출물의 격리 포털 검증 및 현재04 owner 상태에서 정상 전환·복귀하는 정확 계획이다. 현재 활성 실행 경로에 임의로 파일을 채우거나 기존 계획의 digest를 고쳐 재시도하지 않는다. 변경 산출물/필요 제어 버전·새 계획을 확정하고 별도 적용 결정 전에는 현재 환경을 다시 전환하지 않는다. 기능·UI·Rule·OCR·Parser·추천 개선이나 범용 전환체계 개발은 이 보완에 포함하지 않는다.

기존 소스 [PR20](https://github.com/dongarnd-commits/dongalab/pull/20) HEAD04와 [DATCO CI 성공](https://github.com/dongarnd-commits/dongalab/actions/runs/41590876064)은 유지하며 전체 제품시험을 재실행하지 않았다. CI 성공을 실제18445 포털 합격으로 해석하지 않는다. 실제 적용 보호 근거는 원래 data-owner의 `storage/private/runtime/apply04-20261104/` 안 `activation-attempt.json`, `post-boot-core-proof.json`, `browser-focused-proof.json`, `final-application-result.json`, 전후 DB/파일 hash와 실패 진단이다. 보호 산출물/로그는 Git·CI에 넣지 않는다. 준비근거77·고정control e98·제품04·복귀9b의 커밋 객체는 변경하지 않았다.

RT-01·RT-02의 정확한 연결 시험 근거는 확인되지 않아 별도 업무품질 검증 대기로 유지한다. 자유문장 숫자·기간 관련 합성 미지원5건도 유지한다. 실기업 평가·정식공고 기반 B·최종 인수는 미실행이다. 실자료 조건은 기존 단일 결정표를 그대로 사용하며 추가 승인으로 간주하지 않는다. 포털 복구와 기술 검증이 끝난 뒤 비민감 TEST 자료로 수요기업 A–G → 운영자 회사/제출본 유지·보완요청 → 관리자 자산 상세/Excel 비교 → 공통 로그아웃 순서로 사용자 검수를 안내한다. 지금은 사용자에게 오류 재현·로그 수집·빈 화면 반복 검수를 맡기지 않는다.


### 2026-11-04 포털 산출물 최소 보완 계약 — 검증 진행

사용자는 포털 런타임6개 누락의 최소 수정·격리검증·현재04에서의 새 전환계획 준비만 승인했다. 실제18445 정지/재기동/재전환/복귀·실기업자료 사용은 승인하지 않았다. 변경은 acceptance_release의 필수 파일/빌드 출처 계약, 기존 handover의 현재 e98 04 정상 인계 경로와 집중시험에 한정한다. 제품04·복귀9b의 업무 코드/HEAD·DB Schema·권한·기능·UI·Rule·OCR·Parser·추천은 변경하지 않는다. 새 계획의 PENDING 상태는 승인 전 아무 owner 요청도 만들지 않으며, 과거 계획/승인을 신규 실행물에 재사용하지 않는다. 현재04 정상 STOP에는 새 결정에 결합한 별도 이전-owner STOP receipt만 사용하고, 과거 STOPPED725 상태의 공유 읽기 fence를 연속 유지해 구 START 경합을 막는다. 현재 집중 단위131건 PASS이며 실제 분리 실행물/포털 및 인계 시험은 아직 미완료다.
