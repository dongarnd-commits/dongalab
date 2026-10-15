# R-04 / R-07 최소 계약 확장 승인 요청안

작성일: 2026-10-14. 상태: **PROPOSED / NOT APPROVED**.
이 문서는 승인 요청과 이번 구현 한계를 설명한다. Design Baseline, Decision-001~003을 변경하거나 새로운 Decision을 승인 완료로 기록하지 않는다.
근거: AGENTS §2, docs/03 §6·10·16, docs/07 §3·9·11, 사용자 2차 보완 지시 §4.5·5.9·9.

## 현재 확인한 제한

- `analysis_runs.attempt_id` → `job_attempts.id`, `version_id` → `notice_versions.id`: 둘 다 NOT NULL/RESTRICT. attempt_id UNIQUE.
- `background_jobs.ck_jobs_kind_target`: NOTICE_ANALYSIS에는 NoticeVersion 필수, BIZINFO_COLLECTION에는 NULL. 동기 분석에 가짜 Job 생성 금지.
- `analysis_candidates`: run_id 및 source_locations.location_id 필수. SourceLocation은 Notice Source/Run 필수.
- `analysis_reviews`: Notice 중심 공통 candidate_id FK/UNIQUE와 CONFIRM/REQUEST_MORE_INFORMATION/REQUEST_REVISION/REJECT Check. 공식근거 확인 필드 필수.
- `capability_assessments`, `capability_match_candidates`, `capability_match_reviews`: 도메인 이력은 존재하나 공통 Run/Candidate/Review FK가 없음.
- Requirement Item은 kind/content/location/candidate만 저장한다. 원문 Human CONFIRM은 코드/연산/예외/기준일의 별도 구조화 검토 승인이 아니다.
- 권위 있는 Company Fact/Improvement Provider는 정상 실행에 연결되지 않음. 해당 503은 유지해야 함.

## R-04 선택한 최소 확장안: 기존 공통 테이블 + 명시 typed 관계

별도 중복 Run 엔티티를 만들지 않는 A안을 제안한다. B안(기존 Notice Run 그대로 + 별도 공통 실행 부모)은 중복 메타데이터/이력 소유권 분리 위험 때문에 우선하지 않는다.
아래는 **구현 전 승인 대상**이며 실제 Migration/ORM에는 적용하지 않았다.

| 대상 | 제안 변경 | 무결성 조건 |
|---|---|---|
| analysis_runs | analysis_kind 추가, 기존 행 NOTICE_REQUIREMENT_ANALYSIS; version_id/attempt_id 조건부 nullable | Notice kind는 기존 두 FK 필수. 동기 CAPABILITY_ASSESSMENT/SUPPORT_MATCHING은 Notice FK NULL. FK 자체 및 attempt UNIQUE 유지 |
| analysis_capability_contexts (신규 typed 관계) | run_id PK/FK, composition_version_id FK, capability_version_id FK, assessment_id UNIQUE/FK | 실제 고정 CompositionVersion의 context가 ImprovementVersion 입력. 링크의 Capability/Assessment/Company 일치. 삭제 RESTRICT |
| analysis_match_contexts (신규 typed 관계) | run_id PK/FK, snapshot_id FK, match_candidate_id UNIQUE/FK | 실제 Snapshot과 Candidate 일치. requirement_version_id/CompositionVersion 기존 FK 재사용 |
| analysis_candidates | location_id 조건부 nullable; capability_assessment_id 및 match_candidate_id typed FK 추가 | Notice 위치 또는 Assessment 또는 MatchCandidate 중 정확히 하나. Run kind와 대상의 일치는 deferred constraint trigger/검증된 typed 복합 FK로 강제 |
| capability_assessments / capability_match_candidates | analysis_run_id FK 및 legacy_lineage 표시 | 기존 행은 legacy 미연결로 솔직히 보존. 새로운 행은 run 필수. 과거 행에 가짜 실행/시간/검토자 생성 금지 |
| analysis_reviews | review_kind 추가, Notice outcome 조건부 필수; 도메인 검토의 outcome은 NULL | Notice 기존 outcome/official_verified Check 유지. 기존 전체 candidate_id UNIQUE는 Notice review_kind에 대한 부분 UNIQUE Index로 대체하여 Notice 1회 검토를 유지하고 도메인별 실제 검토 이력을 허용. Domain의 원래 state/disposition은 typed 결과 관계에서 보존; HOLD를 CONFIRM으로 억지 매핑 금지 |
| capability_assessment_analysis_reviews (신규 typed 관계) | analysis_review_id PK/FK, assessment_id FK, 기존 Audit 행 FK | 실제 REVIEW_CAPABILITY_ASSESSMENT의 Actor/time/decision/note 참조, 중복 방지 |
| capability_match_reviews | analysis_review_id UNIQUE/FK 및 legacy_lineage 표시 | 새 MatchReview는 실제 Candidate → 공통 Candidate → 공통 Review로 연결, Reviewer 일치 |

