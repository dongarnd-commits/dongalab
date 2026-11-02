# PR #17 1차 사용자 E2E 보완·재인수 통합 보고

기준: 0048e49af8162aab7665c6ef7aab91c7ef51f2ca. 보완 개발 브랜치: fix/mvp-reacceptance-ux-rules.
공식 대상은 기존 Draft PR #17 / integrate/datco-one-mvp-v1 → main이다. main 병합 및 8443 배포는 범위 밖이다.

## 실제 원인과 보완

| 원인/관찰 | 변경 및 보존 |
|---|---|
| 같은 제출의 as_is/problem, goal/to_be 별칭을 각각 후보로 생성 | 동일 Version·역할·정규화 문장만 묶고 모든 원문 Evidence 보존. 파일·답변·Version의 독립 출처는 합치지 않음 |
| 목표의 업무 표현이 일반 문제 후보로 다시 분류 | 현황·명시 문제·목표·원인 설명·추론 기능을 역할별로 분리. 원문에 없는 원인/수치 생성 없음 |
| 필요한 기능 후보가 빈 상태 | 입출고 이력/재고/중복입력/연계/생산/품질/인사/회계/문서의 한정 표현 대응. 실제 제공 서비스·확정 요구와 구분 |
| 현재 회계 업무의 언급이 명시적 개선 대상 제외보다 우선 | 같은 제출 Version의 명시 제외를 기능 후보에도 반영. 현황 원문과 다른 Version 출처는 유지 |
| 목표 수치가 현재 측정값으로 인식되거나 이미 답변한 내용을 재질문 | typed 목표·원문 목표 구간과 현재 측정 구간 분리. 범위·기존 도구·별도 산정/미정 답변과 자료 한계 보존 |
| 분석 내용이 기술 상세 안에 숨고 동일 본문이 반복 | 기본 화면에 내용 요약·추론 표시. 위 제출 내용과 동일한 본문은 재출력하지 않고 상세 근거/이력은 모두 보존 |
| 운영자가 같은 구조화 내용을 반복 검토 | 명시 의견·클릭으로 미검토 STRUCTURE별 기존 Review 기록. 기존 제외/추가확인 판단은 덮어쓰지 않음 |
| 분석 검토에서 후속 구조화로 전사 필요 | 검토한 내용을 편집란으로 불러오기. 남은 확인사항도 유지. 저장·회사 ACK·공식 CONFIRM은 각각 별도 |
| 미해결 확인사항이 있는 저장본의 확정 버튼 활성 | 기존 Backend 거부 조건을 UI에도 표시. 해결/새 Version 저장·기업 확인 없이 Guard를 우회하지 않음 |
| PARTIAL Coverage에서 남은 범위가 없어도 저장 버튼 활성 | 기존 Backend 상태별 조건을 UI에 표시하고 저장 차단. 해결범위별 접근성 이름도 고정 |
| 파일 선택 표시·취소·높이/메뉴/로그아웃 불일치 | FileSelection과 PortalMenu를 세 포털에 재사용. 기존 업로드·추출·원본·Scope·Version 처리는 유지 |
| 기업 홈·사업장·재무·개선요구 사용성 | 기업별 조회 취소/시간 제한, 기존 사업장 등록 상태와 접힌 추가 입력, PC 재무 2열/모바일 1열, 필수/선택/단위 안내, 쉬운 개선요구 이름/짧은 제목/저장·제출 안내 |
| 관리자 미연결 컨트롤과 중복 권한 부여 혼란 | 실제 연결된 5개 메뉴와 업무 이동 사용. 이미 부여된 접근은 버튼 비활성/사유 표시. Backend 권한 정책은 유지 |
| Windows 시험 서버 조회의 일시적 ECONNRESET | 실제 실패한 GET 조회에만 제한된 transport 재시도. 저장·발송 POST의 자동 재시도는 추가하지 않음 |
| 인수 도구의 루트 CLI에서 API 모듈을 못 찾음 | 자식 환경 설정 이전의 API import 경로와 Git UTF-8 경로 디코딩을 보완. PYTHONPATH/UTF-8 모드가 없는 독립 subprocess와 실제 기존 계정 읽기 전용 검증 추가 |
| 실패 진단에 요청 헤더가 포함될 수 있음 | CI stdout/완료된 오류 문서에서 세션 헤더·시험 비밀번호 마스킹. 실패/상태/검증 근거는 보존 |

