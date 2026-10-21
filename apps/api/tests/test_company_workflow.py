from registration_sources import number as synthetic_business_number
"""Guarded real PostgreSQL/API W1 workflow, no business DB or external AI."""
from uuid import uuid4
from urllib.parse import quote
from hashlib import sha256
import pytest
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import get_settings,ROOT
from app.infrastructure.database import get_session_factory
from app.infrastructure.notice_store import SqlNoticeStore
from app.infrastructure.local_auth import hash_password
from app.infrastructure.notice_documents import LocalPrivateFiles
from app.infrastructure import company_schema as S
from app.company.application import CompanyApplication
from app.company.provider import CompanyProvider
from app.notice.domain import Actor
from isolation import require_test_database
import app.api.company as api
pytestmark=pytest.mark.integration
@pytest.fixture(scope='module')
def env():
 require_test_database();factory=get_session_factory();files=LocalPrivateFiles(ROOT/'storage/private/runtime/company-tests'/uuid4().hex);people={};clients={};password='TEST-'+uuid4().hex
 with factory.begin() as s:
  for name,role in [('editor','COMPANY_EDITOR'),('operator','DATCO_OPERATOR'),('admin','DATCO_ADMIN'),('other','COMPANY_EDITOR'),('approver','COMPANY_APPROVER')]:people[name]=SqlNoticeStore(s).add('actors',username='TEST_W1_'+uuid4().hex,role=role,password_hash=hash_password(password))
 old=api.application;api.application=lambda s:CompanyApplication(s,files)
 try:
  for name,person in people.items():
   clients[name]=TestClient(app);r=clients[name].post('/notice/session',json={'username':person['username'],'password':password},headers={'Origin':get_settings().web_origin});assert r.status_code==200
  yield dict(factory=factory,files=files,people=people,clients=clients)
 finally:
  api.application=old
  for c in clients.values():c.close()
def call(e,who,path,body=None,status=200):
 r=e['clients'][who].request('GET' if body is None else 'POST',path,json=body,headers={'Origin':get_settings().web_origin});assert r.status_code==status,(r.status_code,r.text);return r.json()
def fresh(e):
 p=dict(name='TEST Company '+uuid4().hex[:8],business_number=synthetic_business_number(),industry='manufacturing',financials=[dict(year=2025,revenue='100',unit='million',currency='KRW',period='2025')],history=[dict(name='TEST project',period='2024',agency='TEST agency')])
 c=call(e,'editor','/company',p)
 for who in ('operator','approver'):call(e,'admin','/company/'+c['id']+'/access',dict(username=e['people'][who]['username']))
 site=call(e,'editor','/company/'+c['id']+'/sites',{'data':dict(name='TEST Plant',address='TEST address')})['site'];return c,site,p
def upload(e,cid,sid):
 raw='기업명: TEST parsed company\n업종: manufacturing'.encode();r=e['clients']['editor'].post('/company/'+cid+'/files',params=dict(site_id=sid),content=raw,headers={'Origin':get_settings().web_origin,'X-Upload-Name':'TEST.txt'});assert r.status_code==200,r.text;return r.json(),raw

def test_profile_sites_finance_history_and_scope(env):
 e=env;c,site,p=fresh(e);cid=c['id'];d=call(e,'editor','/company/'+cid)
 assert d['inputs'][-1]['data']['financials'][0]['year']==2025 and d['inputs'][-1]['data']['history'][0]['agency']=='TEST agency'
 call(e,'editor','/company/'+cid+'/sites',{'data':dict(name='TEST Second',address='TEST second address')});assert len(call(e,'operator','/company/'+cid)['sites'])==2
 call(e,'other','/company/'+cid,status=404);call(e,'admin','/company/'+cid,status=403);call(e,'editor','/company',p,status=409)
 call(e,'editor','/company/'+cid+'/profile',dict(data=dict(p,overview='TEST revised'),expected_ordinal=1));call(e,'editor','/company/'+cid+'/profile',dict(data=p,expected_ordinal=1),status=409)
 assert len(call(e,'editor','/company/'+cid)['inputs'])==2

