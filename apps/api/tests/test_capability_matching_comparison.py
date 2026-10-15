"""Real authenticated API/DB, explicit TEST semantic review and versioned facts."""
import copy
from dataclasses import asdict, replace
from uuid import uuid4
import pytest
from sqlalchemy import update, insert, select
from app.core.config import ROOT
from capability_scenario_fixture import scenario_environment
from confirmed_comparison_fixture import register, facts, conditions

pytestmark=pytest.mark.integration

@pytest.fixture(scope='module')
def env():
    with scenario_environment(ROOT/'storage/private/runtime/capability-comparison/backend') as e:yield e

@pytest.mark.parametrize('case,confirmed,value,reviewed,expected,status',[
    ('F1',True,'MANUFACTURING',True,'MISMATCH','CONFIRMED_CONFLICT'),
    ('F2',False,'MANUFACTURING',True,'NEED_MORE_INFO','UNKNOWN'),
    ('F3',True,'SERVICE',True,'NEED_MORE_INFO','CONFIRMED_SATISFIED'),
    ('F4',True,'MANUFACTURING',False,'NEED_MORE_INFO','UNKNOWN')])
def test_sc_f_confirmed_inputs_and_exact_snapshot(env,case,confirmed,value,reviewed,expected,status):
    e=env;key='TEST_IMPROVEMENT_'+case
    e.contexts[key]=dict(e.contexts['TEST_IMPROVEMENT_F'],improvement_version_id=key)
    fact,condition=register(e,key,'B',value,confirmed,reviewed)
    r=e.compose(case,['A'],notice='B')
    assert r['candidate']['fit']==expected and r['proposable_blocked']
    comparison=r['candidate']['data']['dimensions']['eligibility']['comparisons'][0]
    assert comparison['status']==status
    assert comparison['requirement_version_id']==condition.requirement_version_id
    snapshot=copy.deepcopy(r['snapshot'])
    assert snapshot['input']['comparison']['facts'][0]['version_id']==fact.version_id
    assert snapshot['input']['comparison']['conditions'][0]['evidence_id']==condition.evidence_id
    again=e.call('operator','/capability/matches/'+r['candidate']['candidate_id'])
    assert again['snapshot']==snapshot and again['reviews'][0]['outcome']=='HOLD'
    assert again['candidate']['data']['dimensions']['eligibility']['comparisons'][0]==comparison
    e.report.setdefault('SC_F_comparison',{})[case]=dict(fact=asdict(fact),condition=asdict(condition),result=comparison,snapshot_id=snapshot['id'])
    e.call('other','/capability/matches/'+r['candidate']['candidate_id'],status=404)
    e.call('company','/capability/matches/'+r['candidate']['candidate_id'],status=403)
    # Idempotent retry is exactly the same receipt; no new Snapshot/Candidate.
    n=e.notices['B'];body=dict(composition_version_id=r['composition']['version_id'],notice_id=n['notice_id'],requirement_version_id=n['requirement_version_id'],idempotency_key=e.nonce())
    first=e.call('operator','/capability/matches',body);assert e.call('operator','/capability/matches',body)==first

def test_new_fact_version_stales_review_and_preserves_history(env):
    e=env;key='TEST_IMPROVEMENT_NEW_FACT'
    e.contexts[key]=dict(e.contexts['TEST_IMPROVEMENT_F'],improvement_version_id=key)
    fact,c=register(e,key,'B')
    r=e.compose('NEW_FACT',['A'],notice='B');candidate=r['candidate']['candidate_id']
    before=e.call('operator','/capability/matches/'+candidate)
    evidence_key,_=e.files.put(b'SYNTHETIC TEST company evidence: SERVICE')
    newer=replace(fact,version_id=str(uuid4()),value='SERVICE',review_id=str(uuid4()),evidence_refs=(evidence_key,))
    with e.factory.begin() as session:
        session.execute(insert(facts).values(id=newer.version_id,reviewer_id=e.accounts['operator']['id'],data=asdict(newer)))
    e.contexts[key]['fact_version_ids']=[newer.version_id]
    e.contexts[key]['evidence_refs']=[evidence_key]
    after=e.call('operator','/capability/matches/'+candidate)
    assert not after['current_valid'] and before['snapshot']==after['snapshot'] and before['reviews']==after['reviews']
    e.call('operator','/capability/matches/'+candidate+'/review',dict(outcome='HOLD',note='TEST stale',idempotency_key=e.nonce()),status=409)
    new=e.compose('NEW_FACT',['A'],notice='B')
    assert new['candidate']['fit']=='NEED_MORE_INFO'
    assert new['snapshot']['id']!=before['snapshot']['id']
    assert new['snapshot']['input']['comparison']['facts'][0]['version_id']==newer.version_id


def test_expired_fact_and_foreign_scope_do_not_produce_match(env):
    e=env;key='TEST_IMPROVEMENT_EXPIRED'
    e.contexts[key]=dict(e.contexts['TEST_IMPROVEMENT_F'],improvement_version_id=key)
    fact,c=register(e,key,'B')
    expired=replace(fact,valid_until='2026-10-13')
    with e.factory.begin() as session:session.execute(update(facts).where(facts.c.id==fact.version_id).values(data=asdict(expired)))
    r=e.compose('EXPIRED',['A'],notice='B')
    assert r['candidate']['fit']=='NEED_MORE_INFO'
    assert r['candidate']['data']['dimensions']['eligibility']['comparisons'][0]['status']=='UNKNOWN'
    foreign=replace(fact,company_id='TEST_COMPANY_B')
    with e.factory.begin() as session:session.execute(update(facts).where(facts.c.id==fact.version_id).values(data=asdict(foreign)))
    n=e.notices['B']
    response=e.call('operator','/capability/matches',dict(composition_version_id=r['composition']['version_id'],notice_id=n['notice_id'],requirement_version_id=n['requirement_version_id'],idempotency_key=e.nonce()),status=404)
    assert response['reason']=='OBJECT_NOT_FOUND'


def test_old_notice_snapshot_remains_readable_but_cannot_be_reviewed(env):
    from app.infrastructure.notice_schema import notices
    e=env;r=e.compose('F',['A'],notice='B');candidate=r['candidate']['candidate_id']
    before=e.call('operator','/capability/matches/'+candidate)
    with e.factory.begin() as session:
        session.execute(update(notices).where(notices.c.id==e.notices['B']['notice_id']).values(current_ordinal=2))
    after=e.call('operator','/capability/matches/'+candidate)
    assert not after['current_valid'] and before['snapshot']==after['snapshot'] and before['reviews']==after['reviews']
    e.call('operator','/capability/matches/'+candidate+'/review',dict(outcome='HOLD',note='TEST stale notice',idempotency_key=e.nonce()),status=409)
    e.call('operator','/capability/matches',dict(composition_version_id=r['composition']['version_id'],notice_id=e.notices['B']['notice_id'],requirement_version_id=e.notices['B']['requirement_version_id'],idempotency_key=e.nonce()),status=409)
