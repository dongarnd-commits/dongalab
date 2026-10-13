# Acceptance mappings are test evidence, not changes to docs/10 status.
from datetime import datetime,timedelta,timezone
from uuid import uuid4
import pytest
from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect
from app.infrastructure.database import Base
from fastapi.testclient import TestClient
from app.main import app
from app.infrastructure.database import get_engine,get_session
from app.infrastructure.notice_store import SqlNoticeStore
from app.infrastructure.notice_documents import LocalPrivateFiles,DeterministicAnalysis,extract
from app.infrastructure.notice_queue import claim,recover_expired
from app.infrastructure import notice_schema as schema
from app.infrastructure.local_auth import hash_password
from app.notice.application import NoticeApplication
from app.notice.domain import Actor,Denied,CandidateOutput,Span
from app.demo import load_input,FIXTURES
from app.worker import process_one

pytestmark=pytest.mark.integration

@pytest.fixture
def context(tmp_path):
    schema_name="test_notice_"+uuid4().hex
    connection=get_engine().connect().execution_options(schema_translate_map={None:schema_name})
    outer=connection.begin()
    connection.exec_driver_sql("CREATE SCHEMA "+schema_name)
    Base.metadata.create_all(connection)
    factory=sessionmaker(bind=connection,join_transaction_mode="create_savepoint")
    files=LocalPrivateFiles(tmp_path/"private")
    with factory.begin() as session:
        actor=SqlNoticeStore(session).add("actors",username=str(uuid4()),role="DATCO_OPERATOR",password_hash=hash_password("test-only-local-password"))
    yield factory,files,Actor(actor["id"],actor["role"])
    outer.rollback()
    connection.close()

def prepare(context,name="normal"):
    factory,files,actor=context
    with factory.begin() as session:
        store=SqlNoticeStore(session)
        notice=load_input(store,files,name,external_key="TEST_"+str(uuid4()))
        version=store.rows("versions",notice_id=notice["id"])[0]
        application=NoticeApplication(store,files)
        job=application.request(actor,version["id"],str(uuid4()))
    return notice,version,job

def detail(context,notice):
    factory,files,actor=context
    with factory() as session:
        return NoticeApplication(SqlNoticeStore(session),files).detail(actor,notice["id"])

def confirm(context,version,candidate,**kwargs):
    factory,files,actor=context
    with factory.begin() as session:
        return NoticeApplication(SqlNoticeStore(session),files).confirm(actor,version["id"],candidate["id"],
            kwargs.get("official",True),"Human source review","Only this reviewed clause",kwargs.get("resolution",""))

def test_ac_notice_01_02_03_04_05_08(context):
    notice,version,job=prepare(context)
    factory,files,actor=context
    before=detail(context,notice)["versions"][0]
    assert before["confirmed"]==[] and before["jobs"][0]["state"]=="QUEUED"
    assert process_one(factory,files)
    after=detail(context,notice)["versions"][0]
    run=after["runs"][0]
    assert run["version_id"]==version["id"]
    assert after["jobs"][0]["state"]=="SUCCEEDED"
    assert after["confirmed"]==[]
    pdf=next(c for c in run["candidates"] if c["kind"]=="REQUIRED_DOCUMENT")
    assert pdf["evidence"]["page"]==2
    assert pdf["content"] in pdf["evidence"]["text"]
    with factory.begin() as session:
        source,data=NoticeApplication(SqlNoticeStore(session),files).download(actor,pdf["evidence"]["source_id"])
        assert data.startswith(b"%PDF-") and source["media_type"]=="application/pdf"
    result=confirm(context,version,pdf)
    repeated=confirm(context,version,pdf)
    assert result["id"]==repeated["id"]
    refreshed=detail(context,notice)["versions"][0]
    saved=refreshed["confirmed"][0]
    assert saved["items"][0]["candidate_id"]==pdf["id"]
    assert saved["review"]["actor_id"]==actor.id
    assert saved["review"]["outcome"]=="CONFIRM"
    assert saved["notice_version_id"]==version["id"]
    assert process_one(factory,files) is False
    with factory() as session:
        records=SqlNoticeStore(session).rows("audits",notice_version_id=version["id"])
        assert {r["action"] for r in records}>={"REQUEST_NOTICE_REVIEW","COMPLETE_JOB","CONFIRM_NOTICE_REQUIREMENT"}

