from copy import deepcopy
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from fastapi.testclient import TestClient
from test_notice_slice import context,prepare,detail,confirm
from app.core.config import ROOT
from app.infrastructure import capability_schema as S
from app.infrastructure.notice_store import SqlNoticeStore
from app.infrastructure.local_auth import hash_password
from app.infrastructure.database import get_session
from app.capability.application import CapabilityApplication,terms
from app.notice.domain import Actor,Denied
from app.worker import process_one
from app.main import app
import app.api.capability as api

pytestmark=pytest.mark.integration
SOURCE=ROOT/'_local_inputs/dmp_features_649.json'

class TestInputs:
    __test__=False
    def __init__(self,actor_id): self.actor_id=actor_id
    def read(self,actor,version_id):
        if actor.id!=self.actor_id or version_id!='TEST_IMPROVEMENT_A': raise Denied('OBJECT_NOT_FOUND',404)
        return {'company_id':'TEST_COMPANY_A','site_id':'TEST_SITE_A','improvement_version_id':version_id,
          'original_text':'재고가 맞지 않고 입출고를 수기로 관리합니다.', 'confirmed':True,'current_valid':True,
          'fact_version_ids':[],'evidence_refs':[],'demo':True}

@pytest.fixture
def setup(context):
    if not SOURCE.exists(): pytest.skip('Actual DMP source missing')
    factory,files,operator=context
    with factory.begin() as session:
        store=SqlNoticeStore(session); record=store.add('actors',username='TEST_ADMIN_'+uuid4().hex,role='DATCO_ADMIN',password_hash=hash_password('test-only-password'))
        admin=Actor(record['id'],record['role']); CapabilityApplication(session,files).import_inventory(SOURCE.read_bytes(),admin)
    return factory,files,operator,admin

def capability(service,admin):
    page=service.inventory(admin,'재고현황'); feature=next(f for f in page['items'] if f['data']['feature_id']=='DMP-D89936F06CA33048')
    data={'service':'TEST 재고 업무 개선','description':'SYNTHETIC TEST: verified feature reference',
      'functions':[{'revision_id':feature['id'],'role':feature['data']['description'] or feature['data']['name']}],
      'problems':['재고 관리'],'conditions':['기업 데이터 검토 필요'],'exclusions':[],
      'prerequisites':['품목정보'],'scope':'재고 정보 관리','evidence_note':'TEST source feature reviewed'}
    root=service.save_capability(admin,data,str(uuid4())); version=service.publish(admin,root['id'],1,str(uuid4()))
    return data,root,version

def composition_data(version):
    return {'name':'TEST 재고 조합','improvement_version_id':'TEST_IMPROVEMENT_A',
      'capability_version_ids':[version['id']], 'excluded_feature_revision_ids':[],
      'coverage':[{'requirement':'TEST 재고 업무','capability_version_id':version['id'],'feature_revision_ids':[], 'role':'도입조건 확인','addressed_scope':'','unaddressed_scope':'해결범위 검토 필요','missing_information':['기초자료']}], 'conditions':['원천 자료 검토 필요'],'unresolved':['자동 원인분석은 제공범위 미확인']}

def test_actual_inventory_counts_reimport_search_and_filter(setup):
    factory,files,operator,admin=setup
    with factory.begin() as session:
        service=CapabilityApplication(session,files)
        before=session.scalar(select(func.count()).select_from(S.revisions))
        result=service.import_inventory(SOURCE.read_bytes(),admin); assert result['replay']
        assert session.scalar(select(func.count()).select_from(S.revisions))==before==649
        page=service.inventory(operator); assert page['total']==649 and len(page['systems'])==10
        data=session.execute(select(S.revisions.c.data)).scalars().all()
        assert len({(d['system'],d['feature_group']) for d in data})==88
        assert len({d['feature_group'] for d in data})==81
        for q in ('재고현황','입출고','재고 수량'):
            assert service.inventory(operator,q)['total']>0
        assert service.inventory(operator,'UNRELATED_TEST_NO_MATCH')['total']==0
        assert service.inventory(operator,'?!#$')['total']==0
        filtered=service.inventory(operator,system='ERP-물류',group='재고관리')
        assert all(f['data']['system']=='ERP-물류' and f['data']['feature_group']=='재고관리' for f in filtered['items'])
        assert service.inventory(operator,page=2)['items'][0]['id']!=page['items'][0]['id']
        assert service.feature(operator,'DMP-D89936F06CA33048')['revisions'][0]['data']['name']=='재고현황'

