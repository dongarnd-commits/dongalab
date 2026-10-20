"""CI-only provisioning: ephemeral loopback PostgreSQL, never normal settings DB."""
import os,sys,json,secrets,subprocess,signal,time,urllib.request,socket
from pathlib import Path
from uuid import uuid4
import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url
ROOT=Path(__file__).resolve().parents[3];API=ROOT/'apps/api';WEB=ROOT/'apps/web'
TESTS=['test_notice_slice.py','test_notice_korean.py','test_bizinfo.py','test_confirmed_notice_reader.py','test_analysis_lineage.py','test_analysis_migration.py','test_capability_matching_comparison.py','test_matching_integrity.py','test_proposal_preparation.py','test_proposal_production.py','test_company_workflow.py','test_company_migration.py','test_workspace.py']
def main():
 phase=sys.argv[1];assert phase in ('integration','proposal','e2e')
 # No fallback to DATABASE_URL or .env. CI admin only provisions this disposable service.
 url=make_url(os.environ['DATCO_CI_ADMIN_URL'])
 assert url.host in ('127.0.0.1','localhost') and url.database=='datco_ci_admin'
 nonce=uuid4().hex[:12];db='datco_test_'+nonce;role='datco_test_role_'+nonce;password=secrets.token_urlsafe(32)
 out=ROOT/'storage/private/runtime/ci'/nonce;out.mkdir(parents=True)
 env=dict(os.environ,DATABASE_URL=url.set(database=db,username=role,password=password).render_as_string(hide_password=False),DATCO_TEST_DATABASE=db,DATCO_TEST_DB_ROLE=role,DATCO_TEST_NONCE=nonce,DATCO_CI_SYNTHETIC='1',DATCO_TEST_PYTHON=sys.executable,BIZINFO_API_KEY='',PYTHONPATH=str(API)+os.pathsep+str(API/'tests'),PYTHONIOENCODING='utf-8',DATCO_TEST_FILES=str(out/'files'),DATCO_TEST_WORKER_READY=str(out/'worker-ready.json'))
 env.pop('DATCO_CI_ADMIN_URL',None)
 admin=psycopg.connect(host=url.host,port=url.port,dbname=url.database,user=url.username,password=url.password,autocommit=True)
 made_db=made_role=False;children=[];logs=[]
 def run(command,cwd=API):
  if os.name=='nt' and command[0]=='npm':command=['cmd.exe','/c','npm.cmd',*command[1:]]
  subprocess.run(command,cwd=cwd,env=env,check=True)
 def port():
  with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
 def wait(address):
  until=time.monotonic()+120
  while time.monotonic()<until:
   if any(p.poll() is not None for p in children):raise RuntimeError('CI_CHILD_EXITED')
   try:
    with urllib.request.urlopen(address,timeout=2) as r:
     if r.status==200:return json.load(r) if 'identity' in address else True
   except (OSError,ValueError):pass
   time.sleep(.3)
  raise RuntimeError('CI_SERVICE_TIMEOUT')
 def start(label,command,cwd):
  log=(out/(label+'.log')).open('w');logs.append(log)
  if os.name=='nt' and command[0]=='npm':command=['cmd.exe','/c','npm.cmd',*command[1:]]
  children.append(subprocess.Popen(command,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name!='nt',creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0))
 try:
  admin.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT PASSWORD {}').format(sql.Identifier(role),sql.Literal(password)));made_role=True
  admin.execute(sql.SQL('CREATE DATABASE {} OWNER {}').format(sql.Identifier(db),sql.Identifier(role)));made_db=True
  # Dedicated connection identity is independently checked by existing integration guards.
  run([sys.executable,'-c','from isolation import require_test_database; import json; print(json.dumps(require_test_database()))'])
  run([sys.executable,'-m','alembic','upgrade','head'])
  run([sys.executable,'-m','alembic','check'])
  if phase in ('integration','proposal'):run([sys.executable,'-m','pytest',*[str(Path('tests')/t) for t in (TESTS if phase=='integration' else ['test_proposal_production.py'])],*(['--maxfail=1'] if phase=='proposal' else []),'-v','--tb=short','--junitxml='+str(out/'integration.xml')])
  else:
   api_port,web_port=port(),port()
   while web_port==api_port:web_port=port()
   origin='http://localhost:'+str(web_port)
   env.update(WEB_ORIGIN=origin,API_ORIGIN='http://127.0.0.1:'+str(api_port),CAPABILITY_API_ORIGIN='http://127.0.0.1:'+str(api_port),DATCO_E2E_BASE_URL=origin,DATCO_E2E_SERVER_READY='1')
   # Seed public demo Notice only; private DMP and stored Live documents are never read.
   user='TEST_CI_'+nonce;pw=secrets.token_urlsafe(24)
   env.update(DATCO_E2E_USER=user,DATCO_E2E_PASSWORD=pw)
   code="from app.infrastructure.database import get_engine; from sqlalchemy.orm import sessionmaker; from app.infrastructure.notice_store import SqlNoticeStore; from app.infrastructure.notice_documents import LocalPrivateFiles; from app.infrastructure.local_auth import hash_password; from app.demo import load_input; import os; from pathlib import Path\nwith sessionmaker(bind=get_engine()).begin() as s:\n st=SqlNoticeStore(s);st.add('actors',username=os.environ['DATCO_E2E_USER'],role='DATCO_OPERATOR',password_hash=hash_password(os.environ['DATCO_E2E_PASSWORD']));[load_input(st,LocalPrivateFiles(Path(os.environ['DATCO_TEST_FILES'])),name) for name in ('normal','conflict','partial')]"
   run([sys.executable,'-c',code])
   env.update(DATCO_TEST_COMPANY='1',DATCO_TEST_COMPANY_READY=str(out/'company-ready.json'),DATCO_TEST_PROPOSAL='1',DATCO_TEST_PROPOSAL_READY=str(out/'proposal-ready.json'),DATCO_TEST_DIST_DIR='.next/datco-e2e-'+nonce)
   config=WEB/('.next/datco-config-'+nonce)/'tsconfig.json';config.parent.mkdir(parents=True,exist_ok=True)
   config.write_text(json.dumps({'extends':'../../tsconfig.json','compilerOptions':{'paths':{'@/*':[str(WEB/'src/*')]}},'include':[str(WEB/'next-env.d.ts'),str(WEB/'src/**/*.ts'),str(WEB/'src/**/*.tsx'),str(WEB/'tests/**/*.ts'),str(WEB/env['DATCO_TEST_DIST_DIR']/'types/**/*.ts')],'exclude':[str(WEB/'node_modules')]}))
   start('api',[sys.executable,'-m','uvicorn','isolated_server:app','--host','127.0.0.1','--port',str(api_port)],API)
   identity=wait(env['API_ORIGIN']+'/__test/identity');assert identity['database']==db and identity['db_user']==role and identity['nonce']==nonce
   env['DATCO_COMPANY_CONTEXT']=(out/'company-ready.json').read_text(encoding='utf-8')
   proposal=json.loads((out/'proposal-ready.json').read_text(encoding='utf-8'));env['DATCO_PROPOSAL_CONTEXT']=json.dumps(proposal)
   start('worker',[sys.executable,'tests/isolated_worker.py'],API)
   deadline=time.monotonic()+30
   while not (out/'worker-ready.json').exists():
    if children[-1].poll() is not None:raise RuntimeError('CI_WORKER_EXITED')
    if time.monotonic()>deadline:raise RuntimeError('CI_WORKER_TIMEOUT')
    time.sleep(.1)
   worker=json.loads((out/'worker-ready.json').read_text());assert worker['database']==db and worker['db_user']==role
   start('web',['npm','run','dev','--','--port',str(web_port)],WEB);wait(origin)
   run(['npm','run','test:e2e','--','tests/smoke.spec.ts','tests/notice.spec.ts','tests/proposal.spec.ts','tests/company.spec.ts','tests/workspace.spec.ts','tests/company-document-first.spec.ts','tests/role-portals.spec.ts','--workers=1','--reporter=line'],WEB)
 except Exception:
  for log in logs:log.flush()
  for name in ('api','worker','web'):
   path=out/(name+'.log')
   if path.exists():
    tail=path.read_text(errors='replace')[-4000:]
    for secret in (password,url.password,env.get('DATCO_E2E_PASSWORD'),env['DATABASE_URL']):
     if secret:tail=tail.replace(secret,'[REDACTED]')
    print('CI_CHILD_DIAGNOSTIC '+name+'\n'+tail,flush=True)
  raise
 finally:
  for p in reversed(children):
   if p.poll() is None:
    if os.name=='nt':subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    else:os.killpg(p.pid,signal.SIGTERM)
    try:p.wait(timeout=15)
    except subprocess.TimeoutExpired:
     if os.name=='nt':p.kill()
     else:os.killpg(p.pid,signal.SIGKILL)
     p.wait()
  for log in logs:log.close()
  if made_db:
   assert admin.execute('select pg_get_userbyid(datdba) from pg_database where datname=%s',(db,)).fetchone()==(role,)
   admin.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(db)))
  if made_role:admin.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(role)))
  admin.close()
  print('CI_OWNED_DATABASE_AND_ROLE_REMOVED')
if __name__=='__main__':main()
