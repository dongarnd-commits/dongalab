"""One bounded 04-to-04 artifact handoff from the frozen e98 custodian.

Preparation is read-only on its predecessor. No receipt or request is written
there until a separately approved new plan is executed. The existing STOPPED
legacy state stays read-fenced across the predecessor/new-custodian gap.
"""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
import http.client
import socket
import ssl
import time
import acceptance_handover as h

PREDECESSOR_CONTROL='e98ca192fa16e553b6a1ba9c57157fb82815f183'


def predecessor_state(path):
    p=h.load_plan(path);out=Path(path).resolve().parent
    h.require(p['control_head']==PREDECESSOR_CONTROL,'HANDOVER_EXACT_PREDECESSOR_CONTROL_REQUIRED')
    control=Path(p['control_root'])
    h.require(h.release.git(control,'rev-parse','HEAD')==PREDECESSOR_CONTROL and not h.release.git(control,'status','--porcelain'),'HANDOVER_PREDECESSOR_CONTROL_CHANGED')
    h.require(all(h.release.file_hash(control/'apps/api/tests'/n)==v for n,v in p['code_hashes'].items()),'HANDOVER_PREDECESSOR_CONTROL_CHANGED')
    state=h.read_json(out/'state.json')
    h.require(state.get('plan')==p['id'] and state.get('phase')=='RUNNING' and state.get('slot')=='TARGET' and state.get('head')==h.PRODUCT,'HANDOVER_RUNNING_04_PREDECESSOR_REQUIRED')
    h.require(h.process_matches(state['custodian']),'HANDOVER_PREDECESSOR_CUSTODIAN_CHANGED')
    h.require(not (out/'request.json').exists(),'HANDOVER_PREDECESSOR_PENDING_REQUEST')
    return p,state


def current_graph(p,state):
    graph=h.descendant_identities(state['custodian']['pid'])
    h.require(all(str(v['pid']) in graph and h.process_matches(v) for v in state['children']),'HANDOVER_PREDECESSOR_CHILD_CHANGED')
    allowed={str(Path(p['control_root'])),str(Path(p['product']['source_root'])),str(Path(p['product']['source_root'])/'apps/api'),str(Path(state['web_execution']['web_root']))}
    images={Path(state['custodian']['exe']),*(Path(v['exe']) for v in state['children'])}
    for v in graph.values():
        console=h.trusted_console_host(v)
        h.require(str(Path(v['cwd'])) in allowed or console,'HANDOVER_PREDECESSOR_FOREIGN_CWD')
        h.require(Path(v['exe']) in images or console,'HANDOVER_PREDECESSOR_FOREIGN_IMAGE')
        v['exe_sha256']=h.release.file_hash(Path(v['exe']).resolve())
    return graph


def require_predecessor(plan):
    previous=plan['predecessor'];p,state=predecessor_state(previous['plan_path'])
    h.require(p['id']==previous['plan_sha256'] and state==previous['state'],'HANDOVER_PREDECESSOR_STATE_CHANGED')
    h.require(current_graph(p,state)==previous['processes'],'HANDOVER_PREDECESSOR_PROCESS_GRAPH_CHANGED')
    m=plan['owner']['manifest'];listeners=h.listener_owners([m[k] for k in ('api_port','web_port','https_port')])
    h.require({str(k):v for k,v in listeners.items()}==previous['listeners'],'HANDOVER_PREDECESSOR_LISTENER_CHANGED')
    for rows in listeners.values():
        h.require(bool(rows) and all(v['address']=='127.0.0.1' and str(v['pid']) in previous['processes'] for v in rows),'HANDOVER_PREDECESSOR_FOREIGN_LISTENER')
    h.require(h.release.file_hash(Path(plan['owner']['data_root'])/'state.json')==previous['historical_state_sha256'],'HANDOVER_HISTORICAL_STATE_CHANGED_NO_REWRITE')
    return p,state


