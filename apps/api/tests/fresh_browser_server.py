"""Production API/CompanyProvider plus owned synthetic CI storage; no state injection."""
import os
from pathlib import Path
from isolation import require_test_database
identity=require_test_database()
from app.main import app
from app.core.config import ROOT
from app.infrastructure.notice_documents import LocalPrivateFiles
from app.infrastructure.notice_store import SqlNoticeStore
from app.notice.application import NoticeApplication
from app.collector.application import CollectionApplication
import app.api.notice as notice_api
import app.api.collection as collector_api
directory=Path(os.environ["DATCO_TEST_FILES"]).resolve()
if directory!=(ROOT/"storage/private/runtime/ci"/os.environ["DATCO_TEST_NONCE"]/"files").resolve():
    raise RuntimeError("FRESH_BROWSER_STORAGE_REQUIRED")
files=LocalPrivateFiles(directory)
notice_api.application=lambda s:NoticeApplication(SqlNoticeStore(s),files)
collector_api.application=lambda s:CollectionApplication(SqlNoticeStore(s),files)
@app.get("/__test/identity")
def test_identity():
    return dict(identity,nonce=os.environ["DATCO_TEST_NONCE"])
