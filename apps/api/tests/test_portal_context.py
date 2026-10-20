"""Real HTTP/read-only Context, exact version references and existing scope boundaries."""
from uuid import uuid4
from sqlalchemy import select,func,update
from app.infrastructure import company_schema as S
from app.infrastructure.notice_schema import actors
from test_company_workflow import env,fresh,call
import pytest
pytestmark=pytest.mark.integration

def setup_context(e):
 c,site,_=fresh(e);data=dict(title='TEST historical title',original_text='TEST original v1',site_id=site['id'],as_is='TEST original As-Is',to_be='TEST goal v1')
 v1=call(e,'editor','/company/'+c['id']+'/improvements',dict(data=data))
 call(e,'editor','/company/'+c['id']+'/sites',dict(data=dict(name='TEST revised site',address='TEST changed address'),site_id=site['id'],expected_ordinal=1))
 v2=call(e,'editor','/company/'+c['id']+'/improvements',dict(data=dict(data,title='TEST latest title',to_be='TEST goal v2'),improvement_id=v1['improvement_id'],expected_ordinal=1))
 return c,site,v1,v2

def test_http_navigation_exact_root_versions_and_read_only_projection(env):
 e=env;c,s,v1,v2=setup_context(e);path='/company/'+c['id']+'/navigation'
 with e['factory']() as session:before={t.name:session.scalar(select(func.count()).select_from(t)) for t in S.TABLES}
 historical=call(e,'editor',path+'?version_id='+v1['id']);operator=call(e,'operator',path+'?version_id='+v1['id'])
 assert historical==operator
 chosen=historical['selection'];assert chosen==dict(company_id=c['id'],site_id=s['id'],site_ordinal=1,improvement_id=v1['improvement_id'],improvement_version_id=v1['id'],improvement_ordinal=1,is_latest_version=False)
 assert historical['sites'][0]['versions'][0]['data']['name']=='TEST Plant'
 assert historical['improvements'][0]['versions'][0]['data']['title']=='TEST historical title'
 latest=call(e,'editor',path);assert latest['selection']['improvement_version_id']==v2['id'] and latest['selection']['site_ordinal']==2
 assert not any(k in str(historical) for k in ('password_hash','storage_key','reviews','fact_version_ids','evidence_ids','audit'))
 with e['factory']() as session:assert before=={t.name:session.scalar(select(func.count()).select_from(t)) for t in S.TABLES}
 data=dict(v2['data'],title='TEST newly added version');call(e,'editor','/company/'+c['id']+'/improvements',dict(data=data,improvement_id=v1['improvement_id'],expected_ordinal=2))
 old=call(e,'editor',path+'?version_id='+v1['id']);assert old['selection']==historical['selection'];assert old['improvements'][0]['versions'][0]==historical['improvements'][0]['versions'][0]
 assert call(e,'editor',path+'?version_id='+v1['id'])['selection']['improvement_version_id']==v1['id']

@pytest.mark.parametrize('role,status',[('other',404),('approver',403),('admin',403)])
def test_http_navigation_preserves_role_and_company_scope(env,role,status):
 c,s,v1,v2=setup_context(env);call(env,role,'/company/'+c['id']+'/navigation?site_id='+s['id']+'&version_id='+v1['id'],status=status)

def test_http_navigation_rejects_mixed_parent_identifiers_and_missing_versions(env):
 e=env;c,s,v1,v2=setup_context(e);foreign,fs,fv1,fv2=setup_context(e);path='/company/'+c['id']+'/navigation'
 for query in ['site_id='+fs['id'],'version_id='+fv1['id'],'improvement_id='+fv1['improvement_id'],'version_id='+v1['id']+'&improvement_id='+fv1['improvement_id'],'site_id='+s['id']+'&version_id='+fv1['id'],'version_id='+str(uuid4()),'site_ordinal=999']:
  call(e,'editor',path+'?'+query,status=404)
 call(e,'editor',path+'?version_id='+v1['id']+'&site_ordinal=2',status=409)
 call(e,'editor',path+'?site_ordinal='+v1['id'],status=422)
 from fastapi.testclient import TestClient
 from app.main import app
 with TestClient(app) as anonymous:assert anonymous.get(path).status_code==401

def test_http_navigation_rechecks_current_actor_role_without_granting_access(env):
 e=env;c,s,v1,v2=setup_context(e);path='/company/'+c['id']+'/navigation';assert call(e,'editor',path)['company']['id']==c['id']
 try:
  with e['factory'].begin() as session:session.execute(update(actors).where(actors.c.id==e['people']['editor']['id']).values(role='DATCO_ADMIN'))
  call(e,'editor',path,status=403)
 finally:
  with e['factory'].begin() as session:session.execute(update(actors).where(actors.c.id==e['people']['editor']['id']).values(role='COMPANY_EDITOR'))
