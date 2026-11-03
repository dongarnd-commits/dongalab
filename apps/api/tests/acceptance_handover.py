"""Narrow Windows legacy owner adapter for product 04. No provisioning or data restore.

prepare is read-only on the legacy owner; activation requires a separate exact
approval receipt. Existing v3 PROTECTED/enrollment guards are never modified.
"""
import argparse
from contextlib import ExitStack
from datetime import datetime,timezone
from hashlib import sha256
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import socket
import ssl
import subprocess
import sys
import time
from uuid import uuid4

import acceptance_release as release
import manual_acceptance as uat
from acceptance_handover_projection import project_manifest
from acceptance_handover_fence import FileFence,process_identity,listener_owners,descendant_identities,trusted_console_host

ROOT=Path(__file__).resolve().parents[3]
TOOL=Path(__file__).resolve()
PRODUCT='04dfea4ee9d2521ba632c430c2218463df5df63c'
RECOVERY='9b8d0e0f9eb79aaaa2b973f7e3455df78b8a046e'
LEGACY='725987f4a375d4f77028e35361e4fcdb05aac4ee'
ACTUAL_NONCE='9ca49b473812'
ACTUAL_ROOT=ROOT.parent/'dongalab-dmp-assets'
DOCS=('docs/mvp/DMP_ASSET_AUTO_COMPOSITION.md','docs/mvp/USER_ACCEPTANCE_GUIDE.md')
FORMAT='datco-legacy-handover-v1'
SCHEMA_HEAD='gh02a0012026'


def require(ok,code):
    if not ok:raise RuntimeError(code)


def read_json(path):
    return json.loads(release.fs_path(release.no_links(path)).read_text(encoding='utf-8-sig'))


def save(path,value):
    release.fs_path(path.parent).mkdir(parents=True,exist_ok=True)
    uat.write(path,value)


def private_directory(path):
    path=release.no_links(path);require(not path.exists(),'HANDOVER_NEW_PRIVATE_DIRECTORY_REQUIRED')
    path.mkdir(parents=True)
    if os.name=='nt':
        import csv
        sid=list(csv.reader(subprocess.check_output(['whoami','/user','/fo','csv','/nh'],text=True).strip().splitlines()))[0][1]
        subprocess.run(['icacls',str(path),'/inheritance:r','/grant:r','*'+sid+':(OI)(CI)F','*S-1-5-18:(OI)(CI)F'],check=True,capture_output=True,creationflags=uat.HIDDEN)
    else:path.chmod(0o700)
    return path


def docker_projection(m):
    fmt='{"id":{{json .Id}},"image":{{json .Image}},"running":{{json .State.Running}},"labels":{{json .Config.Labels}},"mounts":{{json .Mounts}},"ports":{{json .HostConfig.PortBindings}}}'
    result=subprocess.run(['docker','inspect','--format',fmt,m['container']],capture_output=True,text=True,encoding='utf-8',creationflags=uat.HIDDEN)
    require(result.returncode==0,'HANDOVER_CONTAINER_METADATA_UNAVAILABLE');d=json.loads(result.stdout)
    require(d['labels'].get(uat.LABEL)==m['nonce'] and d['running'] is True,'HANDOVER_RUNNING_DATABASE_OWNERSHIP_REQUIRED')
    mounts=[x for x in d['mounts'] if x.get('Destination')=='/var/lib/postgresql/data']
    require(len(mounts)==1 and mounts[0].get('Type')=='volume' and mounts[0].get('Name')==m['volume'],'HANDOVER_VOLUME_MISMATCH')
    ports=d['ports'].get('5432/tcp') or []
    require(ports==[dict(HostIp='127.0.0.1',HostPort=str(m['pg_port']))],'HANDOVER_DATABASE_BINDING_MISMATCH')
    vfmt='{"name":{{json .Name}},"labels":{{json .Labels}},"driver":{{json .Driver}},"created":{{json .CreatedAt}}}'
    v=json.loads(subprocess.check_output(['docker','volume','inspect','--format',vfmt,m['volume']],text=True,encoding='utf-8',creationflags=uat.HIDDEN))
    require(v['labels'].get(uat.LABEL)==m['nonce'],'HANDOVER_VOLUME_OWNERSHIP_REQUIRED')
    return dict(container_id=d['id'],image=d['image'],volume=v,ports=ports)


SCHEMA_SIGNATURE="""SELECT 'C|'||table_name||'|'||column_name||'|'||ordinal_position||'|'||data_type||'|'||udt_name||'|'||is_nullable||'|'||coalesce(column_default,'') AS definition FROM information_schema.columns WHERE table_schema=current_schema()
UNION ALL SELECT 'K|'||c.relname||'|'||k.conname||'|'||pg_get_constraintdef(k.oid,true) FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid WHERE c.relnamespace=current_schema()::regnamespace
UNION ALL SELECT 'I|'||tablename||'|'||indexname||'|'||indexdef FROM pg_indexes WHERE schemaname=current_schema()
UNION ALL SELECT 'F|'||p.proname||'|'||pg_get_function_identity_arguments(p.oid)||'|'||pg_get_functiondef(p.oid) FROM pg_proc p WHERE p.pronamespace=current_schema()::regnamespace AND p.prokind IN ('f','p')
UNION ALL SELECT 'T|'||c.relname||'|'||t.tgname||'|'||pg_get_triggerdef(t.oid,true) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid WHERE c.relnamespace=current_schema()::regnamespace AND NOT t.tgisinternal"""


