"""Inputs and identities only. Never creates a company, review or business result."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from sqlalchemy import inspect, text
from app.infrastructure.database import get_engine, get_session_factory
from app.capability.application import CapabilityApplication
from app.notice.domain import Actor
from isolation import require_test_database
from manual_acceptance import ROOT, owned, write
from registration_sources import scan


def initial_counts():
    engine = get_engine()
    with engine.connect() as connection:
        names = inspect(connection).get_table_names()
        counts = {name: connection.execute(text('SELECT count(*) FROM "' + name.replace('"', '""') + '"')).scalar_one() for name in names}
    assert all(name in counts for name in ("companies", "analysis_runs", "proposals"))
    forbidden = ("candidate", "review", "approval", "match", "composition", "confirmed", "improvement")
    assert counts["companies"] == counts["analysis_runs"] == counts["proposals"] == 0
    assert not {name: count for name, count in counts.items() if count and any(word in name for word in forbidden)}
    return counts


def prepare(nonce, inventory):
    require_test_database()
    out = owned(nonce)
    context = json.loads((out / "accounts.json").read_text(encoding="utf-8"))
    if context["nonce"] != nonce:
        raise RuntimeError("ACCOUNT_NONCE_MISMATCH")
    raw = inventory.read_bytes()
    from app.infrastructure.dmp_inventory import EXPECTED_SHA256
    if sha256(raw).hexdigest() != EXPECTED_SHA256:
        raise RuntimeError("APPROVED_FEATURE_SOURCE_DIGEST_REQUIRED")
    with get_session_factory().begin() as session:
        result = CapabilityApplication(session).import_inventory(raw, Actor(context["ids"]["admin"], "DATCO_ADMIN"))
        assert result["feature_count"] == 649
    counts = initial_counts()
    write(out / "initial-counts.json", counts)
    company = "TEST 합성제조 재고업무 " + nonce
    as_is = "물류 창고 1개 사업장의 입출고를 Excel로 수기 기록하여 재고 차이가 발생한다. 최근 한 달 재고 오차율은 8%이며 입출고 담당자가 월말 실사로 측정한다. 바코드 리더기 2대를 사용하고 재고 이력을 Excel에 기록한다."
    to_be = "입출고 이력과 재고 데이터를 연동하여 월 재고 오차율을 2% 이하로 낮추고, 입출고 이력 관리 기능과 재고 조회 기능을 사용하려고 한다. 사업비와 일정은 근거 확인 후 별도 산정한다."
    demand = "TEST SYNTHETIC INPUT - 실제 기업자료 아님\n기업명: " + company + "\n업종: 제조업\nAs-Is: " + as_is + "\nTo-Be: " + to_be + "\n합성 시험 수치이며 실제 측정값 아님.\n"
    (out / "inputs/TEST-demand-logistics.txt").write_text(demand, encoding="utf-8")
    alternative=demand.replace(company,"TEST 합성 물류서비스기업 "+nonce).replace("업종: 제조업","업종: 물류 서비스")
    (out/"inputs/TEST-demand-service-logistics.txt").write_text(alternative,encoding="utf-8")

    (out / "inputs/TEST-registration-scan.pdf").write_bytes(scan(context["business_number"], company))
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import textwrap
    font = Path("C:/Windows/Fonts/malgun.ttf")
    if not font.exists():
        raise RuntimeError("LOCAL_KOREAN_FONT_REQUIRED")
    pdfmetrics.registerFont(TTFont("ManualKorean", str(font)))
    doc = canvas.Canvas(str(out / "inputs/TEST-demand-logistics.pdf"))
    doc.setTitle("TEST SYNTHETIC INPUT - NOT CUSTOMER DATA")
    doc.setFont("ManualKorean", 11)
    y = 790
    for line in demand.splitlines():
        for row in textwrap.wrap(line, width=46):
            doc.drawString(40, y, row)
            y -= 20
    doc.save()
    samples = dict(label="TEST 합성 서비스 작성 예시 - 실제 제공/가격/구축 확약 아님",
        logistics=dict(service="TEST 합성 — 입출고·재고 이력 연계",
            description="수동 인수용 서비스 작성 예시. 실제 납품/인터페이스/가격은 미확정.",
            source_feature_ids=["DMP-D89936F06CA33048", "DMP-A72B49E339A21D50", "DMP-757AF017E65ADE72", "DMP-9942A5CC2A989A73"],
            problems=["재고", "입출고", "수기"], conditions=["동일 시험 사업장의 입출고 자료를 사람이 확인"],
            exclusions=["가격·구축기간 확약", "자동 정부지원 자격 판정"],
            prerequisites=["품목 식별자·바코드·연계 권한 검토"],
            scope="시험 사업장 1곳의 입출고 등록·재고 조회. 인터페이스는 확인 필요.",
            evidence_note="649개 실제 원천 기능 중 위 ID를 UI에서 선택. 서비스 묶음 자체는 합성 예시이며 관리자 직접 검토·발행."),
        manufacturing=dict(service="TEST 합성 — 작업실적·불량 현황 확인",
            source_feature_ids=["DMP-3B035A3C50B10091", "DMP-B1C747746FD519C7"],
            note="제조업 추가 시험용. 실제 생산실적·불량 원천이 있을 때만 적용. 물류기업에 기계적으로 적용 금지."))
    write(out / "inputs/TEST-service-authoring-examples.json", samples)
    (out / "CREDENTIALS.txt").write_text(
        "LOCAL PRIVATE — 합성 인수계정. Git/PR/채팅에 복사 금지.\n"
        + "\n".join(label + ": " + username for label, username in context["accounts"].items())
        + "\npassword (합성 계정 공통): " + context["password"] + "\n", encoding="utf-8")
    (out / "evidence/issues.csv").write_text("ID,일시,역할,화면,재현절차,기대결과,실제결과,심각도,Version,캡처파일,결과물파일,비고\n", encoding="utf-8-sig")
    manifest=json.loads((out/"manifest.json").read_text(encoding="utf-8"))
    readme = f"""# DATCO ONE 수동 사용자 인수환경