def test_ac_notice_06_conflict_preserved_requires_human_resolution(context):
    notice,version,job=prepare(context,"conflict")
    factory,files,_=context
    process_one(factory,files)
    output=detail(context,notice)["versions"][0]
    assert output["metadata"]["period_original"]=="2026-10-01 to 2026-10-23"
    assert output["runs"][0]["conflicts"]
    periods=[c for c in output["runs"][0]["candidates"] if c["kind"]=="APPLICATION_PERIOD"]
    assert len({c["content"] for c in periods})==2
    with pytest.raises(Denied):
        confirm(context,version,periods[0])
    result=confirm(context,version,periods[0],resolution="Reviewed both conflicting DEMO source clauses; selected this exact clause.")
    assert result
    assert detail(context,notice)["versions"][0]["runs"][0]["conflicts"]

def test_ac_notice_07_partial_source_scoped_confirmation(context):
    notice,version,_=prepare(context,"partial")
    factory,files,_=context
    process_one(factory,files)
    version_output=detail(context,notice)["versions"][0]
    assert version_output["jobs"][0]["state"]=="PARTIAL"
    assert version_output["runs"][0]["missing"]
    candidate=version_output["runs"][0]["candidates"][0]
    confirmed=confirm(context,version,candidate)
    assert "Partial" in confirmed["scope"]

def test_permission_version_evidence_and_empty_candidate_guards(context):
    notice,version,_=prepare(context)
    factory,files,actor=context
    with factory.begin() as session:
        service=NoticeApplication(SqlNoticeStore(session),files)
        with pytest.raises(Denied) as error:
            service.request(Actor(actor.id,"COMPANY_EDITOR"),version["id"],str(uuid4()))
        assert error.value.status==403
    with pytest.raises(Denied):
        confirm(context,version,{"id":str(uuid4())})
    process_one(factory,files)
    candidate=detail(context,notice)["versions"][0]["runs"][0]["candidates"][0]
    with pytest.raises(Denied):
        confirm(context,version,candidate,official=False)
    other,other_version,_=prepare(context)
    with pytest.raises(Denied) as error:
        confirm(context,other_version,candidate)
    assert error.value.reason=="TARGET_VERSION_MISMATCH"
    with factory.begin() as session:
        store=SqlNoticeStore(session)
        store.add("versions",notice_id=notice["id"],ordinal=2,mode="DEMO_TEST",metadata={"changed":True})
        store.change("notices",notice["id"],current_ordinal=2)
    with pytest.raises(Denied) as error:
        confirm(context,version,candidate)
    assert error.value.reason=="STALE_INPUT_VERSION"

def test_forged_provider_location_never_becomes_candidate(context):
    notice,version,job=prepare(context)
    factory,files,_=context
    class Forged:
        version="invalid-test-adapter"
        def analyze(self,spans):
            return [CandidateOutput("REQUIRED_DOCUMENT","Invented","Invalid",Span(spans[0].source_id,"PDF page 999","Invented",999))]
    process_one(factory,files,Forged())
    output=detail(context,notice)["versions"][0]
    assert output["jobs"][0]["state"]=="FAILED"
    assert output["runs"]==[]
    with factory.begin() as session:
        NoticeApplication(SqlNoticeStore(session),files).retry(context[2],job["id"])
    process_one(factory,files)
    recovered=detail(context,notice)["versions"][0]
    assert recovered["jobs"][0]["state"]=="SUCCEEDED"
    assert len(recovered["jobs"][0]["attempts"])==2

