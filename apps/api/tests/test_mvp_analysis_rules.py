"""Synthetic business expectations: evidence, exclusions, answers and numeric contexts."""
import pytest
from app.company.improvement_rules import analyze,validate,VERSION
from app.company.improvement_language import classify_domains
from app.company.improvement_providers import AnalysisContext,execute_provider,provider_status
from app.notice.domain import Denied

def span(text,kind='IMPROVEMENT'):
    return dict(kind=kind,version_id='TEST',field='original_text',quote=text)

@pytest.mark.parametrize('text,domain',[
 ('생산실적이 수작업으로 분리 집계된다','PRODUCTION'),('불량 검사 데이터가 누락된다','QUALITY'),
 ('창고 입출고와 재고 데이터가 분리된다','LOGISTICS'),('인사 근태와 휴가 결재가 중복된다','HR'),
 ('회계 전표와 정산 입력이 중복된다','ACCOUNTING'),('문서공유와 결재가 분리된다','COLLABORATION')])
def test_business_domains_have_literal_evidence_not_service_claims(text,domain):
    sources=[span(text)];found=next(x for x in classify_domains(sources) if x['id']==domain)
    assert found['evidence']==sources and '확정 아님' in found['uncertainty']
    out,_=analyze({},sources)
    for candidate in out:validate(candidate,sources)

@pytest.mark.parametrize('text,rule',[
 ('시스템 연계는 필요 없음','R05'),('설비 도입은 제외','R05'),
 ('예산 검토는 대상이 아님','R06'),('희망 일정 검토는 제외','R07')])
def test_explicit_exclusions_are_not_missing_requirements(text,rule):
    out,diag=analyze({},[span(text)])
    assert not any(c['data']['rule_id']==rule for c in out)
    assert next(d for d in diag if d['rule']==rule)['outcome']=='NOT_APPLICABLE'

@pytest.mark.parametrize('answer,rule',[
 ('주문 처리시간은 현재 평균 25분이다','R02'),('기존 시스템은 TEST ERP','R05'),
 ('현재 엑셀로 관리한다','R05'),('예산은 5000만원','R06'),('일정은 2027년 3월 착수','R07')])
def test_explicit_equivalent_reviewed_answers_prevent_duplicate_questions(answer,rule):
    sources=[span('물류 업무 처리시간 개선 및 시스템 연계, 예산 검토, 희망 일정 검토'),span(answer,'RESPONSE')]
    out,diag=analyze({},sources)
    assert not any(c['data']['rule_id']==rule and c['data'].get('question') for c in out)
    found=next(d for d in diag if d['rule']==rule)
    assert found['outcome']=='FOUND' and found['evidence']==[sources[1]]

def test_unknown_answer_is_not_fabricated_or_asked_again():
    out,diag=analyze({},[span('물류 시스템 예산 검토'),span('예산은 미정','RESPONSE')])
    assert next(d for d in diag if d['rule']=='R06')['outcome']=='DECLARED_UNKNOWN'
    assert not any(c['data']['rule_id']=='R06' for c in out)

def test_stated_cause_remains_unconfirmed_candidate():
    sources=[span('원인 후보: 입력 누락 가능성')];out,_=analyze({},sources)
    cause=next(c for c in out if c['data']['subject']=='원인 후보')
    assert cause['data']['claim_kind']=='INFERRED' and cause['content'] in sources[0]['quote']
    validate(cause,sources)

@pytest.mark.parametrize('second,conflict',[
 ('처리시간(2026년,물류): 120초',False),('처리시간(2026년,물류): 180초',True),
 ('처리시간(2027년,물류): 180초',False),('처리시간(2026년,인사): 180초',False)])
def test_only_same_context_compatible_units_are_compared(second,conflict):
    sources=[span('처리시간(2026년,물류): 2분'),span(second)]
    out,_=analyze({},sources)
    assert bool([c for c in out if c['category']=='CONFLICT']) is conflict
    for candidate in out:validate(candidate,sources)

