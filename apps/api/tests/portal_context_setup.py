from registration_sources import number as synthetic_business_number
"""Synthetic context fixture created via real APIs, only inside runner-owned PostgreSQL."""
import os,json,secrets
from pathlib import Path
from uuid import uuid4
import httpx
from isolation import require_test_database
from app.infrastructure.database import get_session_factory
from app.infrastructure.notice_store import SqlNoticeStore
from app.infrastructure.local_auth import hash_password

def prepare():
 identity=require_test_database();nonce=os.environ['DATCO_TEST_NONCE'];origin=os.environ['WEB_ORIGIN'];api=os.environ['API_ORIGIN']
 c=json.loads(Path(os.environ['DATCO_TEST_COMPANY_READY']).read_text(encoding='utf-8'));accounts=dict(c['accounts'])
 with httpx.Client(base_url=api) as check:assert check.get('/__test/identity').json()['nonce']==nonce
 with get_session_factory().begin() as session:
  for label,role in [('editor','COMPANY_EDITOR'),('operator','DATCO_OPERATOR'),('admin','DATCO_ADMIN'),('other','COMPANY_EDITOR'),('multi','COMPANY_EDITOR'),('zero','COMPANY_EDITOR'),('blocked_operator','DATCO_OPERATOR')]:
   accounts[label]=SqlNoticeStore(session).add('actors',username='TEST_CONTEXT_'+label+'_'+nonce,role=role,password_hash=hash_password(c['password']))['username']
 clients={}
 try:
  for label in ['editor','operator','admin','other','multi','zero','blocked_operator']:
   client=httpx.Client(base_url=api,headers={'Origin':origin});clients[label]=client;r=client.post('/notice/session',json=dict(username=accounts[label],password=c['password']));r.raise_for_status()
  def post(role,path,data):
   r=clients[role].post(path,json=data);r.raise_for_status();return r.json()
  def company(role,label):return post(role,'/company',dict(name='TEST Context '+label+' '+nonce,business_number=synthetic_business_number()))
  a=company('editor','A');b=company('multi','B');empty=company('multi','Empty');foreign=company('other','Foreign')
  for comp in [a,b]:post('admin','/company/'+comp['id']+'/access',dict(username=accounts['operator']))
  for comp in [a]:post('admin','/company/'+comp['id']+'/access',dict(username=accounts['multi']))
  def site(cid,label):
   owner='editor' if cid==a['id'] else 'multi' if cid==b['id'] else 'other'
   return post(owner,'/company/'+cid+'/sites',dict(data=dict(name='TEST '+label+' '+nonce,address='TEST isolated address')))['site']
  a1=site(a['id'],'A1');a2=site(a['id'],'A2');bs=site(b['id'],'B1');fs=site(foreign['id'],'Foreign')
  def improvement(owner,cid,sid,title):return post(owner,'/company/'+cid+'/improvements',dict(data=dict(title='TEST '+title+' '+nonce,original_text='TEST '+title+' original',as_is='TEST '+title+' As-Is',to_be='TEST '+title+' To-Be',site_id=sid)))
  av1=improvement('editor',a['id'],a1['id'],'A historical')
  post('editor','/company/'+a['id']+'/sites',dict(site_id=a1['id'],expected_ordinal=1,data=dict(name='TEST A1 updated '+nonce,address='TEST revised isolated address')))
  av2=post('editor','/company/'+a['id']+'/improvements',dict(improvement_id=av1['improvement_id'],expected_ordinal=1,data=dict(av1['data'],title='TEST A latest '+nonce,to_be='TEST latest To-Be')))
  second=improvement('editor',a['id'],a1['id'],'A second root');other_site=improvement('editor',a['id'],a2['id'],'A2 root');bv=improvement('multi',b['id'],bs['id'],'B root');fv=improvement('other',foreign['id'],fs['id'],'Foreign root')
  result=dict(accounts=accounts,password=c['password'],a=a,b=b,empty=empty,foreign=foreign,a1=a1,a2=a2,bs=bs,fs=fs,av1=av1,av2=av2,second=second,other_site=other_site,bv=bv,fv=fv)
  Path(os.environ['DATCO_TEST_CONTEXT_READY']).write_text(json.dumps(result),encoding='utf-8')
 finally:
  for client in clients.values():client.close()
if __name__=='__main__':prepare()
