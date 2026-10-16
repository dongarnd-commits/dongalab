"""Decision-004 real authenticated API and deferred PostgreSQL invariants."""
import copy
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from sqlalchemy.exc import IntegrityError
from app.core.config import ROOT
from app.capability.application import CapabilityApplication
from app.capability.lineage import AnalysisLineage
from app.infrastructure import notice_schema as N,capability_schema as S,analysis_schema as A
from capability_scenario_fixture import scenario_environment,ScenarioInputs
pytestmark=pytest.mark.integration
@pytest.fixture(scope='module')
def env():
 with scenario_environment(ROOT/'storage/private/runtime/r04-lineage/backend') as e:yield e

def standalone(e):
 body={'improvement_version_id':'TEST_IMPROVEMENT_A','capability_version_id':e.caps['A']['version']['id'],'idempotency_key':e.nonce()}
 receipt=e.call('operator','/capability/assessments',body)
 assert e.call('operator','/capability/assessments',body)==receipt
 return receipt

def test_standalone_assessment_and_reassessment_preserve_review_and_inputs(env):
 e=env;first=standalone(e);before=e.call('operator','/capability/assessments/'+first['id'])
 trace=before['lineage']['runs'][0]
 assert trace['context']['composition_version_id'] is None
 assert trace['context']['improvement_version_id']=='TEST_IMPROVEMENT_A'
 assert trace['context']['capability_version_id']==e.caps['A']['version']['id']
 assert trace['run']['version_id'] is None and trace['run']['attempt_id'] is None
 reviewbody={'decision':'CONFIRMED','note':'TEST actual applicability review','idempotency_key':e.nonce()}
 response=e.call('operator','/capability/assessments/'+first['id']+'/review',reviewbody)
 assert e.call('operator','/capability/assessments/'+first['id']+'/review',reviewbody)==response
 reviewed=e.call('operator','/capability/assessments/'+first['id'])
 assert reviewed['reviews'][0]['analysis_review_id']==reviewed['lineage']['runs'][0]['reviews'][0]['id']
 assert reviewed['reviews'][0]['actor_id']==e.accounts['operator']['id']
 assert reviewed['reviews'][0]['created_at']==reviewed['lineage']['runs'][0]['reviews'][0]['created_at']
 body={'improvement_version_id':'TEST_IMPROVEMENT_A','capability_version_id':e.caps['A']['version']['id'],'idempotency_key':e.nonce()}
 again=e.call('operator','/capability/assessments/'+first['id']+'/reassess',body)
 assert again['id']!=first['id'] and again['analysis_run_id']!=first['analysis_run_id']
 assert e.call('operator','/capability/assessments/'+first['id'])==reviewed
 new=e.call('operator','/capability/assessments/'+again['id'])
 assert new['lineage']['runs'][0]['context']['previous_assessment_id']==first['id']
 assert new['state']=='REVIEW_REQUIRED' and new['reviews']==[]
 e.call('other','/capability/assessments/'+first['id'],status=404)
 e.call('company','/capability/assessments',body,status=403)

def test_composition_match_common_review_and_evidence(env):
 e=env;r=e.compose('A',['A'])
 candidate=e.call('operator','/capability/matches/'+r['candidate']['candidate_id'])
 trace=candidate['lineage']['runs'][0];snap=candidate['snapshot']
 assert trace['context']['snapshot_id']==snap['id']
 assert trace['run']['analysis_kind']=='SUPPORT_MATCHING'
 assert trace['candidates'][0]['match_candidate_id']==candidate['candidate']['id']
 assert snap['input']['notice']['items'][0]['evidence']['source_id']
 second=e.call('operator','/capability/matches/'+candidate['candidate']['id']+'/review',{'outcome':'EXCLUDE','note':'TEST second actual review','idempotency_key':e.nonce()})
 now=e.call('operator','/capability/matches/'+candidate['candidate']['id'])
 assert len(now['reviews'])==2 and len(now['lineage']['runs'][0]['reviews'])==2
 for actual in now['reviews']:
  common=next(x for x in now['lineage']['runs'][0]['reviews'] if x['id']==actual['analysis_review_id'])
  assert common['actor_id']==actual['actor_id'] and common['note']==actual['note'] and common['created_at']==actual['created_at']
  assert common['outcome'] is None and common['official_verified'] is None
 composition=e.call('operator','/capability/compositions/'+r['composition']['id'])
 assessment=composition['assessments'][0]
 detail=e.call('operator','/capability/assessments/'+assessment['id'])
 assert detail['lineage']['runs'][0]['context']['composition_version_id']==r['composition']['version_id']
 assert candidate['snapshot']==now['snapshot']

