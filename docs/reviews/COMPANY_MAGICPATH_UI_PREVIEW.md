# MagicPath v0.2 수요기업 포털 · 개발 전용 UI 미리보기

## 승인 범위와 원본
사용자가 승인한 화면 제작 전용 작업이다. 기존 제품의 인증·Role·API·DB·AI·Company·Capability·Matching·Proposal 코드와 FROZEN 계약은 변경하지 않는다. 이 결과는 제품 E2E 또는 사용자 인수가 아니다.

실제 참조: Repository 외부 DATCO_UI_reference_v0.2의 source/DATCOV02.tsx, UI_화면기능명세_v0.2.md, source/MagicPath_index_참고.css. 원본 TSX의 전체 JSX를 직접 사용했다. 원본 10개 Header, 19개 Card, 11개 Label, 10개 input 구문, 3개 select, 4개 textarea 구문을 보존했다. 배열로 생성되는 항목도 원본과 동일하다. 추가 요소는 화면 이동 도구의 nav/버튼 3개와 안내 텍스트다.

## 11개 화면
개발 전용 GET /ui-preview/company에서 원본 React를 독립 렌더링한다. 기존 Root Shell의 인증 조회나 실제 업무 API를 호출하지 않도록 HTML Route Handler로 제공하며 기존 Layout·로그인·기업 화면은 교체하지 않는다.

| ID | screen query | 화면 |
|---|---|---|
| L-01 | login 또는 생략 | 로그인 디자인 |
| C-01 | home | 수요기업 홈 |
| C-02 | onboarding | 서류로 가져오기 / 직접 입력 |
| C-03 | extraction | 추출정보 확인·수정 |
| C-04 | company | 기업·사업장 |
| C-05 | finance | 재무·정부사업 이력 |
| C-06 | needs | 개선요구 |
| C-07 | files | 첨부자료 관리 |
| C-08 | review | 분석 결과 예시 |
| C-09 | requests | 보완 요청함 |
| C-10 | proposals | 제안서 목록·상세·4개 탭 |

메뉴·홈·다음 화면·브라우저 뒤/앞 이동·새로고침을 URL과 동기화한다. 로그인 버튼은 계정을 검증하지 않고 홈 디자인으로 이동한다. 미리보기 로그아웃도 실제 인증 세션을 변경하지 않는다. 기업 선택 운영자 UI는 없다.

## 원본과 의도적인 차이
- 상단 개발 전용/예시/미연결 안내와 이전·홈·다음 이동 버튼을 추가했다.
- 원본의 시연 계정 검사와 하드코딩된 로그인 정보를 제거했다. 실제 계정을 입력하지 않도록 안내한다.
- 저장·분석 확인·보완 제출·제안서 승인/수정 요청은 미연결 안내만 표시하며 완료 상태를 만들지 않는다. 진행 완료율도 생성하지 않는다.
- 파일 선택/교체/제외/분류는 일시적 UI 메타데이터만 변경하며 파일 업로드·파싱을 실행하지 않는다. 후보는 예시 열기로 제공하며 선택·수정·적용도 화면 내 미리보기다.
- 분석 카드는 고정 예시다. 입력 문장을 AI/규칙 분석한 결과로 주장하지 않는다. 제안서·지원사업은 가상 예시다.
- 외부 Google 폰트 요청과 사용되지 않는 애니메이션 플러그인은 제외했다. 동일 브라우저의 시스템 폰트 폴백을 사용한다. Tailwind·Lucide는 원본 디자인 재현 전용 devDependency이며 기존 의존성 버전은 바꾸지 않았다.

## 개발 전용 차단과 검증
NODE_ENV=development에서만 HTML을 제공한다. Production에서는 쿼리나 입력과 무관하게 404다. 자산은 public에 배치하지 않고 개발 시에만 생성하며 connect-src none CSP로 UI의 네트워크 연결을 차단한다. 실제 사용자 인증/DB/API 서버는 시작하지 않는다.

