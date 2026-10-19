# 수요기업 증빙 우선 통합 v0.3

## 비교 및 영향범위
참조는 Repository 외부 DATCO_UI_reference_v0.2/source/DATCOV02.tsx, 화면명세, README와 가상 샘플이다. DATCO ONE의 네이비·블루·화이트 카드, 서류로 가져오기/직접 입력, 추출 후보 선택·정정·적용 UX를 기존 Shell에 통합한다. 가짜 로그인·메모리 저장·가상 Fact/승인·미연결 AI 성공은 가져오지 않는다.

기존 Company 최소 식별은 기업명·사업자번호이고 재무·사업장은 선택 입력이다. 기존 POST Company/File/parse/evidence/candidates/profile/sites와 GET Detail/download를 재사용한다. 신규 API·Enum·Schema·Migration·Role·State·Provider 소비계약은 없다. 기존 필드의 명시 라벨 규칙만 보완하며 공통 COMPANY_FACT_EXTRACTION 계보를 유지한다. 정확한 매출 형식 `매출액(2025,원,KRW): 1000000`은 연도·단위·통화를 원문에서만 읽고, 문맥이 없는 금액은 후보로 확정하지 않는다. 직원수는 기존 employees 후보로만 저장된다. 담당자·세부 사업이력은 기존 Profile 폼에서 직접 입력한다.

## UI 및 무결성
기업 홈 주요 버튼→/company?tab=onboarding. 기존 로그인·역할 홈·운영자/관리자 업무는 유지한다. 기업 전용 증빙 우선 화면은 최소 식별→실제 Private 업로드→명시적 파싱 실행→원문·출처·기존값·Fact 비교→선택 정정→폼 초안→기존 API의 불변 입력 Version/사업장 Version 저장→개선요구 인계다.

후보 적용은 브라우저 초안이며 자동 Fact 확정이 아니다. 비선택값은 적용하지 않고 기존 비어있지 않은 입력 교체는 명시적 허용이 필요하다. 동일 항목·기간의 중복 선택은 막고 원후보/다른 출처는 보존한다. 사업자번호 변경은 기존 Guard를 유지한다. 사용자 정정·적용 기록은 원파일을 참조한 기존 MANUAL_REVIEW Evidence/Candidate로 별도 보존한다. descriptor에 원후보와 실제 저장 Version을 기록하고 원문값·초안값·최종 저장값을 구분한다. 이는 기존 명시 관계를 변경하는 새 typed FK가 아니라 사람 입력 출처 기록이다. Profile 저장 후 출처 기록 실패는 부분 성공으로 표시하고 재시도를 허용한다. 기존 기업 사실확인·운영자 Review·FactVersion은 자동 생성/갱신하지 않는다.

자료 유형은 업로드 안내용 UI 선택이며 새 분류 Enum으로 저장하지 않는다. PDF 페이지/DOCX 문단/XLSX 시트·셀은 기존 파서 Evidence다. 스캔·이미지·암호화·오류·추출값 없음은 실패 또는 수동 경로로 안내한다. 연도·단위·통화 불명확 값과 자동 인원 Profile 저장·공고/서비스 자동 추천은 미구현을 표시한다.

## 검증 및 완료판정
격리 DB/API/Web/Private File Runner로 실제 브라우저와 Backend/Integration을 검증하고, 기존 W0/W1/Capability/Matching/Proposal과 lint/build/API 타입을 확인한다. 실제 결과는 실행 후 기록한다. 기존 docs00~11의 Source/Version/Human Review/Permission 계약을 유지하며 동결 정책을 변경하지 않는다.

REAL_AI_SEMANTIC_ANALYSIS=BLOCKED_BY_POLICY; W2_AUTO_RECOMMENDATION=NOT_STARTED; W3_PROPOSAL_INTEGRATION=NOT_STARTED; PHASE1_FULL_E2E=NOT_COMPLETED; USER_ACCEPTANCE=PENDING; SYSTEM_ACCEPTANCE=NOT_TESTED.


