"""Only the test runner launches this guarded API with dedicated file storage."""
import os
from pathlib import Path
from isolation import require_test_database
identity=require_test_database()
from app.main import app
from app.core.config import ROOT
from app.infrastructure.notice_documents import LocalPrivateFiles
from app.infrastructure.notice_store import SqlNoticeStore
from app.notice.application import NoticeApplication
from app.capability.application import CapabilityApplication
from app.collector.application import CollectionApplication
import app.api.notice as notice_api
import app.api.capability as cap_api
import app.api.collection as collection_api
files=LocalPrivateFiles(Path(os.environ['DATCO_TEST_FILES']))
notice_api.application=lambda s:NoticeApplication(SqlNoticeStore(s),files)
cap_api.application=lambda s:CapabilityApplication(s,files)
collection_api.application=lambda s:CollectionApplication(SqlNoticeStore(s),files)
@app.get('/__test/identity')
def test_identity():return dict(identity,nonce=os.environ['DATCO_TEST_NONCE'])

if os.environ.get('DATCO_TEST_PROPOSAL')=='1':
 from proposal_browser_setup import prepare
 proposal_environment=prepare()

if os.environ.get("DATCO_TEST_COMPANY")=="1":
 from company_browser_setup import prepare as prepare_company
 company_environment=prepare_company()
