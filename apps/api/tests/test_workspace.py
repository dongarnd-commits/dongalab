"""W0 projections and real session revocation against guarded PostgreSQL."""
from hashlib import sha256
from datetime import datetime,timezone
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import get_settings
from app.infrastructure.notice_store import SqlNoticeStore
from test_company_workflow import env,fresh,call
import pytest
pytestmark=pytest.mark.integration

def test_workspace_scopes_and_role_projections(env):
 e=env;c,site,p=fresh(e)
 for role in ('editor','operator','approver'):
  d=call(e,role,'/workspace');assert d['actor']['role']==e['people'][role]['role'];assert c['id'] in {r['id'] for r in d['companies']};assert 'password_hash' not in str(d) and 'business_number' not in str(d)
 assert c['id'] not in {r['id'] for r in call(e,'other','/workspace')['companies']}
 admin=call(e,'admin','/workspace');assert admin['catalog'] is not None;assert admin['compositions']==admin['matches']==admin['proposals']==[];assert all(set(r)=={'id','name'} for r in admin['companies'])

def test_real_logout_revokes_only_current_session_and_preserves_audit(env):
 e=env;c,site,p=fresh(e);origin=get_settings().web_origin
 with TestClient(app) as client:
  # A second existing session exercises exact-token revocation without revoking the fixture browser.
  import secrets
  token=secrets.token_urlsafe(32)
  with e['factory'].begin() as s:SqlNoticeStore(s).add('sessions',actor_id=e['people']['editor']['id'],token_hash=sha256(token.encode()).hexdigest(),expires_at=datetime(2099,1,1,tzinfo=timezone.utc))
  client.cookies.set('datco_session',token)
  assert client.post('/notice/session/logout',headers={'Origin':'https://wrong.invalid'}).status_code==403
  assert client.get('/workspace').status_code==200
  r=client.post('/notice/session/logout',headers={'Origin':origin});assert r.status_code==200 and r.json()=={'logged_out':True};assert 'Max-Age=0' in r.headers['set-cookie']
  client.cookies.set('datco_session',token)
  assert client.get('/workspace').status_code==401 and client.get('/company').status_code==401
  with e['factory']() as s:
   store=SqlNoticeStore(s);assert store.rows('sessions',token_hash=sha256(token.encode()).hexdigest())[0]['expires_at']<=datetime.now(timezone.utc);assert any(a['action']=='LOGOUT' for a in store.rows('audits',actor_id=e['people']['editor']['id']))
 assert call(e,'editor','/workspace')['actor']['id']==e['people']['editor']['id']
