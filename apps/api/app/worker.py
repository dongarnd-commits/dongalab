import argparse
from importlib.metadata import version as package_version
import time
from datetime import datetime, timezone
from app.core.config import ROOT
from app.infrastructure.database import get_session_factory
from app.infrastructure.notice_store import SqlNoticeStore
from app.infrastructure.notice_queue import claim,recover_expired
from app.infrastructure.notice_documents import LocalPrivateFiles,extract_document,DeterministicAnalysis
from app.notice.application import NoticeApplication
from app.notice.domain import Denied

def process_one(factory=None,files=None,provider=None):
    factory=factory or get_session_factory()
    files=files or LocalPrivateFiles(ROOT/"storage/private/notice")
    provider=provider or DeterministicAnalysis()
    with factory.begin() as session:
        claimed=claim(session)
    if not claimed:
        return False
    job,attempt=claimed
    spans=[]; missing=[]; outputs=[]; conflicts=[]
    try:
        with factory() as session:
            store=SqlNoticeStore(session)
            actor=store.get("actors",job["actor_id"])
            application=NoticeApplication(store,files)
            version=application.version(job["version_id"])
            if actor["role"]!="DATCO_OPERATOR":
                raise Denied("ACTION_NOT_AUTHORIZED")
            sources=store.rows("sources",version_id=job["version_id"])
        # Binary IO, extraction and analysis run outside a DB transaction.
        for source in sources:
            try:
                if not source["storage_key"]:
                    raise Denied("SOURCE_NOT_ACQUIRED")
                extracted=extract_document(source,files.read(source["storage_key"],source["digest"]))
                if extracted.limitation:
                    missing.append({"source_id":source["id"],"reason":"PARTIAL_PAGE_EXTRACTION",
                        "total_pages":extracted.total_pages,"extracted_pages":list(extracted.extracted_pages),
                        "unextractable_pages":list(extracted.unextractable_pages),"limitation":extracted.limitation})
                elif not extracted.spans:
                    raise Denied("SOURCE_NEEDS_MANUAL_REVIEW")
                spans.extend(extracted.spans)
            except Exception:
                missing.append({"source_id":source["id"],"reason":"SOURCE_MISSING_OR_UNREADABLE"})
        outputs=provider.analyze(spans)
        if not outputs:
            raise Denied("NO_VALID_REQUIREMENT_CANDIDATE")
        for output in outputs:
            if output.kind not in {"ELIGIBILITY_REQUIREMENT","SUPPORT_SCOPE","APPLICATION_PERIOD","REQUIRED_DOCUMENT","EVALUATION_CRITERION","FORM_FIELD","PLAN_SECTION","CONDITIONAL_REQUIREMENT"} or output.span not in spans or not output.content.strip() or output.content not in output.span.text or not output.reason.strip():
                raise Denied("INVALID_ANALYSIS_OUTPUT")
        periods=[o for o in outputs if o.kind=="APPLICATION_PERIOD"]
        metadata_period=version["metadata"].get("period_original")
        values={o.content for o in periods}
        if metadata_period:
            values.add(metadata_period)
        if periods and len(values)>1:
            evidence=[{"source_type":"DOCUMENT","source_id":o.span.source_id,"value":o.content,
                "page":o.span.page,"descriptor":o.span.descriptor,"text":o.span.text} for o in periods]
            if metadata_period:
                evidence.append({"source_type":"NOTICE_METADATA","notice_version_id":version["id"],
                    "field":"period_original","value":metadata_period})
            conflicts.append({"kind":"APPLICATION_PERIOD","values":sorted(values),"evidence":evidence})
        state="PARTIAL" if missing else "SUCCEEDED"
        error=None
    except Exception as exc:
        state="FAILED"
        error=exc.reason if isinstance(exc,Denied) else "ANALYSIS_FAILED"
    with factory.begin() as session:
        store=SqlNoticeStore(session)
        current_job=store.get("jobs",job["id"],True)
        current_attempt=store.get("attempts",attempt["id"])
        # Fencing prevents a recovered/retried old execution from publishing.
        if current_job["state"]!="PROCESSING" or current_attempt["state"]!="PROCESSING" or current_job["lease_until"]<=datetime.now(timezone.utc):
            return True
        if state!="FAILED":
            try:
                NoticeApplication(store,files).version(job["version_id"],True)
            except Denied:
                state,error="FAILED","STALE_INPUT_VERSION"
        if state!="FAILED":
            run=store.add("runs",attempt_id=attempt["id"],version_id=job["version_id"],
                provider_version=provider.version,extractor_version="html-blocks-v1/pypdf-"+package_version("pypdf"),
                missing=missing,conflicts=conflicts)
            for output in outputs:
                location=store.add("locations",run_id=run["id"],source_id=output.span.source_id,
                    page=output.span.page,descriptor=output.span.descriptor,text=output.span.text)
                store.add("candidates",run_id=run["id"],location_id=location["id"],
                    kind=output.kind,content=output.content,reason=output.reason)
        store.change("attempts",attempt["id"],state=state,error=error)
        store.change("jobs",job["id"],state=state,error=error,lease_until=None)
        store.add("audits",actor_id=None,notice_version_id=job["version_id"],job_id=job["id"],
            action="FAIL_JOB" if state=="FAILED" else "COMPLETE_JOB",reason=error or state)
    return True

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--once",action="store_true")
    parser.add_argument("--recover-expired",action="store_true")
    args=parser.parse_args()
    if args.recover_expired:
        with get_session_factory().begin() as session:
            print("Recovered expired jobs:",recover_expired(session))
        return
    from app.collector.worker import process_collection_one
    while True:
        process_collection_one()
        process_one()
        if args.once:
            return
        time.sleep(1)

if __name__=="__main__":
    main()
