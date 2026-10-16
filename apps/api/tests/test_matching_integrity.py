"""Real committed PostgreSQL sessions, blocking locks and immutable input history."""
import copy,time,threading,importlib.util,json
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select,func,text,inspect
from sqlalchemy.exc import IntegrityError
from alembic.migration import MigrationContext
from alembic.operations import Operations
from app.core.config import ROOT
from app.capability.application import CapabilityApplication
from app.infrastructure import capability_schema as S,notice_schema as N
from app.notice.domain import Actor,Denied
from capability_scenario_fixture import ScenarioInputs
from committed_capability_fixture import committed_environment
pytestmark=pytest.mark.integration

@pytest.fixture(scope='module')
def env():
    with committed_environment(ROOT/'storage/private/runtime/matching-integrity') as e:yield e

def service(e,s):return CapabilityApplication(s,e.files,ScenarioInputs(e))
def actor(e):return Actor(e.accounts['operator']['id'],'DATCO_OPERATOR')
def counts(e):
    with e.factory() as s:return [s.scalar(select(func.count()).select_from(t)) for t in [S.match_snapshots,S.match_candidates]]+[s.scalar(select(func.count()).select_from(N.runs).where(N.runs.c.analysis_kind=='SUPPORT_MATCHING'))]
def revised(e,r):
    data=copy.deepcopy(r['composition_data']);data['name']+=' TEST v2';return data

def test_p1_original_interleaving_rechecks_after_command_lock(env,monkeypatch):
    e=env;r=e.compose('A',['A']);n=e.notices['A'];original=CapabilityApplication.command;after=[]
    def gated(self,who,key,payload,execute):
        if key=='P1_INTERLEAVED':
            e.call('operator','/capability/compositions/'+r['composition']['id']+'/versions',dict(data=revised(e,r),expected_version=r['composition']['version_id'],idempotency_key=e.nonce()))
            after.extend(counts(e))
        return original(self,who,key,payload,execute)
    monkeypatch.setattr(CapabilityApplication,'command',gated)
    result=e.call('operator','/capability/matches',dict(composition_version_id=r['composition']['version_id'],notice_id=n['notice_id'],requirement_version_id=n['requirement_version_id'],idempotency_key='P1_INTERLEAVED'),status=409)
    assert result['reason']=='STALE_INPUT_VERSION' and counts(e)==after


def blocked(e,waiting,holder):
    until=time.monotonic()+8
    while time.monotonic()<until:
        with e.factory() as s:
            if s.scalar(text('SELECT :holder = ANY(pg_blocking_pids(:waiting))'),dict(holder=holder,waiting=waiting)):return True
        time.sleep(.02)
    return False

@pytest.mark.parametrize('winner',['composition','matching'])
def test_two_actual_transactions_serialize_root_and_preserve_history(env,winner):
    e=env;r=e.compose('A',['A']);n=e.notices['A'];ready=threading.Event();pid=[];before=counts(e)
    first=e.factory();transaction=first.begin();holder=first.scalar(text('SELECT pg_backend_pid()'));saved=None
    def second():
        try:
            with e.factory.begin() as s:
                s.execute(text("SET LOCAL lock_timeout='10s'"));pid.append(s.scalar(text('SELECT pg_backend_pid()')));ready.set()
                app=service(e,s)
                if winner=='composition':return app.prepare_match(actor(e),r['composition']['version_id'],n['notice_id'],n['requirement_version_id'],e.nonce())
                return app.save_composition(actor(e),revised(e,r),e.nonce(),r['composition']['id'],r['composition']['version_id'])
        except Denied as exc:return dict(reason=exc.reason,status=exc.status)
    with ThreadPoolExecutor(max_workers=1) as executor:
        try:
            app=service(e,first)
            if winner=='composition':app.save_composition(actor(e),revised(e,r),e.nonce(),r['composition']['id'],r['composition']['version_id'])
            else:
                saved=app.prepare_match(actor(e),r['composition']['version_id'],n['notice_id'],n['requirement_version_id'],e.nonce())
                frozen=copy.deepcopy(app.get(S.match_snapshots,saved['snapshot_id']))
            future=executor.submit(second);assert ready.wait(5);assert blocked(e,pid[0],holder)
            transaction.commit();result=future.result(timeout=12)
        finally:first.rollback();first.close()
    if winner=='composition':
        assert result==dict(reason='STALE_INPUT_VERSION',status=409) and counts(e)==before
    else:
        assert result['ordinal']==2
        detail=e.call('operator','/capability/matches/'+saved['candidate_id']);assert not detail['current_valid']
        with e.factory() as s:assert service(e,s).get(S.match_snapshots,saved['snapshot_id'])==frozen
    old=e.call('operator','/capability/matches/'+r['candidate']['candidate_id'])
    assert old['snapshot']==r['snapshot'] and old['reviews'][0]['id']==r['review']['id'] and not old['current_valid']


