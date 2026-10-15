"""Scenario-only authority and real API/PostgreSQL fixture; never used by runtime."""
import copy,json,secrets
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from app.core.config import ROOT,get_settings
from app.main import app
from app.infrastructure.database import Base,get_engine,get_session
from app.infrastructure.notice_store import SqlNoticeStore
from app.infrastructure.notice_documents import LocalPrivateFiles
from app.infrastructure.local_auth import hash_password
from app.capability.application import CapabilityApplication
from app.notice.application import NoticeApplication
from app.notice.domain import Denied
from app.worker import process_one
import app.api.capability as cap_api
import app.api.notice as notice_api
import app.demo as demo

TEXTS={
 'A':'창고 재고가 실제 수량과 맞지 않습니다. 입고·출고를 수기로 처리하여 재고현황을 정확하게 파악하기 어렵습니다.',
 'B':'작업 실적과 불량 발생 현황을 체계적으로 관리하고 싶습니다.',
 'C':'종이 문서가 많고 결재를 수기로 처리하여 필요한 자료 검색과 업무 승인이 지연됩니다.',
 'D':'품질 불량 현황을 기록하고, 모든 불량의 원인을 AI로 자동 규명하고 싶습니다.',
 'E':'DMP 기능과 무관한 전문 기술 장치를 새로 개발하고 싶습니다.',
 'F':'재고·입출고 관리 전산화.',
 'G':'회사 업무를 자동화하고 싶습니다.'}
FEATURES={
 'A':('ERP-물류',['재고현황','재고수불부','입고등록','출고등록','재고조정등록']),
 'B':('ERP-생산(MES)',['작업실적등록','공정진행현황','품질검사','불량현황']),
 'C':('그룹웨어 MSA',['문서 기안','결재선 지정','문서 상세·결재처리','파일 검색'])}
NOTICES={
 'A':['Support scope: TEST 업무 디지털화 및 재고·생산·문서 관리 시스템 도입 지원.',
      'Eligibility: TEST 제조기업 및 비제조기업 신청 가능. 공급기업 자격증명은 별도 확인 필요.',
      'Eligibility: TEST 신청 제외 대상은 지원사업 중복 신청기업. 중복 여부는 미확인.'],
 'B':['Support scope: TEST 비제조 서비스업의 문서 업무만 지원하며 제조기업 재고 시스템은 지원하지 않음.',
      'Eligibility: TEST 비제조 서비스업만 신청 가능. 제조기업은 신청 제외 대상.'],
 'C':['Support scope: TEST 업무 디지털화 검토용 부분 원문. 공급자격 및 필수 신청조건은 제공되지 않음.']}

class ScenarioInputs:
 def __init__(self,env): self.env=env
 def read(self,actor,version_id):
  value=self.env.contexts.get(version_id)
  if actor.role!='DATCO_OPERATOR' or value is None or self.env.memberships.get(actor.id)!=value['company_id']:
   raise Denied('OBJECT_NOT_FOUND',404)
  return copy.deepcopy(value)

 def read_comparison_inputs(self,actor,context,notice):
  from confirmed_comparison_fixture import read
  actual=self.read(actor,context['improvement_version_id'])
  return read(self.env,actual,notice)

