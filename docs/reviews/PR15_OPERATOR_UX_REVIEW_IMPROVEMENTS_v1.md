# PR #15 운영자 접수·검토 UX 보완

## 범위와 기준
기준 HEAD: defc4ad25ca57ef9041de75d7356f98cf496a6d3.
기준문서: 00_PROJECT_BASELINE, 01_SYSTEM_ARCHITECTURE, 02_E2E_SYSTEM_FLOW, 07_INTELLIGENCE_DESIGN, OPERATOR_BACKEND_REUSE_AUDIT_v1.
이번 변경은 프론트엔드 UX와 관련 격리 테스트다. Backend, Schema, Migration 파일, Role/Permission/State, Assignment, 분석·추천·매칭 엔진은 변경하지 않는다.

## 수정 전후
| 영역 | 수정 전 | 수정 후 |
| --- | --- | --- |
| 대시보드 | 큰 집계 카드 3개·세로 접수 카드 | 한 줄 업무 요약·접수 표·현재 불러온 목록 검색 |
| 검토 진입 | 기업 통합 업무로 이동해 기업정보부터 탐색 | 정확한 SUBMIT Version의 개선요구 검토로 직접 이동 |
| 기업 통합 업무 | 기업정보·재무·이력 후 개선요구 | 개선요구 요약·목록 우선, 기업·사업장·재무·이력은 접어서 상세 확인 |
| 재무 | 연도별 모든 항목을 세로 반복 | 항목 행 × 원래 기록별 열. 기간·단위·통화를 열에 명시 |
| 수행이력 | 긴 설명·증빙 반복 | 사업명·기관·기간 표, 상세·증빙 펼치기 |
| 원본자료 | 세로 파일 카드 반복 | 접힌 기업 공통자료 표. 제출 당시 첨부자료와 분리 |
| 보완 요청 | 기업 대상으로만 생성 | 선택한 제출 Version을 기존 improvement_version_id로 명시 |
| 재로그인 | 역할 홈으로 이동 | 같은 운영자의 허용된 내부 경로·Context만 복원 |

## 업무 동선
접수목록 → 제출 내용 검토 → 정확한 제출본의 As-Is/To-Be/제약/당시 사업장/첨부 검토 → 필요 시 기업 통합 업무에서 재무·기업 공통자료 확인 → 선택 제출본 보완자료 요청.

새 DRAFT는 접수목록에 포함하지 않는다. 개선요구별 최근 제출본을 목록에 표시하고 과거 제출본은 기존 제출 기록 선택으로 조회한다.
현재 Root 상태를 표시하며 새로운 미처리 상태나 업무 건수를 만들지 않는다.
선택 기업·제출 Version Context는 기존 URL과 서버 Scope 검사로 유지한다.

## 재무·자료 보존
금액은 Number로 바꾸지 않고 문자열 정밀도를 유지한다. 합산·환산·연도 보간을 하지 않는다.
서로 다른 기간·단위의 기록은 같은 연도라도 별도 열로 표시한다.
누락값은 등록되지 않음으로 표시하며 0으로 만들지 않는다.
기업에 등록된 파일과 정확한 제출 Version의 Evidence가 연결한 첨부파일을 구분한다.

## 보완 요청 및 인증
기존 관리자/운영자 Role 계약을 바꾸지 않는다.
기존 보완 요청 UI는 선택 기업에 속한 Version을 확인하고 improvement_version_id를 기존 API로 전달한다.
운영자 화면은 정확한 Context 로딩이 확인된 뒤 요청 패널을 표시하며 기업·Version별로 다시 마운트한다.
Backend의 기업/Version 관계 검사·send/respond/review Guard와 감사 기록은 그대로 사용한다.
공통 로그인과 포털 세션 화면은 동일 운영자·동일 Origin·정확한 운영자 경로·context_actor 일치일 때만 복귀한다.
기업/Version 선택이 없는 세션과 다른 역할의 기본 로그인 이동은 유지한다.

## 검증 환경과 한계
실사용 DB/PDF를 테스트에 복사하지 않고, 기존 CI 격리 러너의 임시 DB·합성 자료와 별도 루프백 production 서버에서 검증한다.
현재 실사용 웹 빌드·Caddy·방화벽 설정은 변경하거나 재시작하지 않는다.
120개 합성 기업 접수목록 검증은 UI 표시·검색·모바일 너비 검사이며 실제 Backend 100기업 부하 성능 PASS를 의미하지 않는다.
서버 검색·필터·페이지 조회·집계 최적화, 분석·추천·매칭·제안서 연결은 후속 Slice다.
실사용 서비스에 새 빌드 적용 및 사용자 직접 검수는 별도 단계다.
Commit/Push/Merge/Draft 변경 없음.

