"""Synthetic real-API/Worker lineage, preserving all existing human decision gates.

Requires the runner-owned PostgreSQL database and the additive MVP migration.
No business DB, customer material, external AI, role impersonation or seeded
analysis/review/confirmation is used.
"""
from copy import deepcopy
from hashlib import sha256
from uuid import uuid4
import pytest
from sqlalchemy import select, func
from fastapi.testclient import TestClient
from app.main import app
from app.notice.domain import Actor
from app.company.application import CompanyApplication
from app.company.improvement_analysis import ImprovementAnalysis
from app.capability.application import CapabilityApplication, fingerprint
from app.infrastructure import company_schema as C, capability_schema as K, notice_schema as N
from test_company_workflow import env, fresh, call, upload
from test_improvement_analysis import submitted, request, finish

pytestmark = pytest.mark.integration


def nonce():
    return str(uuid4())


def review(e, candidate, decision='USE_FOR_REQUEST', ordinal=None):
    return call(e, 'operator', '/company/analysis-candidates/' + candidate['id'] + '/reviews',
        dict(idempotency_key=nonce(),
             expected_review_ordinal=len(candidate['reviews']) if ordinal is None else ordinal,
             decision=decision, note='TEST exact synthetic candidate evidence reviewed'))


def version(e, vid):
    with e['factory']() as session:
        return CompanyApplication(session, e['files']).get(C.improvement_versions, vid)


def basis_current(e, target, basis, who='approver'):
    person = e['people'][who]
    with e['factory']() as session:
        a = CompanyApplication(session, e['files'])
        return ImprovementAnalysis(a).basis_current_for_company_decision(
            Actor(person['id'], person['role']), target, basis['run_id'], basis['review_ids'])


def create_reply(e, cid, vid, text, verified=True):
    item = call(e, 'operator', '/company/' + cid + '/information-requests',
        dict(title='TEST source-scoped question', message='TEST review the actual response', improvement_version_id=vid))
    call(e, 'operator', '/company/information-requests/' + item['id'] + '/send', {})
    response = call(e, 'editor', '/company/information-requests/' + item['id'] + '/responses',
        dict(message=text, file_ids=[], expected_ordinal=0, submit=True))
    checked = None
    if verified:
        checked = call(e, 'operator', '/company/information-requests/' + item['id'] + '/review',
            dict(response_id=response['id'], outcome='VERIFIED', note='TEST response reviewed, not promoted to Fact'))
    return dict(request=item, response=response, review=checked)


def prepare_source(e, run_analysis=True, review_decision='USE_FOR_REQUEST'):
    complete = dict(original_text='입출고 업무 처리시간을 수기로 기록해 재고 현황이 지연됩니다.',
        as_is='입출고 업무 처리시간을 수기로 기록해 재고 현황이 지연됩니다.',
        problem='입출고 기록과 재고 수량의 확인이 지연됩니다.',
        goal='입출고 기록을 통합하여 재고 현황을 확인하고 싶습니다.',
        to_be='입출고 기록과 재고 현황을 함께 검토합니다.',
        required_functions='입출고 기록과 재고 현황 조회')
    company, site, profile, source, values = submitted(e, complete)
    # Normal File -> Extract -> Company ACK -> Operator Fact review. The file is
    # an explicitly selected current common reference in the analysis manifest.
    file, raw = upload(e, company['id'], site['id'])
    call(e, 'operator', '/company/files/' + file['id'] + '/parse', {})
    detail = call(e, 'editor', '/company/' + company['id'])
    fact_candidate = next(c for c in detail['candidates']
        if c['mode'] == 'RULE_BASED_EXTRACTION' and c['field'] == 'company_name')
    call(e, 'editor', '/company/candidates/' + fact_candidate['id'] + '/acknowledge',
        dict(agreed=True, note='TEST company checked this exact synthetic source'))
    fact = call(e, 'operator', '/company/candidates/' + fact_candidate['id'] + '/review',
        dict(outcome='CONFIRM_NEW_VALUE', note='TEST human confirmed the synthetic file value'))['version']
    result = dict(company=company, site=site, profile=profile, source=source,
        values=dict(values, fact_version_ids=[fact['id']], evidence_ids=[fact_candidate['evidence_id']]),
        file=file, raw=raw, fact=fact)
    if run_analysis:
        request(e, source['id'])
        run = finish(e, source['id'])
        candidate = next(c for c in run['candidates']
            if c['category'] == 'STRUCTURE' and c['data'].get('subject') == 'as_is')
        accepted = review(e, candidate, decision=review_decision) if review_decision else None
        result.update(run=run, candidate=candidate, review=accepted,
            basis=dict(run_id=run['run']['id'], review_ids=[accepted['id'] if accepted else candidate['id']], source_version_id=source['id']))
    return result


