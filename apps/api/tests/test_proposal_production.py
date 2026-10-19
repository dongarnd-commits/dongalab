import copy,io,zipfile
from pathlib import Path
from hashlib import sha256
import pytest
from sqlalchemy import select,func,text
from sqlalchemy.exc import IntegrityError
from pypdf import PdfReader
from app.core.config import ROOT
from app.capability.application import CapabilityApplication
from app.infrastructure import proposal_schema as P
from committed_capability_fixture import committed_environment
from proposal_fixture import confirm_company,ProposalInputs,proposable,completions
import app.api.capability as api
pytestmark=pytest.mark.integration
@pytest.fixture(scope='module')
def env():
 with committed_environment(ROOT/'storage/private/runtime/proposal-production') as e:
  old=api.application
  try:
   confirm_company(e);api.application=lambda s:CapabilityApplication(s,e.files,ProposalInputs(e));yield e
  finally:api.application=old

def create(e):
 r,m=proposable(e);body=dict(candidate_id=r['candidate']['candidate_id'],title='TEST 맞춤형 제안서',idempotency_key=e.nonce())
 p=e.call('operator','/proposal',body);assert e.call('operator','/proposal',body)==p;return p,r,m

def test_complete_version_manifest_review_approval_and_real_documents(env):
 e=env;p,r,m=create(e);v=e.call('operator','/proposal/versions/'+p['version_id'])
 assert len(v['sections'])==11 and v['manifest']['refs']['match_review_id']==m['id'] and v['manifest']['refs']['composition_version_id']==r['composition']['version_id']
 e.call('operator','/proposal/versions/'+v['id']+'/approval',dict(idempotency_key=e.nonce()),status=409)
 review=e.call('operator','/proposal/versions/'+v['id']+'/review',dict(confirmed=True,note='TEST actual proposal content reviewed separately from matching.',idempotency_key=e.nonce()))
 request=e.call('operator','/proposal/versions/'+v['id']+'/approval',dict(idempotency_key=e.nonce()))
 e.call('operator','/proposal/approvals/'+request['id']+'/decision',dict(outcome='APPROVE',reason='TEST cannot impersonate company',idempotency_key=e.nonce()),status=403)
 decision=e.call('approver','/proposal/approvals/'+request['id']+'/decision',dict(outcome='APPROVE',reason='TEST company approved this exact version',idempotency_key=e.nonce()))
 assert decision['outcome']=='APPROVE'
 for kind in ('DOCX','PDF'):
  receipt=e.call('operator','/proposal/versions/'+v['id']+'/export',dict(kind=kind,idempotency_key=e.nonce()))
  response=e.clients['approver'].get('/proposal/files/'+receipt['id']+'/download');assert response.status_code==200 and sha256(response.content).hexdigest()==receipt['digest']
  if kind=='DOCX':
   xml=zipfile.ZipFile(io.BytesIO(response.content)).read('word/document.xml').decode();assert v['title'] in xml and v['id'] in xml and '<w:tbl>' in xml
  else:
   pdf=PdfReader(io.BytesIO(response.content));content=''.join(p.extract_text() for p in pdf.pages);assert v['title'] in content and v['id'] in content and '수요기업' in content
  e.call('other','/proposal/files/'+receipt['id']+'/download',status=404)
 assert e.call('operator','/proposal/versions/'+v['id'])==v
 new=copy.deepcopy(v['sections']);new[2]['body']='TEST 담당자 수정 목표'
 saved=e.call('operator','/proposal/'+p['proposal_id']+'/versions',dict(expected_version=v['id'],title=v['title'],sections=new,idempotency_key=e.nonce()))
 assert saved['ordinal']==2 and e.call('operator','/proposal/versions/'+v['id'])==v
 detail=e.call('operator','/proposal/'+p['proposal_id']);assert detail['decisions'][0]['version_id']==v['id']
 assert not any(x['version_id']==saved['version_id'] for x in detail['decisions'])
 e.call('operator','/proposal/'+p['proposal_id']+'/versions',dict(expected_version=v['id'],title=v['title'],sections=new,idempotency_key=e.nonce()),status=409)
 e.call('operator','/proposal/versions/'+saved['version_id']+'/approval',dict(idempotency_key=e.nonce()),status=409)

