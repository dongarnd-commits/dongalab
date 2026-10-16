# PHASE 1 통합 구현 — W0 확인 및 W1 진행 기록

상태: IN_PROGRESS. A/B/C Gate 및 사용자 수용은 완료되지 않았다.
기준 main: f83851bff49f9ec38b7de803c80238f5b363eb9d.
작업 브랜치: feat/datco-phase1-integrated-e2e-v1.

## 실제 확인

- 작업 시작 main/작업 트리 clean, fetch 이후 origin/main 일치.
- 접근 가능한 origin의 모든 브랜치에서 Company/Fact/Improvement 명칭의 Python/TSX 구현 파일은 발견되지 않았다. main의 전체 app 파일 목록과 소비 계약을 확인했다. 확인할 수 없는 연구원의 미공유 작업까지 없다고 단정하지 않는다.
- app/capability/input.py의 운영 기본값은 UnavailableImprovement, API는 입력 미연결 503을 유지한다. tests/proposal_browser_setup.py의 ProposalInputs는 테스트 Provider이며 운영 연결이 아니다.
- local_actors에는 단일 role만 있고 CompanyMembership/Company/Site/CompanyFactVersion/ImprovementVersion 저장 테이블이 없다. 브라우저가 보내는 Company ID만으로 Scope를 부여해서는 안 된다.
- .env의 변수명만 검사했다. AI Provider 관련 변수는 없고 Settings에도 AI Provider 계약이 없다. Secret 값은 출력하지 않았다.
- 기존 analysis_runs/candidates/reviews CHECK 및 deferred 공통 계보 Trigger는 Notice/Capability/SupportMatching 분기만 허용한다. Company 분석을 Notice 분기로 위장하거나 별도 중복 Run 테이블로 우회할 수 없다.

## W1에서 추가한 독립 경계

company/documents.py: 파일 내용을 쓰거나 외부로 보내지 않는 로컬 파서.
PDF text는 페이지, DOCX는 문단 순번, XLSX는 시트·셀, UTF-8 text는 원래 줄 번호와 SHA256을 보존한다.
DOCX 페이지·머리글·바닥글·그림, XLSX 스타일/날짜/단위 추론·수식 계산·그림은 미지원이다. XLSX 수식의 캐시값은 사실값으로 추출하지 않는다.
스캔 PDF는 페이지별 OCR/수동 확인 필요를 표시한다. JPG/PNG는 제한적 signature 검사만 하며 디코딩/OCR/이미지 의미분석 완료로 표시하지 않는다.
파일 크기·ZIP 펼침 크기/entry 수·경로/매크로·XML entity·결과 텍스트 수 제한을 검사한다. 파일 파싱은 업로드 인증·악성코드 검사·별도 Worker 시간/메모리 격리를 대체하지 않는다. 아직 업로드 API에 연결하지 않았다.

company/analysis.py: 서버가 제공한 입력 Company/Version/digest와 일치하는 구조화 후보만 수용한다. 근거 descriptor와 실제 quote, EXTRACTED 값의 원문 포함 여부를 검사한다. 재무 후보는 기간·단위를 요구한다.
Provider 미설정, 미승인 외부 호출, 알 수 없는 Mode는 실행 전에 차단한다. Provider 예외의 원문/Secret은 반환하지 않는다. TEST_FIXTURE와 REAL_AI를 구분한다. 실제 AI Adapter·실호출은 없다.
검증된 후보도 Fact 확인이 아니며 Company Master에 쓰지 않는다. 추론의 의미적 정확성은 사람 검토가 필요하다.
공통 DB/State/Permission/API/기존 소비 계약은 이번 변경에서 수정하지 않았다.

## 공통 구현 영향과 후속 검토할 계약

다음은 아직 구현·승인 완료로 기록하지 않는다.

1. Company/Site/Membership과 입력 Version·Private File/Evidence를 typed FK로 저장한다. 기존 Role 의미와 지정 기업 Scope를 유지하고 ADMIN의 Operator 권한을 자동 상속하지 않는다. 최초 소속/계정 설정은 서버의 관리 경로로만 수행한다.
2. 기존 공통 AnalysisRun/Candidate/Review에 COMPANY_FACT_EXTRACTION 및 IMPROVEMENT_ANALYSIS의 typed context를 증분 연결한다. 기존 Notice/Capability/SupportMatching Trigger·불변 제약·migration chain·FK 검증을 보존한다. 별도 중복 Run/범용 target_type JSON 그래프로 대체하지 않는다.
3. AG-01 입력 저장/Upload, DRAFT→SUBMITTED→REVIEW_REQUIRED→CONFIRMED의 기존 Guard·Actor·정확한 Version을 명시한다. 기업 사실확인과 Operator FactReview를 별도 보존하고 충돌·기간·단위·Site를 분리한다.
4. 이 저장 결과를 기존 ImprovementReader/ConfirmedFact/CompanyBasis 소비 인터페이스에 연결한다. 현재성 비교와 모든 Fact/Proof의 정확한 Version을 제공한다. 미확인 값을 confirmed=True로 조립하지 않는다.
5. 기존 추천 검색을 후보 검색으로 재사용하고 자동 조합은 검토 전 후보로 분리한다. Notice 검색과 R07 IN/NOT_IN 외 조건은 UNKNOWN을 유지한다.
6. Proposal ApprovalRequest를 기업에게 전달된 정확한 Version의 권위로 재사용 가능한지 확인하고 수신·열람 기록을 연결한다. 새 정책이 필요한 공개 범위/State는 임의 확정하지 않는다.

