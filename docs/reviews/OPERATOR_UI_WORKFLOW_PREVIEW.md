# DATCO 운영자 UI 업무 미리보기 v0.2

## 범위 및 기준

2026-10-19 사용자 실행명령에 따른 화면 전용 구현. main `5e99f517af2a2e5fc821e92adc5fc3deda8f9836` 기준.
사용자가 제공한 `DATCO_운영자_Codex_전달패키지_v0.1/source/OperatorPortal.tsx`, CSS, 가상 Fixture를 재사용한다.
첨부 패키지의 예전 로그인·실연동 지시보다 이번 사용자 명령의 UI 전용·빈 상태·명시적 예시 모드를 우선한다.
AGENTS, docs/00~11의 모듈·Version·Evidence·Human Review·권한 계약을 변경하지 않는다.

## 접근 및 데이터

개발 전용 `/ui-preview/operator`. 운영 `NODE_ENV`에서는 번들 생성 이전에 404.
계정·암호 검증 없이 미리보기 진입 버튼만 제공한다. 기존 인증·로그인·운영 화면은 그대로다.
기본 기업 0개. 명시적으로 기업 1개 또는 여러 기업 예시를 선택한다. 종료 시 빈 상태로 복귀한다.
가상 Fixture는 Git에 포함하나 실제 DB, 기업 제출내용, AI 실행 결과가 아니다. 외부 데이터 전송·API 요청이 없으며 CSP connect-src none을 적용한다.
기업별 사업장 2개와 각 사업장의 과제 2개를 시연 선택한다. 추가 사업장/과제는 원본 Fixture가 단일 맥락인 한계를 보완한 명시적 가상 예시다. 다른 맥락의 Fact/매칭/제안서를 승계하지 않는다.
요청·편집·검토 상태는 Company/Site/Improvement 선택 조합별 메모리에 보관된다. 새로고침 시 사라진다. 실제 권한 격리 검증은 아니다.

## 원본 보존과 변경

O-01~O-12 원본 메뉴·레이아웃·네이비/블루 CSS·카드·폼을 유지했다.
가상 계정 로그인 제거, 예시 모드 제어, 맥락 선택, O-04 제출자료 설명/사업장/과제 표시, O-09 세 축 비교, O-04/05/09 보완 요청 및 복귀 동선을 추가했다.
Fact 검토, 서비스 후보/조합 선택, 가상 공고 비교, 미확인·불일치 차단, 제안서 새 버전/내용검토/전달 로그는 화면 시뮬레이션이다. 서버 Guard·승인·전송의 구현 또는 검증이 아니다.
제안서 구성/정책을 새로 확정하지 않는다. 실제 Proposal 엔진은 호출하지 않는다.

## 후속 연동 경계

- Company/Site/Fact/Evidence/Improvement는 기존 Company API·Provider와 승인된 Company Scope/Projection을 재사용해야 한다.
- 기존 Capability/Composition/NoticeVersion/MatchReview를 사용하며 별도 수집·매칭 엔진을 만들지 않는다.
- 실제 ProposalVersion/ContentReview/Delivery/Approval은 기존 P-01~P-05 및 지정 승인자 계약을 사용한다.
- 기업 포털과 운영자 미리보기는 독립 메모리 데이터다. 실제 제출 전달이나 실시간 동기화가 없다.
- DMP SSO, AI, 실제 추천/매칭, 실제 기업 전송은 미연결이다.

## 검증

`node apps/web/run-operator-preview-tests.mjs`는 고유 runtime 그림자 폴더, 별도 Next 포트, API_ORIGIN 127.0.0.1:1을 사용한다. API/PostgreSQL/Worker는 시작하지 않는다.
운영자 6개 브라우저 시나리오와 기존 기업 미리보기 5개 회귀를 실행하고, O-01~12 및 모바일 스크린샷을 생성한다.
lint/typecheck/build와 두 미리보기의 운영 404를 확인한다. 결과는 ignored runtime report.json/log 및 GitHub Actions Artifact에서 확인한다.
최종 PASS/FAIL은 실행 결과 보고를 따른다. 사용자 인수, 실제 DB/API/AI 및 전체 업무 E2E는 이번 완료 범위가 아니다.



로컬 최종 실행: `98a17165-412` — Playwright 11 PASS (운영자 6 / 기존 기업 5), lint/typecheck/build PASS, 운영 미리보기 두 경로 모두 404. DB/API 시작 없음.
