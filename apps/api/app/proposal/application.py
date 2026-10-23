"""Versioned Proposal use cases in the caller-owned PostgreSQL transaction."""
from dataclasses import asdict
from datetime import datetime,timezone
from sqlalchemy import select,update
from app.capability.application import CapabilityApplication,fingerprint,frozen_json
from app.capability.proposal import proposal_blockers
from app.infrastructure import proposal_schema as P,capability_schema as S,notice_schema as N
from app.notice.domain import Denied
from app.proposal.policy import basis
from app.proposal.documents import draft,validate,render

class ProposalApplication:
 def __init__(self,capability):self.s=capability
 def operator(self,actor):self.s.operator(actor)
 def root(self,actor,key,lock=False):
  root=self.s.get(P.roots,key,lock);versions=self.s.rows(P.versions,proposal_id=key)
  if not versions:raise Denied('OBJECT_NOT_FOUND',404)
  latest=max(versions,key=lambda v:v['ordinal']);context=latest['manifest']['input']['company']
  b=basis(self.s,actor,root['company_id'],context['improvement_version_id'])
  if actor.role not in ('DATCO_OPERATOR','COMPANY_APPROVER','COMPANY_EDITOR'):raise Denied('ACTION_NOT_AUTHORIZED',403)
  return root,versions,b
 def locked_match(self,actor,candidate_id):
  self.operator(actor);candidate=self.s.get(S.match_candidates,candidate_id);snap=self.s.get(S.match_snapshots,candidate['snapshot_id']);cv=self.s.get(S.composition_versions,snap['composition_version_id'])
  self.s.composition(actor,cv['composition_id']);self.s.get(S.compositions,cv['composition_id'],True)
  for cid in sorted({self.s.get(S.versions,l['capability_version_id'])['capability_id'] for l in self.s.rows(S.composition_links,version_id=cv['id'])}):self.s.get(S.capabilities,cid,True)
  self.s.get(N.notices,snap['input']['notice']['notice_id'],True);self.s.get(S.match_candidates,candidate_id,True)
  detail=self.s.match(actor,candidate_id);blockers=proposal_blockers(detail,self.s,actor)
  if blockers:raise Denied(blockers[0])
  review=max(detail['reviews'],key=lambda r:(r['created_at'],r['id']))
  return detail,review
 def manifest(self,detail,review):
  snap=detail['snapshot'];cv=self.s.get(S.composition_versions,snap['composition_version_id']);caps=[self.s.get(S.versions,l['capability_version_id']) for l in self.s.rows(S.composition_links,version_id=cv['id'])]
  features=[self.s.get(S.revisions,l['revision_id']) for c in caps for l in self.s.rows(S.links,version_id=c['id'])]
  refs=dict(company_id=snap['input']['company']['company_id'],fact_version_ids=snap['input']['company'].get('fact_version_ids',[]),improvement_version_id=cv['improvement_version_id'],capability_version_ids=[c['id'] for c in caps],feature_revision_ids=[f['id'] for f in features],composition_version_id=cv['id'],notice_version_id=snap['input']['notice']['notice_version_id'],requirement_version_id=snap['requirement_version_id'],match_snapshot_id=snap['id'],match_candidate_id=detail['candidate']['id'],match_review_id=review['id'],evidence_ids=[i['evidence']['id'] for i in snap['input']['notice']['items']])
  return frozen_json(dict(refs=refs,input=snap['input'],notice_title=self.s.get(N.notices,snap['input']['notice']['notice_id'])['title'],capability_versions=caps,feature_revisions=features,match_review=review))
 def write_version(self,actor,root,detail,review,title,sections=None):
  title=title.strip()
  if not title or len(title)>500:raise Denied('INVALID_REQUEST',422)
  manifest=self.manifest(detail,review);sections=sections if sections is not None else draft(manifest)
  validate(sections)
  # Client cannot replace source references while editing prose.
  sections=[dict(s,evidence_refs=manifest['refs']) for s in sections]
  ordinal=root['current_ordinal'];digest=fingerprint(dict(title=title,sections=sections,manifest=manifest))
  version=self.s.add(P.versions,proposal_id=root['id'],ordinal=ordinal,match_snapshot_id=detail['snapshot']['id'],match_review_id=review['id'],title=title,sections=sections,manifest=manifest,content_digest=digest,actor_id=actor.id)
  self.s.record(actor,'CREATE_PROPOSAL_VERSION',proposal_id=root['id'],version_id=version['id'])
  return dict(proposal_id=root['id'],version_id=version['id'],ordinal=ordinal)
 def create(self,actor,candidate_id,title,key):
  self.operator(actor);self.s.match(actor,candidate_id)
  def execute():
   detail,review=self.locked_match(actor,candidate_id);context=detail['snapshot']['input']['company'];basis(self.s,actor,context['company_id'],context['improvement_version_id'])
   root=self.s.add(P.roots,company_id=context['company_id'],match_review_id=review['id'],current_ordinal=1)
   return self.write_version(actor,root,detail,review,title)
  return self.s.command(actor,key,['CREATE_PROPOSAL',candidate_id,title],execute)
 def save(self,actor,key,expected_version,title,sections,idempotency_key,candidate_id=None):
  self.operator(actor);self.root(actor,key)
  def execute():
   root,versions,_=self.root(actor,key,True);previous=max(versions,key=lambda v:v['ordinal'])
   if previous['id']!=expected_version:raise Denied('STALE_INPUT_VERSION')
   candidate=candidate_id or previous['manifest']['refs']['match_candidate_id'];detail,review=self.locked_match(actor,candidate)
   if detail['snapshot']['input']['company']['company_id']!=root['company_id']:raise Denied('OBJECT_NOT_FOUND',404)
   for request in self.s.rows(P.requests,version_id=previous['id']):
    if request['state']=='OPEN':self.s.session.execute(update(P.requests).where(P.requests.c.id==request['id']).values(state='CLOSED',closure_reason='SUPERSEDED'))
   root=dict(root,current_ordinal=root['current_ordinal']+1,match_review_id=review['id'])
   self.s.session.execute(update(P.roots).where(P.roots.c.id==key).values(current_ordinal=root['current_ordinal'],match_review_id=review['id']))
   return self.write_version(actor,root,detail,review,title,sections)
  return self.s.command(actor,idempotency_key,['SAVE_PROPOSAL',key,expected_version,title,sections,candidate_id],execute)
 def version(self,actor,key):
  v=self.s.get(P.versions,key);root,_,b=self.root(actor,v['proposal_id'])
  if actor.role!='DATCO_OPERATOR':
   requests=self.s.rows(P.requests,version_id=key)
   allowed=any(r['intended_approver']==actor.id and ((actor.role=='COMPANY_APPROVER' and r.get('approval_mode','DIRECT_APPROVER')=='DIRECT_APPROVER' and b.approver_id==actor.id) or (actor.role=='COMPANY_EDITOR' and r.get('approval_mode')=='COMPANY_RECORDED_AUTHORIZATION')) for r in requests)
   if not allowed:raise Denied('OBJECT_NOT_FOUND',404)
   if actor.role=='COMPANY_EDITOR':return dict(id=v['id'],proposal_id=v['proposal_id'],ordinal=v['ordinal'],title=v['title'],sections=[dict(heading=section['heading'],body=section['body']) for section in v['sections']],content_digest=v['content_digest'],created_at=v['created_at'])
   return dict(id=v['id'],proposal_id=v['proposal_id'],ordinal=v['ordinal'],title=v['title'],sections=v['sections'],content_digest=v['content_digest'],manifest={'refs':v['manifest']['refs']},created_at=v['created_at'])
  return v
 def detail(self,actor,key):
  if actor.role=='COMPANY_EDITOR':raise Denied('OBJECT_NOT_FOUND',404)
  root,versions,b=self.root(actor,key)
  visible=[]
  for v in sorted(versions,key=lambda x:x['ordinal']):
   try:visible.append(self.version(actor,v['id']))
   except Denied as e:
    if e.status!=404:raise
  if not visible:raise Denied('OBJECT_NOT_FOUND',404)
  ids={v['id'] for v in visible}
  requests=[r for v in visible for r in self.s.rows(P.requests,version_id=v['id'])]
  result=dict(root=root,versions=visible,content_reviews=[r for v in visible for r in sorted(self.s.rows(P.reviews,version_id=v['id']),key=lambda r:(r['created_at'],r['id']))] if actor.role=='DATCO_OPERATOR' else [],requests=requests,decisions=[d for v in visible for d in self.s.rows(P.decisions,version_id=v['id'])],files=[{k:x for k,x in f.items() if k not in ('storage_key',)} for v in visible for f in self.s.rows(P.files,version_id=v['id'])],approver_id=b.approver_id,current_version_visible=any(v['ordinal']==root['current_ordinal'] for v in visible))
  if actor.role=='DATCO_OPERATOR':
   result['recorded_authorizations']=[dict(decision_id=d['id'],version_id=d['version_id'],**proof) for v in visible for d in self.s.rows(P.decisions,version_id=v['id']) if (proof:=self._recorded_authorization(d['id'])) is not None]
  return result
 def _recorded_authorization(self,decision_id):
  rows=self.s.rows(P.authorizations,decision_id=decision_id)
  if not rows:return None
  row=rows[0]
  return dict(actual_approver_name=row['actual_approver_name'],actual_approver_title=row['actual_approver_title'],approved_at=row['approved_at'],method=row['method'],context=row['context'],file_id=row['file_id'],recorded_at=row['created_at'],recorder_name=self.s.get(N.actors,row['recorder_id'])['username'])
 def company_inbox(self,actor,company_id):
  # Explicit sent-version whitelist; never return detail(), root, internal
  # reviews, manifest or source references to the company Inbox.
  from app.company.application import CompanyApplication
  app=CompanyApplication(self.s.session,self.s.files);app.role(actor,'COMPANY_EDITOR','COMPANY_APPROVER');app.scope(actor,company_id)
  result=[]
  for request in self.s.rows(P.requests,intended_approver=actor.id):
   mode=request.get('approval_mode','DIRECT_APPROVER')
   if not ((actor.role=='COMPANY_EDITOR' and mode=='COMPANY_RECORDED_AUTHORIZATION') or (actor.role=='COMPANY_APPROVER' and mode=='DIRECT_APPROVER')):continue
   raw=self.s.get(P.versions,request['version_id']);root=self.s.get(P.roots,raw['proposal_id'])
   if root['company_id']!=company_id:continue
   try:visible=self.version(actor,raw['id'])
   except Denied as error:
    if error.status==404:continue
    raise
   result.append(dict(version_id=visible['id'],ordinal=visible['ordinal'],title=visible['title'],created_at=visible['created_at'],sections=[dict(heading=section['heading'],body=section['body']) for section in visible['sections']],approval=dict(id=request['id'],mode=mode,state=request['state'],closure_reason=request['closure_reason']),files=[dict(id=f['id'],kind=f['kind']) for f in self.s.rows(P.files,version_id=visible['id'])],decisions=[dict(outcome=d['outcome'],reason=d['reason'],created_at=d['created_at'],authorization=self._recorded_authorization(d['id'])) for d in self.s.rows(P.decisions,request_id=request['id'])]))
  return result
 def listing(self,actor,company_id,improvement_version_id):
  basis(self.s,actor,company_id,improvement_version_id)
  return [dict(id=r['id'],company_id=r['company_id'],current_ordinal=r['current_ordinal']) for r in self.s.rows(P.roots,company_id=company_id)] if actor.role=='DATCO_OPERATOR' else [dict(id=r['id'],company_id=r['company_id']) for r in self.s.rows(P.roots,company_id=company_id) if any(q['intended_approver']==actor.id for v in self.s.rows(P.versions,proposal_id=r['id']) for q in self.s.rows(P.requests,version_id=v['id']))]
 def current(self,actor,version_id):
  v=self.version(actor,version_id);root,_,_=self.root(actor,v['proposal_id'],True)
  if root['current_ordinal']!=v['ordinal']:raise Denied('STALE_INPUT_VERSION')
  detail,review=self.locked_match(actor,v['manifest']['refs']['match_candidate_id'])
  if review['id']!=v['match_review_id'] or detail['snapshot']['id']!=v['match_snapshot_id']:raise Denied('STALE_INPUT_VERSION')
  return v
 def review(self,actor,version_id,confirmed,note,key):
  self.operator(actor);self.version(actor,version_id)
  def execute():
   self.current(actor,version_id)
   if self.s.rows(P.requests,version_id=version_id):raise Denied('PROPOSAL_VERSION_LOCKED')
   if not note.strip():raise Denied('REQUIRED_DATA_MISSING')
   r=self.s.add(P.reviews,version_id=version_id,actor_id=actor.id,confirmed=confirmed,note=note,created_at=datetime.now(timezone.utc));self.s.record(actor,'REVIEW_PROPOSAL_CONTENT',review_id=r['id'],version_id=version_id);return dict(id=r['id'],confirmed=confirmed)
  return self.s.command(actor,key,['REVIEW_PROPOSAL_CONTENT',version_id,confirmed,note],execute)
 def confirmed_review(self,version_id):
  reviews=self.s.rows(P.reviews,version_id=version_id)
  if not reviews:raise Denied('PROPOSAL_CONTENT_NOT_REVIEWED')
  r=max(reviews,key=lambda x:(x['created_at'],x['id']))
  if not r['confirmed']:raise Denied('PROPOSAL_CONTENT_NOT_REVIEWED')
  return r
 def request(self,actor,version_id,key,approval_mode="DIRECT_APPROVER",recorder_id=None):
  self.operator(actor);self.version(actor,version_id)
  def execute():
   v=self.current(actor,version_id);self.confirmed_review(version_id);_,_,b=self.root(actor,v['proposal_id'])
   target=b.approver_id
   if approval_mode=='COMPANY_RECORDED_AUTHORIZATION':
    from app.infrastructure import company_schema as C
    target=recorder_id
    if not target or self.s.get(N.actors,target)['role']!='COMPANY_EDITOR' or not self.s.rows(C.memberships,company_id=b.company_id,actor_id=target):raise Denied('REQUIRED_RECORDER_NOT_CONFIGURED',422)
   elif approval_mode=='DIRECT_APPROVER':
    if recorder_id is not None:raise Denied('INVALID_REQUEST',422)
    if not target:raise Denied('REQUIRED_APPROVER_NOT_CONFIGURED')
    if self.s.get(N.actors,target)['role']!='COMPANY_APPROVER':raise Denied('ACTION_NOT_AUTHORIZED',403)
   else:raise Denied('INVALID_REQUEST',422)
   if self.s.rows(P.requests,version_id=version_id):raise Denied('APPROVAL_REQUEST_ALREADY_EXISTS')
   r=self.s.add(P.requests,version_id=version_id,intended_approver=target,approval_mode=approval_mode,requested_by=actor.id,state='OPEN',closure_reason=None);self.s.record(actor,'REQUEST_APPROVAL',request_id=r['id'],version_id=version_id);return dict(id=r['id'],version_id=version_id)
  scope=['REQUEST_APPROVAL',version_id] if approval_mode=='DIRECT_APPROVER' and recorder_id is None else ['REQUEST_APPROVAL',version_id,approval_mode,recorder_id]
  return self.s.command(actor,key,scope,execute)
 def decide(self,actor,request_id,outcome,reason,key,authorization=None):
  if actor.role not in ('COMPANY_APPROVER','COMPANY_EDITOR'):raise Denied('ACTION_NOT_AUTHORIZED',403)
  r=self.s.get(P.requests,request_id);v=self.version(actor,r['version_id'])
  def execute():
   root,_,b=self.root(actor,v['proposal_id'],True);current=self.s.get(P.requests,request_id,True)
   if current['intended_approver']!=actor.id or (current.get('approval_mode','DIRECT_APPROVER')=='DIRECT_APPROVER' and (actor.role!='COMPANY_APPROVER' or b.approver_id!=actor.id)) or (current.get('approval_mode')=='COMPANY_RECORDED_AUTHORIZATION' and actor.role!='COMPANY_EDITOR'):raise Denied('OBJECT_NOT_FOUND',404)
   if current['state']!='OPEN' or root['current_ordinal']!=v['ordinal']:raise Denied('APPROVAL_VERSION_MISMATCH')
   self.confirmed_review(v['id'])
   self.fresh_inputs(actor,self.s.get(P.versions,v['id']))
   if outcome not in ('APPROVE','REVISION_REQUEST','REJECT') or not reason.strip():raise Denied('INVALID_REQUEST',422)
   recorded=current.get('approval_mode')=='COMPANY_RECORDED_AUTHORIZATION'
   if recorded and outcome=='REJECT':raise Denied('ACTION_NOT_AUTHORIZED',403)
   proof=None
   if recorded and outcome=='APPROVE':
    from app.proposal.recorded_authorization import validate_authorization
    proof=validate_authorization(self.s,actor,b.company_id,authorization,v["created_at"])
   elif authorization is not None:raise Denied('INVALID_REQUEST',422)
   d=self.s.add(P.decisions,request_id=request_id,version_id=v['id'],actor_id=actor.id,outcome=outcome,reason=reason)
   if proof:self.s.add(P.authorizations,decision_id=d['id'],request_id=request_id,version_id=v['id'],recorder_id=actor.id,company_id=b.company_id,**proof)
   self.s.session.execute(update(P.requests).where(P.requests.c.id==request_id).values(state='CLOSED',closure_reason='DECIDED'));self.s.record(actor,'DECIDE_PROPOSAL',decision_id=d['id'],version_id=v['id']);return dict(id=d['id'],outcome=outcome)
  scope=['DECIDE_PROPOSAL',request_id,outcome,reason] if authorization is None else ['DECIDE_PROPOSAL',request_id,outcome,reason,authorization]
  return self.s.command(actor,key,scope,execute)
 def fresh_inputs(self,actor,v):
  from app.proposal.policy import verified_completion
  snap=self.s.get(S.match_snapshots,v['match_snapshot_id']);cv=self.s.get(S.composition_versions,snap['composition_version_id']);self.s.get(S.compositions,cv['composition_id'],True)
  current=self.s.get(S.compositions,cv['composition_id'])['current_ordinal']==cv['ordinal']
  for link in sorted(self.s.rows(S.composition_links,version_id=cv['id']),key=lambda l:self.s.get(S.versions,l['capability_version_id'])['capability_id']):
   capv=self.s.get(S.versions,link['capability_version_id']);root=self.s.get(S.capabilities,capv['capability_id'],True);current=current and root['current_ordinal']==capv['ordinal']
  notice=snap['input']['notice'];n=self.s.get(N.notices,notice['notice_id'],True);nv=self.s.get(N.versions,notice['notice_version_id']);rv=self.s.get(N.requirement_versions,snap['requirement_version_id'])
  current=current and n['current_ordinal']==nv['ordinal'] and rv['ordinal']==max(x['ordinal'] for x in self.s.rows(N.requirement_versions,requirement_id=rv['requirement_id']))
  candidate=self.s.get(S.match_candidates,v['manifest']['refs']['match_candidate_id'],True);reviews=self.s.rows(S.match_reviews,candidate_id=candidate['id']);latest=max(reviews,key=lambda r:(r['created_at'],r['id']))
  current=current and latest['id']==v['match_review_id'] and latest['outcome']=='PROPOSABLE'
  for item in notice['items']:
   source=self.s.get(N.sources,item['evidence']['source_id']);self.s.files.verify_location(source,item['evidence'])
  detail=dict(snapshot=snap,candidate=candidate,current_valid=current,lineage={'legacy':candidate['legacy_lineage']},reviews=reviews)
  if not current or not verified_completion(self.s,actor,detail,latest):raise Denied('STALE_INPUT_VERSION')
 def export(self,actor,version_id,kind,key):
  self.operator(actor);v=self.version(actor,version_id)
  def execute():
   self.root(actor,v['proposal_id'],True);review=self.confirmed_review(version_id)
   existing=self.s.rows(P.files,version_id=version_id,kind=kind,content_review_id=review['id'])
   if existing:return dict(id=existing[0]['id'],digest=existing[0]['digest'])
   data=render(v,kind);storage,digest=self.s.files.put(data)
   f=self.s.add(P.files,version_id=version_id,content_review_id=review['id'],kind=kind,storage_key=storage,digest=digest,size=len(data),actor_id=actor.id);self.s.record(actor,'GENERATE_PROPOSAL_DOCUMENT',file_id=f['id'],version_id=version_id);return dict(id=f['id'],digest=digest)
  return self.s.command(actor,key,['GENERATE_PROPOSAL_DOCUMENT',version_id,kind],execute)
 def download(self,actor,file_id):
  f=self.s.get(P.files,file_id);self.version(actor,f['version_id']);data=self.s.files.read(f['storage_key'],f['digest']);self.s.record(actor,'DOWNLOAD_PROPOSAL_DOCUMENT',file_id=file_id,version_id=f['version_id']);return f,data
