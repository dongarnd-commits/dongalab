"""Business expectations remain failing when implemented behavior is incorrect."""
import copy,json
from urllib.parse import urlencode
import pytest
from sqlalchemy import select,func,Table
from app.core.config import ROOT
from app.infrastructure import capability_schema as S
from app.infrastructure.confirmed_notice_reader import ConfirmedNoticeReader
from app.infrastructure.notice_store import SqlNoticeStore
from app.notice.domain import Actor
from capability_scenario_fixture import scenario_environment,TEXTS

pytestmark=pytest.mark.integration

@pytest.fixture(scope='module')
def scenario_env():
 with scenario_environment(ROOT/'storage/private/runtime/capability-scenarios/backend') as env:
  yield env

def discover(env,key):
 result=env.call('operator','/capability/improvements/TEST_IMPROVEMENT_'+key+'/candidates')
 features=env.call('operator','/capability/features?'+urlencode({'q':TEXTS[key],'limit':100}))
 env.report['scenarios'].setdefault(key,{})['discovery']={'feature_ids':[f['data']['feature_id'] for f in features['items']],
  'feature_names':[f['data']['name'] for f in features['items']], 'capability_versions':[c['version_id'] for c in result['candidates']],
  'search_reasons':{c['data']['service']:c['search_reasons'] for c in result['candidates']}}
 return result,features,copy.deepcopy(env.report['scenarios'][key]['discovery'])

def test_sc_a_inventory_composition_confirmed_notice(scenario_env):
 e=scenario_env;found,features,discovery=discover(e,'A')
 assert e.caps['A']['version']['id'] in [c['version_id'] for c in found['candidates']]
 assert any(c['search_reasons'] for c in found['candidates'])
 result=e.compose('A',['A']);result['discovery']=discovery
 assert len(result['composition_data']['coverage'][0]['feature_revision_ids'])==5
 assert result['db_reread'] and result['candidate']['fit']=='NEED_MORE_INFO'
 assert result['snapshot']['input']['notice']['items']
 assert len(result['candidate']['data']['dimensions']['support_scope']['items'])>0
 assert len(result['candidate']['data']['dimensions']['eligibility']['items'])>0


def test_sc_b_production_quality(scenario_env):
 e=scenario_env;found,_,discovery=discover(e,'B')
 assert e.caps['B']['version']['id'] in [c['version_id'] for c in found['candidates']]
 r=e.compose('B',['B']);r['discovery']=discovery
 assert len(r['composition_data']['coverage'][0]['feature_revision_ids'])==4
 assert r['db_reread'] and r['candidate']['fit']!='FIT'


def test_sc_c_document_approval(scenario_env):
 e=scenario_env;found,_,discovery=discover(e,'C')
 assert e.caps['C']['version']['id'] in [c['version_id'] for c in found['candidates']]
 r=e.compose('C',['C']);r['discovery']=discovery
 assert all(f['data']['system']=='그룹웨어 MSA' for f in e.caps['C']['features'])
 assert r['db_reread']


def test_sc_d_partial_solution_not_full_fit(scenario_env):
 e=scenario_env;found,_,discovery=discover(e,'D')
 assert e.caps['B']['version']['id'] in [c['version_id'] for c in found['candidates']]
 r=e.compose('D',['B'],addressed='품질검사 및 불량 발생 현황 기록',unresolved='모든 불량의 AI 자동 원인 규명은 실제 원천에서 확인되지 않음')
 r['discovery']=discovery
 assert r['candidate']['fit']!='FIT' and r['proposable_blocked']
 assert '자동 원인' in r['composition_data']['coverage'][0]['unaddressed_scope']


def test_sc_e_unrelated_request_has_no_forced_candidates(scenario_env):
 e=scenario_env;found,features,_=discover(e,'E')
 e.report['scenarios']['E'].update({'input':found['context'],'actual_candidates':[c['data']['service'] for c in found['candidates']],
   'composition_created':False,'expected':'No unrelated Capability or automatic proposal'})
 assert found['candidates']==[], 'Unrelated DMP mention must not match all source Feature IDs'


def test_sc_f_explicit_exclusion_is_mismatch(scenario_env):
 e=scenario_env;r=e.compose('F',['A'],notice='B')
 clauses=r['snapshot']['input']['notice']['items']
 assert any('제조기업은 신청 제외' in i['content'] for i in clauses)
 e.report['scenarios']['F']['expected_fit']='MISMATCH'
 assert r['candidate']['fit']=='MISMATCH', 'Explicit exclusion currently yields generic NEED_MORE_INFO; eligibility comparison not implemented'