def test_missing_file_and_invalid_page_block_confirmation(context):
    notice,version,_=prepare(context)
    factory,files,_=context
    process_one(factory,files)
    candidate=next(c for c in detail(context,notice)["versions"][0]["runs"][0]["candidates"] if c["kind"]=="REQUIRED_DOCUMENT")
    with factory.begin() as session:
        SqlNoticeStore(session).change("locations",candidate["location_id"],page=999)
    with pytest.raises(Denied):
        confirm(context,version,candidate)

def test_append_only_versions_new_run_and_idempotency(context):
    notice,version,job=prepare(context)
    factory,files,actor=context
    process_one(factory,files)
    # Transaction timestamps tie in this isolated schema; UUID order is not semantic.
    first=next(c for c in detail(context,notice)["versions"][0]["runs"][0]["candidates"] if c["kind"]=="ELIGIBILITY_REQUIREMENT")
    rv1=confirm(context,version,first)
    with factory.begin() as session:
        service=NoticeApplication(SqlNoticeStore(session),files)
        same=service.request(actor,version["id"],job["request_key"])
        assert same["id"]==job["id"]
        service.request(actor,version["id"],str(uuid4()))
    process_one(factory,files)
    output=detail(context,notice)["versions"][0]
    assert len(output["runs"])==2 and len(output["confirmed"])==1
    second=next(c for r in output["runs"] if r["id"]!=first["run_id"] for c in r["candidates"] if c["kind"]=="REQUIRED_DOCUMENT")
    rv2=confirm(context,version,second)
    assert rv2["ordinal"]==2
    result=detail(context,notice)["versions"][0]["confirmed"]
    assert result[0]["id"]==rv1["id"] and len(result[0]["items"])==1
    assert len(result[1]["items"])==2

def test_retry_attempts_recovery_and_fencing(context):
    notice,version,job=prepare(context)
    factory,files,actor=context
    with factory.begin() as session:
        job_before,old_attempt=claim(session,lease_seconds=-1)
    with factory.begin() as session:
        assert claim(session) is None
        assert recover_expired(session)>=1
        NoticeApplication(SqlNoticeStore(session),files).retry(actor,job["id"])
    process_one(factory,files)
    output=detail(context,notice)["versions"][0]
    assert output["jobs"][0]["state"]=="SUCCEEDED"
    attempts=sorted(output["jobs"][0]["attempts"],key=lambda a:a["ordinal"])
    assert len(attempts)==2
    assert attempts[0]["state"]=="FAILED" and attempts[1]["state"]=="SUCCEEDED"

def test_more_source_review_preserves_candidate_without_confirmation(context):
    notice,version,_=prepare(context)
    factory,files,actor=context
    process_one(factory,files)
    candidate=detail(context,notice)["versions"][0]["runs"][0]["candidates"][0]
    with factory.begin() as session:
        NoticeApplication(SqlNoticeStore(session),files).more_source(actor,version["id"],candidate["id"],"Need more source evidence")
    with pytest.raises(Denied):
        confirm(context,version,candidate)
    result=detail(context,notice)["versions"][0]
    assert result["confirmed"]==[] and result["runs"][0]["candidates"]

def test_api_session_origin_and_role_spoofing(context):
    factory,files,who=context
    with factory() as session:
        user=SqlNoticeStore(session).get("actors",who.id)
    def session_override():
        with factory() as session:
            yield session
    app.dependency_overrides[get_session]=session_override
    try:
        with TestClient(app) as client:
            assert client.get("/notice").status_code==401
            body={"username":user["username"],"password":"test-only-local-password"}
            assert client.post("/notice/session",json=body).status_code==403
            response=client.post("/notice/session",json=body,headers={"Origin":"http://localhost:3000"})
            assert response.status_code==200 and "HttpOnly" in response.headers["set-cookie"]
            assert client.get("/notice",headers={"X-Role":"DATCO_OPERATOR"}).status_code==200
            assert client.post("/notice/session",json=dict(body,role="DATCO_OPERATOR"),headers={"Origin":"http://localhost:3000"}).status_code==422
            client.cookies.clear()
            assert client.get("/notice",headers={"X-Role":"DATCO_OPERATOR"}).status_code==401
    finally:
        app.dependency_overrides.clear()

