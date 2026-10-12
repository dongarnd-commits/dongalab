from datetime import datetime,timezone
from hashlib import sha256
import json,time
from app.core.config import ROOT
from app.infrastructure import collector_schema
from app.infrastructure.database import get_session_factory
from app.infrastructure.notice_store import SqlNoticeStore
from app.infrastructure.notice_queue import claim
from app.infrastructure.notice_documents import LocalPrivateFiles,extract,DeterministicAnalysis
from app.infrastructure.bizinfo import BizinfoLive,BizinfoSnapshot
from app.collector.normalizer import parse_page,normalize,VERSION
from app.notice.application import NoticeApplication
from app.notice.domain import Denied

def fenced(store,job,attempt):
    current=store.get("jobs",job["id"],True)
    execution=store.get("attempts",attempt["id"])
    if current["state"]!="PROCESSING" or execution["state"]!="PROCESSING" or current["lease_until"]<=datetime.now(timezone.utc):
        raise Denied("EXECUTION_NO_LONGER_OWNED")

def process_collection_one(factory=None,files=None,provider=None):
    factory=factory or get_session_factory()
    files=files or LocalPrivateFiles(ROOT/"storage/private/notice")
    with factory.begin() as session: claimed=claim(session,kind="BIZINFO_COLLECTION")
    if not claimed: return False
    job,attempt=claimed; options=job["payload"]
    successes=0; issue=False; error=None; seen={}; imported={}; expected=None; observed=0; empty=False
    deadline=time.monotonic()+120
    try:
        with factory() as session:
            if SqlNoticeStore(session).get("actors",job["actor_id"])["role"]!="DATCO_OPERATOR": raise Denied("ACTION_NOT_AUTHORIZED")
        provider=provider or (BizinfoLive() if options["mode"]=="LIVE" else BizinfoSnapshot())
        for number in range(1,options["max_pages"]+1):
            if time.monotonic()>=deadline: raise Denied("COLLECTION_TIME_LIMIT")
            try:
                payload=provider.page(number,options["page_unit"])
                items=parse_page(payload)
                if len(items)>options["page_unit"]: raise Denied("PAGE_SIZE_MISMATCH")
                raw=json.dumps(payload,ensure_ascii=True,sort_keys=True).encode()
                # Input adapters must reject secrets before private Raw persistence.
                if hasattr(provider,"reject_secrets"): provider.reject_secrets(raw)
                raw_key,raw_digest=files.put(raw)
            except Denied as exc:
                with factory.begin() as session:
                    store=SqlNoticeStore(session); fenced(store,job,attempt)
                    store.add("collection_pages",attempt_id=attempt["id"],page_number=number,state="FAILED",error=exc.reason,
                        observed_count=0,expected_total=None,warnings=[])
                raise
            totals=[i.get("totCnt") for i in items if isinstance(i,dict)]
            valid=[n for n in totals if isinstance(n,int) and not isinstance(n,bool) and n>=0]
            warnings=[]
            if items and (len(valid)!=len(totals) or len(set(valid))!=1): warnings.append("TOTAL_COUNT_UNCERTAIN")
            total=valid[0] if valid else None
            if total is not None:
                if expected is not None and expected!=total: warnings.append("TOTAL_COUNT_CHANGED")
                expected=total
            observed+=len(items)
            if len(items)<options["page_unit"] and items: warnings.append("SHORT_PAGE_OBSERVED")
            if not items and expected is not None and len(seen)!=expected: warnings.append("UNIQUE_COUNT_MISMATCH")
            with factory.begin() as session:
                store=SqlNoticeStore(session); fenced(store,job,attempt)
                page=store.add("collection_pages",attempt_id=attempt["id"],page_number=number,state="SUCCEEDED",error=None,
                    raw_key=raw_key,raw_digest=raw_digest,observed_count=len(items),expected_total=total,warnings=warnings)
            issue=issue or any(w!="SHORT_PAGE_OBSERVED" for w in warnings)
            if not items: empty=True; break
            new_ids=0
            for position,item in enumerate(items):
                if time.monotonic()>=deadline: raise Denied("COLLECTION_TIME_LIMIT")
                acquired=[]; notice=None; version=None; outcome="FAILED"; item_error=None; normalized=None
                try:
                    normalized=normalize(item)
                    fingerprint=sha256(json.dumps(normalized.core,sort_keys=True,ensure_ascii=True).encode()).hexdigest()
                    if normalized.external_id in seen:
                        outcome="DUPLICATE" if seen[normalized.external_id]==fingerprint else "CONFLICT"
                        if outcome=="CONFLICT": item_error="DUPLICATE_ID_CONTENT_CONFLICT"; issue=True
                        if normalized.external_id in imported: notice,version=imported[normalized.external_id]
                    else:
                        seen[normalized.external_id]=fingerprint; new_ids+=1
                        for reference in normalized.references:
                            entry=dict(reference,input_origin=provider.origin,status="FAILED",error=None,storage_key=None,digest=None,comparison_digest=None)
                            if not reference["url"]:
                                entry["status"]="NOT_PROVIDED"; acquired.append(entry); continue
                            try:
                                content,media=provider.acquire(reference,normalized.external_id)
                                if hasattr(provider,"reject_secrets"): provider.reject_secrets(content)
                                key,digest=files.put(content)
                                entry.update(storage_key=key,digest=digest,media_type=media,status="ACQUIRED",content_hash=digest)
                                if media=="application/pdf": entry["comparison_digest"]=digest
                                else:
                                    lines=[span.text for span in extract({"id":"comparison","media_type":media},content)
                                        if any(span.text.startswith(prefix) for prefix in DeterministicAnalysis.prefixes)]
                                    entry["comparison_digest"]=sha256(json.dumps(lines).encode()).hexdigest() if lines else None
                                    entry["comparison_scope"]="LABELLED_CLAUSES_ONLY; general portal body completeness unverified"
                            except Denied as exc:
                                entry["error"]=exc.reason; issue=True
                            acquired.append(entry)
                        collected=datetime.now(timezone.utc).isoformat()
                        with factory.begin() as session:
                            store=SqlNoticeStore(session); fenced(store,job,attempt)
                            notice,version,outcome,import_warnings=NoticeApplication(store,files).import_collected(
                                "BIZINFO",normalized,options["mode"],acquired,{"page_id":page["id"],"position":position},collected)
                            item_warnings=normalized.warnings+import_warnings
                            item_error=";".join(item_warnings) or None
                            # Persist import and its typed lineage atomically.
                            store.add("collection_records",page_id=page["id"],position=position,external_id=normalized.external_id,
                                notice_id=notice["id"],notice_version_id=version["id"],outcome=outcome,error=item_error,
                                normalized=dict(normalized.metadata,comparison=normalized.core),acquisitions=acquired)
                        imported[normalized.external_id]=(notice,version)
                        issue=issue or bool(item_warnings); successes+=1
                        continue
                except Denied as exc: item_error=exc.reason; issue=True
                with factory.begin() as session:
                    store=SqlNoticeStore(session); fenced(store,job,attempt)
                    store.add("collection_records",page_id=page["id"],position=position,
                        external_id=normalized.external_id if normalized else None,notice_id=notice["id"] if notice else None,
                        notice_version_id=version["id"] if version else None,
                        outcome=outcome,error=item_error,normalized={},acquisitions=acquired)
            if new_ids==0: issue=True; error="REPEATED_PAGE_NO_PROGRESS"; break
        if not empty and not error: issue=True; error="PAGE_LIMIT_REACHED"
        state="PARTIAL" if issue else "SUCCEEDED"
        if not successes and observed: state="FAILED"; error=error or "NO_NOTICE_IMPORTED"
    except Exception as exc:
        error=exc.reason if isinstance(exc,Denied) else "COLLECTION_FAILED"
        state="PARTIAL" if successes else "FAILED"
    with factory.begin() as session:
        store=SqlNoticeStore(session)
        try: fenced(store,job,attempt)
        except Denied: return True
        store.change("attempts",attempt["id"],state=state,error=error)
        store.change("jobs",job["id"],state=state,error=error,lease_until=None)
        store.add("audits",actor_id=None,job_id=job["id"],action="COMPLETE_COLLECTION" if state!="FAILED" else "FAIL_COLLECTION",reason=error or state)
    return True
