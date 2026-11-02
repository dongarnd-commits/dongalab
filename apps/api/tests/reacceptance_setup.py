"""Fresh UI test: accounts, synthetic source features/documents and unanalysed Notice only."""
import json
import os
from pathlib import Path
from uuid import uuid4
from hashlib import sha256
from isolation import require_test_database
from app.core.config import ROOT
from app.infrastructure.database import get_session_factory, get_engine
from app.infrastructure import capability_schema as K
from app.capability.application import CapabilityApplication, fingerprint
from sqlalchemy import text


def input_documents(out, context):
    from registration_sources import scan
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    font = next(p for p in (Path("C:/Windows/Fonts/malgun.ttf"), Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf")) if p.exists())
    pdfmetrics.registerFont(TTFont("TEST-Reacceptance", str(font)))
    docs=out/"inputs";docs.mkdir(exist_ok=True)
    company="TEST 재인수 제조기업 "+context["nonce"]
    registration=docs/"TEST-registration.pdf"
    registration.write_bytes(scan(context["business_number"],company))
    demand=docs/"TEST-demand.txt"
    demand.write_text("TEST SYNTHETIC INPUT — NOT CUSTOMER DATA\n기업명: "+company+"\n업종: 제조업\n창고 입출고를 엑셀과 수기로 관리해 재고 수량이 일치하지 않는다.\n입출고 이력과 재고정보를 통합 관리하고 중복 입력을 줄이고 싶다.",encoding="utf-8")
    finances=[]
    for year,revenue in ((2023,"10000000"),(2024,"12000000")):
        path=docs/("TEST-finance-"+str(year)+".pdf");pdf=canvas.Canvas(str(path))
        pages=[["TEST 합성 표준재무제표증명","표준재무상태표",str(year)+"년 12월 31일 현재","(단위: 원)","유동자산 001 1500","비유동자산 080 2500","자산총계 228 4000","유동부채 229 300","비유동부채 284 700","부채총계 333 1000","자본금 334 100","자본총계 382 3000"],["표준재무제표증명","표준손익계산서",str(year)+"년 01월 01일 부터",str(year)+"년 12월 31일 까지","(단위: 원)","매출액 001 "+revenue,"영업이익 129 600","당기순이익 219 400"]]
        for lines in pages:
            pdf.setFont("TEST-Reacceptance",11)
            for i,line in enumerate(lines):pdf.drawString(30,780-i*35,line)
            pdf.showPage()
        pdf.save();finances.append(str(path))
    return dict(company_name=company,registration_document=str(registration),demand_document=str(demand),financial_documents=finances)


def prepare():
    require_test_database()
    out=Path(os.environ["DATCO_TEST_FILES"]).resolve().parent
    if not out.is_relative_to((ROOT/"storage/private/runtime/ci").resolve()):
        raise RuntimeError("FRESH_BROWSER_RUNTIME_REQUIRED")
    from mvp_portal_setup import prepare as identities
    original_nonce=os.environ["DATCO_TEST_NONCE"]
    os.environ["DATCO_TEST_NONCE"]=uuid4().hex[:12]
    os.environ["DATCO_MVP_READY"]=str(out/"fresh-ready.json")
    try:identities()
    finally:os.environ["DATCO_TEST_NONCE"]=original_nonce
    target=out/"fresh-ready.json";context=json.loads(target.read_text(encoding="utf-8"))
    context.update(input_documents(out,context))
    # Source inputs are explicitly synthetic; no service draft/publish or company result.
    with get_session_factory().begin() as session:
        app=CapabilityApplication(session)
        imported=app.add(K.imports,digest=fingerprint({"fresh_synthetic":context["nonce"]}),
            metadata=dict(schema_version="1",artifact_kind="SYNTHETIC_REACCEPTANCE",source_workbook="TEST-input",
                source_sheet="TEST",source_display_date="2026-10-30",feature_count=2,system_count=1,
                group_count=1,uniqueness_rule="feature_id",system_counts={"SYNTHETIC_REACCEPTANCE":2}))
        features=[]
        for name in ("TEST 합성 재고 현황 조회","TEST 합성 입출고 이력 관리"):
            external="DMP-"+uuid4().hex[:16].upper()
            data=dict(feature_id=external,system="SYNTHETIC_REACCEPTANCE",feature_group="TEST",
                name=name,description=name+" — synthetic test source, not an actual DMP offering",
                origin="SYNTHETIC_TEST",excel_row=len(features)+1,availability="TEST_ONLY",availability_basis="SYNTHETIC_TEST")
            feature=app.add(K.features,external_id=external)
            revision=app.add(K.revisions,feature_id=feature["id"],ordinal=1,digest=fingerprint(data),data=data)
            app.add(K.members,import_id=imported["id"],feature_id=feature["id"],revision_id=revision["id"])
            features.append(dict(id=feature["id"],revision_id=revision["id"],name=name))
        context["source_features"]=features
    with get_engine().connect() as connection:
        for table in ("companies","analysis_runs","capabilities","proposals"):
            assert connection.execute(text('select count(*) from "'+table+'"')).scalar_one()==0
    context["initial_business_results"]=0
    target.write_text(json.dumps(context,ensure_ascii=False),encoding="utf-8")
    print("FRESH_UI_INPUTS_ONLY_READY")


if __name__=="__main__":
    prepare()
