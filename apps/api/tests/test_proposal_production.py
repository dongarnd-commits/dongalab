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
