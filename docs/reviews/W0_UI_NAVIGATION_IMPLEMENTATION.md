# W0 UI Foundation — 실제 구현·화면 Inventory

사용자 W0 실행 명령의 승인 범위다. 시작 Branch feat/datco-phase1-integrated-e2e-v1 / HEAD 2db747eb822b3ceb8ef6039c9885f445215a8aff, Working Tree clean을 확인했다. 기존 W1, Stash, 외부 백업, Private 자료를 보존한다. DB Schema/업무 State/Role/승인 계약은 변경하지 않는다.

## 실제 라우트와 화면

실제 page.tsx 라우트는 6개다. 기존 /, /company, /notice, /capability, /proposal 5개를 공통 Shell로 연결하고 /login 1개를 추가했다. 탭/역할별 Projection은 독립 페이지 수에 중복 합산하지 않는다.

| 화면/역할 | URL | 표시·주요 Action | 실제 API | 저장·조회 | 이전/다음·오류 |
| --- | --- | --- | --- | --- | --- |
| 공통 로그인 | /login | 기존 계정 인증, 역할별 홈 진입 | POST /notice/session | local_sessions/local_actors/audit_records | 실패 사유 표시, 비밀번호 URL/로그 출력 없음 |
| 기업 홈 E/P | / | 허용 기업, 입력·자료·미검토 후보·과제 및 P의 전달된 승인 요청 | GET /workspace | Company Membership/입력/Fact/Improvement, 지정 Proposal 요청 | 실제 데이터 없으면 등록된 업무 없음, E에게 P 승인 메뉴 제공 안 함 |
| 운영자 홈 O | / | 허용 기업·자료·미검토 후보·과제·저장 조합/매칭·현재 승인요청 | GET /workspace | 기존 Company/Composition/Match/Proposal | 숫자를 완료율/선정가능성으로 해석하지 않음 |
| 관리자 홈 A | / | 실제 기능/발행 Catalog 건수·기업 접근관계 링크 | GET /workspace | dmp_features/capabilities/companies 이름 목록 | 업무 검토·기업 승인 상속 없음 |
| 기업 기본·재무·이력 E 입력/O 조회 | /company?tab=profile | 기업명 등록/선택, 원래 연도/기간/단위/이력 저장 | /company, /company/{id}/profile | company_input_versions/Evidence/후보/Audit | Company 선택 및 Site/자료 단계 |
| 사업장 | /company?tab=sites | 복수 Site 등록·수정·이력 | /company/{id}/sites | company_sites/site_versions | 이전 기업 입력 초기화, 잘못된 참조 API 차단 |
| 자료 제출·원문 | /company?tab=files | 실제 업로드/다운로드/파싱/수동 근거 | 기존 Company File/parse/Evidence API | Private 파일/SHA256/parse/Evidence | 파싱 미지원·실패 표시, OCR 완료 위장 없음 |
| Fact 검토 | /company?tab=facts | E 사실확인/정정, O 별도 근거 검토 | 기존 candidate acknowledge/review | 불변 Review/FactVersion/공통 계보 | 누락/충돌/권한/현재성 Guard 유지 |
| 개선과제 | /company?tab=improvement | 원문 Draft/Submit, O 수동 구조화, E exact 확인, O 확정 | 기존 improvements/actions/context | ImprovementVersion/Review/Fact/Evidence links | 원문/과거 이력 보존, 저장 Version과 URL 동기화 |
| 기업 접근관계 A | /company | 기존 계정에 명시적 Company 접근 부여 | GET /company/access, POST /company/{id}/access | 기존 immutable Membership/Audit | A에 기업 Private Detail/Fact 검토권한 부여 안 함 |
| 기능 원천 A/O | /capability?view=features | 실제 Inventory 검색·조회, 허용된 Import | 기존 features/imports | feature_imports/revisions/members | 실제 DMP 연동/자동 추천과 구분 |
| Capability Catalog A 작성/O 조회 | /capability?view=catalog | 기존 편집·발행·Version | 기존 catalog/draft/publish | capabilities/versions/features | 기존 낙관 잠금·Publish Guard 유지 |
| 서비스 조합 O | /capability?view=composer | 기업/과제명으로 현재 입력 선택, 기존 후보/Composition 작성·조회 | 기존 improvements/candidates/compositions | 기존 CompanyProvider/CompositionVersion/Assessment | 자동 추천 아님, 미확정/오래된 입력 차단 |
| 공고 운영 O | /notice | 기존 저장 Live/명시적 Demo 공고·원문·사람 검토·수집 | 기존 Notice/Collector API | NoticeVersion/Source/Run/Review/Requirement | 공통 메뉴에서 연결, 기존 수집 Mode/Guard 유지 |
| 매칭 검토 O | /capability?view=matching | 저장 조합명·공고명·확정 요건 선택, 기존 Match/Review 조회 | 기존 matches/review/proposal-preparation | MatchSnapshot/Candidate/Review | 서비스 적합과 공식 자격 구분, 자동 추천 완료 표시 없음 |
| 제안·승인 O/P | /proposal | 이름으로 후보/제안 선택, 선행 검토·내용 Version·승인·DOCX/PDF | 기존 Proposal API | ProposalVersion/Manifest/Review/Request/Decision/Private File | 기존 생성·현재성·지정 승인 Guard 유지 |
| 실제 연결 상태 | / 하단 | Web/API/PostgreSQL readiness | /health, /health/db | 연결 상태만 조회 | 미연결을 READY로 표시하지 않음 |

