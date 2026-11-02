# 지속 실행 수동 인수환경

> PR18 현재 작업은 아래 **별도 loopback 준비 모드**를 사용한다. 나머지 PR17/8444 전환 절은 이전 합성 LAN 인수의 보존 기록이며 이번 서비스 전환 지시가 아니다. 사용자용 인수 절차는 USER_ACCEPTANCE_GUIDE.md 하나를 따른다.

## PR18 별도 loopback 준비 모드

initial/resumed preflight는 실제자료 입력 전의 빈 환경·알려진 TEST sentinel만 확인한다. 실제자료가 들어간 뒤 다시 실행하거나 화면을 자동 캡처하지 않는다. 추가 기업/파일·업무 결과가 있으면 준비 probe를 차단한다.

- manual_acceptance.py create에 --preparation --host 127.0.0.1 --https-port <비점유 새 포트>를 명시한다.8443/8444 및 보호 서비스 포트는 거부한다. 기존 확인된 Caddy 실행 파일을 읽기/실행 재사용하며 기존 설정·CA·프로세스는 편집하지 않는다.
- 기존 레이블/nonce/DB Role/볼륨/파일/쿠키 분리 및 안전 STOP/START를 재사용한다. 정확한 승인 해시의 원본649개를 import하고 --no-notice-fixture로 합성 공고도 만들지 않는다. 기업별 분석·검토·추천·제안 결과를 seed하지 않는다.
- 새 준비 환경은 커밋된 내용이어야 한다. 현재 HEAD와 tracked staged/unstaged 내용 및 미추적 소스가 다르면 거부한다. Next 자동 생성 파일의 동등한 줄바꿈/stat 차이는 실제 내용 비교로 구분한다.
- 환경 준비 뒤 manual_acceptance_preflight.py --nonce <nonce> --phase initial로 API/DB/Worker/files/head와 비민감 sentinel을 검증한다. STOP→START 후 --phase resumed로 같은 자료 digest를 확인한다. 브라우저4역할 로그인/F5/로그아웃과 접근/다운로드 차단·세션 namespace·production404도 자동 확인한다. 실제 승인자는 기존 '/'로 진입하며 Operator 업무를 상속하지 않는다.
- API access log는 준비 모드에서 끈다. Node 브라우저 실패는 고정 오류문구만 출력한다. 비밀번호·쿠키·sentinel 로그/Git 검사와 최종 proof는 브라우저 성공 후 기록한다. 기존 Proxy/Live/AI 키를 자식에 상속하지 않으며 제품 외부 AI4종 미설정을 확인한다. 시스템 전역 네트워크 차단을 추가한 것은 아니다.
- 실제 생성 주소·실행 SHA·공개 TLS CA/fingerprint·자격 안내·START/STATUS/STOP은 해당 보호 RUNBOOK에 기록한다. 자격은 CREDENTIALS.txt에서만 로컬 확인한다. 별도의 실제 사용자 계정·자료 권한은 보류하고 TEST4역할로 환경을 확인한다.
- 새 방화벽/인증서 전역 신뢰 등록·기존8443/8444 전환·기존 DB/계정/볼륨/백업 변경을 하지 않는다. 실제자료 입력·보존·삭제/백업·개별 접근자 승인안은 DMP_ASSET_AUTO_COMPOSITION.md에 모았다.
- 공고0은 의도된 준비 상태다. 실제 공식 공고·자격 근거가 없으면 매칭/정식 제안 인수를 보류하며 DEMO로 대체하지 않는다. 실제자료는 사용자가 승인 후 직접 제품에 입력하고 Codex 원문 열람과 혼동하지 않는다.

PR #17 최초 기능 HEAD는 0048e49af8162aab7665c6ef7aab91c7ef51f2ca다. 보완 코드/검증은 REACCEPTANCE_REPORT, 실제 실행 HEAD/주소는 보호 폴더 RUNBOOK과 manifest를 확인한다. PR은 Draft로 유지한다.
기준: 00_PROJECT_BASELINE, 01_SYSTEM_ARCHITECTURE, MVP IMPLEMENTATION_CONTRACT 및 USER_ACCEPTANCE_GUIDE.
이 도구는 합성자료 인수환경만 준비한다. 제품 API/권한/Schema/State/업무 로직과 기존 테스트는 변경하지 않는다.