현재 Rule은 improvement-rules-v4이며 범용 LLM 의미분석이 아니다. R01~R08을 유지한다.
STRUCTURE content가 실제 인용에 포함되어야 한다는 기존 DB 제약을 완화하지 않았다.
기능 이름은 detail.function_label, 원문은 content, 도출은 derivation에 분리하고 대응표/원문을 Backend에서 재검증한다.

## 공통 계약·보안 보존

- 이번 증분의 DB Schema/Migration/Trigger 변경은 없다. 기존 fg31m0012026을 작업 소유 DB에서만 사용한다.
- 기존 Role/Company Scope, CompanyInput/Fact/Improvement Version, Evidence, 회사 ACK, 공식 CONFIRM, PROPOSABLE, Proposal Review/Approval을 보존한다.
- 분석 후보 검토, 보완요청 작성, 공식 확정과 기업 의사결정을 별개로 유지한다. 기존 요청·답변·승인 불변 Trigger는 변경하지 않는다.
- 기존 v3 Run/Review는 이력으로 보존한다. 새 업무의 현재성 검사는 기존 Rule/입력/Review/Version 검증을 사용한다.
- GPT/GEMINI/CLAUDE/GROK은 NOT_CONFIGURED다. 외부 AI·유료 API·실제 기업자료 전송을 수행하지 않는다.
- main/기존 8443/공유 DB/Worker/Caddy/TLS/방화벽/실제 계정·원본은 변경 대상이 아니다.

## 실제 자동검증

| 검증 | 실행 결과/근거 |
|---|---|
| 전체 Backend Unit | 295 PASS / private runtime reacceptance-unit.xml |
| Rule·사용자 재현·기존 추천 평가 | 105 PASS, 기존 서비스 추천 Gold 23개 기대값 유지 |
| 전체 격리 PostgreSQL | 292 PASS / 기존 실제 원문 opt-in 1 SKIP / ci/96d1a7114624/integration.xml |
| 새 빈 데이터 UI 시나리오 | 3 PASS / ci/ffce0c929383/browser-results |
| 기업 업무 집중 재검증 | 3 PASS / slice2/business-ux-e2e.log |
| 기존 전체 Playwright | 63 PASS / slice2/e2e.log (17.7분) |
| Frontend | lint·TypeScript·Production Build·API 타입 일치 PASS, 기존 검토 명령 Unit 9 PASS |
| 세 포털 Preview | 세 파이프라인 PASS. Company 5 / Operator 11 / Admin 20 시나리오는 중복 포함. 운영 빌드 Preview 404 검증 유지 |
| GitHub | 이 보완 커밋을 Push한 뒤 필수 CI 4개와 Preview 3개의 정확 HEAD 성공 확인 필요 |

새 UI 전체 시나리오는 회사/분석/서비스/제안 결과 0건에서 시작한다. 준비 도구는 계정, 명확히 TEST인 원천 기능 2개, 합성 파일과 미분석 DEMO 공고만 만든다.
기업등록·OCR 정정·2023/2024 PDF 확인/저장·개선요구 제출·관리자 Scope/서비스 발행·운영자 Fact/Rule 검토·요청 취소/발송·기업 답변·확인/재분석·공식 구조화/회사 ACK/CONFIRM·단독/복합 구성·공고 Worker/요건 검토·Match 검토·16절 제안·DOCX/PDF 실제 다운로드/digest·전달 취소/중복 방지·기업 수정요청을 실제 UI로 진행한다.
업무 성공 상태를 API로 사전 주입한 기존 회귀와 구분하며, 조회 API는 검증/ID 확인에만 사용한다.
이 자동 통과는 사용자 최종 인수 완료를 의미하지 않는다.

