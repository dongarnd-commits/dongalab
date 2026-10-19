"""W1 typed Company ownership and immutable source/review/version records."""
from sqlalchemy import Column, String, Text, Integer, Boolean, UniqueConstraint, CheckConstraint, ForeignKeyConstraint, ForeignKey, Index, DefaultClause, text
from sqlalchemy.dialects.postgresql import JSONB
from app.infrastructure.notice_schema import table, ref

companies=table('companies', Column('business_number',String(10),nullable=False,unique=True),Column('name',Text,nullable=False),Column('current_ordinal',Integer,nullable=False))
memberships=table('company_memberships',ref('company_id','companies'),ref('actor_id','local_actors'),ref('granted_by','local_actors'),UniqueConstraint('company_id','actor_id'))
sites=table('company_sites',ref('company_id','companies'),Column('name',Text,nullable=False),Column('current_ordinal',Integer,nullable=False),UniqueConstraint('id','company_id'))

def scoped(name,*columns):
 return table(name,ref('company_id','companies'),ref('site_id','company_sites',True),*columns,
  ForeignKeyConstraint(['site_id','company_id'],['company_sites.id','company_sites.company_id'],ondelete='RESTRICT'),UniqueConstraint('id','company_id'))
inputs=scoped('company_input_versions',Column('ordinal',Integer,nullable=False),Column('data',JSONB,nullable=False),ref('actor_id','local_actors'))
site_versions=table('company_site_versions',ref('site_id','company_sites'),Column('ordinal',Integer,nullable=False),Column('data',JSONB,nullable=False),ref('actor_id','local_actors'),UniqueConstraint('site_id','ordinal'))
files=scoped('company_files',Column('name',String(200),nullable=False),Column('media_type',String(100),nullable=False),Column('storage_key',String(64),nullable=False),Column('digest',String(64),nullable=False),Column('size',Integer,nullable=False),ref('actor_id','local_actors'),UniqueConstraint('company_id','digest'),CheckConstraint('size>0'))
parses=table('company_document_parses',ref('file_id','company_files'),ref('actor_id','local_actors'),Column('parser_version',String(80),nullable=False),Column('error',String(100)),Column('limitations',JSONB,nullable=False))
evidence=scoped('company_evidence',ref('file_id','company_files',True),ref('input_version_id','company_input_versions',True),ref('parse_id','company_document_parses',True),Column('descriptor',Text,nullable=False),Column('page',Integer),Column('text',Text,nullable=False),Column('mode',String(40),nullable=False),
 CheckConstraint('(file_id IS NOT NULL) <> (input_version_id IS NOT NULL)'),
 ForeignKeyConstraint(['file_id','company_id'],['company_files.id','company_files.company_id'],ondelete='RESTRICT'),
 ForeignKeyConstraint(['input_version_id','company_id'],['company_input_versions.id','company_input_versions.company_id'],ondelete='RESTRICT'))
candidates=scoped('company_fact_candidates',ref('evidence_id','company_evidence'),Column('field',String(80),nullable=False),Column('value',Text,nullable=False),Column('period',String(100),nullable=False),Column('unit',String(100),nullable=False),Column('currency',String(20),nullable=False),Column('valid_from',String(10),nullable=False),Column('mode',String(40),nullable=False),ref('actor_id','local_actors'),
 ForeignKeyConstraint(['evidence_id','company_id'],['company_evidence.id','company_evidence.company_id'],ondelete='RESTRICT'))
acknowledgements=table('company_fact_acknowledgements',ref('candidate_id','company_fact_candidates'),ref('actor_id','local_actors'),Column('agreed',Boolean,nullable=False),Column('note',Text,nullable=False))
facts=scoped('company_facts',Column('field',String(80),nullable=False),Column('period',String(100),nullable=False),Column('unit',String(100),nullable=False),Column('currency',String(20),nullable=False),Column('current_ordinal',Integer,nullable=False))
reviews=table('company_fact_reviews',ref('candidate_id','company_fact_candidates'),ref('actor_id','local_actors'),Column('outcome',String(40),nullable=False),Column('note',Text,nullable=False),
 Column('existing_version_id',String(36),ForeignKey('company_fact_versions.id',ondelete='RESTRICT',use_alter=True,name='fk_company_review_existing_version')),
 CheckConstraint("outcome IN ('CONFIRM_NEW_VALUE','CONFIRM_EXISTING_VALUE','CONFLICT','REQUEST_MORE_INFORMATION','REJECT_CANDIDATE')"))
