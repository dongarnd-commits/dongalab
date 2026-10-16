"""Proposal entry uses real auth/DB; no fabricated PROPOSABLE or Proposal rows."""
import copy
import pytest
from app.core.config import ROOT
from app.infrastructure import capability_schema as S
from sqlalchemy import select, func
from capability_scenario_fixture import scenario_environment

pytestmark = pytest.mark.integration

@pytest.fixture(scope='module')
def env():
    with scenario_environment(ROOT/'storage/private/runtime/proposal-preparation/backend') as e:
        yield e

@pytest.mark.parametrize('scenario,caps,notice', [('A',['A'],'A'), ('D',['B'],'A'), ('F',['A'],'B')])
def test_proposal_entry_preserves_real_sources_and_blocks_draft(env, scenario, caps, notice):
    e=env
    r=e.compose(scenario,caps,notice=notice)
    candidate=r['candidate']['candidate_id']
    before=e.call('operator','/capability/matches/'+candidate)
    with e.factory() as session:
        counts=[session.scalar(select(func.count()).select_from(t)) for t in (S.audit,S.receipts,S.match_snapshots,S.match_reviews)]
    result=e.call('operator','/capability/matches/'+candidate+'/proposal-preparation')
    assert result['can_create'] is False
    assert set(result['policy_blockers'])=={'MATCH_NOT_PROPOSABLE','MISSING_REQUIRED_INFORMATION'}
    assert result['implementation_blockers']==['PROPOSAL_PERSISTENCE_CONTRACT_PENDING','PROPOSAL_OUTPUT_FORMAT_PENDING']
    refs=result['source_refs']
    assert refs['match_input_snapshot_id']==before['snapshot']['id']
    assert refs['composition_version_id']==r['composition']['version_id']
    assert refs['notice_version_id']==e.notices[notice]['notice_version_id']
    assert refs['requirement_version_id']==e.notices[notice]['requirement_version_id']
    assert refs['review_ids']==[v['id'] for v in before['reviews']]
    assert e.call('operator','/capability/matches/'+candidate)==before
    with e.factory() as session:
        assert counts==[session.scalar(select(func.count()).select_from(t)) for t in (S.audit,S.receipts,S.match_snapshots,S.match_reviews)]
    if scenario=='D':assert before['snapshot']['input']['composition']['coverage'][0]['unaddressed_scope']
    if scenario=='F':assert before['candidate']['fit']=='MISMATCH'


def test_stale_composition_remains_historical_and_cannot_open_proposal(env):
    e=env;r=e.compose('A',['A']);candidate=r['candidate']['candidate_id']
    before=e.call('operator','/capability/matches/'+candidate)
    data=copy.deepcopy(r['composition_data']);data['name']='TEST changed proposal input'
    e.call('operator','/capability/compositions/'+r['composition']['id']+'/versions',
           dict(data=data,expected_version=r['composition']['version_id'],idempotency_key=e.nonce()))
    result=e.call('operator','/capability/matches/'+candidate+'/proposal-preparation')
    assert not result['can_create'] and 'STALE_INPUT_VERSION' in result['policy_blockers']
    assert result['source_refs']['composition_version_id']==r['composition']['version_id']
    after=e.call('operator','/capability/matches/'+candidate)
    assert before['snapshot']==after['snapshot'] and before['reviews']==after['reviews']


def test_proposal_entry_has_backend_role_company_and_session_guards(env):
    from fastapi.testclient import TestClient
    from app.main import app
    e=env;r=e.compose('B',['B']);path='/capability/matches/'+r['candidate']['candidate_id']+'/proposal-preparation'
    assert TestClient(app).get(path).status_code==401
    e.call('admin',path,status=403)
    e.call('company',path,status=403)
    e.call('other',path,status=404)
    e.call('operator','/capability/matches/unknown/proposal-preparation',status=404)


def test_normal_unconnected_provider_stays_unavailable(env,monkeypatch):
    import app.api.capability as api
    from app.capability.application import CapabilityApplication
    monkeypatch.setattr(api,'application',lambda session:CapabilityApplication(session,env.files))
    result=env.call('operator','/capability/matches/unknown/proposal-preparation',status=503)
    assert result['reason']=='IMPROVEMENT_PROVIDER_NOT_CONNECTED'
