"""Gold expectations for bounded published-solution retrieval; synthetic sources only."""
from copy import deepcopy
import pytest
from app.capability import recommendations as R
from test_solution_recommendations import catalog, context


def offered_catalog():
    records, features = catalog()
    # Keep attendance and payroll distinct: sharing the HR domain does not prove
    # that a payroll-only function solves attendance requirements.
    records[2]['data']['description'] = '직원 근태 휴가 현황'
    records[2]['data']['problems'] = ['직원 근태 휴가 현황']
    features['TEST_REVISION_3']['data']['description'] = '직원 근태 휴가 현황'
    for number, name, problem, feature_name, system in (
        (6, 'TEST 품질 솔루션', '검사 기록과 불량 현황 조회', '불량 현황 조회', 'TEST_QMS'),
        (7, 'TEST 인사 급여 솔루션', '급여 계산과 임금 명세', '급여 계산', 'TEST_PAYROLL'),
    ):
        rid = 'TEST_REVISION_' + str(number)
        features[rid] = dict(id=rid, data=dict(feature_id='DMP-' + str(number).zfill(16),
            system=system, feature_group='TEST', name=feature_name, description=problem))
        records.append(dict(id='TEST_CAP_' + str(number), version_id='TEST_CAP_VERSION_' + str(number),
            current_ordinal=1, search_reasons=[], data=dict(service=name, description=problem,
                problems=[problem], functions=[dict(revision_id=rid, role=feature_name)],
                scope=feature_name, conditions=['TEST 적용조건'], prerequisites=['TEST 원천 데이터'],
                exclusions=['TEST 자동 인과 확정 제외'], evidence_note='SYNTHETIC_TEST_ONLY')))
    return records, features


# id, original requirement, extra structured fields, exact expected published
# Capability IDs, unresolved demand IDs.
GOLD = (
    ('G01_PRODUCTION', '제조 현장의 생산 작업 실적을 수기로 기록합니다.', {}, [2], []),
    ('G02_QUALITY', '검사 기록과 불량 현황을 확인하기 어렵습니다.', {}, [6], []),
    ('G03_LOGISTICS', '입출고 수량이 실제 재고와 다릅니다.', {}, [1], []),
    ('G04_HR', '서비스 기업의 출퇴근 근태 기록을 통합합니다.', {}, [3], []),
    ('G05_ACCOUNTING', '회계 전표 입력과 결산 업무가 중복됩니다.', {}, [4], []),
    ('G06_COLLABORATION', '종이 문서의 기안 결재 이력을 검색하고 싶습니다.', {}, [5], []),
    ('G07_PAYROLL_SEPARATE', '급여 계산과 임금 명세를 확인하고 싶습니다.', {}, [7], []),
    ('G08_COMPOSITE_GAP', '재고 현황과 전자결재 문서 이력을 함께 개선합니다.',
        {'required_functions':'의료 영상의 질환 진단 기능'}, [1, 5], ['improvement:required_functions']),
    ('G09_OUTSIDE_CATALOG', '의료 영상의 질환 진단 기능이 필요합니다.', {}, [], ['improvement:as_is']),
    ('G10_GENERIC', '전반적인 개선과 확인이 필요합니다.', {}, [], ['improvement:as_is']),
    ('G11_ALL_EXCLUDED', '제조 품질 물류 인사 회계 협업 업무는 이번 범위에서 제외합니다.',
        {}, [], ['improvement:as_is']),
    ('G12_EXCLUSION_ONLY', '재고 관리는 불필요합니다.', {}, [], ['improvement:as_is']),
    ('G13_EXCLUDE_THEN_NEED', '재고 관리는 필요 없고 회계 전표 결산을 개선합니다.', {}, [4], []),
    ('G14_HR_SUBSCOPE', '근태가 아니라 급여 계산을 개선합니다.', {}, [7], []),
    ('G15_QUALITY_PARTIAL', '불량의 자동 원인 분석은 제외하고 불량 현황 조회를 개선합니다.',
        {}, [6], []),
    ('G16_ABSENT_CURRENT_SYSTEM', '현재 시스템이 없어서 재고 현황 조회가 필요합니다.', {}, [1], []),
    ('G17_GENERIC_TERMS', '업무 관리 기능 정보의 개선과 확인을 원합니다.', {}, [], ['improvement:as_is']),
    ('G18_CONSTRAINT_EXCLUSION', '재고 차이가 발생합니다.', {'constraints':'재고 업무는 이번 구축에서 제외합니다.'},
        [], ['improvement:as_is']),
    ('G19_IRRELEVANT_PAYROLL', '급여와 무관하며 근태 기록을 통합하고 싶습니다.', {}, [3], []),
    ('G20_NO_UNOFFERED_HR', '인사평가 추천과 면접 영상 진단이 필요합니다.', {}, [], ['improvement:as_is']),
    ('G21_KNOWN_SYNONYM', '출퇴근 기록과 휴가 현황을 조회하고 싶습니다.', {}, [3], []),
    ('G22_ONLY_EXCLUDED_DOMAIN', '회계 전표는 검토하지 않습니다.', {}, [], ['improvement:as_is']),
    ('G23_PRODUCTION_QUALITY', '생산 작업 실적과 품질 검사 불량 현황을 함께 검토합니다.', {}, [2, 6], []),
)


def evaluate(case):
    identifier, text, fields, expected, expected_uncovered = case
    records, features = offered_catalog()
    demands, candidates, uncovered = R.retrieve(context(text, **fields), records, features.__getitem__)
    return dict(id=identifier, expected=['TEST_CAP_' + str(number) for number in expected],
        actual=[candidate['id'] for candidate in candidates],
        expected_uncovered=expected_uncovered, actual_uncovered=uncovered,
        candidates=candidates, demands=demands)


@pytest.mark.parametrize('case', GOLD, ids=[case[0] for case in GOLD])
def test_gold_solution_candidates_exact_scope_and_unsupported_demands(case):
    result = evaluate(case)
    assert result['actual'] == result['expected']
    assert result['actual_uncovered'] == result['expected_uncovered']
    for candidate in result['candidates']:
        assert candidate['reasons'] and candidate['version_id'] and candidate['limitations']
        assert candidate['matched_features'], 'An offered source function must support the retrieval'
        assert all(feature['revision_id'].startswith('TEST_REVISION_') for feature in candidate['matched_features'])
        assert 'score' not in candidate and 'FIT' not in str(candidate.keys())


def test_gold_composite_is_candidate_evidence_not_a_claim_of_complete_solution():
    result = evaluate(next(case for case in GOLD if case[0]=='G08_COMPOSITE_GAP'))
    assert len(result['candidates']) == 2
    assert result['actual_uncovered'] == ['improvement:required_functions']
    assert all('적합성 확정' in candidate['limitations'][0] for candidate in result['candidates'])
    assert all(demand['evidence'] for demand in result['demands'])


def test_marketing_label_cannot_cover_an_unoffered_function_in_a_composite():
    records, features = offered_catalog()
    records[0]['data']['description'] += ' 의료 영상 질환 진단 기능'
    demands, candidates, uncovered = R.retrieve(
        context('재고 현황 조회', required_functions='의료 영상 질환 진단 기능'),
        records, features.__getitem__)
    assert [candidate['id'] for candidate in candidates] == ['TEST_CAP_1']
    assert candidates[0]['demand_ids'] == ['improvement:as_is']
    assert uncovered == ['improvement:required_functions']
    assert candidates[0]['matched_features'][0]['revision_id'] == 'TEST_REVISION_1'
