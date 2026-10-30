# DATCO ONE MVP v1.0 개발 실행 계약

기준: 2026-10-30 사용자 전체 시스템 자율 개발 마스터 명령. 출발 main: 10d3d8b0f0142b0d6cbb992acb07bb34ed40c049(PR15/16 병합 및 CI PASS). 이번 지시는 변경 MVP 구현 범위의 사용자 명시 승인이다. 대표/조직의 별도 공식 승인이나 최종 사용자 인수 완료를 선언하지 않는다.

## 범위와 보존

기업 등록·자료 → 개선요구 제출 → Rule 분석·운영자 검토 → 부족정보 요청·응답 → 실제 DATCO 서비스 단독/복합 구성 → 실제 Notice 검토·3자 Matching → 항목별 PROPOSABLE 확인 → 표준 DOCX/PDF 제안서 검토·전달·기업 다운로드까지 구현한다. 기존 전주기 H01~H32는 미래 확장으로 보존하며 이번 완료조건으로 사용하지 않는다. 공식 신청·접수, 선정 후 운영/정산/사후관리, 실제 DMP 연동, 외부 AI 실행은 제외한다.

기존 3포털의 Shell·메뉴·카드·목록·Dialog·디자인을 유지한다. Editor 입력/응답, 지정 Approver 승인, Operator 업무 검토, Admin Catalog/Membership 관리 경계를 유지한다. 관리자에게 Operator 업무를 상속시키지 않는다. Company Scope·CONFIRM·ACKNOWLEDGE·PROPOSABLE·내용검토·승인/재승인·불변 파일/Version/Audit Guard를 완화하지 않는다.

## 한정적 실행 권한

사용자는 MVP 개발용 Branch/Worktree 생성, add/Commit/Push, 검증된 Feature의 통합 Branch 병합, 문서 동기화, 비파괴 추가형 Migration 코드와 작업 소유 격리 PostgreSQL 검증, 합성 테스트 및 통합 Draft PR을 승인했다. AGENTS의 Git 제한에 대한 이 범위만의 명시적 예외다. main에서 직접 개발하지 않는다.

main 병합, HTTPS 배포/재시작, 공유 DB Migration, 실제 기업자료/계정/승인/응답/증빙 변경, Role/State 정책 변경, 파괴 작업, force/reset/history rewrite, 외부 AI/OAuth/유료 호출/기업자료 전송은 별도 승인 대상이다. 기존 dongalab-main·dongalab·Private Runtime·검수 DB를 보존한다.

## 공통 계약 및 영향

| 계약 | 승인된 호환 증분 | 보존 |
|---|---|---|
| Provider | RULE/GPT/GEMINI/CLAUDE/GROK registry, RULE만 AVAILABLE | 외부4개 모두 NOT_CONFIGURED; 실제 Adapter/자격증명/네트워크 없음; Backend 직접 호출 거부 |
| 요청 | AnalysisRequest.provider 기본 RULE | MANUAL/ENSURE는 별도 실행 정책, 기존 호출/자동 진입 Rule 유지 |
| 상태 API | GET /company/analysis/providers | Operator 인증; Admin은 별도 안전 Projection에서 같은 registry 재사용 |
| 공통 결과 | Company/Version/Manifest·Provider Version·현황/문제/원인 후보/목표/기능/범위/부족정보/근거/품질 | 기존 Candidate/Evidence/Review 계보와 현재성; 자동 사실확정 없음 |
| 검토 답변 | 같은 기업·대상 Request의 제출 답변 중 DATCO VERIFIED Review를 입력에 고정 | 타기업/타제출본/미검토 제외; Fact 자동승격 없음; 변경 후 stale 판별 |
| Evidence | 필요 시 검토 답변의 명시적 계보 검증 분기 추가 | 기존 분기/제약 보존. 추가형 Migration은 root 소유, 격리 DB만 실행 |
| 추천 | GET /capability/improvements/{vid}/recommendations | 발행 Capability·실제 FeatureRevision·현재 분석/Review만; 검색≠적용성 확정 |
| 구성 | 기존 Composition data에 선택적 basis/integrations 및 요구별 Coverage 설명 | basis는 동일 Version의 현재 Run·USE_FOR_REQUEST Review; Legacy payload/불변 이력 유지 |
| 제안서 | template_version LEGACY_11(기존 기본)/MVP_16(새 UI), 불변 manifest 식별 | 과거11절/파일/승인 보존; 템플릿 전환은 새Version; 기존 Trigger 우선 유지 |
| 관리자 | /admin/overview, /admin/access, /admin/connections 읽기 Projection | Secret/해시 제외; 기존 ADMIN grant 사용; 신규계정/Role/삭제 정책 없음 |
| 공고 | 기존 GET /notice 유지, 별도 저장검색 Projection | LIVE/SNAPSHOT/저장조회 구분; 관련성≠자격; 공식 Requirement 사람확인 유지 |

공통 Schema/API/Domain 영향은 이 문서와 변경 Commit에 기록한다. 보존 조건을 바꿔야 하는 정책은 BLOCKED로 기록하고 독립 작업을 계속한다.

## 분석·추천·문서 원칙

Rule은 제한된 업무 표현/동의어·부정/제외·명시 수치/단위/기간·실제 카탈로그 근거를 사용한다. 범용 AI 의미분석이라고 표시하지 않는다. 원인은 후보·불확실성으로 표시한다. 미확인 숫자·예산·일정·성과·선정확률을 만들지 않는다.

검사 범위, 직접/공통/미선택/제외/미검사, Parse/digest/Parser를 보존한다. 미검사는 부재 증거가 아니다. 649 원천 기능을 그대로 최종 상품으로 추천하지 않는다. 발행 Capability와 원천 Revision으로 상위 솔루션을 표현하며 AI Agent를 이름만으로 제공 확정하지 않는다.

구성은 역할·연계·전제·해결/부분/미해결 요구와 출처를 제시한다. 없는 공고를 만들지 않는다. 동일 검토 ProposalVersion에서 DOCX/PDF를 생성한다. 자동 발송·자동 기업 승인 없음.

## 운영

통합 integrate/datco-one-mvp-v1 / 별도 dongalab-mvp-v1. root는 공통 계약·분석·문서·Migration·API 등록·생성 타입·CI·통합 담당. 개발 Agent2개는 별도 Feature Worktree에서 솔루션/제안 Backend와 포털/Admin/공고를 담당한다. 공유 파일 소유권을 지킨다.

EXECUTION_PLAN/PROGRESS/ACCEPTANCE에 재개 위치·근거를 기록한다. 과거 CI PASS는 출발점의 증거이며 새 MVP 완성이 아니다. 계획/구현/실행검증을 구분한다.