def structure_and_confirm(e, item):
    source, company = item['source'], item['company']
    data = dict(item['values'], analysis_basis=item['basis'])
    structured = call(e, 'operator', '/company/' + company['id'] + '/improvements',
        dict(data=data, improvement_id=source['improvement_id'], expected_ordinal=1))
    assert structured['ordinal'] == 2 and structured['data']['analysis_basis'] == item['basis']
    # Operator review is not company acknowledgment, and cannot bypass it.
    call(e, 'operator', '/company/improvements/' + structured['id'] + '/actions',
        dict(action='CONFIRM', note='TEST missing company acknowledgement'), status=409)
    call(e, 'editor', '/company/improvements/' + structured['id'] + '/actions',
        dict(action='ACKNOWLEDGE', note='TEST company reviewed exact structured v2'))
    call(e, 'operator', '/company/improvements/' + structured['id'] + '/actions',
        dict(action='CONFIRM', note='TEST complete fields and current evidence reviewed'))
    return structured


def publish_synthetic_capability(e):
    # Only the raw feature is a fixture. The Capability is created and published
    # by the real ADMIN API with an exact source Revision and explicit TEST scope.
    with e['factory'].begin() as session:
        service = CapabilityApplication(session, e['files'])
        data = dict(feature_id='DMP-' + uuid4().hex[:16].upper(), system='SYNTHETIC_TEST_LOGISTICS',
            feature_group='TEST', name='TEST 재고 현황', description='TEST 입출고 기록과 재고 현황 조회',
            origin='SYNTHETIC_TEST_ONLY', excel_row=1, availability='SYNTHETIC_TEST_ONLY',
            availability_basis='SYNTHETIC_TEST_ONLY')
        root = service.add(K.features, external_id=data['feature_id'])
        source = service.add(K.revisions, feature_id=root['id'], ordinal=1, digest=fingerprint(data), data=data)
    cap = dict(service='TEST 발행 물류 솔루션', description='TEST 재고 현황과 입출고 기록 조회',
        functions=[dict(revision_id=source['id'], role='TEST 입출고와 재고 조회 역할')],
        problems=['재고 수량 확인 지연'], conditions=['TEST 식별자 검토'], exclusions=['TEST 자동 인과 확정 제외'],
        prerequisites=['TEST 원천 데이터 확인'], scope='TEST 입출고와 재고 현황 조회',
        evidence_note='SYNTHETIC TEST source Revision reviewed; no actual DATCO offering assertion')
    draft = call(e, 'admin', '/capability/catalog', dict(data=cap, idempotency_key=nonce()))
    published = call(e, 'admin', '/capability/catalog/' + draft['id'] + '/publish',
        dict(expected_revision=1, idempotency_key=nonce()))
    return published, source


