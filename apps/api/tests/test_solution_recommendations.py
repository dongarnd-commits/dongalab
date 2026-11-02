"""Synthetic expected-result evaluation; no real source data, DB or AI."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from app.capability import recommendations as R
from app.notice.domain import Denied


def context(text, **fields):
    return dict(company_id='TEST_COMPANY', improvement_version_id='TEST_VERSION',
                original_text=text, structured=dict(as_is=text, **fields))


def catalog():
    records, features = [], {}
    for i, (name, problem, feature_name, system) in enumerate((
        ('TEST 물류 솔루션', '재고 입출고 수량 불일치', '재고현황', 'TEST_ERP_LOGISTICS'),
        ('TEST 제조 솔루션', '생산 작업실적 수기 기록', '작업실적등록', 'TEST_MES'),
        ('TEST 인사 솔루션', '직원 근태 휴가 급여 확인', '근태등록', 'TEST_HR'),
        ('TEST 회계 솔루션', '전표 결산 회계 확인', '전표등록', 'TEST_ACCOUNTING'),
        ('TEST 협업 솔루션', '문서 기안 결재 자료 검색', '전자결재', 'TEST_GROUPWARE'),
    ), 1):
        rid = 'TEST_REVISION_' + str(i)
        features[rid] = dict(id=rid, data=dict(feature_id='DMP-' + str(i).zfill(16),
            system=system, feature_group='TEST', name=feature_name, description=problem))
        records.append(dict(id='TEST_CAP_' + str(i), version_id='TEST_CAP_VERSION_' + str(i),
            current_ordinal=1, search_reasons=[], data=dict(service=name, description=problem,
                problems=[problem], functions=[dict(revision_id=rid, role=feature_name)],
                scope=feature_name, conditions=['TEST 적용조건'], prerequisites=['TEST 환경 확인'],
                exclusions=['TEST 원천 밖 기능 제외'], evidence_note='SYNTHETIC_TEST_ONLY')))
    return records, features


@pytest.mark.parametrize('text,expected', [
    ('창고 입출고 수량을 수기로 적어 재고가 맞지 않고 차이가 발생합니다.', [1]),
    ('공정별 생산 실적 기록을 정리하고 싶습니다.', [2]),
    ('서비스 기업의 직원 근태와 휴가 현황이 분산되어 있습니다.', [3]),
    ('회계 전표의 확인과 결산 업무가 중복됩니다.', [4]),
    ('전자결재 문서 기안과 자료 검색을 개선하고 싶습니다.', [5]),
    ('재고 관리와 문서 결재를 함께 개선하고 싶습니다.', [1, 5]),
    ('의료 영상 진단 정확도가 낮습니다.', []),
    ('재고 관리는 제외하고 전자결재 문서 기안을 개선합니다.', [5]),
])
def test_expected_offered_solutions_and_unrelated_candidates(text, expected):
    records, features = catalog()
    demands, results, uncovered = R.retrieve(context(text), records, features.__getitem__)
    assert [r['id'] for r in results] == ['TEST_CAP_' + str(i) for i in expected]
    assert all(r['reasons'] and r['demand_ids'] for r in results)
    for result in results:
        assert all(f['revision_id'] in features for f in result['matched_features'])
        assert result['version_id'] and result['limitations']
    assert bool(uncovered) is (not bool(expected))
    assert demands[0]['evidence'][0]['quote'] == text


def test_unpublished_is_never_offered_and_constraints_are_not_needs():
    records, features = catalog()
    records[0]['version_id'] = None
    _, results, _ = R.retrieve(context('재고 불일치', constraints='문서 결재는 제외'), records, features.__getitem__)
    assert results == []


def test_review_is_a_candidate_not_a_confirmed_fact():
    reviewed = [dict(candidate_id='TEST_C', review_id='TEST_R', category='STRUCTURE',
        content='직원 휴가 기록 통합', evidence=[dict(kind='DOCUMENT', quote='직원 휴가 기록 통합')])]
    demands = R.source_demands(context('TEST unrelated'), reviewed)
    assert demands[-1]['id'] == 'analysis:TEST_C'
    assert 'Confirmed Fact' in demands[-1]['uncertainty']
    assert demands[-1]['evidence'] == reviewed[0]['evidence']


def composition():
    return dict(capability_version_ids=['TEST_A', 'TEST_B'], coverage=[dict(
        requirement='TEST demand', capability_version_id='TEST_A', feature_revision_ids=[],
        role='TEST role', addressed_scope='TEST addressed', unaddressed_scope='TEST gap',
        missing_information=[], status='PARTIAL')], integrations=[dict(
        from_capability_version_id='TEST_A', to_capability_version_id='TEST_B',
        data='TEST identifiers', workflow='TEST input then review',
        prerequisites=['TEST mapping'], uncertainty='TEST interface not confirmed')])


@pytest.mark.parametrize('mutate,reason', [
    (lambda d: d['coverage'][0].update(status='ADDRESSED'), 'INVALID_COVERAGE_STATUS'),
    (lambda d: d['coverage'][0].update(status='UNRESOLVED'), 'INVALID_COVERAGE_STATUS'),
    (lambda d: d['integrations'][0].update(to_capability_version_id='FOREIGN'), 'TARGET_VERSION_MISMATCH'),
    (lambda d: d['integrations'][0].update(to_capability_version_id='TEST_A'), 'TARGET_VERSION_MISMATCH'),
    (lambda d: d['integrations'][0].update(uncertainty='  '), 'REQUIRED_DATA_MISSING'),
    (lambda d: d['coverage'][0].update(evidence_refs=[dict(quote='invented')]), 'INVALID_ANALYSIS_BASIS'),
])
def test_wrong_coverage_or_integration_is_rejected(mutate, reason):
    data = composition()
    mutate(data)
    with pytest.raises(Denied, match=reason):
        R.validate_extensions(None, None, context('TEST demand'), data)


def test_exact_source_requirement_and_evidence_are_validated():
    data = composition()
    demand = R.source_demands(context('TEST demand'))[0]
    data['coverage'][0].update(demand_id=demand['id'], evidence_refs=demand['evidence'])
    R.validate_extensions(None, None, context('TEST demand'), data)
    data['coverage'][0]['evidence_refs'][0]['quote'] = 'invented'
    with pytest.raises(Denied, match='REQUIRED_EVIDENCE_MISSING'):
        R.validate_extensions(None, None, context('TEST demand'), data)


def test_basis_uses_latest_exact_run_and_latest_review(monkeypatch):
    current = dict(run_id='TEST_NEW_RUN', review_ids=['TEST_NEW_REVIEW'])
    reviewed = [dict(review_id='TEST_NEW_REVIEW', category='STRUCTURE', content='TEST')]
    monkeypatch.setattr(R, 'read_analysis', lambda *args: (current, reviewed, []))
    monkeypatch.setattr(R, 'authority_basis', lambda service, actor, ctx, value: dict(value, source_version_id='TEST_VERSION'))
    assert R.validate_basis(None, None, context('TEST'), current) == reviewed
    for invalid, reason in [
        (dict(run_id='TEST_OLD_RUN', review_ids=['TEST_NEW_REVIEW']), 'STALE_ANALYSIS'),
        (dict(run_id='TEST_NEW_RUN', review_ids=['TEST_OLD_REVIEW']), 'STALE_REVIEW'),
        (dict(run_id='TEST_NEW_RUN', review_ids=[]), 'INVALID_ANALYSIS_BASIS'),
        (dict(run_id='TEST_NEW_RUN', review_ids=['TEST_NEW_REVIEW'] * 2), 'INVALID_ANALYSIS_BASIS'),
    ]:
        with pytest.raises(Denied, match=reason):
            R.validate_basis(None, None, context('TEST'), invalid)


def test_legacy_payload_keeps_optional_fields_absent():
    from app.api.capability import SaveComposition
    data = composition()
    data['name'] = 'TEST combination'
    data['improvement_version_id'] = 'TEST_VERSION'
    data['capability_version_ids'] = ['a' * 36]
    data['coverage'][0]['capability_version_id'] = 'a' * 36
    for field in ('status',):
        data['coverage'][0].pop(field)
    data.pop('integrations')
    value = SaveComposition(data=data, idempotency_key='TEST').data.model_dump(exclude_unset=True)
    assert value == data


def test_scope_exclusion_overrides_mentioned_problem_and_generic_actions_do_not_recommend():
    records, features = catalog()
    _, results, uncovered = R.retrieve(
        context('재고가 맞지 않습니다.', constraints='재고 업무는 이번 구축에서 제외합니다.'),
        records, features.__getitem__)
    assert results == [] and uncovered
    _, results, _ = R.retrieve(context('업무를 확인하고 개선하고 싶습니다.'), records, features.__getitem__)
    assert results == []