초기 회귀에서는 변경 전 문구/메뉴/사업장 입력 방식의 선택자와 기본 화면 중복 표시, 비동기 저장 대기, Windows 조회 연결 오류를 확인했다.
본문·상태·Scope·Version·원본·발송 건수의 기존 기대값은 삭제하지 않았다. 변경된 업무 조작을 명시하고 실제 저장 응답/다음 단계 Guard도 추가로 확인한다.
이전 실패 증빙은 private runtime에 보존하며 요청 인증값은 마스킹한다.

## 기존 사용자 인수 보존·복구

원래 8444 환경은 개발·검증 중 유지한다. 원래 소유 DB/볼륨/파일/계정/업무 이력은 초기화하거나 삭제하지 않는다.
초기 백업은 원래 Worktree의 storage/private/runtime/reacceptance-backups/20261030T080043Z다.
logical dump를 별도 소유 restore DB에 실제 복원하여 85개 테이블 전체 행 일치와 원본 파일 digest를 확인했다.
최종 전환 직전 앱 중지 후 마지막 백업/복원 확인을 다시 수행해야 하며 해당 경로는 보호 RUNBOOK에 기록한다.

복구 소스는 별도 detached Worktree dongalab-mvp-uat-recovery의 원래 HEAD 0048e49다.
원래 6개 로컬 운영 도구와 기존 운영 빌드 파일 422개의 일치를 확인하고 별도 포트에서 로그인 화면 200을 확인했다.
복구용 Backend/Worker는 실행하지 않았다. 최종 중지 snapshot의 보호 runtime을 복구 경로에 연결하고 배포 경로만 조정한다.
원복은 새 환경 STOP → 8444 비점유 확인 → 원래 HEAD/DB/파일/CA/계정/실행 도구의 복구 경로 START 순이다.
기존 공유 8443 또는 공유 DB를 원복 대상으로 사용하지 않는다. 코드만 되돌리는 것을 DB 복원이라고 표시하지 않는다.

## 새 인수환경과 사용자 시작

주소는 https://10.10.10.145:8444/login, 네 합성 계정명/비밀번호는 기존 보호 CREDENTIALS.txt와 동일하게 유지한다.
새 DB/Role/파일 저장소/포트를 만들고 기존 회사/분석/검토/승인/서비스/제안 결과는 복제하지 않는다.
계정은 소유 레이블·동일 Git common repository·loopback DB·실제 역할/비밀번호를 읽기 전용으로 검증하여 새 해시로 적용한다.
기존 시험 CA/인증서만 재사용하고 새 namespace 쿠키로 이전 인수 세션과 공유 8443 쿠키를 분리한다.

수동 인수에는 승인된 실제 649개 원천 기능을 digest 검증하여 준비한다. 합성 서비스는 관리자 UI에서 직접 작성·검토·발행해야 한다.
기본 입력은 제조기업의 창고/재고 업무다. 별도 물류 서비스업 입력은 제조기업 대상 DEMO 공고의 부적합/미확인 예외를 시험한다.
업종을 바꿔 자격을 통과시키거나 실제 사업이 접수 가능하다고 표시하지 않는다.

순서: 기존 자격으로 재로그인 → 새 기업등록/원본 정정·저장 → 관리자 접근권한/합성 서비스 발행 → 기업 재무/개선요구 제출 →
운영자 근거/분석/필요 보완/공식 구조화 → 회사 확인 → 운영자 확정 → 서비스 조합/공고·매칭 검토 →
16절 제안서 DOCX/PDF·기업 전달 → 기업 조회/수정요청.
현재 runtime/입력 자료/증빙·결과물 위치, 안전 STOP/START, 마지막 백업 및 실제 실행 SHA는 기존 보호 RUNBOOK에서 한 번에 안내한다.
기존 CREDENTIALS.txt 자체는 변경하지 않는다. 비밀번호/해시/토큰은 Git·PR·로그·이 보고에 포함하지 않는다.