@pytest.mark.parametrize('name',['GPT','GEMINI','CLAUDE','GROK'])
def test_unconfigured_provider_is_denied_before_any_network_or_analysis(name,monkeypatch):
    import urllib.request
    monkeypatch.setattr(urllib.request,'urlopen',lambda *a,**k:pytest.fail('EXTERNAL_NETWORK_ATTEMPT'))
    with pytest.raises(Denied) as error:execute_provider(name,AnalysisContext('C','V','a'*64),{},[])
    assert error.value.reason=='ANALYSIS_PROVIDER_NOT_CONFIGURED'
    assert next(p for p in provider_status()['providers'] if p['id']==name)['status']=='NOT_CONFIGURED'

def test_rule_result_retains_exact_context_and_unreviewed_status():
    context=AnalysisContext('TEST_C','TEST_V','a'*64)
    result=execute_provider('RULE',context,{},[span('인사 근태 기록이 누락된다')])
    assert result.context==context and result.provider_version==VERSION
    assert result.structure['review_status']=='UNREVIEWED_CANDIDATES'
    assert result.structure['cause_candidates']==[]

@pytest.mark.parametrize('target,field',[
    ('목표: 처리시간 5분','goal'),
    ('처리시간 5분으로 단축 희망','to_be'),
    ('예상 처리시간 5분','original_text')])
def test_desired_or_predicted_numbers_are_not_observed_measurement_baselines(target,field):
    wanted=dict(span(target),field=field)
    sources=[span('업무 처리시간 개선 필요'),wanted]
    out,diagnostics=analyze({},sources)
    candidate=next(c for c in out if c['data']['rule_id']=='R02')
    assert candidate['category']=='MISSING_INFORMATION'
    assert candidate['data']['evidence']==[sources[0]]
    assert next(d for d in diagnostics if d['rule']=='R02')['outcome']=='NOT_FOUND_IN_SCOPE'


def test_mixed_goal_and_actual_lines_keep_the_exact_actual_source():
    source=span('목표: 처리시간 5분\\n현재 처리시간은 2026년 평균 25분')
    out,diagnostics=analyze({},[span('업무 처리시간 개선 필요'),source])
    assert not any(c['data']['rule_id']=='R02' for c in out)
    assert next(d for d in diagnostics if d['rule']=='R02')['evidence']==[source]

def test_external_provider_is_denied_before_injected_local_rule_callback():
    def forbidden(*args,**kwargs):
        pytest.fail('RULE_CALLBACK_MUST_NOT_RUN_FOR_EXTERNAL_PROVIDER')
    with pytest.raises(Denied,match='ANALYSIS_PROVIDER_NOT_CONFIGURED'):
        execute_provider('GPT',AnalysisContext('C','V','a'*64),{},[],rule_analyzer=forbidden)

# Gold expectations are business cases, not generated from regex or provider output.
GOLD_CASES=[
 ('PRODUCTION','생산 업무 처리시간 측정이 필요하다.',{'R02','R04'}),
 ('QUALITY','품질 불량 검사 결과를 수기 집계한다.',{'R02'}),
 ('LOGISTICS','창고 입출고 업무 처리시간을 줄여야 한다.',{'R02','R04'}),
 ('HR','인사 근태 업무의 중복 입력을 없애려 한다.',{'R04'}),
 ('ACCOUNTING','회계 전표 입력 오류가 발생한다.',set()),
 ('COLLABORATION','협업 전자결재 업무의 승인 처리가 지연된다.',{'R04'}),
]

