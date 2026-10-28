"""Slice 2 typed additions; existing request content/guards are untouched."""
from sqlalchemy import Column, String, Text, Integer, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from app.infrastructure import notice_schema as N, analysis_schema as A, company_schema as C
from app.infrastructure.company_lineage import extend
from app.infrastructure.notice_schema import table, ref

receipts = table('improvement_analysis_request_receipts',ref('job_id','background_jobs'),ref('actor_id','local_actors'),
    Column('request_key',String(100),nullable=False),Column('body_hash',String(64),nullable=False),UniqueConstraint('actor_id','request_key'))
manifests = table('improvement_analysis_manifests', ref('job_id','background_jobs'),
    ref('company_id','companies'), ref('version_id','company_improvement_versions'),
    ref('submit_review_id','company_improvement_reviews'), ref('input_version_id','company_input_versions'),
    ref('site_version_id','company_site_versions'), Column('digest',String(64),nullable=False),
    Column('data',JSONB,nullable=False), UniqueConstraint('job_id'))
inputs = table('improvement_analysis_inputs', ref('manifest_id',manifests.name),
    ref('file_id','company_files',True), ref('evidence_id','company_evidence',True),
    ref('fact_version_id','company_fact_versions',True), ref('fact_review_id','company_fact_reviews',True),
    ref('parse_id','company_document_parses',True), Column('origin',String(30),nullable=False),
    Column('data',JSONB,nullable=False),
    CheckConstraint('num_nonnulls(file_id,evidence_id,fact_version_id)=1'))
contexts = table('analysis_improvement_contexts',ref('run_id','analysis_runs'),ref('manifest_id',manifests.name),
    Column('status',String(20),nullable=False),Column('diagnostics',JSONB,nullable=False),
    CheckConstraint("status IN ('SUCCEEDED','PARTIAL','FAILED')"),UniqueConstraint('run_id'))
inspections = table('improvement_analysis_inspections',ref('run_id','analysis_runs'),ref('input_id',inputs.name),
    ref('parse_id','company_document_parses',True),Column('data',JSONB,nullable=False),UniqueConstraint('run_id','input_id'))
details = table('improvement_analysis_candidate_details',ref('candidate_id','analysis_candidates'),
    Column('category',String(30),nullable=False),Column('data',JSONB,nullable=False),UniqueConstraint('candidate_id'),
    CheckConstraint("category IN ('STRUCTURE','MISSING_INFORMATION','CONFLICT','PROCESSING_LIMITATION')"),
    CheckConstraint("jsonb_typeof(data->'evidence') IS NOT DISTINCT FROM 'array' AND length(COALESCE(data->>'rule_version',''))>0 AND COALESCE(data->>'claim_kind','') IN ('DIRECT_SOURCE','INFERRED','SEARCH_NOT_FOUND','PROCESSING_STATUS')"))
reviews = table('improvement_analysis_reviews',ref('review_id','analysis_reviews'),
    ref('candidate_id','analysis_candidates'),ref('actor_id','local_actors'),Column('ordinal',Integer,nullable=False),
    Column('decision',String(30),nullable=False),Column('question',Text,nullable=False),
    Column('request_key',String(100),nullable=False),Column('body_hash',String(64),nullable=False),
    UniqueConstraint('review_id'),UniqueConstraint('candidate_id','ordinal'),UniqueConstraint('actor_id','request_key'),
    CheckConstraint("decision IN ('USE_FOR_REQUEST','EXCLUDE','NEEDS_CHECK')"))
drafts = table('improvement_request_drafts',ref('run_id','analysis_runs'),ref('company_id','companies'),
    ref('version_id','company_improvement_versions'),ref('actor_id','local_actors'),
    Column('request_key',String(100),nullable=False),Column('body_hash',String(64),nullable=False),
    UniqueConstraint('actor_id','request_key'))
draft_versions = table('improvement_request_draft_versions',ref('draft_id',drafts.name),
    ref('actor_id','local_actors'),Column('ordinal',Integer,nullable=False),
    Column('title',String(300),nullable=False),Column('message',Text,nullable=False),Column('due_date',String(10)),
    Column('request_key',String(100),nullable=False),Column('body_hash',String(64),nullable=False),
    UniqueConstraint('draft_id','ordinal'),UniqueConstraint('actor_id','request_key'),CheckConstraint('ordinal>0'))
selections = table('improvement_request_draft_selections',ref('draft_version_id',draft_versions.name),
    ref('analysis_review_id',reviews.name),UniqueConstraint('draft_version_id','analysis_review_id'))
deliveries = table('improvement_request_deliveries',ref('draft_id',drafts.name),
    ref('draft_version_id',draft_versions.name),ref('request_id','company_information_requests'),
    ref('actor_id','local_actors'),UniqueConstraint('draft_id'),UniqueConstraint('draft_version_id'),UniqueConstraint('request_id'))
TABLES=(receipts,manifests,inputs,contexts,inspections,details,reviews,drafts,draft_versions,selections,deliveries)

extend(N.jobs,'ck_jobs_kind_target',"kind='IMPROVEMENT_ANALYSIS' AND version_id IS NULL")
extend(N.runs,'ck_analysis_run_target',"analysis_kind='IMPROVEMENT_ANALYSIS' AND attempt_id IS NOT NULL AND version_id IS NULL AND actor_id IS NOT NULL")
extend(N.candidates,'ck_analysis_candidate_target',"analysis_kind='IMPROVEMENT_ANALYSIS' AND location_id IS NULL AND assessment_id IS NULL AND match_candidate_id IS NULL AND company_candidate_id IS NULL")
extend(N.reviews,'ck_analysis_review_target',"analysis_kind='IMPROVEMENT_ANALYSIS' AND outcome IS NULL AND official_verified IS NULL")
A.review_contexts.append_column(ref('improvement_review_id',reviews.name,True))
old=next(c for c in A.review_contexts.constraints if isinstance(c,CheckConstraint) and c.name=='ck_domain_review_one_target')
A.review_contexts.constraints.remove(old)
A.review_contexts.append_constraint(CheckConstraint('num_nonnulls(assessment_review_id,match_review_id,company_review_id,improvement_review_id)=1',name='ck_domain_review_one_target'))