def technical_database(m):
    # No URL/password, company rows, actor names or password hashes are returned.
    sql="""BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT json_build_object('database',current_database(),'user',current_user,
'privileged',(SELECT rolsuper OR rolcreatedb OR rolcreaterole FROM pg_roles WHERE rolname=current_user),
'alembic',(SELECT array_agg(version_num ORDER BY version_num) FROM alembic_version),
'schema',(SELECT md5(coalesce(string_agg(definition,E'\\n' ORDER BY definition),'')) FROM ("""+SCHEMA_SIGNATURE+""") signature),
'queued',(SELECT count(*) FROM background_jobs WHERE state='QUEUED'),
'processing',(SELECT count(*) FROM background_jobs WHERE state='PROCESSING'),
'attempts',(SELECT count(*) FROM job_attempts WHERE state='PROCESSING'),
'workbook_imports',(SELECT count(*) FROM feature_imports WHERE metadata ? 'workbook_provenance'),
'actor_scope',(SELECT md5(coalesce(string_agg(id||'|'||username||'|'||role,E'\\n' ORDER BY id),'')) FROM local_actors),
'memberships',(SELECT md5(coalesce(string_agg(id||'|'||company_id||'|'||actor_id||'|'||granted_by,E'\\n' ORDER BY id),'')) FROM company_memberships));
ROLLBACK;"""
    command=['docker','exec','-i',m['container'],'psql','-X','-w','-q','-A','-t','-U',m['role'],'-d',m['db'],'-v','ON_ERROR_STOP=1']
    r=subprocess.run(command,input=sql,capture_output=True,text=True,encoding='utf-8',creationflags=uat.HIDDEN,timeout=30)
    require(r.returncode==0,'HANDOVER_READONLY_DATABASE_METADATA_UNAVAILABLE')
    value=json.loads(r.stdout.strip())
    require((value['database'],value['user'],value['privileged'])==(m['db'],m['role'],False),'HANDOVER_DATABASE_ROLE_MISMATCH')
    require(value['alembic']==[SCHEMA_HEAD],'HANDOVER_DATABASE_SCHEMA_HEAD_MISMATCH')
    return value


def require_quiet(db):
    require(all(db[k]==0 for k in ('queued','processing','attempts')),'HANDOVER_UNFINISHED_JOBS_REJECTED')


def owner_paths(root,nonce,kind):
    root=release.no_links(root)
    require(re.fullmatch('[a-f0-9]{12}',nonce or '') is not None,'HANDOVER_NONCE_INVALID')
    require(release.git(root,'rev-parse','HEAD')==LEGACY,'HANDOVER_EXACT_LEGACY_HEAD_REQUIRED')
    out=release.no_links(root/'storage/private/runtime/manual-acceptance'/nonce)
    m,manifest_hash=project_manifest(release.fs_path(release.no_links(out/'manifest.json')))
    require(m['nonce']==nonce and Path(m['root']).resolve()==root and m['head']==LEGACY and m.get('preparation') is True,'HANDOVER_LEGACY_MANIFEST_IDENTITY_MISMATCH')
    require(m['host']=='127.0.0.1' and m['origin']=='https://127.0.0.1:'+str(m['https_port']),'HANDOVER_LOOPBACK_REQUIRED')
    require(all(m[k]==prefix+nonce for k,prefix in (('db','datco_test_'),('role','datco_test_role_'),('container','datco-mvp-uat-'),('volume','datco-mvp-uat-pg-'))),'HANDOVER_RESOURCE_NAMES_MISMATCH')
    require(len({m[k] for k in ('https_port','api_port','web_port','pg_port')})==4,'HANDOVER_PORT_COLLISION')
    if kind=='EXISTING_OWNER':
        require(root==ACTUAL_ROOT.resolve() and nonce==ACTUAL_NONCE and m['https_port']==18445,'HANDOVER_EXACT_EXISTING_OWNER_REQUIRED')
        require(not {m[k] for k in ('api_port','web_port','pg_port')}&release.PROTECTED,'HANDOVER_PROTECTED_INTERNAL_PORT_REJECTED')
    elif kind=='SYNTHETIC_CLONE':
        require(root.parent==ROOT.parent and root.name.startswith('dongalab-handover-clone-'),'HANDOVER_DECLARED_CLONE_REQUIRED')
        require(not {m[k] for k in ('https_port','api_port','web_port','pg_port')}&release.PROTECTED,'HANDOVER_CLONE_PROTECTED_PORT_REJECTED')
        proof=read_json(out/'clone-origin.json')
        require(proof.get('source_nonce')=='2002c1fabb87' and proof.get('scope')=='NON_SENSITIVE_VOLUME_COPY_ONLY' and proof.get('actual_owner_read') is False,'HANDOVER_NON_SENSITIVE_CLONE_PROOF_REQUIRED')
    else:require(False,'HANDOVER_OWNER_KIND_REJECTED')
    return root,out,m,manifest_hash


def legacy_dirty_contract(root):
    dirty=release.git(root,'diff','--name-only').splitlines()
    require(sorted(dirty)==sorted(DOCS) and not release.git(root,'diff','--cached','--name-only'),'HANDOVER_PROTECTED_DOCUMENT_SET_MISMATCH')
    require(not release.git(root,'ls-files','--others','--exclude-standard'),'HANDOVER_UNEXPECTED_SOURCE_FILES')
    return {path:release.file_hash(root/path) for path in DOCS}


