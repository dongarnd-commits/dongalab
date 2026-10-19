"""Company application commands. Caller owns commit/rollback; all scope is server-read."""
from datetime import date
from decimal import Decimal,InvalidOperation
from hashlib import sha256
import re
from io import BytesIO
import warnings
from PIL import Image
from sqlalchemy import select,insert,update,text
from app.infrastructure import company_schema as S
from app.infrastructure.notice_schema import actors,identity
from app.notice.domain import Denied
from app.company.documents import parse_document,DocumentError,MAX_UPLOAD
from app.company.contracts import Profile,Site,FactInput,Improvement

class CompanyApplication:
 def __init__(self,session,files):self.session=session;self.files=files
 def rows(self,t,**where):return [dict(r) for r in self.session.execute(select(t).where(*[t.c[k]==v for k,v in where.items()]).order_by(t.c.created_at,t.c.id)).mappings()]
 def get(self,t,key,lock=False):
  q=select(t).where(t.c.id==key);r=self.session.execute(q.with_for_update() if lock else q).mappings().first()
  if not r:raise Denied('OBJECT_NOT_FOUND',404)
  return dict(r)
 def add(self,t,**data):
  data.setdefault('id',identity());return dict(self.session.execute(insert(t).values(**data).returning(t)).mappings().one())
 def role(self,who,*roles):
  if who.role not in roles:raise Denied('ACTION_NOT_AUTHORIZED',403)
 def scope(self,who,company_id,write=False):
  self.role(who,*(['COMPANY_EDITOR','DATCO_OPERATOR'] if write else ['COMPANY_EDITOR','COMPANY_APPROVER','DATCO_OPERATOR']))
  if not self.rows(S.memberships,company_id=company_id,actor_id=who.id):raise Denied('OBJECT_NOT_FOUND',404)
  return self.get(S.companies,company_id,write)
 def site(self,company_id,site_id):
  if site_id and self.get(S.sites,site_id)['company_id']!=company_id:raise Denied('OBJECT_NOT_FOUND',404)
 def record(self,who,company_id,action,**targets):self.add(S.audit,actor_id=who.id,company_id=company_id,action=action,**targets)
 def listing(self,who,q=''):
  self.role(who,'COMPANY_EDITOR','COMPANY_APPROVER','DATCO_OPERATOR')
  ids={m['company_id'] for m in self.rows(S.memberships,actor_id=who.id)}
  return [c for c in self.rows(S.companies) if c['id'] in ids and q.casefold() in c['name'].casefold()]
 def grant(self,who,company_id,username):
  self.role(who,'DATCO_ADMIN');self.get(S.companies,company_id,True)
  users=self.rows(actors,username=username)
  if len(users)!=1 or users[0]['role'] not in ('COMPANY_EDITOR','COMPANY_APPROVER','DATCO_OPERATOR'):raise Denied('INVALID_MEMBERSHIP_TARGET',422)
  existing=self.rows(S.memberships,company_id=company_id,actor_id=users[0]['id'])
  if not existing:self.add(S.memberships,company_id=company_id,actor_id=users[0]['id'],granted_by=who.id)
  self.record(who,company_id,'GRANT_COMPANY_ACCESS');return {'ok':True}
 def register(self,who,data):
  self.role(who,'COMPANY_EDITOR');data=Profile.model_validate(data).model_dump()
  self.session.execute(text('SELECT pg_advisory_xact_lock(:k)'),{'k':int.from_bytes(sha256(data['business_number'].encode()).digest()[:8],'big',signed=True)})
  if self.rows(S.companies,business_number=data['business_number']):raise Denied('COMPANY_ALREADY_REGISTERED',409)
  root=self.add(S.companies,business_number=data['business_number'],name=data['name'],current_ordinal=0)
  self.add(S.memberships,company_id=root['id'],actor_id=who.id,granted_by=who.id)
  self.save_profile(who,root['id'],data,0);return self.get(S.companies,root['id'])
 def save_profile(self,who,cid,data,expected):
  self.role(who,'COMPANY_EDITOR');root=self.scope(who,cid,True);data=Profile.model_validate(data).model_dump()
  if expected!=root['current_ordinal']:raise Denied('STALE_INPUT_VERSION',409)
  if data['business_number']!=root['business_number']:raise Denied('BUSINESS_IDENTITY_CHANGE_REQUIRES_REVIEW',409)
  ordinal=expected+1;v=self.add(S.inputs,company_id=cid,site_id=None,ordinal=ordinal,data=data,actor_id=who.id)
  self.session.execute(update(S.companies).where(S.companies.c.id==cid).values(name=data['name'],current_ordinal=ordinal))
  values=[('company_name',data['name'],'','',''),('industry',data['industry'],'','',''),('representative',data['representative'],'','','')]
  values += [('revenue',f['revenue'],f['period'],f['unit'],f['currency']) for f in data['financials']]
  values += [('support_history',h['name'],h['period'],'','') for h in data['history']]
  for field,value,period,unit,currency in values:
   if not value:continue
   e=self.add(S.evidence,actor_id=who.id,company_id=cid,site_id=None,file_id=None,input_version_id=v['id'],parse_id=None,descriptor='Company input: '+field,text=value,mode='COMPANY_INPUT')
   self.add(S.candidates,company_id=cid,site_id=None,evidence_id=e['id'],field=field,value=value,period=period,unit=unit,currency=currency,valid_from=date.today().isoformat(),mode='COMPANY_INPUT',actor_id=who.id)
  self.record(who,cid,'SAVE_COMPANY_INPUT',input_version_id=v['id']);return v
 def save_site(self,who,cid,data,site_id=None,expected=0):
  self.role(who,'COMPANY_EDITOR');self.scope(who,cid,True);data=Site.model_validate(data).model_dump()
  if site_id:
   self.site(cid,site_id);root=self.get(S.sites,site_id,True)
   if expected!=root['current_ordinal']:raise Denied('STALE_INPUT_VERSION',409)
  else:root=self.add(S.sites,company_id=cid,name=data['name'],current_ordinal=0)
  v=self.add(S.site_versions,site_id=root['id'],ordinal=expected+1,data=data,actor_id=who.id)
  self.session.execute(update(S.sites).where(S.sites.c.id==root['id']).values(name=data['name'],current_ordinal=expected+1))
  self.record(who,cid,'SAVE_COMPANY_SITE');return {'site':self.get(S.sites,root['id']),'version':v}
 def upload(self,who,cid,name,raw,site_id=None):
  self.role(who,'COMPANY_EDITOR');self.scope(who,cid,True);self.site(cid,site_id)
  if not name or len(name)>200 or '/' in name or '\\' in name or any(ord(c)<32 for c in name):raise Denied('INVALID_FILENAME',422)
  if not raw or len(raw)>MAX_UPLOAD:raise Denied('UPLOAD_SIZE_INVALID',422)
  try:parsed=parse_document(name,raw)
  except DocumentError as e:raise Denied(str(e),422) from None
  if parsed.format in ('png','jpg','jpeg'):
   try:
    with warnings.catch_warnings():
     warnings.simplefilter('error',Image.DecompressionBombWarning)
     with Image.open(BytesIO(raw)) as image:
      if image.width*image.height>20_000_000:raise ValueError('IMAGE_PIXEL_LIMIT')
      image.verify()
     with Image.open(BytesIO(raw)) as image:image.load()
   except (OSError,ValueError,Image.DecompressionBombError,Image.DecompressionBombWarning):raise Denied('INVALID_IMAGE_CONTENT',422) from None
  digest=sha256(raw).hexdigest();old=self.rows(S.files,company_id=cid,digest=digest)
  if old:raise Denied('DUPLICATE_COMPANY_FILE',409)
  key,digest=self.files.put(raw)
  mime={'pdf':'application/pdf','docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document','xlsx':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','txt':'text/plain','png':'image/png','jpg':'image/jpeg','jpeg':'image/jpeg'}[parsed.format]
  f=self.add(S.files,company_id=cid,site_id=site_id,name=name,media_type=mime,storage_key=key,digest=digest,size=len(raw),actor_id=who.id)
  self.record(who,cid,'UPLOAD_COMPANY_FILE',file_id=f['id']);return f
 def download(self,who,file_id):
  f=self.get(S.files,file_id);self.scope(who,f['company_id']);return f,self.files.read(f['storage_key'],f['digest'])
 def parse(self,who,file_id):
  f=self.get(S.files,file_id);self.scope(who,f['company_id'],True)
  try:p=parse_document(f['name'],self.files.read(f['storage_key'],f['digest']))
  except DocumentError as e:
   return self.add(S.parses,file_id=file_id,actor_id=who.id,parser_version='company-local-parser-v1',error=str(e),limitations=[])
  run=self.add(S.parses,file_id=file_id,actor_id=who.id,parser_version=p.parser_version,error=None,limitations=list(p.limitations))
  analysis_run=None
  for loc in p.locations:
   e=self.add(S.evidence,actor_id=who.id,company_id=f['company_id'],site_id=f['site_id'],file_id=file_id,input_version_id=None,parse_id=run['id'],descriptor=loc.descriptor,page=loc.page,text=loc.text,mode='RULE_BASED_EXTRACTION')
   # Only explicit labelled text, no inferred units/years or eligibility.
   labels={'회사명':'company_name','기업명':'company_name','업종':'industry','소재지':'address','대표자':'representative','사업자번호':'business_number','사업자등록번호':'business_number','상호':'company_name','상호명':'company_name','사업장 소재지':'address','직원수':'employees','근로자수':'employees'}
   for line in loc.text.splitlines():
    m=re.fullmatch(r'\s*([^:：]{1,20})[:：]\s*(.{1,500})\s*',line)
    financial=re.fullmatch(r'\s*매출액\s*\(\s*([0-9]{4})\s*,\s*([^,()]{1,30})\s*,\s*([^,()]{1,10})\s*\)[:：]\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*',line)
    field=labels.get(m[1].strip()) if m else None
    value=m[2].strip() if field else None
    period=unit=currency=''
    if financial and 1900<=int(financial[1])<=2200:
     field='revenue';period,unit,currency,value=[x.strip() for x in financial.groups()]
    if field:
     from app.infrastructure import notice_schema as N
     if analysis_run is None:
      analysis_run=self.add(N.runs,analysis_kind='COMPANY_FACT_EXTRACTION',actor_id=who.id,provider_version='company-labelled-rule-v2',extractor_version=p.parser_version,missing=list(p.limitations),conflicts=[])
      self.add(S.analysis_contexts,run_id=analysis_run['id'],file_id=file_id,parse_id=run['id'],company_id=f['company_id'])
     aid=identity()
     c=self.add(S.candidates,company_id=f['company_id'],site_id=f['site_id'],evidence_id=e['id'],field=field,value=value,period=period,unit=unit,currency=currency,valid_from=date.today().isoformat(),mode='RULE_BASED_EXTRACTION',actor_id=who.id,analysis_candidate_id=aid)
     self.add(N.candidates,id=aid,run_id=analysis_run['id'],analysis_kind='COMPANY_FACT_EXTRACTION',company_candidate_id=c['id'],kind='COMPANY_FACT_EXTRACTION',content=c['value'],reason='Exact labelled source value; rule-based candidate, not confirmed fact')
  self.record(who,f['company_id'],'PARSE_COMPANY_FILE',file_id=file_id);return run
 def manual_evidence(self,who,cid,file_id,site_id,descriptor,transcription):
  self.scope(who,cid,True);f=self.get(S.files,file_id);self.site(cid,site_id)
  if f['company_id']!=cid or (f['site_id'] and f['site_id']!=site_id):raise Denied('OBJECT_NOT_FOUND',404)
  self.files.read(f['storage_key'],f['digest'])
  return self.add(S.evidence,actor_id=who.id,company_id=cid,site_id=site_id,file_id=file_id,input_version_id=None,parse_id=None,descriptor=descriptor,text=transcription,mode='MANUAL_REVIEW')
 def new_candidate(self,who,cid,data):
  self.scope(who,cid,True);v=FactInput.model_validate(data).model_dump(mode='json');e=self.get(S.evidence,v['evidence_id']);self.site(cid,v['site_id'])
  if e['company_id']!=cid or (e['site_id'] and e['site_id']!=v['site_id']):raise Denied('OBJECT_NOT_FOUND',404)
  if v['value'] not in e['text']:raise Denied('EXTRACTED_VALUE_NOT_IN_EVIDENCE',422)
  c=self.add(S.candidates,company_id=cid,mode='MANUAL_REVIEW',actor_id=who.id,**v)
  self.record(who,cid,'CREATE_FACT_CANDIDATE',candidate_id=c['id']);return c
 def acknowledge(self,who,key,agreed,note):
  self.role(who,'COMPANY_EDITOR');c=self.get(S.candidates,key);self.scope(who,c['company_id'],True)
  r=self.add(S.acknowledgements,candidate_id=key,actor_id=who.id,agreed=agreed,note=note);self.record(who,c['company_id'],'ACKNOWLEDGE_FACT',candidate_id=key);return r
 def current_fact(self,version_id):
  v=self.get(S.fact_versions,version_id);root=self.get(S.facts,v['fact_id']);eid,_=self.fact_evidence(v)
  return v,root,v['ordinal']==root['current_ordinal'] and self.evidence_current(eid)
 def fact_evidence(self,version):
  if self.evidence_current(version['evidence_id']):return version['evidence_id'],version['review_id']
  for r in reversed(self.rows(S.reviews,existing_version_id=version['id'],outcome='CONFIRM_EXISTING_VALUE')):
   c=self.get(S.candidates,r['candidate_id'])
   if c['value']==version['value'] and self.evidence_current(c['evidence_id']):return c['evidence_id'],r['id']
  return version['evidence_id'],version['review_id']
 def evidence_current(self,eid):
  e=self.get(S.evidence,eid)
  if e['input_version_id']:
   v=self.get(S.inputs,e['input_version_id']);return v['ordinal']==self.get(S.companies,e['company_id'])['current_ordinal']
  f=self.get(S.files,e['file_id']);self.files.read(f['storage_key'],f['digest']);return True
 def review(self,who,key,outcome,note,existing_version_id=None):
  self.role(who,'DATCO_OPERATOR');c=self.get(S.candidates,key);self.scope(who,c['company_id'],True)
  if outcome not in ('CONFIRM_NEW_VALUE','CONFIRM_EXISTING_VALUE','CONFLICT','REQUEST_MORE_INFORMATION','REJECT_CANDIDATE') or not note.strip():raise Denied('INVALID_REVIEW',422)
  if outcome.startswith('CONFIRM') and c['field'] in ('revenue','assets','liabilities','employees'):
   try:
    if not Decimal(c['value'].replace(',','')).is_finite():raise InvalidOperation
   except InvalidOperation:raise Denied('FINANCIAL_VALUE_MUST_BE_NUMERIC',422) from None
  acks=self.rows(S.acknowledgements,candidate_id=key)
  if outcome.startswith('CONFIRM') and (not acks or not acks[-1]['agreed'] or not self.evidence_current(c['evidence_id'])):raise Denied('COMPANY_CONFIRMATION_OR_CURRENT_EVIDENCE_REQUIRED',409)
  roots=self.rows(S.facts,company_id=c['company_id'],site_id=c['site_id'],field=c['field'],period=c['period'],unit=c['unit'],currency=c['currency'])
  root=roots[0] if roots else None
  if existing_version_id:
   old,oldroot,current=self.current_fact(existing_version_id)
   if not root or oldroot['id']!=root['id'] or old['ordinal']!=oldroot['current_ordinal']:raise Denied('STALE_INPUT_VERSION',409)
  else:old=None
  if outcome=='CONFIRM_EXISTING_VALUE' and (not old or old['value']!=c['value']):raise Denied('FACT_VALUE_MISMATCH',409)
  if outcome=='CONFIRM_NEW_VALUE' and root and root['current_ordinal']>0 and not existing_version_id:raise Denied('EXISTING_FACT_COMPARISON_REQUIRED',409)
  if outcome=='CONFLICT' and not old:raise Denied('EXISTING_FACT_COMPARISON_REQUIRED',409)
  previous=self.rows(S.reviews,candidate_id=key,outcome=outcome)
  if previous:
   r=previous[0]
   if r['note']!=note or r['existing_version_id']!=existing_version_id:raise Denied('REVIEW_ALREADY_RECORDED',409)
   versions=self.rows(S.fact_versions,review_id=r['id']);return {'review':r,'version':versions[0] if versions else None}
  r=self.add(S.reviews,candidate_id=key,actor_id=who.id,outcome=outcome,note=note,existing_version_id=existing_version_id)
  if c.get('analysis_candidate_id'):
   from app.infrastructure import notice_schema as N,analysis_schema as A
   common=self.add(N.reviews,candidate_id=c['analysis_candidate_id'],actor_id=who.id,analysis_kind='COMPANY_FACT_EXTRACTION',outcome=None,official_verified=None,note=note)
   self.add(A.review_contexts,review_id=common['id'],company_review_id=r['id'])
  version=None
  if outcome=='CONFIRM_NEW_VALUE':
   if not root:root=self.add(S.facts,company_id=c['company_id'],site_id=c['site_id'],field=c['field'],period=c['period'],unit=c['unit'],currency=c['currency'],current_ordinal=0)
   version=self.add(S.fact_versions,fact_id=root['id'],ordinal=root['current_ordinal']+1,review_id=r['id'],candidate_id=key,evidence_id=c['evidence_id'],value=c['value'],valid_from=c['valid_from'])
   self.session.execute(update(S.facts).where(S.facts.c.id==root['id']).values(current_ordinal=version['ordinal']))
  self.record(who,c['company_id'],'REVIEW_COMPANY_FACT',fact_review_id=r['id']);return {'review':r,'version':version}
 def detail(self,who,cid):
  root=self.scope(who,cid);sites=self.rows(S.sites,company_id=cid);files=self.rows(S.files,company_id=cid);facts=self.rows(S.facts,company_id=cid);candidates=self.rows(S.candidates,company_id=cid);improvements=self.rows(S.improvements,company_id=cid)
  result={'company':root,'inputs':self.rows(S.inputs,company_id=cid),'sites':[dict(s,versions=self.rows(S.site_versions,site_id=s['id'])) for s in sites],
   'files':[dict(f,parses=self.rows(S.parses,file_id=f['id'])) for f in files],'evidence':self.rows(S.evidence,company_id=cid),
   'candidates':[dict(c,acknowledgements=self.rows(S.acknowledgements,candidate_id=c['id']),reviews=self.rows(S.reviews,candidate_id=c['id'])) for c in candidates],
   'facts':[dict(f,versions=[dict(v,current_valid=self.current_fact(v['id'])[2],review=self.get(S.reviews,v['review_id'])) for v in self.rows(S.fact_versions,fact_id=f['id'])]) for f in facts],
   'improvements':[dict(i,versions=[dict(v,reviews=self.rows(S.improvement_reviews,version_id=v['id'])) for v in self.rows(S.improvement_versions,improvement_id=i['id'])]) for i in improvements], 'audit':self.rows(S.audit,company_id=cid) if who.role=='DATCO_OPERATOR' else []}

  actor_ids=set()
  def collect(value):
   if isinstance(value,dict):
    if value.get('actor_id'):actor_ids.add(value['actor_id'])
    for child in value.values():collect(child)
   elif isinstance(value,list):
    for child in value:collect(child)
  collect(result)
  names=dict(self.session.execute(select(actors.c.id,actors.c.username).where(actors.c.id.in_(actor_ids))).all()) if actor_ids else {}
  def label(value):
   if isinstance(value,dict):
    if value.get('actor_id'):value['actor_name']=names.get(value['actor_id'],'Historical actor')
    for child in list(value.values()):label(child)
   elif isinstance(value,list):
    for child in value:label(child)
  label(result)
  if who.role=='COMPANY_APPROVER':
   result['files']=[];result['evidence']=[];result['candidates']=[];result['inputs']=[]
   result['improvements']=[i for i in result['improvements'] if i['state']=='CONFIRMED']
  return result
 def save_improvement(self,who,cid,data,key=None,expected=0):
  self.role(who,'COMPANY_EDITOR','DATCO_OPERATOR');self.scope(who,cid,True);data=Improvement.model_validate(data).model_dump();self.site(cid,data['site_id'])
  if key:
   root=self.get(S.improvements,key,True)
   if root['company_id']!=cid:raise Denied('OBJECT_NOT_FOUND',404)
   if root['current_ordinal']!=expected:raise Denied('STALE_INPUT_VERSION',409)
   previous=self.rows(S.improvement_versions,improvement_id=key)[-1]
   if data['site_id']!=root['site_id']:raise Denied('IMPROVEMENT_SITE_CHANGE_REQUIRES_NEW_ROOT',409)
   if who.role=='DATCO_OPERATOR':
    if root['state'] not in ('SUBMITTED','REVIEW_REQUIRED'):raise Denied('TRANSITION_NOT_ALLOWED',409)
    if data['original_text']!=previous['data']['original_text'] or data['site_id']!=root['site_id']:raise Denied('ORIGINAL_COMPANY_INPUT_IS_IMMUTABLE',409)
  else:
   self.role(who,'COMPANY_EDITOR');root=self.add(S.improvements,company_id=cid,site_id=data['site_id'],title=data['title'],current_ordinal=0,state='DRAFT')
  for fid in data['fact_version_ids']:
   v,f,current=self.current_fact(fid)
   if f['company_id']!=cid or (f['site_id'] and f['site_id']!=data['site_id']):raise Denied('OBJECT_NOT_FOUND',404)
   if not current:raise Denied('STALE_INPUT_VERSION',409)
  for eid in data['evidence_ids']:
   e=self.get(S.evidence,eid)
   if e['company_id']!=cid or (e['site_id'] and e['site_id']!=data['site_id']):raise Denied('OBJECT_NOT_FOUND',404)
   if not self.evidence_current(eid):raise Denied('STALE_INPUT_VERSION',409)
  v=self.add(S.improvement_versions,improvement_id=root['id'],ordinal=expected+1,data=data,actor_id=who.id,site_ordinal=self.get(S.sites,data['site_id'])['current_ordinal'])
  for fid in set(data['fact_version_ids']):self.add(S.improvement_facts,version_id=v['id'],fact_version_id=fid)
  for eid in set(data['evidence_ids']):self.add(S.improvement_evidence,version_id=v['id'],evidence_id=eid)
  self.session.execute(update(S.improvements).where(S.improvements.c.id==root['id']).values(current_ordinal=expected+1,title=data['title'],site_id=data['site_id'],state='REVIEW_REQUIRED' if who.role=='DATCO_OPERATOR' else 'DRAFT'))
  if who.role=='DATCO_OPERATOR':self.add(S.improvement_reviews,version_id=v['id'],actor_id=who.id,outcome='MANUAL_STRUCTURE',note='Manual structuring; no AI execution')
  self.record(who,cid,'SAVE_IMPROVEMENT_VERSION',improvement_version_id=v['id']);return v
 def improvement_action(self,who,version_id,action,note):
  v=self.get(S.improvement_versions,version_id);root=self.get(S.improvements,v['improvement_id']);self.scope(who,root['company_id'],True);root=self.get(S.improvements,root['id'],True)
  if v['ordinal']!=root['current_ordinal']:raise Denied('STALE_INPUT_VERSION',409)
  state=root['state']
  if action=='SUBMIT':
   self.role(who,'COMPANY_EDITOR')
   if state!='DRAFT':raise Denied('TRANSITION_NOT_ALLOWED',409)
   new='SUBMITTED'
  elif action=='ACKNOWLEDGE':
   self.role(who,'COMPANY_EDITOR')
   if state!='REVIEW_REQUIRED':raise Denied('TRANSITION_NOT_ALLOWED',409)
   new=state
  elif action=='CONFIRM':
   self.role(who,'DATCO_OPERATOR')
   if state!='REVIEW_REQUIRED':raise Denied('TRANSITION_NOT_ALLOWED',409)
   if not all(v['data'][k].strip() for k in ('as_is','problem','goal','to_be')) or v['data']['missing'].strip() or not v['data']['evidence_ids']:raise Denied('MISSING_REQUIRED_INFORMATION',409)
   if not self.rows(S.improvement_reviews,version_id=version_id,outcome='ACKNOWLEDGE'):raise Denied('COMPANY_CONFIRMATION_REQUIRED',409)
   for fid in v['data']['fact_version_ids']:
    if not self.current_fact(fid)[2]:raise Denied('STALE_INPUT_VERSION',409)
   if not all(self.evidence_current(eid) for eid in v['data']['evidence_ids']):raise Denied('STALE_INPUT_VERSION',409)
   new='CONFIRMED'
  elif action=='REQUEST_REVISION':
   self.role(who,'DATCO_OPERATOR')
   if state not in ('SUBMITTED','REVIEW_REQUIRED'):raise Denied('TRANSITION_NOT_ALLOWED',409)
   new='REVISION_REQUIRED'
  else:raise Denied('INVALID_REQUEST',422)
  if not note.strip():raise Denied('REVIEW_NOTE_REQUIRED',422)
  r=self.add(S.improvement_reviews,version_id=version_id,actor_id=who.id,outcome=action,note=note)
  self.session.execute(update(S.improvements).where(S.improvements.c.id==root['id']).values(state=new))
  self.record(who,root['company_id'],'IMPROVEMENT_'+action,improvement_version_id=version_id);return {'state':new,'review':r}
