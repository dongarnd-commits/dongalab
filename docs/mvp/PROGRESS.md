# 진행 체크포인트

## 2026-10-30 P0/P1/P2 통합 준비

- 출발 main/origin main10d3d8b 일치, 기존 main·Feature·서비스 Worktree 보존.
- 통합 Worktree: C:/Users/PC/Desktop/정부지원사업운영체제 구축/dongalab-mvp-v1
- 통합 Branch: integrate/datco-one-mvp-v1 / 최초 계약 Commit 0d59084.
- Python uv --frozen 및 npm ci 완료. 승인된 649 기능 원천은 ignored _local_inputs에서 digest 확인 후 재사용.
- 원격 기존 PR15/16 MERGED 및 main CI40980317860 필수4개 PASS 확인. 이는 새 MVP 인수 결과가 아니다.
- root: Provider 경계(Rule만 실행), Rule v3, 검증답변 Manifest/Evidence, 제출v1→구조화v2 명시 계보, 비파괴 증분 Migration fg31m0012026, 기존 문서 범위 overlay 구현.
- root 집중 Rule 회귀: 47 PASS. 새 Migration/전체 PG·전체 E2E는 통합 후 실행 예정.
- solutions Agent: feat/mvp-solutions-proposals, 7dd6f99까지 실제 추천·Composition·16절 DOCX/PDF 및 집중 테스트 구현. 새 계보 테스트 후속 작성 중.
- portals Agent: feat/mvp-portals-admin, 4c5762e, 운영자6메뉴/Admin4영역·ACK/Fact 기존 Gate UI 및 신규 PG10 PASS, 타입/ESLint/3포털 번들 PASS. 새 MVP E2E는 통합 후 실행 예정.
- Git commit 뒤 자동 maintenance의 pack-refs 권한 경고가 있었으나 Commit/Worktree 생성 성공 확인. 이후 per-command maintenance.auto=false/gc.auto=0 사용, 기존 Git 권한/전역 설정 변경 없음.

상태 PARTIAL. 다음은 root checkpoint Commit→Feature 통합→타입 생성→격리 DB 집중검증→전체 회귀 및 실제 MVP 브라우저 동선 검증이다.
main Merge/HTTPS 배포/공유 DB 변경은 승인 범위가 아니다. 외부 AI4개 NOT_CONFIGURED는 정상 목표 상태다.

재개 시 실제 Branch/status/HEAD와 Agent Commit을 먼저 확인하고 완료 작업을 반복하지 않는다.

## P7 통합 검증 체크포인트

- 공통 구현 c3ca64d, solutions 3c77bfa/2fccd33, portals 4c5762e/c3e2d4b/7dc0f00/697865e가 통합 브랜치에 Merge됨. Feature/main 보존.
- 초기 전체 Backend Unit 210 PASS. 이후 추가 Gold/목표값 방어 포함 Rule 집중 58 PASS.
- 새 MVP 격리 PG27 PASS(d6c7b8653dba), Migration/alembic check·function config/기존 요청 불변성 보존·unsafe downgrade 거부 PASS.
- 첫 full PG는 Worker analyze 오류 주입 seam 누락으로 최초1건 실패 후 Queue 후속31 FAIL/259 PASS/1 SKIP. 기존 테스트를 변경하지 않고 RuleProvider 내부에 기존 analyze 의존성을 보존하는 수정 완료; 새 exactJob 테스트 보강 후 full 재검증 중. 실패를 최종 통과로 덮어쓰지 않는다.
- 첫 신규포털E2E 2PASS/1FAIL은 Match 저장안내 지연 수정 후 기존3개 모두PASS. 새 fresh handoff 추가 시 과도 status의 strict selector 실패1건 확인, 정확 실제문구/성공상태로 새 테스트 정밀화; 전체62개 E2E 재검증 중.
- Frontend lint/tsc/build, 기존 review-unit9, API 타입 일치 PASS.
- Admin/UI Preview 기존3포털20 PASS, 품질·타입·build 및 production preview404 PASS(654cab71-3d3).
- 공식 기업마당 현재 LIVE: GET1회/2건/totCnt1460 성공. 키 출력/복사/변경0, 고객자료 전송0. proof mvp-live/9195b24587134e4aa4c684ad12d49d65/result.json.
- 기존 main/dongalab Working Tree 미반영 변경0 확인. 기존 DB/HTTPS/Worker/Caddy 프로세스 변경0.
- 다음: 추천 고정Gold 과다/누락 보강 통합→전체 결과 확인/오류 수정→최종 회귀→ACCEPTANCE 실측 반영→Commit/명시Push/Draft PR→GitHub CI. 현재 PARTIAL.

