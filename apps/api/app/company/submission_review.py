"""Read projections and explicit whole-version judgement; never business CONFIRM."""
from app.company.improvement_analysis import ImprovementAnalysis,digest
from app.infrastructure import submission_review_schema as R, improvement_schema as S, company_schema as C, company_business_schema as B, notice_schema as N
from app.notice.domain import Denied

LABELS={'NEW_RECEIPT':'신규 접수·미검토','ANALYZING':'분석 중','NEEDS_REVIEW':'검토 필요','NEEDS_CHECK':'추가 확인 필요',
        'COMPLETED':'검토 완료','PREPARING_REQUEST':'보완요청 준비 중','WAITING_RESPONSE':'보완요청 발송·답변 대기','RESPONSE_REVIEW':'기업 답변 검토 필요','REREVIEW':'재검토 필요'}

class SubmissionReview:
 def __init__(self,a):self.a=a;self.analysis=ImprovementAnalysis(a)
 def history(self,who,vid):
  self.analysis.target(who,vid)
  return [dict(r,actor_name=self.a.get(N.actors,r['actor_id'])['username']) for r in self.analysis.ordered(R.reviews,version_id=vid)]
 def jobs(self,vid):
  return [self.a.get(N.jobs,m['job_id']) for m in self.a.rows(S.manifests,version_id=vid)]
 def latest_run(self,who,vid):
  rows=sorted([self.a.get(N.runs,c['run_id']) for m in self.a.rows(S.manifests,version_id=vid) for c in self.a.rows(S.contexts,manifest_id=m['id'])],key=lambda r:(r['created_at'],r['id']))
  return dict(run=rows[-1],freshness=self.analysis.freshness(who,rows[-1]['id'])) if rows else None
 def basis(self,who,vid):
  source=self.analysis.sources(who,vid)
  return dict(input=self.analysis.fingerprint(self.analysis.plan(source,{},[])),requests=digest([
      dict(id=r['id'],state=r['state'],response_ordinal=r['response_ordinal']) for r in self.a.rows(B.requests,improvement_version_id=vid)]))
 def projection(self,who,vid):
  a=self.a;v,root,_=self.analysis.target(who,vid);history=self.history(who,vid);latest=history[-1] if history else None
  jobs=self.jobs(vid);job=jobs[-1] if jobs else None;run=self.latest_run(who,vid)
  current=bool(latest and latest['basis']==self.basis(who,vid) and (latest['run_id']==run['run']['id'] and run['freshness']['usable'] if run else latest['run_id'] is None))
  requests=a.rows(B.requests,improvement_version_id=vid)
  states={r['state'] for r in requests}
  draft_pending=any(not a.rows(S.deliveries,draft_id=d['id']) and (not latest or latest['draft_id']==d['id'] or d['created_at']>latest['created_at']) for d in a.rows(S.drafts,version_id=vid))
  if 'REVIEW_REQUIRED' in states:status='RESPONSE_REVIEW'
  elif states & {'WAITING_RESPONSE','REVISION_REQUESTED'}:status='WAITING_RESPONSE'
  elif job and job['state'] in ('QUEUED','PROCESSING'):status='ANALYZING'
  elif draft_pending or 'DRAFT' in states:status='PREPARING_REQUEST'
  elif latest and not current:status='REREVIEW'
  elif latest and latest['decision']=='COMPLETED':status='COMPLETED'
  elif latest and latest['decision']=='NEEDS_CHECK':status='NEEDS_CHECK'
  elif latest and latest['decision']=='PREPARE_REQUEST':status='NEEDS_REVIEW'
  elif run:status='NEEDS_REVIEW' if run['freshness']['usable'] else 'REREVIEW'
  elif job:status='NEEDS_CHECK'
  elif any(r['version_id']!=vid for r in a.rows(R.reviews,improvement_id=root['id'])):status='REREVIEW'
  else:status='NEW_RECEIPT'
  return dict(status=status,label=LABELS[status],next_action='검토 결과 확인' if status=='COMPLETED' else '제출 내용 검토',latest=latest,current=current,run_id=run['run']['id'] if run else None,job_id=job['id'] if job else None)
 def save(self,who,vid,key,expected,decision,note,run_id=None,job_id=None,draft_id=None,analysis_limit=''):
  a=self.a;v,root,_=self.analysis.target(who,vid,True)
  body=digest(dict(vid=vid,expected=expected,decision=decision,note=note,run_id=run_id,job_id=job_id,draft_id=draft_id,analysis_limit=analysis_limit))
  old=a.rows(R.reviews,actor_id=who.id,request_key=key)
  if old:
   if old[0]['body_hash']!=body:raise Denied('IDEMPOTENCY_CONFLICT',409)
   return old[0]
  if not note.strip() or decision not in ('COMPLETED','NEEDS_CHECK','PREPARE_REQUEST'):raise Denied('INVALID_SUBMISSION_JUDGEMENT',422)
  if len(a.rows(R.reviews,version_id=vid))!=expected:raise Denied('STALE_SUBMISSION_REVIEW',409)
  runs=self.analysis.listing(who,vid)
  if run_id:
   _,_,manifest=self.analysis.manifest_for_run(who,run_id)
   if manifest['version_id']!=vid:raise Denied('OBJECT_NOT_FOUND',404)
   if not runs or runs[-1]['run']['id']!=run_id or not self.analysis.freshness(who,run_id)['usable']:raise Denied('STALE_ANALYSIS',409)
  elif not analysis_limit.strip() or runs:raise Denied('ANALYSIS_BASIS_REQUIRED',422)
  if job_id:
   job=self.analysis.job(who,job_id)
   if not any(j['id']==job_id for j in self.jobs(vid)):raise Denied('OBJECT_NOT_FOUND',404)
   if run_id and a.get(N.attempts,a.get(N.runs,run_id)['attempt_id'])['job_id']!=job_id:raise Denied('ANALYSIS_BASIS_REQUIRED',422)
  if draft_id:
   draft=self.analysis.owned_draft(who,draft_id)
   if draft['version_id']!=vid or draft['run_id']!=run_id:raise Denied('OBJECT_NOT_FOUND',404)
  if (decision=='PREPARE_REQUEST')!=bool(draft_id):raise Denied('DRAFT_BASIS_REQUIRED',422)
  row=a.add(R.reviews,company_id=root['company_id'],improvement_id=root['id'],version_id=vid,run_id=run_id,job_id=job_id,draft_id=draft_id,
    actor_id=who.id,ordinal=expected+1,decision=decision,note=note.strip(),analysis_limit=analysis_limit.strip(),basis=self.basis(who,vid),request_key=key,body_hash=body)
  a.record(who,root['company_id'],'JUDGE_SUBMITTED_IMPROVEMENT',improvement_version_id=vid)
  return row
