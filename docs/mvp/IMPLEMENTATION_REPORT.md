# DATCO ONE MVP v1 개발 보고

2026-10-30. 기준 main10d3d8b(PR15/16 병합), 통합 integrate/datco-one-mvp-v1. 이번 개발 결과는 사용자 인수 전 Draft로 제출한다. 정확 최종 Commit/CI는 PR HEAD와 Checks를 원천으로 사용한다.

## 완성한 업무 연결

기존 3포털에서 기업·사업장·원본 파일·개선요구 제출 → Rule 후보·원문/처리범위·운영자 검토 → 보완요청/답변 → 실제 DATCO 서비스 단독/복합 구성 → 저장 공고/요건 검토 → 3자 Match/항목별 PROPOSABLE → MVP_16 제안 초안/별도 내용 검토 → 동일 Version DOCX/PDF → 지정 회사 전달/조회/다운로드/수정요청을 연결했다.
분석 입력 v1과 회사가 확인한 구조화 v2를 explicit analysis_basis로 구분한다. 회사 원문·Fact·요건·적합성·제안내용·회사 의사결정을 자동 확정하지 않는다.

## 기존 기능을 재사용한 범위

- Company/Profile/Site/InputVersion, Private Files/digest, Evidence/Parse/OCR, Candidate/회사ACK/Operator Fact 확인, 개선요구 State/Version/CONFIRM.
- Slice2 PostgreSQL Job/Attempt/Worker/Manifest/검사범위/Review/영속초안/원자적 InformationRequest 발송 및 요청·답변 불변 Trigger.
- 기존649 Feature/FeatureRevision Import·검색, Capability Draft/Publish, Composition/Coverage/Assessment, MatchInputSnapshot/비교/Review/PROPOSABLE.
- Bizinfo 공식 Collector/Raw/Normalize/Notice/NoticeVersion/원문 추출·요건 검토, 실패/재시도/Snapshot.
- ProposalVersion/내용Review/Approval/지정담당자 전달/회사Inbox/재승인 및 DOCX/PDF 렌더·digest.
- 기존 로그인/세션/Role/Company Scope, 3포털 Shell·사이드바·카드·폼·Native dialog, 격리 PostgreSQL·브라우저 하네스.

## 실제 변경 파일 그룹

