from app.notice.domain import authorize,Denied
from app.notice.application import NoticeApplication

class CollectionApplication:
    def __init__(self,store,files):
        self.store,self.files=store,files
    def request(self,actor,mode,key,page_unit=2,max_pages=3):
        authorize(actor)
        if mode not in ("LIVE","SNAPSHOT") or not 1<=page_unit<=5 or not 1<=max_pages<=5:
            raise Denied("INVALID_COLLECTION_REQUEST",422)
        self.store.lock_identity("collection-request:"+actor.id+":"+key)
        payload={"source_system":"BIZINFO","mode":mode,"page_unit":page_unit,"max_pages":max_pages,"searchCnt":0,
            "snapshot_id":"synthetic-demo-v1" if mode=="SNAPSHOT" else None,
            "input_origin":"SANITIZED_SYNTHETIC_DEMO_V1" if mode=="SNAPSHOT" else "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"}
        previous=self.store.rows("jobs",actor_id=actor.id,request_key=key)
        if previous:
            if previous[0]["kind"]!="BIZINFO_COLLECTION" or previous[0]["payload"]!=payload: raise Denied("IDEMPOTENCY_TARGET_MISMATCH")
            return dict(previous[0],historical_replay=True,current_valid=True)
        job=self.store.add("jobs",version_id=None,actor_id=actor.id,request_key=key,kind="BIZINFO_COLLECTION",payload=payload,
            state="QUEUED",error=None,lease_until=None)
        NoticeApplication(self.store,self.files).audit(actor,"REQUEST_COLLECTION",job=job["id"],reason=mode+" BIZINFO bounded manual collection")
        return job
    def retry(self,actor,job_id,key):
        receipt=NoticeApplication(self.store,self.files).retry(actor,job_id,key,kind="BIZINFO_COLLECTION")
        # Retry receipts preserve historical state; immutable job metadata completes the collection DTO.
        return dict(self.store.get("jobs",job_id),**receipt)
    def detail(self,actor,job_id):
        authorize(actor)
        job=self.store.get("jobs",job_id)
        if job["kind"]!="BIZINFO_COLLECTION": raise Denied("JOB_KIND_MISMATCH")
        attempts=[]
        for attempt in sorted(self.store.rows("attempts",job_id=job_id),key=lambda a:a["ordinal"]):
            pages=[]
            for page in sorted(self.store.rows("collection_pages",attempt_id=attempt["id"]),key=lambda p:p["page_number"]):
                records=[]
                for record in self.store.rows("collection_records",page_id=page["id"]):
                    records.append({k:v for k,v in record.items() if k not in ("normalized","acquisitions")}|{
                        "acquisitions":[{k:v for k,v in a.items() if k not in ("storage_key","digest")} for a in record["acquisitions"]]})
                pages.append({k:v for k,v in page.items() if k not in ("raw_key","raw_digest")}|{"records":records})
            attempts.append(dict(attempt,pages=pages))
        return dict(job,attempts=attempts)
    def list(self,actor):
        authorize(actor)
        return [self.detail(actor,j["id"]) for j in self.store.rows("jobs",kind="BIZINFO_COLLECTION")]