typed context는 공통 AnalysisInputReference의 종류별 관계이며 고정 입력 Version/Snapshot을 참조한다.
analysis_kind/review_kind는 분석 대상 구분이며 새로운 업무 State/Role/Permission을 만들지 않는다.
Review별 공통 Candidate 연결/typed Review 존재와 Run별 정확히 한 context를 deferred trigger로 검증한다. 생성 트랜잭션에서 Run→Domain Candidate→typed Context→common Candidate 순서를 허용하되 Commit 시 필수 관계를 검사한다.
`provider_version`/`extractor_version`는 실제 비교 구현 버전만 기록한다. 없는 LLM/Extractor 식별자를 생성하지 않는다.
동기 비교에는 Job을 만들지 않는다. **background_jobs/job_attempts와 Job target Constraint 확장은 이 최소안에 포함하지 않는다**. 비동기로 바꿀 필요가 생길 때 별도 승인한다.

## 기존 데이터 및 Migration

Up: 새 nullable typed 컬럼/관계 생성 → 기존 Notice kind만 정확히 backfill → 기존 도메인 이력 legacy 표시 → 데이터/FK/Check 검증 → 신규 행 typed 관계 필수화.
기존 Notice ID/Source/Run/Candidate/Review/RequirementVersion/시간/공식성 값은 보존한다. legacy 도메인 행은 연결 없음으로 표시하고 재실행 시 새로운 진짜 Run을 생성한다.
Down: 새로운 비Notice Run/Review/typed 관계 또는 lineage가 사용된 신규 데이터가 있으면 **자동 downgrade 거부**. 백업·명시적 이관 승인 없이 삭제하지 않는다. 새 데이터가 없을 때만 새 관계/컬럼을 제거하고 기존 NOT NULL/Check를 복원한다.
운영 DB 적용은 이 요청의 승인과 별개다. 먼저 격리 DB Migration/데이터 보존 테스트가 필요하다.

API/Service 영향: notice_schema.py, 공통 Notice Store/Worker의 기존 Notice 분기, capability/application.py save_composition/review_assessment/prepare_match/review_match, 조회 응답·OpenAPI·생성 TypeScript, Alembic 새 migration. docs/03·07·11은 승인된 범위만 함께 동기화한다.
필수 테스트: 과거 Notice hash/ID/Review 보존, Notice 필수 FK 유지, 잘못된 typed 대상/Company/Version 거부, 새 Run 및 Review 실제 연결, Evidence 역추적, 동기 분석 Job 없음, idempotent 재요청/별도 재분석, stale/권한/다른기업 Guard, Up 및 안전 Down 거부, 전체 격리 회귀.

**승인할 정확한 문구**:
“R-04에서 기존 공통 AnalysisRun/Candidate/Review를 Notice·CapabilityAssessment·SupportMatching에 명시 typed 관계로 확장하는 위 최소안을 승인한다. Notice 분기의 기존 필수 참조와 이력은 보존하고, 동기 분석에 가짜 Job을 만들지 않는다. 과거 Capability/Matching의 미연결 이력은 legacy로 남기고 새 실행부터 실제 공통 계보를 생성한다. 관련 docs/03·07·11 동기화와 격리 DB Migration·서비스/API·회귀테스트 구현을 허용한다. 업무 State/Role/Permission 및 운영 DB 변경은 승인하지 않는다.”

## R-07 이번에 구현한 독립 범위