fact_versions=table('company_fact_versions',ref('fact_id','company_facts'),Column('ordinal',Integer,nullable=False),ref('review_id','company_fact_reviews'),ref('candidate_id','company_fact_candidates'),ref('evidence_id','company_evidence'),Column('value',Text,nullable=False),Column('valid_from',String(10),nullable=False),UniqueConstraint('fact_id','ordinal'),UniqueConstraint('review_id'))
improvements=scoped('company_improvements',Column('title',Text,nullable=False),Column('current_ordinal',Integer,nullable=False),Column('state',String(30),nullable=False),CheckConstraint("state IN ('DRAFT','SUBMITTED','REVIEW_REQUIRED','CONFIRMED','REVISION_REQUIRED')"))
improvement_versions=table('company_improvement_versions',ref('improvement_id','company_improvements'),Column('ordinal',Integer,nullable=False),Column('data',JSONB,nullable=False),ref('actor_id','local_actors'),UniqueConstraint('improvement_id','ordinal'))
improvement_facts=table('company_improvement_facts',ref('version_id','company_improvement_versions'),ref('fact_version_id','company_fact_versions'),UniqueConstraint('version_id','fact_version_id'))
improvement_evidence=table('company_improvement_evidence',ref('version_id','company_improvement_versions'),ref('evidence_id','company_evidence'),UniqueConstraint('version_id','evidence_id'))
improvement_reviews=table('company_improvement_reviews',ref('version_id','company_improvement_versions'),ref('actor_id','local_actors'),Column('outcome',String(40),nullable=False),Column('note',Text,nullable=False))
audit=table('company_audit',ref('company_id','companies'),ref('actor_id','local_actors'),Column('action',String(80),nullable=False),ref('input_version_id','company_input_versions',True),ref('file_id','company_files',True),ref('candidate_id','company_fact_candidates',True),ref('fact_review_id','company_fact_reviews',True),ref('improvement_version_id','company_improvement_versions',True))
TABLES=(companies,memberships,sites,inputs,site_versions,files,parses,evidence,candidates,acknowledgements,facts,reviews,fact_versions,improvements,improvement_versions,improvement_facts,improvement_evidence,improvement_reviews,audit)
IMMUTABLE=tuple(t.name for t in TABLES if t not in (companies,sites,facts,improvements))

Index('uq_company_fact_meaning',facts.c.company_id,facts.c.site_id,facts.c.field,facts.c.period,facts.c.unit,facts.c.currency,unique=True,postgresql_nulls_not_distinct=True)
inputs.append_constraint(UniqueConstraint('company_id','ordinal'))
candidates.append_constraint(CheckConstraint("field NOT IN ('revenue','assets','liabilities') OR (length(period)>0 AND length(unit)>0 AND length(currency)>0)",name='ck_company_financial_context'))
reviews.append_constraint(UniqueConstraint('candidate_id','outcome'))
for _table in TABLES:
 _table.c.created_at.server_default=DefaultClause(text('clock_timestamp()'))

companies.append_constraint(CheckConstraint("business_number ~ '^[0-9]{10}$'",name='ck_company_business_number'))

improvement_versions.append_column(Column('site_ordinal',Integer,nullable=False))
CURRENT_POINTERS=(('companies',companies,inputs,'company_id','fk_company_current_input'),('company_sites',sites,site_versions,'site_id','fk_company_site_current_version'),('company_facts',facts,fact_versions,'fact_id','fk_company_fact_current_version'),('company_improvements',improvements,improvement_versions,'improvement_id','fk_company_improvement_current_version'))
for _name,_root,_versions,_parent,_constraint in CURRENT_POINTERS:
 _root.append_constraint(ForeignKeyConstraint(['id','current_ordinal'],[_versions.name+'.'+_parent,_versions.name+'.ordinal'],name=_constraint,ondelete='RESTRICT',use_alter=True,deferrable=True,initially='DEFERRED'))
for _versions in (inputs,site_versions,fact_versions,improvement_versions):
 _versions.append_constraint(CheckConstraint('ordinal>0'))

# Explicit user approval: W1_COMMON_LINEAGE_APPROVAL_REQUEST.md.
from app.infrastructure import company_lineage
candidates.append_column(Column('analysis_candidate_id',String(36),ForeignKey('analysis_candidates.id',name='fk_company_candidate_analysis',ondelete='RESTRICT',use_alter=True,deferrable=True,initially='DEFERRED'),nullable=True))
candidates.append_constraint(CheckConstraint("(mode='RULE_BASED_EXTRACTION') = (analysis_candidate_id IS NOT NULL)",name='ck_company_candidate_lineage'))
analysis_contexts=company_lineage.contexts
TABLES=TABLES+(analysis_contexts,)
IMMUTABLE=IMMUTABLE+(analysis_contexts.name,)

evidence.append_column(ref('actor_id','local_actors'))