## 공통 UI와 맥락

Root Layout의 Shell은 사이드바·역할별 메뉴·사용자 이름/역할·명시적 로그아웃·현재 기업/사업장/과제·업무 단계·이전/다음 화면·오류 표시·반응형 구성을 제공한다. 서버에서 읽은 Role/Membership으로 메뉴와 선택 목록을 만든다. 준비 중 메뉴는 disabled 텍스트이며 가짜 완료 화면으로 연결하지 않는다.

URL의 company/site/improvement와 composition/candidate/proposal을 내부 전달한다. 이름 선택 시 기존 자료와 연결하고 Company 변경은 전체 업무 화면을 새로 열어 이전 로컬 임시 상태를 남기지 않는다. W1 내부 Company 변경도 파일 선택·수동 전사·과제·입력값을 초기화한다. 새 Version 저장/재조회 뒤 URL을 실제 표시 Version과 맞춘다. 허용 목록과 맞지 않는 Company/맥락은 재선택 안내를 제공하며 API Scope/Version 검사를 대체하지 않는다. 과거 DB 이력은 삭제하지 않는다.

UUID 직접 조회는 접힌 고급 영역으로 이동했다. 정상 동선은 기업명/과제명/조합명/공고명/제안서 제목을 사용한다. 기존 고급 조회 회귀는 실제 summary 클릭만 추가했고 Assertion을 제거하지 않았다. 공통 Shell 외의 기존 모듈 로그인은 회귀 및 직접 진입 호환을 위해 유지하며, 정상 시작점은 /login이다.

현재 미검토 후보 건수는 Review가 없는 후보 수다. 승인요청 건수는 현재 ProposalVersion의 실제 OPEN 요청 수다. 기능/발행 건수는 실제 테이블 행이다. 정체불명의 작업 상태·완료율·AI 추천 결과를 생성하지 않는다.

## 실제 로그아웃과 최소 API 영향

기존 인증은 8시간 만료의 HttpOnly/SameSite strict Cookie와 local_sessions의 token_hash/expires_at을 사용한다. POST /notice/session/logout은 기존 trusted_origin을 검사하고 해당 token_hash의 세션만 현재 시각으로 만료시키며 LOGOUT Audit를 보존하고 동일 Path Cookie를 삭제한다. 다른 세션·과거 로그인·업무 이력을 삭제하지 않는다. 새 인증 방식/Schema/Role은 추가하지 않는다.

Web은 로그아웃 시작 즉시 자료를 숨기고, 서버 처리가 끝나면 /login으로 이동한다. 연결 실패를 로그아웃 성공으로 표시하지 않고 재시도한다. 다른 창에는 계정 변경/로그아웃 알림만 전송하며 Private 업무 값은 전송하지 않는다. 뒤로가기의 BFCache 화면은 다시 세션을 확인하도록 새로 로드한다. 같은 세션 재확인 때 메뉴를 익명 역할로 바꾸지 않는다.

