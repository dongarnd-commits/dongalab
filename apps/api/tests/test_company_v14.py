"""PR14 v1.4 HTTP authorization, immutable lifecycle and response regression."""
import pytest
from sqlalchemy import update
from app.core.config import get_settings
from sqlalchemy.exc import DBAPIError
from app.infrastructure import company_business_schema as B
from test_company_workflow import env,fresh,call,upload
pytestmark=pytest.mark.integration

def test_file_lifecycle_preserves_original_and_blocks_future_parse(env):
 c,site,_=fresh(env);f,raw=upload(env,c['id'],site['id'])
 call(env,'editor','/company/files/'+f['id']+'/parse',{})
 original=call(env,'editor','/company/'+c['id']);proof=next(e for e in original['evidence'] if e['file_id']==f['id'])
 data=dict(title='TEST original improvement',original_text='TEST original user need',site_id=site['id'],evidence_ids=[proof['id']])
 version=call(env,'editor','/company/'+c['id']+'/improvements',dict(data=data))
 call(env,'approver','/company/files/'+f['id']+'/lifecycle',dict(kind='CANCELLED',note='not public'),403)
 call(env,'other','/company/files/'+f['id']+'/lifecycle',dict(kind='CANCELLED',note='other company'),404)
 event=call(env,'editor','/company/files/'+f['id']+'/lifecycle',dict(kind='CANCELLED',note='keep historical source'))
 assert event['file_id']==f['id']
 call(env,'editor','/company/'+c['id']+'/improvements',dict(data=data),409)
 updated=call(env,'editor','/company/'+c['id']+'/improvements',dict(data=data,improvement_id=version['improvement_id'],expected_ordinal=1))
 assert updated['ordinal']==2 and updated['data']['evidence_ids']==version['data']['evidence_ids']
 blocked=call(env,'editor','/company/improvements/'+updated['id']+'/actions',dict(action='SUBMIT',note='TEST inactive source must not be resubmitted'),409)
 assert blocked['reason']=='COMPANY_FILE_INACTIVE'
 call(env,'editor','/company/files/'+f['id']+'/parse',{},409)
 r=env['clients']['editor'].get('/company/files/'+f['id']+'/download');assert r.status_code==200 and r.content==raw
 detail=call(env,'editor','/company/'+c['id']);assert next(x for x in detail['files'] if x['id']==f['id'])['lifecycle']['kind']=='CANCELLED'
 with pytest.raises(DBAPIError):
  with env['factory'].begin() as s:s.execute(update(B.file_events).where(B.file_events.c.id==event['id']).values(note='rewrite'))

def test_information_request_draft_submit_revision_and_exact_response(env):
 c,site,_=fresh(env);cid=c['id'];path='/company/'+cid+'/information-requests'
 call(env,'editor',path,dict(title='Need evidence',message='Confirm actual period'),403)
 call(env,'other',path,status=404)
 request=call(env,'operator',path,dict(title='Need evidence',message='Confirm actual period'))
 assert call(env,'editor',path)==[]
 key='/company/information-requests/'+request['id']
 call(env,'operator',key+'/send',{})
 delivered=call(env,'editor',path)[0];assert delivered['sent_by']==env['people']['operator']['id'] and delivered['sent_at'] and delivered['sender_name']
 draft=call(env,'editor',key+'/responses',dict(message='draft',expected_ordinal=0))
 assert draft['state']=='WAITING_RESPONSE' and not draft['submitted']
 call(env,'operator',key+'/review',dict(response_id=draft['id'],outcome='VERIFIED',note='cannot review draft'),409)
 submitted=call(env,'editor',key+'/responses',dict(message='actual answer',expected_ordinal=1,submit=True))
 call(env,'editor',key+'/responses',dict(message='stale',expected_ordinal=1,submit=True),409)
 call(env,'approver',key+'/review',dict(response_id=submitted['id'],outcome='VERIFIED',note='wrong role'),403)
 call(env,'operator',key+'/review',dict(response_id=submitted['id'],outcome='REVISION_REQUESTED',note='Please add source'))
 resubmitted=call(env,'editor',key+'/responses',dict(message='revised answer',expected_ordinal=2,submit=True))
 call(env,'operator',key+'/review',dict(response_id=submitted['id'],outcome='VERIFIED',note='old version'),409)
 call(env,'operator',key+'/review',dict(response_id=resubmitted['id'],outcome='VERIFIED',note='Checked source'))
 rows=call(env,'editor',path);assert rows[0]['state']=='VERIFIED';assert [x['message'] for x in rows[0]['responses']]==['draft','actual answer','revised answer']
 call(env,'editor',key+'/responses',dict(message='overwrite verified',expected_ordinal=3),409)
 with pytest.raises(DBAPIError):
  with env['factory'].begin() as s:s.execute(update(B.responses).where(B.responses.c.id==draft['id']).values(message='rewrite'))

