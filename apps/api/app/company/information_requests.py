"""Scoped InformationRequest workflow using the existing logical states."""
from datetime import date
from sqlalchemy import update,func
from app.infrastructure import company_schema as S
from app.infrastructure import company_business_schema as B
from app.notice.domain import Denied

class InformationRequests:
 def information_list(self,who,cid):
  self.role(who,'COMPANY_EDITOR','DATCO_OPERATOR');self.scope(who,cid)
  rows=self.rows(B.requests,company_id=cid)
  if who.role=='COMPANY_EDITOR':rows=[r for r in rows if r['state']!='DRAFT']
  from app.infrastructure.notice_schema import actors
  return [dict(r,sender_name=self.get(actors,r['sent_by'])['username'] if r['sent_by'] else None,responses=[dict(v,file_ids=[f['file_id'] for f in self.rows(B.response_files,response_id=v['id'])]) for v in self.rows(B.responses,request_id=r['id'])],reviews=self.rows(B.request_reviews,request_id=r['id'])) for r in rows]
 def information_create(self,who,cid,title,message,due_date=None,input_version_id=None,improvement_version_id=None,file_id=None):
  self.role(who,'DATCO_OPERATOR');self.scope(who,cid,True)
  if improvement_version_id:
   version=self.get(S.improvement_versions,improvement_version_id)
   if self.get(S.improvements,version['improvement_id'])['company_id']!=cid:raise Denied('OBJECT_NOT_FOUND',404)
  for table,key in ((S.inputs,input_version_id),(S.files,file_id)):
   if key and self.get(table,key)['company_id']!=cid:raise Denied('OBJECT_NOT_FOUND',404)
  if not title.strip() or not message.strip() or len(title)>300 or len(message)>10000:raise Denied('INVALID_REQUEST',422)
  if due_date:
   try:date.fromisoformat(due_date)
   except ValueError:raise Denied('INVALID_REQUEST',422) from None
  r=self.add(B.requests,company_id=cid,input_version_id=input_version_id,improvement_version_id=improvement_version_id,file_id=file_id,actor_id=who.id,title=title.strip(),message=message.strip(),due_date=due_date,state='DRAFT',response_ordinal=0)
  self.record(who,cid,'CREATE_INFORMATION_REQUEST');return r
 def information_send(self,who,key):
  self.role(who,'DATCO_OPERATOR');r=self.get(B.requests,key);self.scope(who,r['company_id'],True);r=self.get(B.requests,key,True)
  if r['state']!='DRAFT':raise Denied('TRANSITION_NOT_ALLOWED',409)
  self.session.execute(update(B.requests).where(B.requests.c.id==key).values(state='WAITING_RESPONSE',sent_by=who.id,sent_at=func.clock_timestamp()))
  self.record(who,r['company_id'],'SEND_INFORMATION_REQUEST');return {'state':'WAITING_RESPONSE'}
 def information_respond(self,who,key,message,file_ids,expected,submit):
  self.role(who,'COMPANY_EDITOR');r=self.get(B.requests,key);self.scope(who,r['company_id'],True);r=self.get(B.requests,key,True)
  if r['state'] not in ('WAITING_RESPONSE','REVISION_REQUESTED'):raise Denied('TRANSITION_NOT_ALLOWED',409)
  if expected!=r['response_ordinal']:raise Denied('STALE_INPUT_VERSION',409)
  if not message.strip() or len(message)>10000 or len(file_ids)>100:raise Denied('INVALID_REQUEST',422)
  for fid in file_ids:
   f=self.get(S.files,fid)
   if f['company_id']!=r['company_id']:raise Denied('OBJECT_NOT_FOUND',404)
   self.active_file(fid)
  v=self.add(B.responses,company_id=r['company_id'],request_id=key,actor_id=who.id,ordinal=expected+1,message=message.strip(),submitted=submit)
  for fid in set(file_ids):self.add(B.response_files,company_id=r['company_id'],response_id=v['id'],file_id=fid)
  state='REVIEW_REQUIRED' if submit else r['state']
  self.session.execute(update(B.requests).where(B.requests.c.id==key).values(response_ordinal=expected+1,state=state))
  self.record(who,r['company_id'],'SUBMIT_INFORMATION_RESPONSE' if submit else 'SAVE_INFORMATION_RESPONSE');return dict(v,state=state)
 def information_review(self,who,key,response_id,outcome,note):
  self.role(who,'DATCO_OPERATOR');r=self.get(B.requests,key);self.scope(who,r['company_id'],True);r=self.get(B.requests,key,True)
  v=self.get(B.responses,response_id)
  if v['request_id']!=key:raise Denied('OBJECT_NOT_FOUND',404)
  if r['state']!='REVIEW_REQUIRED' or v['ordinal']!=r['response_ordinal'] or not v['submitted']:raise Denied('STALE_INPUT_VERSION',409)
  if outcome not in ('VERIFIED','REVISION_REQUESTED') or not note.strip() or len(note)>5000:raise Denied('INVALID_REQUEST',422)
  review=self.add(B.request_reviews,request_id=key,response_id=response_id,actor_id=who.id,outcome=outcome,note=note.strip())
  self.session.execute(update(B.requests).where(B.requests.c.id==key).values(state=outcome))
  self.record(who,r['company_id'],'REVIEW_INFORMATION_RESPONSE');return dict(review,state=outcome)