def compose(e, item, target):
    recommendation = call(e, 'operator', '/capability/improvements/' + target['id'] + '/recommendations')
    assert recommendation['analysis_basis'] == item['basis']
    published, feature = publish_synthetic_capability(e)
    # Re-read the actual published Catalog; no recommendation or matching result is seeded.
    recommendation = call(e, 'operator', '/capability/improvements/' + target['id'] + '/recommendations')
    assert any(c['version_id'] == published['id'] for c in recommendation['candidates'])
    demand = next(d for d in recommendation['demands'] if d['id'] == 'improvement:as_is')
    data = dict(name='TEST reviewed source lineage composition', improvement_version_id=target['id'],
        capability_version_ids=[published['id']], excluded_feature_revision_ids=[],
        basis=recommendation['analysis_basis'], integrations=[],
        coverage=[dict(requirement=demand['text'], demand_id=demand['id'], evidence_refs=demand['evidence'],
            capability_version_id=published['id'], feature_revision_ids=[feature['id']],
            role='TEST map the requested view', addressed_scope='TEST 입출고·재고 조회',
            unaddressed_scope='TEST interface and mapping review remain', missing_information=['TEST mapping'],
            status='PARTIAL')], conditions=['TEST data review'], unresolved=['TEST residual interface work'])
    saved = call(e, 'operator', '/capability/compositions', dict(data=data, idempotency_key=nonce()))
    return saved, data


def test_submitted_rule_review_structured_confirmation_and_composition_preserve_two_versions(env):
    e = env
    item = prepare_source(e)
    old = version(e, item['source']['id'])
    target = structure_and_confirm(e, item)
    saved, data = compose(e, item, target)
    detail = call(e, 'operator', '/capability/compositions/' + saved['id'])
    current = detail['versions'][-1]
    assert current['improvement_version_id'] == target['id']
    assert current['data']['basis']['source_version_id'] == old['id']
    assert current['data']['basis']['run_id'] == item['run']['run']['id']
    assert current['data']['coverage'][0]['evidence_refs'][0]['version_id'] == target['id']
    assert current['data']['coverage'][0]['status'] == 'PARTIAL'
    bad = deepcopy(data)
    bad['basis']['source_version_id'] = target['id']
    call(e, 'operator', '/capability/compositions/' + saved['id'] + '/versions',
        dict(data=bad, expected_version=saved['version_id'], idempotency_key=nonce()), status=409)
    bad = deepcopy(data)
    bad['coverage'][0]['evidence_refs'][0]['version_id'] = old['id']
    call(e, 'operator', '/capability/compositions/' + saved['id'] + '/versions',
        dict(data=bad, expected_version=saved['version_id'], idempotency_key=nonce()), status=409)
    assert len(call(e, 'operator', '/capability/compositions/' + saved['id'])['versions']) == 1
    assert version(e, old['id']) == old
    assert 'analysis_basis' not in old['data']
    with e['factory']() as session:
        a = CompanyApplication(session, e['files'])
        assert a.rows(C.improvement_reviews, version_id=old['id'], outcome='SUBMIT')
        assert not a.rows(C.improvement_reviews, version_id=target['id'], outcome='SUBMIT')
        assert {r['outcome'] for r in a.rows(C.improvement_reviews, version_id=target['id'])} >= {'MANUAL_STRUCTURE', 'ACKNOWLEDGE', 'CONFIRM'}
    assert basis_current(e, target['id'], item['basis'])
    assert not basis_current(e, target['id'], item['basis'], who='other')
    assert not basis_current(e, target['id'], item['basis'], who='admin')
    call(e, 'other', '/capability/improvements/' + target['id'] + '/recommendations', status=403)