def generated_gateway(root,m,head):
    uat.ROOT=root;uat.API=root/'apps/api';uat.WEB=root/'apps/web';uat.BASE=root/'storage/private/runtime/manual-acceptance'
    return uat.caddy_config({**m,'head':head})


def capture_owner(root,nonce,kind):
    root,out,m,mhash=owner_paths(root,nonce,kind)
    docs=legacy_dirty_contract(root);files=release.no_links(out/'files');details=files.stat()
    require(files.is_dir(),'HANDOVER_FILE_DIRECTORY_MISSING')
    state=read_json(out/'state.json')
    require(state.get('nonce')==nonce and state.get('phase')=='RUNNING' and state.get('head')==LEGACY and len(state.get('children',[]))==4,'HANDOVER_RUNNING_LEGACY_REQUIRED')
    dock=docker_projection(m);db=technical_database(m);require_quiet(db)
    caddy=generated_gateway(root,m,LEGACY)
    require(release.file_hash(out/'Caddyfile') in {sha256(caddy.encode()).hexdigest(),sha256(caddy.replace('\n','\r\n').encode()).hexdigest()},'HANDOVER_LEGACY_GATEWAY_TEMPLATE_MISMATCH')
    require(release.owner_guard_version(root)==0,'HANDOVER_LEGACY_GUARD_ZERO_REQUIRED')
    state_pids=[state['supervisor'],*state['children']]
    processes={str(p):process_identity(p) for p in state_pids}
    for identity in processes.values():
        identity['exe_sha256']=release.file_hash(Path(identity['exe']).resolve())
    allowed_cwds={str(root),str(root/'apps/api'),str(root/'apps/web')}
    require(all(str(Path(v['cwd']).resolve()) in allowed_cwds for v in processes.values()),'HANDOVER_LEGACY_CWD_MISMATCH')
    require(all(processes[str(p)]['parent']==state['supervisor'] for p in state['children']),'HANDOVER_LEGACY_PARENT_MISMATCH')
    listeners=listener_owners([m[k] for k in ('api_port','web_port','https_port')])
    for rows in listeners.values():
        require(bool(rows),'HANDOVER_LEGACY_LISTENER_MISSING')
        for row in rows:
            require(row['address']=='127.0.0.1','HANDOVER_NON_LOOPBACK_LISTENER_REJECTED');pid=row['pid'];seen=set()
            while pid!=state['supervisor']:
                require(pid not in seen and len(seen)<12,'HANDOVER_FOREIGN_LISTENER_REJECTED');seen.add(pid)
                key=str(pid)
                if key not in processes:
                    processes[key]=process_identity(pid);processes[key]['exe_sha256']=release.file_hash(Path(processes[key]['exe']).resolve())
                pid=processes[key]['parent']
    complete=descendant_identities(state['supervisor'])
    require(set(processes)<=set(complete),'HANDOVER_PROCESS_TREE_CHANGED')
    initial_images={Path(processes[str(pid)]['exe']) for pid in state_pids}
    for key,identity in complete.items():
        console=trusted_console_host(identity)
        require(Path(identity['exe']) in initial_images or console,'HANDOVER_UNKNOWN_DESCENDANT_EXECUTABLE')
        require(str(Path(identity['cwd']).resolve()) in allowed_cwds or console,'HANDOVER_UNKNOWN_DESCENDANT_CWD')
        identity['exe_sha256']=release.file_hash(Path(identity['exe']).resolve())
    processes=complete
    tls=ssl.create_default_context(cafile=str(out/'tls/pki/authorities/local/root.crt'))
    with socket.create_connection(('127.0.0.1',m['https_port']),timeout=5) as raw:
        with tls.wrap_socket(raw,server_hostname='127.0.0.1') as peer:certificate=sha256(peer.getpeercert(binary_form=True)).hexdigest()
    connection=http.client.HTTPSConnection('127.0.0.1',m['https_port'],context=tls,timeout=5)
    try:
        connection.request('GET','/login');response=connection.getresponse()
        require(response.status==200 and response.getheader('X-DATCO-Acceptance')==nonce and response.getheader('X-DATCO-Acceptance-Head')==LEGACY,'HANDOVER_PUBLIC_LEGACY_IDENTITY_MISMATCH')
    finally:connection.close()
    return dict(kind=kind,root=str(root),data_root=str(out),manifest=m,manifest_sha256=mhash,documents=docs,
        entrypoint_sha256=release.file_hash(root/'apps/api/tests/manual_acceptance.py'),legacy_state=state,
        legacy_state_sha256=release.file_hash(out/'state.json'),processes=processes,listeners={str(k):v for k,v in listeners.items()},
        resources=dock,database=dict(alembic=db['alembic'],schema=db['schema']),initial_checkpoint=db,
        files_directory=dict(path=str(files),device=details.st_dev,inode=details.st_ino),
        accounts_file_sha256=release.file_hash(out/'accounts.json'),ca_sha256=release.file_hash(out/'tls/pki/authorities/local/root.crt'),
        certificate_sha256=certificate,caddy_sha256=release.file_hash(out/'Caddyfile'),cookie='datco_uat_'+nonce)


