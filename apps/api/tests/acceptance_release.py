"""Opt-in, fail-closed code releases over one labelled synthetic UAT data owner.

Never provisions/migrates/seeds/restores a DB or edits the owner manifest. The
separate loopback owner must be explicitly enrolled by nonce. Existing services
and protected ports are refused. Public output never includes DB credentials.
"""
import argparse
import ast
from contextlib import contextmanager
from hashlib import sha256
import importlib
import json
import os
from pathlib import Path
import re
import stat as statmod
import subprocess
import sys
import time
from uuid import uuid4

import manual_acceptance as uat

ROOT = Path(__file__).resolve().parents[3]
TOOL = Path(__file__).resolve()
PROTECTED = {8443, 8444, 18445, 49355, 49356}
RECORD_SCHEMA = 'datco-uat-release-v2'
DATA_FORMAT = 'dmp-workbook-metadata-v1'


def fail(code):
    raise RuntimeError(code)


def digest(value):
    return sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def file_hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def no_links(path):
    path=Path(path).absolute()
    for item in [path,*path.parents]:
        if item.exists() or item.is_symlink():
            stat=item.lstat()
            if item.is_symlink() or getattr(stat,'st_file_attributes',0)&0x400:
                fail('RELEASE_LINKED_PATH_REJECTED')
    return path.resolve()


def tree_hash(directory):
    directory=no_links(directory)
    if not directory.is_dir():fail('RELEASE_ARTIFACT_MISSING')
    entries=[]
    for base,dirs,files in os.walk(directory,followlinks=False):
        for name in [*dirs,*files]:
            # Root ancestors are checked once above. Each walked entry needs
            # only its own lstat, avoiding repeated ancestor resolution per file.
            entry=(Path(base)/name).lstat()
            if statmod.S_ISLNK(entry.st_mode) or getattr(entry,'st_file_attributes',0)&0x400:
                fail('RELEASE_LINKED_PATH_REJECTED')
        dirs[:]=sorted(d for d in dirs if d not in ('cache','.cache','__pycache__'))
        for name in sorted(files):
            path=Path(base)/name
            if name in ('trace','.DS_Store') or name.endswith(('.pyc','.log')):continue
            entries.append((path.relative_to(directory).as_posix(),file_hash(path)))
    if not entries:fail('RELEASE_ARTIFACT_EMPTY')
    return digest(entries)


def git(project,*args):
    return subprocess.check_output(['git',*args],cwd=project,text=True,encoding='utf-8').strip()


def clean_source(source,head):
    source=no_links(source)
    if git(source,'rev-parse','--show-toplevel').replace('\\','/').lower()!=source.as_posix().lower():fail('RELEASE_SOURCE_NOT_ROOT')
    if not re.fullmatch('[a-f0-9]{40}',head) or git(source,'rev-parse','HEAD')!=head:fail('RELEASE_SOURCE_HEAD_MISMATCH')
    if git(source,'status','--porcelain','--untracked-files=all'):fail('RELEASE_SOURCE_NOT_CLEAN')
    return source


def python_at(source):
    venv=no_links(Path(source)/'apps/api/.venv')
    python=venv/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    no_links(python)
    if not python.is_file() or not (venv/'pyvenv.cfg').is_file():fail('RELEASE_OWN_PYTHON_REQUIRED')
    return python



def owner_guard_version(source):
    """Read the declared opt-in START contract without importing owner code."""
    path=Path(source)/'apps/api/tests/manual_acceptance.py'
    try:tree=ast.parse(path.read_text(encoding='utf-8'))
    except (OSError,SyntaxError):return 0
    declarations=[]
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name)
                and target.id=='RELEASE_OWNER_GUARD_VERSION' for target in node.targets):
            declarations.append(node.value.value if isinstance(node.value,ast.Constant)
                                and type(node.value.value) is int else None)
    return declarations[0] if len(declarations)==1 and declarations[0]==1 else 0



