import json
from copy import deepcopy
from uuid import uuid4
from io import BytesIO
from urllib.error import URLError,HTTPError
import pytest
from fastapi.testclient import TestClient
from test_notice_slice import context,detail,confirm
from app.collector.application import CollectionApplication
from app.collector.normalizer import parse_page,normalize
from app.collector.worker import process_collection_one
from app.infrastructure.bizinfo import BizinfoLive,BizinfoSnapshot,safe_url,validate_content
from app.infrastructure.notice_store import SqlNoticeStore
from app.infrastructure.notice_queue import claim,recover_expired
from app.infrastructure.database import get_session
from app.notice.application import NoticeApplication
from app.notice.domain import Actor,Denied
from app.worker import process_one
from app.main import app

pytestmark=pytest.mark.integration

def request_collection(context,mode="SNAPSHOT",key=None,pages=3,unit=2):
    factory,files,actor=context
    with factory.begin() as session:
        return CollectionApplication(SqlNoticeStore(session),files).request(actor,mode,key or str(uuid4()),unit,pages)

def collected(context,job):
    factory,files,actor=context
    with factory() as session:
        return CollectionApplication(SqlNoticeStore(session),files).detail(actor,job["id"])

def first_record(context,job):
    return collected(context,job)["attempts"][-1]["pages"][0]["records"][0]

def test_snapshot_input_to_existing_notice_analysis_and_human_confirm(context):
    factory,files,actor=context
    job=request_collection(context)
    assert process_one(factory,files) is False # Analysis worker cannot consume collection jobs.
    assert process_collection_one(factory,files)
    output=collected(context,job)
    assert output["state"]=="SUCCEEDED" and len(output["attempts"][0]["pages"])==2
    record=first_record(context,job)
    notice={"id":record["notice_id"]}; version={"id":record["notice_version_id"]}
    result=detail(context,notice)["versions"][0]
    assert result["mode"]=="SANITIZED_SNAPSHOT" and result["confirmed"]==[] and result["runs"]==[]
    assert result["metadata"]["period_original"]=="2026-10-01 ~ 2026-10-23"
    assert len(result["sources"])==2
    assert any(a["status"]=="NOT_PROVIDED" for a in record["acquisitions"])
    with factory.begin() as session:
        store=SqlNoticeStore(session)
        NoticeApplication(store,files).request(actor,version["id"],str(uuid4()))
        page=store.get("collection_pages",record["page_id"])
        assert b'jsonArray' in files.read(page["raw_key"],page["raw_digest"])
    assert process_collection_one(factory,files) is False
    assert process_one(factory,files)
    analyzed=detail(context,notice)["versions"][0]
    assert not analyzed["runs"][0]["conflicts"] and analyzed["confirmed"]==[]
    pdf=next(c for c in analyzed["runs"][0]["candidates"] if c["kind"]=="REQUIRED_DOCUMENT")
    assert pdf["evidence"]["page"]==2
    confirmed=confirm(context,version,pdf)
    assert detail(context,notice)["versions"][0]["confirmed"][0]["id"]==confirmed["id"]
    for _ in range(2):
        same=request_collection(context); process_collection_one(factory,files)
        assert first_record(context,same)["outcome"]=="UNCHANGED"
    assert len(detail(context,notice)["versions"])==1
    assert detail(context,notice)["versions"][0]["confirmed"][0]["id"]==confirmed["id"]


def test_live_and_snapshot_same_normalizer_and_no_timestamp_only_version(context):
    factory,files,_=context
    original=BizinfoSnapshot()
    live=BizinfoSnapshot(); live.origin="CONTROLLED_LIVE_RESPONSE_TEST_DOUBLE"
    live.data["jsonArray"][0]["updtPnttm"]="2026-10-15 12:00:00"
    live.data["jsonArray"][0]["inqireCo"]=999
    assert normalize(original.page(1,2)["jsonArray"][0]).core==normalize(live.page(1,2)["jsonArray"][0]).core
    first=request_collection(context); process_collection_one(factory,files,original)
    second=request_collection(context,"LIVE"); process_collection_one(factory,files,live)
    assert first_record(context,second)["notice_id"]==first_record(context,first)["notice_id"]
    assert first_record(context,second)["outcome"]=="UNCHANGED"
    assert collected(context,second)["payload"]["mode"]=="LIVE"