- 기준 코드: {manifest["head"]} / PR #17 Draft
- 주소: {manifest["origin"]}/login
- 독립 환경: {nonce}. 실제 기업자료를 입력하거나 외부 AI/유료 API를 사용하지 마세요.
- CREDENTIALS.txt에서 계정/비밀번호를 로컬 확인합니다. 다른 PC 사용자에게는 사내 승인된 보안 경로로 전달하세요.
- 새 환경의 자체 CA를 사용합니다. 기존 HTTPS 인증서/신뢰 저장소는 변경하지 않았습니다.
  LAN PC에서는 TEST 주소/포트와 환경 식별자를 확인하고 이 시험환경의 인증서 경고만 승인하거나,
  public-root.crt 공개 인증서를 해당 시험 브라우저에서 별도 확인 후 신뢰하세요. 개인키는 배포하지 마세요.
- 최초 상태: 계정 4개, 실제 기능 649개, 미분석 합성 공고 1건. 기업·사업장·검토·승인·서비스·제안서 결과 0건.
- 649개는 승인된 실제 DMP 기능 원천(원본 digest 검증). 서비스 작성 예시는 TEST 합성 자료이며 납품 가능성/가격 확약이 아닙니다.
- 실제 공개 공고는 미사용합니다. 공고 원천은 apps/api/fixtures/notice/normal.json 및 연결된 DEMO PDF입니다.
  화면의 MVP synthetic unanalysed {nonce} 공고는 실제 접수 가능한 사업이 아닙니다.\n  이 DEMO 원문은 제조기업 대상입니다. 기본 제조기업/재고 업무 사례와 구분하여 TEST-demand-service-logistics.txt의\n  물류 서비스업을 시험할 때는 공고 부적합·미확인 예외가 정상일 수 있습니다. 업종을 임의 변경하여 자격을 통과시키지 마세요.