def test_capability_permissions_versions_and_idempotency(setup):
    factory,files,operator,admin=setup
    with factory.begin() as session:
        service=CapabilityApplication(session,files); data,root,version=capability(service,admin)
        assert service.catalog(operator,'입출고')==[] or service.catalog(operator,'재고')
        assert 'draft' not in service.capability(operator,root['id'])['root']
        assert service.catalog(operator,'?!#$')==[]
        with pytest.raises(Denied,match='ACTION_NOT_AUTHORIZED'): service.publish(operator,root['id'],1,'denied')
        changed=deepcopy(data); changed['scope']='새 TEST 범위'
        saved=service.save_capability(admin,changed,'save-v2',root['id'],1)
        assert service.save_capability(admin,changed,'save-v2',root['id'],1)==saved
        with pytest.raises(Denied,match='IDEMPOTENCY_TARGET_MISMATCH'): service.save_capability(admin,data,'save-v2',root['id'],1)
        with pytest.raises(Denied,match='STALE_INPUT_VERSION'): service.save_capability(admin,data,'stale',root['id'],1)
        second=service.publish(admin,root['id'],2,'publish-v2')
        assert service.publish(admin,root['id'],2,'publish-v2')==second
        history=service.capability(admin,root['id'])['versions']
        assert len(history)==2 and history[0]['data']['scope']==data['scope']

@pytest.mark.parametrize('role',['COMPANY_EDITOR','COMPANY_APPROVER'])
def test_global_catalog_is_not_public(setup,role):
    factory,files,operator,admin=setup
    with factory() as session:
        with pytest.raises(Denied,match='ACTION_NOT_AUTHORIZED'): CapabilityApplication(session).inventory(Actor(operator.id,role))

def test_composition_provider_boundary_and_scope(setup):
    factory,files,operator,admin=setup
    with factory.begin() as session:
        service=CapabilityApplication(session,files); data,root,version=capability(service,admin)
        with pytest.raises(Denied,match='IMPROVEMENT_PROVIDER_NOT_CONNECTED'): service.save_composition(operator,composition_data(version),'blocked')
        assert session.scalar(select(func.count()).select_from(S.compositions))==0
        service=CapabilityApplication(session,files,TestInputs(operator.id))
        comp=service.save_composition(operator,composition_data(version),'create')
        assert service.save_composition(operator,composition_data(version),'create')==comp
        saved=service.composition(operator,comp['id'])
        assert saved['versions'][0]['improvement_version_id']=='TEST_IMPROVEMENT_A'
        assessment=saved['assessments'][0]
        reviewed=service.review_assessment(operator,assessment['id'],'CONFIRMED','TEST limited applicability review','assessment-review')
        assert reviewed['fit']=='NEED_MORE_INFO'
        assert service.review_assessment(operator,assessment['id'],'CONFIRMED','TEST limited applicability review','assessment-review')==reviewed
        with pytest.raises(Denied,match='OBJECT_NOT_FOUND'): service.composition(Actor(admin.id,'DATCO_OPERATOR'),comp['id'])
        with pytest.raises(Denied,match='ACTION_NOT_AUTHORIZED'): service.composition(admin,comp['id'])

