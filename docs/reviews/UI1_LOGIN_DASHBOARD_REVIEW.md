# UI 1단계 로그인·역할별 업무 시작 화면 검수

## 승인 범위와 재사용
사용자의 UI 1단계 명령으로 W0 로그인·세션·Role/Membership·Shell·workspace 조회 API 및 W1/Capability/Matching/Proposal을 재사용한다. 로그인 UI, 역할별 홈과 업무 진입 동선만 개선한다. Schema/API/Auth 계약/Role/State/Permission 변경은 없다. docs/00·01·04·05·08·10 및 Decision-007과 정합성을 유지한다. 기존 동결 기준을 변경하지 않는다.

## 실제 변경
- 공통 로그인: 요청한 시스템명, 비밀번호 표시/숨김, 중복 제출 방지, 진행 상태, 비밀번호 오류/네트워크 오류 안내. 서버 인증 결과로 공통 홈에 이동하며 계정명으로 Role을 판단하지 않는다.
- 수요기업: 증빙자료 제출을 첫 업무로 배치. 실제 기업/사업장/Fact·자료·미검토 후보·개선과제 상태를 조회한다. 기업 미등록/미선택을 안내한다. 후보 건수를 자격확정·자료완비로 표현하지 않는다. Editor의 Proposal 미연결과 Approver의 지정 승인 요청을 구분한다.
- 운영자: 허용 기업 선택, Fact·Evidence, 개선요구, 기존 서비스 조합·매칭·제안서 진입. 현재 선택 기업으로 건수를 필터하고 Company/Site/Improvement 맥락을 유지한다.
- 관리자: 실제 기능 원천·발행 Capability·접근관계 관리. 공고 운영의 Operator 전용 권한과 통합 분석/감사 화면 미구현을 명시한다. 관리자에게 Operator/기업 승인 권한을 부여하지 않는다.
- 공유 스타일: 업무 시작 영역, 주요 버튼, 카드·상태 안내, 로그인·모바일 가독성 개선. 기존 공통 Header/Sidebar와 실제 로그아웃은 재사용한다.

## 검증 계획과 인수 구분
기존 격리 PostgreSQL/API/Web Runner에서 전체 Backend/Integration/Playwright 및 lint/build/API 타입을 검증한다. UI1 역할별 CASE-01~03에 실제 로그인·업무 연결·권한 거절·로그아웃을 추가하고 기존 W0의 타기업/다른계정/뒤로가기/영속성 검증을 유지한다. 실제 결과는 실행 후 기록한다. USER_ACCEPTANCE=PENDING. 신규 AI·자동 추천·Proposal 엔진·전주기 기능은 개발하지 않는다.


## 최종 실행 검증

- 전체 Backend: 310 PASS / 0 FAIL / 1 SKIP. 격리 실행 0b026218ded4.
- 전체 Playwright: 28 PASS / 0 FAIL / 1 SKIP (29개). 격리 실행 4ee7c9e36d64.
- 신규 역할별 CASE-01 기업 / CASE-02 운영자 / CASE-03 관리자: 각각 1 PASS / 0 FAIL / 0 SKIP.
- lint / production build / API 타입 비교: PASS. 기존 W0/W1·Capability·Matching·Proposal 회귀 포함.
- 최초 연관 브라우저 실행은 로그인 오류와 Next.js 내부 announcer의 중복 alert 선택으로 1건 실패했다. 로그인 본문으로 선택 범위를 한정한 뒤 위 전체 실행에서 통과했다. 오류 안내·권한 검증 Assertion은 유지했다.
- SKIP: 기존 별도 API 장애 조건부 브라우저 사례 및 opt-in 원문 Backend 사례. 실제 저장 한국어 공고 브라우저 검증은 PASS.
- 기존 체험 서버에서 세 역할 로그인→실제 홈→로그아웃→이전 Cookie API 401을 확인했다. 업무 데이터 20개 테이블은 기존 지문과 일치한다. UI 3개 파일 갱신 전 소스는 비공개 before-ui1-web-src에 보존했다. 업무·승인 상태를 Seed하거나 자동 확정하지 않았다.
- 체험 URL http://127.0.0.1:57386/login. 로그인 정보·사용자 안내서·4개 스크린샷은 기존 Private Runtime에만 보관하며 Git에서 제외한다. 기존 Stash·외부 백업을 보존한다.
- ROLE_LOGIN_GATE / COMPANY_HOME_GATE / OPERATOR_HOME_GATE / ADMIN_HOME_GATE / LOGOUT_GATE / ROLE_BROWSER_E2E: PASS. USER_ACCEPTANCE: PENDING. 전체 Phase 1 또는 외부 AI·자동 추천 완성을 주장하지 않는다.

- 최종 PostgreSQL Integration: 194 PASS / 0 FAIL / 1 SKIP / 116 deselected. Migration check PASS. 두 최종 Runner 모두 shared_write_privileges=[false,false,false], public_changed_tables=[], test_database_and_role_removed=true.
