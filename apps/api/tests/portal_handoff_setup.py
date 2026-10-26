from registration_sources import number as synthetic_business_number
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
  for label,role in [('slice1_editor','COMPANY_EDITOR'),('slice1_operator','DATCO_OPERATOR'),('slice1_admin','DATCO_ADMIN'),('editor','COMPANY_EDITOR'),('stage_a','COMPANY_EDITOR'),('other','COMPANY_EDITOR'),('negative','COMPANY_EDITOR'),('registration','COMPANY_EDITOR'),('registration_direct','COMPANY_EDITOR'),('registration_conflict','COMPANY_EDITOR'),('registration_retry','COMPANY_EDITOR'),('ux_v13','COMPANY_EDITOR'),('files_v142','COMPANY_EDITOR'),('files_v143','COMPANY_EDITOR'),('operator','DATCO_OPERATOR'),('admin','DATCO_ADMIN')]:
   name='TEST_HANDOFF_'+label+'_'+cohort;store.add('actors',username=name,role=role,password_hash=hash_password(password));accounts[label]=name
 context=dict(accounts=accounts,password=password,nonce=cohort,business_number=synthetic_business_number(),negative_number=synthetic_business_number(),stage_a_number=synthetic_business_number())
 from company_browser_setup import document_first_sources
 context['documents']=document_first_sources(Path(os.environ['DATCO_TEST_HANDOFF_READY']).parent/('handoff-docs-'+cohort))
 from registration_sources import scan
 docs=Path(os.environ['DATCO_TEST_HANDOFF_READY']).parent/('registration-docs-'+cohort);docs.mkdir(exist_ok=True)
 context['registration_number']=synthetic_business_number();context['direct_number']=synthetic_business_number();context['retry_number']=synthetic_business_number()
 context['registration_documents']=[]
 for label,company in [('certificate','합성검증기업'),('proof','합성검증기업')]:
  path=docs/(label+'.pdf');path.write_bytes(scan(context['registration_number'],company,certificate=label=='proof'));context['registration_documents'].append(str(path))
 retry=docs/'retry.pdf';retry.write_bytes(scan(context['retry_number']));context['retry_document']=str(retry)
 conflict=docs/'conflict.pdf';conflict.write_bytes(scan(context['registration_number'][:3]+'-'+context['registration_number'][3:5]+'-'+context['registration_number'][5:],'다른합성기업',certificate=True));context['conflict_document']=str(conflict)
 context['files_v142_number']=synthetic_business_number()
 context['files_v143_number']=synthetic_business_number()
 context['ux_v13_number']=synthetic_business_number()
 ux=docs/'TEST-ux-registration.pdf';ux.write_bytes(scan(context['ux_v13_number']));context['ux_v13_registration']=str(ux)
 from business_sources import portal_sources
 context['business_documents']=portal_sources(docs/'business')
 Path(os.environ['DATCO_TEST_HANDOFF_READY']).write_text(json.dumps(context),encoding='utf-8')
if __name__=='__main__':prepare()