## 실행 검증 결과
- 격리 Backend 회귀: 25 passed (test_operator_intake, test_company_workflow, test_portal_context).
- 별도 production build 후 수요기업/운영자/관리자/세션 안정성 E2E: 15 passed.
- 모바일 메뉴 닫힘·캡처를 보완한 운영자 추가 production E2E: 2 passed.
- 전체 Frontend lint: PASS. TypeScript noEmit: PASS. production build: PASS.
- 과거 제출본·원본 digest, 새 DRAFT 제외, 정확한 제출 Version 이동, F5·동일 계정 재로그인 복원, 보완 요청 Version 연결 및 타기업 Version 거부를 검증했다.
- 재무 긴 정수·소수 정밀도와 0.000000, 같은 연도/다른 기간·단위의 별도 열을 검증했다.
- 120개 합성 기업 목록의 표시·검색 및 모바일 페이지 overflow 검사를 통과했다. Backend 부하 시험은 미실행이다.
- 초기 개발모드 검증은 실패 기록이 있다. 선택 없는 운영자의 로그인 복귀 동선은 보정했고, 재로그인은 POST 응답과 실제 이동을 기다리도록 검증을 강화했다. 개발모드의 ECONNRESET 원인은 미확정이며 최종 production 회귀에서는 재현되지 않았다.
- 기존 Alembic 순환 FK 관련 경고는 남아 있으나 격리 DB migration check는 새 변경 없음으로 통과했다. 제품 Migration 파일은 변경하지 않았다.
- 실사용 기업 읽기 전용 확인: PDF 6건, SUBMIT 1건, 보완 요청 0건. 실사용 DB에 테스트 요청을 발송하지 않았다.
- 현재 내부망 서비스는 기존 빌드·포트·루프백 경계를 유지한다. 새 UX를 실사용 서비스에 적용하지 않았다.
- USER_ACCEPTANCE: PENDING. Commit/Push/Merge/Draft 변경 없음.

검증 로그·합성 화면 캡처는 Git 제외 Private runtime의 pr15-operator-ux-review, pr15-operator-ux-review2/3/4에 보존했다.
최종 화면은 review4의 operator-slice1-submitted-snapshot.png, operator-workspace-financial-comparison.png, operator-improvement-mobile.png, operator-120-receipts-desktop/mobile.png에서 확인한다.

## 2026-10-28 최종 소규모 UX 보완 (기준 a0b2286)

기존 구현·검증 기록은 위에 보존한다. 이번 추가 변경은 Slice 1의 화면·사용성 및 관련 회귀에 한정하며 Backend·Schema·Migration·권한·업무 State는 변경하지 않는다. 실사용 HTTPS 빌드에는 배포하거나 재시작하지 않는다.

### 화면 변경
- 대시보드: 기존 집계·접수 표·검색·정확한 SUBMIT 이동을 유지하고 하단 다음 업무 안내를 제거했다.
- 기업 통합 업무: 자기 이동·선택 제출본 중복 버튼을 없애고 선택 제출본 검토 버튼을 한 곳으로 정리했다. 다른 개선요구 선택은 목록에서 유지한다. As-Is와 To-Be의 원문을 줄임 표시하고 상세에서 전체 내용을 보존한다.
- 개선요구 검토·보완 요청: 현재 화면으로의 자기 이동을 제거했다. 제출본 v번호·제출일시를 우선 표시하고 UUID는 기술 상세정보로 접었다. API와 URL은 정확한 원본 ID를 계속 사용한다.
- 재무: 원본 배열을 바꾸지 않고 연도 내림차순으로 표시한다. 동일 연도는 원본 순서를 유지하며 기간·단위별 열을 합치지 않는다. 긴 정수·소수·후행 0·기간·단위·통화를 유지한다.
- 기업 공통자료: 파일 ID·digest·다운로드를 유지하고 행 간격과 현재/교체/취소 상태 표시를 정리했다. 일반 파일 목록의 확정 문서유형·기준연도를 추정하지 않고 기존 순서를 유지했다. 파일명이나 미확정 추출 후보로 문서 분류를 확정하지 않는다.
- 요청 이력 없음 문구는 운영자에만 보완 요청 이력이 없습니다로 변경했다. 수요기업 안내는 유지한다.

