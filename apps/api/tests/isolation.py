"""Fail closed before any integration/harness writes; no product auth bypass."""
import os,re
from sqlalchemy import text
from app.infrastructure.database import get_engine

def require_test_database(engine=None):
 expected=os.environ.get('DATCO_TEST_DATABASE','')
 role=os.environ.get('DATCO_TEST_DB_ROLE','')
 if not re.fullmatch(r'datco_test_[a-f0-9]{12}',expected) or not re.fullmatch(r'datco_test_role_[a-f0-9]{12}',role):
  raise RuntimeError('ISOLATION_REQUIRED: run tests/isolated_run.py; normal DATABASE_URL cannot run writing tests')
 engine=engine or get_engine()
 with engine.connect() as c:
  row=dict(c.execute(text("select current_database() as database,current_schema() as schema,current_setting('search_path') as search_path,inet_server_addr()::text as server,inet_server_port() as port,current_user as db_user,current_setting('application_name') as application_name")).mappings().one())
  privileges=c.execute(text('select rolsuper,rolcreatedb,rolcreaterole from pg_roles where rolname=current_user')).one()
  if row['database']!=expected or row['db_user']!=role or any(privileges):
   raise RuntimeError('ISOLATION_TARGET_MISMATCH: writing tests stopped')
  return row
