"""Focused handover guards; no existing environment access."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime,timedelta,timezone
import pytest
import acceptance_handover as handover
from acceptance_handover_projection import project_manifest,ProjectionRejected
from acceptance_handover_fence import FileFence,process_identity


def manifest():
    return dict(nonce='abc123abc123',head=handover.LEGACY,root='C:/SYNTHETIC',host='127.0.0.1',https_port=19452,api_port=59451,web_port=59452,pg_port=59453,origin='https://127.0.0.1:19452',db='datco_test_abc123abc123',role='datco_test_role_abc123abc123',container='datco-mvp-uat-abc123abc123',volume='datco-mvp-uat-pg-abc123abc123',caddy='C:/SYNTHETIC/caddy.exe',preparation=True)


def test_projection_discards_unknown_nested_values_and_hashes_original_bytes(tmp_path):
    value=manifest();value.update(url='SYNTHETIC_SECRET_NOT_FOR_PROJECTION',admin_password='SYNTHETIC_ADMIN_NOT_FOR_PROJECTION',unknown={'nested':['SYNTHETIC_NESTED_NOT_FOR_PROJECTION',123.4e5]})
    content=json.dumps(value,ensure_ascii=False).encode();path=tmp_path/'manifest.json';path.write_bytes(content)
    projected,digest=project_manifest(path)
    assert projected==manifest() and digest==hashlib.sha256(content).hexdigest()
    assert 'SECRET' not in json.dumps(projected) and 'url' not in projected


@pytest.mark.parametrize('suffix',[',"nonce":"abc123abc123"',',"\\u006eonce":"abc123abc123"',',"unknown":{"x":1,"x":2}',',"unknown":[NaN]',',"unknown":"\\ud800"',',"unknown":00',',"unknown":[1,]'])
def test_projection_rejects_malformed_or_duplicate_keys_without_secret_echo(tmp_path,suffix):
    path=tmp_path/'manifest.json';path.write_text(json.dumps(manifest())[:-1]+suffix+'}',encoding='utf-8')
    with pytest.raises(ProjectionRejected,match='^MANIFEST_PROJECTION_REJECTED$'):project_manifest(path)


@pytest.mark.parametrize('key,value',[('api_port',True),('api_port',1234.5),('api_port',123),('root',None),('preparation',1),('head','bad'),('origin','https://foreign.invalid')])
def test_projection_known_fields_are_strict(tmp_path,key,value):
    m=manifest();m[key]=value;path=tmp_path/'manifest.json';path.write_text(json.dumps(m),encoding='utf-8')
    with pytest.raises(ProjectionRejected):project_manifest(path)


def test_projection_bounds_and_unicode(tmp_path):
    m=manifest();m['root']='C:/SYNTHETIC/한글';path=tmp_path/'manifest.json';path.write_bytes(b'\xef\xbb\xbf'+json.dumps(m,ensure_ascii=False).encode())
    assert project_manifest(path)[0]==m
    m['unknown']='x'*65536;path.write_text(json.dumps(m),encoding='utf-8')
    with pytest.raises(ProjectionRejected):project_manifest(path)


def test_exclusive_fence_blocks_legacy_entrypoint_without_edit(tmp_path):
    script=tmp_path/'legacy.py';marker=tmp_path/'started';script.write_text("from pathlib import Path\nPath('started').write_text('SYNTHETIC')\n",encoding='utf-8');before=script.read_bytes()
    with FileFence(script,exclusive=True) as fence:
        assert fence.sha256()==hashlib.sha256(before).hexdigest()
        r=subprocess.run([sys.executable,'-B',str(script)],cwd=tmp_path,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
        assert r.returncode!=0 and not marker.exists()
    assert script.read_bytes()==before
    r=subprocess.run([sys.executable,'-B',str(script)],cwd=tmp_path,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
    assert r.returncode==0 and marker.read_text()=='SYNTHETIC'


def test_stopped_state_fence_allows_read_and_refuses_replacement(tmp_path):
    state=tmp_path/'state.json';other=tmp_path/'state.tmp';state.write_bytes(b'{"phase":"STOPPED"}');other.write_bytes(b'{"phase":"STARTING"}');before=state.read_bytes()
    with FileFence(state,exclusive=False) as fence:
        assert state.read_bytes()==before
        with pytest.raises(PermissionError):other.replace(state)
        assert fence.sha256()==hashlib.sha256(before).hexdigest()
    assert state.read_bytes()==before


def test_identity_is_read_only_and_has_no_command_or_environment():
    identity=process_identity(os.getpid())
    assert identity['pid']==os.getpid() and int(identity['created'])>0
    assert Path(identity['cwd']).resolve()==Path.cwd().resolve()
    assert set(identity)=={'pid','created','exe','cwd','parent'}


def approval_pair():
    now=datetime.now(timezone.utc);m=manifest();plan={'id':'a'*64,'owner':{'manifest':m}}
    approval=dict(decision='APPROVED',plan_sha256=plan['id'],nonce=m['nonce'],origin=m['origin'],product_head=handover.PRODUCT,recovery_head=handover.PRODUCT,actions=['activate','recover','stop'],not_before=(now-timedelta(minutes=1)).isoformat(),expires=(now+timedelta(minutes=10)).isoformat(),decided_by='SYNTHETIC_TEST_ONLY',decision_reference='fixture test decision',real_data_approved=False)
    return plan,approval,now


@pytest.mark.parametrize('problem',['pending','digest','nonce','origin','product','recovery','expired','action','real_data'])
def test_missing_or_wrong_approval_refused(problem):
    p,a,now=approval_pair()
    if problem=='pending':a['decision']='PENDING_USER_DECISION'
    if problem=='digest':a['plan_sha256']='b'*64
    if problem=='nonce':a['nonce']='def456def456'
    if problem=='origin':a['origin']='https://127.0.0.1:18445'
    if problem=='product':a['product_head']=handover.LEGACY
    if problem=='recovery':a['recovery_head']=handover.LEGACY
    if problem=='expired':a['expires']=(now-timedelta(seconds=1)).isoformat()
    if problem=='action':a['actions']=['stop']
    if problem=='real_data':a['real_data_approved']=True
    with pytest.raises(RuntimeError):handover.validate_approval(p,a,'activate',now)


def test_exact_bounded_approval_and_protected_set_are_preserved():
    p,a,now=approval_pair();handover.validate_approval(p,a,'activate',now)
    assert handover.release.PROTECTED=={8443,8444,18445,49355,49356}

def test_listener_projection_handles_windows_powershell_array_output():
    import socket
    from acceptance_handover_fence import listener_owners
    with socket.socket() as one,socket.socket() as two:
        one.bind(('127.0.0.1',0));two.bind(('127.0.0.1',0));one.listen();two.listen()
        a,b=one.getsockname()[1],two.getsockname()[1]
        rows=listener_owners([a,b])
        assert rows[a]==[dict(address='127.0.0.1',pid=os.getpid())]
        assert rows[b]==[dict(address='127.0.0.1',pid=os.getpid())]
        assert listener_owners([a])[a]==rows[a]

def test_owned_job_terminates_only_own_child(tmp_path):
    from acceptance_handover_job import OwnedJob
    from acceptance_release import alive
    with OwnedJob() as job:
        p=job.spawn([sys.executable,'-c','import time;time.sleep(60)'],tmp_path,os.environ.copy())
        assert p.poll() is None
        pid=p.pid
    assert not alive(pid)
    assert alive(os.getpid())


def test_job_hard_custodian_exit_kills_descendants(tmp_path):
    from acceptance_release import alive
    import time
    script=tmp_path/'custodian.py';report=tmp_path/'pid'
    script.write_text("import os,sys,time\nfrom acceptance_handover_job import OwnedJob\nfrom pathlib import Path\nj=OwnedJob()\np=j.spawn([sys.executable,'-c','import time;time.sleep(60)'],Path.cwd(),os.environ.copy())\nPath(sys.argv[1]).write_text(str(p.pid))\nos._exit(17)\n",encoding='utf-8')
    env=os.environ.copy();env['PYTHONPATH']=str(Path(handover.__file__).parent)
    p=subprocess.run([sys.executable,'-B',str(script),str(report)],cwd=tmp_path,env=env,capture_output=True)
    assert p.returncode==17
    pid=int(report.read_text());until=time.monotonic()+10
    while alive(pid) and time.monotonic()<until:time.sleep(.05)
    assert not alive(pid)


def test_approval_gate_precedes_control_or_owner_access(tmp_path,monkeypatch):
    p,a,_=approval_pair();a['decision']='PENDING_USER_DECISION'
    monkeypatch.setattr(handover,'load_plan',lambda _:p)
    monkeypatch.setattr(handover,'read_json',lambda _:a)
    def forbidden(*_,**__):pytest.fail('Owner/control must not be accessed before approval')
    monkeypatch.setattr(handover,'validate_control',forbidden)
    monkeypatch.setattr(handover,'static_owner',forbidden)
    with pytest.raises(RuntimeError,match='SEPARATE_APPLY_DECISION'):handover.run_owner(tmp_path/'plan.json',tmp_path/'approval.json')

def test_failed_cleanup_is_sticky_and_cannot_become_success(tmp_path,monkeypatch):
    from acceptance_handover_job import OwnedJob,Child
    job=OwnedJob();job.spawn([sys.executable,'-c','import time;time.sleep(60)'],tmp_path,os.environ.copy())
    def failed_wait(*_,**__):raise RuntimeError('HANDOVER_OWN_CHILD_EXIT_UNCONFIRMED')
    monkeypatch.setattr(Child,'wait',failed_wait)
    with pytest.raises(RuntimeError,match='EXIT_UNCONFIRMED'):job.close()
    assert not job.cleanup_confirmed and job.cleanup_error
    with pytest.raises(RuntimeError,match='CLEANUP_UNCONFIRMED'):job.close()