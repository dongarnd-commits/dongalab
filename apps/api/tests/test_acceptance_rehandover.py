"""Focused current04 handoff guards; no live service or database access."""
from copy import deepcopy
from pathlib import Path
from datetime import datetime,timezone,timedelta
import pytest
import acceptance_handover as h
import acceptance_rehandover as rh


def approved(plan):
    now=datetime.now(timezone.utc)
    return dict(decision='APPROVED',plan_sha256=plan['id'],nonce='abc123456789',origin='https://127.0.0.1:19459',product_head=h.PRODUCT,recovery_head=h.RECOVERY,actions=['replace','recover','stop'],not_before=(now-timedelta(minutes=1)).isoformat(),expires=(now+timedelta(minutes=5)).isoformat(),decided_by='SYNTHETIC_ONLY',decision_reference='NEW_EXACT_PLAN_ONLY',real_data_approved=False)


def simple_plan():return dict(id='a'*64,owner=dict(manifest=dict(nonce='abc123456789',origin='https://127.0.0.1:19459')))


def test_previous_approval_cannot_authorize_new_artifacts():
    p=simple_plan();a=approved(p);a['plan_sha256']='b'*64
    with pytest.raises(RuntimeError,match='APPROVAL_BINDING_MISMATCH'):h.validate_approval(p,a,'replace')


def test_pending_new_plan_never_reads_owner_or_writes_stop(tmp_path,monkeypatch):
    p=simple_plan();monkeypatch.setattr(h,'load_plan',lambda _:p);monkeypatch.setattr(h,'read_json',lambda _:dict(decision='PENDING_USER_DECISION'))
    monkeypatch.setattr(h,'validate_control',lambda _:pytest.fail('pending plan reached control/owner access'))
    with pytest.raises(RuntimeError,match='SEPARATE_APPLY_DECISION_REQUIRED'):h.run_owner(tmp_path/'plan.json',tmp_path/'pending.json','replace')
    assert list(tmp_path.iterdir())==[]


def test_missing_new_portal_is_rejected_before_current04_stop(tmp_path,monkeypatch):
    p=simple_plan();monkeypatch.setattr(h,'load_plan',lambda _:p);monkeypatch.setattr(h,'read_json',lambda _:approved(p))
    monkeypatch.setattr(h,'validate_control',lambda _:h.release.fail('RELEASE_REQUIRED_PORTAL_FILE_MISSING'))
    monkeypatch.setattr(rh,'stop_predecessor',lambda *a:pytest.fail('incomplete artifact reached predecessor stop'))
    with pytest.raises(RuntimeError,match='RELEASE_REQUIRED_PORTAL_FILE_MISSING'):h.run_owner(tmp_path/'plan.json',tmp_path/'approved.json','replace')
    assert list(tmp_path.iterdir())==[]


@pytest.mark.parametrize('phase',['STOPPED','FAILED','STARTING'])
def test_nonrunning_predecessor_never_becomes_replacement_owner(tmp_path,monkeypatch,phase):
    p=dict(id='a'*64,control_head=rh.PREDECESSOR_CONTROL,control_root=str(tmp_path),code_hashes={})
    monkeypatch.setattr(h,'load_plan',lambda _:p)
    monkeypatch.setattr(h.release,'git',lambda root,*args:'' if args[0]=='status' else rh.PREDECESSOR_CONTROL)
    monkeypatch.setattr(h,'read_json',lambda _:dict(plan='a'*64,phase=phase,head=h.PRODUCT,slot='TARGET'))
    with pytest.raises(RuntimeError,match='RUNNING_04_PREDECESSOR_REQUIRED'):rh.predecessor_state(tmp_path/'plan.json')


def test_changed_current_process_graph_prevents_normal_stop(tmp_path,monkeypatch):
    old=dict(id='b'*64);state=dict(phase='RUNNING')
    p=dict(predecessor=dict(plan_path=str(tmp_path/'old.json'),plan_sha256=old['id'],state=state,processes={'1':dict(pid=1)}))
    monkeypatch.setattr(rh,'predecessor_state',lambda _: (old,state))
    monkeypatch.setattr(rh,'current_graph',lambda *a: {'1':dict(pid=1),'2':dict(pid=2)})
    with pytest.raises(RuntimeError,match='PREDECESSOR_PROCESS_GRAPH_CHANGED'):rh.require_predecessor(p)