def test_content_change_new_version_preserves_confirmed_and_stale_guards(context):
    factory,files,actor=context
    first=request_collection(context); process_collection_one(factory,files)
    record=first_record(context,first); notice={"id":record["notice_id"]}; version={"id":record["notice_version_id"]}
    with factory.begin() as session: NoticeApplication(SqlNoticeStore(session),files).request(actor,version["id"],str(uuid4()))
    process_one(factory,files)
    candidates=detail(context,notice)["versions"][0]["runs"][0]["candidates"]
    confirmed=confirm(context,version,candidates[0])
    changed=BizinfoSnapshot(); changed.data["jsonArray"][0]["reqstBeginEndDe"]="2026-10-01 ~ 2026-10-30"
    second=request_collection(context); process_collection_one(factory,files,changed)
    assert first_record(context,second)["outcome"]=="NEW_VERSION"
    result=detail(context,notice)
    assert result["current_ordinal"]==2 and len(result["versions"])==2
    assert result["versions"][0]["confirmed"][0]["id"]==confirmed["id"]
    assert result["versions"][1]["confirmed"]==[]
    replay=confirm(context,version,candidates[0]); assert replay["historical_replay"] and not replay["current_valid"]
    with pytest.raises(Denied,match="STALE_INPUT_VERSION"): confirm(context,version,candidates[1])


def test_attachment_failure_retains_previous_source_without_spurious_version(context):
    factory,files,_=context
    first=request_collection(context);process_collection_one(factory,files)
    class FailedPDF(BizinfoSnapshot):
        def acquire(self,reference,external):
            if reference["field"]=="flpthNm":raise Denied("SOURCE_NOT_ACQUIRED")
            return super().acquire(reference,external)
    second=request_collection(context);process_collection_one(factory,files,FailedPDF())
    record=first_record(context,second)
    assert collected(context,second)["state"]=="PARTIAL" and record["outcome"]=="UNCHANGED"
    assert record["notice_version_id"]==first_record(context,first)["notice_version_id"]
    assert any(a["status"]=="FAILED" for a in record["acquisitions"])
    notice={"id":record["notice_id"]}
    assert len(detail(context,notice)["versions"])==1
    with factory() as session:
        pdf=next(s for s in SqlNoticeStore(session).rows("sources",version_id=record["notice_version_id"]) if s["name"]=="flpthNm")
        assert files.read(pdf["storage_key"],pdf["digest"]).startswith(b"%PDF-")


def test_missing_source_then_successful_retry_creates_new_input_version(context):
    factory,files,actor=context
    class Missing(BizinfoSnapshot):
        def acquire(self,reference,external):
            if reference["field"]=="flpthNm":raise Denied("SOURCE_NOT_ACQUIRED")
            return super().acquire(reference,external)
    job=request_collection(context);process_collection_one(factory,files,Missing())
    first=first_record(context,job)
    key=str(uuid4())
    with factory.begin() as session:
        app=CollectionApplication(SqlNoticeStore(session),files)
        assert app.retry(actor,job["id"],key)["state"]=="QUEUED"
        assert app.retry(actor,job["id"],key)["historical_replay"]
    process_collection_one(factory,files)
    result=collected(context,job)
    assert [a["state"] for a in result["attempts"]]==["PARTIAL","SUCCEEDED"]
    last=first_record(context,job)
    assert last["notice_id"]==first["notice_id"] and last["notice_version_id"]!=first["notice_version_id"]


def test_page_failure_preserves_first_import_then_retry_deduplicates(context):
    factory,files,actor=context
    class PageFailed(BizinfoSnapshot):
        def page(self,page,unit):
            if page==2:raise Denied("BIZINFO_NETWORK_TIMEOUT")
            return super().page(page,unit)
    job=request_collection(context);process_collection_one(factory,files,PageFailed())
    first=first_record(context,job)
    result=collected(context,job)
    assert result["state"]=="PARTIAL" and result["attempts"][0]["pages"][-1]["state"]=="FAILED"
    with factory.begin() as session:CollectionApplication(SqlNoticeStore(session),files).retry(actor,job["id"],str(uuid4()))
    process_collection_one(factory,files)
    assert first_record(context,job)["notice_id"]==first["notice_id"]
    assert first_record(context,job)["outcome"]=="UNCHANGED"