def test_actual_file_fact_improvement_and_provider(env):
 e=env;c,site,p=fresh(e);cid=c['id'];f,raw=upload(e,cid,site['id']);assert f['digest']==sha256(raw).hexdigest()
 call(e,'operator','/company/files/'+f['id']+'/parse',{});d=call(e,'editor','/company/'+cid);candidate=next(x for x in d['candidates'] if x['mode']=='RULE_BASED_EXTRACTION' and x['field']=='company_name');assert not d['facts']
 review=dict(outcome='CONFIRM_NEW_VALUE',note='TEST operator evidence reviewed')
 call(e,'operator','/company/candidates/'+candidate['id']+'/review',review,status=409)
 call(e,'editor','/company/candidates/'+candidate['id']+'/acknowledge',dict(agreed=True,note='TEST exact source acknowledged'))
 call(e,'editor','/company/candidates/'+candidate['id']+'/review',review,status=403)
 fv=call(e,'operator','/company/candidates/'+candidate['id']+'/review',review)['version'];assert fv['value']=='TEST parsed company'
 assert e['clients']['operator'].get('/company/files/'+f['id']+'/download').content==raw
 assert e['clients']['other'].get('/company/files/'+f['id']+'/download').status_code==404
 data=dict(title='TEST inventory improvement',original_text='TEST manual stock movements cause inventory differences.',site_id=site['id'],as_is='TEST manual stock',problem='TEST inventory differences',goal='TEST accurate inventory',to_be='TEST managed inventory',fact_version_ids=[fv['id']],evidence_ids=[candidate['evidence_id']])
 v1=call(e,'editor','/company/'+cid+'/improvements',{'data':data});call(e,'editor','/company/improvements/'+v1['id']+'/actions',dict(action='SUBMIT',note='TEST submit original'))
 v2=call(e,'operator','/company/'+cid+'/improvements',dict(data=data,improvement_id=v1['improvement_id'],expected_ordinal=1))
 call(e,'operator','/company/improvements/'+v2['id']+'/actions',dict(action='CONFIRM',note='TEST no company acknowledgement'),status=409)
 call(e,'editor','/company/improvements/'+v2['id']+'/actions',dict(action='ACKNOWLEDGE',note='TEST exact version acknowledged'));call(e,'operator','/company/improvements/'+v2['id']+'/actions',dict(action='CONFIRM',note='TEST evidence reviewed'))
 context=call(e,'operator','/company/improvements/'+v2['id']+'/context');assert context['confirmed'] and context['current_valid'] and context['fact_version_ids']==[fv['id']]
 consumed=call(e,'operator','/capability/improvements/'+v2['id']+'/candidates');assert consumed['context']['improvement_version_id']==v2['id'] and consumed['context']['fact_details'][0]['evidence_id']==candidate['evidence_id']
 with e['factory']() as s:
  provider=CompanyProvider(CompanyApplication(s,e['files']));who=Actor(e['people']['operator']['id'],'DATCO_OPERATOR');b=provider.proposal_basis(who,cid,v2['id']);assert b.company_confirmed and b.current_valid and b.proofs[0].digest==f['digest'];assert provider.read_comparison_inputs(who,context,{}).facts[0].version_id==fv['id']
 v3=call(e,'editor','/company/'+cid+'/improvements',dict(data=data,improvement_id=v1['improvement_id'],expected_ordinal=2));assert v3['data']['original_text']==v1['data']['original_text'];assert not call(e,'operator','/company/improvements/'+v2['id']+'/context')['current_valid']
 with e['factory'].begin() as s:
  with pytest.raises(IntegrityError):
   with s.begin_nested():s.execute(update(S.fact_versions).where(S.fact_versions.c.id==fv['id']).values(value='TEST tamper'))

