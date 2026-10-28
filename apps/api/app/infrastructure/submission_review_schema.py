"""Whole-submission operator judgement, separate from CONFIRM and candidate reviews."""
from sqlalchemy import Column,String,Integer,Text,CheckConstraint,UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from app.infrastructure.notice_schema import table,ref

reviews=table('improvement_submission_reviews',ref('company_id','companies'),ref('improvement_id','company_improvements'),
    ref('version_id','company_improvement_versions'),ref('run_id','analysis_runs',True),ref('job_id','background_jobs',True),
    ref('draft_id','improvement_request_drafts',True),ref('actor_id','local_actors'),
    Column('ordinal',Integer,nullable=False),Column('decision',String(30),nullable=False),
    Column('note',Text,nullable=False),Column('analysis_limit',Text,nullable=False),Column('basis',JSONB,nullable=False),
    Column('request_key',String(100),nullable=False),Column('body_hash',String(64),nullable=False),
    UniqueConstraint('version_id','ordinal'),UniqueConstraint('actor_id','request_key'),
    CheckConstraint('ordinal>0 AND length(trim(note))>0'),
    CheckConstraint("decision IN ('COMPLETED','NEEDS_CHECK','PREPARE_REQUEST')"),
    CheckConstraint("run_id IS NOT NULL OR length(trim(analysis_limit))>0"),
    CheckConstraint("(decision='PREPARE_REQUEST')=(draft_id IS NOT NULL)"),
    CheckConstraint("jsonb_typeof(basis)='object'"))

GUARD=r"""
BEGIN
 IF NOT EXISTS(SELECT 1 FROM company_improvements i JOIN company_improvement_versions v ON v.improvement_id=i.id
   WHERE i.id=NEW.improvement_id AND i.company_id=NEW.company_id AND v.id=NEW.version_id
   AND EXISTS(SELECT 1 FROM company_improvement_reviews r WHERE r.version_id=v.id AND r.outcome='SUBMIT'))
 OR NOT EXISTS(SELECT 1 FROM local_actors a JOIN company_memberships m ON m.actor_id=a.id
   WHERE a.id=NEW.actor_id AND a.role='DATCO_OPERATOR' AND m.company_id=NEW.company_id)
 THEN RAISE EXCEPTION 'SUBMISSION_REVIEW_SCOPE_MISMATCH' USING ERRCODE='23514'; END IF;
 IF NEW.run_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM analysis_runs r JOIN analysis_improvement_contexts c ON c.run_id=r.id
   JOIN improvement_analysis_manifests m ON m.id=c.manifest_id WHERE r.id=NEW.run_id AND r.analysis_kind='IMPROVEMENT_ANALYSIS'
   AND m.company_id=NEW.company_id AND m.version_id=NEW.version_id)
 OR NEW.job_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM improvement_analysis_manifests m WHERE m.job_id=NEW.job_id AND m.company_id=NEW.company_id AND m.version_id=NEW.version_id)
 OR NEW.run_id IS NOT NULL AND NEW.job_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM analysis_runs r JOIN job_attempts a ON a.id=r.attempt_id WHERE r.id=NEW.run_id AND a.job_id=NEW.job_id)
 OR NEW.draft_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM improvement_request_drafts d WHERE d.id=NEW.draft_id AND d.company_id=NEW.company_id AND d.version_id=NEW.version_id AND d.run_id=NEW.run_id AND d.actor_id=NEW.actor_id)
 THEN RAISE EXCEPTION 'SUBMISSION_REVIEW_BASIS_MISMATCH' USING ERRCODE='23514'; END IF;
 IF NEW.ordinal<>(SELECT COALESCE(max(ordinal),0)+1 FROM improvement_submission_reviews WHERE version_id=NEW.version_id)
 THEN RAISE EXCEPTION 'SUBMISSION_REVIEW_ORDINAL_MISMATCH' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END
"""