def test_sc_g_unconfirmed_vague_input_is_blocked(scenario_env):
 e=scenario_env
 before=len(e.call('operator','/capability/catalog'))
 response=e.call('operator','/capability/improvements/TEST_IMPROVEMENT_G/candidates',status=409)
 e.report['scenarios']['G']={'input':e.contexts['TEST_IMPROVEMENT_G'],'http':409,'reason':response['reason'],
  'composition_created':False,'expected':'Unconfirmed vague input must not become confirmed automatically',
  'missing_question_generation':'NOT_IMPLEMENTED'}
 assert response['reason']=='REQUIRED_DATA_MISSING'
 assert len(e.call('operator','/capability/catalog'))==before


def test_sc_h_versions_snapshot_and_stale_review(scenario_env):
 e=scenario_env
 e.contexts['TEST_IMPROVEMENT_H']=dict(e.contexts['TEST_IMPROVEMENT_A'],improvement_version_id='TEST_IMPROVEMENT_H',original_text='TEST 재고와 생산실적·품질관리 복수 서비스 Version 검증')
 r=e.compose('H',['A','B'])
 old=e.call('operator','/capability/matches/'+r['candidate']['candidate_id']);snapshot=copy.deepcopy(old['snapshot'])
 changed=copy.deepcopy(r['composition_data']);changed['name']='TEST SC-H 조합 v2'
 new=e.call('operator','/capability/compositions/'+r['composition']['id']+'/versions',{'data':changed,'expected_version':r['composition']['version_id'],'idempotency_key':e.nonce()})
 history=e.call('operator','/capability/compositions/'+r['composition']['id'])
 assert len(history['versions'])==2 and history['versions'][0]['id']==r['composition']['version_id']
 now=e.call('operator','/capability/matches/'+r['candidate']['candidate_id'])
 assert not now['current_valid'] and now['snapshot']==snapshot and now['reviews']
 denied=e.call('operator','/capability/matches/'+r['candidate']['candidate_id']+'/review',{'outcome':'HOLD','note':'TEST stale review','idempotency_key':e.nonce()},status=409)
 cap=e.caps['A'];data=copy.deepcopy(cap['data']);data['scope']+=' / TEST revised reviewed scope'
 e.call('admin','/capability/catalog/'+cap['root']['id']+'/draft',{'data':data,'expected_revision':1,'idempotency_key':e.nonce()})
 latest=e.call('admin','/capability/catalog/'+cap['root']['id']+'/publish',{'expected_revision':2,'idempotency_key':e.nonce()})
 published=e.call('admin','/capability/catalog/'+cap['root']['id'])
 assert len(published['versions'])==2 and published['versions'][0]['id']==cap['version']['id']
 r.update({'new_composition':new,'new_capability':latest,'historical_match_current_valid':now['current_valid'],'stale_review_http':409,'historical_review_preserved':True})


def test_sc_i_real_auth_and_test_company_scope(scenario_env):
 e=scenario_env;cap=e.caps['B'];r=e.compose('B',['B']);composition=r['composition']['id']
 e.call('operator','/capability/catalog/'+cap['root']['id']+'/publish',{'expected_revision':1,'idempotency_key':e.nonce()},status=403)
 e.call('other','/capability/compositions/'+composition,status=404)
 e.call('other','/capability/improvements/TEST_IMPROVEMENT_B/candidates',status=404)
 e.call('company','/capability/features',status=403)
 e.call('admin','/capability/compositions/'+composition,status=403)
 assert e.call('other','/capability/improvements/TEST_OTHER/candidates')['context']['company_id']=='TEST_COMPANY_B'
 e.report['scenarios']['I']={'operator_publish':403,'other_company_composition':404,'other_company_input':404,
  'company_catalog':403,'admin_business':403,'scope_authority':'TEST dependency injection only','normal_membership_integration':'BLOCKED'}


def test_r03_blank_required_coverage_rejected(scenario_env):
 e=scenario_env;cap=e.caps['B'];r=e.compose('D',['B']);data=copy.deepcopy(r['composition_data'])
 data['coverage'][0].update(requirement='   ',role='   ',addressed_scope='   ',unaddressed_scope='',missing_information=[])
 response=e.clients['operator'].post('/capability/compositions',json={'data':data,'idempotency_key':e.nonce()},headers={'Origin':'http://localhost:3000'})
 evidence={'http':response.status_code,'body':response.json(),'expected':'Blank required requirement/role must be rejected'}
 if response.status_code==200:
  saved=e.call('operator','/capability/compositions/'+response.json()['id'])
  evidence['persisted_coverage']=saved['versions'][-1]['data']['coverage']
 e.report['R03']=evidence
 assert response.status_code in (409,422), 'Blank required Coverage was persisted'


