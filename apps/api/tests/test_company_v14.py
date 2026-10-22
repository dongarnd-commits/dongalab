"""PR14 v1.4 HTTP authorization, immutable lifecycle and response regression."""
import pytest
from sqlalchemy import update
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
