"""Real isolated API/DB regression for versioned MVP documents and compositions."""
from copy import deepcopy
import io
import zipfile
import pytest
from pypdf import PdfReader
from test_proposal_production import env, create
from proposal_fixture import completions

pytestmark = pytest.mark.integration


def key(e):
    return e.nonce()


def test_legacy_approval_and_files_survive_explicit_sixteen_section_new_version(env):
    e = env
    p, _, _ = create(e)
    old = e.call('operator', '/proposal/versions/' + p['version_id'])
    assert len(old['sections']) == 11
    e.call('operator', '/proposal/versions/' + old['id'] + '/review',
        dict(confirmed=True, note='TEST exact legacy content reviewed', idempotency_key=key(e)))
    legacy_file = e.call('operator', '/proposal/versions/' + old['id'] + '/export',
        dict(kind='DOCX', idempotency_key=key(e)))
    old_bytes = e.clients['operator'].get('/proposal/files/' + legacy_file['id'] + '/download').content
    request = e.call('operator', '/proposal/versions/' + old['id'] + '/approval', dict(idempotency_key=key(e)))
    upgrade = dict(expected_version=old['id'], title=old['title'], template_version='MVP_16',
                   sections=None, idempotency_key=key(e))
    saved = e.call('operator', '/proposal/' + p['proposal_id'] + '/versions', upgrade)
    assert e.call('operator', '/proposal/' + p['proposal_id'] + '/versions', upgrade) == saved
    latest = e.call('operator', '/proposal/versions/' + saved['version_id'])
    assert len(latest['sections']) == 16 and latest['manifest']['template_version'] == 'MVP_16'
    assert e.call('operator', '/proposal/versions/' + old['id']) == old
    assert e.clients['operator'].get('/proposal/files/' + legacy_file['id'] + '/download').content == old_bytes
    detail = e.call('operator', '/proposal/' + p['proposal_id'])
    assert next(r for r in detail['requests'] if r['id'] == request['id'])['closure_reason'] == 'SUPERSEDED'
    assert not any(r['version_id'] == latest['id'] for r in detail['content_reviews'])
    e.call('approver', '/proposal/approvals/' + request['id'] + '/decision',
        dict(outcome='APPROVE', reason='TEST old request cannot approve new version', idempotency_key=key(e)), status=409)
    e.call('operator', '/proposal/versions/' + latest['id'] + '/export', dict(kind='PDF', idempotency_key=key(e)), status=409)
    e.call('operator', '/proposal/versions/' + latest['id'] + '/review',
        dict(confirmed=True, note='TEST all sixteen sections separately reviewed', idempotency_key=key(e)))
    for kind in ('DOCX', 'PDF'):
        f = e.call('operator', '/proposal/versions/' + latest['id'] + '/export', dict(kind=kind, idempotency_key=key(e)))
        e.call('approver', '/proposal/files/' + f['id'] + '/download', status=404)
    sent = e.call('operator', '/proposal/versions/' + latest['id'] + '/approval', dict(idempotency_key=key(e)))
    e.call('approver', '/proposal/approvals/' + sent['id'] + '/decision',
        dict(outcome='APPROVE', reason='TEST exact MVP sixteen-section version reviewed', idempotency_key=key(e)))
    for f in e.call('operator', '/proposal/' + p['proposal_id'])['files']:
        if f['version_id'] == latest['id']:
            response = e.clients['approver'].get('/proposal/files/' + f['id'] + '/download')
            assert response.status_code == 200
            if f['kind'] == 'DOCX':
                text = zipfile.ZipFile(io.BytesIO(response.content)).read('word/document.xml').decode()
            else:
                text = ''.join(page.extract_text() for page in PdfReader(io.BytesIO(response.content)).pages)
            assert latest['id'] in text and all(s['heading'] in text for s in latest['sections'])
            e.call('other', '/proposal/files/' + f['id'] + '/download', status=404)


def test_multiple_solution_roles_integrations_and_partial_coverage_are_frozen(env):
    e = env
    initial = e.compose('A', ['A', 'B'])
    data = deepcopy(initial['composition_data'])
    for item in data['coverage']:
        item['status'] = 'PARTIAL'
    integration = dict(from_capability_version_id=e.caps['A']['version']['id'],
        to_capability_version_id=e.caps['B']['version']['id'],
        data='TEST item and work identifiers', workflow='TEST receipts then production review',
        prerequisites=['TEST mapping review'], uncertainty='TEST interface verification required')
    data['integrations'] = [integration]
    revised = e.call('operator', '/capability/compositions/' + initial['composition']['id'] + '/versions',
        dict(data=data, expected_version=initial['composition']['version_id'], idempotency_key=key(e)))
    old_match = e.call('operator', '/capability/matches/' + initial['candidate']['candidate_id'])
    assert not old_match['current_valid']
    n = initial['notice']
    result = e.call('operator', '/capability/matches', dict(composition_version_id=revised['version_id'],
        notice_id=n['notice_id'], requirement_version_id=n['requirement_version_id'], idempotency_key=key(e)))
    cid = result['candidate_id']
    e.call('operator', '/capability/matches/' + cid + '/review', dict(outcome='PROPOSABLE',
        note='TEST all source tasks reviewed', completion_items=completions(e, cid), idempotency_key=key(e)))
    p = e.call('operator', '/proposal', dict(candidate_id=cid, title='TEST integrated services',
        template_version='MVP_16', idempotency_key=key(e)))
    version = e.call('operator', '/proposal/versions/' + p['version_id'])
    assert version['manifest']['input']['composition']['integrations'] == [integration]
    assert all(item['status'] == 'PARTIAL' for item in version['manifest']['input']['composition']['coverage'])
    assert integration['workflow'] in version['sections'][7]['body']
    assert integration['data'] in version['sections'][7]['body']
    assert all(cap['version']['id'] in version['sections'][5]['body'] for cap in (e.caps['A'], e.caps['B']))


def test_recommendations_fail_closed_and_legacy_context_has_explicit_analysis_limit(env):
    e = env
    path = '/capability/improvements/TEST_IMPROVEMENT_A/recommendations'
    value = e.call('operator', path)
    assert value['analysis_basis'] == dict(run_id=None, review_ids=[])
    assert value['limitations'] and value['demands']
    e.call('other', path, status=404)
    e.call('company', path, status=403)
    e.call('admin', path, status=403)