@pytest.mark.parametrize('domain,current,questions',GOLD_CASES)
def test_business_gold_question_sets_and_source_grounding(domain,current,questions):
    data=dict(as_is=current,to_be='등록한 기록을 조회한다.')
    sources=[dict(span(value),field=field) for field,value in data.items()]
    result=execute_provider('RULE',AnalysisContext('TEST','TEST_V','a'*64),data,sources)
    assert {c['data']['rule_id'] for c in result.candidates if c['category']=='MISSING_INFORMATION'}==questions
    assert domain in {d['id'] for d in result.structure['domains']}
    assert result.structure['cause_candidates']==[]
    for candidate in result.candidates:
        validate(candidate,sources)
        assert candidate['data']['rule_id'] in {'R01','R02','R03','R04','R05','R06','R07','R08'}
        assert candidate['data']['claim_kind']!='CONFIRMED_FACT'


@pytest.mark.parametrize("answer", [
    "예산은 미정이며 일정도 미정입니다.",
    "예산도 아직 미정이고 일정은 미확정입니다.",
    "예산과 일정은 미정입니다.",
])
def test_budget_and_schedule_declared_unknown_are_answers_with_common_particles(answer):
    sources=[span("시스템 구축 예산 및 희망 일정 검토"),dict(span(answer),field="constraints")]
    out,diagnostics=analyze({},sources)
    for rule in ("R06","R07"):
        assert next(d["outcome"] for d in diagnostics if d["rule"]==rule)=="DECLARED_UNKNOWN"
        assert not any(c["data"]["rule_id"]==rule for c in out)
    assert not any(c["data"]["claim_kind"]=="CONFIRMED_FACT" for c in out)


def test_unknown_schedule_does_not_reclassify_an_explicit_budget_amount_as_unknown():
    sources=[span("예산과 일정 검토"),dict(span("예산은 3000만원이며 일정은 아직 미정입니다."),field="constraints")]
    out,diagnostics=analyze({},sources)
    assert next(d["outcome"] for d in diagnostics if d["rule"]=="R06")=="FOUND"
    assert next(d["outcome"] for d in diagnostics if d["rule"]=="R07")=="DECLARED_UNKNOWN"


def test_current_accounting_program_answer_is_not_repeated():
    sources=[span("업무 시스템 개선"),dict(span("기존 회계 프로그램은 유지합니다."),field="constraints")]
    out,diagnostics=analyze({},sources)
    assert next(d["outcome"] for d in diagnostics if d["rule"]=="R05")=="FOUND"
    assert not any(c["category"]=="MISSING_INFORMATION" and c["data"]["rule_id"]=="R05" for c in out)


def test_known_current_program_and_explicit_unresolved_linkage_remain_distinct():
    known=dict(span("기존 회계 프로그램은 유지합니다."),field="constraints")
    unresolved=dict(span("실제 시스템 연계 방식은 추가 확인이 필요합니다."),field="constraints")
    sources=[span("업무 시스템 개선"),known,unresolved]
    out,diagnostics=analyze({},sources)
    linkage=next(c for c in out if c["category"]=="MISSING_INFORMATION" and c["data"]["rule_id"]=="R05")
    assert linkage["data"]["assessment"]=="DECLARED_UNKNOWN"
    assert linkage["data"]["evidence"]==[unresolved]
    assert linkage["data"]["claim_kind"]=="DIRECT_SOURCE"
    assert "연계 대상·방식·제약만" in linkage["data"]["question"]
    assert next(d["outcome"] for d in diagnostics if d["rule"]=="R05")=="DECLARED_UNKNOWN"
    assert any(c["data"]["subject"]=="constraints" and c["content"]==known["quote"] for c in out)
    validate(linkage,sources)


def test_excluded_equipment_linkage_is_not_reopened_as_unknown_requirement():
    sources=[dict(span("신규 센서 및 생산설비 연계는 제외합니다."),field="constraints")]
    out,diagnostics=analyze({},sources)
    assert next(d["outcome"] for d in diagnostics if d["rule"]=="R05")=="NOT_APPLICABLE"
    assert not any(c["category"]=="MISSING_INFORMATION" and c["data"]["rule_id"]=="R05" for c in out)