## 최소 도구 변경 범위
- apps/api/tests/manual_acceptance.py: 독립 Docker PostgreSQL/Role/DB/볼륨/포트, build와 지속 실행, start/status/stop/cleanup.
- manual_acceptance_server.py: 실제 API와 CompanyProvider를 유지하고 Notice/Collector의 파일 저장소만 소유 경로로 연결한다.
- manual_acceptance_seed.py: 기존 mvp_portal_setup의 계정 4개와 미분석 공고 입력 재사용, 승인된 digest의 실제 649개 기능 import, 합성 입력/안내 생성.
- manual_acceptance_lan.ps1: 별도 관리자 승인 후 지정 PC에만 8444/TCP 규칙 추가/제거. 기존 규칙 편집 금지.
- test_manual_acceptance_tools.py: nonce/경로/manifest, 외부 키 제거, 쿠키 분리와 정리 확인의 보호 검사.
- 기존 isolation.py, isolated_worker.py, Alembic, LocalPrivateFiles, Capability inventory import를 재사용한다.
- 기업/사업장/Fact/분석/Review/서비스/조합/Match/Proposal/승인 결과를 준비 도구에서 생성하지 않는다.

## 환경 분리
API/Web/PostgreSQL은 loopback, 별도 Caddy 프로세스만 지정 LAN IP의 새 HTTPS 포트를 사용한다.
기존 8443 서비스/프로세스/설정/CA, 공유 DB, 실제 자료/권한/계정을 변경하지 않는다.
자기 CA/PKI, 비활성 admin endpoint, 시스템 인증서 신뢰 자동 설치 금지로 Caddy를 분리한다.
같은 IP의 포트 간 쿠키 충돌을 막기 위해 datco_uat_<nonce>만 내부 datco_session으로 변환한다.
원래 서비스의 datco_session은 전달하지 않고 응답에는 별도 namespace와 Secure를 적용한다. 제품 인증은 그대로다.
자격정보·manifest·로그·자료는 Git 제외된 storage/private/runtime/manual-acceptance/<nonce>에 저장한다.
ACL은 현재 Windows 사용자와 SYSTEM만 허용한다. 비밀번호/토큰을 Git/PR/채팅에 기록하지 않는다.
일반 DATABASE_URL/.env로 fallback하지 않으며 Live 키/성공 fixture flags를 상속하지 않는다.
기업마당 키는 비어 있고 외부 AI는 NOT_CONFIGURED다. 실제 고객자료/계정을 복제하지 않는다.

## PR17 보존 기록 — 아래 8444 준비·전환 명령은 PR18에서 실행 금지
설치된 .venv, Node/Docker, 승인된 649개 입력, 확인한 Caddy 실행 파일을 사용한다.
~~~powershell
& apps/api/.venv/Scripts/python.exe -B apps/api/tests/manual_acceptance.py create --host 10.10.10.145 --https-port 8444 --caddy <실행파일> --inventory _local_inputs/dmp_features_649.json
& apps/api/.venv/Scripts/python.exe -B apps/api/tests/manual_acceptance.py start --nonce <생성된-nonce>
~~~
create는 일회 실행이다. 인수 중 다시 create/seed하지 않는다. 소유 DB에서만 Alembic upgrade/check를 수행한다.
Web은 고유 distDir로 production build하며 자동 생성 next-env.d.ts는 원래 내용으로 복원한다.
CI finally의 자동 DB 삭제 경로는 호출하지 않는다. 도구 종료 후에도 supervisor가 자식 프로세스를 유지한다.

보호 폴더의 RUNBOOK.md에 실제 주소/입력값/역할/검증 순서/운영 방법을 제공한다.
CREDENTIALS.txt는 로컬 확인하며 원격 검수자에게는 사용자가 승인된 사내 보안 경로로 전달한다.
inputs에는 TEST 사업자등록 스캔 PDF, 물류 요구 TXT/PDF, 합성 서비스 작성 예시가 있다.
649개 기능은 실제 원천이다. 서비스 묶음은 합성 예시이며 관리자 본인이 UI에서 작성·검토·발행한다.
실제 공개 Live 공고는 사용하지 않는다. 공고 원천은 apps/api/fixtures/notice/normal.json 및 연결 HTML/PDF의 DEMO다.
자료의 최신성/적용조건을 사람이 검토하고 미확정 조건의 Guard를 우회하지 않는다.

## 사용자 인수 순서
기업 담당자 신규등록 → 운영자 접근범위 확인 → 관리자 접근권한 부여/서비스 발행 →
기업 개선요구 제출/ACK → 운영자 분석/근거/보완요청/공식 확정 →
서비스 조합/공고 요건 검토/Matching → 16절 제안서 DOCX/PDF →
기업/지정 승인자 검토/수정요청/새 Version 재전달.
최초 기업이 없어 operator/approver Membership은 새 기업에 관리자 UI로 직접 부여한다.
직접 승인자와 담당자 내부 승인근거 기록 방식은 구분한다.
evidence/issues.csv에 PASS/오류/사용성 문제·Version·캡처·결과물을 연결한다.
Windows+Shift+S로 캡처하며 실제 포털에서 다운로드한 DOCX/PDF를 downloads에 보존한다.
public-root.crt는 시험 CA 공개 인증서다. 개인키를 배포하지 않는다. 신뢰 등록은 사용자 별도 확인 후 처리한다.

