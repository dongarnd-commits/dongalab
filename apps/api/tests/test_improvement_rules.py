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

def coverage(status,origin='COMMON_REFERENCE',identifier='TEST'):
    return dict(inspection_id=identifier,status=status,origin=origin,locations=[],exclude_reason='TEST unrelated marketing image' if status=='EXCLUDED' else '')

@pytest.mark.parametrize('business',['물류 업무 처리시간 개선','서비스 업무 처리시간 개선','제조 공정 불량 개선'])
def test_excluded_common_reference_does_not_suppress_rule_questions(business):
    sources=[span(business)]
    out,diag=analyze({},sources,coverage=[coverage('COMPLETE',identifier='PDF'),coverage('EXCLUDED')])
    c=next(c for c in out if c['category']=='MISSING_INFORMATION' and c['data']['rule_id']=='R02')
    assert c['data']['assessment']=='NOT_FOUND_IN_SCOPE' and len(c['data']['search_scope'])==2
    assert c['data']['uninspected_ids']==[]
    validate(c,sources)

@pytest.mark.parametrize('status,origin',[('PARTIAL','COMMON_REFERENCE'),('FAILED','COMMON_REFERENCE'),('UNSUPPORTED','COMMON_REFERENCE'),('EXCLUDED','DIRECT_ATTACHMENT'),('NOT_INSPECTED','DIRECT_ATTACHMENT')])
def test_unread_data_yields_rule_specific_review_not_an_absence_claim(status,origin):
    sources=[span('업무 처리시간 및 시스템 연계'),dict(kind='DOCUMENT',quote='기존 시스템: TEST ERP',file_id='F')]
    out,diag=analyze({},sources,coverage=[coverage(status,origin)])
    c=next(c for c in out if c['data']['rule_id']=='R02')
    assert c['category']=='PROCESSING_LIMITATION' and c['data']['assessment']=='NEEDS_SOURCE_REVIEW'
    assert c['data']['uninspected_ids']==['TEST'] and c['data']['evidence']==[sources[0]]
    assert not any(c['data']['rule_id']=='R05' for c in out)
    assert next(d for d in diag if d['rule']=='R05')['outcome']=='FOUND'
    assert not any(c['category']=='MISSING_INFORMATION' for c in out)
    validate(c,sources)
    c['category']='MISSING_INFORMATION'
    with pytest.raises(ValueError,match='UNINSPECTED_SOURCE_IS_NOT_ABSENCE'):validate(c,sources)

def test_goal_in_direct_evidence_prevents_duplicate_question():
    sources=[span('TEST problem','as_is'),dict(kind='EVIDENCE',quote='개선 목표: TEST faster service')]
    out,diag=analyze({'as_is':'TEST problem'},sources,coverage=[coverage('FAILED')])
    assert next(d for d in diag if d['rule']=='R03')['outcome']=='FOUND'
    assert not any(c['data'].get('question') for c in out)
