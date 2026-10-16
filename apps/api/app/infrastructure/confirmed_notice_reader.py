"""Read-only consumer of existing Human-confirmed Notice requirements."""
from app.notice.domain import Actor, Denied, NoticeStore, FileProvider, authorize

class ConfirmedNoticeReader:
    def __init__(self, store: NoticeStore, files: FileProvider):
        self.store,self.files=store,files

    def read(self, actor: Actor, notice_id: str, requirement_version_id: str) -> dict:
        authorize(actor)
        notice=self.store.get("notices",notice_id)
        rv=self.store.get("requirement_versions",requirement_version_id)
        root=self.store.get("requirements",rv["requirement_id"])
        version=self.store.get("versions",rv["notice_version_id"])
        if root["notice_id"]!=notice_id or version["notice_id"]!=notice_id:
            raise Denied("TARGET_VERSION_MISMATCH")
        history=self.store.rows("requirement_versions",requirement_id=root["id"])
        if version["ordinal"]!=notice["current_ordinal"] or rv["ordinal"]!=max(v["ordinal"] for v in history):
            raise Denied("STALE_INPUT_VERSION")
        def verified(candidate_id):
            reviews=self.store.rows("reviews",candidate_id=candidate_id)
            if len(reviews)!=1 or reviews[0]["outcome"]!="CONFIRM" or not reviews[0]["official_verified"]:
                raise Denied("OFFICIAL_SOURCE_NOT_VERIFIED")
            return reviews[0]
        main_review=self.store.get("reviews",rv["review_id"])
        if verified(main_review["candidate_id"])["id"]!=main_review["id"]:
            raise Denied("REQUIRED_EVIDENCE_MISSING")
        items=self.store.rows("items",version_id=rv["id"])
        if not items:
            raise Denied("REQUIRED_DATA_MISSING")
        output=[]; run_ids=set()
        for item in items:
            candidate=self.store.get("candidates",item["candidate_id"])
            review=verified(candidate["id"])
            location=self.store.get("locations",item["location_id"])
            source=self.store.get("sources",location["source_id"])
            run=self.store.get("runs",candidate["run_id"])
            if (candidate["location_id"]!=location["id"] or location["run_id"]!=run["id"] or
                run["version_id"]!=version["id"] or source["version_id"]!=version["id"] or
                candidate["kind"]!=item["kind"] or candidate["content"]!=item["content"] or
                not item["content"].strip() or item["content"] not in location["text"] or
                not source["storage_key"]):
                raise Denied("REQUIRED_EVIDENCE_MISSING")
            self.files.verify_location(source,location)
            run_ids.add(run["id"])
            output.append({"id":item["id"],"kind":item["kind"],"content":item["content"],
                "candidate_id":candidate["id"],"review":review,"evidence":location})
        runs=[self.store.get("runs",identity) for identity in sorted(run_ids)]
        return {"notice_id":notice_id,"notice_version_id":version["id"],
            "requirement_version_id":rv["id"],"ordinal":rv["ordinal"],"scope":rv["scope"],
            "current_valid":True,"review":main_review,"items":output,
            "limitations":[{"run_id":r["id"],"missing":r["missing"],"conflicts":r["conflicts"]} for r in runs]}
