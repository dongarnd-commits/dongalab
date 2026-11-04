"""No runtime access: reject unsafe rollback evidence before any handoff."""
import pytest
import acceptance_pr21_compat as c

RECOVERY = '9b8d0e0f9eb79aaaa2b973f7e3455df78b8a046e'


def evidence():
    def row(head, valid, usable, reasons):
        return dict(head=head, typed_data_roundtrip=True, current_valid=valid,
            analysis_usable=usable, reasons=reasons, database_unchanged=True)
    return dict(
        fresh=[row(c.TARGET,True,True,[]),row(c.PREVIOUS,True,False,['RULE_CHANGED']),
            row(RECOVERY,True,False,['RULE_CHANGED'])],
        stale=[row(c.TARGET,False,False,['COMPANY_INPUT_CHANGED']),
            row(c.PREVIOUS,False,False,['COMPANY_INPUT_CHANGED','RULE_CHANGED']),
            row(RECOVERY,False,False,['COMPANY_INPUT_CHANGED','RULE_CHANGED'])])


@pytest.mark.parametrize('head',[c.PREVIOUS,RECOVERY])
def test_json_roundtrip_does_not_hide_stale_context_acceptance(head):
    proof=evidence()
    next(r for r in proof['stale'] if r['head']==head)['current_valid']=True
    result=c.assess(proof)
    assert result['result']=='BLOCKED'
    assert result['reason']=='PR21_RECOVERY_STALE_BASIS_ACCEPTED'
    assert result['incompatible_recovery_heads']==[head]
    assert result['deployment_ready'] is False


@pytest.mark.parametrize('bad',['missing','wrong_head','duplicate','untyped','mutated','lossy','bad_writer'])
def test_incomplete_or_unsafe_measurements_cannot_authorize_transition(bad):
    proof=evidence()
    if bad=='missing':proof['fresh'].pop()
    elif bad=='wrong_head':proof['stale'][1]['head']='0'*40
    elif bad=='duplicate':proof['stale'][1]['head']=c.TARGET
    elif bad=='untyped':proof['stale'][1]['current_valid']='false'
    elif bad=='mutated':proof['fresh'][1]['database_unchanged']=False
    elif bad=='lossy':proof['stale'][1]['typed_data_roundtrip']=False
    elif bad=='bad_writer':proof['stale'][0]['current_valid']=True
    with pytest.raises(RuntimeError,match='^PR21_'):c.assess(proof)


def test_even_data_compatibility_pass_is_neither_apply_approval_nor_readiness():
    result=c.assess(evidence())
    assert result['result']=='DATA_COMPATIBILITY_PROBE_ONLY'
    assert result['deployment_ready'] is False
    assert result['actual_owner_changed'] is False


def test_actual_owner_is_rejected_before_docker_or_manifest_access(tmp_path,monkeypatch):
    monkeypatch.setattr(c.subprocess,'run',lambda *a,**k:pytest.fail('actual owner reached Docker'))
    with pytest.raises(RuntimeError,match='PR21_SYNTHETIC_CLONE_REQUIRED'):
        c.clone_manifest(tmp_path/'dongalab-dmp-assets')


def test_original_fixed_controller_has_not_been_reconfigured():
    import acceptance_handover as h
    import acceptance_rehandover as rh
    assert (h.PRODUCT,h.RECOVERY)==(c.PREVIOUS,RECOVERY)
    assert rh.PREDECESSOR_CONTROL=='e98ca192fa16e553b6a1ba9c57157fb82815f183'
    assert h.release.PROTECTED==c.PROTECTED


def test_existing_fixture_is_preserved_before_any_new_business_writes(tmp_path,monkeypatch):
    from types import SimpleNamespace
    fixture=tmp_path/'fixture.json';fixture.write_text('TEST original proof')
    monkeypatch.setattr(c,'context',lambda *a:pytest.fail('existing proof reached writer context'))
    with pytest.raises(RuntimeError,match='PR21_EXISTING_PROOF_MUST_BE_PRESERVED'):
        c.writer(SimpleNamespace(out=tmp_path))
    assert fixture.read_text()=='TEST original proof'