## 안전한 운영/정리
START.cmd / STATUS.cmd / STOP.cmd를 현재 PC에서 실행한다.
STOP은 자기 API/Worker/Web/게이트웨이와 레이블을 확인한 전용 PostgreSQL 컨테이너만 종료한다.
DB 볼륨/계정/업로드/업무이력/증빙은 보존하고 START로 동일 환경을 재개한다.
소스 HEAD 변경/비정상 상태/재부팅 후에는 자동 복구·새 seed 없이 담당자 확인을 요구한다.
supervisor 실패는 자기 자식만 종료하고 DB/파일을 보존한다. 검증하지 않은 PID를 임의 종료하지 않는다.
인수 종료 후 STOP → 증빙 보존 확인 → CLEANUP.cmd에서 정확한 nonce 확인 순으로 정리한다.
cleanup은 manifest 이름과 컨테이너/볼륨 레이블을 둘 다 확인하고 소유 DB 컨테이너/볼륨만 삭제한다.
입력/증빙/안내는 자동 재귀 삭제하지 않는다. 공유 DB Drop/Migration reset을 하지 않는다.
승인 후 만든 LAN 규칙은 관리자 권한으로 manual_acceptance_lan.ps1 -Action Remove를 실행하여 자기 규칙만 제거한다.
접속이 차단된 상태에서 USER_ACCEPTANCE_READY로 보고하지 않는다.

## 실제 검증과 한계
2026-10-30: 별도 Web production build, 독립 Alembic fg31m0012026와 check,
보호 검사 15 PASS, 4역할 브라우저 로그인/F5/로그아웃 및 기존 쿠키 보존,
시험 CA/IP SAN 검증, 외부 private endpoint 404, 중지/동일 DB·파일·자격정보 재시작을 실행했다.
evidence/preflight-browser.json, persistence-validation.json과 초기 화면 캡처에 증빙을 보존한다.
정상 LOGIN/LOGOUT 감사기록은 보존하며 전체 업무 성공 결과를 주입하지 않는다.
이는 제품 전체 업무의 사용자 인수 완료를 뜻하지 않는다. 준비 단계의 업무 결과는 0건이다.
PR HEAD는 그대로다. 신규 로컬 인수 도구를 원격 CI가 검증했다고 표시하지 않는다.


## 같은 주소·계정으로 새 인수 시작 (2026-11-02 증분)

1. 기존 소유 인수 DB의 pg_dump, runtime 원본/증빙/도구 사본을 보호 경로에 확보하고 별도 restore DB에서 전체 행·파일 복원을 검증한다. 원래 DB/볼륨/파일은 삭제하지 않는다.
2. 기존 8444 환경을 유지한 채 개발/전체 자동검증을 수행한다. 별도 8445 준비 시 create에 --accounts-from <이전-보호-runtime>을 지정한다.
3. source는 같은 Git common repository, 소유 manifest/DB/Role/컨테이너 레이블·loopback 포트와 네 TEST_MVP 계정의 실제 역할·비밀번호를 읽기 전용으로 검증한다. 비밀번호/해시는 출력하지 않는다. 새 DB에는 새 해시로 동일 합성 자격만 적용하고 기존 회사/검토/결과는 복제하지 않는다.
4. 이전 시험 CA/인증서 저장소만 새 보호 경로로 복사한다. 공유 8443 TLS/신뢰 저장소와 방화벽은 변경하지 않는다. 새 환경의 계정/포털·DB/Worker·원천649·빈 업무 결과를 검증한다.
5. 최종 CI 통과 후 원래 8444 앱만 중지하고 마지막 데이터 백업·복원 확인을 수행한다. 새 환경도 중지한 상태에서 rebind --nonce <새-nonce> --confirm <새-nonce> --https-port 8444로 자체 주소만 변경하고 시작한다.
6. rebind는 중지·정확 nonce·소유 Docker 레이블과 포트 비점유를 검사한다. 8443/49355/49356은 거부한다. 승인된 기존 8444 규칙/동일 Caddy 실행 파일을 재사용하며 새 규칙은 추가하지 않는다.
7. 새 namespace 쿠키로 기존 세션을 재사용하지 않는다. /login에서 기존 자격으로 다시 로그인하고 F5/로그아웃을 확인한다. 원래 CREDENTIALS.txt 값은 그대로 보존한다.
8. 원래 보호 폴더의 실행 안내/바로가기는 새 환경을 가리키되 이전본을 백업한다. 이전 데이터의 복구는 원래 코드 HEAD+백업 도구·DB·파일을 별도 소유 경로에 복원하여 수행한다. 공유 서비스를 복구 대상으로 사용하지 않는다.

서비스 전환 전 모든 필수 자동검증이 통과해야 한다. 실제 새 runtime과 최종 실행 결과는 단일 통합 보고 및 보호 RUNBOOK에 기록하며, 자동 통과를 사용자 인수 완료로 표시하지 않는다.