def workbook_data_contract(source):
    """Probe a source's pure JSON reader with synthetic data; no DB or files data.

    A field accepted but discarded is not backward-compatible reading. A tracked
    writer is conservatively considered capable of persisting this JSON format.
    """
    sample=dict(schema_version='workbook-v1',artifact_kind='SYNTHETIC_RELEASE_PROBE',
        source_workbook='SYNTHETIC.xlsx',source_sheet='SYNTHETIC',source_display_date='',
        feature_count=1,system_count=1,group_count=1,uniqueness_rule='feature_id',
        system_counts={'SYNTHETIC':1},workbook_provenance={
            'file_sha256':'a'*64,'parser_version':'synthetic-probe-v1',
            'rows':[{'row_key':'0:2','cells':{'name':{'cell':'C2'}}}]})
    code="""import json,sys
sys.path.insert(0,sys.argv[1])
from app.infrastructure.dmp_inventory import Metadata
sample=json.loads(sys.argv[2])
try:
    parsed=Metadata.model_validate(sample)
    preserved=parsed.model_dump().get('workbook_provenance')==sample['workbook_provenance']
except Exception:
    preserved=False
print(json.dumps({'reader':preserved}))
"""
    env={key:value for key,value in os.environ.items()
         if not key.startswith(('DATCO_','OPENAI_','ANTHROPIC_','GEMINI_','GOOGLE_API_',
            'BIZINFO_','GROK_','XAI_','AZURE_OPENAI_'))
         and key not in ('DATABASE_URL','PYTHONPATH','HTTP_PROXY','HTTPS_PROXY','ALL_PROXY',
            'http_proxy','https_proxy','all_proxy')}
    env['PYTHONIOENCODING']='utf-8'
    result=subprocess.run([str(python_at(source)),'-I','-B','-c',code,
        str(Path(source)/'apps/api'),json.dumps(sample)],cwd=Path(source)/'apps/api',
        env=env,capture_output=True,text=True,encoding='utf-8',creationflags=uat.HIDDEN)
    if result.returncode:fail('RELEASE_DATA_CONTRACT_PROBE_FAILED')
    try:reader=json.loads(result.stdout)['reader']
    except (ValueError,KeyError,TypeError):fail('RELEASE_DATA_CONTRACT_PROBE_FAILED')
    if type(reader) is not bool:fail('RELEASE_DATA_CONTRACT_PROBE_FAILED')
    writer_path='apps/api/app/capability/workbook_import.py'
    writer=bool(git(source,'ls-files','--',writer_path))
    return dict(format=DATA_FORMAT,probe_version=1,
        reader_preserves_workbook_provenance=reader,
        writer_may_emit_workbook_provenance=writer)


def data_descriptor(record):
    if record.get('schema')!=RECORD_SCHEMA:fail('RELEASE_RECORD_SCHEMA_UNSUPPORTED')
    descriptor=record.get('source_contract',{}).get('workbook_data')
    if (not isinstance(descriptor,dict) or descriptor.get('format')!=DATA_FORMAT
            or descriptor.get('probe_version')!=1
            or type(descriptor.get('reader_preserves_workbook_provenance')) is not bool
            or type(descriptor.get('writer_may_emit_workbook_provenance')) is not bool):
        fail('RELEASE_BACKWARD_DATA_CONTRACT_INCOMPATIBLE')
    return descriptor


def source_contract(source):
    source=Path(source)
    python=python_at(source)
    modules=no_links(source/'apps/web/node_modules')
    if not (modules/'next/dist/bin/next').is_file():fail('RELEASE_OWN_NODE_DEPS_REQUIRED')
    locks=['apps/api/uv.lock','apps/api/pyproject.toml','apps/web/package-lock.json','apps/web/package.json']
    locked={p:file_hash(source/p) for p in locks}
    schemas=sorted((source/'apps/api/app/infrastructure').glob('*schema*.py'))
    migrations=sorted((source/'apps/api/alembic').rglob('*.py'))
    contract={p.relative_to(source).as_posix():file_hash(p) for p in [*schemas,*migrations]}
    if not schemas or not migrations:fail('RELEASE_SCHEMA_CONTRACT_MISSING')
    site=source/('apps/api/.venv/Lib/site-packages' if os.name=='nt' else 'apps/api/.venv/lib')
    return dict(locks=locked,schema_code=digest(contract),release_owner_guard=owner_guard_version(source),
                workbook_data=workbook_data_contract(source),python=str(python),
                python_config=file_hash(source/'apps/api/.venv/pyvenv.cfg'),
                python_deps=tree_hash(site),node_deps=tree_hash(modules))