## P7 최종 자동검증 중간 기록

- 최신 전체 Backend Unit246 PASS(mvp-unit.xml), 전체 격리 PG292 PASS / 기존 실제 공개원문 opt-in1 SKIP / Unit246 deselected(a89f824e7b85,630.15초), DB/Role/Container 정리 확인.
- 최신 추천 버전 published-solutions-v2: 고정23Gold 15/23→23/23, 복합·상위문구 근거위조 방어2개 PASS. Rule v3 업무별 질문/목표값 혼동/근거 검증 포함 집중58 PASS.
- 최신MVP PG29 PASS(523142efb06d): 동일기업 제출v1→Rule/USE→구조화v2/회사ACK/OPCONFIRM→실제원천입력 공고 HumanReview→Match PROPOSABLE→16절 문서/지정회사 전달/수정요청까지 하나의 실제Domain 계보 검증.
- 파일 추출 후보의 기업ACK 경로가 숨겨진 문제를 기존첨부관리 내CompanyCandidates fileOnly 재사용으로 연결. Role/State/API 정책 무변경. 이Fact를Rule와구조화에명시연결하는최신fresh브라우저 포함 MVP4개 모두PASS(1.6분).
- 첫전체Playwright62개는58PASS/4FAIL. (1) option disabled matcher 지원차이를실제DOM속성/키보드/직접API차단검증으로정밀화 (2) 신규공통결과요약과기존구조화접기CSS선택자중복분리 (3) 회사입력raw원문위치를사용자용문구로표시 (4) Admin신규패널과기존요약testid중복분리. 기존테스트삭제/완화0, 최종전체재실행예정.
- 격리Web dev와같은Worktree의Next production build 병행으로생성물경합1회발생(ENOTEMPTY/CI_SERVICE_TIMEOUT). 해당자기환경자동정리후순차실행으로빌드PASS+최신MVP4브라우저PASS. 기존서비스/DB에영향0. 앞으로같은Worktree의빌드와dev브라우저는순차실행.
- 최신lint/TypeScript/검토명령9PASS/Production build/API생성타입일치PASS. 기존3포털 Preview20PASS 및production404확인.
- read-only교차검토: 새Admin/Provider/CompanyACK/Fact/분석계보 경로에서중요Role/Scope/이력/외부전송위반발견없음(침투테스트나전체보안보장은아님).
- 추가발견1건: OperatorNotices 분석버튼version_id가Backend expected_version과달라422예상. 포털Agent가좁은수정및미분석공고부터시작하는실브라우저검증작성중. 이항목완료전최종READY선언안함.
- 기존Bizinfo키정확비교검사: 변경75파일에키포함0(키미출력/미저장). 실제고객자료외부AI전송0, 외부4종NOT_CONFIGURED는정상목표.
- 다음: GovUI payload/분석전원문 E2E 통합→최종전체 E2E→인수문서실측반영→통합명시Push/DraftPR→최신GitHub7Job확인. 현재PARTIAL.

## 최종 코드 동결

- root 통합 기능HEAD3102548까지, portals bf5fabb / solutions0d4d156 통합. Gov UI expected_version 필드 및생성API Body타입검증수정완료.
- 미분석Notice원문입력에서실제UI/Worker/사람요건검토까지신규브라우저5건모두PASS(1.7분). FileACK→Fact→Rule→구조화와MVP16전달/회사수정요청도포함.
- 최종소스Frontend lint/TypeScript/Production build PASS(FINAL_FRONTEND_QUALITY_PASS). 새소스동결, 허용된CI오류수정외추가개발없음.
- tests/ci_run.py에신규공고spec을focused/full모두등록. 다음은최종전체63브라우저회귀, 이후인수문서최종화/통합Push/DraftPR/최신CI. 현재전체확인전PARTIAL.