def validate_approval(plan,approval,action,now=None):
    require(approval.get('decision')=='APPROVED','HANDOVER_SEPARATE_APPLY_DECISION_REQUIRED')
    require(approval.get('plan_sha256')==plan['id'] and approval.get('nonce')==plan['owner']['manifest']['nonce']
        and approval.get('origin')==plan['owner']['manifest']['origin'] and approval.get('product_head')==PRODUCT
        and approval.get('recovery_head')==RECOVERY,'HANDOVER_APPROVAL_BINDING_MISMATCH')
    require(action in approval.get('actions',[]) and bool(approval.get('decided_by')) and bool(approval.get('decision_reference')),'HANDOVER_APPROVAL_SCOPE_MISSING')
    try:
        start=datetime.fromisoformat(approval['not_before']);end=datetime.fromisoformat(approval['expires']);current=now or datetime.now(timezone.utc)
        require(start.tzinfo is not None and end.tzinfo is not None and start<=current<end,'HANDOVER_APPROVAL_WINDOW_INVALID')
    except (ValueError,KeyError,TypeError):require(False,'HANDOVER_APPROVAL_WINDOW_INVALID')
    require(approval.get('real_data_approved') is False,'HANDOVER_REAL_DATA_SCOPE_NOT_GRANTED_BY_TOOL')


def load_plan(path):
    plan=read_json(path);body={k:v for k,v in plan.items() if k!='id'}
    require(plan.get('format')==FORMAT and plan.get('id')==release.digest(body),'HANDOVER_PLAN_TAMPERED')
    require(plan['product']['head']==PRODUCT and plan['recovery']['head']==RECOVERY,'HANDOVER_FIXED_PRODUCT_REQUIRED')
    return plan


def validate_product(record,out):
    require(record['head'] in (PRODUCT,RECOVERY),'HANDOVER_FIXED_PRODUCT_REQUIRED')
    source=release.clean_source(record['source_root'],record['head'])
    require(release.source_contract(source)==record['source_contract'],'HANDOVER_PRODUCT_CONTRACT_CHANGED')
    require(record['source_contract']['workbook_data']['reader_preserves_workbook_provenance'] is True,'HANDOVER_INCOMPATIBLE_RECOVERY_READER')
    require(not any((source/x).exists() for x in ('.env','apps/api/.env','apps/api/.env.local','apps/web/.env','apps/web/.env.local')),'HANDOVER_UNEXPECTED_RUNTIME_ENV_FILE')
    interpreters=record['interpreters']
    for key in ('python_launcher','python_base','node'):
        require(release.file_hash(Path(interpreters[key]).resolve())==interpreters[key+'_sha256'],'HANDOVER_INTERPRETER_CHANGED')
    release.validate_web_artifact(out,record)
    return source


def compatible_pair(product,recovery):
    require(product['head']==PRODUCT and recovery['head']==RECOVERY,'HANDOVER_EXACT_TARGET_AND_PREVIOUS_REQUIRED')
    for key in ('locks','schema_code'):
        require(product['source_contract'][key]==recovery['source_contract'][key],'HANDOVER_PREVIOUS_CONTRACT_INCOMPATIBLE')
    require(all(r['source_contract']['workbook_data']['reader_preserves_workbook_provenance'] is True for r in (product,recovery)),'HANDOVER_PREVIOUS_DATA_READER_INCOMPATIBLE')
    require(not release.git(Path(product['source_root']),'diff',RECOVERY,PRODUCT,'--','apps/api/app'),'HANDOVER_PREVIOUS_BACKEND_BYTES_DIFFER')

def make_plan(owner_root,nonce,kind,product_file,out,previous_file=None):
    require(release.no_links(out).is_relative_to(ROOT/'storage/private/runtime'),'HANDOVER_EXTERNAL_PRIVATE_PLAN_PATH_REQUIRED')
    require(previous_file is not None,'HANDOVER_VERIFIED_PREVIOUS_ARTIFACT_REQUIRED')
    owner=capture_owner(owner_root,nonce,kind)
    records=[read_json(product_file),read_json(previous_file)];compatible_pair(*records)
    bound=[]
    for slot,record in zip(('TARGET','RECOVERY'),records):
        require(record.get('portable') is True,'HANDOVER_PORTABLE_PRODUCT_ARTIFACT_REQUIRED')
        validate_product(record,Path(record['artifact_store']))
        artifact=release.validate_web_artifact(Path(record['artifact_store']),record)
        destination=out/record['web_artifact']['relative_root']
        if not destination.exists():release.copy_entries(artifact,destination,record['web_artifact']['files'])
        release.immutable(destination.parent/'artifact.json',record['web_artifact'])
        value={**record,'id':'r'+release.digest(dict(slot=slot,head=record['head'],artifact=record['build_hash']))[:24],'slot':slot}
        value.pop('artifact_store',None);validate_product(value,out);bound.append(value)
    body=dict(format=FORMAT,owner=owner,product=bound[0],recovery=bound[1],control_root=str(ROOT),control_head=release.git(ROOT,'rev-parse','HEAD'),
        code_hashes={name:release.file_hash(TOOL.parent/name) for name in CONTROL_FILES},
        legacy_semantics='guard0; original state is historical; external custodian is the sole normal owner',
        recovery_semantics='Verified previous9b using the same current DB/files; never a725 downgrade or database restore',real_data_approved=False)
    plan=dict(body,id=release.digest(body));release.immutable(out/'plan.json',plan)
    template=dict(decision='PENDING_USER_DECISION',plan_sha256=plan['id'],nonce=nonce,origin=owner['manifest']['origin'],product_head=PRODUCT,recovery_head=RECOVERY,
        actions=['activate','resume','recover','stop'],not_before=None,expires=None,decided_by=None,decision_reference=None,real_data_approved=False)
    release.immutable(out/'approval-template.json',template)
    return plan


CONTROL_FILES=('acceptance_handover.py','acceptance_handover_fence.py','acceptance_handover_projection.py','acceptance_handover_job.py')

