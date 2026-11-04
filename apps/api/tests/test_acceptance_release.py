"""Release guards and recovery order, without Docker/DB/HTTP/services/credentials."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest
import acceptance_release as release
import manual_acceptance as uat

# Exact SourceModel/Metadata definitions extracted read-only from f49dbd8;
# full original source SHA256 c4f29352b9a0275415c2d46d9bb5aa7dd30fb42b54b5c1fa4f9bafc360f1324f.
# Kept inline so CI does not require historical Git objects or an old worktree.
F49_METADATA_SOURCE = 'from pydantic import BaseModel, ConfigDict, Field\n\nclass SourceModel(BaseModel):\n    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=False)\n\nclass Metadata(SourceModel):\n    schema_version: str\n    artifact_kind: str = Field(min_length=1)\n    source_workbook: str = Field(min_length=1)\n    source_sheet: str = Field(min_length=1)\n    source_display_date: str\n    feature_count: int = Field(gt=0)\n    system_count: int = Field(gt=0)\n    group_count: int = Field(gt=0)\n    uniqueness_rule: str = Field(min_length=1)\n    system_counts: dict[str,int]\n    prepared_date: str | None = None\n    availability_assertion: str | None = None\n    fields: list[str] | None = None\n'


@pytest.fixture(autouse=True)
def preserve_legacy_globals(monkeypatch):
    for key in ('ROOT','API','WEB','BASE'):
        monkeypatch.setattr(uat,key,getattr(uat,key))


def sample(root,nonce='abc123456789'):
    return dict(nonce=nonce,root=str(root),head='a'*40,db='datco_test_'+nonce,
        role='datco_test_role_'+nonce,container='datco-mvp-uat-'+nonce,
        volume='datco-mvp-uat-pg-'+nonce,host='127.0.0.1',https_port=19451,
        pg_port=45100,api_port=45101,web_port=45102,preparation=True,
        origin='https://127.0.0.1:19451',url='postgresql+psycopg://TEST:TEST@127.0.0.1:45100/TEST')


def record(head='a'*40,identifier=None):
    value=dict(schema=release.RECORD_SCHEMA,owner={'identity':'SYNTHETIC'},head=head,source_root='SYNTHETIC_SOURCE',
        source_contract=dict(locks={'lock':'fixed'},schema_code='fixed',release_owner_guard=1,workbook_data=dict(format=release.DATA_FORMAT,probe_version=1,reader_preserves_workbook_provenance=True,writer_may_emit_workbook_provenance=True)),database=dict(alembic=['v1'],schema='fixed'))
    return dict(value,id=identifier or 'r'+release.digest(value)[:24])


@pytest.mark.parametrize('port',[8443,8444,18445,49355,49356])
def test_protected_owner_refused_before_any_docker_or_database_access(tmp_path,monkeypatch,port):
    m=sample(tmp_path);m['https_port']=port;m['origin']='https://127.0.0.1:'+str(port)
    monkeypatch.setattr(uat,'repository_common_dir',lambda *a:tmp_path)
    monkeypatch.setattr(uat,'load',lambda *a:m)
    monkeypatch.setattr(uat,'owned',lambda *a:tmp_path/m['nonce'])
    monkeypatch.setattr(uat,'inspect_label',lambda *a:pytest.fail('protected owner must not inspect Docker'))
    with pytest.raises(RuntimeError,match='SEPARATE_LOOPBACK'):
        release.owner_context(tmp_path,m['nonce'])


def test_records_are_append_only_and_tampering_is_detected(tmp_path):
    body=dict(schema=release.RECORD_SCHEMA,head='a'*40,build_hash='synthetic-build',source_contract=record()['source_contract'])
    identifier='r'+release.digest(body)[:24]
    value=dict(body,id=identifier);path=tmp_path/'releases'/(identifier+'.json')
    release.immutable(path,value)
    assert release.load_record(tmp_path,identifier)==value
    with pytest.raises(FileExistsError):release.immutable(path,value)
    path.write_text(json.dumps(dict(value,head='b'*40)),encoding='utf-8')
    with pytest.raises(RuntimeError,match='TAMPERED'):release.load_record(tmp_path,identifier)


def test_build_hash_detects_actual_artifact_change_and_ignores_runtime_cache(tmp_path):
    (tmp_path/'BUILD_ID').write_text('SYNTHETIC_BUILD',encoding='utf-8')
    first=release.tree_hash(tmp_path)
    (tmp_path/'cache').mkdir();(tmp_path/'cache/runtime').write_text('temporary',encoding='utf-8')
    assert release.tree_hash(tmp_path)==first
    (tmp_path/'BUILD_ID').write_text('CHANGED_BUILD',encoding='utf-8')
    assert release.tree_hash(tmp_path)!=first


@pytest.mark.parametrize('part',['locks','schema_code','database','owner'])
def test_rollback_is_blocked_for_incompatible_schema_or_dependency_contract(part):
    a=record();b=deepcopy(a)
    if part in ('locks','schema_code'):b['source_contract'][part]='different'
    else:b[part]={'different':'contract'}
    with pytest.raises(RuntimeError):release.compatible(a,b)


def test_enrollment_preserves_manifest_and_requires_exact_nonce_and_initial_artifact(tmp_path,monkeypatch):
    m=sample(tmp_path);r=record();r.update(source_root=str(tmp_path),head=m['head'])
    manifest=tmp_path/'manifest.json';manifest.write_text(json.dumps(m),encoding='utf-8');before=manifest.read_bytes()
    monkeypatch.setattr(release,'state',lambda *a:dict(phase='STOPPED'))
    monkeypatch.setattr(release,'owner_guard_version',lambda *a:1)
    monkeypatch.setattr(release,'validate_record',lambda *a,**k:tmp_path)
    with pytest.raises(RuntimeError,match='NONCE_REQUIRED'):release.enroll(tmp_path,m,tmp_path,r,'wrong')
    release.enroll(tmp_path,m,tmp_path,r,m['nonce'])
    assert manifest.read_bytes()==before
    assert release.selection(tmp_path)['current']==r['id']
    assert release.enrollment(tmp_path)['owner']==r['owner']
    with pytest.raises(FileExistsError):release.enroll(tmp_path,m,tmp_path,r,m['nonce'])


def setup_switch(tmp_path,monkeypatch):
    m=sample(tmp_path);old=record();new=record('b'*40);seen=[]
    monkeypatch.setattr(release,'enrollment',lambda *a:dict(owner=old['owner']))
    monkeypatch.setattr(release,'owner_identity',lambda *a:old['owner'])
    monkeypatch.setattr(release,'selection',lambda *a:dict(current=old['id'],previous=None))
    monkeypatch.setattr(release,'load_record',lambda out,key:{old['id']:old,new['id']:new}[key])
    monkeypatch.setattr(release,'state',lambda *a:dict(nonce=m['nonce'],phase='RUNNING',head=old['head'],release=old['id']))
    monkeypatch.setattr(release,'validate_record',lambda owner,m,out,r,**k:seen.append('validate:'+r['id']))
    monkeypatch.setattr(release,'wait_stopped',lambda *a,**k:seen.append('stopped'))
    return m,old,new,seen


def test_switch_verifies_both_artifacts_before_stop_and_only_changes_selection_after_start(tmp_path,monkeypatch):
    m,old,new,seen=setup_switch(tmp_path,monkeypatch)
    monkeypatch.setattr(release,'launch',lambda owner,m,out,r:seen.append('launch:'+r['id']))
    release.switch(tmp_path,m,tmp_path,new['id'],m['nonce'])
    assert seen==['validate:'+old['id'],'validate:'+new['id'],'stopped','launch:'+new['id']]
    chosen=json.loads((tmp_path/'release-selection.json').read_text(encoding='utf-8'))
    assert chosen==dict(current=new['id'],previous=old['id'])


def test_failed_target_restores_previous_artifact_after_confirmed_cleanup_without_db_restore(tmp_path,monkeypatch):
    m,old,new,seen=setup_switch(tmp_path,monkeypatch)
    def launch(owner,m,out,r):
        seen.append('launch:'+r['id'])
        if r['id']==new['id']:raise RuntimeError('RELEASE_TARGET_START_FAILED_CLEANED')
    monkeypatch.setattr(release,'launch',launch)
    with pytest.raises(RuntimeError,match='PREVIOUS_RESTORED'):
        release.switch(tmp_path,m,tmp_path,new['id'],m['nonce'])
    assert seen[-3:]==['launch:'+new['id'],'validate:'+old['id'],'launch:'+old['id']]
    assert not (tmp_path/'release-selection.json').exists()
    assert len(list((tmp_path/'release-events').glob('*.json')))==1


def test_uncertain_target_cleanup_never_starts_another_release(tmp_path,monkeypatch):
    m,old,new,seen=setup_switch(tmp_path,monkeypatch)
    def launch(owner,m,out,r):
        seen.append('launch:'+r['id']);raise RuntimeError('RELEASE_CHILD_CLEANUP_UNCONFIRMED')
    monkeypatch.setattr(release,'launch',launch)
    with pytest.raises(RuntimeError,match='CLEANUP_UNCONFIRMED'):
        release.switch(tmp_path,m,tmp_path,new['id'],m['nonce'])
    assert seen.count('launch:'+new['id'])==1 and 'launch:'+old['id'] not in seen


def test_changed_source_or_database_is_rejected_before_stop(tmp_path,monkeypatch):
    m,old,new,seen=setup_switch(tmp_path,monkeypatch)
    def changed(*args,**kwargs):raise RuntimeError('RELEASE_DATABASE_SCHEMA_CHANGED')
    monkeypatch.setattr(release,'validate_record',changed)
    with pytest.raises(RuntimeError,match='SCHEMA_CHANGED'):
        release.switch(tmp_path,m,tmp_path,new['id'],m['nonce'])
    assert 'stopped' not in seen


def test_recovery_lock_rejects_concurrent_switch_and_retains_owner_state(tmp_path):
    with release.action_lock(tmp_path):
        with pytest.raises(RuntimeError,match='ACTION_IN_PROGRESS'):
            with release.action_lock(tmp_path):pytest.fail('must not enter')
    assert not (tmp_path/'release-action.lock').exists()


def test_release_environment_keeps_owner_data_identity_and_uses_source_code_paths(tmp_path):
    owner=tmp_path/'owner';source=tmp_path/'source';out=owner/'storage/private/runtime/manual-acceptance/abc123456789'
    m=sample(owner);r=dict(head='b'*40,dist_dir='.next/datco-e2e-b123456789ab')
    env=release.release_environment(m,out,source,r)
    assert Path(env['DATCO_TEST_FILES'])==out/'files'
    assert env['DATCO_TEST_NONCE']==m['nonce'] and env['DATCO_TEST_DATABASE']==m['db']
    assert env['DATCO_ACCEPTANCE_HEAD']==r['head'] and env['DATCO_TEST_DIST_DIR']==r['dist_dir']
    assert str(source/'apps/api') in env['PYTHONPATH']
    assert env['DATABASE_URL']==m['url']


def test_only_enrolled_owner_is_redirected_from_legacy_start(tmp_path,monkeypatch):
    m=sample(tmp_path)
    monkeypatch.setattr(uat,'load',lambda *a:m);monkeypatch.setattr(uat,'owned',lambda *a:tmp_path)
    uat.write(tmp_path/'state.json',dict(phase='STOPPED'))
    (tmp_path/'release-owner.json').write_text('{}',encoding='utf-8')
    monkeypatch.setattr(sys,'argv',['manual_acceptance.py','start','--nonce',m['nonce']])
    monkeypatch.setattr(uat,'head',lambda:pytest.fail('enrolled legacy start must not bypass release validation'))
    with pytest.raises(RuntimeError,match='USE_ACCEPTANCE_RELEASE_TOOL'):uat.main()


def test_stopped_wait_never_kills_unverified_pids(tmp_path,monkeypatch):
    monkeypatch.setattr(release,'state',lambda *a:dict(phase='STOPPED'))
    monkeypatch.setattr(release,'alive',lambda *a:False)
    release.wait_stopped(tmp_path,dict(phase='RUNNING',children=[123]),timeout=1)
    assert (tmp_path/'stop.request').exists()


def test_internal_service_requires_release_handshake_before_starting_children(tmp_path):
    uat.write(tmp_path/'state.json',dict(phase='STOPPED'))
    with pytest.raises(RuntimeError,match='HANDSHAKE_REQUIRED'):
        release.serve(tmp_path,sample(tmp_path),tmp_path,record())


def test_target_cannot_claim_an_unattested_existing_build(tmp_path,monkeypatch):
    owner=tmp_path/'owner';source=tmp_path/'source';m=sample(owner)
    monkeypatch.setattr(release,'clean_source',lambda *a:source)
    monkeypatch.setattr(uat,'repository_common_dir',lambda *a:tmp_path)
    monkeypatch.setattr(release,'source_contract',lambda *a:pytest.fail('must reject before dependency or DB inspection'))
    with pytest.raises(RuntimeError,match='FRESH_ARTIFACT_BUILD_REQUIRED'):
        release.prepare(owner,m,tmp_path,source,'b'*40,'.next/datco-e2e-a123456789bc',False)


@pytest.mark.parametrize('declaration,expected',[
    ('RELEASE_OWNER_GUARD_VERSION = 1',1),
    ('RELEASE_OWNER_GUARD_VERSION = 0',0),
    ('RELEASE_OWNER_GUARD_VERSION = True',0),
    ('RELEASE_OWNER_GUARD_VERSION = int(1)',0),
    ('RELEASE_OWNER_GUARD_VERSION = 1\nRELEASE_OWNER_GUARD_VERSION = 0',0),
    ('OTHER_VERSION = 1',0)])
def test_owner_start_guard_contract_is_read_only_ast_not_executed(tmp_path,declaration,expected):
    path=tmp_path/'apps/api/tests/manual_acceptance.py';path.parent.mkdir(parents=True)
    path.write_text(declaration+'\nraise RuntimeError("OWNER_CODE_MUST_NOT_EXECUTE")\n',encoding='utf-8')
    assert release.owner_guard_version(tmp_path)==expected


@pytest.mark.parametrize('declared,recorded',[(0,1),(1,0),(0,0)])
def test_enrollment_refuses_legacy_owner_without_opt_in_start_guard_before_writing(tmp_path,monkeypatch,declared,recorded):
    m=sample(tmp_path);r=record();r['source_contract']['release_owner_guard']=recorded
    monkeypatch.setattr(release,'state',lambda *a:dict(phase='STOPPED'))
    monkeypatch.setattr(release,'owner_guard_version',lambda *a:declared)
    monkeypatch.setattr(release,'validate_record',lambda *a,**k:pytest.fail('unsupported owner must fail before artifact or DB validation'))
    with pytest.raises(RuntimeError,match='OWNER_START_GUARD_UNSUPPORTED'):
        release.enroll(tmp_path,m,tmp_path,r,m['nonce'])
    assert not (tmp_path/'release-owner.json').exists()
    assert not (tmp_path/'release-selection.json').exists()


def test_current_legacy_start_implements_the_declared_opt_in_contract():
    assert uat.RELEASE_OWNER_GUARD_VERSION==1
    assert release.owner_guard_version(release.ROOT)==1


@pytest.mark.parametrize('old_reader,old_writer,new_reader,new_writer,allowed',[
    (False,False,False,False,True),
    (False,False,True,True,False),
    (True,True,False,False,False),
    (False,True,True,False,False),
    (True,False,True,True,True),
    (True,True,True,False,True),
    (True,True,True,True,True)])
def test_persisted_workbook_json_must_be_readable_on_both_sides_of_code_rollback(old_reader,old_writer,new_reader,new_writer,allowed):
    old,new=record(),record('b'*40)
    for value,reader,writer in ((old,old_reader,old_writer),(new,new_reader,new_writer)):
        value['source_contract']['workbook_data'].update(reader_preserves_workbook_provenance=reader,writer_may_emit_workbook_provenance=writer)
    if allowed:release.compatible(old,new)
    else:
        with pytest.raises(RuntimeError,match='BACKWARD_DATA_CONTRACT_INCOMPATIBLE'):release.compatible(old,new)


def test_missing_json_descriptor_and_old_record_schema_fail_closed():
    old,new=record(),record('b'*40)
    del old['source_contract']['workbook_data']
    with pytest.raises(RuntimeError,match='BACKWARD_DATA_CONTRACT_INCOMPATIBLE'):release.compatible(old,new)
    old=record();old['schema']='datco-uat-release-v1'
    with pytest.raises(RuntimeError,match='RECORD_SCHEMA_UNSUPPORTED'):release.compatible(old,new)


def test_workbook_json_incompatibility_is_rejected_before_stop_or_database_checks(tmp_path,monkeypatch):
    m,old,new,seen=setup_switch(tmp_path,monkeypatch)
    old['source_contract']['workbook_data'].update(reader_preserves_workbook_provenance=False,writer_may_emit_workbook_provenance=False)
    with pytest.raises(RuntimeError,match='BACKWARD_DATA_CONTRACT_INCOMPATIBLE'):
        release.switch(tmp_path,m,tmp_path,new['id'],m['nonce'])
    assert not seen


def test_exact_f49_metadata_rejects_synthetic_new_json_while_current_preserves_it():
    from app.infrastructure.dmp_inventory import Metadata
    original=F49_METADATA_SOURCE
    namespace={'__name__':'q06_frozen_metadata'}
    exec(compile(original,'frozen_metadata.py','exec'),namespace)
    sample=dict(schema_version='workbook-v1',artifact_kind='SYNTHETIC_RELEASE_PROBE',source_workbook='SYNTHETIC.xlsx',source_sheet='SYNTHETIC',source_display_date='',feature_count=1,system_count=1,group_count=1,uniqueness_rule='feature_id',system_counts={'SYNTHETIC':1},workbook_provenance={'rows':[{'row_key':'0:2','cells':{'name':{'cell':'C2'}}}]})
    from pydantic import ValidationError
    with pytest.raises(ValidationError) as error:namespace['Metadata'].model_validate(sample)
    assert any(item['type']=='extra_forbidden' for item in error.value.errors())
    assert Metadata.model_validate(sample).model_dump()['workbook_provenance']==sample['workbook_provenance']


def test_current_source_python_reports_actual_workbook_reader_and_tracked_writer(monkeypatch):
    monkeypatch.setattr(release,'python_at',lambda source:Path(sys.executable))
    descriptor=release.workbook_data_contract(release.ROOT)
    assert descriptor==dict(format=release.DATA_FORMAT,probe_version=1,reader_preserves_workbook_provenance=True,writer_may_emit_workbook_provenance=True)


def test_reader_that_accepts_but_discards_workbook_json_is_not_compatible(tmp_path,monkeypatch):
    module=tmp_path/'apps/api/app/infrastructure/dmp_inventory.py';module.parent.mkdir(parents=True)
    module.write_text("from pydantic import BaseModel\nclass Metadata(BaseModel):\n    schema_version: str\n",encoding='utf-8')
    monkeypatch.setattr(release,'python_at',lambda source:Path(sys.executable))
    monkeypatch.setattr(release,'git',lambda *a:'')
    descriptor=release.workbook_data_contract(tmp_path)
    assert descriptor['reader_preserves_workbook_provenance'] is False
    assert descriptor['writer_may_emit_workbook_provenance'] is False


def canonical_old_tree_hash(directory):
    # Exact pre-optimization order, exclusions, ancestor guard and digest recipe.
    import os
    directory=release.no_links(directory)
    if not directory.is_dir():release.fail('RELEASE_ARTIFACT_MISSING')
    entries=[]
    for base,dirs,files in os.walk(directory,followlinks=False):
        for name in [*dirs,*files]:release.no_links(Path(base)/name)
        dirs[:]=sorted(d for d in dirs if d not in ('cache','.cache','__pycache__'))
        for name in sorted(files):
            path=Path(base)/name
            if name in ('trace','.DS_Store') or name.endswith(('.pyc','.log')):continue
            entries.append((path.relative_to(directory).as_posix(),release.file_hash(path)))
    if not entries:release.fail('RELEASE_ARTIFACT_EMPTY')
    return release.digest(entries)


def test_linear_tree_hash_is_identical_to_canonical_old_order_exclusions_and_digest(tmp_path,monkeypatch):
    for relative,content in [('z/root.bin',b'\x00first'),('a/deep/one.txt',b'one'),('a/deep/two.txt',b'two'),
            ('a/trace',b'ignore'),('a/cache/ignored.bin',b'ignore'),('.cache/x',b'ignore'),
            ('__pycache__/x.pyc',b'ignore'),('z/debug.log',b'ignore'),('z/.DS_Store',b'ignore'),('BUILD_ID',b'fixed')]:
        path=tmp_path/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
    expected=canonical_old_tree_hash(tmp_path)
    original=release.no_links;checks=[]
    monkeypatch.setattr(release,'no_links',lambda value:(checks.append(Path(value)),original(value))[1])
    assert release.tree_hash(tmp_path)==expected
    assert checks==[tmp_path]
    (tmp_path/'a/deep/two.txt').write_bytes(b'changed')
    assert release.tree_hash(tmp_path)!=expected


@pytest.mark.parametrize('relative',['a/deep/link','a/cache'])
def test_linear_hash_rejects_nested_links_even_before_excluding_cache(tmp_path,relative):
    import os,subprocess
    target=tmp_path/'real';target.mkdir();(target/'value').write_text('synthetic',encoding='utf-8')
    link=tmp_path/relative;link.parent.mkdir(parents=True,exist_ok=True)
    if os.name=='nt':
        result=subprocess.run(['cmd.exe','/c','mklink','/J',str(link),str(target)],capture_output=True,text=True)
        assert result.returncode==0,'Owned temporary NTFS junction creation failed'
    else:link.symlink_to(target,target_is_directory=True)
    try:
        with pytest.raises(RuntimeError,match='LINKED_PATH_REJECTED'):release.tree_hash(tmp_path)
        with pytest.raises(RuntimeError,match='LINKED_PATH_REJECTED'):canonical_old_tree_hash(tmp_path)
        with pytest.raises(RuntimeError,match='LINKED_PATH_REJECTED'):release.no_links(release.fs_path(link))
    finally:
        if os.name=='nt':os.rmdir(link)
        else:link.unlink()


@pytest.mark.parametrize('port_free',[True,False])
def test_startup_validation_failure_records_zero_children_cleanup_result(tmp_path,monkeypatch,port_free):
    m=sample(tmp_path);r=record()
    uat.write(tmp_path/'state.json',dict(phase='STARTING',release=r['id']))
    def invalid(*args,**kwargs):raise RuntimeError('RELEASE_SOURCE_HEAD_MISMATCH')
    monkeypatch.setattr(release,'validate_record',invalid)
    monkeypatch.setattr(release.subprocess,'Popen',lambda *a,**k:pytest.fail('validation failure must spawn zero children'))
    checked=[]
    def available(host,port):
        checked.append(port)
        if not port_free and port==m['api_port']:raise OSError('owned test occupied listener')
    monkeypatch.setattr(uat,'available',available)
    with pytest.raises(RuntimeError,match='SOURCE_HEAD_MISMATCH'):release.serve(tmp_path,m,tmp_path,r)
    runtime=json.loads((tmp_path/'release-runtime.json').read_text(encoding='utf-8'))
    assert runtime==dict(release=r['id'],phase='FAILED',cleanup_complete=port_free,children=[])
    assert checked==[m['api_port'],m['web_port'],m['https_port']]
    assert json.loads((tmp_path/'state.json').read_text(encoding='utf-8'))['phase']=='FAILED'


WEB_DIST='.next/datco-e2e-a123456789bc'

def synthetic_web(source):
    web=source/'apps/web';dist=web/WEB_DIST
    (dist/'server').mkdir(parents=True)
    (dist/'BUILD_ID').write_text('SYNTHETIC_BUILD_V3',encoding='utf-8')
    (dist/'server/app.js').write_text('synthetic compiled output',encoding='utf-8')
    (web/'public/roles').mkdir(parents=True)
    (web/'public/roles/index.html').write_text('synthetic public artifact',encoding='utf-8')
    (web/'package.json').write_text('{"name":"synthetic"}',encoding='utf-8')
    (web/'next.config.mjs').write_text('export default {};',encoding='utf-8')
    for relative in release.PORTAL_FILES:
        file=web/relative;file.parent.mkdir(parents=True,exist_ok=True);file.write_text('SYNTHETIC '+relative,encoding='utf-8')
    return web


def artifact_record(source,out):
    from unittest.mock import patch
    with patch.object(release,'portal_source',return_value=dict(head='a'*40,web_tree='b'*40)):
        release.attest_portal_build(source,out,WEB_DIST)
        artifact=release.snapshot_web(source,out,WEB_DIST)
    return dict(schema=release.RECORD_SCHEMA,id='r'+'1'*24,source_root=str(source),head='a'*40,
        dist_dir=WEB_DIST,web_artifact=artifact,build_hash=artifact['manifest_sha256'])


def test_web_execution_cache_changes_cannot_mutate_immutable_artifact_or_next_execution(tmp_path):
    source=tmp_path/'source';out=tmp_path/'owner';synthetic_web(source)
    # A private root env is deliberately present, but never selected/copied.
    (source/'apps/web/.env').write_text('SYNTHETIC_PRIVATE_NOT_FOR_COPY',encoding='utf-8')
    r=artifact_record(source,out);artifact=release.validate_web_artifact(out,r)
    original=release.all_files(artifact)
    one=release.execution_web(out,r);runtime=Path(one['web_root'])
    assert release.all_files(runtime)==original
    assert not (runtime/'.env').exists() and not (runtime/'node_modules').exists()
    assert (runtime/'public/roles/index.html').read_text(encoding='utf-8')=='synthetic public artifact'
    cache=runtime/WEB_DIST/'server/route-cache/APP_PAGE/SYNTHETIC/login.html'
    cache.parent.mkdir(parents=True);cache.write_text('new runtime cache',encoding='utf-8')
    assert release.all_files(runtime)!=original
    assert release.all_files(release.validate_web_artifact(out,r))==original
    two=release.execution_web(out,r)
    assert two['web_root']!=one['web_root'] and not (Path(two['web_root'])/WEB_DIST/'server/route-cache').exists()
    assert two['initial_manifest_sha256']==one['initial_manifest_sha256']==r['build_hash']


def test_route_cache_is_part_of_immutable_artifact_tamper_guard(tmp_path):
    source=tmp_path/'source';out=tmp_path/'owner';web=synthetic_web(source)
    route=web/WEB_DIST/'server/route-cache/APP_PAGE/build/login.rsc'
    route.parent.mkdir(parents=True);route.write_text('initial source route cache',encoding='utf-8')
    r=artifact_record(source,out);artifact=release.validate_web_artifact(out,r)
    assert any('route-cache/' in entry['path'] for entry in r['web_artifact']['files'])
    (artifact/route.relative_to(web)).write_text('tampered immutable route cache',encoding='utf-8')
    with pytest.raises(RuntimeError,match='IMMUTABLE_ARTIFACT_CHANGED'):release.validate_web_artifact(out,r)


def test_private_env_inside_selected_public_tree_is_rejected_before_snapshot_copy(tmp_path):
    source=tmp_path/'source';web=synthetic_web(source)
    (web/'public/.env.local').write_text('SYNTHETIC_ONLY',encoding='utf-8')
    release.attest_portal_build(source,tmp_path/'owner',WEB_DIST)
    with pytest.raises(RuntimeError,match='SNAPSHOT_FORBIDDEN_FILE'):release.snapshot_web(source,tmp_path/'owner',WEB_DIST)


def test_v2_records_are_valid_anchor_material_but_cannot_be_loaded_for_execution(tmp_path):
    r=record();r['schema']=release.ANCHOR_SCHEMA
    r.pop('id');r=dict(r,id='r'+release.digest(r)[:24])
    release.immutable(tmp_path/'releases'/(r['id']+'.json'),r)
    assert release.load_record(tmp_path,r['id'],anchor_only=True)==r
    with pytest.raises(RuntimeError,match='SCHEMA_UNSUPPORTED'):release.load_record(tmp_path,r['id'])
    with pytest.raises(RuntimeError,match='SCHEMA_UNSUPPORTED'):release.validate_record(tmp_path,sample(tmp_path),tmp_path,r)


def setup_recover(tmp_path,monkeypatch):
    m=sample(tmp_path);old=record();old.update(schema=release.ANCHOR_SCHEMA,source_root=str(tmp_path),head=m['head'])
    new=record(identifier='r'+'2'*24);new.update(source_root=str(tmp_path),head=m['head'],web_artifact={'fresh_build':True})
    selected=dict(current=old['id'],previous=None);seen=[]
    monkeypatch.setattr(release,'state',lambda *a:dict(nonce=m['nonce'],phase='STOPPED',head=m['head']))
    uat.write(tmp_path/'release-runtime.json',dict(phase='STOPPED',cleanup_complete=True,children=[]))
    monkeypatch.setattr(release,'enrollment',lambda *a:dict(owner=old['owner'],initial_release=old['id']))
    monkeypatch.setattr(release,'selection',lambda *a:selected)
    monkeypatch.setattr(release,'owner_identity',lambda *a:old['owner'])
    monkeypatch.setattr(release,'load_record',lambda out,key,**kwargs:{old['id']:old,new['id']:new}[key])
    monkeypatch.setattr(release,'alive',lambda *a:False)
    monkeypatch.setattr(uat,'available',lambda host,port:seen.append('port:'+str(port)))
    monkeypatch.setattr(release,'ensure_database_running',lambda *a:seen.append('owned-db-start'))
    monkeypatch.setattr(release,'validate_record',lambda owner,m,out,r,**kwargs:seen.append('validate:'+r['id']))
    return m,old,new,selected,seen


def test_explicit_recover_preserves_old_bytes_and_selects_only_new_immutable_baseline(tmp_path,monkeypatch):
    m,old,new,selected,seen=setup_recover(tmp_path,monkeypatch)
    oldfile=tmp_path/'releases'/(old['id']+'.json');release.immutable(oldfile,old);before=oldfile.read_bytes()
    release.recover(tmp_path,m,tmp_path,new['id'],m['nonce'])
    assert oldfile.read_bytes()==before
    choice=json.loads((tmp_path/'release-selection.json').read_text(encoding='utf-8'))
    assert choice==dict(current=new['id'],previous=None,unusable_previous=old['id'])
    event=json.loads(next((tmp_path/'release-events').glob('*.json')).read_text(encoding='utf-8'))
    assert event['previous_selection']==selected and event['unusable_previous']==old['id']
    assert seen[-2:]==['owned-db-start','validate:'+new['id']]


@pytest.mark.parametrize('problem',['running','cleanup','live_child','owner_identity','head','schema','fresh_build'])
def test_recover_requires_stopped_clean_exact_compatible_new_baseline_before_database_action(tmp_path,monkeypatch,problem):
    m,old,new,selected,seen=setup_recover(tmp_path,monkeypatch)
    if problem=='running':monkeypatch.setattr(release,'state',lambda *a:dict(nonce=m['nonce'],phase='RUNNING'))
    if problem=='cleanup':uat.write(tmp_path/'release-runtime.json',dict(phase='FAILED',cleanup_complete=False,children=[]))
    if problem=='live_child':
        uat.write(tmp_path/'release-runtime.json',dict(phase='STOPPED',cleanup_complete=True,children=[123]))
        monkeypatch.setattr(release,'alive',lambda *a:True)
    if problem=='owner_identity':monkeypatch.setattr(release,'owner_identity',lambda *a:{'different':'owner'})
    if problem=='head':new['head']='b'*40
    if problem=='schema':new['database']={'changed':'schema'}
    if problem=='fresh_build':new['web_artifact']['fresh_build']=False
    with pytest.raises(RuntimeError):release.recover(tmp_path,m,tmp_path,new['id'],m['nonce'])
    assert 'owned-db-start' not in seen
    assert not (tmp_path/'release-selection.json').exists()


def test_copy_manifest_rejects_parent_escape_and_windows_drive_relative_path(tmp_path):
    import os
    source=tmp_path/'source';source.mkdir();(source/'payload').write_text('synthetic',encoding='utf-8')
    entry=dict(size=9,sha256='a'*64)
    paths=['../payload','/absolute/payload']
    if os.name=='nt':paths.append('D:payload')
    for i,unsafe in enumerate(paths):
        with pytest.raises(RuntimeError,match='MANIFEST_PATH_INVALID'):
            release.copy_entries(source,tmp_path/('dest'+str(i)),[dict(entry,path=unsafe)])


def test_artifact_sidecar_is_checked_by_link_guard_before_read(tmp_path,monkeypatch):
    source=tmp_path/'source';out=tmp_path/'owner';synthetic_web(source)
    r=artifact_record(source,out);guard=release.no_links;checked=[]
    def reject_sidecar(path):
        checked.append(Path(path))
        if Path(path).name=='artifact.json':raise RuntimeError('RELEASE_LINKED_PATH_REJECTED')
        return guard(path)
    monkeypatch.setattr(release,'no_links',reject_sidecar)
    with pytest.raises(RuntimeError,match='LINKED_PATH_REJECTED'):release.validate_web_artifact(out,r)
    assert checked[-1].name=='artifact.json'


def test_same_head_running_build_must_match_the_selected_exact_release_before_stop(tmp_path,monkeypatch):
    m,old,new,seen=setup_switch(tmp_path,monkeypatch)
    monkeypatch.setattr(release,'state',lambda *a:dict(nonce=m['nonce'],phase='RUNNING',head=old['head'],release='r'+'f'*24))
    monkeypatch.setattr(release,'launch',lambda *a,**k:pytest.fail('must not launch from mismatched exact build identity'))
    with pytest.raises(RuntimeError,match='RUNNING_IDENTITY_MISMATCH'):
        release.switch(tmp_path,m,tmp_path,new['id'],m['nonce'])
    assert 'stopped' not in seen


def test_actual_long_path_copy_manifest_and_runtime_identity_keep_normal_paths(tmp_path):
    import os,shutil
    from hashlib import sha256
    sandbox=tmp_path/'owned-long-path-case';sandbox.mkdir()
    source=sandbox/'source'
    try:
        web=synthetic_web(source)
        relative=WEB_DIST+'/server/app/'+('/'.join('level-'+str(i)+'-'+'x'*42 for i in range(5)))+'/__PAGE__.segment.rsc'
        deep=web/relative
        assert len(str(deep))>260
        release.fs_path(deep.parent).mkdir(parents=True)
        payload=b'SYNTHETIC_LONG_PATH_MANIFEST_ONLY'
        release.fs_path(deep).write_bytes(payload)
        entry=next(item for item in release.all_files(web) if item['path']==relative)
        assert entry==dict(path=relative,size=len(payload),sha256=sha256(payload).hexdigest())
        assert release.all_files(release.fs_path(web))==release.all_files(web)
        # The artifact/metadata root itself is also longer than MAX_PATH.
        out=sandbox/('owner-'+'a'*64)/('data-'+'b'*64)/('retained-'+'c'*64)
        assert len(str(out))>260
        r=artifact_record(source,out)
        artifact=release.validate_web_artifact(out,r)
        assert release.file_hash(artifact/relative)==sha256(payload).hexdigest()
        execution=release.execution_web(out,r)
        runtime=Path(execution['web_root'])
        assert release.all_files(runtime)==r['web_artifact']['files']
        assert release.normal_path(release.fs_path(runtime))==runtime
        assert not str(runtime).startswith(chr(92)*2+'?'+chr(92))
        assert all(not item['path'].startswith(chr(92)*2+'?'+chr(92)) for item in r['web_artifact']['files'])
        saved=json.loads(release.fs_path(runtime.parent/'execution.json').read_text(encoding='utf-8'))
        assert saved==execution and Path(saved['source_root'])==source
        if os.name=='nt':assert str(release.fs_path(runtime)).startswith(chr(92)*2+'?'+chr(92))
        else:assert release.fs_path(runtime)==runtime
    finally:
        # Remove only this test's exact owned temporary tree, using one OS
        # namespace end to end. No workspace/runtime/source data is targeted.
        resolved=release.no_links(sandbox)
        assert resolved.parent==tmp_path.resolve() and resolved.name=='owned-long-path-case'
        shutil.rmtree(release.fs_path(resolved))


def test_windows_namespace_conversion_preserves_unc_and_local_logical_identity(tmp_path):
    import os
    local=tmp_path/'synthetic-file'
    assert release.normal_path(release.fs_path(local))==local.absolute()
    if os.name=='nt':
        unc=Path(chr(92)*2+'synthetic-server'+chr(92)+'synthetic-share'+chr(92)+'nested')
        physical=release.fs_path(unc)
        assert str(physical).startswith(chr(92)*2+'?'+chr(92)+'UNC'+chr(92))
        assert release.normal_path(physical)==unc
    else:assert release.fs_path(local)==local.absolute()


def test_owned_build_uses_fixed_memory_cap_and_restores_tracked_next_env_on_failure(tmp_path,monkeypatch):
    import subprocess
    source=tmp_path/'source';web=source/'apps/web';web.mkdir(parents=True)
    tracked=web/'next-env.d.ts';original=b'SYNTHETIC_EXACT_ORIGINAL\r\n';tracked.write_bytes(original)
    out=tmp_path/'owned-output';out.mkdir()
    monkeypatch.setattr(release,'git',lambda *a:'a'*40)
    monkeypatch.setattr(release,'release_environment',lambda *a:{'NODE_OPTIONS':'--inspect=SYNTHETIC_UNTRUSTED_FLAG','SAFE_MARKER':'retained'})
    observed=[]
    def failed_build(command,**kwargs):
        observed.append(kwargs['env'].copy())
        tracked.write_bytes(b'SYNTHETIC_BUILD_SIDE_EFFECT')
        raise subprocess.CalledProcessError(1,command)
    monkeypatch.setattr(release.subprocess,'run',failed_build)
    with pytest.raises(subprocess.CalledProcessError):release.build(source,sample(tmp_path),out,WEB_DIST)
    assert observed==[{'NODE_OPTIONS':'--max-old-space-size=2048','SAFE_MARKER':'retained'}]
    assert tracked.read_bytes()==original


@pytest.fixture(autouse=True)
def synthetic_portal_identity(monkeypatch):
    monkeypatch.setattr(release,'portal_source',lambda source:dict(head='a'*40,web_tree='b'*40))


@pytest.mark.parametrize('relative',release.PORTAL_FILES)
def test_missing_portal_fails_before_immutable_artifact_creation(tmp_path,relative):
    source=tmp_path/'source';out=tmp_path/'owner';web=synthetic_web(source)
    release.attest_portal_build(source,out,WEB_DIST)
    (web/relative).unlink()
    with pytest.raises(RuntimeError,match='RELEASE_REQUIRED_PORTAL_FILE_MISSING'):release.snapshot_web(source,out,WEB_DIST)
    assert not (out/'release-artifacts').exists()


def test_portal_bytes_and_source_version_are_bound_to_fresh_build(tmp_path):
    source=tmp_path/'source';out=tmp_path/'owner';web=synthetic_web(source)
    release.attest_portal_build(source,out,WEB_DIST)
    (web/release.PORTAL_FILES[0]).write_text('WRONG_ROLE_OR_BUILD',encoding='utf-8')
    with pytest.raises(RuntimeError,match='RELEASE_PORTAL_ROLE_OR_BYTES_MISMATCH'):release.snapshot_web(source,out,WEB_DIST)
    assert not (out/'release-artifacts').exists()


def test_incomplete_old_artifact_is_refused_even_with_consistent_manifest(tmp_path):
    source=tmp_path/'source';out=tmp_path/'owner';synthetic_web(source);r=artifact_record(source,out)
    r['web_artifact'].pop('portal_contract')
    with pytest.raises(RuntimeError,match='RELEASE_REQUIRED_PORTAL_CONTRACT_MISSING'):release.validate_web_artifact(out,r)


def test_execution_copy_cannot_start_if_a_required_portal_is_missing(tmp_path,monkeypatch):
    source=tmp_path/'source';out=tmp_path/'owner';synthetic_web(source);r=artifact_record(source,out)
    original=release.copy_entries
    def damaged_copy(source,destination,entries):
        original(source,destination,entries)
        (destination/release.PORTAL_FILES[2]).unlink()
    monkeypatch.setattr(release,'copy_entries',damaged_copy)
    with pytest.raises(RuntimeError,match='RELEASE_REQUIRED_PORTAL_FILE_MISSING'):release.execution_web(out,r)
    assert not list((out/'executions').rglob('execution.json'))


def test_portal_contract_rejects_cross_version_and_cross_role(tmp_path):
    source=tmp_path/'source';out=tmp_path/'owner';web=synthetic_web(source);r=artifact_record(source,out)
    c=r['web_artifact']['portal_contract']
    with pytest.raises(RuntimeError,match='RELEASE_PORTAL_VERSION_MISMATCH'):release.validate_portals(web,c,'c'*40,c['build_id'])
    a,b=[web/x for x in release.PORTAL_FILES[::2]][:2]
    a.write_bytes(b.read_bytes())
    with pytest.raises(RuntimeError,match='RELEASE_PORTAL_ROLE_OR_BYTES_MISMATCH'):release.validate_portals(web,c,r['head'],c['build_id'])


def test_stale_role_bundles_are_never_attested_as_a_new_build(tmp_path,monkeypatch):
    source=tmp_path/'source';web=source/'apps/web';web.mkdir(parents=True)
    (web/'next-env.d.ts').write_text('SYNTHETIC',encoding='utf-8')
    stale=web/'.role-portals/company/portal.js';stale.parent.mkdir(parents=True);stale.write_text('ANOTHER_COMMIT',encoding='utf-8')
    monkeypatch.setattr(release.subprocess,'run',lambda *a,**k:pytest.fail('stale bundle reached npm build'))
    with pytest.raises(RuntimeError,match='RELEASE_FRESH_PORTAL_OUTPUT_REQUIRED'):release.build(source,sample(tmp_path),tmp_path/'out',WEB_DIST)
    assert stale.read_text(encoding='utf-8')=='ANOTHER_COMMIT'
