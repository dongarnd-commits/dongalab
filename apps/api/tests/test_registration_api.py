"""Real PostgreSQL/HTTP initial registration; synthetic scans only."""
from hashlib import sha256
import pytest
from sqlalchemy import select,func
from test_company_workflow import env,call
from app.infrastructure import company_schema as S
from app.core.config import get_settings
from registration_sources import scan,number
pytestmark=pytest.mark.integration

def counts(e):
    with e['factory']() as s:return tuple(s.scalar(select(func.count()).select_from(t)) for t in [S.companies,S.files,S.evidence])

def test_preview_is_editor_only_stateless_and_no_precreated_company(env):
    e=env;before=counts(e);raw=scan();headers={'Origin':get_settings().web_origin,'X-Upload-Name':'TEST-registration.pdf'}
    for who in ['operator','admin','approver']:
        assert e['clients'][who].post('/company/registration/preview',content=raw,headers=headers).status_code==403
    r=e['clients']['editor'].post('/company/registration/preview',content=raw,headers=headers);assert r.status_code==200
    result=r.json();assert result['error'] is None and result['digest']==sha256(raw).hexdigest()
    assert any(c['field']=='company_name' for c in result['candidates']);assert counts(e)==before
    assert e['clients']['editor'].post('/company/registration/preview',content=b'not a PDF',headers=headers).status_code==422
    assert counts(e)==before

def test_same_registration_guard_normalizes_and_rejects_invalid_duplicate_without_scope_grant(env):
    e=env;n=number();hyphen=n[:3]+'-'+n[3:5]+'-'+n[5:];before=counts(e)
    bad=n[:-1]+str((int(n[-1])+1)%10)
    call(e,'editor','/company',{'name':'TEST Invalid check digit','business_number':bad},status=422);assert counts(e)==before
    c=call(e,'editor','/company',{'name':'TEST Direct normalized','business_number':hyphen});d=call(e,'editor','/company/'+c['id']);assert d['inputs'][-1]['data']['business_number']==n
    for who in ['editor','other']:call(e,who,'/company',{'name':'TEST duplicate','business_number':n},status=409)
    call(e,'other','/company/'+c['id'],status=404)
    assert counts(e)[0]==before[0]+1

def test_scan_original_and_ocr_evidence_survive_registration_and_operator_read(env):
    e=env;n=number();raw=scan(n);c=call(e,'editor','/company',{'name':'TEST Human reviewed registration','business_number':n});cid=c['id'];headers={'Origin':get_settings().web_origin,'X-Upload-Name':'TEST-scan.pdf'}
    f=e['clients']['editor'].post('/company/'+cid+'/files',content=raw,headers=headers).json();assert f['digest']==sha256(raw).hexdigest()
    parsed=call(e,'editor','/company/files/'+f['id']+'/parse?registration=true',{});assert parsed['error'] is None
    d=call(e,'editor','/company/'+cid);assert d['facts']==[];assert any(x['page']==1 and x['file_id']==f['id'] and 'OCR' in x['descriptor'] for x in d['evidence'])
    assert any(x['field']=='business_number' and x['value']==n for x in d['candidates'])
    call(e,'admin','/company/'+cid+'/access',{'username':e['people']['operator']['username']})
    o=call(e,'operator','/company/'+cid)
    for key in ['company','inputs','files','evidence','candidates','facts']:assert d[key]==o[key]
    result=e['clients']['operator'].get('/company/files/'+f['id']+'/download');assert sha256(result.content).hexdigest()==f['digest']


def test_business_document_mode_actual_http_profile_linked_improvement_and_scope(env):
    from test_company_workflow import fresh
    e=env;c,site,p=fresh(e);cid=c['id'];raw='연도: 2024\n매출액: 12345\n기준기간: 2024\n단위: 원\n통화: KRW'.encode()
    headers={'Origin':get_settings().web_origin,'X-Upload-Name':'TEST-finance.txt'}
    r=e['clients']['editor'].post('/company/'+cid+'/files',content=raw,headers=headers);assert r.status_code==200;f=r.json()
    for who,status in [('other',404),('approver',403),('admin',403)]:call(e,who,'/company/files/'+f['id']+'/parse?purpose=finance',{},status=status)
    analysis=call(e,'editor','/company/files/'+f['id']+'/parse?purpose=finance',{});assert analysis['error'] is None
    assert analysis['entries']==[dict(year=2024,revenue='12345',period='2024',unit='원',currency='KRW')]
    before=call(e,'editor','/company/'+cid);assert before['inputs'][-1]['data']['financials']==p['financials'];assert before['facts']==[]
    updated={**before['inputs'][-1]['data'],'financials':analysis['entries']};call(e,'editor','/company/'+cid+'/profile',dict(data=updated,expected_ordinal=before['company']['current_ordinal']))
    after=call(e,'editor','/company/'+cid);assert after['inputs'][-1]['data']['financials']==analysis['entries'];assert after['inputs'][0]['data']['financials']==p['financials']
    ev=call(e,'editor','/company/'+cid+'/evidence',dict(file_id=f['id'],site_id=site['id'],descriptor='개선요구 첨부자료',transcription='TEST 사용자 첨부자료 연결'))
    data=dict(title='TEST 문제',site_id=site['id'],original_text='TEST As-Is\nTEST To-Be',as_is='TEST As-Is',to_be='TEST To-Be',evidence_ids=[ev['id']])
    v=call(e,'editor','/company/'+cid+'/improvements',dict(data=data));call(e,'editor','/company/improvements/'+v['id']+'/actions',dict(action='SUBMIT',note='TEST 사용자가 제출 확인'))
    d=call(e,'operator','/company/'+cid);root=next(i for i in d['improvements'] if i['id']==v['improvement_id']);assert root['state']=='SUBMITTED';assert root['versions'][-1]['data']['evidence_ids']==[ev['id']]
    assert next(x for x in d['evidence'] if x['id']==ev['id'])['file_id']==f['id'];assert sha256(e['clients']['operator'].get('/company/files/'+f['id']+'/download').content).hexdigest()==f['digest']
    call(e,'editor','/company/files/'+f['id']+'/parse?registration=true&purpose=finance',{},status=422)