class ScenarioEnvironment:
 def __init__(self,factory,files,directory):
  self.factory,self.files,self.directory=factory,files,directory
  self.password=secrets.token_urlsafe(24);self.accounts={};self.contexts={};self.memberships={};self.caps={};self.notices={}
  self.report={'mode':'ISOLATED_TEST_POSTGRES','official_notice':False,'scenarios':{},'capabilities':{},'notices':{}}
  self.clients={};self.http=[]
 def call(self,who,path,data=None,status=200):
  c=self.clients[who];r=c.get(path) if data is None else c.post(path,json=data,headers={'Origin':get_settings().web_origin})
  self.http.append({'actor':who,'method':'GET' if data is None else 'POST','path':path,'status':r.status_code})
  assert r.status_code==status, f'{path}: {r.status_code}, reason={r.json().get("reason") if isinstance(r.json(),dict) else "unexpected response"}'
  return r.json()
 def nonce(self):return uuid4().hex
 def prepare(self):
  with self.factory.begin() as s:
   store=SqlNoticeStore(s)
   for name,role in [('admin','DATCO_ADMIN'),('operator','DATCO_OPERATOR'),('other','DATCO_OPERATOR'),('company','COMPANY_EDITOR')]:
    self.accounts[name]=store.add('actors',username='TEST_SCENARIO_'+name+'_'+uuid4().hex,role=role,password_hash=hash_password(self.password))
   self.memberships={self.accounts['operator']['id']:'TEST_COMPANY_A',self.accounts['other']['id']:'TEST_COMPANY_B'}
  for name,a in self.accounts.items():
   self.clients[name]=TestClient(app)
   self.call(name,'/notice/session',{'username':a['username'],'password':self.password})
  # Do not include login request bodies in evidence logs.
  imported=self.call('admin','/capability/imports',{})
  page=self.call('operator','/capability/features?limit=100')
  assert page['total']==649 and len(page['systems'])==10
  self.report['inventory']={'total':page['total'],'import':imported,'systems':page['systems'],'sha256':page['import']['digest']}
  for letter,text in TEXTS.items():
   version='TEST_IMPROVEMENT_'+letter
   self.contexts[version]={'company_id':'TEST_COMPANY_A','site_id':'TEST_SITE_A','improvement_version_id':version,
    'original_text':text,'confirmed':letter!='G','current_valid':True,'fact_version_ids':[],
    'evidence_refs':[],'demo':True,'fixture_facts':{'industry':'제조업','source':'SYNTHETIC_TEST_ONLY'}}
  self.contexts['TEST_OTHER']={'company_id':'TEST_COMPANY_B','site_id':'TEST_SITE_B','improvement_version_id':'TEST_OTHER','original_text':'TEST 다른 기업 입력','confirmed':True,'current_valid':True,'fact_version_ids':[],'evidence_refs':[],'demo':True}
  for letter,(system,names) in FEATURES.items():
   refs=[]
   for name in names:
    page=self.call('admin','/capability/features',None)
    # The search API is used; exact source identity is checked after keyword retrieval.
    from urllib.parse import urlencode
    page=self.call('admin','/capability/features?'+urlencode({'q':name,'system':system,'limit':100}))
    matching=[f for f in page['items'] if f['data']['name']==name and f['data']['system']==system]
    assert len(matching)==1, f'Actual source ambiguous/missing: {system}/{name}'
    refs.append(matching[0])
   problems={'A':['재고 불일치','수기 입고 출고'],'B':['작업 실적 관리','품질 불량 현황'],'C':['종이 문서','수기 결재','자료 검색']}[letter]
   data={'service':'TEST CAP-'+letter,'description':'실제 원천 기능 연결을 검증하는 TEST Capability',
    'functions':[{'revision_id':f['id'],'role':f['data']['name']+': '+f['data']['description']} for f in refs],
    'problems':problems,'conditions':['기업 원천 자료와 도입환경 확인'],'exclusions':['원천에 없는 기능은 제공범위 미확인'],
    'prerequisites':['기업 기초자료'],'scope':' / '.join(f['data']['name'] for f in refs),
    'evidence_note':'TEST 원천 Revision의 명칭·설명 확인. 실제 사업 적격성 확정 아님.'}
   if letter=='B':data['exclusions'].append('모든 불량의 AI 자동 원인 규명은 원천에서 확인되지 않음')
   root=self.call('admin','/capability/catalog',{'data':data,'idempotency_key':self.nonce()})
   v=self.call('admin','/capability/catalog/'+root['id']+'/publish',{'expected_revision':1,'idempotency_key':self.nonce()})
   self.caps[letter]={'root':root,'version':v,'data':data,'features':refs}
   self.report['capabilities'][letter]={'capability_id':root['id'],'version_id':v['id'],'ordinal':v['ordinal'],
    'features':[{'feature_id':f['data']['feature_id'],'revision_id':f['id'],'name':f['data']['name'],'description':f['data']['description']} for f in refs], 'evidence_note':data['evidence_note']}
  for name,lines in NOTICES.items():self.prepare_notice(name,lines)
  from confirmed_comparison_fixture import register
  register(self,'TEST_IMPROVEMENT_F','B')
 def prepare_notice(self,name,lines):
  inputs=self.directory/'notice-inputs';inputs.mkdir(exist_ok=True)
  (inputs/(name+'.html')).write_text('<html><body><h1>TEST/DEMO NOTICE-'+name+'</h1>'+''.join('<p>'+line+'</p>' for line in lines)+'</body></html>',encoding='utf-8')
  metadata={'title':'TEST NOTICE-'+name,'external_key':'TEST_SCENARIO_'+name,'metadata':{'fixture_kind':'SYNTHETIC_TEST','official_notice':False},
   'sources':[{'name':'TEST_'+name+'.html','file':name+'.html','media_type':'text/html'}]}
  (inputs/(name+'.json')).write_text(json.dumps(metadata,ensure_ascii=False),encoding='utf-8')
  original=demo.FIXTURES
  try:
   demo.FIXTURES=inputs
   with self.factory.begin() as s:
    store=SqlNoticeStore(s);n=demo.load_input(store,self.files,name,external_key='TEST_SCENARIO_'+name)
    nv=store.rows('versions',notice_id=n['id'])[0]
  finally:demo.FIXTURES=original
  job=self.call('operator','/notice/analysis',{'expected_version':nv['id'],'idempotency_key':self.nonce()})
  assert process_one(self.factory,self.files)
  detail=self.call('operator','/notice/'+n['id']);run=detail['versions'][0]['runs'][0]
  assert run['candidates'], 'Notice extraction produced no candidate; do not seed results'
  rv=None
  for candidate in run['candidates']:
   rv=self.call('operator','/notice/candidates/'+candidate['id']+'/confirm',{'expected_version':nv['id'],'official_verified':True,
    'note':'TEST original reviewed; official_verified tests guard only, not government verification.',
    'scope':'TEST explicitly reviewed clauses only','conflict_resolution':'TEST source comparison' if run['conflicts'] else ''})
  current=self.call('operator','/notice/'+n['id'])['versions'][0]['confirmed'][-1]
  self.notices[name]={'notice_id':n['id'],'notice_version_id':nv['id'],'requirement_version_id':rv['id'],'run_id':run['id']}
  self.report['notices'][name]=dict(self.notices[name],original_lines=lines,job_id=job['id'],candidate_count=len(run['candidates']),confirmed_items=current['items'])
 def compose(self,scenario,letters,notice='A',addressed=None,unresolved=None):
  context=self.contexts['TEST_IMPROVEMENT_'+scenario]
  caps=[self.caps[x] for x in letters]
  coverage=[{'requirement':context['original_text'],'capability_version_id':cap['version']['id'],
   'feature_revision_ids':[f['id'] for f in cap['features']],'role':' / '.join(f['data']['name'] for f in cap['features']),
   'addressed_scope':addressed or cap['data']['scope'],'unaddressed_scope':unresolved or '도입조건 및 자료 품질 확인 필요',
   'missing_information':['기업 기초자료','공고 공급자격 확인']} for cap in caps]
  data={'name':'TEST SC-'+scenario+' 조합','improvement_version_id':context['improvement_version_id'],
   'capability_version_ids':[cap['version']['id'] for cap in caps],'excluded_feature_revision_ids':[],
   'coverage':coverage,'conditions':['원천 도입환경 검토'],'unresolved':[unresolved or '공식 자격 미확인']}
  comp=self.call('operator','/capability/compositions',{'data':data,'idempotency_key':self.nonce()})
  saved=self.call('operator','/capability/compositions/'+comp['id'])
  n=self.notices[notice]
  candidate=self.call('operator','/capability/matches',{'composition_version_id':comp['version_id'],'notice_id':n['notice_id'],'requirement_version_id':n['requirement_version_id'],'idempotency_key':self.nonce()})
  detail=self.call('operator','/capability/matches/'+candidate['candidate_id'])
  review=self.call('operator','/capability/matches/'+candidate['candidate_id']+'/review',{'outcome':'HOLD','note':'TEST scope and eligibility separately reviewed; missing evidence retained.','idempotency_key':self.nonce()})
  self.call('operator','/capability/matches/'+candidate['candidate_id']+'/review',{'outcome':'PROPOSABLE','note':'TEST negative guard','idempotency_key':self.nonce()},status=409)
  result={'input':context,'selected_capabilities':letters,'selection_reason':'TEST human selected exact source functions; no suitability score',
   'composition':comp,'composition_data':data,'db_reread':saved['versions'][-1]['id']==comp['version_id'],
   'notice':n,'candidate':candidate,'snapshot':detail['snapshot'],'review':review,'proposable_blocked':True}
  self.report.setdefault('scenario_attempts',{}).setdefault(scenario,[]).append(copy.deepcopy(result))
  if 'discovery' in self.report['scenarios'].get(scenario,{}):result['discovery']=self.report['scenarios'][scenario]['discovery']
  if 'candidate' not in self.report['scenarios'].get(scenario,{}):self.report['scenarios'][scenario]=result
  return result
 def flush(self):
  self.report['http']=self.http
  (self.directory/'scenario-evidence.json').write_text(json.dumps(self.report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')

@contextmanager
def scenario_environment(directory):
 from isolation import require_test_database
 require_test_database()
 directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
 schema='test_cap_scenarios_'+uuid4().hex
 connection=get_engine().connect().execution_options(schema_translate_map={None:schema})
 outer=connection.begin();connection.exec_driver_sql('CREATE SCHEMA '+schema);Base.metadata.create_all(connection)
 from confirmed_comparison_fixture import metadata as comparison_metadata
 comparison_metadata.create_all(connection)
 factory=sessionmaker(bind=connection,join_transaction_mode='create_savepoint')
 from lineage_test_support import install_test_lineage
 install_test_lineage(connection,schema,factory)
 env=ScenarioEnvironment(factory,LocalPrivateFiles(directory/'sources'),directory)
 old_overrides=dict(app.dependency_overrides);old_cap,old_notice=cap_api.application,notice_api.application
 def sessions():
  with factory() as session:yield session
 app.dependency_overrides[get_session]=sessions
 cap_api.application=lambda session:CapabilityApplication(session,env.files,ScenarioInputs(env))
 notice_api.application=lambda session:NoticeApplication(SqlNoticeStore(session),env.files)
 try:
  env.prepare();yield env
 finally:
  try:env.flush()
  finally:
   for c in env.clients.values():c.close()
   cap_api.application,notice_api.application=old_cap,old_notice
   app.dependency_overrides.clear();app.dependency_overrides.update(old_overrides)
   outer.rollback();connection.close()