@pytest.mark.parametrize('case',['missing','foreign_proof','wrong_notice','conflict','stale'])
def test_review_and_generation_negative_guards(env,case):
 e=env;r=e.compose('F',['A'],notice='B') if case=='conflict' else e.compose('A',['A']);cid=r['candidate']['candidate_id'];items=completions(e,cid)
 if case=='missing':items.pop()
 if case=='foreign_proof':items[0]['proof_ids']=['TEST_OTHER_EVIDENCE']
 if case=='wrong_notice':next(i for i in items if i['task_id'].startswith('notice:'))['notice_evidence_id']='WRONG'
 if case=='stale':
  data=copy.deepcopy(r['composition_data']);data['name']='TEST new input';e.call('operator','/capability/compositions/'+r['composition']['id']+'/versions',dict(data=data,expected_version=r['composition']['version_id'],idempotency_key=e.nonce()))
 e.call('operator','/capability/matches/'+cid+'/review',dict(outcome='PROPOSABLE',note='TEST invalid completion',completion_items=items,idempotency_key=e.nonce()),status=409)
 e.call('operator','/proposal',dict(candidate_id=cid,title='TEST blocked',idempotency_key=e.nonce()),status=409)

@pytest.mark.parametrize('table',['versions','reviews','decisions','files','completions'])
@pytest.mark.parametrize('operation',['update','delete'])
def test_immutable_records_reject_direct_sql(env,table,operation):
 t=getattr(P,table)
 with env.factory() as s:key=s.scalar(select(t.c.id).limit(1))
 assert key
 with pytest.raises(IntegrityError):
  with env.factory.begin() as s:s.execute((t.update().values(id=key) if operation=='update' else t.delete()).where(t.c.id==key))

def test_failed_document_does_not_create_file_record(env,monkeypatch):
 e=env;p,_,_=create(e);v=p['version_id'];e.call('operator','/proposal/versions/'+v+'/review',dict(confirmed=True,note='TEST confirmed content',idempotency_key=e.nonce()))
 from app.proposal import application
 from app.notice.domain import Denied
 def fail(*args):raise Denied('PROPOSAL_DOCUMENT_GENERATION_FAILED',503)
 monkeypatch.setattr(application,'render',fail)
 e.call('operator','/proposal/versions/'+v+'/export',dict(kind='PDF',idempotency_key=e.nonce()),status=503)
 with e.factory() as s:assert s.scalar(select(func.count()).select_from(P.files).where(P.files.c.version_id==v))==0

def test_approval_is_superseded_and_scope_enforced(env):
 e=env;p,_,_=create(e);v=e.call('operator','/proposal/versions/'+p['version_id']);e.call('operator','/proposal/versions/'+v['id']+'/review',dict(confirmed=True,note='TEST content',idempotency_key=e.nonce()));q=e.call('operator','/proposal/versions/'+v['id']+'/approval',dict(idempotency_key=e.nonce()))
 for who,status in [('other',404),('company',404),('admin',404)]:e.call(who,'/proposal/'+p['proposal_id'],status=status)
 saved=e.call('operator','/proposal/'+p['proposal_id']+'/versions',dict(expected_version=v['id'],title=v['title'],sections=v['sections'],idempotency_key=e.nonce()))
 e.call('approver','/proposal/approvals/'+q['id']+'/decision',dict(outcome='APPROVE',reason='TEST old version',idempotency_key=e.nonce()),status=409)
 assert saved['ordinal']==2


def test_two_committed_edit_transactions_prevent_lost_update(env):
 import threading
 from concurrent.futures import ThreadPoolExecutor
 from app.proposal.application import ProposalApplication
 from app.notice.domain import Actor,Denied
 e=env;p,_,_=create(e);v=e.call('operator','/proposal/versions/'+p['version_id']);barrier=threading.Barrier(2)
 def edit(label):
  try:
   with e.factory.begin() as session:
    session.execute(text("SET LOCAL lock_timeout='10s'"));app=ProposalApplication(CapabilityApplication(session,e.files,ProposalInputs(e)));barrier.wait(timeout=5)
    return app.save(Actor(e.accounts['operator']['id'],'DATCO_OPERATOR'),p['proposal_id'],v['id'],label,v['sections'],e.nonce())
  except Denied as exc:return {'status':exc.status,'reason':exc.reason}
 with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(edit,['TEST editor A','TEST editor B']))
 assert sorted(409 if 'status' in x else 200 for x in results)==[200,409]
 detail=e.call('operator','/proposal/'+p['proposal_id']);assert len(detail['versions'])==2 and detail['root']['current_ordinal']==2
 assert detail['versions'][0]==v