@pytest.mark.parametrize('change', ['REVIEW', 'VERIFIED_RESPONSE', 'COMPANY_INPUT', 'REANALYSIS'])
def test_changed_review_answer_company_or_run_stales_basis_without_rewriting_history(env, change):
    e = env
    item = prepare_source(e)
    target = structure_and_confirm(e, item)
    saved, data = compose(e, item, target)
    frozen_source, frozen_target = version(e, item['source']['id']), version(e, target['id'])
    manifest = deepcopy(item['run']['manifest'])
    if change == 'REVIEW':
        review(e, item['candidate'], decision='NEEDS_CHECK', ordinal=1)
    elif change == 'VERIFIED_RESPONSE':
        create_reply(e, item['company']['id'], item['source']['id'], '측정 기준: TEST 새 검토 답변의 처리시간 12분')
    elif change == 'COMPANY_INPUT':
        call(e, 'editor', '/company/' + item['company']['id'] + '/profile',
            dict(data=dict(item['profile'], overview='TEST updated company input'), expected_ordinal=1))
    else:
        request(e, item['source']['id'])
        newer = finish(e, item['source']['id'])
        assert newer['run']['id'] != item['run']['run']['id']
    assert not basis_current(e, target['id'], item['basis'])
    recommendation = call(e, 'operator', '/capability/improvements/' + target['id'] + '/recommendations')
    assert recommendation['analysis_basis']['run_id'] is None
    assert recommendation['analysis_basis']['review_ids'] == [] and recommendation['limitations']
    call(e, 'operator', '/capability/compositions/' + saved['id'] + '/versions',
        dict(data=data, expected_version=saved['version_id'], idempotency_key=nonce()), status=409)
    assert len(call(e, 'operator', '/capability/compositions/' + saved['id'])['versions']) == 1
    assert version(e, item['source']['id']) == frozen_source and version(e, target['id']) == frozen_target
    assert call(e, 'operator', '/company/analysis-runs/' + item['run']['run']['id'])['manifest'] == manifest


@pytest.mark.parametrize('forgery', ['UNREVIEWED', 'NO_REVIEW', 'SOURCE_VERSION', 'OTHER_COMPANY', 'OTHER_ROOT'])
def test_unreviewed_or_foreign_analysis_cannot_be_used_to_structure(env, forgery):
    e = env
    item = prepare_source(e, review_decision=None if forgery=='NO_REVIEW' else 'NEEDS_CHECK' if forgery=='UNREVIEWED' else 'USE_FOR_REQUEST')
    bad = deepcopy(item['basis'])
    expected = 404 if forgery=='NO_REVIEW' else 409
    if forgery in ('UNREVIEWED', 'NO_REVIEW'):
        pass
    elif forgery == 'SOURCE_VERSION':
        bad['source_version_id'] = nonce()
    elif forgery == 'OTHER_COMPANY':
        foreign = prepare_source(e)
        bad = foreign['basis']
        expected = 404
    else:
        other = call(e, 'editor', '/company/' + item['company']['id'] + '/improvements',
            dict(data=dict(item['values'], title='TEST another task in same site')))
        call(e, 'editor', '/company/improvements/' + other['id'] + '/actions',
            dict(action='SUBMIT', note='TEST another actual task submitted'))
        request(e, other['id'])
        other_run = finish(e, other['id'])
        other_candidate = next(c for c in other_run['candidates'] if c['category'] == 'STRUCTURE')
        other_review = review(e, other_candidate)
        bad = dict(run_id=other_run['run']['id'], review_ids=[other_review['id']], source_version_id=other['id'])
        expected = 404
    call(e, 'operator', '/company/' + item['company']['id'] + '/improvements',
        dict(data=dict(item['values'], analysis_basis=bad), improvement_id=item['source']['improvement_id'],
             expected_ordinal=1), status=expected)
    with e['factory']() as session:
        a = CompanyApplication(session, e['files'])
        assert len(a.rows(C.improvement_versions, improvement_id=item['source']['improvement_id'])) == 1
    call(e, 'editor', '/company/' + item['company']['id'] + '/improvements',
        dict(data=dict(item['values'], analysis_basis=item['basis']), improvement_id=item['source']['improvement_id'],
             expected_ordinal=1), status=403)


