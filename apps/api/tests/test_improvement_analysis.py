"""Actual isolated PostgreSQL, API and production worker; synthetic inputs only."""
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from sqlalchemy import update, text
from sqlalchemy.exc import IntegrityError, ProgrammingError
import pytest
from test_company_workflow import env, fresh, call, upload
from app.company.improvement_worker import process_improvement_one
from app.infrastructure import notice_schema as N, improvement_schema as S
pytestmark=pytest.mark.integration

@pytest.mark.parametrize('path',['/company/analysis-runs/TEST_MISSING','/company/analysis-jobs/TEST_MISSING','/company/analysis-drafts/TEST_MISSING'])
def test_operator_role_is_checked_before_object_lookup(env,path):
    from fastapi.testclient import TestClient
    from app.main import app
    call(env,'editor',path,status=403);call(env,'admin',path,status=403)
    with TestClient(app) as client:assert client.get(path).status_code==401

def submitted(e,data=None):
    c,s,p=fresh(e)
    values=dict(title='TEST analysis',original_text='업무 처리시간 개선과 시스템 연계',as_is='업무 처리시간 측정 필요',to_be='시스템 연계로 개선',site_id=s['id'])
    values.update(data or {})
    v=call(e,'editor','/company/'+c['id']+'/improvements',dict(data=values))
    call(e,'editor','/company/improvements/'+v['id']+'/actions',dict(action='SUBMIT',note='TEST submit'))
    return c,s,p,v,values

def request(e,vid,excluded=None):
    src=call(e,'operator',f'/company/improvements/{vid}/analysis-inputs')
    body=dict(idempotency_key=str(uuid4()),selection_token=src['selection_token'],excluded_files=excluded or {},reason='TEST explicit execution')
    job=call(e,'operator',f'/company/improvements/{vid}/analysis-jobs',body,status=202)
    return job,body,src

def finish(e,vid,**kw):
    assert process_improvement_one(e['factory'],e['files'],**kw)
    return call(e,'operator',f'/company/improvements/{vid}/analysis-runs')[-1]

def test_exact_manifest_review_draft_atomic_send_and_preserved_request_guard(env):
    e=env;c,s,p,v,values=submitted(e);f,raw=upload(e,c['id'],s['id']);job,body,src=request(e,v['id'])
    path=f"/company/improvements/{v['id']}/analysis-jobs"
    assert call(e,'operator',path,body,status=202)['id']==job['id']
    alias=dict(body,idempotency_key=str(uuid4()))
    assert call(e,'operator',path,alias,status=202)['id']==job['id']
    v2=call(e,'editor','/company/'+c['id']+'/improvements',dict(data=dict(values,original_text='TEST DRAFT MUST NOT MIX'),improvement_id=v['improvement_id'],expected_ordinal=1))
    run=finish(e,v['id']);assert run['freshness']['usable'];assert 'TEST DRAFT MUST NOT MIX' not in str(run)
    assert call(e,'operator',path,alias,status=202)['id']==job['id']
    assert run['manifest']['data']['input_version_id']==src['input_version_id']
    assert run['inspections'][0]['data']['digest']==f['digest']
    candidate=next(x for x in run['candidates'] if x['category']=='MISSING_INFORMATION')
    review=call(e,'operator',f"/company/analysis-candidates/{candidate['id']}/reviews",dict(idempotency_key=str(uuid4()),expected_review_ordinal=0,decision='USE_FOR_REQUEST',note='TEST evidence checked',question='TEST measurement question'))
    body=dict(idempotency_key=str(uuid4()),run_id=run['run']['id'],review_ids=[review['id']])
    draft=call(e,'operator','/company/analysis-drafts',body,status=201)
    assert call(e,'operator','/company/analysis-drafts',body,status=201)['id']==draft['id']
    assert not call(e,'operator','/company/'+c['id']+'/information-requests')
    path='/company/analysis-drafts/'+draft['id']
    saved=call(e,'operator',path+'/versions',dict(idempotency_key=str(uuid4()),expected_ordinal=1,title='TEST edited',message='TEST edited question',review_ids=[review['id']]))
    assert call(e,'operator',path)['versions'][-1]['id']==saved['id']
    sent=call(e,'operator',path+'/send',dict(expected_ordinal=2));assert call(e,'operator',path+'/send',dict(expected_ordinal=2))['id']==sent['id']
    requests=call(e,'operator','/company/'+c['id']+'/information-requests');assert len(requests)==1 and requests[0]['message']=='TEST edited question' and requests[0]['improvement_version_id']==v['id']
    with e['factory'].begin() as session:
        with pytest.raises(ProgrammingError,match='INFORMATION_REQUEST_CONTENT_IS_IMMUTABLE'):
            with session.begin_nested():session.execute(text("UPDATE company_information_requests SET message='TEST forbidden' WHERE id=:id"),dict(id=sent['request_id']))
    call(e,'other',path,status=403);call(e,'editor',f"/company/analysis-runs/{run['run']['id']}",status=403)
    call(e,'operator',f"/company/improvements/{v2['id']}/analysis-inputs",status=404)
    from pathlib import Path
    import json
    from app.core.config import ROOT
    proof=ROOT/'storage/private/runtime/slice2/evidence.json';proof.parent.mkdir(parents=True,exist_ok=True)
    proof.write_text(json.dumps(dict(company_id=c['id'],submitted_version=v['id'],draft_version=v2['id'],manifest=run['manifest']['id'],run=run['run']['id'],parse=run['inspections'][0]['parse_id'],candidate=candidate['id'],review=review['id'],draft=draft['id'],saved_version=saved['id'],request=sent['request_id']),indent=2),encoding='utf-8')