def test_pdf_html_quality_and_migration():
    assert get_engine().dialect.name=="postgresql"
    tables=set(inspect(get_engine()).get_table_names())
    assert set(schema.Base.metadata.tables)<=tables
    source={"id":str(uuid4()),"media_type":"application/pdf"}
    spans=extract(source,(FIXTURES/"normal.pdf").read_bytes())
    assert any(s.page==2 and "Business registration" in s.text for s in spans)
    html=extract(dict(source,media_type="text/html"),(FIXTURES/"normal.html").read_bytes())
    assert any("\uc81c\uc870\uae30\uc5c5" in s.text for s in html)

def test_empty_pdf_is_partial_not_invented_evidence(context):
    from pypdf import PdfWriter
    from io import BytesIO
    notice,version,job=prepare(context)
    factory,files,_=context
    writer=PdfWriter()
    writer.add_blank_page(width=612,height=792)
    content=BytesIO()
    writer.write(content)
    key,digest=files.put(content.getvalue())
    assert extract({"id":"empty","media_type":"application/pdf"},content.getvalue())==[]
    with factory.begin() as session:
        store=SqlNoticeStore(session)
        pdf=next(s for s in store.rows("sources",version_id=version["id"]) if s["media_type"]=="application/pdf")
        store.change("sources",pdf["id"],storage_key=key,digest=digest)
    process_one(factory,files)
    output=detail(context,notice)["versions"][0]
    assert output["jobs"][0]["state"]=="PARTIAL"
    assert output["runs"][0]["missing"]
    assert all(c["evidence"]["page"] is None for c in output["runs"][0]["candidates"])

def test_changed_source_creates_version_preserves_history(context,monkeypatch,tmp_path):
    import shutil
    import app.demo as demo
    fixture_dir=tmp_path/"fixtures"
    fixture_dir.mkdir()
    for name in ["normal.json","normal.html","normal.pdf"]:
        shutil.copyfile(FIXTURES/name,fixture_dir/name)
    monkeypatch.setattr(demo,"FIXTURES",fixture_dir)
    notice,version,job=prepare(context)
    factory,files,actor=context
    process_one(factory,files)
    candidate=detail(context,notice)["versions"][0]["runs"][0]["candidates"][0]
    rv=confirm(context,version,candidate)
    html=fixture_dir/"normal.html"
    html.write_text(html.read_text(encoding="utf-8").replace("2026-10-23","2026-10-24"),encoding="utf-8")
    with factory.begin() as session:
        changed=load_input(SqlNoticeStore(session),files,"normal",external_key=notice["external_key"])
    output=detail(context,notice)
    assert output["current_ordinal"]==2 and len(output["versions"])==2
    assert output["versions"][0]["confirmed"][0]["id"]==rv["id"]
    assert output["versions"][1]["confirmed"]==[]
    replay=confirm(context,version,candidate)
    assert replay["id"]==rv["id"] and replay["historical_replay"] and not replay["current_valid"]

def test_expired_worker_cannot_publish_after_recovery_and_retry(context):
    notice,version,job=prepare(context)
    factory,files,actor=context
    class Interrupted(DeterministicAnalysis):
        def analyze(self,spans):
            with factory.begin() as session:
                store=SqlNoticeStore(session)
                store.change("jobs",job["id"],lease_until=datetime.now(timezone.utc)-timedelta(seconds=1))
                recover_expired(session)
                NoticeApplication(store,files).retry(actor,job["id"])
            assert process_one(factory,files)
            return super().analyze(spans)
    assert process_one(factory,files,Interrupted())
    output=detail(context,notice)["versions"][0]
    assert len(output["runs"])==1
    attempts=sorted(output["jobs"][0]["attempts"],key=lambda a:a["ordinal"])
    assert [a["state"] for a in attempts]==["FAILED","SUCCEEDED"]
    assert output["jobs"][0]["state"]=="SUCCEEDED"