@pytest.mark.parametrize("variant,expected",[("duplicate","DUPLICATE"),("conflict","CONFLICT"),("invalid","FAILED")])
def test_duplicate_conflicting_and_invalid_items_are_not_silent_overwrites(context,variant,expected):
    factory,files,_=context
    adapter=BizinfoSnapshot(); second=deepcopy(adapter.data["jsonArray"][0])
    if variant=="conflict":second["pblancNm"]="Different conflicting title"
    if variant=="invalid":second.pop("pblancId")
    adapter.data["jsonArray"][0]["totCnt"]=2;second["totCnt"]=2
    adapter.data["jsonArray"].append(second)
    job=request_collection(context);process_collection_one(factory,files,adapter)
    result=collected(context,job)
    assert expected in [r["outcome"] for r in result["attempts"][0]["pages"][0]["records"]]
    with factory() as session:assert len(SqlNoticeStore(session).rows("notices"))==1
    assert result["state"]=="PARTIAL" # Total 2 versus one unique ID or an invalid item.


def test_empty_repeated_page_and_bounded_page_limit(context):
    factory,files,_=context
    empty=BizinfoSnapshot();empty.data["jsonArray"]=[]
    job=request_collection(context);process_collection_one(factory,files,empty)
    assert collected(context,job)["state"]=="SUCCEEDED"
    class Repeated(BizinfoSnapshot):
        def page(self,page,unit):return super().page(1,unit)
    job=request_collection(context);process_collection_one(factory,files,Repeated())
    assert collected(context,job)["error"]=="REPEATED_PAGE_NO_PROGRESS"
    limited=request_collection(context,pages=1);process_collection_one(factory,files)
    assert collected(context,limited)["state"]=="PARTIAL" and collected(context,limited)["error"]=="PAGE_LIMIT_REACHED"


def test_request_permission_idempotency_and_wrong_job_kind(context):
    factory,files,actor=context
    job=request_collection(context,key="same-key")
    assert request_collection(context,key="same-key")["id"]==job["id"]
    with factory.begin() as session:
        service=CollectionApplication(SqlNoticeStore(session),files)
        with pytest.raises(Denied,match="IDEMPOTENCY_TARGET_MISMATCH"):service.request(actor,"LIVE","same-key")
        with pytest.raises(Denied,match="ACTION_NOT_AUTHORIZED"):service.request(Actor(actor.id,"COMPANY_EDITOR"),"SNAPSHOT",str(uuid4()))
        with pytest.raises(Denied,match="JOB_KIND_MISMATCH"):NoticeApplication(SqlNoticeStore(session),files).retry(actor,job["id"])
    assert collected(context,job)["state"]=="QUEUED"


def test_collection_recovery_retains_attempt_and_retries(context):
    factory,files,actor=context
    job=request_collection(context)
    with factory.begin() as session:assert claim(session,lease_seconds=-1,kind="BIZINFO_COLLECTION")
    with factory.begin() as session:
        assert recover_expired(session)==1
        CollectionApplication(SqlNoticeStore(session),files).retry(actor,job["id"],str(uuid4()))
    process_collection_one(factory,files)
    assert [a["state"] for a in collected(context,job)["attempts"]]==["FAILED","SUCCEEDED"]