def test_zero_candidates_profile_change_and_new_common_warning(env):
    e=env;c,s,p,v,_=submitted(e,dict(original_text='TEST neutral',as_is='',to_be=''))
    request(e,v['id']);run=finish(e,v['id']);assert run['status']=='SUCCEEDED' and run['candidates']==[]
    upload(e,c['id'],s['id']);newer=call(e,'operator',f"/company/analysis-runs/{run['run']['id']}")
    assert newer['freshness']['usable'] and newer['freshness']['warnings']
    call(e,'editor','/company/'+c['id']+'/profile',dict(data=dict(p,overview='TEST changed'),expected_ordinal=1))
    stale=call(e,'operator',f"/company/analysis-runs/{run['run']['id']}");assert not stale['freshness']['usable'] and 'COMPANY_INPUT_CHANGED' in stale['freshness']['reasons']

def test_partial_failure_retry_and_fencing(env):
    from io import BytesIO
    from pypdf import PdfWriter
    from app.company.documents import DocumentError
    from app.core.config import get_settings
    e=env;c,s,p,v,_=submitted(e);out=BytesIO();w=PdfWriter();w.add_blank_page(width=100,height=100);w.write(out)
    r=e['clients']['editor'].post('/company/'+c['id']+'/files',content=out.getvalue(),headers={'Origin':get_settings().web_origin,'X-Upload-Name':'TEST-scan.pdf'});assert r.status_code==200
    job,_,_=request(e,v['id'])
    def failed(name,raw):raise DocumentError('OCR_UNAVAILABLE')
    run=finish(e,v['id'],extractor=failed)
    assert run['status']=='PARTIAL' and not any(c['category']=='MISSING_INFORMATION' for c in run['candidates'])
    assert any(c['category']=='PROCESSING_LIMITATION' for c in run['candidates'])
    call(e,'operator',f"/company/analysis-jobs/{job['id']}/retry",dict(idempotency_key=str(uuid4()),expected_attempt=1),status=202)
    def expire(j,t):
        with e['factory'].begin() as session:session.execute(update(N.jobs).where(N.jobs.c.id==j['id']).values(lease_until=datetime.now(timezone.utc)-timedelta(seconds=1)))
    assert process_improvement_one(e['factory'],e['files'],extractor=failed,before_publish=expire)
    with e['factory']() as session:assert len(session.execute(text('SELECT id FROM analysis_improvement_contexts WHERE manifest_id=:id'),dict(id=run['manifest']['id'])).all())==1
    status=call(e,'operator',f"/company/analysis-jobs/{job['id']}");assert status['retry_allowed']
    call(e,'operator',f"/company/analysis-jobs/{job['id']}/retry",dict(idempotency_key=str(uuid4()),expected_attempt=2),status=202)
    latest=finish(e,v['id'],extractor=failed);assert latest['run']['id']!=run['run']['id']

