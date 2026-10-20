"""Empty role cohort only; actual browser commands create all business records."""
import os,json,secrets
from pathlib import Path
import httpx
from isolation import require_test_database
from app.infrastructure.database import get_session_factory
from app.infrastructure.notice_store import SqlNoticeStore
from app.infrastructure.local_auth import hash_password

def prepare():
 require_test_database();nonce=os.environ['DATCO_TEST_NONCE'];identity=httpx.get(os.environ['API_ORIGIN']+'/__test/identity').json();assert identity['nonce']==nonce and identity['database']==os.environ['DATCO_TEST_DATABASE']
 cohort=secrets.token_hex(4);password=secrets.token_urlsafe(24);accounts={}
 with get_session_factory().begin() as session:
  store=SqlNoticeStore(session)
  for label,role in [('editor','COMPANY_EDITOR'),('stage_a','COMPANY_EDITOR'),('other','COMPANY_EDITOR'),('negative','COMPANY_EDITOR'),('operator','DATCO_OPERATOR'),('admin','DATCO_ADMIN')]:
   name='TEST_HANDOFF_'+label+'_'+cohort;store.add('actors',username=name,role=role,password_hash=hash_password(password));accounts[label]=name
 context=dict(accounts=accounts,password=password,nonce=cohort,business_number=str(secrets.randbelow(9_000_000_000)+1_000_000_000),stage_a_number=str(secrets.randbelow(9_000_000_000)+1_000_000_000))
 from company_browser_setup import document_first_sources
 context['documents']=document_first_sources(Path(os.environ['DATCO_TEST_HANDOFF_READY']).parent/('handoff-docs-'+cohort))
 Path(os.environ['DATCO_TEST_HANDOFF_READY']).write_text(json.dumps(context),encoding='utf-8')
if __name__=='__main__':prepare()