외부 AI의 Provider/모델·전송 자료·보관·비용·개인정보 조건은 사용자 확인 대기다. 다른 작업의 포괄 승인으로 실제 기업문서 외부 전송을 허용하지 않는다.

## 단계별 현재 판정

| 단계 | 판정 | 실제 범위/남은 사항 |
|---|---|---|
| W0 | 검토 진행 | main/원격/소비 계약 확인. 공통 계보 확장 상세 설계·검증·동기화 미완료 |
| W1 A | PARTIAL | 로컬 파서·Provider 출력 경계/단위 테스트. Company DB/API/UI·공통 계보 연결·실AI 미완료 |
| W2 B | NOT_IMPLEMENTED | 기존 Catalog/Composition/Matching 유지. 자동 조합·공고 추천 UI 미완료 |
| W3 C | NOT_IMPLEMENTED | 기존 Proposal 기반 유지. 기업 업무함·전달/열람 동선 미완료 |
| W4 | NOT_TESTED | 새 기업 입력부터 제안 승인까지 실제 E2E 미실행 |
| USER_ACCEPTANCE | PENDING | 사용자 실사용 검수 전 |

실행 결과는 실제 명령의 결과로 별도 기록한다. 이전 PR의 PASS 숫자를 이번 변경의 실행 결과로 대체하지 않는다.


## 구현 순서와 단계 간 전달 계약

아래는 이번 통합 구현 범위의 상세 작업 목록이며 실제 제공 중인 화면/API로 오인하지 않는다.

| 전달 | 송신 데이터 | 수신 측 재검사 | 실패/복귀 |
|---|---|---|---|
| 기업 입력→Intake | Company/Site, 입력 Version, Actor, 원문, 파일 digest/분류 미확정 | 서버 Membership, Site 소속, Draft 현재 Version, 파일 크기/포맷/저장 성공 | 입력 유지, 파일별 실패 사유 |
| Intake→분석 | exact File/입력 Version, Company/Site, 파서·모델·프롬프트 Version | 동일 Scope 실제 파일 digest, 승인된 Provider 전송 범위, 입력 현재성 | 새 Attempt/실패 기록; 이전 성공·Review 보존 |
| 분석→Fact 검토 | Candidate, SourceLocation/quote, 기간·단위·불확실성, 기존 값/충돌 | quote 실존, 분류·필드 검증, Company 사실확인, Operator의 별도 근거 검토 | Conflict/Request/Reject; Master 자동 수정 없음 |
| Fact→Improvement | 확정 FactVersion 목록, 문제/영향/ToBe/제약, 원문·첨부 | Company/Site 일치, 확정 Review 및 현재성, 누락·충돌 | 보완 요청; 재입력은 새 Version |
| Improvement→추천 | 확인된 ImprovementVersion/FactVersion, Catalog 발행 Version | 입력 현재성, Catalog Publish, FeatureRevision 실제 연결 | 추천 없음/일부 해결/추가 확인을 구분 |
| 추천→Composition | 선택 가능한 복수 조합안, Coverage 근거, 제외·전제·미해결 | 운영자 선택/수정, 중복 Feature/Version 충돌, 필요범위 | 자동 저장·확정하지 않고 기존 Composer 재사용 |
| Composition→Notice | exact CompositionVersion, 과제/Company/Fact, 등록 공고 | 실제 Notice/RequirementVersion와 공식 Review, R07 지원 의미 | 검색 연관성과 자격충족 분리; 미지원 조건 UNKNOWN |
| Notice→MatchReview | Snapshot, 각 조건의 충족/충돌/미확인, 모든 Evidence | 기존 항목별 Gate/현재성/필수 보완 완료, MISMATCH 차단 | 기업 Request/Response→Operator 검토→새 Fact/재분석 |
| MatchReview→Proposal | exact PROPOSABLE Review/Completion/InputSnapshot | 기존 Guard·Manifest·지정 승인자·서비스/공고 현재성 | 자동 생성 불가 사유 및 원 검토 화면 연결 |
| Proposal→기업 | 공개 제안내용/정확한 ProposalVersion/ApprovalRequest/수신자 | Content Review·정확한 기업/승인자·전달 대상 Version | 내부 Draft/전체 Manifest/내부 메모는 공개하지 않음 |
| 기업→Decision/출력 | exact Request/Version, 결정/사유, 파일 요청 | 현재 역할·지정 승인자·Company·superseded·파일 digest | 과거 결정 보존, 수정은 새 Version/재요청 |

