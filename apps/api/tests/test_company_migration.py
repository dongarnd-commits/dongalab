from v14_migration_chain import ThroughLatest,AFTER_COMPANY
from registration_sources import number as synthetic_business_number
"""Actual frozen migration chain, guarded schemas and non-destructive Down."""
from uuid import uuid4
import importlib.util
import pytest
from sqlalchemy import inspect,text
from sqlalchemy.orm import Session
from alembic.migration import MigrationContext
from alembic.operations import Operations
from app.core.config import ROOT
from app.infrastructure.database import Base,get_engine
from app.infrastructure.notice_store import SqlNoticeStore
from app.infrastructure.notice_documents import LocalPrivateFiles
from app.company.application import CompanyApplication
from app.notice.domain import Actor
from isolation import require_test_database
pytestmark=pytest.mark.integration

def load(name):
 path=ROOT/'apps/api/alembic/versions'/name;spec=importlib.util.spec_from_file_location('test_company_'+name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
@pytest.fixture
def migration():
 require_test_database();schema='test_company_migration_'+uuid4().hex;connection=get_engine().connect().execution_options(schema_translate_map={None:schema});outer=connection.begin();connection.exec_driver_sql('CREATE SCHEMA '+schema);connection.exec_driver_sql('SET LOCAL search_path = '+schema+', public')
 try:
  with Operations.context(MigrationContext.configure(connection)):
   for filename in ['6d5ba2015303_notice_first_slice.py','a44df74db1ac_bizinfo_ingestion.py','b730cf01a649_capability_catalog.py','c941a0042026_common_analysis_lineage.py','d752a0012026_immutable_matching_inputs.py','e863p0012026_proposal_production.py']:load(filename).upgrade()
   yield connection,ThroughLatest(load('f974c0012026_company_workflow.py'),AFTER_COMPANY),schema
 finally:outer.rollback();connection.close()

def assert_model(c,schema):
 for name,t in Base.metadata.tables.items():
  columns={x['name']:x for x in inspect(c).get_columns(name,schema=schema)}
  assert set(columns)==set(t.c.keys()),name
  assert all(columns[col.name]['nullable']==col.nullable for col in t.c),name

def test_company_up_empty_down_reup_preserves_notice(migration):
 c,m,schema=migration;key=str(uuid4());c.execute(text("INSERT INTO notices(id,external_key,title,current_ordinal) VALUES (:id,:key,'TEST preserved Notice',1)"),dict(id=key,key='TEST_'+key))
 m.upgrade();assert_model(c,schema);m.downgrade()
 assert 'companies' not in inspect(c).get_table_names(schema=schema)
 assert c.execute(text('SELECT title FROM notices WHERE id=:id'),dict(id=key)).scalar_one()=='TEST preserved Notice'
 m.upgrade();assert_model(c,schema)

def test_company_history_down_refused_without_data_loss(migration,tmp_path):
 c,m,schema=migration;m.upgrade();session=Session(c,join_transaction_mode='create_savepoint');store=SqlNoticeStore(session);row=store.add('actors',username='TEST_'+uuid4().hex,role='COMPANY_EDITOR',password_hash='TEST_NOT_LOGIN')
 app=CompanyApplication(session,LocalPrivateFiles(tmp_path));company=app.register(Actor(row['id'],'COMPANY_EDITOR'),dict(name='TEST source company',business_number=synthetic_business_number('123456789')));session.flush();c.exec_driver_sql('SET CONSTRAINTS ALL IMMEDIATE')
 with pytest.raises(RuntimeError,match='COMPANY_HISTORY_EXISTS'):m.downgrade()
 assert c.execute(text('SELECT name FROM companies WHERE id=:id'),dict(id=company['id'])).scalar_one()=='TEST source company'
 session.close()

def test_partial_ddl_failure_rolls_back_then_retry_succeeds(migration,monkeypatch):
 c,m,schema=migration;execute=m.op.execute;count=0
 def fail(statement,*args,**kwargs):
  nonlocal count
  count+=1
  if count==3:raise RuntimeError('TEST_DDL_FAILURE')
  return execute(statement,*args,**kwargs)
 with pytest.raises(RuntimeError,match='TEST_DDL_FAILURE'):
  with c.begin_nested():
   with monkeypatch.context() as patch:
    patch.setattr(m.op,'execute',fail);m.upgrade()
 assert 'companies' not in inspect(c).get_table_names(schema=schema)
 m.upgrade();assert_model(c,schema)


def test_registration_increment_rollback_and_retry(migration):
 c,m,schema=migration;m.upgrade()
 increment=load('fd18e0012026_company_file_reregistration.py')
 increment.downgrade()
 assert any(x['column_names']==['company_id','digest'] for x in inspect(c).get_unique_constraints('company_files',schema=schema))
 increment.upgrade()
 assert not any(x['column_names']==['company_id','digest'] for x in inspect(c).get_unique_constraints('company_files',schema=schema))
 assert any(x['name']=='ix_company_files_company_digest' for x in inspect(c).get_indexes('company_files',schema=schema))


def test_registration_increment_existing_data_compatibility_and_safe_down(migration,tmp_path):
 c,m,schema=migration;m.upgrade();increment=load('fd18e0012026_company_file_reregistration.py');increment.downgrade()
 session=Session(c,join_transaction_mode='create_savepoint');store=SqlNoticeStore(session)
 actor=store.add('actors',username='TEST_'+uuid4().hex,role='COMPANY_EDITOR',password_hash='TEST_NOT_LOGIN')
 who=Actor(actor['id'],'COMPANY_EDITOR');app=CompanyApplication(session,LocalPrivateFiles(tmp_path))
 company=app.register(who,dict(name='TEST compatibility',business_number=synthetic_business_number()))
 old=app.upload(who,company['id'],'TEST.txt',b'TEST retained original')
 session.flush();before=c.execute(text('SELECT * FROM company_files WHERE id=:id'),{'id':old['id']}).mappings().one()
 increment.upgrade()
 assert dict(c.execute(text('SELECT * FROM company_files WHERE id=:id'),{'id':old['id']}).mappings().one())==dict(before)
 increment.downgrade();increment.upgrade()
 app.file_event(who,old['id'],'CANCELLED','TEST retained history')
 new=app.upload(who,company['id'],'TEST.txt',b'TEST retained original');session.flush()
 assert old['id']!=new['id']
 with pytest.raises(RuntimeError,match='COMPANY_FILE_REGISTRATION_HISTORY_EXISTS'):increment.downgrade()
 assert c.scalar(text('SELECT count(*) FROM company_files'))==2
 assert app.files.read(old['storage_key'],old['digest'])==b'TEST retained original'
 session.close()