def test_reg01_period_replacement_preserves_other_items_and_history(context):
    notice,version,_=prepare(context,"conflict")
    factory,files,_=context
    process_one(factory,files)
    candidates=detail(context,notice)["versions"][0]["runs"][0]["candidates"]
    old=next(c for c in candidates if c["kind"]=="APPLICATION_PERIOD" and c["content"].endswith("23"))
    new=next(c for c in candidates if c["kind"]=="APPLICATION_PERIOD" and c["content"].endswith("30"))
    other=next(c for c in candidates if c["kind"]=="ELIGIBILITY_REQUIREMENT")
    first=confirm(context,version,old,resolution="Selected 23")
    confirm(context,version,other,resolution="Selected eligibility")
    last=confirm(context,version,new,resolution="Selected 30 replacing 23")
    history=detail(context,notice)["versions"][0]["confirmed"]
    assert history[0]["id"]==first["id"] and history[0]["items"][0]["content"].endswith("23")
    assert history[-1]["id"]==last["id"]
    assert [i["content"] for i in history[-1]["items"] if i["kind"]=="APPLICATION_PERIOD"]==[new["content"]]
    assert any(i["candidate_id"]==other["id"] for i in history[-1]["items"])
    assert old["evidence"] and len(history)==3
    old_replay=confirm(context,version,old,resolution="Selected 23")
    assert old_replay["historical_replay"] and not old_replay["current_valid"]
    with factory.begin() as session:
        NoticeApplication(SqlNoticeStore(session),files).request(context[2],version["id"],str(uuid4()))
    process_one(factory,files)
    output=detail(context,notice)["versions"][0]
    repeated=next(c for r in output["runs"] if r["id"]!=other["run_id"] for c in r["candidates"] if c["kind"]==other["kind"] and c["content"]==other["content"])
    confirm(context,version,repeated,resolution="Reviewed repeated clause")
    assert len(detail(context,notice)["versions"][0]["confirmed"][-1]["items"])==2


def test_reg02_replay_identity_before_current_guard(context):
    notice,version,job=prepare(context)
    factory,files,actor=context
    process_one(factory,files)
    candidates=detail(context,notice)["versions"][0]["runs"][0]["candidates"]
    confirmed=confirm(context,version,candidates[0])
    with factory.begin() as session:
        store=SqlNoticeStore(session)
        newer=store.add("versions",notice_id=notice["id"],ordinal=2,mode="DEMO_TEST",metadata={})
        store.change("notices",notice["id"],current_ordinal=2)
        application=NoticeApplication(store,files)
        replay=application.request(actor,version["id"],job["request_key"])
        assert replay["id"]==job["id"] and replay["historical_replay"] and not replay["current_valid"]
        with pytest.raises(Denied,match="IDEMPOTENCY_TARGET_MISMATCH"):
            application.request(actor,newer["id"],job["request_key"])
        with pytest.raises(Denied,match="STALE_INPUT_VERSION"):
            application.request(actor,version["id"],str(uuid4()))
    replay=confirm(context,version,candidates[0])
    assert replay["id"]==confirmed["id"] and replay["historical_replay"] and not replay["current_valid"]
    with pytest.raises(Denied,match="IDEMPOTENCY_TARGET_MISMATCH"):
        confirm(context,version,candidates[0],official=False)
    with pytest.raises(Denied,match="STALE_INPUT_VERSION"):
        confirm(context,version,candidates[1])