def test_api_cookie_permission_origin_and_private_raw_boundary(context):
    factory,files,actor=context
    def session_override():
        with factory() as session:yield session
    app.dependency_overrides[get_session]=session_override
    try:
        with TestClient(app) as client:
            headers={"Origin":"http://localhost:3000"}
            body={"mode":"SNAPSHOT","idempotency_key":str(uuid4())}
            assert client.post("/notice/collections",json=body,headers=headers).status_code==401
            with factory() as session:user=SqlNoticeStore(session).get("actors",actor.id)
            assert client.post("/notice/session",json={"username":user["username"],"password":"test-only-local-password"},headers=headers).status_code==200
            assert client.post("/notice/collections",json=body).status_code==403
            assert client.post("/notice/collections",json=dict(body,role="DATCO_OPERATOR"),headers=headers).status_code==422
            response=client.post("/notice/collections",json=body,headers=headers)
            assert response.status_code==200
            job=response.json()
            class Partial(BizinfoSnapshot):
                def page(self,page,unit):
                    if page==2: raise Denied("BIZINFO_NETWORK_TIMEOUT")
                    return super().page(page,unit)
            process_collection_one(factory,files,Partial())
            response=client.get("/notice/collections/"+job["id"])
            assert response.status_code==200 and response.json()["state"]=="PARTIAL"
            assert "raw_key" not in response.text and "storage_key" not in response.text and "normalized" not in response.text
            retry_body={"idempotency_key":str(uuid4())}
            url="/notice/collections/"+job["id"]+"/retry"
            first=client.post(url,json=retry_body,headers=headers)
            replay=client.post(url,json=retry_body,headers=headers)
            assert first.status_code==replay.status_code==200
            assert replay.json()["historical_replay"] and replay.json()["payload"]==first.json()["payload"]
            assert replay.json()["created_at"]==first.json()["created_at"]
            with factory.begin() as session:SqlNoticeStore(session).change("actors",actor.id,role="COMPANY_EDITOR")
            assert client.post("/notice/collections",json=body,headers=headers).status_code==403
            assert client.get("/notice/collections").status_code==403
    finally:app.dependency_overrides.clear()


@pytest.mark.parametrize("payload",[{"jsonArray":{}},{"items":[]},[],None])
def test_wrong_wrapper_is_not_empty_success(payload):
    with pytest.raises(Denied,match="INVALID_BIZINFO_WRAPPER"):parse_page(payload)


def test_live_timeout_retry_invalid_json_secret_and_ssrf_guards():
    class Response(BytesIO):
        status=200
        headers={"Content-Type":"application/json"}
    class Opener:
        def __init__(self,body=b'{"jsonArray":[]}'):self.body=body;self.calls=0
        def open(self,request,timeout):self.calls+=1;return Response(self.body)
    resolver=lambda *args,**kwargs:[(None,None,None,None,("8.8.8.8",443))]
    opener=Opener();client=BizinfoLive(key="fake-test-secret",opener=opener,resolver=resolver)
    assert client.page(1,2)=={"jsonArray":[]} and opener.calls==1
    opener=Opener(b'not-json');client=BizinfoLive(key="fake-test-secret",opener=opener,resolver=resolver)
    with pytest.raises(Denied,match="BIZINFO_INVALID_JSON"):client.page(1,2)
    opener=Opener(b'{"jsonArray":[],"echo":"fake-test-secret"}')
    with pytest.raises(Denied,match="SECRET_REFLECTION_BLOCKED"):BizinfoLive(key="fake-test-secret",opener=opener,resolver=resolver).page(1,2)
    class Timeout(Opener):
        def open(self,request,timeout):self.calls+=1;raise URLError("private authentication URL")
    opener=Timeout()
    with pytest.raises(Denied,match="BIZINFO_NETWORK_TIMEOUT"):BizinfoLive(key="fake-test-secret",opener=opener,resolver=resolver).page(1,2)
    assert opener.calls==2
    for url in ['http://www.bizinfo.go.kr/a','https://127.0.0.1/a','https://evil.example/a','https://www.bizinfo.go.kr:444/a','https://user:pw@www.bizinfo.go.kr/a','https://www.bizinfo.go.kr/a?crtfcKey=value']:
        with pytest.raises(Denied,match="SOURCE_URL_REJECTED"):safe_url(url)
    with pytest.raises(Denied,match="SOURCE_HOST_REJECTED"):
        BizinfoLive(key="fake",opener=Opener(),resolver=lambda *a,**k:[(None,None,None,None,("127.0.0.1",443))]).page(1,2)
    with pytest.raises(Denied,match="SECRET_REFLECTION_BLOCKED"):
        BizinfoLive(key="Case/+",opener=Opener(),resolver=resolver).reject_secrets(b"Case%2f%2b")
    with pytest.raises(Denied,match="DETAIL_ID_OR_FORMAT_MISMATCH"):validate_content(b'<html>other notice</html>',"text/html","PBLN_expected")
    with pytest.raises(Denied,match="SOURCE_NOT_VALID_PDF"):validate_content(b'%PDF-truncated',"application/pdf")