def owner_context(owner_root,nonce):
    owner=no_links(owner_root)
    if uat.repository_common_dir(owner)!=uat.repository_common_dir(ROOT):fail('RELEASE_REPOSITORY_MISMATCH')
    # Configure only this process's legacy loader, preserving its exact checks.
    uat.ROOT=owner;uat.API=owner/'apps/api';uat.WEB=owner/'apps/web'
    uat.BASE=owner/'storage/private/runtime/manual-acceptance'
    m=uat.load(nonce);out=no_links(uat.owned(nonce))
    if (not m.get('preparation') or m.get('host')!='127.0.0.1'
            or m.get('https_port') in PROTECTED
            or any(m.get(k) in PROTECTED for k in ('api_port','web_port','pg_port'))
            or m.get('origin')!='https://127.0.0.1:'+str(m.get('https_port'))):
        fail('RELEASE_SEPARATE_LOOPBACK_OWNER_REQUIRED')
    for name in ('files','tls'):
        no_links(out/name)
    resource=uat.inspect_label('container',m['container'],nonce)
    uat.inspect_label('volume',m['volume'],nonce)
    ports=(resource.get('NetworkSettings',{}).get('Ports',{}).get('5432/tcp')
           or resource.get('HostConfig',{}).get('PortBindings',{}).get('5432/tcp') or [])
    if not any(p['HostIp']=='127.0.0.1' and int(p['HostPort'])==m['pg_port'] for p in ports):fail('RELEASE_POSTGRES_PORT_MISMATCH')
    return owner,m,out



def ensure_database_running(m):
    # Only a previously provisioned, exactly labelled owner container is started.
    # No DB/role/volume/schema creation or migration is part of a release.
    resource=uat.inspect_label('container',m['container'],m['nonce'])
    if not resource.get('State',{}).get('Running'):
        uat.run(m,['docker','start',m['container']],log='release-database-start.log')
        uat.wait_postgres_tcp(m)


def db_snapshot(m):
    import psycopg
    from sqlalchemy.engine import make_url
    url=make_url(m['url'])
    if (url.host,url.port,url.database,url.username)!=('127.0.0.1',m['pg_port'],m['db'],m['role']):fail('RELEASE_DATABASE_IDENTITY_MISMATCH')
    queries=[
        "SELECT table_name,column_name,ordinal_position,data_type,udt_name,is_nullable,column_default FROM information_schema.columns WHERE table_schema=current_schema() ORDER BY table_name,ordinal_position",
        "SELECT c.relname,k.conname,pg_get_constraintdef(k.oid,true) FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid WHERE c.relnamespace=current_schema()::regnamespace ORDER BY 1,2",
        "SELECT tablename,indexname,indexdef FROM pg_indexes WHERE schemaname=current_schema() ORDER BY 1,2",
        "SELECT p.proname,pg_get_function_identity_arguments(p.oid),pg_get_functiondef(p.oid),p.proconfig FROM pg_proc p WHERE p.pronamespace=current_schema()::regnamespace AND p.prokind IN ('f','p') ORDER BY 1,2",
        "SELECT c.relname,t.tgname,pg_get_triggerdef(t.oid,true) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid WHERE c.relnamespace=current_schema()::regnamespace AND NOT t.tgisinternal ORDER BY 1,2",
        "SELECT tablename,policyname,permissive,roles,cmd,qual,with_check FROM pg_policies WHERE schemaname=current_schema() ORDER BY 1,2"]
    with psycopg.connect(host=url.host,port=url.port,dbname=url.database,user=url.username,password=url.password,connect_timeout=5) as connection:
        connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        if connection.execute('select current_database(),current_user').fetchone()!=(m['db'],m['role']):fail('RELEASE_DATABASE_IDENTITY_MISMATCH')
        if any(connection.execute('select rolsuper,rolcreatedb,rolcreaterole from pg_roles where rolname=current_user').fetchone()):fail('RELEASE_DATABASE_PRIVILEGE_MISMATCH')
        versions=sorted(row[0] for row in connection.execute('select version_num from alembic_version').fetchall())
        values=[connection.execute(query).fetchall() for query in queries]
    return dict(alembic=versions,schema=digest(values))


def owner_identity(owner,m,out):
    return dict(root=str(owner),nonce=m['nonce'],manifest=file_hash(out/'manifest.json'),
        origin=m['origin'],db=m['db'],role=m['role'],container=m['container'],volume=m['volume'],
        files=str(out/'files'),session_cookie='datco_uat_'+m['nonce'],
        accounts=file_hash(out/'accounts.json'),tls_ca=file_hash(out/'tls/pki/authorities/local/root.crt'),
        gateway=file_hash(out/'Caddyfile'))