추가 GET /workspace는 읽기 전용 Projection이다. E/O/P는 Membership과 기존 Company Projection으로 허용된 이름/건수/과제만 읽는다. O만 조합/매칭 목록, P는 현재 Version의 지정 요청이 있는 제안 요약만 받는다. A는 기업 이름/ID와 실제 기능/발행 수만 받고 기업 Private Detail·매칭·제안은 받지 않는다. 일반 E에 승인자 제안 메뉴를 주지 않는다. 실제 상세/저장 Action은 원래 각 Module Guard를 다시 통과한다.

## 준비 중 및 비목표

DATCO 자동 솔루션 추천·정부지원사업 자동 추천·진행현황/전주기 D~F·관리자 분석 작업/오류/감사 전용 화면·시스템 설정은 준비 중이다. 실제 기존 Catalog/Composer/Matching과 혼동하지 않는다. 새로운 AI/OCR/DMP 실연동/공고 조건 엔진/사업 State·권한·승인 정책/Phase2는 구현하지 않는다. 메뉴의 준비 중 표시는 해당 기능의 구현 완료나 API 승인 의미가 아니다.

## 검증 기록

초기 격리 W0 서버+기존 W1 API 회귀 15 PASS. W0 로그인/로그아웃/계정 변경·역할 홈/관리자 비상속과 기존 W1/Proposal 브라우저 5 PASS를 확인했다. 개발 중 같은 창의 계정 알림이 홈 이동을 취소하는 문제 및 역할 메뉴 일시 초기화를 수정했다. 마지막 전체 Backend/Integration/26개 Playwright 및 lint/build/API Type 실행은 완료 후 아래에 실제 결과를 기록한다. 이전 실행 결과로 최종 미실행 항목을 PASS 처리하지 않는다.

W0_USER_ACCEPTANCE=PENDING. W1_DATA_FACT_E2E의 기존 완료를 회귀 보호한다. W2_AUTO_RECOMMENDATION/W3_PROPOSAL_INTEGRATION=NOT_STARTED, PHASE1_FULL_E2E=NOT_COMPLETED, SYSTEM_ACCEPTANCE=NOT_TESTED. GitHub main Merge는 수행하지 않는다.


## Final verified results (W0)

- Backend: 310 PASS / 0 FAIL / 1 SKIP; PostgreSQL integration: 194 PASS / 0 FAIL / 1 SKIP (116 deselected). Isolation report: ce73ad4fd56e.
- Full Playwright: 25 PASS / 0 FAIL / 1 SKIP (26 cases); lint, production build and generated API type equality: PASS. Isolation report: 2f24f8cfbcb7.
- Backend optional stored-source test was skipped by its existing opt-in condition; actual stored Korean Notice browser regression passed. The existing separate unavailable-API browser case retained its conditional skip.
- Both final runners report public_changed_tables=[] and successful isolated cleanup. No migration, schema, Role, State or business Guard changes.
- Browser regressions cover W1 persistence/Fact review, Capability/Matching, Proposal approval and document output, scoped access, actual logout/expired-cookie rejection, account changes and mobile navigation.
- Existing child-server browser fixtures now route the common workspace request to their own real isolated API and drain pending requests before shutdown. Fact persistence checks await the actual save and reload responses and verify the saved version ID. Assertions were preserved.
- Common authentication remains visible when business-summary loading fails; late refresh results cannot restore private data during logout. Mobile navigation no longer expands the document beyond the viewport.
- Existing local W1 experience environment was updated in place, with its former web source backed up. Actual editor, approver, operator and administrator login/home/logout checks passed. Only an approver authentication account was added; no business completion or approvals were seeded. All 20 pre-existing business-table fingerprints and private-file fingerprints were preserved.
- Local experience URL: http://127.0.0.1:57386/login. Credentials and the W0 user guide remain private runtime files and are excluded from Git. Start/stop scripts operate only on the owned experience environment.
- W0_USER_ACCEPTANCE=PENDING; W1_DATA_FACT_E2E=PASS; W2_AUTO_RECOMMENDATION=NOT_STARTED; W3_PROPOSAL_INTEGRATION=NOT_STARTED; PHASE1_FULL_E2E=NOT_COMPLETED; SYSTEM_ACCEPTANCE=NOT_TESTED.