def test_upload_and_candidate_guards(env):
 e=env;c,site,p=fresh(e);cid=c['id'];f,raw=upload(e,cid,site['id'])
 r=e['clients']['editor'].post('/company/'+cid+'/files',params=dict(site_id=site['id']),content=raw,headers={'Origin':get_settings().web_origin,'X-Upload-Name':'TEST.txt'});assert r.status_code==409
 for name,content in [('TEST.exe',b'bad'),('../TEST.txt',b'bad'),('bad.pdf',b'not PDF')]:
  r=e['clients']['editor'].post('/company/'+cid+'/files',content=content,headers={'Origin':get_settings().web_origin,'X-Upload-Name':quote(name,safe='')});assert r.status_code==422
 other,foreign_site,_=fresh(e);call(e,'editor','/company/'+cid+'/improvements',{'data':dict(title='TEST',original_text='TEST original',site_id=foreign_site['id'])},status=404)
 call(e,'operator','/company/files/'+f['id']+'/parse',{});d=call(e,'editor','/company/'+cid);ev=next(x for x in d['evidence'] if x['file_id']==f['id'])
 call(e,'editor','/company/'+cid+'/candidates',dict(evidence_id=ev['id'],field='revenue',value='100',valid_from='2025-01-01'),status=422)
 call(e,'editor','/company/'+other['id']+'/candidates',dict(evidence_id=ev['id'],field='industry',value='manufacturing',valid_from='2025-01-01'),status=404)


@pytest.mark.parametrize('who,path', [('admin','review'),('approver','review'),('operator','acknowledge')])
def test_fact_role_separation(env,who,path):
 e=env;c,site,p=fresh(e);d=call(e,'editor','/company/'+c['id']);candidate=d['candidates'][0]
 body=dict(outcome='CONFIRM_NEW_VALUE',note='TEST forbidden') if path=='review' else dict(agreed=True,note='TEST cannot impersonate company')
 call(e,who,'/company/candidates/'+candidate['id']+'/'+path,body,status=403)


def test_unauthenticated_and_origin_are_rejected(env):
 with TestClient(app) as client:assert client.get('/company').status_code==401
 e=env;c,site,p=fresh(e)
 r=e['clients']['editor'].post('/company/'+c['id']+'/profile',json=dict(data=p,expected_ordinal=1),headers={'Origin':'https://untrusted.invalid'});assert r.status_code==403


def test_cross_site_evidence_is_rejected_by_api_and_database(env):
 e=env;c,site,p=fresh(e);other=call(e,'editor','/company/'+c['id']+'/sites',{'data':dict(name='TEST other plant',address='TEST other address')})['site'];f,_=upload(e,c['id'],site['id']);call(e,'operator','/company/files/'+f['id']+'/parse',{})
 d=call(e,'editor','/company/'+c['id']);ev=next(x for x in d['evidence'] if x['file_id']==f['id'])
 body=dict(evidence_id=ev['id'],site_id=other['id'],field='company_name',value='TEST parsed company',valid_from='2026-01-01')
 call(e,'editor','/company/'+c['id']+'/candidates',body,status=404)
 with e['factory'].begin() as s:
  with pytest.raises(IntegrityError):
   with s.begin_nested():CompanyApplication(s,e['files']).add(S.candidates,company_id=c['id'],mode='MANUAL_REVIEW',actor_id=e['people']['editor']['id'],period='',unit='',currency='',**body)


def test_parse_failure_retry_preserves_original_and_attempts(env,monkeypatch):
 import app.company.application as module
 e=env;c,site,p=fresh(e);f,raw=upload(e,c['id'],site['id']);original=module.parse_document
 def fail(*args):raise module.DocumentError('TEST_PARSE_FAILURE')
 monkeypatch.setattr(module,'parse_document',fail)
 first=call(e,'operator','/company/files/'+f['id']+'/parse',{});assert first['error']=='TEST_PARSE_FAILURE'
 monkeypatch.setattr(module,'parse_document',original)
 second=call(e,'operator','/company/files/'+f['id']+'/parse',{});assert second['error'] is None
 assert e['files'].read(f['storage_key'],f['digest'])==raw
 d=call(e,'editor','/company/'+c['id']);assert len(d['files'][0]['parses'])==2