def test_information_response_rejects_foreign_file_and_other_actors(env):
 c,site,_=fresh(env);other,os,_=fresh(env);f,_=upload(env,other['id'],os['id'])
 request=call(env,'operator','/company/'+c['id']+'/information-requests',dict(title='Source',message='Attach file'))
 key='/company/information-requests/'+request['id'];call(env,'operator',key+'/send',{})
 call(env,'editor',key+'/responses',dict(message='foreign source',file_ids=[f['id']],expected_ordinal=0,submit=True),404)
 call(env,'other',key+'/responses',dict(message='wrong company',expected_ordinal=0,submit=True),404)
 call(env,'operator',key+'/responses',dict(message='cannot impersonate editor',expected_ordinal=0,submit=True),403)
 assert call(env,'editor','/company/'+c['id']+'/information-requests')[0]['response_ordinal']==0


def test_replacement_preserves_both_originals_and_rejects_foreign_target(env):
 from app.core.config import get_settings
 c,site,_=fresh(env);old,raw=upload(env,c['id'],site['id']);other,other_site,_=fresh(env);foreign,_=upload(env,other['id'],other_site['id'])
 path='/company/files/'+old['id']+'/lifecycle'
 call(env,'editor',path,dict(kind='REPLACED',replacement_id=foreign['id'],note='TEST wrong company'),404)
 replacement_raw=b'TEST replacement original bytes'
 response=env['clients']['editor'].post('/company/'+c['id']+'/files',content=replacement_raw,headers={'Origin':get_settings().web_origin,'X-Upload-Name':'TEST-replacement.txt'});assert response.status_code==200
 new=response.json();event=call(env,'editor',path,dict(kind='REPLACED',replacement_id=new['id'],note='TEST explicit replacement'))
 assert event['replacement_id']==new['id']
 assert env['clients']['editor'].get('/company/files/'+old['id']+'/download').content==raw
 assert env['clients']['editor'].get('/company/files/'+new['id']+'/download').content==replacement_raw
 call(env,'editor','/company/files/'+old['id']+'/parse',{},409)
 assert call(env,'editor','/company/files/'+new['id']+'/parse',{})['error'] is None
 call(env,'editor',path,dict(kind='CANCELLED',note='TEST cannot overwrite replacement event'),409)


def test_editor_post_submit_revision_preserves_exact_original_and_scope(env):
 c,site,_=fresh(env);cid=c['id'];f,raw=upload(env,cid,site['id'])
 call(env,'editor','/company/files/'+f['id']+'/parse',{})
 detail=call(env,'editor','/company/'+cid);evidence=next(e for e in detail['evidence'] if e['file_id']==f['id'])
 data=dict(title='TEST submitted input',original_text='TEST original submitted input',as_is='TEST original problem',to_be='TEST original goal',site_id=site['id'],evidence_ids=[evidence['id']])
 first=call(env,'editor','/company/'+cid+'/improvements',dict(data=data));path='/company/improvements/'+first['id']+'/actions'
 sent=call(env,'editor',path,dict(action='SUBMIT',note='TEST first submit'))
 baseline=next(v for i in call(env,'operator','/company/'+cid)['improvements'] if i['id']==first['improvement_id'] for v in i['versions'] if v['id']==first['id'])
 call(env,'editor',path,dict(action='SUBMIT',note='TEST duplicate submit'),409)
 revised=dict(data,original_text='TEST revised company input',as_is='TEST revised problem')
 body=dict(data=revised,improvement_id=first['improvement_id'],expected_ordinal=1)
 call(env,'other','/company/'+cid+'/improvements',body,404)
 call(env,'approver','/company/'+cid+'/improvements',body,403)
 second=call(env,'editor','/company/'+cid+'/improvements',body)
 assert second['ordinal']==2 and second['id']!=first['id']
 call(env,'editor',path,dict(action='SUBMIT',note='TEST obsolete submit'),409)
 call(env,'editor','/company/'+cid+'/improvements',body,409)
 call(env,'editor','/company/improvements/'+second['id']+'/actions',dict(action='SUBMIT',note='TEST resubmit'))
 actual=call(env,'operator','/company/'+cid);root=next(i for i in actual['improvements'] if i['id']==first['improvement_id'])
 assert root['state']=='SUBMITTED' and root['current_ordinal']==2
 original=next(v for v in root['versions'] if v['id']==first['id']);latest=next(v for v in root['versions'] if v['id']==second['id'])
 assert original==baseline and original['data']==first['data']
 assert all(original['reviews'][0][key]==value for key,value in sent['review'].items())
 assert latest['data']['as_is']=='TEST revised problem' and latest['data']['evidence_ids']==first['data']['evidence_ids']
 assert latest['reviews'][0]['outcome']=='SUBMIT' and latest['reviews'][0]['actor_id']==env['people']['editor']['id']
 assert env['clients']['editor'].get('/company/files/'+f['id']+'/download').content==raw