## 최종 전환·판정 조건

기존 전체 회귀와 정확 PR HEAD의 필수 GitHub CI/Preview가 모두 통과하기 전에는 8444를 교체하지 않는다.
새 환경은 별도 포트에서 먼저 검증하고 STOP 상태에서만 자체 8444로 재바인딩한다. 기존 8444 승인 규칙/동일 Caddy 실행 파일을 유지한다.
기존 Worktree 로컬 도구와 사용자 파일은 백업/일치 확인 후 보존하여 통합 브랜치에 반영한다. Reset/Stash/Clean/Force는 사용하지 않는다.
최종 실제 CI와 runtime 확인이 끝난 뒤에만 RE_ACCEPTANCE_READY다. PR은 Draft이며 사용자/GPT 인수는 별도다.

## 남는 한계

Rule의 표현 대응과 OCR에는 한계가 있으며 원문 정정·범위·추론·미확정 조건은 사람이 검토한다.
원천 기능 649개는 실제 서비스 공급/가격/일정 확약이 아니다. DEMO 공고·검토한 요건과 실제 신청자격도 구분한다.
외부 AI 승인·연결, 다중 공고 수집 확장, 정식 배포/공유 DB Migration, main Merge 및 이후 사업 주기 기능은 수행하지 않는다.
자체 시험 CA 경고는 이 시험 주소에 한정해 확인하며 시스템/브라우저 전체 보안 설정을 변경하지 않는다.

## 실제 변경 파일

- .github/workflows/datco-ci.yml
- apps/api/app/company/improvement_language.py
- apps/api/app/company/improvement_providers.py
- apps/api/app/company/improvement_rules.py
- apps/api/app/company/improvement_structure.py
- apps/api/tests/ci_run.py
- apps/api/tests/fresh_browser_server.py
- apps/api/tests/manual_acceptance.py
- apps/api/tests/manual_acceptance_lan.ps1
- apps/api/tests/manual_acceptance_seed.py
- apps/api/tests/manual_acceptance_server.py
- apps/api/tests/mvp_portal_setup.py
- apps/api/tests/reacceptance_setup.py
- apps/api/tests/test_manual_acceptance_tools.py
- apps/api/tests/test_reacceptance_rules.py
- apps/web/src/portal/admin-live.tsx
- apps/web/src/portal/admin.tsx
- apps/web/src/portal/company-business.tsx
- apps/web/src/portal/company-documents.tsx
- apps/web/src/portal/company-finance.tsx
- apps/web/src/portal/company-home-summary.tsx
- apps/web/src/portal/company-improvements.tsx
- apps/web/src/portal/company-registration.tsx
- apps/web/src/portal/file-selection.css
- apps/web/src/portal/file-selection.tsx
- apps/web/src/portal/improvement-analysis.tsx
- apps/web/src/portal/operator-intake.tsx
- apps/web/src/portal/operator-mvp.tsx
- apps/web/src/portal/operator-worklists.tsx
- apps/web/src/portal/portal-menu.css
- apps/web/src/portal/portal-menu.tsx
- apps/web/src/ui-preview/admin/AdminControlCenter.tsx
- apps/web/src/ui-preview/company/DATCOV02.tsx
- apps/web/tests/admin-visual-preview.spec.ts
- apps/web/tests/business-ux.spec.ts
- apps/web/tests/mvp-analysis-handoff.spec.ts
- apps/web/tests/mvp-portals.spec.ts
- apps/web/tests/portal-handoff.spec.ts
- apps/web/tests/portal-stability.spec.ts
- apps/web/tests/reacceptance-full-ui.spec.ts
- apps/web/tests/role-portals.spec.ts
- docs/11_DECISION_LOG.md
- docs/mvp/IMPLEMENTATION_CONTRACT.md
- docs/mvp/MANUAL_ACCEPTANCE_ENVIRONMENT.md
- docs/mvp/REACCEPTANCE_REPORT.md
- docs/mvp/RULE_EVALUATION.md