def immutable(path,value):
    no_links(path.parent)
    path.parent.mkdir(parents=True,exist_ok=True)
    no_links(path)
    with path.open('x',encoding='utf-8') as output:json.dump(value,output,ensure_ascii=False,sort_keys=True,indent=2)


def load_record(out,identifier):
    if not re.fullmatch('r[a-f0-9]{24}',identifier):fail('RELEASE_ID_INVALID')
    path=no_links(out/'releases'/(identifier+'.json'))
    record=json.loads(path.read_text(encoding='utf-8'))
    data_descriptor(record)
    body={k:v for k,v in record.items() if k!='id'}
    if record.get('id')!=identifier or identifier!='r'+digest(body)[:24]:fail('RELEASE_RECORD_TAMPERED')
    return record


def validate_record(owner,m,out,record,check_db=True):
    data_descriptor(record)
    if record['owner']!=owner_identity(owner,m,out):fail('RELEASE_OWNER_CHANGED')
    source=clean_source(record['source_root'],record['head'])
    if uat.repository_common_dir(source)!=uat.repository_common_dir(owner):fail('RELEASE_REPOSITORY_MISMATCH')
    if source_contract(source)!=record['source_contract']:fail('RELEASE_DEPS_OR_SCHEMA_CODE_CHANGED')
    if tree_hash(source/'apps/web'/record['dist_dir'])!=record['build_hash']:fail('RELEASE_BUILD_CHANGED')
    if not (source/'apps/web'/record['dist_dir']/'BUILD_ID').is_file():fail('RELEASE_BUILD_INCOMPLETE')
    if file_hash(record['launcher'])!=record['launcher_hash']:fail('RELEASE_LAUNCHER_CHANGED')
    if check_db and db_snapshot(m)!=record['database']:fail('RELEASE_DATABASE_SCHEMA_CHANGED')
    return source


def compatible(previous,target):
    old_data,new_data=data_descriptor(previous),data_descriptor(target)
    if ((old_data['writer_may_emit_workbook_provenance'] or new_data['writer_may_emit_workbook_provenance'])
            and not (old_data['reader_preserves_workbook_provenance'] and new_data['reader_preserves_workbook_provenance'])):
        fail('RELEASE_BACKWARD_DATA_CONTRACT_INCOMPATIBLE')
    if previous['owner']!=target['owner']:fail('RELEASE_DATA_OWNER_MISMATCH')
    for key in ('locks','schema_code'):
        if previous['source_contract'][key]!=target['source_contract'][key]:fail('RELEASE_CONTRACT_INCOMPATIBLE')
    if previous['database']!=target['database']:fail('RELEASE_DATABASE_INCOMPATIBLE')


def release_environment(m,out,source,record):
    uat.ROOT=Path(source);uat.API=Path(source)/'apps/api';uat.WEB=Path(source)/'apps/web'
    uat.BASE=out.parent
    env=uat.environment({**m,'head':record['head']})
    env['DATCO_TEST_DIST_DIR']=record['dist_dir']
    env['DATCO_ACCEPTANCE_HEAD']=record['head']
    env['DATCO_ACCEPTANCE_PREPARATION']='1'
    return env


def build(source,m,out,dist):
    config=source/'apps/web'/dist.replace('datco-e2e-','datco-config-')/'tsconfig.json'
    config.parent.mkdir(parents=True,exist_ok=True)
    web=source/'apps/web'
    config.write_text(json.dumps(dict(extends='../../tsconfig.json',compilerOptions=dict(paths={'@/*':[str(web/'src/*')]}),include=[str(web/'next-env.d.ts'),str(web/'src/**/*.ts'),str(web/'src/**/*.tsx'),str(web/'tests/**/*.ts'),str(web/dist/'types/**/*.ts')],exclude=[str(web/'node_modules')])),encoding='utf-8')
    env=release_environment(m,out,source,dict(head=git(source,'rev-parse','HEAD'),dist_dir=dist))
    original=(web/'next-env.d.ts').read_bytes()
    command=['cmd.exe','/c','npm.cmd','run','build'] if os.name=='nt' else ['npm','run','build']
    try:
        with (out/'release-build.log').open('a',encoding='utf-8') as log:
            subprocess.run(command,cwd=web,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=uat.HIDDEN,check=True)
    finally:(web/'next-env.d.ts').write_bytes(original)