def test_attachment_detach_creates_new_version_without_changing_other_submission(env,tmp_path):
 from business_sources import portal_sources
 from pathlib import Path
 c,site,_=fresh(env);cid=c['id'];raw=Path(portal_sources(tmp_path)['financial']).read_bytes()
 response=env['clients']['editor'].post('/company/'+cid+'/files',params={'site_id':site['id']},content=raw,headers={'Origin':get_settings().web_origin,'X-Upload-Name':'TEST-detach.pdf'})
 assert response.status_code==200;file=response.json()
 call(env,'editor','/company/files/'+file['id']+'/parse',{})
 evidence=next(e for e in call(env,'editor','/company/'+cid)['evidence'] if e['file_id']==file['id'])
 data=dict(title='TEST detach source',original_text='TEST original attached source',as_is='TEST problem',to_be='TEST goal',site_id=site['id'],evidence_ids=[evidence['id']])
 first=call(env,'editor','/company/'+cid+'/improvements',dict(data=data))
 call(env,'editor','/company/improvements/'+first['id']+'/actions',dict(action='SUBMIT',note='TEST original submission'))
 other=call(env,'editor','/company/'+cid+'/improvements',dict(data=dict(data,title='TEST other submitted root')))
 call(env,'editor','/company/improvements/'+other['id']+'/actions',dict(action='SUBMIT',note='TEST independent submission'))
 before=call(env,'editor','/company/'+cid);original_root=next(i for i in before['improvements'] if i['id']==first['improvement_id']);other_root=next(i for i in before['improvements'] if i['id']==other['improvement_id'])
 body=dict(data=dict(data,evidence_ids=[],constraints='TEST detach in new revision'),improvement_id=first['improvement_id'],expected_ordinal=1)
 call(env,'other','/company/'+cid+'/improvements',body,404)
 revised=call(env,'editor','/company/'+cid+'/improvements',body);assert revised['data']['evidence_ids']==[]
 saved=call(env,'editor','/company/'+cid);assert next(i for i in saved['improvements'] if i['id']==other['improvement_id'])==other_root
 assert next(i for i in saved['improvements'] if i['id']==first['improvement_id'])['versions'][0]==original_root['versions'][0]
 call(env,'editor','/company/improvements/'+revised['id']+'/actions',dict(action='SUBMIT',note='TEST detached revision resubmitted'))
 actual=call(env,'operator','/company/'+cid);root=next(i for i in actual['improvements'] if i['id']==first['improvement_id'])
 assert root['state']=='SUBMITTED' and root['current_ordinal']==2 and root['versions'][-1]['data']['evidence_ids']==[]
 assert len([v for v in root['versions'] if any(r['outcome']=='SUBMIT' for r in v['reviews'])])==2
 assert env['clients']['editor'].get('/company/files/'+file['id']+'/download').content==raw