- 파일 원천: registration_sources.scan 및 위 텍스트에서 생성. 사업자번호는 체크섬만 맞는 무작위 합성값입니다.
  모든 수치는 시험값입니다. 실제 자료/계정/공유 DB는 복사하지 않았습니다.

## 사용자 업무 순서
1. 기업 담당자(editor): 로그인 → 신규 기업등록. inputs/TEST-registration-scan.pdf를 업로드해 추출 후보를 확인하거나,
   합성 기업명 '{company}', 사업자번호 '{context["business_number"]}', 업종 '제조업'을 입력합니다. 기본 사례는 제조기업 내부의 창고 업무이며 업종과 문제 분야를 구분합니다.
   사업장은 'TEST 합성창고', 주소 'TEST 합성주소', 공정 '창고 입출고'로 사용합니다.
   스캔 추출 오류도 시험결과로 기록하고 수동 입력 경로를 사용합니다.
2. 운영자(operator): 자신의 메뉴와 아직 기업 접근범위가 없는 상태를 확인합니다.
3. 관리자(admin): 사용자·권한에서 새 기업에 operator, approver의 접근범위를 각각 부여합니다.
   실제 기능 649개를 확인합니다. 기준정보·버전의 Capability 작성에서
   inputs/TEST-service-authoring-examples.json의 합성 서비스와 실제 기능 ID를 확인하고
   문제/적용조건/제외/선행조건/제공범위/근거를 직접 작성·검토·발행합니다.
   미리 발행된 서비스는 없습니다. 연결 모니터의 외부 AI 4종은 NOT_CONFIGURED가 정상입니다.
4. 기업 담당자: 개선요구 등록 → 새 개선요구. 현재 문제점에 아래 As-Is, 개선목표에 To-Be를 입력합니다.
   제약은 '동일 시험 사업장의 Excel 원본과 연계 권한 확인 필요'로 입력합니다.
   inputs/TEST-demand-logistics.txt 또는 PDF를 관련파일로 첨부하고 제출합니다.
   첨부자료의 추출 후보 ACK와 개선요구 ACK는 실제 해당 Version을 확인한 후 수행합니다.
   As-Is: {as_is}
   To-Be: {to_be}
5. 운영자: 기업 통합 업무 → 제출 Version·첨부·검사범위 확인 → 분석을 명시 실행.
   후보/근거/자료처리 한계를 검토하고 선택/제외/의견을 기록합니다. 필요 시 보완요청 초안을 편집합니다.
   최종 확인 취소 시 발송 0건, 새로고침 후 영속 초안, 기업 답변·재보완을 확인합니다.
   기업 ACK 후에만 Fact/개선요구를 사람이 공식 확정합니다. 후보 검토와 공식 확정은 별개입니다.
6. 운영자: DATCO 서비스 추천 → 서비스 조합 검토에서 발행 서비스와 동일 개선요구 Version을 선택합니다.
   포함/제외 이유, 기능별 역할, 범위, 충족/부분/미충족, 통합 조건과 불확실성을 직접 검토·저장합니다.
7. 운영자: 정부지원사업 추천 → 위 합성 공고의 원문/PDF → 분석 Worker 실행 → 실제 근거/위치 확인 → 요건 확인 의견 저장.
   미확정 요건/기업 Fact는 자동 충족으로 처리하지 않습니다.
8. 운영자: 매칭·자격 검토에서 조건별 근거와 미해결 항목을 확인하고 사람이 판정합니다.
   필수 입력이 부족하면 버튼 불가 이유를 기록하고 해당 앞 단계로 돌아갑니다. Guard를 우회하지 않습니다.
9. 운영자: 맞춤형 제안서 → 16개 항목 검토 → DOCX/PDF 생성·다운로드.
   evidence/와 downloads/에 정확한 Version·파일명을 함께 보존합니다.
   기업 전달 최종 확인창에서 Escape/취소/이중 클릭 방지를 검증한 뒤 실제 합성 계정에만 전달합니다.
