"""Same production worker functions, explicit isolated factory/files; Snapshot only."""
import json,os,time
from pathlib import Path
from isolation import require_test_database
identity=require_test_database()
from app.infrastructure.database import get_session_factory
from app.infrastructure.notice_documents import LocalPrivateFiles
from app.worker import process_one
from app.collector.worker import process_collection_one
factory=get_session_factory();files=LocalPrivateFiles(Path(os.environ['DATCO_TEST_FILES']))
Path(os.environ['DATCO_TEST_WORKER_READY']).write_text(json.dumps(identity),encoding='utf-8')
while True:
 process_collection_one(factory,files)
 process_one(factory,files)
 time.sleep(.15)
