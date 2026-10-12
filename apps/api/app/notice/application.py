import json
from hashlib import sha256
from app.notice.domain import Actor, Denied, authorize, FileProvider, AnalysisProvider, NoticeStore

class NoticeApplication:
    def __init__(self, store: NoticeStore, files: FileProvider):
        self.store, self.files = store, files

    def audit(self,actor,action,version=None,job=None,review=None,source=None,reason=""):
        self.store.add("audits",actor_id=actor.id if actor else None,action=action,
            notice_version_id=version,job_id=job,review_id=review,source_id=source,reason=reason)

    def version(self,version_id,lock=False):
        version=self.store.get("versions",version_id)
        notice=self.store.get("notices",version["notice_id"],lock)
        if notice["current_ordinal"] != version["ordinal"]:
            raise Denied("STALE_INPUT_VERSION")
        return version

    def replay_result(self,result,version_id,replay=False):
        if version_id is None:
            return dict(result,historical_replay=replay,current_valid=True)
        version=self.store.get("versions",version_id)
        notice=self.store.get("notices",version["notice_id"])
        current_valid=notice["current_ordinal"]==version["ordinal"]
        if "requirement_id" in result:
            history=self.store.rows("requirement_versions",requirement_id=result["requirement_id"])
            current_valid=current_valid and result["ordinal"]==max(v["ordinal"] for v in history)
        return dict(result,historical_replay=replay,current_valid=current_valid)

    def request(self,actor,version_id,key):
        authorize(actor)
        # Serialize requests for this input without applying the current-version guard yet.
        version=self.store.get("versions",version_id)
        self.store.get("notices",version["notice_id"],True)
        previous=self.store.rows("jobs",actor_id=actor.id,request_key=key)
        if previous:
            if previous[0]["version_id"]!=version_id:
                raise Denied("IDEMPOTENCY_TARGET_MISMATCH")
            return self.replay_result(previous[0],version_id,True)
        self.version(version_id)
        if not self.store.rows("sources",version_id=version_id):
            raise Denied("REQUIRED_DATA_MISSING")
        job=self.store.add("jobs",version_id=version_id,actor_id=actor.id,
            request_key=key,state="QUEUED",error=None,lease_until=None)
        self.audit(actor,"REQUEST_NOTICE_REVIEW",version_id,job["id"])
        return job

    def retry(self,actor,job_id,key=None,kind="NOTICE_ANALYSIS"):
        authorize(actor)
        job=self.store.get("jobs",job_id,True)
        if job["kind"]!=kind: raise Denied("JOB_KIND_MISMATCH")
        # Direct local callers retain an attempt-specific identity; HTTP callers supply a key.
        key=key or f"{job_id}:{len(self.store.rows('attempts',job_id=job_id))}"
        fingerprint=sha256(key.encode()).hexdigest()
        for audit in self.store.rows("audits",actor_id=actor.id,action="RETRY_JOB"):
            try:
                saved=json.loads(audit["reason"])
            except (ValueError,TypeError):
                continue
            if isinstance(saved,dict) and saved.get("request_key_hash")==fingerprint:
                if audit["job_id"]!=job_id:
                    raise Denied("IDEMPOTENCY_TARGET_MISMATCH")
                return self.replay_result(saved["result"],job["version_id"],True)
        if job["version_id"] is not None: self.version(job["version_id"])
        if job["state"] not in ("FAILED","PARTIAL"):
            raise Denied("TRANSITION_NOT_ALLOWED")
        self.store.change("jobs",job_id,state="QUEUED",error=None,lease_until=None)
        result=self.store.get("jobs",job_id)
        receipt={field:result[field] for field in ("id","version_id","state","error")}
        self.audit(actor,"RETRY_JOB",job["version_id"],job_id,
            reason=json.dumps({"request_key_hash":fingerprint,"result":receipt},sort_keys=True))
        return self.replay_result(result,job["version_id"])

    def confirm(self,actor,version_id,candidate_id,official_verified,note,scope,conflict_resolution):
        authorize(actor)
        version=self.store.get("versions",version_id)
        self.store.get("notices",version["notice_id"],True)
        candidate=self.store.get("candidates",candidate_id)
        run=self.store.get("runs",candidate["run_id"])
        if run["version_id"]!=version_id:
            raise Denied("TARGET_VERSION_MISMATCH")
        fingerprint=sha256(json.dumps([actor.id,version_id,candidate_id,official_verified,
            note,scope,conflict_resolution],ensure_ascii=True,separators=(",",":")).encode()).hexdigest()
        reviewed=self.store.rows("reviews",candidate_id=candidate_id)
        if reviewed:
            review=reviewed[0]
            if review["outcome"]!="CONFIRM":
                raise Denied("TRANSITION_NOT_ALLOWED")
            result=self.store.rows("requirement_versions",review_id=review["id"])[0]
            audits=self.store.rows("audits",review_id=review["id"],action="CONFIRM_NOTICE_REQUIREMENT")
            try:
                saved=json.loads(audits[0]["reason"])
                recorded=saved.get("request_fingerprint") if isinstance(saved,dict) else None
            except (ValueError,TypeError,IndexError):
                recorded=None
            legacy_match=(review["actor_id"]==actor.id and official_verified and
                review["note"]==note+"\n"+conflict_resolution and
                result["scope"]==scope+(" [Partial sources; only reviewed items confirmed]" if run["missing"] else ""))
            if (recorded is not None and recorded!=fingerprint) or (recorded is None and not legacy_match):
                raise Denied("IDEMPOTENCY_TARGET_MISMATCH")
            return self.replay_result(result,version_id,True)
        self.version(version_id)
        location=self.store.get("locations",candidate["location_id"])
        source=self.store.get("sources",location["source_id"])
        if location["run_id"]!=run["id"] or source["version_id"]!=version_id:
            raise Denied("REQUIRED_EVIDENCE_MISSING")
        if not source["storage_key"] or not location["text"].strip() or candidate["content"] not in location["text"]:
            raise Denied("REQUIRED_EVIDENCE_MISSING")
        self.files.verify_location(source,location)
        if not official_verified:
            raise Denied("OFFICIAL_SOURCE_NOT_VERIFIED")
        if not note.strip() or not scope.strip():
            raise Denied("REQUIRED_DATA_MISSING")
        if run["conflicts"] and not conflict_resolution.strip():
            raise Denied("MISSING_REQUIRED_INFORMATION")
        # Explicit scoped confirmation never declares partial input complete.
        roots=self.store.rows("requirements",notice_id=version["notice_id"])
        root=roots[0] if roots else self.store.add("requirements",notice_id=version["notice_id"])
        history=self.store.rows("requirement_versions",requirement_id=root["id"])
        review=self.store.add("reviews",candidate_id=candidate_id,actor_id=actor.id,outcome="CONFIRM",
            official_verified=True,note=note+"\n"+conflict_resolution)
        result=self.store.add("requirement_versions",requirement_id=root["id"],notice_version_id=version_id,
            review_id=review["id"],ordinal=max([v["ordinal"] for v in history],default=0)+1,
            scope=scope+(" [Partial sources; only reviewed items confirmed]" if run["missing"] else ""))
        current_history=[v for v in history if v["notice_version_id"]==version_id]
        if current_history:
            previous=max(current_history,key=lambda v:v["ordinal"])
            for item in self.store.rows("items",version_id=previous["id"]):
                # Period is a single chosen value; other labelled clauses may be multi-valued.
                if item["kind"]==candidate["kind"] and (candidate["kind"]=="APPLICATION_PERIOD" or item["content"]==candidate["content"]):
                    continue
                self.store.add("items",version_id=result["id"],candidate_id=item["candidate_id"],
                    location_id=item["location_id"],kind=item["kind"],content=item["content"])
        self.store.add("items",version_id=result["id"],candidate_id=candidate_id,
            location_id=location["id"],kind=candidate["kind"],content=candidate["content"])
        self.audit(actor,"CONFIRM_NOTICE_REQUIREMENT",version_id,review=review["id"],reason=json.dumps({"note":note,"request_fingerprint":fingerprint},sort_keys=True))
        return self.replay_result(result,version_id)

    def more_source(self,actor,version_id,candidate_id,note):
        authorize(actor)
        self.version(version_id,True)
        candidate=self.store.get("candidates",candidate_id)
        run=self.store.get("runs",candidate["run_id"])
        if run["version_id"]!=version_id or not note.strip():
            raise Denied("TARGET_VERSION_MISMATCH")
        if self.store.rows("reviews",candidate_id=candidate_id):
            raise Denied("TRANSITION_NOT_ALLOWED")
        review=self.store.add("reviews",candidate_id=candidate_id,actor_id=actor.id,
            outcome="REQUEST_MORE_INFORMATION",official_verified=False,note=note)
        self.audit(actor,"REQUEST_MORE_SOURCE_REVIEW",version_id,review=review["id"],reason=note)
        return review

    def detail(self,actor,notice_id):
        authorize(actor)
        notice=self.store.get("notices",notice_id)
        versions=self.store.rows("versions",notice_id=notice_id)
        output=[]
        for version in sorted(versions,key=lambda v:v["ordinal"]):
            sources=self.store.rows("sources",version_id=version["id"])
            public_sources=[{k:v for k,v in source.items() if k not in ("storage_key","digest")} for source in sources]
            jobs=self.store.rows("jobs",version_id=version["id"])
            run_results=[]
            for run in self.store.rows("runs",version_id=version["id"]):
                proposed=[]
                for candidate in self.store.rows("candidates",run_id=run["id"]):
                    location=self.store.get("locations",candidate["location_id"])
                    proposed.append(dict(candidate,evidence=location,reviews=self.store.rows("reviews",candidate_id=candidate["id"])))
                run_results.append(dict(run,candidates=proposed))
            confirmed=[]
            for rv in self.store.rows("requirement_versions",notice_version_id=version["id"]):
                review=self.store.get("reviews",rv["review_id"])
                confirmed.append(dict(self.replay_result(rv,version["id"]),review=review,items=self.store.rows("items",version_id=rv["id"])))
            output.append(dict(version,sources=public_sources,jobs=[dict(self.replay_result(j,version["id"]),attempts=sorted(self.store.rows("attempts",job_id=j["id"]),key=lambda a:a["ordinal"])) for j in jobs],
                runs=run_results,confirmed=sorted(confirmed,key=lambda v:v["ordinal"])))
        return dict(notice,versions=output)

    def download(self,actor,source_id):
        authorize(actor)
        source=self.store.get("sources",source_id)
        if not source["storage_key"]:
            raise Denied("SOURCE_NOT_ACQUIRED",404)
        content=self.files.read(source["storage_key"],source["digest"])
        self.audit(actor,"DOWNLOAD_NOTICE_SOURCE",version=source["version_id"],source=source_id)
        return source,content


    def import_collected(self,source_system,normalized,mode,acquired,raw_reference,collected_at):
        # Notice owns root identity, immutable version composition and current selection.
        key=source_system+":"+normalized.external_id
        self.store.lock_identity(key)
        roots=self.store.rows("notices",external_key=key)
        previous=None; prior_sources=[]
        if roots:
            notice=self.store.get("notices",roots[0]["id"],True)
            previous=next(v for v in self.store.rows("versions",notice_id=notice["id"]) if v["ordinal"]==notice["current_ordinal"])
            prior_sources=self.store.rows("sources",version_id=previous["id"])
        else:
            notice=self.store.add("notices",external_key=key,title=normalized.title or "Notice "+normalized.external_id+" (title missing)",current_ordinal=1)
        old_core=previous["metadata"].get("comparison",{}) if previous else {}
        core=dict(old_core,**normalized.core)
        old_comparisons=previous["metadata"].get("source_comparisons",{}) if previous else {}
        comparisons={}; source_rows=[]; warnings=[]
        for incoming in acquired:
            item=dict(incoming)
            field=item["field"]
            if not item["url"]: continue
            old=next((r for r in prior_sources if r["name"]==field),None)
            old_url=old_comparisons.get(field,{}).get("url")
            if not item.get("digest") and old and old_url==item["url"] and old["storage_key"] and old["digest"]:
                # Retain the validated file metadata without changing this acquisition's failure status.
                item["storage_key"],item["digest"]=old["storage_key"],old["digest"]
                item["media_type"]=old["media_type"]
                item["comparison_digest"]=old_comparisons.get(field,{}).get("digest")
                item["retained_previous_file"]=True
            comparison_digest=item.get("comparison_digest")
            if item["media_type"]=="text/html" and comparison_digest is None and old and old_url==item["url"]:
                if item.get("digest") and item["digest"]!=old["digest"]:
                    warnings.append("DETAIL_CHANGE_REQUIRES_REVIEW")
                comparison_digest=old_comparisons.get(field,{}).get("digest")
            comparisons[field]={"url":item["url"],"digest":comparison_digest}
            source_rows.append(item)
        # Missing/invalid fields do not mean an explicit reference deletion.
        for field,comparison in old_comparisons.items():
            if field not in comparisons and field in normalized.metadata["missing_fields"]:
                comparisons[field]=comparison
                old=next(r for r in prior_sources if r["name"]==field)
                source_rows.append({"field":field,"url":comparison["url"],"media_type":old["media_type"],
                    "storage_key":old["storage_key"],"digest":old["digest"],"status":"RETAINED_UNOBSERVED"})
        if previous and core==old_core and comparisons==old_comparisons:
            self.audit(None,"KEEP_EXISTING_VERSION",previous["id"],reason="Same normalized content and available source comparison; no automatic confirmation")
            return notice,previous,"UNCHANGED",warnings
        ordinal=notice["current_ordinal"]+1 if previous else 1
        metadata=dict(normalized.metadata,**core,comparison=core,source_comparisons=comparisons,
            input_mode=mode,raw_reference=raw_reference,collected_at=collected_at,
            acquisition_warnings=warnings,previous_version_id=previous["id"] if previous else None)
        version=self.store.add("versions",notice_id=notice["id"],ordinal=ordinal,
            mode="LIVE" if mode=="LIVE" else "SANITIZED_SNAPSHOT",metadata=metadata)
        for item in source_rows:
            provenance={k:v for k,v in item.items() if k not in ("storage_key","digest")}
            provenance.update(source_system=source_system,input_mode=mode,collected_at=collected_at,content_hash=item.get("digest"))
            self.store.add("sources",version_id=version["id"],name=item["field"],media_type=item["media_type"],
                provenance=json.dumps(provenance,ensure_ascii=True,sort_keys=True),storage_key=item.get("storage_key"),digest=item.get("digest"))
        self.store.change("notices",notice["id"],current_ordinal=ordinal,title=core.get("title") or notice["title"])
        self.audit(None,"CREATE_NOTICE_VERSION" if previous else "IMPORT_NEW_NOTICE",version["id"],
            reason=source_system+" normalized content/source change; analysis and human review required")
        return self.store.get("notices",notice["id"]),version,"NEW_VERSION" if previous else "NEW",warnings