def test_live_status_redirect_size_and_encoded_secret_are_bounded():
    class Response(BytesIO):
        status=200
        headers={"Content-Type":"application/json"}
    resolver=lambda *args,**kwargs:[(None,None,None,None,("8.8.8.8",443))]
    class Status:
        def __init__(self,code):self.code=code;self.calls=0
        def open(self,request,timeout):
            self.calls+=1
            raise HTTPError("private authenticated URL",self.code,"private message",{},None)
    for status,expected_calls in [(302,1),(401,1),(500,2)]:
        opener=Status(status)
        with pytest.raises(Denied,match="BIZINFO_HTTP_"+str(status)):
            BizinfoLive(key="fake",opener=opener,resolver=resolver).page(1,2)
        assert opener.calls==expected_calls
    class Content:
        def __init__(self,content):self.content=content
        def open(self,request,timeout):return Response(self.content)
    with pytest.raises(Denied,match="SOURCE_SIZE_LIMIT"):
        BizinfoLive(key="fake",opener=Content(b'x'*65536),resolver=resolver,max_bytes=100).get("https://www.bizinfo.go.kr/a")
    with pytest.raises(Denied,match="SECRET_REFLECTION_BLOCKED"):
        BizinfoLive(key="sensitive-test",opener=Content(b'{"jsonArray":[],"echo":"sensi\\u0074ive-test"}'),resolver=resolver).page(1,2)


def test_failed_first_page_is_failed_not_partial_and_no_notice_created(context):
    factory,files,_=context
    class Wrong(BizinfoSnapshot):
        def page(self,page,unit):return {"html":"not a Bizinfo JSON wrapper"}
    job=request_collection(context);process_collection_one(factory,files,Wrong())
    result=collected(context,job)
    assert result["state"]=="FAILED" and result["error"]=="INVALID_BIZINFO_WRAPPER"
    assert result["attempts"][0]["pages"][0]["state"]=="FAILED"
    with factory() as session:assert SqlNoticeStore(session).rows("notices")==[]


def test_snapshot_secret_reflection_does_not_persist_raw(context,monkeypatch):
    from app.infrastructure.bizinfo import FIXTURES
    factory,files,_=context
    provider=BizinfoSnapshot();provider.key="private-test-api-key"
    provider.data["jsonArray"][0]["unknown_field"]="private-test-api-key"
    job=request_collection(context);process_collection_one(factory,files,provider)
    assert collected(context,job)["state"]=="FAILED"
    assert not files.root.exists()


def test_changed_pdf_same_url_creates_version_and_preserves_old_file(context):
    from app.demo import FIXTURES
    factory,files,actor=context
    job=request_collection(context);process_collection_one(factory,files)
    first=first_record(context,job)
    with factory() as session:
        source=next(s for s in SqlNoticeStore(session).rows("sources",version_id=first["notice_version_id"]) if s["name"]=="flpthNm")
        original=files.read(source["storage_key"],source["digest"])
    class ChangedPDF(BizinfoSnapshot):
        def acquire(self,reference,external):
            if reference["field"]=="flpthNm":return validate_content((FIXTURES/"conflict.pdf").read_bytes(),"application/octet-stream")
            return super().acquire(reference,external)
    second=request_collection(context);process_collection_one(factory,files,ChangedPDF())
    record=first_record(context,second)
    assert record["outcome"]=="NEW_VERSION" and record["notice_id"]==first["notice_id"]
    assert files.read(source["storage_key"],source["digest"])==original
    with factory.begin() as session:NoticeApplication(SqlNoticeStore(session),files).request(actor,record["notice_version_id"],str(uuid4()))
    process_one(factory,files)
    latest=detail(context,{"id":record["notice_id"]})["versions"][-1]
    assert latest["runs"][0]["conflicts"] and latest["confirmed"]==[]