def test_wrong_quote_database_guard_and_cross_site(env):
    e=env;c,s,p,v,_=submitted(e);other=call(e,'editor','/company/'+c['id']+'/sites',dict(data=dict(name='TEST other',address='TEST address')))['site']
    f,_=upload(e,c['id'],other['id']);src=call(e,'operator',f"/company/improvements/{v['id']}/analysis-inputs");assert f['id'] not in [x['id'] for x in src['files']]
    request(e,v['id']);run=finish(e,v['id']);rid=run['run']['id']
    with e['factory'].begin() as session:
        with pytest.raises(IntegrityError,match='IMPROVEMENT_EVIDENCE_MISMATCH'):
            with session.begin_nested():
                from app.company.application import CompanyApplication
                a=CompanyApplication(session,e['files']);job=a.get(N.jobs,run['manifest']['job_id'])
                attempt=a.add(N.attempts,job_id=job['id'],ordinal=2,owner=str(uuid4()),state='SUCCEEDED')
                newrun=a.add(N.runs,analysis_kind='IMPROVEMENT_ANALYSIS',attempt_id=attempt['id'],actor_id=e['people']['operator']['id'],provider_version='TEST',extractor_version='TEST',missing=[],conflicts=[])
                a.add(S.contexts,run_id=newrun['id'],manifest_id=run['manifest']['id'],status='SUCCEEDED',diagnostics=dict(candidate_count=1))
                c=a.add(N.candidates,run_id=newrun['id'],analysis_kind='IMPROVEMENT_ANALYSIS',kind='STRUCTURE',content='TEST invented',reason='TEST invalid')
                a.add(S.details,candidate_id=c['id'],category='STRUCTURE',data=dict(rule_version='TEST',claim_kind='DIRECT_SOURCE',evidence=[dict(kind='IMPROVEMENT',version_id=v['id'],field='as_is',quote='TEST invented')]))
                session.execute(text('SET CONSTRAINTS ALL IMMEDIATE'))

def test_atomic_send_failure_and_new_submit_guard(env,monkeypatch):
    from app.company.application import CompanyApplication
    from app.notice.domain import Denied
    e=env;c,s,p,v,values=submitted(e);request(e,v['id']);run=finish(e,v['id'])
    candidate=next(x for x in run['candidates'] if x['category']=='MISSING_INFORMATION')
    r=call(e,'operator',f"/company/analysis-candidates/{candidate['id']}/reviews",dict(idempotency_key=str(uuid4()),expected_review_ordinal=0,decision='USE_FOR_REQUEST',note='TEST checked'))
    draft=call(e,'operator','/company/analysis-drafts',dict(idempotency_key=str(uuid4()),run_id=run['run']['id'],review_ids=[r['id']]),status=201)
    original=CompanyApplication.information_send
    def fail(*args):raise Denied('TEST_SEND_FAILED',409)
    monkeypatch.setattr(CompanyApplication,'information_send',fail)
    path='/company/analysis-drafts/'+draft['id'];call(e,'operator',path+'/send',dict(expected_ordinal=1),status=409)
    assert not call(e,'operator','/company/'+c['id']+'/information-requests')
    assert not call(e,'operator',path)['deliveries']
    monkeypatch.setattr(CompanyApplication,'information_send',original)
    r2=call(e,'operator',f"/company/analysis-candidates/{candidate['id']}/reviews",dict(idempotency_key=str(uuid4()),expected_review_ordinal=1,decision='USE_FOR_REQUEST',note='TEST reviewed again'))
    assert 'REVIEW_CHANGED' in call(e,'operator',path)['freshness']['reasons']
    call(e,'operator',path+'/send',dict(expected_ordinal=1),status=409)
    call(e,'operator',path+'/versions',dict(idempotency_key=str(uuid4()),expected_ordinal=1,title='TEST refreshed review',message='TEST request',review_ids=[r2['id']]))
    v2=call(e,'editor','/company/'+c['id']+'/improvements',dict(data=values,improvement_id=v['improvement_id'],expected_ordinal=1))
    call(e,'editor','/company/improvements/'+v2['id']+'/actions',dict(action='SUBMIT',note='TEST new submit'))
    call(e,'operator',path+'/send',dict(expected_ordinal=2),status=409)
    assert call(e,'operator',path)['versions'][0]['id']==draft['versions'][0]['id']

