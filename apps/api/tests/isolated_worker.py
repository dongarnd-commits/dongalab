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
ready=Path(os.environ['DATCO_TEST_WORKER_READY'])
temporary=ready.with_suffix('.tmp')
temporary.write_text(json.dumps(identity),encoding='utf-8')
# Windows antivirus/indexer may briefly hold a newly written file.
for attempt in range(100):
 try:
  temporary.replace(ready);break
 except PermissionError:
  if attempt==99:raise
  time.sleep(.05)
while True:
 process_collection_one(factory,files)
 process_one(factory,files)
 from app.company.improvement_worker import process_improvement_one
 process_improvement_one(factory,files)
 time.sleep(.15)
