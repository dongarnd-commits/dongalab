"""Administrator projections and existing Membership commands, on owned PostgreSQL."""
import json
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.admin import router
from app.main import app as business_app
from app.notice.domain import Actor, Denied
from app.operations.admin import AdminProjection
from app.infrastructure import company_schema as C, notice_schema as N
from sqlalchemy import select, func
from test_company_workflow import env, fresh, call

pytestmark = pytest.mark.integration


def admin_client(env, role):
    application = FastAPI()
    application.exception_handlers.update(business_app.exception_handlers)
    application.include_router(router)
    client = TestClient(application)
    client.cookies.update(env['clients'][role].cookies)
    return client


def test_admin_whitelist_real_counts_and_existing_membership_command(env):
    company, _, _ = fresh(env)
    with admin_client(env, 'admin') as client:
        overview = client.get('/admin/overview')
        assert overview.status_code == 200
        with env['factory']() as session:
            assert overview.json()['companies'] == session.scalar(select(func.count()).select_from(C.companies))
            assert overview.json()['accounts'] == session.scalar(select(func.count()).select_from(N.actors))
        access = client.get('/admin/access').json()
        assert set(access) == {'users', 'companies', 'memberships', 'allowed_actions', 'limitations'}
        user = next(u for u in access['users'] if u['id'] == env['people']['other']['id'])
        assert set(user) == {'id', 'username', 'role', 'created_at'}
        assert not any(m['company_id'] == company['id'] and m['actor_id'] == user['id'] for m in access['memberships'])
        for forbidden in ('password_hash', 'token_hash', 'storage_key', 'business_number'):
            assert forbidden not in json.dumps(access)
        # Reuse the actual approved admin command; no new role or business authority.
        call(env, 'admin', '/company/' + company['id'] + '/access', {'username': user['username']})
        after = client.get('/admin/access').json()
        grants = [m for m in after['memberships'] if m['company_id'] == company['id'] and m['actor_id'] == user['id']]
        assert len(grants) == 1
        assert grants[0]['granted_by'] == env['people']['admin']['id']
        assert client.get('/admin/access').json() == after
        call(env, 'admin', '/company/' + company['id'], status=403)
        call(env, 'operator', '/company/' + company['id'] + '/access', {'username': user['username']}, status=403)
        call(env, 'admin', '/company/' + company['id'] + '/access', {'username': env['people']['admin']['username']}, status=422)
    assert call(env, 'other', '/company/' + company['id'])['company']['id'] == company['id']


@pytest.mark.parametrize('role', ['editor', 'operator', 'approver', 'other'])
def test_admin_routes_deny_all_other_roles_without_scope_expansion(env, role):
    with admin_client(env, role) as client:
        for path in ('overview', 'access', 'connections'):
            response = client.get('/admin/' + path)
            assert response.status_code == 403
            assert response.json()['reason'] == 'ACTION_NOT_AUTHORIZED'


def test_connections_only_settings_boolean_and_disabled_external_providers(env, monkeypatch):
    from pydantic import SecretStr
    from types import SimpleNamespace
    import app.api.admin as api
    sentinel = 'TEST_SECRET_MUST_NOT_LEAVE_BACKEND'
    monkeypatch.setattr(api, 'get_settings', lambda: SimpleNamespace(bizinfo_api_key=SecretStr(sentinel)))
    with admin_client(env, 'admin') as client:
        response = client.get('/admin/connections')
        assert response.status_code == 200 and sentinel not in response.text
        value = response.json()
        assert value['bizinfo']['status'] == 'CONFIGURED' and value['bizinfo']['validation'] == 'NOT_PROBED'
        assert value['worker']['status'] == 'UNMEASURED'
        assert {p['id']: p['status'] for p in value['analysis']['providers']} == {'RULE': 'AVAILABLE', 'GPT': 'NOT_CONFIGURED', 'GEMINI': 'NOT_CONFIGURED', 'CLAUDE': 'NOT_CONFIGURED', 'GROK': 'NOT_CONFIGURED'}
        for path in ('overview', 'access', 'connections'):
            assert client.post('/admin/' + path, json={}).status_code == 405
    with env['factory']() as session:
        with pytest.raises(Denied):
            AdminProjection(session).access(Actor(env['people']['operator']['id'], 'DATCO_OPERATOR'))


def test_admin_routes_require_a_real_session():
    application = FastAPI()
    application.exception_handlers.update(business_app.exception_handlers)
    application.include_router(router)
    with TestClient(application) as client:
        assert client.get('/admin/overview').status_code == 401
        assert client.get('/admin/access').status_code == 401
        assert client.get('/admin/connections').status_code == 401
