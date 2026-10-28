# 운영자 Backend 재사용 감사 v1

기준: main `9a9c6eef3b0765894dd2d739d9fffaacdcc8d2f4`, PR #9~14 병합 코드. 2026-10-26 사용자 명령은 Slice 0 감사와 Slice 1 구현·격리 회귀·전용 브랜치 Commit/Push·Draft PR만 승인한다. 이후 Slice는 사용자 검수 후 진행한다.

| 사용자 업무 | 기존 Backend / API / 데이터 근거 | 기존 운영자 포털 연결 | 판정 / 재사용 방향 |
|---|---|---|---|
| 로그인·Role·Company Access | local_auth, notice/session, CompanyApplication.scope/grant, company_memberships | 실제 연결 | 실제 연결·사용 가능. 관리자는 운영자 업무권한을 상속하지 않음 |
| 기업·사업장·재무·수행이력 | CompanyApplication.detail, company_input_versions/site_versions, company/business_records.py | 조회 연결 | 실제 연결. 현재 기업정보와 제출 당시 사업장을 구분 |
| 개선요구 접수·제출본 | improvement_versions / improvement_reviews의 SUBMIT, 기존 actions API | 최신 Root를 따라가 초안이 섞임 | 일부 기능만 존재. Slice 1에 불변 SUBMIT 기반 읽기 Projection 추가 |
| File·OCR·Evidence | files/parses/evidence, company/documents.py·ocr.py·statement_documents.py, 기존 download | 실제 조회·다운로드 | 실제 연결. Private Storage 및 기존 Scope/digest 검사 재사용 |
| 자동 개선요구 분석 | 수동 구조화, RULE_BASED 문서 추출, 공통 계보 | AI 의미분석 없음 | 일부 기능만 존재. 외부 AI Provider/모델/전송·비용·보존 정책 추가 결정 필요 |
| 보완 요청·응답 | company/information_requests.py, InformationRequest/Response/Review 및 send/respond/review API | 기업 통합 업무에서 실제 연결 | 실제 연결·사용 가능. 자동 초안 작성은 미구현. 기존 Panel 재사용 |
| DATCO 솔루션 검색·추천 | capability/application.py·search.py, /capability/catalog, improvements/{version}/candidates, published CapabilityVersion | 신포털 미연결, 구형 /capability 존재 | Backend 존재/UI 미연결. 검색 근거는 키워드·규칙 기반이며 AI 의미분석으로 표시 금지 |
| 솔루션 조합 | /capability/compositions 및 versions, service_composition_versions | 신포털 미연결 | Backend 존재/UI 미연결. CompanyProvider의 확인·현재성 Guard 유지 |
| 공고 수집·요건 | api/collection.py·notice.py, Collector→NoticeVersion→Analysis, Live/Snapshot 경로 | 신포털 미연결, /notice 존재 | Backend 존재/UI 미연결. 범용 한국어 요건 자동 확정은 미완료 |
| 자격·3자 매칭 | capability/comparison.py·application.py, matches/review, MatchInputSnapshot/Review | 신포털 미연결 | 일부 기능 존재. UNKNOWN/충돌 유지, 자동 Top3 추천은 미구현 |
| 제안서 자동 작성 | proposal/application.py·policy.py, create/version/review, 불변 Manifest | 신포털 미연결, /proposal 존재 | Backend 존재/UI 미연결. 현재 11개 내용 계약을 새 9개 구조로 임의 변경하지 않음. Slice 5 계획 과제 |
| DOCX/PDF·전달·승인 | proposal/documents.py, export/files/download, approval/inbox/decision, recorded_authorization | C10과 구형 화면 연결 | Backend 존재/UI 미연결. 정확한 Version·지정 승인자·기록자·원본 보존 재사용 |
| 감사·이력 | company/audit, analysis lineage, Proposal review/manifest, 불변 DB Trigger | 일부 표시 | 실제 Backend 존재. 사용자 UI에서는 근거/변경 이력 안으로 정리 |

관련 실행 검증: test_company_workflow.py, test_company_v14.py, test_portal_context.py, test_capability_matching_comparison.py, test_matching_integrity.py, test_proposal_preparation.py, test_proposal_production.py, test_operator_intake.py 및 실제 PostgreSQL/Web E2E. 최종 실행 결과는 OPERATOR_SLICE1_IMPLEMENTATION_REPORT.md에 기록한다. 코드 존재만으로 전체 기능 PASS를 선언하지 않는다.

## Slice 1 영향과 한계

GET /company/operator/intake 및 /company/operator/intake/{company_id}?version_id= 는 기존 DATCO_OPERATOR Role/Membership 내 읽기 Projection이다. DB·Role·State·Assignment·기존 소비 Provider·기존 navigation 계약은 변경하지 않는다. 접수 건은 Root 현재 상태가 아닌 정확한 Version의 SUBMIT 기록으로 판단한다. 현재 Root가 DRAFT여도 과거 제출본은 유지하며 새 DRAFT는 접수 목록에 포함하지 않는다.

기존 SUBMIT에는 CompanyInputVersion Snapshot FK가 없다. 임의 시각 추정으로 과거 기업정보를 만들지 않고 현재 기업 입력과 과거 제출 개선요구/명시적 Site ordinal을 분리한다. 운영자 의견 저장의 신규 계약은 추가하지 않는다. 기존 Company Fact 확정·원문 변경·승인 Gate를 우회하지 않는다.

Slice 2~5: 자동 분석 Provider/보완초안 → 발행 Catalog 기반 후보·조합 → 검증된 Notice 요건·최대 3개 추천·UNKNOWN 보존 → 기존 Proposal 계약 기반 9개 사용자 장 구성 검토·출력·전달. 각 Slice는 별도 사용자 지시 후 구현한다. 외부 AI 자료 전송, 운영 DB Migration, 물리 삭제는 승인 범위 밖이다.
