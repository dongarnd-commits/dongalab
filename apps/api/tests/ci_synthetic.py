"""Public, three-feature synthetic TEST data. Never an actual DMP import."""
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.infrastructure.notice_store import SqlNoticeStore
from app.infrastructure.local_auth import hash_password
from app.infrastructure import capability_schema as S
from app.capability.application import CapabilityApplication,fingerprint
from capability_scenario_fixture import ScenarioEnvironment,TEXTS,NOTICES
from isolation import require_test_database

class SyntheticEnvironment(ScenarioEnvironment):
 def prepare(self):
  require_test_database()
  with self.factory.begin() as s:
   store=SqlNoticeStore(s)
   for name,role in [('admin','DATCO_ADMIN'),('operator','DATCO_OPERATOR'),('other','DATCO_OPERATOR'),('company','COMPANY_EDITOR')]:
    self.accounts[name]=store.add('actors',username='TEST_CI_'+name+'_'+uuid4().hex,role=role,password_hash=hash_password(self.password))
   self.memberships={self.accounts['operator']['id']:'TEST_COMPANY_A',self.accounts['other']['id']:'TEST_COMPANY_B'}
   service=CapabilityApplication(s,self.files)
   imported=service.add(S.imports,digest=fingerprint({'synthetic':self.nonce()}),metadata=dict(schema_version='1',artifact_kind='SYNTHETIC_CI_THREE_FEATURES',source_workbook='synthetic.xlsx',source_sheet='TEST',source_display_date='2026-01-01',feature_count=3,system_count=1,group_count=1,uniqueness_rule='feature_id',system_counts={'SYNTHETIC_CI':3}))
   self.refs={}
   for i,letter in enumerate('ABC',1):
    data=dict(feature_id='DMP-'+format(i,'016X'),system='SYNTHETIC_CI',feature_group='TEST',name='TEST feature '+letter,description='Synthetic function '+letter,origin='SYNTHETIC_TEST',excel_row=i,availability='TEST_ONLY',availability_basis='SYNTHETIC_TEST')
    root=service.add(S.features,external_id=data['feature_id'])
    rev=service.add(S.revisions,feature_id=root['id'],ordinal=1,digest=fingerprint(data),data=data)
    service.add(S.members,import_id=imported['id'],feature_id=root['id'],revision_id=rev['id']);self.refs[letter]=rev
  for name,a in self.accounts.items():
   self.clients[name]=TestClient(app);self.call(name,'/notice/session',{'username':a['username'],'password':self.password})
  page=self.call('operator','/capability/features?limit=100');assert page['total']==3
  self.report['inventory']={'total':3,'mode':'SYNTHETIC_CI_NOT_REAL_DMP'}
  for letter,original in TEXTS.items():
   key='TEST_IMPROVEMENT_'+letter
   self.contexts[key]=dict(company_id='TEST_COMPANY_A',site_id='TEST_SITE_A',improvement_version_id=key,original_text=original,confirmed=letter!='G',current_valid=True,fact_version_ids=[],evidence_refs=[],demo=True)
  self.contexts['TEST_OTHER']=dict(self.contexts['TEST_IMPROVEMENT_A'],company_id='TEST_COMPANY_B',improvement_version_id='TEST_OTHER')
  for letter,ref in self.refs.items():
   data=dict(service='TEST CAP-'+letter,description='Synthetic CI service',functions=[{'revision_id':ref['id'],'role':'TEST function'}],problems=[TEXTS[letter]],conditions=['TEST review needed'],exclusions=['TEST no automatic eligibility'],prerequisites=['TEST evidence'],scope='TEST scope '+letter,evidence_note='SYNTHETIC_TEST_ONLY')
   root=self.call('admin','/capability/catalog',dict(data=data,idempotency_key=self.nonce()))
   self.call('operator','/capability/catalog/'+root['id']+'/publish',dict(expected_revision=1,idempotency_key=self.nonce()),status=403)
   version=self.call('admin','/capability/catalog/'+root['id']+'/publish',dict(expected_revision=1,idempotency_key=self.nonce()))
   self.caps[letter]=dict(root=root,version=version,data=data,features=[ref])
  for name,lines in NOTICES.items():self.prepare_notice(name,lines)
  from confirmed_comparison_fixture import register
  register(self,'TEST_IMPROVEMENT_F','B')
