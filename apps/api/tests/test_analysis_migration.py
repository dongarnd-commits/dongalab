"""Execute frozen new Migration in guarded disposable schema, never normal DB."""
import importlib.util,json
from uuid import uuid4
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import MetaData,Table,select,inspect
from app.core.config import ROOT
from app.infrastructure.database import Base,get_engine
from isolation import require_test_database
pytestmark=pytest.mark.integration

@pytest.fixture
def migration_schema():
 require_test_database()
 schema='test_analysis_migration_'+uuid4().hex
 connection=get_engine().connect().execution_options(schema_translate_map={None:schema})
 outer=connection.begin();connection.exec_driver_sql('CREATE SCHEMA '+schema)
 connection.exec_driver_sql('SET LOCAL search_path = '+schema+', public')
 def load(name):
  path=ROOT/'apps/api/alembic/versions'/name
  spec=importlib.util.spec_from_file_location('tested_'+name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
 # Build the actual historical revision, not today's metadata with future columns.
 chain=['6d5ba2015303_notice_first_slice.py','a44df74db1ac_bizinfo_ingestion.py','b730cf01a649_capability_catalog.py','c941a0042026_common_analysis_lineage.py']
 try:
  with Operations.context(MigrationContext.configure(connection)):
   for name in chain:load(name).upgrade()
   module=load(chain[-1])
   yield connection,module,schema
 finally:outer.rollback();connection.close()

def reflected(connection,name,schema):return Table(name,MetaData(),schema=schema,autoload_with=connection)
def add(connection,table_name,schema,**values):
 values.setdefault('id',str(uuid4()))
 t=reflected(connection,table_name,schema)
 return dict(connection.execute(t.insert().values(**values).returning(t)).mappings().one())

def test_safe_empty_down_and_up_model_columns(migration_schema):
 c,m,schema=migration_schema;m.downgrade()
 assert 'analysis_kind' not in {x['name'] for x in inspect(c).get_columns('analysis_runs',schema=schema)}
 m.upgrade()
 # Verify the historical round-trip also upgrades through the real remaining chain.
 for filename in ['d752a0012026_immutable_matching_inputs.py','e863p0012026_proposal_production.py','f974c0012026_company_workflow.py','fa85b0012026_company_business_sources.py','fb96c0012026_information_requests.py','fc07d0012026_recorded_authorization.py']:
  path=ROOT/'apps/api/alembic/versions'/filename
  spec=importlib.util.spec_from_file_location('tested_following_'+filename,path);following=importlib.util.module_from_spec(spec);spec.loader.exec_module(following);following.upgrade()
 for name,t in Base.metadata.tables.items():
  actual={x['name']:x for x in inspect(c).get_columns(name,schema=schema)}
  assert set(actual)==set(t.c.keys())
  assert all(actual[col.name]['nullable']==col.nullable for col in t.c)

def test_legacy_and_notice_rows_survive_up_exactly(migration_schema):
 c,m,schema=migration_schema;m.downgrade()
 actor=add(c,'local_actors',schema,username='TEST migration actor',role='DATCO_OPERATOR',password_hash='TEST_HASH_NOT_LOGIN')
 notice=add(c,'notices',schema,external_key='TEST_MIGRATION',title='TEST preserved Notice',current_ordinal=1)
 version=add(c,'notice_versions',schema,notice_id=notice['id'],ordinal=1,mode='DEMO_TEST',metadata={})
 source=add(c,'notice_sources',schema,version_id=version['id'],name='TEST source',media_type='text/html',provenance='SYNTHETIC MIGRATION HISTORY',storage_key=None,digest=None)
 job=add(c,'background_jobs',schema,version_id=version['id'],actor_id=actor['id'],request_key='TEST history',kind='NOTICE_ANALYSIS',payload={},state='SUCCEEDED')
 attempt=add(c,'job_attempts',schema,job_id=job['id'],ordinal=1,owner=str(uuid4()),state='SUCCEEDED')
 run=add(c,'analysis_runs',schema,attempt_id=attempt['id'],version_id=version['id'],provider_version='TEST historical provider',extractor_version='TEST history',missing=[],conflicts=[])
 location=add(c,'source_locations',schema,run_id=run['id'],source_id=source['id'],descriptor='TEST HTML history',text='TEST requirement')
 candidate=add(c,'analysis_candidates',schema,run_id=run['id'],location_id=location['id'],kind='ELIGIBILITY_REQUIREMENT',content='TEST requirement',reason='TEST historical execution')
 review=add(c,'analysis_reviews',schema,candidate_id=candidate['id'],actor_id=actor['id'],outcome='CONFIRM',note='TEST historical human review',official_verified=True)
 requirement=add(c,'notice_requirements',schema,notice_id=notice['id'])
 rv=add(c,'notice_requirement_versions',schema,requirement_id=requirement['id'],notice_version_id=version['id'],review_id=review['id'],ordinal=1,scope='TEST history')
 cap=add(c,'capabilities',schema,draft={},draft_revision=1,current_ordinal=1,provider_mapping={})
 cv=add(c,'capability_versions',schema,capability_id=cap['id'],ordinal=1,data={},actor_id=actor['id'])
 assessment=add(c,'capability_assessments',schema,company_id='TEST company',improvement_version_id='TEST improvement',capability_version_id=cv['id'],state='CONFIRMED',fit='NEED_MORE_INFO',reason='TEST preserved legacy',input={'context':{'company_id':'TEST company','improvement_version_id':'TEST improvement'}})
 composition=add(c,'service_compositions',schema,company_id='TEST company',current_ordinal=1)
 compositionv=add(c,'service_composition_versions',schema,composition_id=composition['id'],ordinal=1,improvement_version_id='TEST improvement',context={},data={},actor_id=actor['id'])
 snapshot=add(c,'capability_match_snapshots',schema,composition_version_id=compositionv['id'],requirement_version_id=rv['id'],input={})
 match=add(c,'capability_match_candidates',schema,snapshot_id=snapshot['id'],fit='NEED_MORE_INFO',data={'preserved':'TEST'})
 matchreview=add(c,'capability_match_reviews',schema,candidate_id=match['id'],actor_id=actor['id'],outcome='HOLD',note='TEST legacy review')
 before={name:[dict(r) for r in c.execute(select(reflected(c,name,schema))).mappings()] for name in ['analysis_runs','analysis_candidates','analysis_reviews','source_locations','capability_assessments','capability_match_candidates','capability_match_reviews']}
 m.upgrade();c.exec_driver_sql('SET CONSTRAINTS ALL IMMEDIATE');c.exec_driver_sql('SET CONSTRAINTS ALL DEFERRED')
 for name,old in before.items():
  now=[dict(r) for r in c.execute(select(reflected(c,name,schema))).mappings()]
  assert [{k:r[k] for k in old[0]} for r in now]==old
 for name in ['capability_assessments','capability_match_candidates','capability_match_reviews']:
  row=c.execute(select(reflected(c,name,schema))).mappings().one()
  assert row['legacy_lineage'] and row.get('analysis_run_id') is None and row.get('analysis_review_id') is None
 assert c.execute(select(reflected(c,'analysis_runs',schema))).mappings().one()['analysis_kind']=='NOTICE_REQUIREMENT_ANALYSIS'
 # Down with only unlinked legacy + Notice history is safe and preserves all original rows.
 m.downgrade()
 for name,old in before.items():assert [dict(r) for r in c.execute(select(reflected(c,name,schema))).mappings()]==old

def test_down_refuses_new_non_notice_history_without_deleting(migration_schema):
 c,m,schema=migration_schema
 actor=add(c,'local_actors',schema,username='TEST down guard',role='DATCO_OPERATOR',password_hash='TEST_HASH')
 run=add(c,'analysis_runs',schema,analysis_kind='SUPPORT_MATCHING',actor_id=actor['id'],provider_version='TEST',extractor_version='not-applicable',missing=[],conflicts=[])
 # A pending same-transaction Run is sufficient to prohibit destructive Down.
 with pytest.raises(RuntimeError,match='No data deleted'):m.downgrade()
 assert c.execute(select(reflected(c,'analysis_runs',schema))).mappings().one()['id']==run['id']