def prepare(owner,m,out,source,head,dist=None,do_build=False):
    source=clean_source(source,head)
    if uat.repository_common_dir(source)!=uat.repository_common_dir(owner):fail('RELEASE_REPOSITORY_MISMATCH')
    dist=dist or '.next/datco-e2e-'+uuid4().hex[:12]
    if not re.fullmatch(r'\.next/datco-e2e-[a-f0-9]{12}',dist):fail('RELEASE_DIST_PATH_INVALID')
    if not do_build and not (source==owner and head==m['head']
                              and dist=='.next/datco-e2e-'+m['nonce']):
        fail('RELEASE_TARGET_BUILD_REQUIRED')
    contract=source_contract(source)
    database=db_snapshot(m)
    env=release_environment(m,out,source,dict(head=head,dist_dir=dist))
    expected=json.loads(subprocess.check_output([str(python_at(source)),'-B','-c',"import json;from alembic.config import Config;from alembic.script import ScriptDirectory;print(json.dumps(sorted(ScriptDirectory.from_config(Config('alembic.ini')).get_heads())))"],cwd=source/'apps/api',env=env,text=True,encoding='utf-8'))
    if expected!=database['alembic']:fail('RELEASE_MIGRATION_REQUIRED_NOT_ALLOWED')
    if do_build:
        if (source/'apps/web'/dist).exists():fail('RELEASE_IMMUTABLE_BUILD_ALREADY_EXISTS')
        build(source,m,out,dist)
    if not (source/'apps/web'/dist/'BUILD_ID').is_file():fail('RELEASE_BUILD_INCOMPLETE')
    clean_source(source,head)
    body=dict(schema=RECORD_SCHEMA,source_root=str(source),head=head,dist_dir=dist,
        source_contract=contract,build_hash=tree_hash(source/'apps/web'/dist),database=database,
        owner=owner_identity(owner,m,out),launcher=str(TOOL),launcher_hash=file_hash(TOOL))
    record=dict(body,id='r'+digest(body)[:24]);path=out/'releases'/(record['id']+'.json')
    if path.exists():
        if load_record(out,record['id'])!=record:fail('RELEASE_RECORD_CONFLICT')
    else:immutable(path,record)
    return record


def enrollment(out):
    value=json.loads((out/'release-owner.json').read_text(encoding='utf-8'))
    return value


def selection(out):
    return json.loads((out/'release-selection.json').read_text(encoding='utf-8'))


def state(out):
    return json.loads((out/'state.json').read_text(encoding='utf-8'))


def enroll(owner,m,out,record,confirmation):
    if confirmation!=m['nonce'] or state(out)['phase']!='STOPPED':fail('RELEASE_ENROLL_STOP_AND_NONCE_REQUIRED')
    if (owner_guard_version(owner)!=1
            or record['source_contract'].get('release_owner_guard')!=1):
        fail('RELEASE_OWNER_START_GUARD_UNSUPPORTED')
    validate_record(owner,m,out,record)
    if record['source_root']!=str(owner) or record['head']!=m['head']:fail('RELEASE_INITIAL_OWNER_ARTIFACT_REQUIRED')
    marker=dict(schema='datco-uat-release-owner-v1',owner=record['owner'],initial_release=record['id'])
    immutable(out/'release-owner.json',marker)
    uat.write(out/'release-selection.json',dict(current=record['id'],previous=None))


@contextmanager
def action_lock(out):
    path=out/'release-action.lock'
    try:
        with path.open('x',encoding='utf-8') as lock:lock.write(str(os.getpid()))
    except FileExistsError:fail('RELEASE_ACTION_IN_PROGRESS')
    try:yield
    finally:path.unlink(missing_ok=True)


