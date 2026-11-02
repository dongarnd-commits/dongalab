# DMP 기술자산 관리·자동 솔루션 조합 통합 계약 및 검증 보고

기준 2ee2640836ae1fa07bf4ccf0a34d03a4f27851e0, 2026-11-02 사용자 명시 통합 보완개발 지시.
이 문서는 구현 전 영향 계약과 이후 실제 검증 결과를 한 곳에 유지한다.
현재 검증 상태: LOCAL_AUTOMATED_PASS (2026-11-02). Commit·Push·Draft PR과 최신 HEAD 원격 결과는 해당 Feature Branch의 PR Checks 및 완료 보고를 참조한다. 사용자 최종 인수·운영 배포는 대기 상태다.

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
