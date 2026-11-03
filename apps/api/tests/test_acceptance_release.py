"""Release guards and recovery order, without Docker/DB/HTTP/services/credentials."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest
import acceptance_release as release
import manual_acceptance as uat


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
    value=dict(owner={'identity':'SYNTHETIC'},head=head,source_root='SYNTHETIC_SOURCE',
        source_contract=dict(locks={'lock':'fixed'},schema_code='fixed',release_owner_guard=1),database=dict(alembic=['v1'],schema='fixed'))
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
    body=dict(head='a'*40,build_hash='synthetic-build')
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
    monkeypatch.setattr(release,'state',lambda *a:dict(nonce=m['nonce'],phase='RUNNING',head=old['head']))
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
    with pytest.raises(RuntimeError,match='TARGET_BUILD_REQUIRED'):
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