def test_cancel_reregister_pdf_preserves_history_scope_and_concurrent_guard(env,tmp_path):
 from concurrent.futures import ThreadPoolExecutor
 from uuid import uuid4
 from sqlalchemy import insert,select
 from app.infrastructure import company_schema as S
 from app.company.application import CompanyApplication
 from app.notice.domain import Actor,Denied
 c,site,_=fresh(env)
 # Actual synthetic PDF through HTTP and private content-addressed storage.
 from reportlab.pdfgen import canvas
 from io import BytesIO
 buf=BytesIO();pdf=canvas.Canvas(buf);pdf.drawString(40,700,'TEST registration source');pdf.save();raw=buf.getvalue()
 def post():
  return env['clients']['editor'].post('/company/'+c['id']+'/files',params={'site_id':site['id']},content=raw,headers={'Origin':get_settings().web_origin,'X-Upload-Name':'TEST.pdf'})
 first=post();assert first.status_code==200;old=first.json()
 call(env,'editor','/company/files/'+old['id']+'/parse',{})
 before=call(env,'editor','/company/'+c['id'])
 event=call(env,'editor','/company/files/'+old['id']+'/lifecycle',dict(kind='CANCELLED',note='TEST cancelled original'))
 who=Actor(env['people']['editor']['id'],'COMPANY_EDITOR')
 def concurrent_upload(_):
  try:
   with env['factory'].begin() as session:
    return CompanyApplication(session,env['files']).upload(who,c['id'],'TEST.pdf',raw,site['id'])['id']
  except Denied as error:return str(error)
 with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(concurrent_upload,range(2)))
 after=call(env,'editor','/company/'+c['id']);active=[f for f in after['files'] if not f.get('lifecycle')]
 assert len(active)==1 and active[0]['id']!=old['id']
 assert sum(value==active[0]['id'] for value in results)==1
 assert active[0]['digest']==old['digest'] and active[0]['storage_key']==old['storage_key']
 assert next(f for f in after['files'] if f['id']==old['id'])['lifecycle']['id']==event['id']
 assert after['evidence']==before['evidence']
 assert after['improvements']==before['improvements']
 assert post().status_code==409
 for f in (old,active[0]):
  assert env['clients']['editor'].get('/company/files/'+f['id']+'/download').content==raw
  assert env['clients']['other'].get('/company/files/'+f['id']+'/download').status_code==404
 with pytest.raises(DBAPIError):
  with env['factory'].begin() as session:
   values={k:v for k,v in active[0].items() if k in S.files.c and k not in ('id','created_at')};values['id']=str(uuid4())
   session.execute(insert(S.files).values(**values))


def test_reregistration_storage_failure_rolls_back_and_history_down_refused(env,monkeypatch):
 from alembic.operations import Operations
 from alembic.migration import MigrationContext
 from v14_migration_chain import load
 from app.company.application import CompanyApplication
 from app.notice.domain import Actor
 c,site,_=fresh(env);old,raw=upload(env,c['id'],site['id'])
 event=call(env,'editor','/company/files/'+old['id']+'/lifecycle',dict(kind='CANCELLED',note='TEST failure recovery'))
 who=Actor(env['people']['editor']['id'],'COMPANY_EDITOR')
 with monkeypatch.context() as patch:
  def fail(_):raise OSError('TEST storage unavailable')
  patch.setattr(env['files'],'put',fail)
  with pytest.raises(OSError,match='TEST storage unavailable'):
   with env['factory'].begin() as session:CompanyApplication(session,env['files']).upload(who,c['id'],'TEST.txt',raw,site['id'])
 detail=call(env,'editor','/company/'+c['id']);assert len(detail['files'])==1 and detail['files'][0]['lifecycle']['id']==event['id']
 with env['factory'].begin() as session:new=CompanyApplication(session,env['files']).upload(who,c['id'],'TEST.txt',raw,site['id'])
 assert new['id']!=old['id']
 with env['factory'].begin() as session:
  with Operations.context(MigrationContext.configure(session.connection())):
   with pytest.raises(RuntimeError,match='COMPANY_FILE_REGISTRATION_HISTORY_EXISTS'):load('fd18e0012026_company_file_reregistration.py').downgrade()
 assert env['clients']['editor'].get('/company/files/'+old['id']+'/download').content==raw


def test_direct_sql_concurrent_registration_and_cross_company_content(env):
 from concurrent.futures import ThreadPoolExecutor
 from uuid import uuid4
 from sqlalchemy import insert
 from app.infrastructure import company_schema as S
 c,site,_=fresh(env);old,raw=upload(env,c['id'],site['id'])
 call(env,'editor','/company/files/'+old['id']+'/lifecycle',dict(kind='CANCELLED',note='TEST database concurrency'))
 values={k:v for k,v in old.items() if k in S.files.c and k not in ('id','created_at')}
 def register(_):
  try:
   with env['factory'].begin() as session:session.execute(insert(S.files).values(**values,id=str(uuid4())))
   return 'CREATED'
  except DBAPIError as error:return error.orig.sqlstate
 with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(register,range(2)))
 assert sorted(results)==['23505','CREATED']
 other,other_site,_=fresh(env)
 r=env['clients']['editor'].post('/company/'+other['id']+'/files',params={'site_id':other_site['id']},content=raw,headers={'Origin':get_settings().web_origin,'X-Upload-Name':'TEST.txt'})
 assert r.status_code==200 and r.json()['digest']==old['digest'] and r.json()['id']!=old['id']
 assert env['clients']['other'].get('/company/files/'+r.json()['id']+'/download').status_code==404
