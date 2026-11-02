"""Manual UAT API: production routes/adapters, only guarded file storage differs."""
import os
from pathlib import Path
from isolation import require_test_database
identity = require_test_database()
from app.main import app
from app.infrastructure.notice_documents import LocalPrivateFiles
from app.infrastructure.notice_store import SqlNoticeStore
from app.notice.application import NoticeApplication
from app.collector.application import CollectionApplication
from manual_acceptance import owned
import app.api.notice as notice_api
import app.api.collection as collection_api

out = owned(os.environ["DATCO_TEST_NONCE"])
if Path(os.environ["DATCO_TEST_FILES"]).resolve() != out / "files":
    raise RuntimeError("MANUAL_FILE_STORAGE_MISMATCH")
if os.environ.get("BIZINFO_API_KEY") or os.environ.get("DATCO_TEST_COMPANY") or os.environ.get("DATCO_TEST_PROPOSAL"):
    raise RuntimeError("MANUAL_FIXTURE_FLAGS_FORBIDDEN")
files = LocalPrivateFiles(out / "files")
notice_api.application = lambda s: NoticeApplication(SqlNoticeStore(s), files)
collection_api.application = lambda s: CollectionApplication(SqlNoticeStore(s), files)
# Keep production capability.application, including its CompanyProvider adapter.

@app.get("/__test/identity")
def test_identity():
    return dict(identity, nonce=os.environ["DATCO_TEST_NONCE"])