def test_html_menu_noise_does_not_create_business_version(context):
    factory,files,_=context
    first=request_collection(context);process_collection_one(factory,files)
    class MenuNoise(BizinfoSnapshot):
        def acquire(self,reference,external):
            content,media=super().acquire(reference,external)
            if media=="text/html":content=content.replace(b'</body>',b'<footer>Unrelated dynamic menu 123</footer></body>')
            return content,media
    second=request_collection(context);process_collection_one(factory,files,MenuNoise())
    assert first_record(context,second)["outcome"]=="UNCHANGED"
    assert first_record(context,second)["notice_version_id"]==first_record(context,first)["notice_version_id"]


def test_recovered_old_collection_cannot_publish_over_new_attempt(context):
    from datetime import datetime,timedelta,timezone
    factory,files,actor=context
    job=request_collection(context)
    class Interrupted(BizinfoSnapshot):
        def page(self,page,unit):
            with factory.begin() as session:
                store=SqlNoticeStore(session)
                store.change("jobs",job["id"],lease_until=datetime.now(timezone.utc)-timedelta(seconds=1))
                assert recover_expired(session)==1
                CollectionApplication(store,files).retry(actor,job["id"],str(uuid4()))
            assert process_collection_one(factory,files)
            return super().page(page,unit)
    process_collection_one(factory,files,Interrupted())
    result=collected(context,job)
    assert result["state"]=="SUCCEEDED"
    assert [a["state"] for a in result["attempts"]]==["FAILED","SUCCEEDED"]
    assert result["attempts"][0]["pages"]==[]
    assert len(result["attempts"][1]["pages"])==2
    with factory() as session:assert len(SqlNoticeStore(session).rows("versions"))==1


def test_invalid_reference_field_does_not_mean_previous_source_was_deleted(context):
    factory,files,_=context
    first=request_collection(context);process_collection_one(factory,files)
    adapter=BizinfoSnapshot();adapter.data["jsonArray"][0]["flpthNm"]=123
    second=request_collection(context);process_collection_one(factory,files,adapter)
    record=first_record(context,second)
    assert collected(context,second)["state"]=="PARTIAL" and record["outcome"]=="UNCHANGED"
    assert record["notice_version_id"]==first_record(context,first)["notice_version_id"]
    assert "FIELD_TYPE_INVALID:flpthNm" in record["error"]
    with factory() as session:
        sources=SqlNoticeStore(session).rows("sources",version_id=record["notice_version_id"])
        pdf=next(s for s in sources if s["name"]=="flpthNm")
        assert files.read(pdf["storage_key"],pdf["digest"]).startswith(b"%PDF-")