def validate_control(plan):
    require(Path(plan['control_root']).resolve()==ROOT,'HANDOVER_FROZEN_LAUNCHER_ROOT_MISMATCH')
    require(release.git(ROOT,'rev-parse','HEAD')==plan['control_head'],'HANDOVER_LAUNCHER_HEAD_CHANGED')
    require(not release.git(ROOT,'status','--porcelain'),'HANDOVER_LAUNCHER_MUST_BE_CLEAN')
    require(set(plan['code_hashes'])==set(CONTROL_FILES),'HANDOVER_CONTROL_CONTRACT_MISSING')
    require(all(release.file_hash(TOOL.parent/n)==plan['code_hashes'][n] for n in CONTROL_FILES),'HANDOVER_LAUNCHER_BYTES_CHANGED')
    compatible_pair(plan['product'],plan['recovery'])
    for rec in (plan['product'],plan['recovery']):validate_product(rec,Path(plan['_out']))

def static_owner(plan,entry_fence=None):
    owner=plan['owner'];root,data,m,mhash=owner_paths(owner['root'],owner['manifest']['nonce'],owner['kind'])
    require(mhash==owner['manifest_sha256'] and m==owner['manifest'],'HANDOVER_MANIFEST_CHANGED')
    require(legacy_dirty_contract(root)==owner['documents'],'HANDOVER_PROTECTED_DOCUMENT_CHANGED')
    require((entry_fence.sha256() if entry_fence else release.file_hash(root/'apps/api/tests/manual_acceptance.py'))==owner['entrypoint_sha256'],'HANDOVER_ENTRYPOINT_CHANGED')
    require(docker_projection(m)==owner['resources'],'HANDOVER_DATABASE_RESOURCE_CHANGED')
    details=(data/'files').stat()
    require(dict(path=str(data/'files'),device=details.st_dev,inode=details.st_ino)==owner['files_directory'],'HANDOVER_FILES_DIRECTORY_REPLACED')
    for relative,key in [('accounts.json','accounts_file_sha256'),('tls/pki/authorities/local/root.crt','ca_sha256'),('Caddyfile','caddy_sha256')]:
        require(release.file_hash(data/relative)==owner[key],'HANDOVER_PRESERVED_RESOURCE_CHANGED')
    db=technical_database(m);require_quiet(db)
    require({k:db[k] for k in ('alembic','schema')}==owner['database'],'HANDOVER_SCHEMA_CHANGED')
    require(all(db[k]==owner['initial_checkpoint'][k] for k in ('actor_scope','memberships')),'HANDOVER_ROLE_OR_COMPANY_SCOPE_CHANGED')
    return root,data,m,db

def process_matches(expected):
    if not release.alive(expected['pid']):return False
    current=process_identity(expected['pid'])
    require(all(current[k]==expected[k] for k in ('created','exe','cwd','parent')),'HANDOVER_PID_REUSED_OR_OWNER_CHANGED')
    return True

def ports_free(m):
    require(not any(listener_owners([m[k] for k in ('api_port','web_port','https_port')]).values()),'HANDOVER_UNKNOWN_LISTENER_OR_CLEANUP_UNCONFIRMED')

def stop_legacy(plan,data,m):
    expected=plan['owner']['processes']
    require(read_json(data/'state.json')==plan['owner']['legacy_state'],'HANDOVER_LEGACY_STATE_CHANGED')
    require(all(process_matches(v) for v in expected.values()),'HANDOVER_LEGACY_PROCESS_MISSING')
    require(set(descendant_identities(plan['owner']['legacy_state']['supervisor']))==set(expected),'HANDOVER_NEW_OR_UNKNOWN_LEGACY_DESCENDANT')
    require(all(release.file_hash(Path(v['exe']).resolve())==v['exe_sha256'] for v in expected.values()),'HANDOVER_LEGACY_EXECUTABLE_BYTES_CHANGED')
    require(not (data/'stop.request').exists(),'HANDOVER_EXISTING_STOP_REQUEST')
    # This is the legacy supervisor's normal protocol, not a state rewrite or DB stop.
    (data/'stop.request').write_text(m['nonce'],encoding='utf-8')
    until=time.monotonic()+60
    while time.monotonic()<until:
        state=read_json(data/'state.json')
        if state.get('phase')=='STOPPED' and not any(release.alive(v['pid']) for v in expected.values()):break
        time.sleep(.2)
    else:require(False,'HANDOVER_LEGACY_NORMAL_STOP_UNCONFIRMED_NO_KILL')
    require(state.get('nonce')==m['nonce'] and state.get('head')==LEGACY,'HANDOVER_LEGACY_STOP_IDENTITY_CHANGED')
    ports_free(m);require_quiet(technical_database(m))
    return release.file_hash(data/'state.json')

def public_identity(plan,head):
    owner=plan['owner'];m=owner['manifest'];data=Path(owner['data_root'])
    tls=ssl.create_default_context(cafile=str(data/'tls/pki/authorities/local/root.crt'))
    with socket.create_connection(('127.0.0.1',m['https_port']),timeout=5) as raw:
        with tls.wrap_socket(raw,server_hostname='127.0.0.1') as peer:
            require(sha256(peer.getpeercert(binary_form=True)).hexdigest()==owner['certificate_sha256'],'HANDOVER_CERTIFICATE_CHANGED')
    connection=http.client.HTTPSConnection('127.0.0.1',m['https_port'],context=tls,timeout=5)
    try:
        connection.request('GET','/login');response=connection.getresponse()
        require(response.status==200 and response.getheader('X-DATCO-Acceptance')==m['nonce'] and response.getheader('X-DATCO-Acceptance-Head')==head,'HANDOVER_PUBLIC_IDENTITY_MISMATCH')
    finally:connection.close()

