"""PostgreSQL-backed TEST authority; not a Company module or production adapter."""
import json
from dataclasses import asdict
from uuid import uuid4
from sqlalchemy import MetaData, Table, Column, String, JSON, ForeignKey, insert, select
from app.infrastructure.notice_schema import actors
from app.capability.comparison import ConfirmedFact, ReviewedCondition, ComparisonInputs

metadata=MetaData()
actors.to_metadata(metadata)
facts=Table('test_confirmed_fact_versions',metadata,Column('id',String,primary_key=True),Column('reviewer_id',String,ForeignKey('local_actors.id',ondelete='RESTRICT'),nullable=False),Column('data',JSON,nullable=False))
conditions=Table('test_reviewed_condition_versions',metadata,Column('id',String,primary_key=True),Column('reviewer_id',String,ForeignKey('local_actors.id',ondelete='RESTRICT'),nullable=False),Column('improvement_version_id',String,nullable=False),Column('data',JSON,nullable=False))

def register(env, improvement_version_id, notice_key, value='MANUFACTURING', confirmed=True, reviewed=True):
    context=env.contexts[improvement_version_id]
    notice=env.notices[notice_key]
    with env.factory() as session:
        from app.infrastructure.confirmed_notice_reader import ConfirmedNoticeReader
        from app.infrastructure.notice_store import SqlNoticeStore
        from app.notice.domain import Actor
        actor=Actor(env.accounts['operator']['id'],'DATCO_OPERATOR')
        read=ConfirmedNoticeReader(SqlNoticeStore(session),env.files).read(actor,notice['notice_id'],notice['requirement_version_id'])
    item=next(i for i in read['items'] if i['kind']=='ELIGIBILITY_REQUIREMENT')
    evidence_key,_=env.files.put(('SYNTHETIC TEST company evidence: '+value).encode())
    fact=ConfirmedFact(str(uuid4()),context['company_id'],context['site_id'],'enterprise_type',value,
        str(uuid4()),(evidence_key,),confirmed,True,'2026-01-01')
    condition=ReviewedCondition(read['requirement_version_id'],item['id'],'enterprise_type','NOT_IN',('MANUFACTURING',),
        str(uuid4()),item['evidence']['id'],reviewed,True,'2026-10-14')
    # A separate TEST human semantic review, not inferred from Notice CONFIRM.
    # The manufacturer/nonmanufacturer codes are fixture semantics only.
    with env.factory.begin() as session:
        session.execute(insert(facts).values(id=fact.version_id,reviewer_id=actor.id,data=asdict(fact)))
        session.execute(insert(conditions).values(id=condition.review_id,reviewer_id=actor.id,
            improvement_version_id=improvement_version_id,data=asdict(condition)))
    context['fact_version_ids']=[fact.version_id]
    context['evidence_refs']=[evidence_key]
    env.report.setdefault('comparison_authority',{})[improvement_version_id]=dict(
        mode='SYNTHETIC_TEST_ONLY',fact=asdict(fact),condition=asdict(condition),
        reviewer_id=actor.id,source_content=item['content'],condition_interpretation='TEST human-reviewed manufacturer exclusion')
    return fact,condition

def read(env,context,notice):
    with env.factory() as session:
        fs=[r for r in session.execute(select(facts.c.data)).scalars() if r['version_id'] in context.get('fact_version_ids',[])]
        cs=[r for r in session.execute(select(conditions.c.data).where(conditions.c.improvement_version_id==context['improvement_version_id'])).scalars()
            if r['requirement_version_id']==notice['requirement_version_id']]
    for f in fs:
        for evidence in f['evidence_refs']: env.files.read(evidence,evidence)
    return ComparisonInputs(tuple(ConfirmedFact(**dict(f,evidence_refs=tuple(f['evidence_refs']))) for f in fs),
        tuple(ReviewedCondition(**dict(c,values=tuple(c['values']))) for c in cs))