def test_reg02_retry_duplicate_is_one_transition_and_historical_receipt(context):
    notice,version,job=prepare(context,"partial")
    factory,files,actor=context
    process_one(factory,files)
    key=str(uuid4())
    with factory.begin() as session:
        application=NoticeApplication(SqlNoticeStore(session),files)
        original=application.retry(actor,job["id"],key)
        duplicate=application.retry(actor,job["id"],key)
        assert original["id"]==duplicate["id"] and duplicate["historical_replay"]
    process_one(factory,files)
    with factory.begin() as session:
        store=SqlNoticeStore(session)
        store.add("versions",notice_id=notice["id"],ordinal=2,mode="DEMO_TEST",metadata={})
        store.change("notices",notice["id"],current_ordinal=2)
        application=NoticeApplication(store,files)
        replay=application.retry(actor,job["id"],key)
        assert replay["state"]=="QUEUED" and not replay["current_valid"]
        assert len(store.rows("audits",job_id=job["id"],action="RETRY_JOB"))==1
        with pytest.raises(Denied,match="STALE_INPUT_VERSION"):
            application.retry(actor,job["id"],str(uuid4()))
    another,_,other_job=prepare(context,"partial")
    process_one(factory,files)
    with factory.begin() as session:
        with pytest.raises(Denied,match="IDEMPOTENCY_TARGET_MISMATCH"):
            NoticeApplication(SqlNoticeStore(session),files).retry(actor,other_job["id"],key)


def test_reg03_metadata_only_conflict_retains_both_source_identities(context):
    notice,version,_=prepare(context)
    factory,files,_=context
    with factory.begin() as session:
        store=SqlNoticeStore(session)
        for source in store.rows("sources",version_id=version["id"]):
            content=((FIXTURES/"conflict.pdf").read_bytes() if source["media_type"]=="application/pdf"
                else (FIXTURES/"normal.html").read_bytes().replace(b"2026-10-23",b"2026-10-30"))
            key,digest=files.put(content)
            store.change("sources",source["id"],storage_key=key,digest=digest)
    process_one(factory,files)
    run=detail(context,notice)["versions"][0]["runs"][0]
    conflict=run["conflicts"][0]
    assert conflict["values"]==["2026-10-01 to 2026-10-23","2026-10-01 to 2026-10-30"]
    metadata=next(e for e in conflict["evidence"] if e["source_type"]=="NOTICE_METADATA")
    pdf=next(e for e in conflict["evidence"] if e.get("page")==1)
    assert metadata["notice_version_id"]==version["id"] and metadata["field"]=="period_original"
    assert metadata["value"].endswith("23") and pdf["value"].endswith("30")
    assert pdf["source_id"] and pdf["descriptor"] and pdf["text"]
    assert detail(context,notice)["versions"][0]["confirmed"]==[]


def test_reg04_mixed_pdf_pages_are_partial_with_readable_evidence(context):
    from io import BytesIO
    from pypdf import PdfReader,PdfWriter
    from app.infrastructure.notice_documents import extract_document
    notice,version,_=prepare(context)
    factory,files,_=context
    writer=PdfWriter()
    writer.add_page(PdfReader(FIXTURES/"normal.pdf").pages[0])
    writer.add_blank_page(width=612,height=792)
    buffer=BytesIO(); writer.write(buffer)
    content=buffer.getvalue()
    extracted=extract_document({"id":"test","media_type":"application/pdf"},content)
    assert extracted.total_pages==2 and extracted.extracted_pages==(1,) and extracted.unextractable_pages==(2,)
    key,digest=files.put(content)
    with factory.begin() as session:
        store=SqlNoticeStore(session)
        pdf=next(s for s in store.rows("sources",version_id=version["id"]) if s["media_type"]=="application/pdf")
        store.change("sources",pdf["id"],storage_key=key,digest=digest)
    process_one(factory,files)
    output=detail(context,notice)["versions"][0]
    assert output["jobs"][0]["state"]=="PARTIAL"
    missing=output["runs"][0]["missing"][0]
    assert missing["total_pages"]==2 and missing["extracted_pages"]==[1] and missing["unextractable_pages"]==[2]
    assert missing["source_id"]==pdf["id"] and "OCR" in missing["limitation"]
    assert any(c["evidence"]["page"]==1 for c in output["runs"][0]["candidates"])
    assert output["confirmed"]==[]
    from app.api.notice import actor as actor_dependency
    def session_override():
        with factory() as session:
            yield session
    app.dependency_overrides[get_session]=session_override
    app.dependency_overrides[actor_dependency]=lambda:context[2]
    try:
        with TestClient(app) as client:
            response=client.get("/notice/"+notice["id"])
            assert response.status_code==200
            api_missing=response.json()["versions"][0]["runs"][0]["missing"][0]
            assert api_missing==missing
            assert response.json()["versions"][0]["jobs"][0]["state"]=="PARTIAL"
    finally:
        app.dependency_overrides.clear()