def alive(pid):
    if os.name=='nt':
        import ctypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong]
        kernel.OpenProcess.restype=ctypes.c_void_p
        kernel.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
        kernel.CloseHandle.argtypes=[ctypes.c_void_p]
        handle=kernel.OpenProcess(0x1000,False,int(pid))
        if not handle:
            if ctypes.get_last_error()==5:fail('RELEASE_PROCESS_CHECK_DENIED')
            return False
        try:
            code=ctypes.c_ulong()
            if not kernel.GetExitCodeProcess(handle,ctypes.byref(code)):fail('RELEASE_PROCESS_CHECK_FAILED')
            return code.value==259
        finally:kernel.CloseHandle(handle)
    try:os.kill(int(pid),0);return True
    except ProcessLookupError:return False


def wait_stopped(out,old,timeout=60):
    if old['phase']=='STOPPED':return
    if old['phase']!='RUNNING':fail('RELEASE_OWNER_NOT_RUNNING_OR_STOPPED')
    (out/'stop.request').write_text(out.name,encoding='utf-8')
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        current=state(out)
        if current['phase']=='STOPPED' and not any(alive(pid) for pid in old.get('children',[])):
            return
        time.sleep(.2)
    fail('RELEASE_STOP_TIMEOUT_NO_PID_KILL')


def launch(owner,m,out,record,timeout=160):
    source=Path(record['source_root'])
    uat.write(out/'state.json',dict(nonce=m['nonce'],phase='STARTING',head=record['head'],release=record['id']))
    uat.write(out/'release-runtime.json',dict(release=record['id'],phase='STARTING',cleanup_complete=False))
    command=[record['source_contract']['python'],'-B',record['launcher'],'serve','--owner-root',str(owner),'--nonce',m['nonce'],'--release',record['id'],'--confirm',m['nonce']]
    with (out/'release-supervisor.log').open('a',encoding='utf-8') as log:
        process=subprocess.Popen(command,cwd=source,env=release_environment(m,out,source,record),stdout=log,stderr=subprocess.STDOUT,creationflags=uat.HIDDEN,start_new_session=os.name!='nt')
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        current=state(out);runtime=json.loads((out/'release-runtime.json').read_text(encoding='utf-8'))
        if current.get('phase')=='RUNNING' and current.get('release')==record['id']:return
        if process.poll() is not None:
            if not runtime.get('cleanup_complete'):fail('RELEASE_CHILD_CLEANUP_UNCONFIRMED')
            fail('RELEASE_TARGET_START_FAILED_CLEANED')
        time.sleep(.25)
    (out/'stop.request').write_text(m['nonce'],encoding='utf-8')
    try:process.wait(timeout=45)
    except subprocess.TimeoutExpired:fail('RELEASE_START_TIMEOUT_CLEANUP_UNCONFIRMED')
    runtime=json.loads((out/'release-runtime.json').read_text(encoding='utf-8'))
    if not runtime.get('cleanup_complete'):fail('RELEASE_CHILD_CLEANUP_UNCONFIRMED')
    fail('RELEASE_TARGET_START_FAILED_CLEANED')


def switch(owner,m,out,identifier,confirmation):
    if confirmation!=m['nonce']:fail('RELEASE_EXPLICIT_NONCE_REQUIRED')
    with action_lock(out):
        registered=enrollment(out)
        if registered['owner']!=owner_identity(owner,m,out):fail('RELEASE_OWNER_CHANGED')
        selected=selection(out);previous=load_record(out,selected['current']);target=load_record(out,identifier)
        # Full preflight happens before stop. Supervisor/API children revalidate
        # the same immutable inputs at startup; no validation is skipped.
        compatible(previous,target);validate_record(owner,m,out,previous);validate_record(owner,m,out,target)
        before=state(out)
        if before.get('nonce')!=m['nonce']:fail('RELEASE_STATE_NONCE_MISMATCH')
        if before['phase']=='RUNNING' and before.get('head')!=previous['head']:fail('RELEASE_RUNNING_IDENTITY_MISMATCH')
        wait_stopped(out,before)
        try:launch(owner,m,out,target)
        except RuntimeError as exc:
            if str(exc)!='RELEASE_TARGET_START_FAILED_CLEANED':raise
            # Previous immutable artifact uses the SAME current DB and files.
            validate_record(owner,m,out,previous)
            launch(owner,m,out,previous)
            immutable(out/'release-events'/(uuid4().hex+'.json'),dict(action='FAILED_TARGET_RESTORED',target=target['id'],current=previous['id']))
            fail('RELEASE_SWITCH_FAILED_PREVIOUS_RESTORED')
        uat.write(out/'release-selection.json',dict(current=target['id'],previous=previous['id'] if target['id']!=previous['id'] else selected.get('previous')))
        immutable(out/'release-events'/(uuid4().hex+'.json'),dict(action='SWITCHED',previous=previous['id'],current=target['id']))


