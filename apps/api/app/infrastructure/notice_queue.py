from datetime import datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy import select, update
from app.infrastructure.notice_schema import jobs, attempts
from app.infrastructure.notice_store import SqlNoticeStore

def claim(session,lease_seconds=300,kind="NOTICE_ANALYSIS"):
    row=session.execute(select(jobs).where(jobs.c.state=="QUEUED",jobs.c.kind==kind)
        .order_by(jobs.c.created_at).with_for_update(skip_locked=True).limit(1)).mappings().first()
    if row is None:
        return None
    store=SqlNoticeStore(session)
    job=dict(row)
    history=store.rows("attempts",job_id=job["id"])
    attempt=store.add("attempts",job_id=job["id"],ordinal=len(history)+1,
        owner=str(uuid4()),state="PROCESSING",error=None)
    store.change("jobs",job["id"],state="PROCESSING",
        lease_until=datetime.now(timezone.utc)+timedelta(seconds=lease_seconds))
    store.add("audits",actor_id=None,notice_version_id=job["version_id"],job_id=job["id"],action="START_JOB",reason=attempt["owner"])
    return job,attempt

def recover_expired(session):
    now=datetime.now(timezone.utc)
    rows=session.execute(select(jobs).where(jobs.c.state=="PROCESSING",jobs.c.lease_until<now)
        .with_for_update(skip_locked=True)).mappings().all()
    store=SqlNoticeStore(session)
    for row in rows:
        for attempt in store.rows("attempts",job_id=row["id"]):
            if attempt["state"]=="PROCESSING":
                store.change("attempts",attempt["id"],state="FAILED",error="INTERRUPTED_EXECUTION")
        store.change("jobs",row["id"],state="FAILED",error="INTERRUPTED_EXECUTION",lease_until=None)
        store.add("audits",actor_id=None,notice_version_id=row["version_id"],job_id=row["id"],
            action="RECOVER_INTERRUPTED_JOB",reason="Expired local execution lease; no successful completion recorded")
    return len(rows)
