"""Owns a disposable DB/least-privilege role and fresh Web/API/Worker. No shared writes."""
import argparse,hashlib,json,os,secrets,socket,subprocess,sys,time,urllib.request
from pathlib import Path
from uuid import uuid4
import psycopg
from psycopg import sql
from sqlalchemy import create_engine,select,text,inspect,Table,MetaData
from sqlalchemy.orm import sessionmaker
from app.core.config import ROOT,get_settings
from app.infrastructure.database import Base,get_engine
from app.infrastructure.notice_store import SqlNoticeStore
from app.infrastructure.notice_documents import LocalPrivateFiles
from app.infrastructure.local_auth import hash_password
from app.capability.application import CapabilityApplication
from app.demo import load_input
from app.main import app
from isolation import require_test_database

API=ROOT/'apps/api';WEB=ROOT/'apps/web'
def digest_shared(engine):
 with engine.connect() as c:
  c.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
  existing=set(inspect(c).get_table_names(schema='public'))
  result={}
  for name in Base.metadata.tables:
   if name not in existing:result[name]={'exists':False};continue
   actual=Table(name,MetaData(),autoload_with=c,schema='public')
   rows=[dict(r) for r in c.execute(select(actual).order_by(actual.c.id)).mappings()]
   result[name]={'exists':True,'columns':list(actual.c.keys()),'count':len(rows),'sha256':hashlib.sha256(json.dumps(rows,sort_keys=True,default=str,separators=(',',':')).encode()).hexdigest()}
  return result

def read_public_inputs(engine):
 result=[];files=LocalPrivateFiles(ROOT/'storage/private/notice')
 with engine.connect() as c:
  c.execute(text('SET TRANSACTION READ ONLY'))
  with sessionmaker(bind=c)() as s:
   st=SqlNoticeStore(s)
   for n in st.rows('notices'):
    if not n['title'].startswith(('2026년 연구개발특구','2026년 에너지기술')):continue
    for v in st.rows('versions',notice_id=n['id']):
     if v['mode']=='LIVE':result.append((n,v,[(r,files.read(r['storage_key'],r['digest']) if r['storage_key'] else None) for r in st.rows('sources',version_id=v['id'])]))
 if len(result)!=2:raise RuntimeError('STORED_KOREAN_INPUTS_UNAVAILABLE')
 return result

def free_port():
 with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
def wait_url(url,seconds=90):
 until=time.monotonic()+seconds
 while time.monotonic()<until:
  try:
   with urllib.request.urlopen(url,timeout=2) as r:
    if r.status==200:return json.loads(r.read()) if 'identity' in url else True
  except (OSError,ValueError):pass
  time.sleep(.2)
 raise RuntimeError('ISOLATED_SERVICE_NOT_READY')