def test_concurrent_jobs_reuse_extraction_and_preserve_reviews(env):
    from concurrent.futures import ThreadPoolExecutor
    from app.core.config import get_settings
    e=env;c,s,p,v,_=submitted(e);f,_=upload(e,c['id'],s['id']);parsed=call(e,'operator','/company/files/'+f['id']+'/parse',{})
    src=call(e,'operator',f"/company/improvements/{v['id']}/analysis-inputs")
    def execute(n):
        return e['clients']['operator'].post(f"/company/improvements/{v['id']}/analysis-jobs",json=dict(idempotency_key=str(uuid4()),selection_token=src['selection_token'],reason='TEST concurrent'),headers={'Origin':get_settings().web_origin})
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(execute,range(2)))
    assert all(r.status_code==202 for r in responses);assert responses[0].json()['id']==responses[1].json()['id']
    run=finish(e,v['id']);assert run['inspections'][0]['parse_id']==parsed['id']
    candidate=run['candidates'][0];r=call(e,'operator',f"/company/analysis-candidates/{candidate['id']}/reviews",dict(idempotency_key=str(uuid4()),expected_review_ordinal=0,decision='NEEDS_CHECK',note='TEST preserved note'))
    with e['factory'].begin() as session:
        with pytest.raises(ProgrammingError,match='IMMUTABLE_COMPANY_BUSINESS_RECORD'):
            with session.begin_nested():session.execute(update(S.reviews).where(S.reviews.c.id==r['id']).values(decision='USE_FOR_REQUEST'))

def test_invalid_output_failure_rolls_back_and_scan_ocr_error_is_not_absence(env,monkeypatch):
    from io import BytesIO
    from pypdf import PdfWriter
    from app.company.improvement_worker import extract
    from app.company.documents import DocumentError
    import app.company.ocr as ocr
    import app.company.improvement_worker as worker
    e=env;c,s,p,v,_=submitted(e);job,_,_=request(e,v['id'])
    def malformed(*args,**kwargs):return [dict(category='STRUCTURE',content='INVENTED',reason='bad',data=dict(evidence=[dict(quote='INVENTED')]))],[]
    monkeypatch.setattr(worker,'analyze',malformed);assert worker.process_improvement_one(e['factory'],e['files'])
    status=call(e,'operator','/company/analysis-jobs/'+job['id']);assert status['state']=='FAILED' and status['runs']==[]
    out=BytesIO();w=PdfWriter();w.add_blank_page(width=100,height=100);w.write(out)
    def fail(*args,**kwargs):raise DocumentError('OCR_TIMEOUT')
    monkeypatch.setattr(ocr,'ocr_pdf',fail);parsed=extract('TEST scan.pdf',out.getvalue())
    assert not parsed.locations and 'OCR_TIMEOUT' in parsed.limitations

def test_direct_manual_evidence_and_unsupported_image_scope(env):
    from io import BytesIO
    from PIL import Image
    from app.core.config import get_settings
    e=env;c,s,p=fresh(e);f,_=upload(e,c['id'],s['id'])
    proof=call(e,'editor','/company/'+c['id']+'/evidence',dict(file_id=f['id'],site_id=s['id'],descriptor='TEST manual transcription',transcription='현황: TEST manual context\n측정 기준: TEST 기준'))
    raw=BytesIO();Image.new('RGB',(20,20),'white').save(raw,format='PNG')
    response=e['clients']['editor'].post('/company/'+c['id']+'/files',content=raw.getvalue(),headers={'Origin':get_settings().web_origin,'X-Upload-Name':'TEST unsupported-image.png'});assert response.status_code==200
    image=response.json()
    v=call(e,'editor','/company/'+c['id']+'/improvements',dict(data=dict(title='TEST manual evidence',original_text='업무 처리시간 개선',as_is='업무 처리시간 개선',site_id=s['id'],evidence_ids=[proof['id']])))
    call(e,'editor','/company/improvements/'+v['id']+'/actions',dict(action='SUBMIT',note='TEST submit'))
    job,_,src=request(e,v['id']);assert not next(f for f in src['files'] if f['id']==image['id'])['default_included']
    run=finish(e,v['id']);assert run['status']=='PARTIAL'
    assert any(c['content']=='TEST manual context' and c['data']['evidence'][0]['kind']=='EVIDENCE' for c in run['candidates'])
    assert not any(c['category']=='MISSING_INFORMATION' and c['data']['rule_id']=='R02' for c in run['candidates'])
