"""Owned loopback preparation checks using non-sensitive sentinel inputs only.

Never prints credentials, cookies, source text or HTTP response bodies. Both
phases are only for the empty/sentinel environment before real-data approval.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import secrets
import shutil
import ssl
import subprocess
import sys

import httpx
import psycopg
from sqlalchemy.engine import make_url

from manual_acceptance import ROOT, WEB, owned, load, head, inspect_label, write, environment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--nonce', required=True)
    parser.add_argument('--phase', choices=('initial', 'resumed'), required=True)
    args = parser.parse_args()
    m = load(args.nonce)
    out = owned(args.nonce)
    if not m.get('preparation') or m['host'] != '127.0.0.1' or m['https_port'] in (8443, 8444):
        raise RuntimeError('ONLY_SEPARATE_LOOPBACK_PREPARATION_ALLOWED')
    if m['origin'] != 'https://127.0.0.1:' + str(m['https_port']):
        raise RuntimeError('PREPARATION_ORIGIN_MISMATCH')
    if head() != m['head']:
        raise RuntimeError('ACCEPTANCE_HEAD_MISMATCH')
    for kind, name in (('container', m['container']), ('volume', m['volume'])):
        inspect_label(kind, name, m['nonce'])
    state = json.loads((out / 'state.json').read_text(encoding='utf-8'))
    if state['phase'] != 'RUNNING' or state['head'] != m['head']:
        raise RuntimeError('OWN_ACCEPTANCE_NOT_RUNNING')
    accounts = json.loads((out / 'accounts.json').read_text(encoding='utf-8'))
    if accounts['nonce'] != m['nonce']:
        raise RuntimeError('PREPARATION_ACCOUNT_IDENTITY_MISMATCH')
    ca = out / 'tls/pki/authorities/local/root.crt'
    shutil.copyfile(ca, out / 'public-root.crt')
    tls = ssl.create_default_context(cafile=str(ca))
    url = make_url(m['url'])
    if (url.host, url.port, url.database, url.username) != ('127.0.0.1', m['pg_port'], m['db'], m['role']):
        raise RuntimeError('PREPARATION_DATABASE_URL_MISMATCH')
    with psycopg.connect(host=url.host, port=url.port, dbname=url.database,
                         user=url.username, password=url.password) as connection:
        assert connection.execute('select current_database(),current_user').fetchone() == (m['db'], m['role'])
        assert not any(connection.execute('select rolsuper,rolcreatedb,rolcreaterole from pg_roles where rolname=current_user').fetchone())
        counts = {name: connection.execute('select count(*) from ' + name).fetchone()[0]
                  for name in ('dmp_features', 'dmp_asset_nodes', 'notices', 'companies', 'analysis_runs', 'proposals', 'dmp_solution_runs')}
        assert counts['dmp_features'] == 649 and counts['dmp_asset_nodes'] == 0
        assert counts['notices'] == counts['analysis_runs'] == counts['proposals'] == counts['dmp_solution_runs'] == 0
        if args.phase == 'initial':
            assert counts['companies'] == 0 and not (out / 'preflight-probe.json').exists()
        else:
            # Never enumerate a populated customer environment in this probe.
            assert counts['companies'] == 1 and (out / 'preflight-probe.json').exists()
            probe = json.loads((out / 'preflight-probe.json').read_text(encoding='utf-8'))
            assert connection.execute('select count(*) from companies where id=%s and name=%s and current_ordinal=1',
                                      (probe['company'], 'TEST 환경 유지 확인')).fetchone()[0] == 1
            assert connection.execute('select count(*) from company_sites').fetchone()[0] == 1
            assert connection.execute('select count(*) from company_sites where current_ordinal<>1').fetchone()[0] == 0
            assert connection.execute('select count(*) from company_files').fetchone()[0] == 1
            assert connection.execute('select count(*) from company_files where id=%s and digest=%s',
                                      (probe['file'], probe['digest'])).fetchone()[0] == 1
            for name in ('company_facts', 'company_improvements', 'company_document_parses'):
                assert connection.execute('select count(*) from ' + name).fetchone()[0] == 0
    identity = httpx.get('http://127.0.0.1:' + str(m['api_port']) + '/__test/identity', trust_env=False).json()
    worker = json.loads((out / 'worker-ready.json').read_text(encoding='utf-8'))
    for value in (identity, worker):
        assert value['database'] == m['db'] and value['db_user'] == m['role']
        assert value['nonce'] == m['nonce'] and value['head'] == m['head']
        assert Path(value['files']).resolve() == out / 'files'
    clients, tokens = {}, []
    expected = dict(editor='COMPANY_EDITOR', operator='DATCO_OPERATOR', admin='DATCO_ADMIN', approver='COMPANY_APPROVER')
    try:
        for label, role in expected.items():
            client = httpx.Client(base_url=m['origin'], verify=tls, trust_env=False,
                                  headers={'Origin': m['origin']}, timeout=45)
            clients[label] = client
            response = client.post('/api/notice/session', json={'username': accounts['accounts'][label], 'password': accounts['password']})
            assert response.status_code == 200
            assert response.headers['x-datco-acceptance'] == m['nonce']
            assert response.headers['x-datco-acceptance-head'] == m['head']
            assert client.get('/api/notice/session').json()['role'] == role
            assert client.cookies.get('datco_uat_' + m['nonce']) and not client.cookies.get('datco_session')
            tokens.extend(cookie.value for cookie in client.cookies.jar)
        editor, operator, admin, approver = (clients[k] for k in ('editor', 'operator', 'admin', 'approver'))
        providers = operator.get('/api/company/analysis/providers').json()['providers']
        assert sum(p['status'] == 'NOT_CONFIGURED' for p in providers) == 4
        assert operator.get('/api/capability/assets', params={'status': 'VERIFIED'}).json()['total'] == 0
        assert editor.get('/api/capability/assets').status_code == 403
        assert approver.get('/api/capability/assets').status_code == 403
        with httpx.Client(base_url=m['origin'], verify=tls, trust_env=False, cookies={'datco_session': 'TEST_OTHER_ENVIRONMENT_COOKIE'}) as stranger:
            assert stranger.get('/api/workspace').status_code == 401
            assert stranger.get('/__test/identity').status_code == 404
        if args.phase == 'initial':
            from registration_sources import number
            sentinel = 'TEST_PRIVATE_SENTINEL_' + secrets.token_hex(12)
            response = editor.post('/api/company', json={'name': 'TEST 환경 유지 확인', 'business_number': number(), 'industry': 'TEST', 'financials': [], 'history': []})
            assert response.status_code == 200
            cid = response.json()['id']
            site = editor.post('/api/company/' + cid + '/sites', json={'data': {'name': 'TEST 사무소', 'address': 'TEST 로컬 확인'}})
            assert site.status_code == 200
            body = ('TEST NON-SENSITIVE ONLY\n' + sentinel).encode('utf-8')
            uploaded = editor.post('/api/company/' + cid + '/files', params={'site_id': site.json()['site']['id']},
                                   content=body, headers={'Content-Type': 'application/octet-stream', 'X-Upload-Name': 'TEST-preflight.txt'})
            assert uploaded.status_code == 200
            fid = uploaded.json()['id']
            assert operator.get('/api/company/' + cid).status_code == 404
            assert operator.get('/api/company/files/' + fid + '/download').status_code == 404
            assert approver.get('/api/company/' + cid).status_code == 404
            for label in ('operator', 'approver'):
                assert admin.post('/api/company/' + cid + '/access', json={'username': accounts['accounts'][label]}).status_code == 200
            write(out / 'preflight-probe.json', {'company': cid, 'file': fid, 'digest': sha256(body).hexdigest(), 'sentinel': sentinel})
        probe = json.loads((out / 'preflight-probe.json').read_text(encoding='utf-8'))
        for label in ('editor', 'operator'):
            downloaded = clients[label].get('/api/company/files/' + probe['file'] + '/download')
            assert downloaded.status_code == 200 and sha256(downloaded.content).hexdigest() == probe['digest']
        assert approver.get('/api/company/files/' + probe['file'] + '/download').status_code == 403
        assert admin.get('/api/company/files/' + probe['file'] + '/download').status_code == 403
        subprocess.run(['node', 'tests/manual-acceptance-preflight.mjs', str(out), args.phase],
                       cwd=WEB, env=environment(m), check=True, stdout=subprocess.DEVNULL)
        for client in clients.values():
            assert client.post('/api/notice/session/logout').status_code == 200
        private_values = [probe['sentinel'], accounts['password'], *tokens]
        assert all(not any(value.encode() in path.read_bytes() for value in private_values)
                   for path in out.glob('*.log'))
        tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0')
        assert all(not any(value.encode() in (ROOT / name).read_bytes() for value in private_values)
                   for name in tracked if name and (ROOT / name).is_file())
        proof = dict(phase=args.phase, nonce=m['nonce'], head=m['head'], origin=m['origin'],
                     db_identity=True, least_privilege=True, api_worker_file_identity=True,
                     original649=True, no_demo_notice=True, no_precreated_analysis=True,
                     roles=4, namespaced_session=True, other_cookie_rejected=True,
                     scope_and_download_guards=True, persisted_file_digest=probe['digest'],
                     no_private_values_in_logs_or_git=True, external_ai_not_configured=4,
                     tls_ca_sha256=sha256(ca.read_bytes()).hexdigest())
        write(out / ('evidence/preflight-' + args.phase + '.json'), proof)
        print('OWN_LOOPBACK_PREFLIGHT_PASS ' + args.phase + ' ' + m['nonce'])
    finally:
        for client in clients.values():
            try:
                if client.cookies.get('datco_uat_' + m['nonce']):
                    client.post('/api/notice/session/logout')
            except httpx.HTTPError:
                pass
            client.close()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('OWN_PREFLIGHT_FAILED: ' + type(error).__name__ + '; inspect protected evidence', file=sys.stderr)
        sys.exit(1)