def test_composition_versions_coverage_and_feature_conflict(setup):
    factory,files,operator,admin=setup
    with factory.begin() as session:
        service=CapabilityApplication(session,files,TestInputs(operator.id)); capdata,root,v=capability(service,admin)
        data=composition_data(v); feature_id=capdata['functions'][0]['revision_id']
        data['coverage']=[{'requirement':'재고 관리','capability_version_id':v['id'],'feature_revision_ids':[feature_id],
          'role':'정보 조회','addressed_scope':'재고현황','unaddressed_scope':'자동 분석 미확인','missing_information':['기초재고']}]
        comp=service.save_composition(operator,data,'c1')
        changed=deepcopy(data); changed['name']='TEST revision 2'
        second=service.save_composition(operator,changed,'c2',comp['id'],comp['version_id'])
        history=service.composition(operator,comp['id'])['versions']; assert len(history)==2
        assert history[0]['data']['name']==data['name'] and second['ordinal']==2
        with pytest.raises(Denied,match='STALE_INPUT_VERSION'): service.save_composition(operator,data,'c3',comp['id'],comp['version_id'])
        bad=deepcopy(data); bad['coverage'][0]['feature_revision_ids']=[str(uuid4())]
        with pytest.raises(Denied,match='TARGET_VERSION_MISMATCH'): service.save_composition(operator,bad,'bad')

def test_confirmed_notice_match_snapshot_review_and_stale(setup,context):
    factory,files,operator,admin=setup
    notice,nv,job=prepare(context); process_one(factory,files)
    candidate=detail(context,notice)['versions'][0]['runs'][0]['candidates'][0]
    rv=confirm(context,nv,candidate)
    with factory.begin() as session:
        service=CapabilityApplication(session,files,TestInputs(operator.id)); data,root,v=capability(service,admin)
        comp=service.save_composition(operator,composition_data(v),'comp')
        match=service.prepare_match(operator,comp['version_id'],notice['id'],rv['id'],'match')
        assert match['fit']=='NEED_MORE_INFO' and len(match['data']['dimensions'])==3
        snap=service.match(operator,match['candidate_id']); assert snap['current_valid']
        assert snap['snapshot']['input']['notice']['requirement_version_id']==rv['id']
        with pytest.raises(Denied,match='MISSING_REQUIRED_INFORMATION'): service.review_match(operator,match['candidate_id'],'PROPOSABLE','unverified','bad-review')
        service.review_match(operator,match['candidate_id'],'HOLD','Review evidence','review')
        changed=deepcopy(data); changed['scope']='TEST revised scope'
        service.save_capability(admin,changed,'draft',root['id'],1); service.publish(admin,root['id'],2,'publish')
        assert not service.match(operator,match['candidate_id'])['current_valid']
        assert service.prepare_match(operator,comp['version_id'],notice['id'],rv['id'],'match')['snapshot_id']==match['snapshot_id']
        assert service.save_composition(operator,composition_data(v),'comp')['version_id']==comp['version_id']
        assert service.review_match(operator,match['candidate_id'],'HOLD','Review evidence','review')['outcome']=='HOLD'
        with pytest.raises(Denied,match='STALE_INPUT_VERSION'): service.review_match(operator,match['candidate_id'],'HOLD','stale','stale-review')

def test_api_contract_cookie_origin_admin_and_fail_closed(setup,monkeypatch):
    factory,files,operator,admin=setup
    def sessions():
        with factory() as s: yield s
    app.dependency_overrides[get_session]=sessions
    monkeypatch.setattr(api,'application',lambda s:CapabilityApplication(s,files))
    try:
        with TestClient(app) as client:
            assert client.get('/capability/features').status_code==401
            assert client.get('/capability/features',headers={'X-Role':'DATCO_ADMIN'}).status_code==401
            with factory() as session:
                username=SqlNoticeStore(session).get('actors',admin.id)['username']
            login=client.post('/notice/session',json={'username':username,'password':'test-only-password'},headers={'Origin':'http://localhost:3000'})
            assert login.status_code==200
            page=client.get('/capability/features?q=재고'); assert page.status_code==200 and page.json()['total']>0
            assert client.post('/capability/catalog',json={},headers={'Origin':'https://untrusted.example'}).status_code==403
            assert client.get('/capability/features?limit=10000').status_code==422
    finally: app.dependency_overrides.clear()