def test_db_failure_rolls_back_file_metadata_without_false_success(env,monkeypatch):
 e=env;c,site,p=fresh(e);original=CompanyApplication.record
 def fail(self,who,cid,action,**targets):
  if action=='UPLOAD_COMPANY_FILE':self.add(S.audit,company_id=cid,actor_id='00000000-0000-0000-0000-000000000000',action=action)
  return original(self,who,cid,action,**targets)
 monkeypatch.setattr(CompanyApplication,'record',fail)
 raw=b'TEST failure preservation source';r=e['clients']['editor'].post('/company/'+c['id']+'/files',content=raw,headers={'Origin':get_settings().web_origin,'X-Upload-Name':'TEST-rollback.txt'});assert r.status_code==503
 d=call(e,'editor','/company/'+c['id']);assert d['files']==[] and d['company']['current_ordinal']==1
 # File-before-DB failure can leave an unreferenced blob; no automatic deletion policy.
 assert e['files'].read(sha256(raw).hexdigest(),sha256(raw).hexdigest())==raw


def test_concurrent_profile_update_only_one_expected_version_succeeds(env):
 from concurrent.futures import ThreadPoolExecutor
 e=env;c,site,p=fresh(e)
 def edit(n):
  return e['clients']['editor'].post('/company/'+c['id']+'/profile',json=dict(data=dict(p,overview='TEST concurrent '+str(n)),expected_ordinal=1),headers={'Origin':get_settings().web_origin}).status_code
 with ThreadPoolExecutor(max_workers=2) as pool:statuses=list(pool.map(edit,[1,2]))
 assert sorted(statuses)==[200,409]
 assert len(call(e,'editor','/company/'+c['id'])['inputs'])==2


def test_fact_conflict_reconfirmation_and_history(env):
 e=env;c,site,p=fresh(e);cid=c['id'];d=call(e,'editor','/company/'+cid);candidate=next(x for x in d['candidates'] if x['field']=='industry')
 def ack(candidate):call(e,'editor','/company/candidates/'+candidate['id']+'/acknowledge',dict(agreed=True,note='TEST source acknowledged'))
 def review(candidate,outcome,existing=None,status=200):
  return call(e,'operator','/company/candidates/'+candidate['id']+'/review',dict(outcome=outcome,note='TEST '+outcome,existing_version_id=existing),status=status)
 ack(candidate);v=review(candidate,'CONFIRM_NEW_VALUE')['version']
 revised=dict(p,industry='services');call(e,'editor','/company/'+cid+'/profile',dict(data=revised,expected_ordinal=1));d=call(e,'editor','/company/'+cid);new=next(x for x in d['candidates'] if x['field']=='industry' and x['value']=='services');ack(new)
 review(new,'CONFIRM_NEW_VALUE',status=409);review(new,'CONFLICT',v['id']);d=call(e,'editor','/company/'+cid);assert d['facts'][0]['current_ordinal']==1 or any(f['current_ordinal']==1 for f in d['facts'])
 v2=review(new,'CONFIRM_NEW_VALUE',v['id'])['version'];assert v2['ordinal']==2 and v2['value']=='services'
 revised['overview']='TEST fresh source';call(e,'editor','/company/'+cid+'/profile',dict(data=revised,expected_ordinal=2));d=call(e,'editor','/company/'+cid);same=next(x for x in reversed(d['candidates']) if x['field']=='industry' and x['value']=='services');ack(same);review(same,'CONFIRM_EXISTING_VALUE',v2['id'])
 with e['factory']() as session:
  application=CompanyApplication(session,e['files']);assert not application.current_fact(v['id'])[2];assert application.current_fact(v2['id'])[2];assert application.fact_evidence(v2)[0]==same['evidence_id']
 d=call(e,'editor','/company/'+cid);root=next(f for f in d['facts'] if f['id']==v['fact_id']);assert [x['value'] for x in root['versions']]==['manufacturing','services']