내부 immutable 비교 DTO/Service 및 optional 소비측 reader를 구현했다. 이는 다른 연구원의 Company 물리 Schema나 Provider API 확정이 아니다.
- 별도 사람이 검토한 구조화 코드/명시 IN·NOT_IN만 비교한다. 숫자·기간의 업무 연산/단위 정책 및 자유원문 자동 해석은 구현하지 않는다.
- Fact의 Company/Site, FactVersion, 확인/현재성, Review, Evidence, 기준일 유효성 확인. Scope 위반은 404.
- 조건의 RequirementVersion/Item/공식 확인/SourceLocation, 별도 구조화 검토/기준일 확인.
- UNKNOWN/CONFIRMED_SATISFIED/CONFIRMED_CONFLICT는 내부 비교 의미. 기존 JSON Candidate/Snapshot 안에 결과와 입력을 기록하고 기존 상태만 사용한다.
- docs/07 §9가 허용한 명확한 필수 충돌만 MISMATCH **후보**. 공급자격·서비스/지원범위 미확인은 별도 유지; FIT/PROPOSABLE 자동 부여 없음.
- 기존 Provider에 비교 reader가 없으면 빈 비교 입력과 NEED_MORE_INFO. 정상 Improvement Provider 503 유지.
- 테스트는 자체 PostgreSQL test_confirmed_fact_versions/test_reviewed_condition_versions와 실제 로그인/Membership/원문 검토/파일을 사용한다. 테스트 표준코드와 구조화 검토는 TEST 명시이며 운영 승인으로 취급하지 않는다.

## R-07 남은 최소 승인 및 연구원 계약

운영 공고조건을 자동 구조화하지 않는다. 다음 계약은 아직 승인/연동 전이다.
1. NoticeRequirementVersion/Item에 귀속하는 별도 ReviewedConditionVersion: 실제 Item/Version/SourceLocation/구조화 Review FK, subject(기업/공급자), attribute/code dictionary, 연산·값·단위·기준일·예외·적용부문, Actor/time·불변 Version.
2. 사람이 원문 검토와 구조화 조건 검토를 구분하여 승인하는 API/화면. 기존 CONFIRM을 구조화 조건 자동 승인으로 확대하지 않음.
3. 연구원 Provider에서 실제 CompanyFactVersion/FactReview/Evidence/Validity/Company·Site Scope를 반환하는 소비측 매핑. 필드/코드 의미는 연구원 계약 확인 후 확정.
4. 실제 DB FactVersion typed FK/MatchInputReference는 해당 Company Schema가 확인된 뒤 승인. 내부 Snapshot의 TEST Fact ID를 운영 FK처럼 보고하지 않음.

**승인할 정확한 문구**:
“R-07의 운영 연결을 위해 공고 원문 확인과 별개인 불변 ReviewedConditionVersion 및 구조화 Human Review 계약의 상세설계안을 작성하도록 승인한다. 실제 Item/RequirementVersion/SourceLocation 연결, 기업·공급자·사업부문·기준일·예외·단위를 구분하고 연구원 Fact Provider와 코드 의미를 합의한다. 아직 이 승인으로 물리 Migration, 자유문구 자동 적격판정, 새 업무 State/권한 또는 운영 데이터 변경을 허용하지 않는다.”

승인 전 가능한 독립 비교/Adapter/격리 테스트/UI 근거 표시 작업은 이번 작업에서 수행한다. R-04 실패 Assertion은 보존한다. 이 문서는 확정 Decision이 아니다.

## 승인 이후 상태 — Decision-004 / 2026-10-14

사용자 최종 통합 명령으로 **R-04 구현과 R-07 상세설계 진행이 승인**되었다. 위 본문은 당시 승인 요청안의 역사적 기록이며 최종 구현 계약은 docs/03·07·11의 Decision-004 동기화를 따른다.

보완된 실제 R-04에서는 Assessment의 본질적 입력을 ImprovementVersion × CapabilityVersion으로 유지하고 CompositionVersion은 선택적으로 연결한다. 동일 입력의 실제 재평가는 새 결과 Assessment/Run/Candidate를 만들고 previous_assessment_id로 이전 결과·검토를 보존한다. typed Context의 assessment_id/match_candidate_id에 전역 UNIQUE를 두지 않는다. 공통 Run/Candidate/Review를 재사용하고 실제 도메인 검토 결과를 별도 typed 기록으로 연결한다. Notice의 필수 FK와 단일 공식 Review를 보존한다. 새 행의 legacy 우회를 금지하고 기존 미연결 행은 가짜로 backfill하지 않는다.

R-07 범용 운영 엔진/ReviewedConditionVersion Migration·정책·Provider 도입은 **여전히 구현 미승인**이다. 상세설계 산출물은 R07_REVIEWED_CONDITION_DESIGN.md이며 PROPOSED / NOT APPROVED FOR IMPLEMENTATION 상태다. 운영 DB 적용 및 Git 반영은 이번 승인에 포함되지 않는다.
