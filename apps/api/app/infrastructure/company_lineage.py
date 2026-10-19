"""Approved W1 typed Company extension of the R04 common analysis lineage."""
from sqlalchemy import Column,String,ForeignKey,CheckConstraint,UniqueConstraint
from app.infrastructure import notice_schema as N,analysis_schema as A
from app.infrastructure.notice_schema import table,ref
OLD_CHECKS={}
def extend(table,name,branch):
 old=next(c for c in table.constraints if isinstance(c,CheckConstraint) and c.name==name)
 OLD_CHECKS[(table.name,name)]=str(old.sqltext);table.constraints.remove(old)
 table.append_constraint(CheckConstraint('('+str(old.sqltext)+') OR ('+branch+')',name=name))
contexts=table('analysis_company_contexts',ref('run_id','analysis_runs'),ref('file_id','company_files'),ref('parse_id','company_document_parses'),ref('company_id','companies'),UniqueConstraint('run_id'))
N.candidates.append_column(Column('company_candidate_id',String(36),ForeignKey('company_fact_candidates.id',name='fk_analysis_company_candidate',ondelete='RESTRICT'),nullable=True))
A.review_contexts.append_column(Column('company_review_id',String(36),ForeignKey('company_fact_reviews.id',name='fk_analysis_company_review',ondelete='RESTRICT'),nullable=True))
A.review_contexts.append_constraint(UniqueConstraint('company_review_id',name='uq_analysis_company_review'))
extend(N.runs,'ck_analysis_run_target',"analysis_kind='COMPANY_FACT_EXTRACTION' AND attempt_id IS NULL AND version_id IS NULL AND actor_id IS NOT NULL")
extend(N.candidates,'ck_analysis_candidate_target',"analysis_kind='COMPANY_FACT_EXTRACTION' AND location_id IS NULL AND assessment_id IS NULL AND match_candidate_id IS NULL AND company_candidate_id IS NOT NULL")
N.candidates.append_constraint(CheckConstraint("(analysis_kind='COMPANY_FACT_EXTRACTION') = (company_candidate_id IS NOT NULL)",name='ck_company_candidate_kind'))
extend(N.reviews,'ck_analysis_review_target',"analysis_kind='COMPANY_FACT_EXTRACTION' AND outcome IS NULL AND official_verified IS NULL")
old=next(c for c in A.review_contexts.constraints if isinstance(c,CheckConstraint) and c.name=='ck_domain_review_one_target')
OLD_CHECKS[(A.review_contexts.name,old.name)]=str(old.sqltext);A.review_contexts.constraints.remove(old)
A.review_contexts.append_constraint(CheckConstraint('(CASE WHEN assessment_review_id IS NULL THEN 0 ELSE 1 END + CASE WHEN match_review_id IS NULL THEN 0 ELSE 1 END + CASE WHEN company_review_id IS NULL THEN 0 ELSE 1 END)=1',name='ck_domain_review_one_target'))
BODY=r"""
BEGIN
 IF EXISTS(SELECT 1 FROM analysis_runs r WHERE r.analysis_kind='COMPANY_FACT_EXTRACTION' AND (SELECT count(*) FROM analysis_company_contexts x WHERE x.run_id=r.id)<>1)
 OR EXISTS(SELECT 1 FROM analysis_company_contexts x JOIN analysis_runs r ON r.id=x.run_id JOIN company_files f ON f.id=x.file_id JOIN company_document_parses p ON p.id=x.parse_id WHERE r.analysis_kind<>'COMPANY_FACT_EXTRACTION' OR x.company_id<>f.company_id OR p.file_id<>f.id OR p.error IS NOT NULL OR r.actor_id<>p.actor_id)
 OR EXISTS(SELECT 1 FROM company_fact_candidates c LEFT JOIN analysis_candidates a ON a.id=c.analysis_candidate_id LEFT JOIN analysis_company_contexts x ON x.run_id=a.run_id JOIN company_evidence e ON e.id=c.evidence_id WHERE c.mode='RULE_BASED_EXTRACTION' AND (a.id IS NULL OR x.run_id IS NULL OR a.analysis_kind<>'COMPANY_FACT_EXTRACTION' OR a.company_candidate_id<>c.id OR x.file_id IS DISTINCT FROM e.file_id OR x.parse_id IS DISTINCT FROM e.parse_id OR x.company_id<>c.company_id OR a.content<>c.value OR a.kind<>'COMPANY_FACT_EXTRACTION' OR c.actor_id IS DISTINCT FROM (SELECT actor_id FROM analysis_runs WHERE id=a.run_id)))
 OR EXISTS(SELECT 1 FROM analysis_candidates a WHERE a.analysis_kind='COMPANY_FACT_EXTRACTION' AND NOT EXISTS(SELECT 1 FROM company_fact_candidates c WHERE c.id=a.company_candidate_id AND c.analysis_candidate_id=a.id))
 THEN RAISE EXCEPTION 'COMPANY_ANALYSIS_LINEAGE_MISMATCH' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT 1 FROM company_fact_reviews r JOIN company_fact_candidates c ON c.id=r.candidate_id WHERE c.analysis_candidate_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM analysis_domain_review_contexts x JOIN analysis_reviews a ON a.id=x.review_id WHERE x.company_review_id=r.id AND a.candidate_id=c.analysis_candidate_id AND a.analysis_kind='COMPANY_FACT_EXTRACTION' AND a.actor_id=r.actor_id AND a.note=r.note))
 OR EXISTS(SELECT 1 FROM analysis_domain_review_contexts x JOIN analysis_reviews a ON a.id=x.review_id WHERE x.company_review_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM company_fact_reviews r JOIN company_fact_candidates c ON c.id=r.candidate_id WHERE r.id=x.company_review_id AND c.analysis_candidate_id=a.candidate_id AND a.actor_id=r.actor_id AND a.analysis_kind='COMPANY_FACT_EXTRACTION'))
 THEN RAISE EXCEPTION 'COMPANY_REVIEW_LINEAGE_MISMATCH' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END
"""
GUARDED=('analysis_runs','analysis_candidates','analysis_reviews','analysis_domain_review_contexts','analysis_company_contexts','company_fact_candidates','company_fact_reviews')