def test_changed_source_revision_preserves_published_capability(setup):
    import json
    factory,files,operator,admin=setup
    with factory.begin() as session:
        service=CapabilityApplication(session,files); data,root,v=capability(service,admin)
        old_revision=data['functions'][0]['revision_id']
        changed=json.loads(SOURCE.read_bytes())
        item=next(f for f in changed['features'] if f['feature_id']=='DMP-D89936F06CA33048')
        item['description']+=' SYNTHETIC_TEST_REVISION'
        service.import_inventory(json.dumps(changed,ensure_ascii=False).encode(),admin)
        assert session.scalar(select(func.count()).select_from(S.features))==649
        assert session.scalar(select(func.count()).select_from(S.revisions))==650
        assert service.get(S.versions,v['id'])['data']['functions'][0]['revision_id']==old_revision
        assert 'SYNTHETIC_TEST_REVISION' not in service.get(S.revisions,old_revision)['data']['description']
        assert service.feature(operator,'DMP-D89936F06CA33048')['revisions'][-1]['ordinal']==2

def test_multiple_capabilities_union_and_conflicting_source_revisions(setup):
    import json
    factory,files,operator,admin=setup
    with factory.begin() as session:
        service=CapabilityApplication(session,files,TestInputs(operator.id))
        data,root,unused=capability(service,admin)
        ids=['DMP-D89936F06CA33048','DMP-A72B49E339A21D50','DMP-757AF017E65ADE72','DMP-9942A5CC2A989A73']
        refs=[service.feature(admin,key)['revisions'][-1] for key in ids]
        data['functions']=[{'revision_id':r['id'],'role':r['data']['name']} for r in refs]
        data['service']='TEST 재고 및 입출고 네 기능'
        one=service.save_capability(admin,data,'multi-one'); onev=service.publish(admin,one['id'],1,'multi-publish-one')
        two_data=deepcopy(data); two_data['service']='TEST 공유 재고 조회'; two_data['functions']=data['functions'][:1]
        two=service.save_capability(admin,two_data,'multi-two'); twov=service.publish(admin,two['id'],1,'multi-publish-two')
        compdata=composition_data(onev); compdata['capability_version_ids'].append(twov['id'])
        comp=service.save_composition(operator,compdata,'multi-composition')
        links=service.rows(S.composition_links,version_id=comp['version_id']); assert len(links)==2
        feature_ids=[f['revision_id'] for link in links for f in service.rows(S.links,version_id=link['capability_version_id'])]
        assert len(feature_ids)==5 and len(set(feature_ids))==4
        changed=json.loads(SOURCE.read_bytes()); next(f for f in changed['features'] if f['feature_id']==ids[0])['description']+=' SYNTHETIC_CONFLICT_TEST'
        service.import_inventory(json.dumps(changed,ensure_ascii=False).encode(),admin)
        changed_revision=service.feature(admin,ids[0])['revisions'][-1]
        three_data=deepcopy(two_data); three_data['service']='TEST 다른 원천 Revision'; three_data['functions']=[{'revision_id':changed_revision['id'],'role':'검토된 새 원천 테스트'}]
        three=service.save_capability(admin,three_data,'multi-three'); threev=service.publish(admin,three['id'],1,'multi-publish-three')
        conflicting=composition_data(onev); conflicting['capability_version_ids'].append(threev['id'])
        with pytest.raises(Denied,match='FEATURE_REVISION_CONFLICT'):
            service.save_composition(operator,conflicting,'conflicting-composition')
        assert session.scalar(select(func.count()).select_from(S.compositions))==1