def test_common_company_lineage_rejects_unpaired_run(env):
 from app.infrastructure import notice_schema as N
 e=env
 with e['factory'].begin() as session:
  with pytest.raises(IntegrityError,match='(COMPANY_ANALYSIS_LINEAGE_MISMATCH|ANALYSIS_RUN_CONTEXT_MISMATCH)'):
   with session.begin_nested():
    CompanyApplication(session,e['files']).add(N.runs,analysis_kind='COMPANY_FACT_EXTRACTION',actor_id=e['people']['operator']['id'],provider_version='TEST',extractor_version='TEST',missing=[],conflicts=[])
    session.execute(__import__('sqlalchemy').text('SET CONSTRAINTS ALL IMMEDIATE'))


def test_explicit_financial_rules_keep_source_and_reject_guessed_context(env):
 e=env;c,site,p=fresh(e);cid=c['id']
 raw='기업명: TEST document first\n사업장 소재지: TEST Seoul\n직원수: 42\n매출액(2025,원,KRW): 1800000000\n매출액: 999\n매출액(0000,원,KRW): 888'.encode()
 r=e['clients']['editor'].post('/company/'+cid+'/files',content=raw,headers={'Origin':get_settings().web_origin,'X-Upload-Name':'TEST-finance-context.txt'});assert r.status_code==200
 f=r.json();call(e,'editor','/company/files/'+f['id']+'/parse',{})
 d=call(e,'editor','/company/'+cid);candidates=[x for x in d['candidates'] if x['mode']=='RULE_BASED_EXTRACTION']
 finance=[x for x in candidates if x['field']=='revenue'];assert len(finance)==1
 value=finance[0];assert (value['value'],value['period'],value['unit'],value['currency'])==('1800000000','2025','원','KRW')
 ev=next(x for x in d['evidence'] if x['id']==value['evidence_id']);assert ev['file_id']==f['id'] and ev['descriptor']=='TEXT line 4' and value['value'] in ev['text']
 assert any(x['field']=='employees' and x['value']=='42' for x in candidates)
 assert not d['facts'];assert d['inputs'][-1]['data']['financials']==p['financials']
 call(e,'other','/company/files/'+f['id']+'/parse',{},status=404)


def security_fact(e):
 c,site,p=fresh(e);f,raw=upload(e,c['id'],site['id'])
 call(e,'operator','/company/files/'+f['id']+'/parse',{})
 d=call(e,'editor','/company/'+c['id']);candidate=next(x for x in d['candidates'] if x['field']=='company_name')
 call(e,'editor','/company/candidates/'+candidate['id']+'/acknowledge',dict(agreed=True,note='TEST company source acknowledgement'))
 version=call(e,'operator','/company/candidates/'+candidate['id']+'/review',dict(outcome='CONFIRM_NEW_VALUE',note='TEST_DATCO_INTERNAL_PRIVATE_REVIEW'))['version']
 return c,site,p,f,raw,candidate,version