def test_r04_analysis_lineage_required(scenario_env):
 e=scenario_env;r=e.compose('D',['B'])
 with e.factory() as session:
  assessment=dict(session.execute(select(S.assessments).where(S.assessments.c.capability_version_id==e.caps['B']['version']['id']).limit(1)).mappings().one())
  candidate=dict(session.execute(select(S.match_candidates).where(S.match_candidates.c.id==r['candidate']['candidate_id'])).mappings().one())
 e.report['R04']={'assessment_keys':list(assessment),'candidate_keys':list(candidate),
  'assessment_has_run_reference':'run_id' in assessment or 'analysis_run_id' in assessment,
  'candidate_has_run_reference':'run_id' in candidate or 'analysis_run_id' in candidate,
  'existing_contract':'docs/03:241 and docs/07:30'}
 assert e.report['R04']['assessment_has_run_reference'] and e.report['R04']['candidate_has_run_reference'], 'AnalysisRun/Review lineage not connected'


def test_r05_tables_only_contains_tables(scenario_env):
 invalid={k:type(v).__name__ for k,v in S.TABLES.items() if not isinstance(v,Table)}
 scenario_env.report['R05']={'non_table_entries':invalid,'production_api_failure_observed':False}
 assert invalid=={}, 'TABLES includes non-Table objects'


@pytest.mark.parametrize('scenario,expected_service',[('A','TEST CAP-A'),('C','TEST CAP-C')])
def test_search_quality_generic_notes_do_not_match_unrelated_services(scenario_env,scenario,expected_service):
 e=scenario_env
 result=e.call('operator','/capability/improvements/TEST_IMPROVEMENT_'+scenario+'/candidates')
 actual={c['data']['service']:c['search_reasons'] for c in result['candidates']}
 e.report.setdefault('search_quality',{})[scenario]={'input':TEXTS[scenario],'expected_service':expected_service,'actual':actual}
 assert set(actual)=={expected_service}, 'Generic source/review notes must not make unrelated services appear task-relevant'


def test_notice_c_missing_supplier_conditions_remain_unknown(scenario_env):
 e=scenario_env;r=e.compose('B',['B'],notice='C')
 assert r['candidate']['fit']=='NEED_MORE_INFO'
 assert r['candidate']['data']['dimensions']['eligibility']['items']==[]
 assert r['candidate']['data']['missing'] and r['proposable_blocked']
 e.report['notice_c_missing_conditions']={'candidate_id':r['candidate']['candidate_id'],'snapshot_id':r['candidate']['snapshot_id'],
  'requirement_version_id':e.notices['C']['requirement_version_id'],'fit':r['candidate']['fit'],'proposable_http':409}


@pytest.mark.parametrize('query,expected',[('재고 수량이 맞지 않고 입고·출고를 수기로 관리합니다.','A'),('작업 실적과 불량 발생 현황을 관리하고 싶습니다.','B'),('문서를 검색하고 전자결재를 처리하고 싶습니다.','C')])
def test_specific_business_search_and_exact_id(scenario_env,query,expected):
 e=scenario_env
 result=e.call('operator','/capability/catalog?'+urlencode({'q':query}))
 assert {v['data']['service'] for v in result}=={'TEST CAP-'+expected}
 assert all(v['search_reasons'] for v in result)
 feature=e.caps[expected]['features'][0]
 assert e.call('operator','/capability/features/'+feature['data']['feature_id'])['root']['external_id']==feature['data']['feature_id']


@pytest.mark.parametrize('field',['requirement','role'])
@pytest.mark.parametrize('invalid',[None,'','   ','\t\r\n','\u00a0'])
def test_required_coverage_rejects_all_blank_forms_without_partial_write(scenario_env,field,invalid):
 e=scenario_env;cap=e.caps['B'];context=e.contexts['TEST_IMPROVEMENT_B']
 data={'name':'TEST invalid coverage','improvement_version_id':context['improvement_version_id'],'capability_version_ids':[cap['version']['id']],
  'excluded_feature_revision_ids':[],'coverage':[{'requirement':'유효한 한글 요구사항','capability_version_id':cap['version']['id'],'feature_revision_ids':[],
   'role':'유효한 기능 역할','addressed_scope':'','unaddressed_scope':'','missing_information':[]}],'conditions':[],'unresolved':[]}
 data['coverage'][0][field]=invalid
 with e.factory() as session:before=session.scalar(select(func.count()).select_from(S.composition_versions))
 response=e.clients['operator'].post('/capability/compositions',json={'data':data,'idempotency_key':e.nonce()},headers={'Origin':'http://localhost:3000'})
 assert response.status_code in (409,422)
 with e.factory() as session:assert session.scalar(select(func.count()).select_from(S.composition_versions))==before
