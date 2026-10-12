from sqlalchemy import Column,String,Integer,Text,UniqueConstraint,CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from app.infrastructure.notice_schema import table,ref,TABLES

collection_pages=table("collection_pages",ref("attempt_id","job_attempts"),
    Column("page_number",Integer,nullable=False),Column("state",String(20),nullable=False),
    Column("error",Text),Column("raw_key",String(64)),Column("raw_digest",String(64)),
    Column("observed_count",Integer,nullable=False),Column("expected_total",Integer),
    Column("warnings",JSONB,nullable=False),
    UniqueConstraint("attempt_id","page_number"),CheckConstraint("page_number > 0"),
    CheckConstraint("state IN ('SUCCEEDED','PARTIAL','FAILED')"))
collection_records=table("collection_records",ref("page_id","collection_pages"),
    Column("position",Integer,nullable=False),Column("external_id",String(120)),
    ref("notice_id","notices",True),ref("notice_version_id","notice_versions",True),
    Column("outcome",String(24),nullable=False),Column("error",Text),
    Column("normalized",JSONB,nullable=False),Column("acquisitions",JSONB,nullable=False),
    UniqueConstraint("page_id","position"))
TABLES.update(collection_pages=collection_pages,collection_records=collection_records)
