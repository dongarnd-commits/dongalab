"""Typed common lineage. External Company/Improvement authority stays in Provider."""
from sqlalchemy import Column,String,CheckConstraint,UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from app.infrastructure.notice_schema import table,ref
capability_contexts=table('analysis_capability_contexts',ref('run_id','analysis_runs'),
    ref('assessment_id','capability_assessments'),ref('capability_version_id','capability_versions'),
    ref('composition_version_id','service_composition_versions',True),
    ref('previous_assessment_id','capability_assessments',True),
    Column('improvement_version_id',String(100),nullable=False),Column('company_id',String(100),nullable=False),
    Column('input',JSONB,nullable=False),UniqueConstraint('run_id'))
match_contexts=table('analysis_match_contexts',ref('run_id','analysis_runs'),ref('snapshot_id','capability_match_snapshots'),
    ref('match_candidate_id','capability_match_candidates'),UniqueConstraint('run_id'))
assessment_reviews=table('capability_assessment_reviews',ref('assessment_id','capability_assessments'),
    ref('actor_id','local_actors'),ref('analysis_review_id','analysis_reviews'),
    Column('decision',String(30),nullable=False),Column('note',String(5000),nullable=False),
    ref('audit_id','capability_audit'),UniqueConstraint('analysis_review_id'),
    CheckConstraint("decision IN ('CONFIRMED','REVISION_REQUIRED')"))
review_contexts=table('analysis_domain_review_contexts',ref('review_id','analysis_reviews'),
    ref('assessment_review_id','capability_assessment_reviews',True),ref('match_review_id','capability_match_reviews',True),
    UniqueConstraint('review_id'),UniqueConstraint('assessment_review_id'),UniqueConstraint('match_review_id'),
    CheckConstraint('(assessment_review_id IS NOT NULL) <> (match_review_id IS NOT NULL)',name='ck_domain_review_one_target'))