10. 기업 담당자: 받은 제안서에서 정확한 전달 Version·본문·파일·이력을 열고 수정 요청/내부 승인근거 기록을 검토합니다.
    직접 승인자 방식은 approver 계정으로 '/'의 기존 승인 업무에서 검토합니다.
    직접 승인과 담당자의 내부 승인근거 기록은 별도 방식입니다.
11. 수정 요청 → 운영자 새 Version → 재검토·재전달 → 기업 재확인. 과거 Version/첨부/승인 이력을 보존합니다.
12. 같은 브라우저에서는 로그아웃 후 역할을 변경하거나 역할별 브라우저 프로필을 사용합니다.
    F5/재로그인·타기업 접근 거부·타Version 혼합 방지·전달 취소도 기록합니다.

## 문제/증빙 기록
- evidence/issues.csv에 정상 PASS/오류/사용성 문제를 구분해 기록합니다. 비밀번호·토큰을 캡처하지 마세요.
- 화면 캡처: Windows+Shift+S → evidence/에 단계-역할-번호.png로 저장.
- DOCX/PDF: 실제 포털 다운로드를 downloads/에 저장하고 Version과 결과를 CSV에 연결합니다.
- 준비 도구는 회사등록/분석/서비스/매칭/제안/승인 결과를 미리 생성하지 않았습니다.

## 안전한 운영
- START.cmd: 동일 DB·파일·포트·계정으로 시작. 이미 실행 중이거나 코드 HEAD가 달라지면 중단합니다.
- STATUS.cmd: 현재 상태 조회. 포트/브라우저 응답도 함께 확인하세요.
- STOP.cmd: 이 환경의 API/Worker/Web/게이트웨이와 전용 PostgreSQL 컨테이너만 종료합니다.
  DB 볼륨·업로드·계정·이력·증빙은 보존됩니다. 중지 후 START.cmd로 재개합니다.
- CLEANUP.cmd: STOP 후 nonce를 명시 입력해야 이 환경의 레이블을 검증하고 전용 DB 컨테이너/볼륨만 제거합니다.
  증빙/입력/로컬 안내는 보존됩니다. 인수 완료 전 실행하지 마세요.
- Windows/Docker 재부팅 후 자동 실행하지 않습니다. 상태가 FAILED/STARTING 또는 비정상 종료이면 로그를 확인하고
  연구 담당자에게 환경 상태 복구를 요청하세요. 검증하지 않은 PID를 임의 종료하지 않습니다.
- 원래 https://10.10.10.145:8443와 다른 포트이며 로그인 쿠키도 별도 namespace입니다.
- 기존 Caddy·방화벽·DB·원본 PDF·계정·서비스 프로세스는 변경하지 않습니다.
"""
    (out / "RUNBOOK.md").write_text(readme, encoding="utf-8")
    python = str(ROOT / "apps/api/.venv/Scripts/python.exe")
    script = str(ROOT / "apps/api/tests/manual_acceptance.py")
    for filename, action in (("START", "start"), ("STOP", "stop"), ("STATUS", "status")):
        (out / (filename + ".cmd")).write_text('@echo off\r\nchcp 65001 >nul\r\n"' + python + '" -B "' + script + '" ' + action + " --nonce " + nonce + "\r\npause\r\n", encoding="utf-8",newline="")
    (out / "CLEANUP.cmd").write_text('@echo off\r\nchcp 65001 >nul\r\necho DESTRUCTIVE: removes ONLY this isolated acceptance database. Stop first.\r\n"' + python + '" -B "' + script + '" cleanup --nonce ' + nonce + ' --confirm-prompt\r\npause\r\n', encoding="utf-8",newline="")
    print("SYNTHETIC_INPUTS_READY: companies/reviews/results/approvals=0; source_features=649")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.nonce, args.inventory)