## 역할별 업무 동선 계획

- 수요기업 EDITOR: 자기 기업 홈→기본/Site/재무/지원이력→개선요구 Draft/Submit→자료 분석상태·후보 사실확인→보완요청 응답. APPROVER의 제안 승인을 대신하지 않는다.
- 수요기업 APPROVER: 지정 요청 업무함→정확한 제안 Version/책임·범위·부담 확인→승인/수정요청/거절→허용된 문서 다운로드. EDITOR 편집권한을 자동 상속하지 않는다.
- DATCO_OPERATOR: 허용 기업 목록→입력·자료·Fact 근거 검토→개선과제 확인→자동 추천/조합안 검토→공고 후보/조건 검토→보완 루프→MatchReview→Proposal 생산/Content Review/전달→승인 이력.
- DATCO_ADMIN: Inventory→Catalog 편집/발행→명시된 접근권한/분석 설정/작업 오류/감사 조회. Operator의 업무 검토/기업 승인을 대행하지 않는다.

각 화면은 한 Company/Site/Improvement Context를 유지하고 다음 Action과 차단 사유를 표시한다. URL의 UUID는 내부 전달 가능하지만 정상 사용자가 복사해 입력해야 하는 필수 동선으로 만들지 않는다. 검증되지 않은 화면 URL/로그인 계정은 제공 중이라고 안내하지 않는다.

## W4 수용 증거 계획

기업 로그인부터 파일 Upload/분석→후보 사실확인→Operator 검토→개선과제→추천/조합→공고→보완→MatchReview→Proposal 편집·전달→지정 기업 승인·다운로드까지 UI Action으로 생성한다. 중간 확정 상태 SQL seed는 사용하지 않는다.
새로고침/다른 세션에서도 저장·Version·Evidence가 유지되어야 한다. 기업 B의 API/파일/근거 직접 접근, 미지정 승인자, stale 입력, 중복/동시 요청, 분석/렌더 실패를 별도 재현한다.
실제 649 원천 SHA 검증과 공개 CI synthetic Fixture는 구분한다. 기존 공용 DB는 읽기 전용 fingerprint 비교만 수행하고 별도 Role/DB/파일/포트의 소유 자원만 정리한다.
주말 이후 실제 사용자의 UI 검수 전 USER_ACCEPTANCE는 PENDING이다.


## 이번 변경의 실제 실행 결과

- 새 문서/Provider 경계 단위 테스트: 최종 32 PASS.
- CI Backend Unit 전체 목록: 최종 87 PASS (새 테스트 32개 포함).
- 기존 격리 Runner backend: Backend 290 PASS / 1 SKIP, Integration 176 PASS / 1 SKIP, Migration upgrade/check PASS. Backend 수집 당시 새 테스트는 30개였으며 이후 보완·추가한 2개는 최종 Unit 전체 목록 87 PASS로 별도 검증했다. 최종 전체 Backend 292 PASS라고 추정하여 보고하지 않는다.
- 격리 실행 nonce: 39009eb94ab0. 공용 DB 쓰기 권한 검사 [false,false,false], public_changed_tables=[], 테스트 DB/Role 정리 완료.
- GitHub Actions actionlint 및 git diff --check PASS.
- 명시된 변경 파일의 Secret 패턴 검사 0건, .env/Private/Runtime 혼입 없음. 실제 Secret 부재를 패턴 검사 하나로 보증한다는 의미는 아니다.
- DMP 원천 SHA256: 28b1967ed77360d0fcc6d5525f6d7395fd899865b2e01e358402edc347d1d368 (변경 없음).
- 기존 Proposal 브랜치 c1914ee, Stash 4aa8e071, Next.js 외부 백업 두 파일 SHA 일치 확인. 기존 체험 서버/자료 변경 없음.
- 이번 로컬 실행에서 전체 Playwright·lint/build는 재실행하지 않았다. 새 UI/새 API/DB Schema 변경은 없다. GitHub 새 Head CI 결과는 별도로 확인한다.
- 실제 기업자료/외부 AI 실호출/기업 입력부터 Proposal 승인까지 통합 UI E2E: 미실행. USER_ACCEPTANCE=PENDING, PHASE1_FULL_E2E=NO.