def event(out,action,**details):
    release.immutable(out/'events'/(uuid4().hex+'.json'),dict(action=action,time=datetime.now(timezone.utc).isoformat(),**details))

def runtime_environment(plan,rec,m):
    data=Path(plan['owner']['data_root']);source=Path(rec['source_root'])
    env=release.release_environment(m,data,source,rec)
    env['DATCO_TEST_WORKER_READY']=str(Path(plan['_out'])/'worker-ready.json')
    env['NEXT_TELEMETRY_DISABLED']='1'
    return env

def runtime_manifest(plan):
    # Trusted runtime configuration is consumed only AFTER approval and owner gates.
    # Never inspect test account passwords or emit the database URL.
    data=Path(plan['owner']['data_root']);raw=read_json(data/'manifest.json')
    m={**plan['owner']['manifest'],'url':raw['url']}
    require(isinstance(m['url'],str),'HANDOVER_RUNTIME_DATABASE_CONFIGURATION_MISSING')
    from sqlalchemy.engine import make_url
    url=make_url(m['url'])
    require((url.drivername,url.host,url.port,url.database,url.username)==('postgresql+psycopg','127.0.0.1',m['pg_port'],m['db'],m['role']),'HANDOVER_DATABASE_URL_IDENTITY_MISMATCH')
    return m

def child_main(plan_path,component):
    out=Path(plan_path).resolve().parent;plan=load_plan(plan_path);plan['_out']=str(out)
    lease=read_json(out/'state.json')
    require(lease.get('plan')==plan['id'] and lease.get('phase')=='STARTING','HANDOVER_CHILD_HANDSHAKE_REQUIRED')
    require(process_matches(lease['custodian']),'HANDOVER_CUSTODIAN_MISSING')
    parent=process_identity(os.getpid())['parent']
    if parent!=lease['custodian']['pid']:
        ancestors={v['pid']:v for v in lease.get('children',[])}
        require(parent in ancestors and process_matches(ancestors[parent]) and ancestors[parent]['parent']==lease['custodian']['pid'],'HANDOVER_CHILD_PARENT_MISMATCH')
    validate_approval(plan,read_json(out/'active-approval.json'),lease['approval_action'])
    validate_control(plan)
    m=runtime_manifest(plan);rec=plan['product' if lease['slot']=='TARGET' else 'recovery'];source=Path(rec['source_root'])
    env=runtime_environment(plan,rec,m);os.environ.clear();os.environ.update(env)
    sys.path[:0]=[str(source/'apps/api'),str(source/'apps/api/tests')]
    uat.ROOT=source;uat.API=source/'apps/api';uat.WEB=source/'apps/web';uat.BASE=Path(plan['owner']['data_root']).parent
    if component=='api':
        import uvicorn
        uvicorn.run('manual_acceptance_server:app',host='127.0.0.1',port=m['api_port'],access_log=False,log_level='critical')
    else:
        import runpy
        runpy.run_path(str(source/'apps/api/tests/isolated_worker.py'),run_name='__main__')

def start_slot(plan,slot,m,fault=None):
    from acceptance_handover_job import OwnedJob
    out=Path(plan['_out']);rec=plan['product' if slot=='TARGET' else 'recovery'];source=validate_product(rec,out)
    if fault:require(plan['owner']['kind']=='SYNTHETIC_CLONE' and fault in ('api','worker','web'),'HANDOVER_TEST_FAULT_REJECTED')
    ports_free(m);execution=release.execution_web(out,rec);ready=out/'worker-ready.json';ready.unlink(missing_ok=True)
    env=runtime_environment(plan,rec,m);job=OwnedJob()
    def spawn(label,command,cwd):
        if label==fault:command=[rec['interpreters']['python_launcher'],'-c','raise SystemExit(73)']
        def remember(_):
            lease=read_json(out/'state.json');lease['children']=[process_identity(p.pid) for p in job.children];save(out/'state.json',lease)
        return job.spawn(command,cwd,env,on_created=remember)
    try:
        python=rec['interpreters']['python_launcher']
        spawn('api',[python,'-B',TOOL,'api-child','--plan',out/'plan.json'],source/'apps/api')
        identity=uat.wait_url('http://127.0.0.1:'+str(m['api_port'])+'/__test/identity',job.children,deadline=70)
        expected=(m['db'],m['role'],m['nonce'],rec['head'],str(Path(plan['owner']['data_root'])/'files'))
        require((identity['database'],identity['db_user'],identity['nonce'],identity['head'],str(Path(identity['files']).resolve()))==expected,'HANDOVER_API_IDENTITY_MISMATCH')
        spawn('worker',[python,'-B',TOOL,'worker-child','--plan',out/'plan.json'],source/'apps/api')
        until=time.monotonic()+30
        while not ready.exists():
            require(job.children[-1].poll() is None and time.monotonic()<until,'HANDOVER_WORKER_NOT_READY');time.sleep(.2)
        worker=read_json(ready)
        require((worker['database'],worker['db_user'],worker['nonce'],worker['head'],str(Path(worker['files']).resolve()))==expected,'HANDOVER_WORKER_IDENTITY_MISMATCH')
        spawn('web',[rec['interpreters']['node'],source/'apps/web/node_modules/next/dist/bin/next','start','--hostname','127.0.0.1','--port',str(m['web_port'])],execution['web_root'])
        uat.wait_url('http://127.0.0.1:'+str(m['web_port'])+'/login',job.children,deadline=70)
        gateway=out/('gateway-'+rec['id']+'.Caddyfile')
        text=generated_gateway(Path(plan['owner']['root']),m,rec['head'])
        if gateway.exists():require(gateway.read_text(encoding='utf-8')==text,'HANDOVER_DERIVED_GATEWAY_CHANGED')
        else:gateway.write_text(text,encoding='utf-8')
        spawn('gateway',[m['caddy'],'run','--config',gateway,'--adapter','caddyfile'],source)
        until=time.monotonic()+20
        while True:
            require(all(p.poll() is None for p in job.children),'HANDOVER_CHILD_EXITED')
            try:public_identity(plan,rec['head']);break
            except (OSError,RuntimeError):
                require(time.monotonic()<until,'HANDOVER_GATEWAY_START_UNCONFIRMED');time.sleep(.2)
        return job,execution
    except BaseException as exc:
        lease=read_json(out/'state.json');lease['children']=[dict(pid=p.pid) for p in job.children];save(out/'state.json',lease)
        job.close();ports_free(m)
        if isinstance(exc,KeyboardInterrupt):raise
        raise RuntimeError('HANDOVER_SLOT_START_FAILED_CLEANED') from None