def test_new_site_version_does_not_relabel_old_analysis_as_current_structuring_input(env):
    e = env
    item = prepare_source(e)
    call(e, 'editor', '/company/' + item['company']['id'] + '/sites',
        dict(data=dict(name='TEST revised site', address='TEST changed address'),
             site_id=item['site']['id'], expected_ordinal=1))
    call(e, 'operator', '/company/' + item['company']['id'] + '/improvements',
        dict(data=dict(item['values'], analysis_basis=item['basis']), improvement_id=item['source']['improvement_id'],
             expected_ordinal=1), status=409)


def test_verified_response_scope_digest_and_question_resolution_without_fact_promotion(env):
    e = env
    item = prepare_source(e, run_analysis=False)
    cid, vid = item['company']['id'], item['source']['id']
    exact = create_reply(e, cid, vid, '측정 기준: TEST_EXACT_VERIFIED 처리시간 현재값 12분')
    common = create_reply(e, cid, None, '기존 시스템: TEST_COMMON_VERIFIED ERP')
    pending = create_reply(e, cid, vid, 'TEST_UNVERIFIED_RESPONSE_MUST_NOT_ENTER', verified=False)
    other = call(e, 'editor', '/company/' + cid + '/improvements',
        dict(data=dict(item['values'], title='TEST separate improvement')))
    call(e, 'editor', '/company/improvements/' + other['id'] + '/actions',
        dict(action='SUBMIT', note='TEST separate target'))
    other_task = create_reply(e, cid, other['id'], 'TEST_OTHER_TASK_RESPONSE_MUST_NOT_ENTER')
    foreign_company, foreign_site, _ = fresh(e)
    foreign = create_reply(e, foreign_company['id'], None, 'TEST_FOREIGN_RESPONSE_MUST_NOT_ENTER')
    with e['factory']() as session:
        before_facts = session.scalar(select(func.count()).select_from(C.fact_versions).join(C.facts, C.fact_versions.c.fact_id == C.facts.c.id).where(C.facts.c.company_id == cid))
    request(e, vid)
    run = finish(e, vid)
    selected = run['manifest']['data']['reviewed_answers']
    assert {row['response_id'] for row in selected} == {exact['response']['id'], common['response']['id']}
    for value in (exact, common):
        source = next(row for row in selected if row['response_id'] == value['response']['id'])
        assert source['request_id'] == value['request']['id'] and source['review_id'] == value['review']['id']
        assert source['message_digest'] == sha256(value['response']['message'].encode()).hexdigest()
    assert not {pending['response']['id'], other_task['response']['id'], foreign['response']['id']} & {row['response_id'] for row in selected}
    rule = next(rule for rule in run['diagnostics']['rules'] if rule['rule'] == 'R02')
    assert rule['outcome'] == 'FOUND'
    evidence = next(source for source in rule['evidence'] if source['kind'] == 'RESPONSE')
    assert evidence['request_id'] == exact['request']['id']
    assert evidence['response_id'] == exact['response']['id'] and evidence['review_id'] == exact['review']['id']
    assert exact['response']['message'] == evidence['quote']
    assert not any(c['category'] == 'MISSING_INFORMATION' and c['data']['rule_id'] == 'R02' for c in run['candidates'])
    assert all(sentinel not in str(run) for sentinel in ('TEST_UNVERIFIED_RESPONSE_MUST_NOT_ENTER',
        'TEST_OTHER_TASK_RESPONSE_MUST_NOT_ENTER', 'TEST_FOREIGN_RESPONSE_MUST_NOT_ENTER'))
    with e['factory']() as session:
        after_facts = session.scalar(select(func.count()).select_from(C.fact_versions).join(C.facts, C.fact_versions.c.fact_id == C.facts.c.id).where(C.facts.c.company_id == cid))
    assert after_facts == before_facts