def configure_source(source,out):
    source=Path(source)
    sys.path[:0]=[str(source/'apps/api'),str(source/'apps/api/tests')]
    uat.ROOT=source;uat.API=source/'apps/api';uat.WEB=source/'apps/web';uat.BASE=out.parent


def serve(owner,m,out,record):
    if state(out).get('release')!=record['id'] or state(out)['phase']!='STARTING':fail('RELEASE_START_HANDSHAKE_REQUIRED')
    children=[];logs=[];error=None;stopped=False
    def spawn(label,command,cwd):
        log=(out/('release-'+label+'.log')).open('a',encoding='utf-8');logs.append(log)
        process=subprocess.Popen(command,cwd=cwd,env=release_environment(m,out,source,record),stdout=log,stderr=subprocess.STDOUT,creationflags=uat.HIDDEN)
        children.append(process)
        return process
    try:
        source=validate_record(owner,m,out,record)
        configure_source(source,out)
        for port in (m['api_port'],m['web_port'],m['https_port']):uat.available('127.0.0.1',port)
        ready=out/'worker-ready.json';ready.unlink(missing_ok=True)
        spawn('api',[sys.executable,'-B',record['launcher'],'api-child','--owner-root',str(owner),'--nonce',m['nonce'],'--release',record['id'],'--confirm',m['nonce']],source/'apps/api')
        identity=uat.wait_url('http://127.0.0.1:'+str(m['api_port'])+'/__test/identity',children)
        expected=(m['db'],m['role'],m['nonce'],record['head'],str(out/'files'))
        if (identity['database'],identity['db_user'],identity['nonce'],identity['head'],str(Path(identity['files']).resolve()))!=expected:fail('RELEASE_API_IDENTITY_MISMATCH')
        spawn('worker',[sys.executable,'-B','tests/isolated_worker.py'],source/'apps/api')
        until=time.monotonic()+45
        while not ready.exists():
            if children[-1].poll() is not None or time.monotonic()>until:fail('RELEASE_WORKER_NOT_READY')
            time.sleep(.2)
        worker=json.loads(ready.read_text(encoding='utf-8'))
        if (worker['database'],worker['db_user'],worker['nonce'],worker['head'],str(Path(worker['files']).resolve()))!=expected:fail('RELEASE_WORKER_IDENTITY_MISMATCH')
        spawn('web',['node','node_modules/next/dist/bin/next','start','--hostname','127.0.0.1','--port',str(m['web_port'])],source/'apps/web')
        uat.wait_url('http://127.0.0.1:'+str(m['web_port']),children)
        # Derive a release-specific gateway file without touching owner Caddyfile
        # or TLS: only its public running-code identity header changes.
        gateway=out/'releases'/(record['id']+'.Caddyfile')
        text=(out/'Caddyfile').read_text(encoding='utf-8')
        old='X-DATCO-Acceptance-Head "'+m['head']+'"'
        if text.count(old)!=1:fail('RELEASE_GATEWAY_IDENTITY_NOT_FOUND')
        text=text.replace(old,'X-DATCO-Acceptance-Head "'+record['head']+'"')
        if gateway.exists():
            if gateway.read_text(encoding='utf-8')!=text:fail('RELEASE_GATEWAY_CHANGED')
        else:
            with gateway.open('x',encoding='utf-8') as output:output.write(text)
        spawn('gateway',[m['caddy'],'run','--config',str(gateway),'--adapter','caddyfile'],source)
        time.sleep(3)
        if any(p.poll() is not None for p in children):fail('RELEASE_CHILD_EXITED')
        import ssl
        import urllib.request
        tls=ssl.create_default_context(cafile=str(out/'tls/pki/authorities/local/root.crt'))
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=tls))
        with opener.open(m['origin']+'/login',timeout=10) as response:
            if (response.status!=200 or response.headers.get('X-DATCO-Acceptance')!=m['nonce']
                    or response.headers.get('X-DATCO-Acceptance-Head')!=record['head']):
                fail('RELEASE_GATEWAY_IDENTITY_MISMATCH')
        uat.write(out/'state.json',dict(nonce=m['nonce'],phase='RUNNING',head=record['head'],release=record['id'],supervisor=os.getpid(),children=[p.pid for p in children],origin=m['origin']))
        uat.write(out/'release-runtime.json',dict(release=record['id'],phase='RUNNING',cleanup_complete=False,children=[p.pid for p in children]))
        while not (out/'stop.request').exists():
            if any(p.poll() is not None for p in children):fail('RELEASE_CHILD_EXITED')
            time.sleep(.25)
        stopped=True
    except BaseException as exc:error=exc
    finally:
        clean=True
        for process in reversed(children):
            if process.poll() is None:
                if os.name=='nt':subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,creationflags=uat.HIDDEN)
                else:process.terminate()
                try:process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    try:process.wait(timeout=15)
                    except subprocess.TimeoutExpired:clean=False
            clean=clean and process.poll() is not None
        for log in logs:log.close()
        for port in (m['api_port'],m['web_port'],m['https_port']):
            try:uat.available('127.0.0.1',port)
            except OSError:clean=False
        (out/'stop.request').unlink(missing_ok=True)
        phase='STOPPED' if stopped and clean else 'FAILED'
        uat.write(out/'release-runtime.json',dict(release=record['id'],phase=phase,cleanup_complete=clean,children=[p.pid for p in children]))
        uat.write(out/'state.json',dict(nonce=m['nonce'],phase=phase,head=record['head'],release=record['id'],reason=type(error).__name__ if error else None))
    if error:raise error


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','enroll','switch','rollback','start','status','serve','api-child'))
    parser.add_argument('--owner-root',required=True,type=Path);parser.add_argument('--nonce',required=True)
    parser.add_argument('--source-root',type=Path);parser.add_argument('--head');parser.add_argument('--dist-dir')
    parser.add_argument('--build',action='store_true');parser.add_argument('--release');parser.add_argument('--confirm')
    args=parser.parse_args();owner,m,out=owner_context(args.owner_root,args.nonce)
    if args.action in ('enroll','switch','rollback','start','serve','api-child') and args.confirm!=m['nonce']:
        fail('RELEASE_EXPLICIT_NONCE_REQUIRED')
    if args.action!='status':ensure_database_running(m)
    if args.action=='prepare':
        if not args.source_root or not args.head:fail('RELEASE_SOURCE_AND_HEAD_REQUIRED')
        record=prepare(owner,m,out,args.source_root,args.head,args.dist_dir,args.build)
        print(json.dumps(dict(release=record['id'],head=record['head'],build_hash=record['build_hash'])))
    elif args.action=='status':
        selected=selection(out) if (out/'release-selection.json').exists() else None
        print(json.dumps(dict(nonce=m['nonce'],origin=m['origin'],phase=state(out)['phase'],selection=selected)))
    elif args.action=='enroll':enroll(owner,m,out,load_record(out,args.release),args.confirm);print('RELEASE_OWNER_ENROLLED')
    elif args.action in ('switch','rollback','start'):
        chosen=selection(out)
        identifier=args.release if args.action=='switch' else chosen['previous'] if args.action=='rollback' else chosen['current']
        if not identifier:fail('RELEASE_TARGET_REQUIRED')
        switch(owner,m,out,identifier,args.confirm);print('RELEASE_RUNNING_DATA_PRESERVED')
    else:
        if args.confirm!=m['nonce']:fail('RELEASE_EXPLICIT_NONCE_REQUIRED')
        record=load_record(out,args.release)
        if args.action=='serve':serve(owner,m,out,record)
        else:
            if state(out).get('release')!=record['id'] or state(out)['phase']!='STARTING':fail('RELEASE_START_HANDSHAKE_REQUIRED')
            source=validate_record(owner,m,out,record,check_db=False)
            configure_source(source,out)
            import uvicorn
            uvicorn.run('manual_acceptance_server:app',host='127.0.0.1',port=m['api_port'],access_log=False)


if __name__=='__main__':
    try:main()
    except Exception as exc:
        # Exceptions may contain a DSN/source data; expose only bounded codes.
        code=str(exc) if isinstance(exc,RuntimeError) and re.fullmatch('[A-Z0-9_]+',str(exc)) else type(exc).__name__
        print('ACCEPTANCE_RELEASE_FAILED: '+code,file=sys.stderr)
        sys.exit(1)