def test_reg05_actual_errors_match_openapi_and_safe_storage_error(context,monkeypatch):
    from app.api import notice as api_notice
    from sqlalchemy.exc import SQLAlchemyError
    notice,version,_=prepare(context)
    factory,files,who=context
    monkeypatch.setattr(api_notice,"application",lambda session:NoticeApplication(SqlNoticeStore(session),files))
    def session_override():
        with factory() as session:
            yield session
    app.dependency_overrides[get_session]=session_override
    try:
        with TestClient(app) as client:
            contract=client.get("/openapi.json").json()
            assert contract["components"]["schemas"]["ErrorResponse"]["required"]==["reason"]
            def check(response,path,method,status,reason):
                assert response.status_code==status and response.json()=={"reason":reason}
                assert contract["paths"][path][method]["responses"][str(status)]["content"]["application/json"]["schema"]=={"$ref":"#/components/schemas/ErrorResponse"}
            check(client.get("/notice"),"/notice","get",401,"AUTHENTICATION_REQUIRED")
            check(client.post("/notice/session",json={}),"/notice/session","post",403,"UNTRUSTED_ORIGIN")
            with factory() as session:
                user=SqlNoticeStore(session).get("actors",who.id)
            headers={"Origin":"http://localhost:3000"}
            assert client.post("/notice/session",json={"username":user["username"],"password":"test-only-local-password"},headers=headers).status_code==200
            check(client.get("/notice/"+str(uuid4())),"/notice/{notice_id}","get",404,"OBJECT_NOT_FOUND")
            check(client.post("/notice/analysis",json={},headers=headers),"/notice/analysis","post",422,"INVALID_REQUEST")
            factory,files,_=context
            process_one(factory,files)
            candidate=detail(context,notice)["versions"][0]["runs"][0]["candidates"][0]
            payload={"expected_version":version["id"],"official_verified":False,"note":"Review","scope":"Clause"}
            check(client.post("/notice/candidates/"+candidate["id"]+"/confirm",json=payload,headers=headers),"/notice/candidates/{candidate_id}/confirm","post",409,"OFFICIAL_SOURCE_NOT_VERIFIED")
            def unavailable(session):
                raise SQLAlchemyError("private connection details must not escape")
            monkeypatch.setattr(api_notice,"application",unavailable)
            check(client.get("/notice/"+notice["id"]),"/notice/{notice_id}","get",503,"STORAGE_UNAVAILABLE")
    finally:
        app.dependency_overrides.clear()


def test_reg02_pre_fix_review_receipt_replays_without_rewriting_audit(context):
    notice,version,_=prepare(context)
    factory,files,actor=context
    process_one(factory,files)
    candidate=detail(context,notice)["versions"][0]["runs"][0]["candidates"][0]
    # Emulate the previous implementation's plain-text audit reason, including JSON-looking human text.
    with factory.begin() as session:
        store=SqlNoticeStore(session)
        application=NoticeApplication(store,files)
        original=application.confirm(actor,version["id"],candidate["id"],True,"[]","Clause","")
        audit=store.rows("audits",review_id=original["review_id"])[0]
        store.change("audits",audit["id"],reason="[]")
        store.add("versions",notice_id=notice["id"],ordinal=2,mode="DEMO_TEST",metadata={})
        store.change("notices",notice["id"],current_ordinal=2)
    with factory.begin() as session:
        store=SqlNoticeStore(session)
        replay=NoticeApplication(store,files).confirm(actor,version["id"],candidate["id"],True,"[]","Clause","")
        assert replay["id"]==original["id"] and replay["historical_replay"] and not replay["current_valid"]
        assert store.get("audits",audit["id"])["reason"]=="[]"
        assert len(store.rows("requirement_versions",notice_version_id=version["id"]))==1
