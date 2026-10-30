"""Explicit operator judgement and automatic-entry input policy, synthetic DB only."""
from uuid import uuid4
import pytest
from sqlalchemy import text,update
from sqlalchemy.exc import ProgrammingError,IntegrityError
from test_company_workflow import env,call,upload
from test_improvement_analysis import submitted,finish
from app.infrastructure import submission_review_schema as R,company_schema as C
pytestmark=pytest.mark.integration

def ensure(e,vid):
 src=call(e,'operator',f'/company/improvements/{vid}/analysis-inputs')
 return call(e,'operator',f'/company/improvements/{vid}/analysis-jobs',dict(idempotency_key=str(uuid4()),selection_token=src['selection_token'],mode='ENSURE',reason='TEST operator detail entry'),status=202)

def history(e,vid):return call(e,'operator',f'/company/improvements/{vid}/submission-reviews')
def judge(e,vid,run=None,**kw):
 body=dict(idempotency_key=str(uuid4()),expected_ordinal=0,decision='COMPLETED',note='TEST explicitly reviewed',run_id=run['run']['id'] if run else None,job_id=run['manifest']['job_id'] if run else None)
 body.update(kw)
 return body,call(e,'operator',f'/company/improvements/{vid}/submission-reviews',body)

def test_default_common_is_unselected_and_completed_run_reused_after_refresh(env):
 e=env;c,s,p,v,_=submitted(e);f,_=upload(e,c['id'],s['id'])
 src=call(e,'operator',f"/company/improvements/{v['id']}/analysis-inputs")
 assert not src['files'][0]['default_included']
 assert history(e,v['id'])['history']==[]
 from concurrent.futures import ThreadPoolExecutor
 with ThreadPoolExecutor(max_workers=2) as pool:jobs=list(pool.map(lambda _:ensure(e,v['id']),range(2)))
 job=jobs[0];assert jobs[1]['id']==job['id'];assert ensure(e,v['id'])['id']==job['id']
 run=finish(e,v['id']);item=run['inputs'][0]
 assert item['data']['selection']=='NOT_SELECTED' and item['data']['exclude_reason']==''
 assert run['inspections'][0]['data']['status']=='NOT_SELECTED'
 assert any(c['category']=='MISSING_INFORMATION' for c in run['candidates'])
 assert ensure(e,v['id'])['id']==job['id']
 call(e,'operator','/company/files/'+f['id']+'/parse',{})
 assert ensure(e,v['id'])['id']==job['id']
 assert history(e,v['id'])['history']==[]
 assert history(e,v['id'])['projection']['status']=='NEEDS_REVIEW'

def test_whole_judgement_is_append_only_exact_version_and_separate_from_confirm(env):
 e=env;c,s,p,v,values=submitted(e);ensure(e,v['id']);run=finish(e,v['id'])
 body,review=judge(e,v['id'],run)
 assert call(e,'operator',f"/company/improvements/{v['id']}/submission-reviews",body)['id']==review['id']
 saved=history(e,v['id']);assert saved['projection']['status']=='COMPLETED' and saved['projection']['current']
 assert saved['history'][0]['actor_name']==e['people']['operator']['username'] and saved['history'][0]['created_at']
 with e['factory'].begin() as session:
  assert session.execute(text('SELECT state FROM company_improvements WHERE id=:id'),dict(id=v['improvement_id'])).scalar()!='CONFIRMED'
  with pytest.raises(ProgrammingError):
   with session.begin_nested():session.execute(update(R.reviews).where(R.reviews.c.id==review['id']).values(note='TEST overwrite'))
  with pytest.raises(ProgrammingError):
   with session.begin_nested():session.execute(R.reviews.delete().where(R.reviews.c.id==review['id']))
  from alembic.operations import Operations
  from alembic.migration import MigrationContext
  from v14_migration_chain import load
  with Operations.context(MigrationContext.configure(session.connection())):
   with pytest.raises(RuntimeError,match='history exists'):load('ff30u0012026_operator_submission_review.py').downgrade()
 body2=dict(body,idempotency_key=str(uuid4()),decision='NEEDS_CHECK')
 call(e,'operator',f"/company/improvements/{v['id']}/submission-reviews",body2,status=409)
 judge(e,v['id'],run,expected_ordinal=1,decision='NEEDS_CHECK',note='TEST new opinion')
 assert len(history(e,v['id'])['history'])==2 and history(e,v['id'])['projection']['status']=='NEEDS_CHECK'
 other=call(e,'editor','/company/'+c['id']+'/improvements',dict(data=dict(values,title='TEST independent task')))
 call(e,'editor','/company/improvements/'+other['id']+'/actions',dict(action='SUBMIT',note='TEST'))
 assert history(e,other['id'])['projection']['status']=='NEW_RECEIPT'
 v2=call(e,'editor','/company/'+c['id']+'/improvements',dict(data=values,improvement_id=v['improvement_id'],expected_ordinal=1))
 call(e,'editor','/company/improvements/'+v2['id']+'/actions',dict(action='SUBMIT',note='TEST'))
 assert history(e,v2['id'])['history']==[] and history(e,v2['id'])['projection']['status']=='REREVIEW'
 assert history(e,v['id'])['projection']['status']=='REREVIEW'