재현 명령: apps/web에서 `node run-company-preview-tests.mjs`. 기존 소스/Next 생성파일을 변경하지 않는 소유 임시 Web 복사본과 별도 포트를 사용한다. 실행 환경의 API 주소는 연결 불가 loopback 주소로 고정한다. 소유 프로세스만 정리한다.

최종 로컬 검증: 0317e43d-2b1. Playwright 2 PASS / 0 FAIL / 0 SKIP. 11개 화면·전체 메뉴·후보 선택/수정/적용·파일 메타데이터·제안서 4탭/확인창·미연결 저장/분석/제출 안내·샘플 다운로드·브라우저 뒤/앞/새로고침·모바일을 검증했다. 업무 API 요청 0, 신규 Cookie 0. lint/typecheck/build 및 실제 production 404 검사 PASS. DB/API/Worker를 실행하지 않았다.

개발 전용 CI는 별도 company-ui-preview.yml이다. 기존 CI·업무 모듈은 수정하지 않는다. 실제 출력/화면·원본 비교 갤러리·시작/종료 방법은 Git 제외 Private Runtime의 company-visual-preview에 보관한다. 원본 화면은 JSX를 그대로 독립 렌더링하고 인증 대신 화면 이동만 계측하여 캡처했다.

UI_VISUAL_PREVIEW_COMPLETE: YES (기술 검증). BACKEND_INTEGRATION / AI_ANALYSIS / COMPANY_FULL_E2E: NOT_IN_SCOPE. USER_ACCEPTANCE: PENDING. 실제 기능 연결은 UI 승인 후 별도 명령으로 진행한다. main Merge는 수행하지 않는다.

원본 TSX SHA256: 2d74366067540b83355d906104123569d467b4f16b74b9f32d617981747db848

## v0.2.1 사용자 1차 검수 반영
사용자 요청에 따라 L-01 공통 로그인 문구/안내 박스, C-02 불필요 예시 버튼, C-04 복수 사업장, C-05 수행이력 3가지 선택 및 다건 입력, C-07 파일별 설명·사업장·현재 개선과제 연결 UI만 수정했다. 사업장에는 원본의 사업장명·소재지와 담당자 입력을 제공한다. 기업 기본 담당자는 기존 입력폼에 유지한다. 수행사업은 명칭·연도/기간·기관·수행내용·선택 증빙 메모를 직접 입력하며 제외할 수 있다. 없음과 미확인은 분리하고 선택을 바꾸어도 입력한 이력은 이번 세션에서 유지한다.

자료 설명은 다중 행이며 편집 접기/수정, 파일 교체 후에도 유지된다. 사업장 선택은 동일 미리보기의 사업장 목록을 사용한다. 입력은 컴포넌트 메모리에만 유지하므로 메뉴 이동에서는 보존되지만 브라우저 새로고침/탭 종료 후에는 초기화된다. DB·API·인증·AI·실제 업무 코드·FROZEN 기준문서 변경은 없다. C-01/03/06/08/09/10 JSX는 시작 Commit f774fab과 동일하다. 제거한 C-02 예시 버튼으로 진입하던 테스트만 직접 작성 경로로 바꾸었다. C-03의 빈 후보 초기 상태는 유지한다.

완료 판정은 UI_PREVIEW_REVISION_COMPLETE에 한정한다. BACKEND_INTEGRATION/AI_ANALYSIS는 범위 밖이며 USER_ACCEPTANCE는 사용자 승인 대기다.

최종 v0.2.1 검증: 격리 Runner 4a5d6e07-7fd. Playwright 3 PASS / 0 FAIL / 0 SKIP, lint/typecheck/build/production 404 PASS. 업무 API 요청 및 신규 Cookie 0. 기존 실제 업무 소스는 변경하지 않았으며 이번 실행은 업무 서버 전체 E2E 검증이 아니다.
