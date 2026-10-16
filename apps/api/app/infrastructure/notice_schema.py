# Physical records only for the first Notice review slice.
from uuid import uuid4
from sqlalchemy import Table, Column, String, Text, Integer, Boolean, DateTime, ForeignKey, Index, UniqueConstraint, CheckConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from app.infrastructure.database import Base

def identity():
    return str(uuid4())

def table(name, *columns):
    return Table(name, Base.metadata,
        Column("id", String(36), primary_key=True, default=identity),
        Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
        *columns)

def ref(name, target, nullable=False):
    return Column(name, String(36), ForeignKey(target+".id", ondelete="RESTRICT"), nullable=nullable)

actors = table("local_actors", Column("username", String(80), unique=True, nullable=False),
    Column("role", String(40), nullable=False), Column("password_hash", Text, nullable=False))
sessions = table("local_sessions", ref("actor_id","local_actors"),
    Column("token_hash", String(64), unique=True, nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False))
notices = table("notices", Column("external_key", String(160), unique=True, nullable=False),
    Column("title", Text, nullable=False), Column("current_ordinal", Integer, nullable=False))
versions = table("notice_versions", ref("notice_id","notices"),
    Column("ordinal", Integer, nullable=False), Column("mode", String(20), nullable=False),
    Column("metadata", JSONB, nullable=False),
    UniqueConstraint("notice_id","ordinal"), CheckConstraint("ordinal > 0"))
sources = table("notice_sources", ref("version_id","notice_versions"),
    Column("name", Text, nullable=False), Column("media_type", String(40), nullable=False),
    Column("provenance", Text, nullable=False), Column("storage_key", String(64), nullable=True),
    Column("digest", String(64), nullable=True),
    CheckConstraint("(storage_key IS NULL) = (digest IS NULL)"))
jobs = table("background_jobs", ref("version_id","notice_versions",True), ref("actor_id","local_actors"),
    Column("request_key", String(100), nullable=False),
    Column("kind", String(40), nullable=False, server_default="NOTICE_ANALYSIS"),
    Column("payload", JSONB, nullable=False, server_default="{}"),
    Column("state", String(20), nullable=False), Column("error", Text),
    Column("lease_until", DateTime(timezone=True)),
    UniqueConstraint("actor_id","request_key"),
    CheckConstraint("(kind = 'NOTICE_ANALYSIS' AND version_id IS NOT NULL) OR (kind = 'BIZINFO_COLLECTION' AND version_id IS NULL)",name="ck_jobs_kind_target"),
    CheckConstraint("state IN ('QUEUED','PROCESSING','SUCCEEDED','PARTIAL','FAILED')"))
attempts = table("job_attempts", ref("job_id","background_jobs"),
    Column("ordinal", Integer, nullable=False), Column("owner", String(36), nullable=False),
    Column("state", String(20), nullable=False), Column("error", Text),
    UniqueConstraint("job_id","ordinal"),
    CheckConstraint("state IN ('PROCESSING','SUCCEEDED','PARTIAL','FAILED')"))
runs = table("analysis_runs", ref("attempt_id","job_attempts",True), ref("version_id","notice_versions",True),
    Column("analysis_kind",String(40),nullable=False,server_default="NOTICE_REQUIREMENT_ANALYSIS"),
    ref("actor_id","local_actors",True),
    CheckConstraint("(analysis_kind='NOTICE_REQUIREMENT_ANALYSIS' AND attempt_id IS NOT NULL AND version_id IS NOT NULL) OR (analysis_kind IN ('CAPABILITY_ASSESSMENT','SUPPORT_MATCHING') AND attempt_id IS NULL AND version_id IS NULL AND actor_id IS NOT NULL)",name="ck_analysis_run_target"),
    Column("provider_version", String(80), nullable=False),
    Column("extractor_version", String(80), nullable=False),
    Column("missing", JSONB, nullable=False), Column("conflicts", JSONB, nullable=False),
    UniqueConstraint("attempt_id"))
locations = table("source_locations", ref("run_id","analysis_runs"), ref("source_id","notice_sources"),
    Column("page", Integer), Column("descriptor", Text, nullable=False),
    Column("text", Text, nullable=False), CheckConstraint("page IS NULL OR page > 0"))
candidates = table("analysis_candidates", ref("run_id","analysis_runs"),
    ref("location_id","source_locations",True),
    Column("analysis_kind",String(40),nullable=False,server_default="NOTICE_REQUIREMENT_ANALYSIS"),
    ref("assessment_id","capability_assessments",True),ref("match_candidate_id","capability_match_candidates",True),
    CheckConstraint("(analysis_kind='NOTICE_REQUIREMENT_ANALYSIS' AND location_id IS NOT NULL AND assessment_id IS NULL AND match_candidate_id IS NULL) OR (analysis_kind='CAPABILITY_ASSESSMENT' AND location_id IS NULL AND assessment_id IS NOT NULL AND match_candidate_id IS NULL) OR (analysis_kind='SUPPORT_MATCHING' AND location_id IS NULL AND assessment_id IS NULL AND match_candidate_id IS NOT NULL)",name="ck_analysis_candidate_target"), Column("kind", String(60), nullable=False),
    Column("content", Text, nullable=False), Column("reason", Text, nullable=False))
reviews = table("analysis_reviews", ref("candidate_id","analysis_candidates"),
    ref("actor_id","local_actors"), Column("analysis_kind",String(40),nullable=False,server_default="NOTICE_REQUIREMENT_ANALYSIS"), Column("outcome", String(40), nullable=True),
    Column("note", Text, nullable=False), Column("official_verified", Boolean, nullable=True),
    CheckConstraint("(analysis_kind='NOTICE_REQUIREMENT_ANALYSIS' AND outcome IS NOT NULL AND outcome IN ('CONFIRM','REQUEST_MORE_INFORMATION','REQUEST_REVISION','REJECT') AND official_verified IS NOT NULL) OR (analysis_kind IN ('CAPABILITY_ASSESSMENT','SUPPORT_MATCHING') AND outcome IS NULL AND official_verified IS NULL)",name="ck_analysis_review_target"))
Index("uq_notice_analysis_review_candidate",reviews.c.candidate_id,unique=True,postgresql_where=reviews.c.analysis_kind=='NOTICE_REQUIREMENT_ANALYSIS')
requirements = table("notice_requirements", ref("notice_id","notices"), UniqueConstraint("notice_id"))
requirement_versions = table("notice_requirement_versions", ref("requirement_id","notice_requirements"),
    ref("notice_version_id","notice_versions"), ref("review_id","analysis_reviews"),
    Column("ordinal", Integer, nullable=False), Column("scope", Text, nullable=False),
    UniqueConstraint("requirement_id","ordinal"), UniqueConstraint("review_id"))
items = table("notice_requirement_items", ref("version_id","notice_requirement_versions"),
    ref("candidate_id","analysis_candidates"), ref("location_id","source_locations"),
    Column("kind", String(60), nullable=False), Column("content", Text, nullable=False))
audits = table("audit_records", ref("actor_id","local_actors",True),
    ref("notice_version_id","notice_versions",True), ref("job_id","background_jobs",True),
    ref("review_id","analysis_reviews",True), ref("source_id","notice_sources",True),
    Column("action", String(80), nullable=False), Column("reason", Text, nullable=False))

TABLES = {name: value for name,value in globals().copy().items() if isinstance(value,Table)}