def migration_module():
 import importlib.util
 path=ROOT/'apps/api/alembic/versions/e863p0012026_proposal_production.py';spec=importlib.util.spec_from_file_location('proposal_migration',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def test_migration_refuses_down_with_existing_proposal_history(env):
 from alembic.operations import Operations
 from alembic.migration import MigrationContext
 e=env;create(e)
 with e.engine.begin() as connection:
  connection.exec_driver_sql('SET LOCAL search_path='+e.schema+',public')
  with Operations.context(MigrationContext.configure(connection)):
   with pytest.raises(RuntimeError,match='No data deleted'):migration_module().downgrade()

def test_new_migration_up_empty_down_up_and_legacy_notice_preservation():
 from uuid import uuid4
 from alembic.operations import Operations
 from alembic.migration import MigrationContext
 from sqlalchemy import inspect
 from app.infrastructure.database import Base,get_engine
 from app.infrastructure import notice_schema as N
 from isolation import require_test_database
 require_test_database();schema='test_proposal_migration_'+uuid4().hex;new={P.roots,P.versions,P.reviews,P.requests,P.decisions,P.files,P.completions}
 with get_engine().connect().execution_options(schema_translate_map={None:schema}) as c:
  transaction=c.begin();c.exec_driver_sql('CREATE SCHEMA '+schema);Base.metadata.create_all(c,tables=[t for t in Base.metadata.tables.values() if t not in new]);c.exec_driver_sql('SET LOCAL search_path='+schema+',public')
  old=c.execute(N.notices.insert().values(external_key='TEST legacy',title='TEST preserved Notice',current_ordinal=1).returning(N.notices)).mappings().one()
  with Operations.context(MigrationContext.configure(c)):
   m=migration_module();m.upgrade()
   assert dict(c.execute(select(N.notices).where(N.notices.c.id==old['id'])).mappings().one())==dict(old)
   for t in new:assert set(t.c.keys())=={x['name'] for x in inspect(c).get_columns(t.name,schema=schema)}
   m.downgrade();m.upgrade()
   assert c.scalar(select(func.count()).select_from(N.notices))==1
  transaction.rollback()


def test_multiple_capabilities_and_exact_coverage_are_preserved(env):
 e=env;r=e.compose('A',['A','B']);cid=r['candidate']['candidate_id']
 e.call('operator','/capability/matches/'+cid+'/review',dict(outcome='PROPOSABLE',note='TEST reviewed both service scopes and prerequisites',completion_items=completions(e,cid),idempotency_key=e.nonce()))
 p=e.call('operator','/proposal',dict(candidate_id=cid,title='TEST multiple services',idempotency_key=e.nonce()));v=e.call('operator','/proposal/versions/'+p['version_id'])
 assert set(v['manifest']['refs']['capability_version_ids'])=={e.caps[x]['version']['id'] for x in ('A','B')}
 assert v['manifest']['input']['composition']['coverage']==r['composition_data']['coverage']
 assert len(v['manifest']['capability_versions'])==2

def test_file_cannot_use_content_review_of_another_version(env):
 e=env;p,_,_=create(e);q,_,_=create(e);v=q['version_id']
 review=e.call('operator','/proposal/versions/'+v+'/review',dict(confirmed=True,note='TEST exact second version',idempotency_key=e.nonce()))
 with pytest.raises(IntegrityError,match='PROPOSAL_LINK_MISMATCH'):
  with e.factory.begin() as s:s.execute(P.files.insert().values(version_id=p['version_id'],content_review_id=review['id'],kind='DOCX',storage_key='a'*64,digest='a'*64,size=1,actor_id=e.accounts['operator']['id']))


@pytest.mark.parametrize('kind',['DOCX','PDF'])
@pytest.mark.parametrize('failure_point',['before_commit','after_commit'])
def test_export_commit_failure_has_safe_reference_and_bounded_retry(env,monkeypatch,kind,failure_point):
 from fastapi.testclient import TestClient
 from sqlalchemy.orm import Session
 from app.main import app
 from app.core.config import get_settings
 from unittest.mock import patch
 import time
 e=env;p,_,_=create(e);v=p['version_id']
 e.call('operator','/proposal/versions/'+v+'/review',dict(confirmed=True,note='TEST reviewed exact export version',idempotency_key=e.nonce()))
 before={p.name for p in e.files.root.iterdir() if p.is_file()}
 body=dict(kind=kind,idempotency_key=e.nonce());url='/proposal/versions/'+v+'/export';original=Session.commit
 def fail(session):
  if failure_point=='after_commit':original(session)
  raise RuntimeError('TEST_COMMIT_RESPONSE_FAILURE')
 with TestClient(app,raise_server_exceptions=False) as client:
  client.cookies.update(e.clients['operator'].cookies)
  with monkeypatch.context() as m:
   m.setattr(Session,'commit',fail)
   for offset in (10,20):
    with patch('time.time',return_value=time.time()+offset):
     response=client.post(url,json=body,headers={'Origin':get_settings().web_origin})
    assert response.status_code==500
 after={p.name for p in e.files.root.iterdir() if p.is_file()};created=after-before
 assert len(created)==1
 with e.factory() as session:
  rows=list(session.execute(select(P.files).where(P.files.c.version_id==v)).mappings())
 assert len(rows)==(1 if failure_point=='after_commit' else 0)
 # Retry reattaches the same bytes after rollback or replays the committed receipt.
 receipt=e.call('operator',url,body);assert e.call('operator',url,body)==receipt
 assert {p.name for p in e.files.root.iterdir() if p.is_file()}==after
 assert receipt['digest'] in created
 with e.factory() as session:assert session.scalar(select(func.count()).select_from(P.files).where(P.files.c.version_id==v))==1
 response=e.clients['approver'].get('/proposal/files/'+receipt['id']+'/download')
 assert response.status_code==404  # Not shared with the approver yet.
 e.call('other','/proposal/files/'+receipt['id']+'/download',status=404)

@pytest.mark.parametrize('outcome',['REVISION_REQUEST','REJECT'])
def test_company_nonapproval_decisions_are_exact_and_idempotent(env,outcome):
 e=env;p,_,_=create(e);v=p['version_id'];e.call('operator','/proposal/versions/'+v+'/review',dict(confirmed=True,note='TEST exact content',idempotency_key=e.nonce()))
 q=e.call('operator','/proposal/versions/'+v+'/approval',dict(idempotency_key=e.nonce()))
 body=dict(outcome=outcome,reason='TEST company decision, not approval',idempotency_key=e.nonce())
 decision=e.call('approver','/proposal/approvals/'+q['id']+'/decision',body)
 assert e.call('approver','/proposal/approvals/'+q['id']+'/decision',body)==decision
 detail=e.call('operator','/proposal/'+p['proposal_id'])
 assert detail['decisions']==[dict(detail['decisions'][0],outcome=outcome,version_id=v)]
 assert detail['requests'][0]['state']=='CLOSED'


def test_partial_migration_failure_rolls_back_and_can_retry(monkeypatch):
 from uuid import uuid4
 from alembic.operations import Operations
 from alembic.migration import MigrationContext
 from sqlalchemy import inspect
 from app.infrastructure.database import Base,get_engine
 from app.infrastructure import notice_schema as N
 from isolation import require_test_database
 require_test_database();schema='test_proposal_partial_'+uuid4().hex;new={P.roots,P.versions,P.reviews,P.requests,P.decisions,P.files,P.completions}
 with get_engine().connect().execution_options(schema_translate_map={None:schema}) as c:
  transaction=c.begin();c.exec_driver_sql('CREATE SCHEMA '+schema);Base.metadata.create_all(c,tables=[t for t in Base.metadata.tables.values() if t not in new]);c.exec_driver_sql('SET LOCAL search_path='+schema+',public')
  old=c.execute(N.notices.insert().values(external_key='TEST partial migration',title='TEST source preserved',current_ordinal=1).returning(N.notices)).mappings().one()
  with Operations.context(MigrationContext.configure(c)):
   migration=migration_module();execute=migration.op.execute;calls=[]
   def fail(statement,*args,**kwargs):
    calls.append(statement)
    if len(calls)==3:raise RuntimeError('TEST_PARTIAL_DDL_FAILURE')
    return execute(statement,*args,**kwargs)
   with pytest.raises(RuntimeError,match='TEST_PARTIAL_DDL_FAILURE'):
    with c.begin_nested():
     with monkeypatch.context() as m:m.setattr(migration.op,'execute',fail);migration.upgrade()
   assert not ({t.name for t in new}&set(inspect(c).get_table_names(schema=schema)))
   assert dict(c.execute(select(N.notices).where(N.notices.c.id==old['id'])).mappings().one())==dict(old)
   migration.upgrade();assert {t.name for t in new}<=set(inspect(c).get_table_names(schema=schema))
  transaction.rollback()


def test_approval_scoped_public_documents_survive_company_source_lockdown(env):
 e=env;p,_,_=create(e);vid=p['version_id']
 e.call('approver','/proposal/versions/'+vid,status=404)
 e.call('operator','/proposal/versions/'+vid+'/review',dict(confirmed=True,note='TEST_INTERNAL_CONTENT_REVIEW_NOT_PUBLIC',idempotency_key=e.nonce()))
 q=e.call('operator','/proposal/versions/'+vid+'/approval',dict(idempotency_key=e.nonce()))
 visible=e.call('approver','/proposal/versions/'+vid);assert set(visible['manifest'])=={'refs'} and 'TEST_INTERNAL_CONTENT_REVIEW_NOT_PUBLIC' not in str(visible)
 detail=e.call('approver','/proposal/'+p['proposal_id']);assert detail['content_reviews']==[]
 file=e.call('operator','/proposal/versions/'+vid+'/export',dict(kind='DOCX',idempotency_key=e.nonce()))
 response=e.clients['approver'].get('/proposal/files/'+file['id']+'/download');assert response.status_code==200 and sha256(response.content).hexdigest()==file['digest']
 from fastapi.testclient import TestClient
 from app.main import app
 from app.core.config import get_settings
 # Same synthetic Company membership, same Role, but not the designated approver.
 with e.factory.begin() as session:
  from app.infrastructure.notice_store import SqlNoticeStore
  from app.infrastructure.local_auth import hash_password
  user=SqlNoticeStore(session).add('actors',username='TEST_UNASSIGNED_'+e.nonce(),role='COMPANY_APPROVER',password_hash=hash_password('TEST_UNASSIGNED_PASSWORD'))
 e.memberships[user['id']]='TEST_COMPANY_A'
 with TestClient(app) as client:
  assert client.post('/notice/session',json={'username':user['username'],'password':'TEST_UNASSIGNED_PASSWORD'},headers={'Origin':get_settings().web_origin}).status_code==200
  for path in ['/proposal/versions/'+vid,'/proposal/files/'+file['id']+'/download','/proposal/'+p['proposal_id']]:assert client.get(path).status_code==404
  assert client.post('/proposal/approvals/'+q['id']+'/decision',json=dict(outcome='APPROVE',reason='TEST not designated',idempotency_key=e.nonce()),headers={'Origin':get_settings().web_origin}).status_code==404
 decision=e.call('approver','/proposal/approvals/'+q['id']+'/decision',dict(outcome='APPROVE',reason='TEST exact assigned version',idempotency_key=e.nonce()));assert decision['outcome']=='APPROVE'
 assert any(d['id']==decision['id'] and d['version_id']==vid for d in e.call('approver','/proposal/'+p['proposal_id'])['decisions'])


def test_real_company_provider_approval_projection_and_workspace_context(tmp_path,monkeypatch):
 # Real W1 records/provider plus normal Proposal commands in an isolated schema.
 from app.company.application import CompanyApplication
 from app.company.provider import CompanyProvider
 from app.proposal.policy import tasks
 from app.infrastructure.notice_store import SqlNoticeStore
 from app.infrastructure.local_auth import hash_password
 from app.core.config import get_settings
 from fastapi.testclient import TestClient
 from app.main import app
 import app.api.company as company_api
 with committed_environment(tmp_path/'real-company-approval') as e:
  with monkeypatch.context() as patch:
   patch.setattr(company_api,'application',lambda session:CompanyApplication(session,e.files))
   c=e.call('company','/company',dict(name='TEST real provider company',business_number=str(int(e.nonce()[:12],16))[-10:].zfill(10)))
   with e.factory.begin() as session:
    person=SqlNoticeStore(session).add('actors',username='TEST_REAL_APPROVER_'+e.nonce(),role='COMPANY_APPROVER',password_hash=hash_password(e.password))
   e.accounts['approver']=person;e.clients['approver']=TestClient(app);e.call('approver','/notice/session',dict(username=person['username'],password=e.password))
   for name in ('operator','approver'):e.call('admin','/company/'+c['id']+'/access',dict(username=e.accounts[name]['username']))
   site=e.call('company','/company/'+c['id']+'/sites',{'data':dict(name='TEST approved site',address='TEST location')})['site']
   raw='기업명: TEST real provider company'.encode('utf8');response=e.clients['company'].post('/company/'+c['id']+'/files',content=raw,headers={'Origin':get_settings().web_origin,'X-Upload-Name':'TEST-real.txt'});assert response.status_code==200;source=response.json()
   e.call('operator','/company/files/'+source['id']+'/parse',{})
   candidate=next(x for x in e.call('company','/company/'+c['id'])['candidates'] if x['mode']=='RULE_BASED_EXTRACTION')
   e.call('company','/company/candidates/'+candidate['id']+'/acknowledge',dict(agreed=True,note='TEST source acknowledged'))
   fact=e.call('operator','/company/candidates/'+candidate['id']+'/review',dict(outcome='CONFIRM_NEW_VALUE',note='TEST_PRIVATE_FACT_NOTE'))['version']
   original=e.contexts['TEST_IMPROVEMENT_A']['original_text'];data=dict(title='TEST company improvement',original_text=original,site_id=site['id'],as_is='TEST as-is',problem='TEST problem',goal='TEST goal',to_be='TEST to-be',fact_version_ids=[fact['id']],evidence_ids=[candidate['evidence_id']])
   initial=e.call('company','/company/'+c['id']+'/improvements',{'data':data});e.call('company','/company/improvements/'+initial['id']+'/actions',dict(action='SUBMIT',note='TEST original submitted'))
   current=e.call('operator','/company/'+c['id']+'/improvements',dict(data=data,improvement_id=initial['improvement_id'],expected_ordinal=1));e.call('company','/company/improvements/'+current['id']+'/actions',dict(action='ACKNOWLEDGE',note='TEST exact version acknowledged'));e.call('operator','/company/improvements/'+current['id']+'/actions',dict(action='CONFIRM',note='TEST current evidence reviewed'))
   e.contexts['TEST_IMPROVEMENT_A']=e.call('operator','/company/improvements/'+current['id']+'/context')
   patch.setattr(api,'application',lambda session:CapabilityApplication(session,e.files,CompanyProvider(CompanyApplication(session,e.files))))
   r=e.compose('A',['A']);cid=r['candidate']['candidate_id'];detail=e.call('operator','/capability/matches/'+cid)
   items=[dict(task_id=t['id'],decision='CONFIRMED',note='TEST reviewed item against synthetic source',proof_ids=[candidate['evidence_id']],notice_evidence_id=t.get('notice_evidence_id')) for t in tasks(detail)]
   e.call('operator','/capability/matches/'+cid+'/review',dict(outcome='PROPOSABLE',note='TEST complete synthetic review',completion_items=items,idempotency_key=e.nonce()))
   p=e.call('operator','/proposal',dict(candidate_id=cid,title='TEST public proposal title',idempotency_key=e.nonce()));vid=p['version_id']
   assert not e.call('approver','/workspace')['proposals']
   e.call('operator','/proposal/versions/'+vid+'/review',dict(confirmed=True,note='TEST_PRIVATE_PROPOSAL_NOTE',idempotency_key=e.nonce()));q=e.call('operator','/proposal/versions/'+vid+'/approval',dict(idempotency_key=e.nonce()))
   workspace=e.call('approver','/workspace');company=next(x for x in workspace['companies'] if x['id']==c['id']);assert [x['version_id'] for x in company['improvements']]==[current['id']];assert company['improvements'][0]['title']=='TEST public proposal title';assert company['sites']==[dict(id=site['id'],name='TEST approved site')];assert len(workspace['proposals'])==1
   for path in ['/workspace','/company/'+c['id'],'/proposal/'+p['proposal_id'],'/proposal/versions/'+vid]:
    text=str(e.call('approver',path));assert 'TEST_PRIVATE_FACT_NOTE' not in text and 'TEST_PRIVATE_PROPOSAL_NOTE' not in text
   e.call('approver','/company/files/'+source['id']+'/download',status=403);e.call('approver','/company/improvements/'+current['id']+'/context',status=403)
   evidence_url='/proposal/matches/'+cid+'/evidence/'+candidate['evidence_id']+'/download'
   e.call('approver',evidence_url,status=403)
   response=e.clients['operator'].get(evidence_url);assert response.status_code==200 and response.content==raw
   exported=e.call('operator','/proposal/versions/'+vid+'/export',dict(kind='DOCX',idempotency_key=e.nonce()));response=e.clients['approver'].get('/proposal/files/'+exported['id']+'/download');assert response.status_code==200 and sha256(response.content).hexdigest()==exported['digest']
   decision=e.call('approver','/proposal/approvals/'+q['id']+'/decision',dict(outcome='APPROVE',reason='TEST exact version approved',idempotency_key=e.nonce()));assert decision['outcome']=='APPROVE'