def test_provider_status_and_not_configured_direct_requests_create_no_jobs(env):
    e = env
    item = prepare_source(e, run_analysis=False)
    registry = call(e, 'operator', '/company/analysis/providers')
    assert registry['default'] == 'RULE'
    statuses = {p['id']: p for p in registry['providers']}
    assert set(statuses) == {'RULE', 'GPT', 'GEMINI', 'CLAUDE', 'GROK'}
    assert statuses['RULE']['status'] == 'AVAILABLE' and statuses['RULE']['external'] is False
    assert all(statuses[name]['status'] == 'NOT_CONFIGURED' and statuses[name]['version'] is None
               for name in ('GPT', 'GEMINI', 'CLAUDE', 'GROK'))
    for who in ('editor', 'approver', 'admin', 'other'):
        call(e, who, '/company/analysis/providers', status=403)
    with TestClient(app) as client:
        assert client.get('/company/analysis/providers').status_code == 401
    source = call(e, 'operator', '/company/improvements/' + item['source']['id'] + '/analysis-inputs')
    path = '/company/improvements/' + item['source']['id'] + '/analysis-jobs'
    with e['factory']() as session:
        before = session.scalar(select(func.count()).select_from(N.jobs))
    for provider in ('GPT', 'GEMINI', 'CLAUDE', 'GROK'):
        for mode in ('MANUAL', 'ENSURE'):
            response = call(e, 'operator', path, dict(provider=provider, mode=mode, idempotency_key=nonce(),
                selection_token=source['selection_token'], excluded_files={}, common_file_ids=[], reason='TEST explicit unsupported request'), status=409)
            assert response['reason'] == 'ANALYSIS_PROVIDER_NOT_CONFIGURED'
    call(e, 'operator', path, dict(provider='UNVERIFIED_PROVIDER', idempotency_key=nonce(),
        selection_token=source['selection_token'], reason='TEST unknown provider'), status=422)
    with e['factory']() as session:
        assert session.scalar(select(func.count()).select_from(N.jobs)) == before
    job, body, _ = request(e, item['source']['id'])
    assert call(e, 'operator', path, dict(body, provider='RULE'), status=202)['id'] == job['id']
    result = finish(e, item['source']['id'])
    assert result['run']['provider_version'].startswith('improvement-rules-')
    assert result['manifest']['data']['provider'] == 'RULE'


def test_new_lineage_history_refuses_migration_downgrade_without_changing_records(env):
    from alembic.operations import Operations
    from alembic.migration import MigrationContext
    from sqlalchemy import text
    from v14_migration_chain import load
    from app.infrastructure import improvement_schema as I

    e = env
    item = prepare_source(e)
    target = structure_and_confirm(e, item)
    frozen_target = version(e, target['id'])
    # The operation is confined to the runner-owned DB transaction. The expected
    # guard raises before DDL; even a missing guard causes this transaction to roll
    # back when pytest detects the missing RuntimeError.
    with e['factory'].begin() as session:
        connection = session.connection()
        before_function = connection.scalar(text("SELECT pg_get_functiondef('validate_improvement_lineage()'::regprocedure)"))
        tables = (C.improvement_versions, I.manifests, I.details, N.candidates, N.reviews)
        counts = [session.scalar(select(func.count()).select_from(table)) for table in tables]
        with Operations.context(MigrationContext.configure(connection)):
            with pytest.raises(RuntimeError, match='MVP_ANALYSIS_HISTORY_EXISTS_NO_DATA_DELETED'):
                load('fg31m0012026_mvp_analysis_lineage.py').downgrade()
        assert connection.scalar(text("SELECT pg_get_functiondef('validate_improvement_lineage()'::regprocedure)")) == before_function
        assert [session.scalar(select(func.count()).select_from(table)) for table in tables] == counts
        assert connection.scalar(text("SELECT EXISTS(SELECT 1 FROM pg_trigger WHERE tgname='ck_mvp_structure_basis' AND NOT tgisinternal)"))
    assert version(e, target['id']) == frozen_target
