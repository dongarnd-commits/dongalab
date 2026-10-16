"""Approved Capability slice physical records; no Company/Improvement master tables."""
from sqlalchemy import Table,Column,String,Text,Integer,Boolean,ForeignKey,UniqueConstraint,CheckConstraint,Index
from sqlalchemy.dialects.postgresql import JSONB
from app.infrastructure.notice_schema import table,ref

imports=table('feature_imports',Column('digest',String(64),nullable=False,unique=True),Column('metadata',JSONB,nullable=False))
features=table('dmp_features',Column('external_id',String(20),nullable=False,unique=True))
revisions=table('dmp_feature_revisions',ref('feature_id','dmp_features'),Column('ordinal',Integer,nullable=False),
    Column('digest',String(64),nullable=False),Column('data',JSONB,nullable=False),
    UniqueConstraint('feature_id','ordinal'),UniqueConstraint('feature_id','digest'),CheckConstraint('ordinal>0'))
members=table('feature_import_members',ref('import_id','feature_imports'),ref('feature_id','dmp_features'),ref('revision_id','dmp_feature_revisions'),UniqueConstraint('import_id','feature_id'))
capabilities=table('capabilities',Column('draft',JSONB,nullable=False),Column('draft_revision',Integer,nullable=False),Column('current_ordinal',Integer,nullable=False,server_default='0'),Column('provider_mapping',JSONB,nullable=False,server_default='{}'))
versions=table('capability_versions',ref('capability_id','capabilities'),Column('ordinal',Integer,nullable=False),Column('data',JSONB,nullable=False),ref('actor_id','local_actors'),UniqueConstraint('capability_id','ordinal'),CheckConstraint('ordinal>0'))
links=table('capability_version_features',ref('version_id','capability_versions'),ref('revision_id','dmp_feature_revisions'),Column('role',Text,nullable=False),UniqueConstraint('version_id','revision_id'))
assessments=table('capability_assessments',Column('company_id',String(100),nullable=False),Column('improvement_version_id',String(100),nullable=False),ref('capability_version_id','capability_versions'),Column('state',String(30),nullable=False),Column('fit',String(30),nullable=False),Column('reason',Text,nullable=False),Column('input',JSONB,nullable=False),ref('analysis_run_id','analysis_runs',True),Column('legacy_lineage',Boolean,nullable=False,server_default='false'),CheckConstraint("legacy_lineage OR analysis_run_id IS NOT NULL",name='ck_assessment_lineage'),CheckConstraint("state IN ('REVIEW_REQUIRED','CONFIRMED','REVISION_REQUIRED')"),CheckConstraint("fit IN ('FIT','PARTIAL_FIT','NEED_MORE_INFO','MISMATCH')"))
compositions=table('service_compositions',Column('company_id',String(100),nullable=False),Column('current_ordinal',Integer,nullable=False))
composition_versions=table('service_composition_versions',ref('composition_id','service_compositions'),Column('ordinal',Integer,nullable=False),Column('improvement_version_id',String(100),nullable=False),Column('context',JSONB,nullable=False),Column('data',JSONB,nullable=False),ref('actor_id','local_actors'),UniqueConstraint('composition_id','ordinal'),CheckConstraint('ordinal>0'))
composition_links=table('composition_capabilities',ref('version_id','service_composition_versions'),ref('capability_version_id','capability_versions'),ref('assessment_id','capability_assessments',True),UniqueConstraint('version_id','capability_version_id'))
match_snapshots=table('capability_match_snapshots',ref('composition_version_id','service_composition_versions'),ref('requirement_version_id','notice_requirement_versions'),Column('input',JSONB,nullable=False))
match_candidates=table('capability_match_candidates',ref('snapshot_id','capability_match_snapshots'),Column('fit',String(30),nullable=False),Column('data',JSONB,nullable=False),ref('analysis_run_id','analysis_runs',True),Column('legacy_lineage',Boolean,nullable=False,server_default='false'),CheckConstraint("legacy_lineage OR analysis_run_id IS NOT NULL",name='ck_match_candidate_lineage'),CheckConstraint("fit IN ('FIT','PARTIAL_FIT','NEED_MORE_INFO','MISMATCH')"))
match_reviews=table('capability_match_reviews',ref('candidate_id','capability_match_candidates'),ref('actor_id','local_actors'),Column('outcome',String(30),nullable=False),Column('note',Text,nullable=False),ref('analysis_review_id','analysis_reviews',True),Column('legacy_lineage',Boolean,nullable=False,server_default='false'),CheckConstraint("legacy_lineage OR analysis_review_id IS NOT NULL",name='ck_match_review_lineage'),CheckConstraint("outcome IN ('PROPOSABLE','REQUEST_MORE_INFO','HOLD','EXCLUDE')"))
receipts=table('capability_command_receipts',ref('actor_id','local_actors'),Column('key',String(100),nullable=False),Column('fingerprint',String(64),nullable=False),Column('result',JSONB,nullable=False),UniqueConstraint('actor_id','key'))
audit=table('capability_audit',ref('actor_id','local_actors',True),Column('action',String(80),nullable=False),Column('targets',JSONB,nullable=False))
TABLES={k:v for k,v in globals().copy().items() if isinstance(v,Table)}

from app.infrastructure import analysis_schema