def make_replacement_plan(previous_path,product_file,recovery_file,out):
    h.require(h.release.no_links(out).is_relative_to(h.ROOT/'storage/private/runtime'),'HANDOVER_EXTERNAL_PRIVATE_PLAN_PATH_REQUIRED')
    old,state=predecessor_state(previous_path);owner=deepcopy(old['owner'])
    root,data,m,_=h.owner_paths(owner['root'],owner['manifest']['nonce'],owner['kind'])
    # Data/entry hash anchors are inherited from the verified live frozen owner;
    # no historic state or manifest is rewritten to pretend this is legacy RUNNING.
    historical=h.read_json(data/'state.json')
    h.require(historical.get('phase')=='STOPPED' and historical.get('head')==h.LEGACY,'HANDOVER_HISTORICAL_STOPPED_REQUIRED')
    owner['legacy_state']=historical;owner['legacy_state_sha256']=h.release.file_hash(data/'state.json')
    graph=current_graph(old,state);listeners=h.listener_owners([m[k] for k in ('api_port','web_port','https_port')])
    tls=ssl.create_default_context(cafile=str(data/'tls/pki/authorities/local/root.crt'))
    with socket.create_connection(('127.0.0.1',m['https_port']),timeout=5) as raw:
        with tls.wrap_socket(raw,server_hostname='127.0.0.1') as peer:owner['certificate_sha256']=sha256(peer.getpeercert(binary_form=True)).hexdigest()
    predecessor=dict(plan_path=str(Path(previous_path).resolve()),plan_sha256=old['id'],state=state,processes=graph,listeners={str(k):v for k,v in listeners.items()},historical_state_sha256=owner['legacy_state_sha256'])
    records=[h.read_json(product_file),h.read_json(recovery_file)];h.compatible_pair(*records);bound=[]
    for slot,record in zip(('TARGET','RECOVERY'),records):
        h.require(record.get('portable') is True,'HANDOVER_PORTABLE_PRODUCT_ARTIFACT_REQUIRED')
        store=Path(record['artifact_store']);h.validate_product(record,store);artifact=h.release.validate_web_artifact(store,record)
        target=out/record['web_artifact']['relative_root']
        h.release.copy_entries(artifact,target,record['web_artifact']['files']);h.release.immutable(target.parent/'artifact.json',record['web_artifact'])
        value={**record,'id':'r'+h.release.digest(dict(slot=slot,head=record['head'],artifact=record['build_hash']))[:24],'slot':slot};value.pop('artifact_store');h.validate_product(value,out);bound.append(value)
    body=dict(format=h.FORMAT,owner=owner,product=bound[0],recovery=bound[1],predecessor=predecessor,control_root=str(h.ROOT),control_head=h.release.git(h.ROOT,'rev-parse','HEAD'),code_hashes={n:h.release.file_hash(h.TOOL.parent/n) for n in h.CONTROL_FILES},legacy_semantics='historical STOPPED725 read-fenced continuously; stop current e98 04 custodian normally',recovery_semantics='verified complete previous9b on the same current DB/files; never725 or DB restore',real_data_approved=False)
    plan=dict(body,id=h.release.digest(body));plan['_out']=str(out)
    h.static_owner(plan);h.public_identity(plan,h.PRODUCT);require_predecessor(plan)
    plan.pop('_out');h.release.immutable(out/'plan.json',plan)
    template=dict(decision='PENDING_USER_DECISION',plan_sha256=plan['id'],nonce=m['nonce'],origin=m['origin'],product_head=h.PRODUCT,recovery_head=h.RECOVERY,actions=['replace','recover','stop'],not_before=None,expires=None,decided_by=None,decision_reference=None,real_data_approved=False)
    h.release.immutable(out/'approval-template.json',template)
    return plan


def stop_predecessor(plan,approval,stack):
    h.validate_approval(plan,approval,'replace');require_predecessor(plan)
    out=Path(plan['_out']);data=Path(plan['owner']['data_root']);m=plan['owner']['manifest'];previous=plan['predecessor']
    # Existing read-sharing fence is compatible with e98's read-sharing fence.
    # It remains held while e98 releases its entry fence and the new owner takes it.
    historical=stack.enter_context(h.FileFence(data/'state.json',exclusive=False))
    h.require(historical.sha256()==previous['historical_state_sha256'],'HANDOVER_HISTORICAL_STATE_CHANGED_NO_REWRITE')
    require_predecessor(plan);h.public_identity(plan,h.PRODUCT);h.require_quiet(h.technical_database(m))
    fresh={**approval,'plan_sha256':previous['plan_sha256'],'actions':['stop'],'decision_reference':approval['decision_reference']+'; new replacement plan '+plan['id']+' explicitly authorizes predecessor normal STOP'}
    receipt=out/'predecessor-stop-approval.json';h.release.immutable(receipt,fresh)
    h.request_action(Path(previous['plan_path']),receipt,'stop')
    until=time.monotonic()+70
    while time.monotonic()<until:
        state=h.read_json(Path(previous['plan_path']).parent/'state.json')
        if state.get('phase')=='STOPPED' and state.get('cleanup_complete') is True and not any(h.release.alive(v['pid']) for v in previous['processes'].values()):break
        time.sleep(.2)
    else:h.require(False,'HANDOVER_PREDECESSOR_NORMAL_STOP_UNCONFIRMED_NO_KILL')
    h.require(state.get('plan')==previous['plan_sha256'] and state.get('head')==h.PRODUCT,'HANDOVER_PREDECESSOR_FINAL_IDENTITY_CHANGED')
    h.ports_free(m);h.require_quiet(h.technical_database(m))
    entry=stack.enter_context(h.FileFence(Path(plan['owner']['root'])/'apps/api/tests/manual_acceptance.py',exclusive=True))
    h.require(entry.sha256()==plan['owner']['entrypoint_sha256'],'HANDOVER_ENTRYPOINT_CHANGED')
    h.event(out,'CURRENT_04_NORMAL_HANDOFF',predecessor_plan=previous['plan_sha256'],historical_state_sha256=historical.sha256())
    return entry,historical.sha256()