def test_no_run_requires_explicit_limit_and_scope_is_enforced(env):
 e=env;c,s,p,v,_=submitted(e)
 body=dict(idempotency_key=str(uuid4()),expected_ordinal=0,decision='NEEDS_CHECK',note='TEST cannot judge')
 path=f"/company/improvements/{v['id']}/submission-reviews"
 call(e,'operator',path,body,status=422)
 judge(e,v['id'],decision='NEEDS_CHECK',analysis_limit='TEST extraction unavailable')
 call(e,'editor',path,status=403);call(e,'other',path,status=403);call(e,'admin',path,status=403)
 ensure(e,v['id']);run=finish(e,v['id']);assert history(e,v['id'])['projection']['status']=='REREVIEW'
 foreign= submitted(e)[3];ensure(e,foreign['id']);foreignrun=finish(e,foreign['id'])
 call(e,'operator',path,dict(body,expected_ordinal=1,run_id=foreignrun['run']['id']),status=404)
 with e['factory'].begin() as session:
  from app.company.application import CompanyApplication
  a=CompanyApplication(session,e['files'])
  old=a.rows(R.reviews,version_id=v['id'])[0]
  with pytest.raises(IntegrityError,match='SUBMISSION_REVIEW_BASIS_MISMATCH'):
   with session.begin_nested():a.add(R.reviews,**{k:x for k,x in dict(old,id=str(uuid4()),ordinal=2,request_key=str(uuid4()),run_id=foreignrun['run']['id']).items() if k!='created_at'})
 assert run['freshness']['usable']

def test_new_company_input_makes_prior_judgement_stale(env):
 e=env;c,s,p,v,_=submitted(e);ensure(e,v['id']);run=finish(e,v['id']);judge(e,v['id'],run)
 call(e,'editor','/company/'+c['id']+'/profile',dict(data=dict(p,overview='TEST changed basis'),expected_ordinal=1))
 assert history(e,v['id'])['projection']['status']=='REREVIEW'
 newjob=ensure(e,v['id']);assert newjob['id']!=run['manifest']['job_id'];finish(e,v['id'])

def test_authorized_second_operator_sees_history_and_reanalysis_invalidates_review(env):
 from app.company.application import CompanyApplication
 from app.company.submission_review import SubmissionReview
 from app.infrastructure.notice_store import SqlNoticeStore
 from app.notice.domain import Actor
 e=env;c,s,p,v,_=submitted(e);ensure(e,v['id']);run=finish(e,v['id']);judge(e,v['id'],run)
 with e['factory'].begin() as session:
  a=CompanyApplication(session,e['files']);person=SqlNoticeStore(session).add('actors',username='TEST second '+uuid4().hex,role='DATCO_OPERATOR',password_hash='TEST_NO_LOGIN')
  a.add(C.memberships,company_id=c['id'],actor_id=person['id'],granted_by=e['people']['editor']['id'])
  other=Actor(person['id'],'DATCO_OPERATOR');svc=SubmissionReview(a)
  assert svc.history(other,v['id'])[0]['actor_id']==e['people']['operator']['id']
  svc.save(other,v['id'],str(uuid4()),1,'COMPLETED','TEST second judgement',run['run']['id'],run['manifest']['job_id'])
 assert history(e,v['id'])['history'][-1]['actor_name']==person['username']
 from test_improvement_analysis import request
 request(e,v['id']);new=finish(e,v['id']);assert new['run']['id']!=run['run']['id']
 assert history(e,v['id'])['projection']['status']=='REREVIEW'

def test_failed_entry_is_reused_until_explicit_retry(env,monkeypatch):
 e=env;c,s,p,v,_=submitted(e);job=ensure(e,v['id'])
 def invalid(*args,**kw):raise ValueError('TEST synthetic analysis failure')
 import app.company.improvement_worker as worker
 original=worker.analyze;monkeypatch.setattr(worker,'analyze',invalid)
 assert worker.process_improvement_one(e['factory'],e['files'])
 assert ensure(e,v['id'])['id']==job['id']
 assert history(e,v['id'])['projection']['status']=='NEEDS_CHECK'
 state=call(e,'operator','/company/analysis-jobs/'+job['id']);assert state['retry_allowed']
 call(e,'operator','/company/analysis-jobs/'+job['id']+'/retry',dict(idempotency_key=str(uuid4()),expected_attempt=1),status=202)
 monkeypatch.setattr(worker,'analyze',original)
 finish(e,v['id'])
