from dataclasses import replace
import pytest
from app.capability.comparison import ConfirmedFact, ReviewedCondition, ComparisonInputs, compare
from app.notice.domain import Denied

@pytest.fixture
def inputs():
    fact=ConfirmedFact('fact-v1','company-a','site-a','type','MANUFACTURING','fact-review',('fact-evidence',),True,True,'2026-01-01')
    condition=ReviewedCondition('rv','item','type','NOT_IN',('MANUFACTURING',),'semantic-review','location',True,True,'2026-10-14')
    notice={'requirement_version_id':'rv','current_valid':True,'items':[{'id':'item','kind':'ELIGIBILITY_REQUIREMENT',
        'content':'TEST original clause','review':{'outcome':'CONFIRM','official_verified':True},'evidence':{'id':'location','text':'TEST original clause'}}]}
    return fact,condition,notice

def evaluate(inputs,fact=None,condition=None,notice=None):
    f,c,n=inputs
    return compare(ComparisonInputs((fact or f,),(condition or c,)), 'company-a','site-a',notice or n)

def test_confirmed_conflict_records_both_evidence_and_versions(inputs):
    result=evaluate(inputs)
    assert result['fit']=='MISMATCH'
    r=result['conditions'][0]
    assert r['status']=='CONFIRMED_CONFLICT' and r['fact_version_ids']==['fact-v1']
    assert r['requirement_version_id']=='rv' and r['fact_evidence_refs']==['fact-evidence']
    assert r['notice_evidence']['id']=='location' and r['condition_review_id']=='semantic-review'

@pytest.mark.parametrize('change',[{'confirmed':False},{'confirmed':'false'},{'current_valid':False},{'review_id':''},{'evidence_refs':()},
    {'valid_from':'2027-01-01'},{'valid_until':'2026-10-13'},{'valid_from':'not-date'},{'value':''},{'evidence_refs':('',)}])
def test_invalid_fact_never_proves_conflict(inputs,change):
    r=evaluate(inputs,fact=replace(inputs[0],**change))
    assert r['fit']=='NEED_MORE_INFO' and r['conditions'][0]['status']=='UNKNOWN'

@pytest.mark.parametrize('change',[{'reviewed':False},{'reviewed':'false'},{'current_valid':False},{'review_id':''},{'evidence_id':'other'},
    {'requirement_version_id':'older'},{'item_id':'other'},{'operator':'TEXT_SIMILARITY'},{'as_of':'not-date'},{'values':()}])
def test_invalid_condition_never_proves_conflict(inputs,change):
    r=evaluate(inputs,condition=replace(inputs[1],**change))
    assert r['fit']=='NEED_MORE_INFO' and r['conditions'][0]['status']=='UNKNOWN'

@pytest.mark.parametrize('operator,value,status',[('NOT_IN','SERVICE','CONFIRMED_SATISFIED'),('IN','MANUFACTURING','CONFIRMED_SATISFIED'),('IN','SERVICE','CONFIRMED_CONFLICT')])
def test_exact_code_membership(inputs,operator,value,status):
    r=evaluate(inputs,fact=replace(inputs[0],value=value),condition=replace(inputs[1],operator=operator))
    assert r['conditions'][0]['status']==status
    assert r['fit']!='FIT'  # Supplier/service/support completeness has not been established.

@pytest.mark.parametrize('scope',[{'company_id':'other'},{'site_id':'other'}])
def test_other_scope_facts_denied(inputs,scope):
    with pytest.raises(Denied) as error:evaluate(inputs,fact=replace(inputs[0],**scope))
    assert error.value.status==404

def test_duplicate_condition_and_conflicting_facts_are_unknown(inputs):
    f,c,n=inputs
    for i in [ComparisonInputs((f,),(c,c)),ComparisonInputs((f,replace(f,version_id='v2',value='SERVICE')),(c,))]:
        r=compare(i,'company-a','site-a',n)
        assert r['fit']=='NEED_MORE_INFO' and all(x['status']=='UNKNOWN' for x in r['conditions'])

def test_unknown_notice_and_empty_input(inputs):
    f,c,n=inputs
    n=dict(n,current_valid=False)
    assert evaluate(inputs,notice=n)['fit']=='NEED_MORE_INFO'
    r=compare(ComparisonInputs(),'company-a','site-a',inputs[2])
    assert r['conditions'][0]['status']=='UNKNOWN' and not r['opposing_evidence']

def test_optional_conflict_not_promoted_to_whole_match(inputs):
    assert evaluate(inputs,condition=replace(inputs[1],mandatory=False))['fit']=='NEED_MORE_INFO'


def test_no_adapter_does_not_interpret_confirmed_original_text(inputs):
    from app.capability.comparison import read_comparison_inputs
    empty=read_comparison_inputs(object(),None,{},inputs[2])
    assert empty==ComparisonInputs()
    assert compare(empty,'company-a','site-a',inputs[2])['fit']=='NEED_MORE_INFO'


def test_invalid_adapter_response_is_rejected(inputs):
    from app.capability.comparison import read_comparison_inputs
    class Invalid:
        def read_comparison_inputs(self,*args):return {'confirmed':True}
    with pytest.raises(Denied):read_comparison_inputs(Invalid(),None,{},inputs[2])
