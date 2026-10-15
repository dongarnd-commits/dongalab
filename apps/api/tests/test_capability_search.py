import json
from app.capability.search import search_reasons
from app.core.config import ROOT

def test_actual_corpus_beyond_three_scenario_capabilities():
 features=json.loads((ROOT/'_local_inputs/dmp_features_649.json').read_bytes())['features']
 payroll=next(f for f in features if f['system']=='ERP-인사' and f['name']=='급여 자료 입력')
 data={'service':'급여 업무 지원','description':'검증된 급여 자료 입력 기능','problems':['급여 자료 입력'],
  'functions':[{'revision_id':'TEST_UNUSED_IDENTIFIER','role':payroll['description']}], 'prerequisites':['기업 자료'],'evidence_note':'DMP 실제 원천 검토'}
 assert search_reasons('급여를 입력하고 싶습니다.',data,[payroll])
 assert not search_reasons('실제',data,[payroll])
 assert not search_reasons('자료',data,[payroll])
 assert not search_reasons('DMP 기능과 무관한 장치 개발',data,[payroll])
 # Exact multiword problem remains meaningful although its generic words alone do not.
 assert search_reasons('급여 자료 입력',data,[payroll])


def test_production_synonym_is_supported_by_actual_process_function():
 features=json.loads((ROOT/'_local_inputs/dmp_features_649.json').read_bytes())['features']
 process=next(f for f in features if f['feature_id']=='DMP-04CC3BA519E87467')
 data={'service':'공정 진행 확인','description':'공정 진행 상태 조회','problems':['공정 진행 파악'],
  'functions':[{'revision_id':'TEST_REF','role':process['description']}]}
 reasons=search_reasons('생산 관리',data,[process])
 assert reasons and any('공정' in reason for reason in reasons)