### 발송 확인과 안전한 오류 처리
네이티브 dialog에서 대상 기업·개선요구·제출본·요청 제목·내용·기한을 최종 확인한다. 발송 취소·Escape는 쓰기 없이 닫고 포커스를 복귀시킨다. 최종 발송 전에는 생성·발송 POST를 호출하지 않는다.
기존 workflow 잠금과 추가 전송 ref로 중복 클릭을 차단한다. 기업·계정·Version이 바뀌면 이전 확인은 무효이며, 비동기 후속 발송도 Context를 다시 확인한다.
결과가 불확실하면 자동 재생성·재발송하지 않는다. ID를 확인한 초안은 상태 조회 후 같은 ID로 발송할 수 있고 이미 발송된 요청은 재생성하지 않는다. 생성 응답이 유실되어 ID를 모르면 이력 확인을 안내하고 현재 화면의 새 생성을 차단한다.
이는 프론트엔드 클릭·실행 보호이며 새 Backend idempotency 계약이나 전역 exactly-once 보장은 추가하지 않았다. 기존 401/403/404 오류는 원래 workflow Guard로 전달한다.

### 회귀 근거
합성 자료·임시 PostgreSQL·별도 Production Web만 사용했다. 실제 기업자료를 테스트에 복사하거나 실제 보완 요청을 발송하지 않았다.
기존 operator-intake 검증에 합성 PDF 6건, As-Is/To-Be, 자기 이동 제거, UUID 접기, 연도 내림차순과 동일 연도 안정 정렬, 확인 전 POST 0건, 취소·Escape·포커스, 중복 클릭, 생성 응답 유실, 발송 실패 후 같은 초안 상태 확인, Context 변경 차단을 추가했다. 기존 PDF 다운로드 SHA-256·과거 Version·권한·세션 검증은 제거하지 않았다.
business-ux는 발송 전 확인 절차를 실제로 거치며 기업 응답·운영자 확인 흐름을 유지한다. portal-handoff는 현재 선택한 제출본 Context를 검증하고 단일 검토 버튼으로 이동한다.
초기 격리 빌드는 Windows Turbopack 캐시 파일 공유 잠금(OS error 32)으로 실패했다. 설치된 Next.js가 지원하는 캐시 비활성화 옵션을 격리 검증 복사본에만 적용했으며 제품 설정은 변경하지 않았다.
초기 전체 회귀에서는 제거한 중복 상세 버튼을 기다리는 기존 인계 테스트가 타임아웃되어, 기업·Version 검증을 강화한 실제 동선으로 수정했다. 실패 기록은 Private runtime에 보존했다.

### 최종 로컬 검증 결과
- 관련 Production E2E: 15 PASS.
- 최종 전체 Production E2E: 49 PASS / 0 FAIL / 0 SKIP (최종 실행 7.9분).
- Backend Unit: 108 PASS.
- PostgreSQL Integration: 220 PASS / 기존 Live opt-in 1 SKIP. 신규 skip 없음.
- Frontend production build·lint·typecheck 통과를 확인한다. 최종 로그는 Private runtime의 pr15-final-ux-full3/review.log에 보존한다.
- 새 확인 창은 발송 전·취소 후 POST 0건, Escape·포커스 복귀, 중복 클릭의 단일 생성, 생성 응답 유실 시 재생성 차단을 검증했다.
- 발송 실패 후 확인 창을 취소해도 기존 초안 ID를 보존하며, 상태 조회 후 같은 ID로 발송을 이어가는 것을 검증했다.
- Context 변경 시 이전 확인 창을 무효화하고 타기업·타Version 연결 거부, 기존 응답·검토·F5·재로그인·역할 격리를 유지했다.
- GitHub CI는 이 보고서가 포함된 Commit의 Actions 결과를 확인한다. 최종 Run URL은 완료 보고에 기재한다.
- 파일 유형·연도 자동 분류, 서버 전체 검색·필터·페이지 조회, 분석·추천·매칭 및 후속 제안서 연결은 추가하지 않았다.
- 실사용 HTTPS에는 이번 최종 UX를 자동 배포·재시작하지 않는다. 사용자·GPT 최종 검토 및 별도 적용 승인 대기다.