def test_idempotent_historical_receipt_is_not_current_input(env):
    e=env;r=e.compose('A',['A']);n=e.notices['A']
    body=dict(composition_version_id=r['composition']['version_id'],notice_id=n['notice_id'],requirement_version_id=n['requirement_version_id'],idempotency_key=e.nonce())
    first=e.call('operator','/capability/matches',body);before=counts(e)
    e.call('operator','/capability/compositions/'+r['composition']['id']+'/versions',dict(data=revised(e,r),expected_version=r['composition']['version_id'],idempotency_key=e.nonce()))
    assert e.call('operator','/capability/matches',body)==first and counts(e)==before
    assert not e.call('operator','/capability/matches/'+first['candidate_id'])['current_valid']

@pytest.mark.parametrize('table_name',['match_snapshots','composition_versions','composition_links','versions','links','revisions','features'])
@pytest.mark.parametrize('operation',['update','delete'])
def test_snapshot_and_referenced_inputs_reject_direct_dml(env,table_name,operation):
    e=env;r=e.compose('B',['B']);table=getattr(S,table_name)
    with e.factory() as s:row=s.execute(select(table).limit(1)).mappings().one();key=row['id']
    with pytest.raises(IntegrityError,match='IMMUTABLE_MATCHING_INPUT'):
        with e.factory.begin() as s:
            command=table.update().values(id=key) if operation=='update' else table.delete()
            s.execute(command.where(table.c.id==key))
    assert e.call('operator','/capability/matches/'+r['candidate']['candidate_id'])['snapshot']==r['snapshot']


def test_raw_sql_jsonb_change_rejected_and_new_snapshot_is_independent(env):
    e=env;r=e.compose('B',['B']);sid=r['snapshot']['id']
    with pytest.raises(IntegrityError,match='IMMUTABLE_MATCHING_INPUT'):
        with e.factory.begin() as s:s.execute(text('UPDATE "'+e.schema+'".capability_match_snapshots SET input=jsonb_set(input,CAST(:path AS text[]),CAST(:replacement AS jsonb)) WHERE id=:id'),dict(id=sid,path='{composition,name}',replacement=json.dumps('TEST silent edit')))
    new=e.compose('B',['B'])
    assert new['snapshot']['id']!=sid and e.call('operator','/capability/matches/'+r['candidate']['candidate_id'])['snapshot']==r['snapshot']

@pytest.mark.parametrize('kind',['capability','composition'])
def test_late_child_insert_cannot_change_frozen_version_meaning(env,kind):
    e=env;r=e.compose('A',['A'])
    with pytest.raises(IntegrityError,match='IMMUTABLE_VERSION_LINK_MISMATCH'):
        with e.factory.begin() as s:
            app=service(e,s)
            if kind=='capability':
                revision=next(v for v in app.rows(S.revisions) if v['id'] not in {x['id'] for x in e.caps['A']['features']})
                app.add(S.links,version_id=e.caps['A']['version']['id'],revision_id=revision['id'],role='TEST late extra input')
            else:app.add(S.composition_links,version_id=r['composition']['version_id'],capability_version_id=e.caps['B']['version']['id'],assessment_id=None)


def migration():
    path=ROOT/'apps/api/alembic/versions/d752a0012026_immutable_matching_inputs.py'
    spec=importlib.util.spec_from_file_location('matching_input_migration',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def test_new_migration_preserves_existing_snapshots_and_refuses_unsafe_down():
    with committed_environment(ROOT/'storage/private/runtime/matching-migration-history',protect_inputs=False) as e:
        r=e.compose('A',['A']);m=migration()
        tables=[S.match_snapshots,S.match_candidates,S.match_reviews,S.composition_versions,S.versions,N.runs,N.reviews,N.locations]
        def read():
            with e.factory() as s:return [[dict(x) for x in s.execute(select(t).order_by(t.c.id)).mappings()] for t in tables]
        before=read()
        with e.engine.begin() as c:
            c.exec_driver_sql('SET LOCAL search_path='+e.schema+',public')
            with Operations.context(MigrationContext.configure(c)):m.upgrade()
        assert read()==before
        with pytest.raises(IntegrityError,match='IMMUTABLE_MATCHING_INPUT'):
            with e.factory.begin() as s:s.execute(S.match_snapshots.update().where(S.match_snapshots.c.id==r['snapshot']['id']).values(input={}))
        with e.engine.begin() as c:
            c.exec_driver_sql('SET LOCAL search_path='+e.schema+',public')
            with Operations.context(MigrationContext.configure(c)):
                with pytest.raises(RuntimeError,match='No data deleted'):m.downgrade()
        assert read()==before


def test_new_migration_empty_down_up_and_metadata_compatibility():
    with committed_environment(ROOT/'storage/private/runtime/matching-migration-empty',protect_inputs=False) as e:
        m=migration()
        with e.engine.begin() as c:
            c.exec_driver_sql('SET LOCAL search_path='+e.schema+',public')
            with Operations.context(MigrationContext.configure(c)):
                m.upgrade();m.downgrade();m.upgrade()
            from app.infrastructure.database import Base
            for name,t in Base.metadata.tables.items():assert set(t.c.keys())=={x['name'] for x in inspect(c).get_columns(name,schema=e.schema)}
