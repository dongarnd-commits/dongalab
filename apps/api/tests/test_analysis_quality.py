"""Business gold regressions; synthetic only, no OCR/DB/private files/network."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import pytest
from quality_evaluator import CORPUS, evaluate_case
from app.capability.asset_solutions import generate
from app.capability.recommendations import source_demands, exclusions
from app.company.improvement_worker import fact_span
from test_asset_solutions import catalog, context

FROZEN=json.loads(CORPUS.read_text(encoding='utf-8'))


@pytest.mark.parametrize('case',FROZEN['cases'],ids=[c['id'] for c in FROZEN['cases']])
def test_frozen_development_business_gold(case):
    result=evaluate_case(case)
    assert result['passed'], result['checks']


def test_development_gold_is_identical_to_the_prechange_baseline():
    baseline=json.loads((CORPUS.parent/'analysis_quality_baseline_v1.json').read_text(encoding='utf-8'))
    assert sha256(CORPUS.read_bytes()).hexdigest()==baseline['corpus_sha256']
    assert baseline['versions']['improvement_rule']=='improvement-rules-v4'
    assert baseline['versions']['asset_rule']=='asset-solutions-v2'
    # These are assertion failures, not a claimed real-company accuracy rate.
    assert baseline['summary']['failed']==12
    assert baseline['summary']['unsupported_inputs']==1


def reviewed(subject, text, key='REVIEWED'):
    return dict(category='STRUCTURE',candidate_id=key,subject=subject,content=text,
                evidence=[dict(kind='RESPONSE',response_id='REPLY_V2',review_id='VERIFIED_V2',quote=text)])


def test_reviewed_constraint_goal_and_cause_preserve_their_business_roles():
    records=[reviewed('constraints','급여계산 제외','C'),reviewed('goal','근태 기록 조회','G'),
             reviewed('원인 후보','입력 누락 가능성','CAUSE')]
    demands=source_demands(context('근태 기록이 분리됨'),records)
    assert {d['id']:d['kind'] for d in demands}=={
        'improvement:as_is':'CURRENT_STATE','analysis:C':'CONSTRAINT','analysis:G':'GOAL'}
    assert next(d for d in demands if d['id']=='analysis:G')['evidence']==records[1]['evidence']
    assert '급여' in exclusions(context('근태 기록이 분리됨'),records)[0]


def test_reviewed_scope_exclusion_blocks_an_otherwise_relevant_source_candidate():
    result=generate(context('급여계산과 근태 기록 조회'),catalog(),
                    [reviewed('constraints','급여계산은 이번 범위에서 제외')])
    assert {f['name'] for f in result['candidates']}=={'근태등록'}
    assert any('급여계산' in clause for clause in result['limitations'])
    assert all(r['status']!='ADDRESSED' for a in result['alternatives'] for r in a['coverage'])


def test_reviewed_fact_keeps_exact_value_and_distinct_period_unit_currency():
    version=dict(id='FACT_V2',value='1,200')
    fact=dict(field='revenue',period='2027',unit='천원',currency='KRW')
    link=dict(review_id='FACT_REVIEW_V2',evidence_id='ORIGINAL_PROOF')
    original=deepcopy((version,fact,link))
    first=fact_span(version,fact,link)
    second=fact_span(version,dict(fact,period='2028',unit='원'),link)
    assert first['quote']==second['quote']=='1,200'
    assert (first['period'],first['unit'],first['currency'])==('2027','천원','KRW')
    assert (second['period'],second['unit'])==('2028','원')
    assert first['version_id']=='FACT_V2' and first['review_id']=='FACT_REVIEW_V2'
    assert first['evidence_id']=='ORIGINAL_PROOF'
    assert (version,fact,link)==original


def test_alternative_scope_uses_only_literal_registered_source_quotes():
    result=generate(context('생산 공정별 작업 실적 기록'),catalog())
    for alternative in result['alternatives']:
        for row in alternative['coverage']:
            if row['status']=='UNRESOLVED':
                continue
            selected=[c for c in result['candidates'] if c['revision_id'] in row['feature_revision_ids']]
            assert row['requirement'] in row['role']
            for candidate in selected:
                assert candidate['module_name'] in row['role']
            assert any(e['quote'] in row['addressed_scope'] for c in selected for e in c['evidence'])
            assert '아직 검증하지 않았습니다' in row['unaddressed_scope']