@pytest.mark.parametrize("field",["flpthNm","printFlpthNm"])
def test_retained_pdf_metadata_survives_content_change_and_recovery(context,field):
    from app.infrastructure.notice_documents import extract_document
    factory,files,actor=context
    provider=BizinfoSnapshot()
    if field=="printFlpthNm":
        item=provider.data["jsonArray"][0]
        item["printFlpthNm"],item["flpthNm"]=item["flpthNm"],""
        item["printFileNm"],item["fileNm"]=item["fileNm"],""
    first=request_collection(context); process_collection_one(factory,files,provider)
    record=first_record(context,first)
    notice={"id":record["notice_id"]}; version={"id":record["notice_version_id"]}
    with factory.begin() as session:
        store=SqlNoticeStore(session)
        original=next(s for s in store.rows("sources",version_id=version["id"]) if s["name"]==field)
        NoticeApplication(store,files).request(actor,version["id"],str(uuid4()))
    assert original["media_type"]=="application/pdf" and original["storage_key"] and original["digest"]
    content=files.read(original["storage_key"],original["digest"])
    assert extract_document(original,content).spans
    assert process_one(factory,files)
    candidate=next(c for c in detail(context,notice)["versions"][0]["runs"][0]["candidates"] if c["kind"]=="REQUIRED_DOCUMENT")
    confirmed=confirm(context,version,candidate)
    previous=deepcopy(detail(context,notice)["versions"][0])

    class FailedPDF(BizinfoSnapshot):
        def acquire(self,reference,external):
            if reference["field"]==field: raise Denied("SOURCE_NOT_ACQUIRED")
            return super().acquire(reference,external)
    failed=FailedPDF(); failed.data=deepcopy(provider.data)
    failed.data["jsonArray"][0]["pblancNm"]+=" changed"
    second=request_collection(context); process_collection_one(factory,files,failed)
    changed=first_record(context,second)
    assert changed["notice_id"]==notice["id"] and changed["outcome"]=="NEW_VERSION"
    assert collected(context,second)["state"]=="PARTIAL"
    acquisition=next(a for a in changed["acquisitions"] if a["field"]==field)
    assert acquisition["status"]=="FAILED" and acquisition["error"]=="SOURCE_NOT_ACQUIRED"
    with factory.begin() as session:
        store=SqlNoticeStore(session)
        retained=next(s for s in store.rows("sources",version_id=changed["notice_version_id"]) if s["name"]==field)
        assert store.get("sources",original["id"])==original
        NoticeApplication(store,files).request(actor,changed["notice_version_id"],str(uuid4()))
    assert retained["id"]!=original["id"] and retained["name"]==original["name"]
    for name in ("storage_key","digest","media_type"): assert retained[name]==original[name]
    provenance=json.loads(retained["provenance"])
    assert provenance["retained_previous_file"] is True
    assert provenance["status"]=="FAILED" and provenance["error"]=="SOURCE_NOT_ACQUIRED"
    assert files.read(retained["storage_key"],retained["digest"])==content
    assert extract_document(retained,content).spans
    assert process_one(factory,files)
    latest=detail(context,notice)["versions"][-1]
    assert latest["jobs"][-1]["state"]=="SUCCEEDED" and latest["runs"][-1]["missing"]==[]
    assert any(c["kind"]=="REQUIRED_DOCUMENT" and c["evidence"]["source_id"]==retained["id"] for c in latest["runs"][-1]["candidates"])
    assert latest["confirmed"]==[]

    recovered=BizinfoSnapshot(); recovered.data=deepcopy(failed.data)
    third=request_collection(context); process_collection_one(factory,files,recovered)
    recovery=first_record(context,third)
    assert collected(context,third)["state"]=="SUCCEEDED" and recovery["outcome"]=="UNCHANGED"
    assert recovery["notice_version_id"]==changed["notice_version_id"]
    assert next(a for a in recovery["acquisitions"] if a["field"]==field)["status"]=="ACQUIRED"
    result=detail(context,notice)
    assert len(result["versions"])==2
    old=result["versions"][0]
    assert old["confirmed"][0]["id"]==confirmed["id"]
    for name in ("metadata","sources","runs"): assert old[name]==previous[name]
    assert old["confirmed"][0]["review"]==previous["confirmed"][0]["review"]
    assert old["confirmed"][0]["items"]==previous["confirmed"][0]["items"]
    with factory() as session:
        current=SqlNoticeStore(session).get("sources",retained["id"])
        assert current==retained
        assert extract_document(current,files.read(current["storage_key"],current["digest"])).spans


def test_unacquired_previous_reference_is_not_a_verified_retained_pdf(context):
    factory,files,_=context
    class MissingPDF(BizinfoSnapshot):
        def acquire(self,reference,external):
            if reference["field"]=="flpthNm": raise Denied("SOURCE_NOT_ACQUIRED")
            return super().acquire(reference,external)
    provider=MissingPDF()
    first=request_collection(context); process_collection_one(factory,files,provider)
    initial=first_record(context,first)
    provider.data["jsonArray"][0]["pblancNm"]+=" changed"
    second=request_collection(context); process_collection_one(factory,files,provider)
    changed=first_record(context,second)
    assert changed["outcome"]=="NEW_VERSION" and changed["notice_id"]==initial["notice_id"]
    assert collected(context,first)["state"]==collected(context,second)["state"]=="PARTIAL"
    with factory() as session:
        store=SqlNoticeStore(session)
        for version_id in (initial["notice_version_id"],changed["notice_version_id"]):
            source=next(s for s in store.rows("sources",version_id=version_id) if s["name"]=="flpthNm")
            assert source["storage_key"] is None and source["digest"] is None
            assert source["media_type"]=="application/octet-stream"
            provenance=json.loads(source["provenance"])
            assert provenance["status"]=="FAILED" and provenance["error"]=="SOURCE_NOT_ACQUIRED"
            assert not provenance.get("retained_previous_file",False)
