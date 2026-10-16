"""Explicit guarded test server setup; no runtime Company adapter or seeded approval."""
import os,json
from pathlib import Path
from app.infrastructure.database import get_session_factory,get_engine
from app.infrastructure.notice_documents import LocalPrivateFiles
from app.capability.application import CapabilityApplication
from ci_synthetic import SyntheticEnvironment
from capability_scenario_fixture import ScenarioEnvironment
from proposal_fixture import confirm_company,ProposalInputs
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
 env.prepare();confirm_company(env)
 cap=env.caps['A'];context=env.contexts['TEST_IMPROVEMENT_A']
 data=dict(name='TEST Browser service composition',improvement_version_id=context['improvement_version_id'],capability_version_ids=[cap['version']['id']],excluded_feature_revision_ids=[],coverage=[dict(requirement=context['original_text'],capability_version_id=cap['version']['id'],feature_revision_ids=[x['id'] for x in cap['features']],role='TEST selected function',addressed_scope=cap['data']['scope'],unaddressed_scope='TEST reviewed exclusions',missing_information=[])],conditions=['TEST conditions'],unresolved=[])
 result=dict(operator=env.accounts['operator']['username'],approver=env.accounts['approver']['username'],password=env.password,composition_data=data,notice=env.notices['A'])
 Path(os.environ['DATCO_TEST_PROPOSAL_READY']).write_text(json.dumps(result),encoding='utf-8')
 return env