def test_invalid_kind_missing_context_and_scope_rejected_at_commit(env):
 e=env;actor=e.accounts['operator']['id'];assessment=standalone(e)
 with pytest.raises(IntegrityError):
  with e.factory.begin() as session:
   session.execute(N.runs.insert().values(id=str(uuid4()),analysis_kind='NOTICE_REQUIREMENT_ANALYSIS',attempt_id=None,version_id=None,provider_version='TEST',extractor_version='TEST',missing=[],conflicts=[]))
 with pytest.raises(IntegrityError,match='ANALYSIS_RUN_CONTEXT_MISMATCH'):
  with e.factory.begin() as session:
   session.execute(N.runs.insert().values(id=str(uuid4()),analysis_kind='CAPABILITY_ASSESSMENT',actor_id=actor,provider_version='TEST',extractor_version='not-applicable',missing=[],conflicts=[]))
 with pytest.raises(IntegrityError,match='ASSESSMENT_CONTEXT_MISMATCH'):
  with e.factory.begin() as session:
   service=CapabilityApplication(session,e.files,ScenarioInputs(e))
   run=service.add(N.runs,analysis_kind='CAPABILITY_ASSESSMENT',actor_id=actor,provider_version='TEST',extractor_version='not-applicable',missing=[],conflicts=[])
   service.add(A.capability_contexts,run_id=run['id'],assessment_id=assessment['id'],capability_version_id=e.caps['A']['version']['id'],company_id='OTHER',improvement_version_id='TEST_IMPROVEMENT_A',input={'context':{'company_id':'OTHER','improvement_version_id':'TEST_IMPROVEMENT_A'}})
   service.add(N.candidates,run_id=run['id'],analysis_kind='CAPABILITY_ASSESSMENT',kind='CAPABILITY_ASSESSMENT',assessment_id=assessment['id'],content='NEED_MORE_INFO',reason='TEST context scope fault only')
   assert len(service.rows(N.candidates,run_id=run['id']))==1
   assert len(service.rows(A.capability_contexts,run_id=run['id']))==1

def test_middle_failure_rolls_back_every_lineage_record(env,monkeypatch):
 e=env;r=e.compose('B',['B'])
 tables=[N.runs,N.candidates,S.match_snapshots,S.match_candidates,A.match_contexts]
 with e.factory() as s:before=[s.scalar(select(func.count()).select_from(t)) for t in tables]
 def fail(*args):raise RuntimeError('TEST injected after domain candidate insertion')
 monkeypatch.setattr(AnalysisLineage,'match',fail)
 with pytest.raises(RuntimeError,match='TEST injected'):
  e.call('operator','/capability/matches',{'composition_version_id':r['composition']['version_id'],'notice_id':e.notices['A']['notice_id'],'requirement_version_id':e.notices['A']['requirement_version_id'],'idempotency_key':e.nonce()})
 with e.factory() as s:assert before==[s.scalar(select(func.count()).select_from(t)) for t in tables]