def current_lease(out,plan,phase,slot,**extra):
    value=dict(plan=plan['id'],phase=phase,slot=slot,product_head=PRODUCT,head=plan['product' if slot=='TARGET' else 'recovery']['head'],custodian=process_identity(os.getpid()),**extra)
    save(out/'state.json',value);return value

def require_clean_resume(lease):
    require(lease.get('phase') in ('STOPPED','FAILED') and lease.get('cleanup_complete') is True,'HANDOVER_UNCLEAN_LEASE_REQUIRES_TECHNICAL_RECONCILIATION')

def run_owner(plan_path,approval_path,mode='activate',fault=None):
    out=Path(plan_path).resolve().parent;plan=load_plan(plan_path);plan['_out']=str(out)
    approval=read_json(approval_path);validate_approval(plan,approval,mode)
    require(fault is None or (plan['owner']['kind']=='SYNTHETIC_CLONE' and fault in ('api','worker','web')),'HANDOVER_TEST_FAULT_REJECTED')
    validate_control(plan);root,data,m,_=static_owner(plan)
    m=runtime_manifest(plan) # Exact URL target gate before any legacy stop/fence/write.
    require(release.db_snapshot(m)['alembic']==plan['owner']['database']['alembic'],'HANDOVER_RUNTIME_DATABASE_PROBE_MISMATCH')
    require(not (out/'request.json').exists(),'HANDOVER_PENDING_REQUEST_REJECTED')
    if mode=='activate':
        require(not (out/'state.json').exists(),'HANDOVER_EXISTING_LEASE_REQUIRES_RESUME')
        require(read_json(data/'state.json')==plan['owner']['legacy_state'],'HANDOVER_LEGACY_STATE_CHANGED')
    else:
        require(mode=='resume','HANDOVER_MODE_REJECTED')
        lease=read_json(out/'state.json');require_clean_resume(lease)
        require(lease.get('plan')==plan['id'] and lease.get('stopped_state_sha256'),'HANDOVER_RESUME_ANCHOR_MISSING')
        require(not release.alive(lease['custodian']['pid']),'HANDOVER_CUSTODIAN_STILL_RUNNING_OR_PID_REUSED')
        require(not any(release.alive(v['pid']) for v in lease.get('children',[])),'HANDOVER_PRIOR_CHILD_CLEANUP_UNCONFIRMED')
        require(read_json(data/'state.json').get('phase')=='STOPPED' and release.file_hash(data/'state.json')==lease['stopped_state_sha256'],'HANDOVER_HISTORICAL_STATE_CHANGED_NO_REWRITE')
        ports_free(m)
    job=None;slot='TARGET';stopped_hash=None;children=[];finished=False
    with release.action_lock(out),ExitStack() as stack:
        entry=stack.enter_context(FileFence(root/'apps/api/tests/manual_acceptance.py',exclusive=True))
        static_owner(plan,entry)
        if mode=='activate':stopped_hash=stop_legacy(plan,data,m)
        else:stopped_hash=lease['stopped_state_sha256']
        current_lease(out,plan,'STOPPED',slot,stopped_state_sha256=stopped_hash,children=[],cleanup_complete=True)
        fence=stack.enter_context(FileFence(data/'state.json',exclusive=False))
        require(fence.sha256()==stopped_hash,'HANDOVER_STATE_FENCE_RACE')
        save(out/'active-approval.json',approval)
        event(out,'LEGACY_HANDED_OVER' if mode=='activate' else 'EXPLICIT_RECONCILIATION',legacy_state_sha256=stopped_hash)
        def begin(selected,inject=None,action=mode):
            nonlocal job,children,slot
            slot=selected;validate_approval(plan,approval,action);validate_control(plan);static_owner(plan,entry)
            current_lease(out,plan,'STARTING',slot,stopped_state_sha256=stopped_hash,approval_action=action,children=[])
            job,execution=start_slot(plan,slot,m,inject)
            children=[process_identity(p.pid) for p in job.children]
            current_lease(out,plan,'RUNNING',slot,stopped_state_sha256=stopped_hash,approval_action=action,children=children,web_execution=execution)
            event(out,'RUNNING',slot=slot,release=plan['product' if slot=='TARGET' else 'recovery']['id'])
        try:
            try:begin(slot,fault)
            except RuntimeError as exc:
                require(str(exc)=='HANDOVER_SLOT_START_FAILED_CLEANED','HANDOVER_PREFLIGHT_OR_CLEANUP_FAILED_NO_FALLBACK')
                event(out,'START_FAILED_CLEANED',component_fault=fault,reason=type(exc).__name__)
                validate_approval(plan,approval,'recover');begin('RECOVERY',action='recover')
            while True:
                require(all(p.poll() is None for p in job.children),'HANDOVER_CHILD_EXITED')
                request=out/'request.json'
                if not request.exists():time.sleep(.25);continue
                req=read_json(request);action=req['action'];receipt=req['approval']
                try:
                    require(action in ('recover','stop'),'HANDOVER_REQUEST_ACTION_REJECTED');validate_approval(plan,receipt,action)
                    require(req.get('custodian')==process_identity(os.getpid()),'HANDOVER_REQUEST_CUSTODIAN_CHANGED')
                    approval=receipt;save(out/'active-approval.json',approval)
                    validate_control(plan);static_owner(plan,entry);require(fence.sha256()==stopped_hash,'HANDOVER_HISTORICAL_STATE_CHANGED')
                except BaseException as exc:
                    event(out,'REQUEST_REJECTED',reason=type(exc).__name__);request.unlink();continue
                require_quiet(technical_database(m));job.close();job=None;ports_free(m);request.unlink()
                event(out,'OWN_CHILDREN_STOPPED',action_requested=action)
                if action=='stop':finished=True;break
                begin('RECOVERY',action='recover')
        finally:
            clean=finished
            if job is not None:
                try:job.close();clean=job.cleanup_confirmed
                except BaseException:
                    prior=read_json(out/'state.json');current_lease(out,plan,'FAILED',slot,stopped_state_sha256=stopped_hash,children=children or prior.get('children',[]),cleanup_complete=False)
                    raise
            ports_free(m)
            prior=read_json(out/'state.json')
            current_lease(out,plan,'STOPPED' if finished and clean else 'FAILED',slot,stopped_state_sha256=stopped_hash,children=children or prior.get('children',[]),cleanup_complete=clean)
            event(out,'STOPPED_PRESERVED' if finished and clean else 'FAILED_REQUIRES_RECONCILIATION',slot=slot,cleanup_complete=clean)