def main():
 parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['baseline','verify','ui','backend','r04']);args=parser.parse_args()
 nonce=uuid4().hex[:12];dbname='datco_test_'+nonce;role='datco_test_role_'+nonce
 directory=ROOT/'storage/private/runtime/test-isolation'/nonce;directory.mkdir(parents=True)
 normal=get_engine();before=digest_shared(normal);public_inputs=read_public_inputs(normal)
 (directory/'public-before.json').write_text(json.dumps(before,indent=2),encoding='utf-8')
 source_hash=hashlib.sha256((ROOT/'_local_inputs/dmp_features_649.json').read_bytes()).hexdigest()
 if source_hash!='28b1967ed77360d0fcc6d5525f6d7395fd899865b2e01e358402edc347d1d368':raise RuntimeError('SOURCE_HASH_MISMATCH')
 base=normal.url;password=secrets.token_urlsafe(32);admin=psycopg.connect(host=base.host,port=base.port,dbname=base.database,user=base.username,password=base.password,autocommit=True)
 children=[];handles=[];test_engine=None;created_db=False;created_role=False
 report={'phase':args.phase,'nonce':nonce,'database':dbname,'role':role,'source_hash':source_hash,'commands':[]}
 env=os.environ.copy();test_url=base.set(database=dbname,username=role,password=password,query={'application_name':'datco-tests-'+nonce,'sslmode':'disable'})
 env.update(DATABASE_URL=test_url.render_as_string(hide_password=False),DATCO_TEST_DATABASE=dbname,DATCO_TEST_DB_ROLE=role,DATCO_TEST_NONCE=nonce,PYTHONPATH=str(API)+os.pathsep+str(API/'tests'),PYTHONIOENCODING='utf-8',WEB_ORIGIN='http://localhost:3000',DATCO_TEST_FILES=str(directory/'notice'),DATCO_TEST_WORKER_READY=str(directory/'worker-ready.json'))
 # An inherited Live key cannot be used in any isolated subprocess.
 env['BIZINFO_API_KEY']=''
 def run(label,command,cwd,child_env=env):
  with (directory/(label+'.log')).open('w',encoding='utf-8') as log:
   completed=subprocess.run(command,cwd=cwd,env=child_env,stdout=log,stderr=subprocess.STDOUT)
  report['commands'].append({'label':label,'exit':completed.returncode});print(json.dumps({'step':label,'exit':completed.returncode}),flush=True)
  return completed.returncode
 def start(label,command,cwd,child_env):
  log=(directory/(label+'.log')).open('w',encoding='utf-8');handles.append(log)
  proc=subprocess.Popen(command,cwd=cwd,env=child_env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
  children.append(proc);return proc
 try:
  admin.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION PASSWORD {}').format(sql.Identifier(role),sql.Literal(password)));created_role=True
  admin.execute(sql.SQL('CREATE DATABASE {} OWNER {}').format(sql.Identifier(dbname),sql.Identifier(role)));created_db=True
  test_engine=create_engine(test_url)
  # Guard works on actual connections, not environment labels alone.
  os.environ.update({k:env[k] for k in ['DATCO_TEST_DATABASE','DATCO_TEST_DB_ROLE']})
  report['database_identity']=require_test_database(test_engine)
  restricted_normal=create_engine(base.set(username=role,password=password))
  try:
   with restricted_normal.connect() as c:
    c.execute(text('SET TRANSACTION READ ONLY'))
    rights=c.execute(text("select has_database_privilege(current_user,current_database(),'CREATE'),has_schema_privilege(current_user,'public','CREATE'),exists(select 1 from pg_tables where schemaname='public' and (has_table_privilege(current_user,quote_ident(schemaname)||'.'||quote_ident(tablename),'INSERT') or has_table_privilege(current_user,quote_ident(schemaname)||'.'||quote_ident(tablename),'UPDATE') or has_table_privilege(current_user,quote_ident(schemaname)||'.'||quote_ident(tablename),'DELETE') or has_table_privilege(current_user,quote_ident(schemaname)||'.'||quote_ident(tablename),'TRUNCATE')))" )).one()
    if any(rights):raise RuntimeError('SHARED_DB_WRITE_PRIVILEGE_NOT_BLOCKED')
    report['shared_write_privileges']=list(rights)
  finally:restricted_normal.dispose()
  print(json.dumps({'isolation_preflight':report['database_identity'],'shared_write_privileges':report['shared_write_privileges']}),flush=True)
  if run('migration',[sys.executable,'-m','alembic','upgrade','head'],API):raise RuntimeError('ISOLATED_MIGRATION_FAILED')
  factory=sessionmaker(bind=test_engine);files=LocalPrivateFiles(directory/'notice');username='TEST_E2E_'+nonce;actor_password=secrets.token_urlsafe(28)
  with factory.begin() as s:
   st=SqlNoticeStore(s);st.add('actors',username=username,role='DATCO_OPERATOR',password_hash=hash_password(actor_password))
   for name in ['normal','conflict','partial']:load_input(st,files,name)
   for n,v,inputs in public_inputs:
    copied=st.add('notices',external_key='ISOLATED_COPY_'+uuid4().hex,title=n['title'],current_ordinal=1)
    version=st.add('versions',notice_id=copied['id'],ordinal=1,mode='LIVE',metadata=dict(v['metadata'],test_copy=True))
    for r,data in inputs:
     key,digest=files.put(data) if data else (None,None)
     st.add('sources',version_id=version['id'],name=r['name'],media_type=r['media_type'],provenance='ISOLATED TEST COPY OF STORED PUBLIC DOCUMENT; NO LIVE ACQUISITION',storage_key=key,digest=digest)
   CapabilityApplication(s,files).import_inventory((ROOT/'_local_inputs/dmp_features_649.json').read_bytes())
  if args.phase=='baseline':
   run('backend-baseline',[sys.executable,'-m','pytest','tests/test_capability_scenarios.py','-v','--tb=short'],API)
  elif args.phase in ('verify','backend'):
   run('backend',[sys.executable,'-m','pytest','-q','--tb=short','--junitxml='+str(directory/'backend.xml')],API)
   run('integration',[sys.executable,'-m','pytest','-m','integration','-q','--tb=short','--junitxml='+str(directory/'integration.xml')],API)
   run('migration-check',[sys.executable,'-m','alembic','check'],API)
  if args.phase=='r04':
   run('r04',[sys.executable,'-m','pytest','tests/test_analysis_lineage.py','tests/test_analysis_migration.py','tests/test_capability_scenarios.py','-q','--tb=short'],API)
   run('migration-check',[sys.executable,'-m','alembic','check'],API)
  if args.phase in ('backend','r04'):
   return 1 if any(step['exit'] for step in report['commands']) else 0
  api_port,web_port=free_port(),free_port()
  while web_port==api_port:web_port=free_port()
  origin='http://localhost:'+str(web_port)
  browser_env=dict(env,WEB_ORIGIN=origin,DATCO_E2E_BASE_URL=origin,DATCO_E2E_USER=username,DATCO_E2E_PASSWORD=actor_password,DATCO_E2E_SERVER_READY='1',API_ORIGIN='http://127.0.0.1:'+str(api_port),CAPABILITY_API_ORIGIN='http://127.0.0.1:'+str(api_port),DATCO_TEST_DIST_DIR='.next/datco-e2e-'+nonce)
  test_tsconfig=WEB/browser_env['DATCO_TEST_DIST_DIR'].replace('datco-e2e-','datco-config-')/'tsconfig.json';test_tsconfig.parent.mkdir(parents=True,exist_ok=True)
  test_tsconfig.write_text(json.dumps({'extends':'../../tsconfig.json','compilerOptions':{'paths':{'@/*':[str(WEB/'src/*')]}},'include':[str(WEB/'next-env.d.ts'),str(WEB/'src/**/*.ts'),str(WEB/'src/**/*.tsx'),str(WEB/'tests/**/*.ts'),str(WEB/browser_env['DATCO_TEST_DIST_DIR']/'types/**/*.ts'),str(WEB/browser_env['DATCO_TEST_DIST_DIR']/'dev/types/**/*.ts')],'exclude':[str(WEB/'node_modules')]}),encoding='utf-8')
  start('api',[sys.executable,'-m','uvicorn','isolated_server:app','--host','127.0.0.1','--port',str(api_port)],API,browser_env)
  identity=wait_url(browser_env['API_ORIGIN']+'/__test/identity')
  if identity['database']!=dbname or identity['nonce']!=nonce:raise RuntimeError('ISOLATED_API_IDENTITY_MISMATCH')
  report['api_identity']=identity;report['api_url']=browser_env['API_ORIGIN'];report['web_url']=origin
  worker=start('worker',[sys.executable,'tests/isolated_worker.py'],API,browser_env)
  worker_ready=directory/'worker-ready.json';until=time.monotonic()+15
  while not worker_ready.exists():
   if worker.poll() is not None or time.monotonic()>until:raise RuntimeError('ISOLATED_WORKER_NOT_READY')
   time.sleep(.1)
  report['worker_identity']=json.loads(worker_ready.read_text(encoding='utf-8'))
  if report['worker_identity']['database']!=dbname or report['worker_identity']['db_user']!=role:raise RuntimeError('ISOLATED_WORKER_TARGET_MISMATCH')
  start('web',['cmd.exe','/c','npm.cmd','run','dev','--','--port',str(web_port)],WEB,browser_env)
  wait_url(origin+'/capability',120)
  # Proxy must authenticate a test-only user and read the exact isolated Import.
  from http.cookiejar import CookieJar
  jar=CookieJar();opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
  body=json.dumps({'username':username,'password':actor_password}).encode()
  with opener.open(urllib.request.Request(origin+'/api/notice/session',body,headers={'Content-Type':'application/json','Origin':origin})) as r:assert r.status==200
  with opener.open(origin+'/api/capability/features') as r:page=json.load(r)
  with factory() as s:expected_import=CapabilityApplication(s).rows(__import__('app.infrastructure.capability_schema',fromlist=['imports']).imports)[0]['id']
  if page['total']!=649 or page['import']['id']!=expected_import:raise RuntimeError('WEB_PROXY_TEST_DATABASE_MISMATCH')
  report['web_proxy_database_verified']=True
  command=['cmd.exe','/c','npm.cmd','run','test:e2e','--']
  if args.phase=='baseline':command+=['tests/capability-scenarios.spec.ts']
  command+=['--workers=1']
  run('playwright',command,WEB,browser_env)
  if args.phase in ('verify','ui'):
   run('lint',['cmd.exe','/c','npm.cmd','run','lint'],WEB,browser_env)
   # Stop only the owned Web before building into its dedicated Next directory.
   subprocess.run(['taskkill','/PID',str(children[-1].pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   children[-1].wait(timeout=20)
   run('build',['cmd.exe','/c','npm.cmd','run','build'],WEB,browser_env)
   run('api-types',[sys.executable,'tests/verify_api_types.py',str(directory)],API,env)
 finally:
  for proc in reversed(children):
   if proc.poll() is None:
    if os.name=='nt':subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    else:proc.terminate()
    try:proc.wait(timeout=20)
    except subprocess.TimeoutExpired:proc.kill();proc.wait()
  for log in handles:log.close()
  if test_engine:test_engine.dispose()
  # Only this newly created, verified nonce database/role is disposable.
  if created_db:
   found=admin.execute('select datname,pg_get_userbyid(datdba) from pg_database where datname=%s',(dbname,)).fetchone()
   if found!=(dbname,role):raise RuntimeError('CLEANUP_DATABASE_IDENTITY_MISMATCH')
   admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(dbname)))
  if created_role:admin.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(role)))
  admin.close()
  after=digest_shared(normal);(directory/'public-after.json').write_text(json.dumps(after,indent=2),encoding='utf-8')
  report['public_changed_tables']=[k for k in before if before[k]!=after[k]]
  report['test_database_and_role_removed']=created_db and created_role
  (directory/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
  print(json.dumps({'report':str(directory/'report.json'),'public_changed_tables':report['public_changed_tables'],'test_cleanup':report['test_database_and_role_removed']}),flush=True)
  if report['public_changed_tables']:raise RuntimeError('SHARED_DATABASE_CHANGED')
 return 1 if any(step['exit'] for step in report['commands']) else 0
if __name__=='__main__':
 try:raise SystemExit(main())
 except Exception as exc:
  print('ISOLATED_RUN_ABORTED: '+type(exc).__name__,flush=True)
  raise SystemExit(2)