| 영역 | 주요 파일 | 변경 |
|---|---|---|
| 공통분석/Rule | app/company/improvement_providers.py, improvement_language.py, improvement_rules.py | Rule만 실행하는 Provider 경계, 공통 결과, 업무분류·부정·답변·명시수치/기간 비교 |
| 입력/계보/Worker | improvement_analysis.py, improvement_worker.py, application.py, contracts.py | 검증답변 Manifest/RESPONSE근거, v1/v2명시basis·현재성, 기존 오류주입/rollback 검증 보존 |
| DB | infrastructure/improvement_constraints.py, alembic/versions/fg31m0012026_mvp_analysis_lineage.py | 비파괴 함수body/Version constraint trigger 증분, 새이력 있으면 downgrade 거부 |
| 솔루션 | capability/recommendations.py, capability/application.py, api/capability.py | 발행서비스·실제 기능 근거 추천, 좁은 동의어/제외·미해결, 역할·연계·Coverage |
| 공고/Admin | notice/catalog.py, operations/admin.py, api/admin.py, api/notice.py, main.py | 저장 검색/기간·원천·현재요건, whitelist 실제관리 Projection, 기존Role/권한 유지 |
| 제안서 | proposal/mvp_template.py, documents.py, application.py, api/proposal.py | LEGACY_11 보존/MVP_16 명시 버전, 실제기능·연계·근거16절·한글동일본문 출력 |
| 운영자UI | portal/operator-mvp.tsx, operator-notices.tsx, operator-proposals.tsx, improvement-analysis.tsx, operator-intake.tsx | 기존후속6메뉴, 현재/과거 정확입력, Rule/외부상태, 구조화·서비스·공고·매칭·전달 |
| 기업UI | company-improvements.tsx, company-business.tsx, company-documents.tsx, company-proposals.tsx | 기업ACK/파일후보 사실확인 접근경로, 원본보존, 정확 전달Version 16절 본문 |
| Admin/UI | admin-live.tsx, admin.tsx, ui-preview/admin 기존컴포넌트 | 실제4영역, 기존요약/미래미연결구분·유일선택자, 사용자/기업 기존grant |
| 테스트/CI | test_mvp_*.py, test_solution_*.py, mvp-*.spec.ts, mvp_portal_setup.py, ci_run.py, v14_migration_chain.py, datco-ci.yml | 기존테스트보존+신규Gold/계보/미분석공고/파일ACK/전체브라우저 |
| 문서/타입 | docs00/01/03/04/05/07/08/09/10/11, docs/mvp/*, generated/api.d.ts | 새MVP overlay/미래H01~H32보존, 계약/진행/인수/생성API타입 동기화 |

API/DB 상세 계약과 영향은 IMPLEMENTATION_CONTRACT.md, 고정 Rule/추천 품질 비교는 RULE_EVALUATION.md 및 SOLUTION_RULE_EVALUATION.md를 참조한다.

## 실제 검증과 수정

- 전체 Backend Unit246 PASS, 전체 격리PG292 PASS/기존1 SKIP, 최신MVP29 PASS. 한기업의 분석근거가 실제공고요건·Match·문서·기업의견까지 이어지는 연속 Domain 경로를 검증했다.
- Frontend lint/TypeScript/Production Build/API타입일치, 기존검토명령9 PASS. 기존3포털Preview20 PASS/운영미리보기404.
- 새fresh 파일ACK/Fact→분석/구조화, 미분석공고UI→Worker→Human Review, Admin/메뉴/실제제안전달 등5개 브라우저 PASS.
- 최종 전체 Playwright63 PASS/FAIL0/SKIP0(17.6분), 자기 격리환경 정리 확인. 정확 최신 원격 CI는 PR Checks를 원천으로 사용한다. 최초 실패와 수정 이력은 PROGRESS에 보존했다.
- 발견·해결: 기존Worker analyze 오류주입 지점 누락, 넓은HR분류 과다추천/부분제외 누락, Match 저장안내 지연, 신규/기존DOM선택자중복, raw기업입력descriptor 표시, 회사문서ACK UI접근누락, Notice 분석 Body 필드불일치.
- 알려진 환경 경합: 같은Worktree Next dev와production build 병행으로산출물충돌1회. 자기 격리환경정리후순차실행으로해결, 운영서비스영향0. 최종검증은순차실행했다.
- 읽기전용보안·계보교차검토에서 새중요 Role/Scope/불변이력/AI전송 위반을 발견하지 못했다. 이는 전체 침투테스트·무결성의 무조건 보장이 아니다.

## 외부 연결 및 실제 데이터

RULE AVAILABLE; GPT/GEMINI/CLAUDE/GROK 전부 NOT_CONFIGURED. 실제 AI/OAuth/키/자동과금/기업자료외부전송을 추가하지 않았다.
공식 기업마당 API 소량GET1회2건 LIVE 성공과 합성자료 업무검증을 구분했다. 전체 공고 수집/모든 첨부/장기 가동/실제 자격 성공으로 확대 해석하지 않는다.
승인된649원천은ignored local inputs에서digest 검증 후 재사용, 실제고객 원본은 Fixture로복사하지 않았다. 최종변경76파일에기존Bizinfo키포함0을확인했고키값을출력/저장하지않았다.

기존 dongalab-main(main10d3d8b), dongalab(6beb859), 기존 HTTPS/Frontend/Backend/Worker/Caddy/DB/첨부/계정/Membership을 변경하지 않았다. 실제 DB Migration/재배포/main Merge는 수행하지 않았다.

## 남은 사용자 인수·별도 결정

전체자동검증·CI가 완료되어도 사용자 인수 및 조직 공식 승인은 별도다. USER_ACCEPTANCE_GUIDE.md로 정상·예외를 한 번에 검토한다.
실제 상위서비스의 제공범위와 Feature 연결은 사업 담당자가 발행·검토해야 한다. 규칙이 자동 제공확정하지 않는다. 비용/일정/인과/통합 실현성/지원자격의 실제판단은 사람의 책임이다.
외부AI 자격/전송/비용/보존정책, main Merge, 공유DB 백업·복원·Migration, HTTPS 적용은 다음 별도승인이다. H01~H32 전주기·공식신청/정산·실DMP·멀티AI 실제연동은 이번 완료범위가 아니다.