def request_action(plan_path,approval_path,action):
    out=Path(plan_path).resolve().parent;plan=load_plan(plan_path);approval=read_json(approval_path)
    validate_approval(plan,approval,action);require(action in ('recover','stop'),'HANDOVER_REQUEST_ACTION_REJECTED')
    lease=read_json(out/'state.json');require(lease.get('plan')==plan['id'] and lease.get('phase')=='RUNNING','HANDOVER_RUNNING_CUSTODIAN_REQUIRED')
    require(process_matches(lease['custodian']),'HANDOVER_CUSTODIAN_MISSING')
    require(not (out/'request.json').exists(),'HANDOVER_PENDING_REQUEST_REJECTED')
    save(out/'request.json',dict(action=action,approval=approval,custodian=lease['custodian']))

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','activate','resume','recover','stop','status','api-child','worker-child'])
    parser.add_argument('--plan',type=Path);parser.add_argument('--approval',type=Path)
    parser.add_argument('--owner-root',type=Path);parser.add_argument('--nonce');parser.add_argument('--kind',choices=['EXISTING_OWNER','SYNTHETIC_CLONE'])
    parser.add_argument('--previous-product',type=Path);parser.add_argument('--product',type=Path);parser.add_argument('--out',type=Path);parser.add_argument('--fixture-fault',choices=['api','worker','web'])
    a=parser.parse_args()
    try:
        if a.action=='prepare':
            require(all((a.owner_root,a.nonce,a.kind,a.product,a.out,a.previous_product)),'HANDOVER_PREPARE_ARGUMENTS_REQUIRED')
            private_directory(a.out);p=make_plan(a.owner_root,a.nonce,a.kind,a.product,a.out,a.previous_product)
            print(json.dumps(dict(result='PREPARED_NOT_APPLIED',plan_sha256=p['id'],product_head=PRODUCT,recovery_head=RECOVERY)))
        elif a.action in ('api-child','worker-child'):child_main(a.plan,'api' if a.action=='api-child' else 'worker')
        elif a.action in ('activate','resume'):run_owner(a.plan,a.approval,a.action,a.fixture_fault)
        elif a.action in ('recover','stop'):request_action(a.plan,a.approval,a.action)
        else:
            p=load_plan(a.plan);out=a.plan.resolve().parent
            print(json.dumps(dict(plan_sha256=p['id'],applied=(out/'state.json').exists(),product_head=p['product']['head'],recovery_head=p['recovery']['head'],approval='SEPARATE_DECISION_REQUIRED')))
    except BaseException as exc:
        # Runtime exceptions can contain DSNs; only bounded known codes/class names.
        reason=str(exc) if isinstance(exc,RuntimeError) and re.fullmatch('(HANDOVER|RELEASE)_[A-Z0-9_]+',str(exc)) else type(exc).__name__
        if a.action in ('api-child','worker-child'):
            save(a.plan.resolve().parent/('diagnostic-'+a.action+'.json'),dict(component=a.action,reason=reason))
        else:print(json.dumps(dict(result='BLOCKED',reason=reason)),flush=True)
        raise SystemExit(1) from None

if __name__=='__main__':main()