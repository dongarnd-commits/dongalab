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
