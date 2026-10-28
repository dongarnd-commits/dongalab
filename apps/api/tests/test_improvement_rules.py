"""Meaningful local rule boundaries, no DB or external services."""
import pytest
from app.company.improvement_rules import analyze,validate

def span(text,field='original_text'):return dict(kind='IMPROVEMENT',version_id='TEST',field=field,quote=text)
@pytest.mark.parametrize('text', ['일반적인 개선 의견','고객 만족 향상','TEST neutral','회계 문서 정리'])
def test_no_universal_budget_equipment_or_numeric_requirements(text):
    out,diag=analyze({},[span(text)])
    assert not any(x['category']=='MISSING_INFORMATION' for x in out)
@pytest.mark.parametrize('text,rule',[('처리시간 개선','R02'),('업무 개선','R04'),('시스템 구축','R05'),('예산 검토','R06'),('희망 일정 검토','R07')])
def test_conditional_questions_need_explicit_basis(text,rule):
    sources=[span(text)];out,diag=analyze({},sources)
    c=next(c for c in out if c['data']['rule_id']==rule)
    assert c['data']['claim_kind']=='SEARCH_NOT_FOUND' and c['data']['evidence']==sources
    validate(c,sources)
    partial,_=analyze({},sources,incomplete=True)
    assert not any(c['category']=='MISSING_INFORMATION' for c in partial)
def test_conflict_and_fabricated_quote_rejection():
    sources=[span('기존 시스템(2026,본사): TEST A'),span('기존 시스템(2026,본사): TEST B')]
    out,_=analyze({},sources);c=next(c for c in out if c['category']=='CONFLICT');assert len(c['data']['evidence'])==2
    c['data']['evidence']=[span('TEST invented')]
    with pytest.raises(ValueError,match='INVALID_ANALYSIS_EVIDENCE'):validate(c,sources)

def test_common_document_does_not_make_equipment_or_budget_mandatory():
    sources=[span('TEST neutral improvement'),dict(kind='DOCUMENT',evidence_id='TEST',inspection_id='TEST',quote='시스템 구축, 설비 도입, 예산 검토')]
    out,_=analyze({},sources)
    assert not any(c['category']=='MISSING_INFORMATION' for c in out)