def test_approver_private_download_is_denied_by_application_and_http(env):
 e=env;c,site,p,f,raw,candidate,version=security_fact(e)
 with e['factory']() as session:
  a=CompanyApplication(session,e['files'])
  from app.notice.domain import Denied
  with pytest.raises(Denied) as denied:a.download(Actor(e['people']['approver']['id'],'COMPANY_APPROVER'),f['id'])
  assert denied.value.status==403
 for ident,status in [(f['id'],403),(candidate['evidence_id'],404),('TEST_UNKNOWN_FILE_ID',404)]:
  call(e,'approver','/company/files/'+ident+'/download',status=status)
 # A nonmember approver has the same role but no access to this company.
 from app.core.config import get_settings
 with e['factory'].begin() as session:
  user=SqlNoticeStore(session).add('actors',username='TEST_NONMEMBER_'+uuid4().hex,role='COMPANY_APPROVER',password_hash=hash_password('TEST_NONMEMBER_PASSWORD'))
 other_company=call(e,'other','/company',dict(p,name='TEST Different company',business_number=synthetic_business_number()))
 call(e,'admin','/company/'+other_company['id']+'/access',dict(username=user['username']))
 with TestClient(app) as client:
  assert client.post('/notice/session',json={'username':user['username'],'password':'TEST_NONMEMBER_PASSWORD'},headers={'Origin':get_settings().web_origin}).status_code==200
  assert client.get('/company/files/'+f['id']+'/download').status_code==404
 for role in ('editor','operator'):
  response=e['clients'][role].get('/company/files/'+f['id']+'/download');assert response.status_code==200 and response.content==raw


def test_approver_detail_is_whitelisted_before_private_history_load(env,monkeypatch):
 e=env;c,site,p,f,raw,candidate,version=security_fact(e)
 expected={'company':{'id':c['id'],'name':c['name']},**{k:[] for k in ('inputs','sites','files','evidence','candidates','facts','improvements','audit')}}
 assert call(e,'approver','/company/'+c['id'])==expected
 assert all(set(row)=={'id','name'} for row in call(e,'approver','/company'))
 assert call(e,'approver','/workspace')['actor']['role']=='COMPANY_APPROVER'
 operator=call(e,'operator','/company/'+c['id']);assert operator['facts'][0]['versions'][0]['review']['note']=='TEST_DATCO_INTERNAL_PRIVATE_REVIEW'
 assert call(e,'editor','/company/'+c['id'])['inputs'][-1]['data']['financials']==p['financials']
 with e['factory']() as session:
  a=CompanyApplication(session,e['files']);rows=a.rows
  def private_read_guard(table,**where):
   assert table in (S.memberships,), 'Approver projection must not load private nested tables'
   return rows(table,**where)
  monkeypatch.setattr(a,'rows',private_read_guard)
  assert a.detail(Actor(e['people']['approver']['id'],'COMPANY_APPROVER'),c['id'])==expected


def test_approver_direct_context_and_guessed_fact_evidence_routes_are_denied(env):
 e=env;c,site,p,f,raw,candidate,fact=security_fact(e)
 data=dict(title='TEST private improvement',original_text='TEST unshared original',site_id=site['id'],fact_version_ids=[fact['id']],evidence_ids=[candidate['evidence_id']])
 v=call(e,'editor','/company/'+c['id']+'/improvements',{'data':data})
 from app.notice.domain import Denied
 with e['factory']() as session:
  with pytest.raises(Denied):CompanyApplication(session,e['files']).read_context(Actor(e['people']['approver']['id'],'COMPANY_APPROVER'),v['id'])
 call(e,'approver','/company/improvements/'+v['id']+'/context',status=403)
 for role in ('editor','operator'):assert call(e,role,'/company/improvements/'+v['id']+'/context')['improvement_version_id']==v['id']
 call(e,'other','/company/improvements/'+v['id']+'/context',status=404)
 for path in ['/company/facts/'+fact['id'],'/company/evidence/'+candidate['evidence_id'],'/company/candidates/'+candidate['id']]:call(e,'approver',path,status=404)
 # Editor writes and operator review remain real, independently authorized commands.
 call(e,'editor','/company/'+c['id']+'/profile',dict(data=dict(p,overview='TEST permitted update'),expected_ordinal=1))
 call(e,'approver','/company/'+c['id']+'/profile',dict(data=p,expected_ordinal=2),status=403)