def test_new_legacy_bypass_and_history_mutation_rejected(env):
 e=env;a=standalone(e)
 with pytest.raises(IntegrityError,match='NEW_LEGACY_LINEAGE_FORBIDDEN'):
  with e.factory.begin() as session:
   service=CapabilityApplication(session,e.files,ScenarioInputs(e))
   service.add(S.assessments,company_id='TEST_COMPANY_A',improvement_version_id='TEST_IMPROVEMENT_A',capability_version_id=e.caps['A']['version']['id'],state='REVIEW_REQUIRED',fit='NEED_MORE_INFO',reason='TEST bypass',input={},legacy_lineage=True)
 with pytest.raises(IntegrityError,match='IMMUTABLE_ANALYSIS_HISTORY'):
  with e.factory.begin() as session:session.execute(N.runs.update().where(N.runs.c.id==a['analysis_run_id']).values(provider_version='FORGED'))
 with pytest.raises(IntegrityError,match='IMMUTABLE_DOMAIN_ANALYSIS_HISTORY'):
  with e.factory.begin() as session:session.execute(S.assessments.update().where(S.assessments.c.id==a['id']).values(legacy_lineage=True))

def test_common_candidate_kind_mismatch_rejected(env):
 e=env;r=e.compose('C',['C']);a=standalone(e)
 candidate=e.call('operator','/capability/matches/'+r['candidate']['candidate_id'])
 with pytest.raises(IntegrityError,match='ANALYSIS_CANDIDATE_TARGET_MISMATCH'):
  with e.factory.begin() as session:
   session.execute(N.candidates.insert().values(id=str(uuid4()),run_id=candidate['candidate']['analysis_run_id'],analysis_kind='CAPABILITY_ASSESSMENT',kind='CAPABILITY_ASSESSMENT',assessment_id=a['id'],content='NEED_MORE_INFO',reason='TEST wrong kind'))

def test_stale_assessment_review_cannot_create_common_review(env):
 e=env;a=standalone(e);key='TEST_IMPROVEMENT_A'
 before=e.call('operator','/capability/assessments/'+a['id'])
 e.contexts[key]['current_valid']=False
 try:
  e.call('operator','/capability/assessments/'+a['id']+'/review',{'decision':'CONFIRMED','note':'TEST stale input','idempotency_key':e.nonce()},status=409)
  after=e.call('operator','/capability/assessments/'+a['id'])
  assert not after['current_valid'] and before['lineage']==after['lineage'] and before['reviews']==after['reviews']
 finally:e.contexts[key]['current_valid']=True


def test_run_with_context_but_no_generated_candidate_is_incomplete(env):
 e=env;a=standalone(e)
 with pytest.raises(IntegrityError,match='ANALYSIS_RUN_CONTEXT_MISMATCH'):
  with e.factory.begin() as session:
   service=CapabilityApplication(session,e.files,ScenarioInputs(e))
   assessment=service.get(S.assessments,a['id'])
   run=service.add(N.runs,analysis_kind='CAPABILITY_ASSESSMENT',actor_id=e.accounts['operator']['id'],provider_version='TEST',extractor_version='not-applicable',missing=[],conflicts=[])
   service.add(A.capability_contexts,run_id=run['id'],assessment_id=a['id'],capability_version_id=assessment['capability_version_id'],company_id=assessment['company_id'],improvement_version_id=assessment['improvement_version_id'],input=assessment['input'])

def test_wrong_common_review_actor_or_target_is_rejected(env):
 e=env;r=e.compose('B',['B']);result=e.call('operator','/capability/matches/'+r['candidate']['candidate_id'])
 common_candidate=result['lineage']['runs'][0]['candidates'][0]
 with pytest.raises(IntegrityError,match='DOMAIN_REVIEW_TARGET_MISMATCH'):
  with e.factory.begin() as session:
   service=CapabilityApplication(session,e.files,ScenarioInputs(e))
   common=service.add(N.reviews,candidate_id=common_candidate['id'],actor_id=e.accounts['other']['id'],analysis_kind='SUPPORT_MATCHING',outcome=None,official_verified=None,note='TEST mismatched actor')
   actual=service.add(S.match_reviews,candidate_id=r['candidate']['candidate_id'],actor_id=e.accounts['operator']['id'],outcome='HOLD',note=common['note'],analysis_review_id=common['id'],legacy_lineage=False,created_at=common['created_at'])
   service.add(A.review_contexts,review_id=common['id'],assessment_review_id=None,match_review_id=actual['id'])