## 실행된 검증 증거
- 관련 W1/workspace Backend: 16 PASS (20fea470313d).
- 전체 Backend: 311 PASS / 0 FAIL / 1 SKIP. Integration 및 migration-check 종료 0 (cef4d08c65dc); 공용 DB 변경 없음·격리 DB/Role 정리 성공.
- 신규 증빙 정상/예외 브라우저: 2 PASS (04b23c6cb680). PDF/DOCX/XLSX 원본 바이트·Metadata, 페이지/문단/시트·셀 Evidence, 선택 해제·정정·초안, 실제 Profile/Site/재무/사업이력 저장, Fact 보존·수정값 출처, 재로그인·개선요구 맥락, 타기업·잘못된 파일·크기 초과·추출값 없음·중복 후보·422 입력 오류·409 stale 저장을 검증했다.
- 기존 소유 체험 환경에서도 정상 수직 흐름 1 PASS. 별도 실제 브라우저에서 새 원본 추가·재분석 후 기존 Fact 전체가 동일하고 신규 후보는 미확인임을 확인했다.
- 작업 전 기존 20개 업무 테이블의 모든 행과 기존 Private 파일 바이트를 보존했다. 새 가상 TEST 기업·자료·명시적 검토 기록만 시연 과정에서 추가했다. 예전 소스는 before-v03-web-src에 새로 보존했으며 기존 Stash·백업·원자료를 삭제하지 않았다.
- 첫 신규 테스트는 직접 POST의 Origin 누락으로 기존 CSRF Guard가 거절했다. 테스트를 기존 계약에 맞췄고 Guard는 변경하지 않았다.
- 전체 회귀에서 기존 재조회 중 탭 이동 시 늦은 응답이 이전 URL 탭을 다시 기록할 수 있는 경합을 확인했다. 기존 처리 중에는 탭을 비활성화하여 URL/화면 맥락을 보존했다. 운영자에게는 새 기업 담당자 전용 탭을 표시하지 않는다. 최종 전체 결과는 아래에 별도 기록한다.


## 최종 결과
- 전체 Integration: 195 PASS / 0 FAIL / 1 SKIP / 116 deselected (cef4d08c65dc).
- 최종 전체 Playwright: 30 PASS / 0 FAIL / 1 SKIP (31개, 01aaa881b631). lint / build / API 타입 비교 PASS. 기존 W0/UI1/W1·한국어 공고·Capability·Matching·Proposal·권한·모바일 회귀 포함.
- 기존 선택적 Backend 원문 검사와 별도 API 장애 조건부 브라우저 검사의 SKIP을 유지했다. 실제 저장 한국어 공고 브라우저 검증은 PASS다.
- COMPANY_DOCUMENT_FIRST_UI / REAL_FILE_UPLOAD / REAL_PDF_PARSING / REAL_DOCX_PARSING / REAL_XLSX_PARSING / CANDIDATE_SOURCE_TRACEABILITY / CANDIDATE_REVIEW_AND_EDIT / SELECTED_FIELD_PREFILL / REAL_COMPANY_DB_SAVE / REAL_FINANCE_HISTORY_DB_SAVE / RELOAD_AND_RELOGIN_PERSISTENCE / COMPANY_SCOPE_SECURITY / IMPROVEMENT_SCREEN_HANDOFF / COMPANY_DOCUMENT_FIRST_BROWSER_E2E: PASS.
- 실제 외부 AI/OCR·일반 표 문맥 추론·자동 서비스/공고 추천은 구현하지 않았다. 담당자/정부사업 세부 이력은 수동 입력, 직원수는 기존 Fact 후보에서 검토한다. 위 Gate는 이 명시적 지원 범위의 기술 검증이며 전체 업무·사용자 인수가 아니다.
