"""Synthetic snapshots with production CompanyProvider and real workflow commands."""
import os,json
from pathlib import Path
from app.infrastructure.database import get_session_factory,get_engine
from app.infrastructure.notice_documents import LocalPrivateFiles
from app.capability.application import CapabilityApplication
from ci_synthetic import SyntheticEnvironment
from capability_scenario_fixture import ScenarioEnvironment
from proposal_fixture import ProposalInputs
from confirmed_comparison_fixture import metadata
from isolation import require_test_database
import app.api.capability as cap_api

def prepare():
 require_test_database()
 with get_engine().begin() as c:metadata.create_all(c)
 directory=Path(os.environ['DATCO_TEST_FILES']).parent/'proposal-browser';directory.mkdir(parents=True,exist_ok=True)
 environment=ScenarioEnvironment if os.environ.get('DATCO_TEST_PROPOSAL_SOURCE')=='private' else SyntheticEnvironment
 env=environment(get_session_factory(),LocalPrivateFiles(Path(os.environ['DATCO_TEST_FILES'])),directory)
 cap_api.application=lambda s:CapabilityApplication(s,env.files,ProposalInputs(env))
 env.prepare()
 # The running browser API uses the production CompanyProvider. All business
 # confirmation/state transitions below are real HTTP commands on synthetic data.
 from app.company.application import CompanyApplication
 from app.company.provider import CompanyProvider
 from app.infrastructure.notice_store import SqlNoticeStore
 from app.infrastructure.local_auth import hash_password
 from app.core.config import get_settings
 from registration_sources import number
 from fastapi.testclient import TestClient
 from app.main import app
 editor=env.accounts['company']
 with get_session_factory().begin() as session:
  approver=SqlNoticeStore(session).add('actors',username='TEST_BROWSER_APPROVER_'+env.nonce(),role='COMPANY_APPROVER',password_hash=hash_password(env.password))
 env.accounts['approver']=approver;env.clients['approver']=TestClient(app);env.call('approver','/notice/session',dict(username=approver['username'],password=env.password))
 company=env.call('company','/company',dict(name='TEST proposal browser company',business_number=number()));cid=company['id']
 for recipient in ('operator','approver'):env.call('admin','/company/'+cid+'/access',dict(username=env.accounts[recipient]['username']))
 site=env.call('company','/company/'+cid+'/sites',{'data':dict(name='TEST browser site',address='TEST location')})['site']
 raw='기업명: TEST proposal browser company'.encode('utf-8');uploaded=env.clients['company'].post('/company/'+cid+'/files',content=raw,headers={'Origin':get_settings().web_origin,'X-Upload-Name':'TEST-browser-company.txt'});assert uploaded.status_code==200
 env.call('operator','/company/files/'+uploaded.json()['id']+'/parse',{})
 candidate=next(row for row in env.call('company','/company/'+cid)['candidates'] if row['mode']=='RULE_BASED_EXTRACTION')
 env.call('company','/company/candidates/'+candidate['id']+'/acknowledge',dict(agreed=True,note='TEST company acknowledged exact source'))
 fact=env.call('operator','/company/candidates/'+candidate['id']+'/review',dict(outcome='CONFIRM_NEW_VALUE',note='TEST internal fact review'))['version']
 original=env.contexts['TEST_IMPROVEMENT_A']['original_text'];data=dict(title='TEST browser improvement',original_text=original,site_id=site['id'],as_is='TEST as-is',problem='TEST problem',goal='TEST goal',to_be='TEST to-be',fact_version_ids=[fact['id']],evidence_ids=[candidate['evidence_id']])
 first=env.call('company','/company/'+cid+'/improvements',dict(data=data));env.call('company','/company/improvements/'+first['id']+'/actions',dict(action='SUBMIT',note='TEST company submitted source'))
 current=env.call('operator','/company/'+cid+'/improvements',dict(data=data,improvement_id=first['improvement_id'],expected_ordinal=1))
 env.call('company','/company/improvements/'+current['id']+'/actions',dict(action='ACKNOWLEDGE',note='TEST exact structured version acknowledged'))
 env.call('operator','/company/improvements/'+current['id']+'/actions',dict(action='CONFIRM',note='TEST operator reviewed current evidence'))
 env.contexts['TEST_IMPROVEMENT_A']=env.call('operator','/company/improvements/'+current['id']+'/context')
 cap_api.application=lambda session:CapabilityApplication(session,env.files,CompanyProvider(CompanyApplication(session,env.files)))
 cap=env.caps['A'];context=env.contexts['TEST_IMPROVEMENT_A']
 data=dict(name='TEST Browser service composition',improvement_version_id=context['improvement_version_id'],capability_version_ids=[cap['version']['id']],excluded_feature_revision_ids=[],coverage=[dict(requirement=context['original_text'],capability_version_id=cap['version']['id'],feature_revision_ids=[x['id'] for x in cap['features']],role='TEST selected function',addressed_scope=cap['data']['scope'],unaddressed_scope='TEST reviewed exclusions',missing_information=[])],conditions=['TEST conditions'],unresolved=[])
 result=dict(company_editor=editor['username'],company_editor_id=editor['id'],company_id=cid,operator=env.accounts['operator']['username'],approver=env.accounts['approver']['username'],password=env.password,composition_data=data,notice=env.notices['A'])
 Path(os.environ['DATCO_TEST_PROPOSAL_READY']).write_text(json.dumps(result),encoding='utf-8')
 return env
