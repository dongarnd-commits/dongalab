"""Scoped local analysis orchestration and versioned drafts; no external AI."""
from hashlib import sha256
import json
from datetime import date, datetime, timezone
from pathlib import PurePath
from sqlalchemy import update
from app.infrastructure import company_schema as C, notice_schema as N, improvement_schema as S, analysis_schema as A
from app.notice.domain import Denied
from app.company.improvement_rules import VERSION

KIND='IMPROVEMENT_ANALYSIS'
def digest(value):return sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),default=str).encode()).hexdigest()

class ImprovementAnalysis:
    def __init__(self,application):self.a=application
    def ordered(self,table,**where):return sorted(self.a.rows(table,**where),key=lambda row:row['ordinal'])
    def target(self,who,vid,lock=False):
        a=self.a;a.role(who,'DATCO_OPERATOR');v=a.get(C.improvement_versions,vid);root=a.get(C.improvements,v['improvement_id']);a.scope(who,root['company_id'],lock)
        submits=a.rows(C.improvement_reviews,version_id=vid,outcome='SUBMIT')
        if not submits:raise Denied('OBJECT_NOT_FOUND',404)
        return v,root,submits[0]
    def sources(self,who,vid):
        a=self.a;v,r,sub=self.target(who,vid)
        files=[]
        direct={a.get(C.evidence,l['evidence_id'])['file_id'] for l in a.rows(C.improvement_evidence,version_id=vid)}
        from app.infrastructure import company_business_schema as B
        for f in a.rows(C.files,company_id=r['company_id']):
            if f['site_id'] not in (None,r['site_id']):continue
            inactive=bool(a.rows(B.file_events,file_id=f['id']))
            if inactive and f['id'] not in direct:continue
            parses=[p for p in a.rows(C.parses,file_id=f['id']) if p['error'] is None]
            supported=PurePath(f['name']).suffix.lower() in ('.pdf','.docx','.xlsx','.txt')
            files.append(dict(id=f['id'],name=f['name'],digest=f['digest'],direct=f['id'] in direct,inactive=inactive,
                default_included=not inactive and supported,parse_id=parses[-1]['id'] if parses else None))
        current=a.get(C.companies,r['company_id'])['current_ordinal']
        profile=next(p for p in a.rows(C.inputs,company_id=r['company_id']) if p['ordinal']==current)
        site=next(s for s in a.rows(C.site_versions,site_id=r['site_id']) if s['ordinal']==v['site_ordinal'])
        facts=[]
        linked={x['fact_version_id'] for x in a.rows(C.improvement_facts,version_id=vid)}
        for f in a.rows(C.facts,company_id=r['company_id']):
            if f['site_id'] not in (None,r['site_id']):continue
            for fv in a.rows(C.fact_versions,fact_id=f['id']):
                current=a.current_fact(fv['id'])[2]
                if fv['id'] in linked or current:
                    eid,rid=a.fact_evidence(fv)
                    facts.append(dict(id=fv['id'],review_id=rid,evidence_id=eid,current=current,direct=fv['id'] in linked))
        result=dict(company_id=r['company_id'],version_id=vid,submit_review_id=sub['id'],input_version_id=profile['id'],
            site_version_id=site['id'],site_current_ordinal=a.get(C.sites,r['site_id'])['current_ordinal'],files=files,facts=facts,rule_version=VERSION)
        return dict(result,selection_token=digest(result))
    def request(self,who,vid,key,token,excluded,reason):
        a=self.a;v,r,_=self.target(who,vid,True)
        body=digest(dict(vid=vid,token=token,excluded=excluded,reason=reason))
        old=a.rows(S.receipts,actor_id=who.id,request_key=key)
        if old:
            if old[0]['body_hash']!=body:raise Denied('IDEMPOTENCY_CONFLICT',409)
            return a.get(N.jobs,old[0]['job_id'])
        if a.rows(N.jobs,actor_id=who.id,request_key=key):raise Denied('IDEMPOTENCY_CONFLICT',409)
        src=self.sources(who,vid)
        if src['selection_token']!=token:raise Denied('STALE_INPUT_VERSION',409)
        if any(fid not in {f['id'] for f in src['files']} for fid in excluded):raise Denied('OBJECT_NOT_FOUND',404)
        plan=dict(src,excluded=excluded,reason=reason);fingerprint=digest({k:v for k,v in plan.items() if k!='reason'})
        for m in a.rows(S.manifests,company_id=r['company_id']):
            job=a.get(N.jobs,m['job_id'])
            if m['digest']==fingerprint and job['state'] in ('QUEUED','PROCESSING'):
                a.add(S.receipts,job_id=job['id'],actor_id=who.id,request_key=key,body_hash=body)
                return job
        job=a.add(N.jobs,actor_id=who.id,request_key=key,kind=KIND,version_id=None,payload=dict(body_hash=body),state='QUEUED')
        a.add(S.receipts,job_id=job['id'],actor_id=who.id,request_key=key,body_hash=body)
        m=a.add(S.manifests,job_id=job['id'],company_id=r['company_id'],version_id=vid,submit_review_id=src['submit_review_id'],
            input_version_id=src['input_version_id'],site_version_id=src['site_version_id'],digest=fingerprint,data=plan)
        for f in src['files']:
            a.add(S.inputs,manifest_id=m['id'],file_id=f['id'],parse_id=f['parse_id'],origin='DIRECT_ATTACHMENT' if f['direct'] else 'COMMON_REFERENCE',data=dict(f,included=f['id'] not in excluded and f['default_included'],exclude_reason=excluded.get(f['id'],'')))
        for f in src['facts']:
            a.add(S.inputs,manifest_id=m['id'],fact_version_id=f['id'],fact_review_id=f['review_id'],origin='DIRECT_FACT' if f['direct'] else 'CURRENT_FACT',data=f)
        for link in a.rows(C.improvement_evidence,version_id=vid):
            a.add(S.inputs,manifest_id=m['id'],evidence_id=link['evidence_id'],origin='DIRECT_EVIDENCE',data={})
        a.record(who,r['company_id'],'REQUEST_IMPROVEMENT_ANALYSIS',improvement_version_id=vid)
        return job
    def manifest_for_run(self,who,rid,lock=False):
        a=self.a;a.role(who,'DATCO_OPERATOR');run=a.get(N.runs,rid)
        if run['analysis_kind']!=KIND:raise Denied('OBJECT_NOT_FOUND',404)
        ctx=a.rows(S.contexts,run_id=rid)[0];m=a.get(S.manifests,ctx['manifest_id']);self.target(who,m['version_id'],lock)
        return run,ctx,m
    def freshness(self,who,rid):
        a=self.a;run,ctx,m=self.manifest_for_run(who,rid);old=m['data'];now=self.sources(who,m['version_id']);reasons=[];warnings=[]
        v,r,_=self.target(who,m['version_id'])
        submitted=[]
        for version in a.rows(C.improvement_versions,improvement_id=r['id']):
            if a.rows(C.improvement_reviews,version_id=version['id'],outcome='SUBMIT'):submitted.append(version)
        if submitted[-1]['id']!=m['version_id']:reasons.append('NEW_SUBMIT_VERSION')
        if old['input_version_id']!=now['input_version_id']:reasons.append('COMPANY_INPUT_CHANGED')
        if old['site_current_ordinal']!=now['site_current_ordinal']:reasons.append('SITE_CHANGED')
        current_facts={f['id']:f for f in now['facts']}
        if any(f['id'] not in current_facts or current_facts[f['id']]!=f for f in old['facts']):reasons.append('FACT_BASIS_CHANGED')
        if set(current_facts)-{f['id'] for f in old['facts']}:warnings.append('NEW_FACT_REVIEW_SUGGESTED')
        from app.infrastructure import company_business_schema as B
        for fact in old['facts']:
            ev=a.get(C.evidence,fact['evidence_id'])
            if ev['file_id'] and a.rows(B.file_events,file_id=ev['file_id']):reasons.append('FACT_BASIS_CHANGED')
        current={f['id']:f for f in now['files']}
        for f in old['files']:
            if f['id'] not in old['excluded'] and not f['inactive']:
                if f['id'] not in current or current[f['id']]['inactive'] or current[f['id']]['digest']!=f['digest']:reasons.append('SOURCE_CHANGED')
        if set(current)-{f['id'] for f in old['files']}:warnings.append('NEW_COMMON_SOURCE_REVIEW_SUGGESTED')
        if r['current_ordinal']>v['ordinal']:warnings.append('NEWER_WORKING_VERSION')
        attempt=a.get(N.attempts,run['attempt_id']);attempts=self.ordered(N.attempts,job_id=m['job_id']);job=a.get(N.jobs,m['job_id'])
        if attempt['id']!=attempts[-1]['id'] or job['state'] in ('QUEUED','PROCESSING'):reasons.append('NEW_ATTEMPT')
        if ctx['status']=='FAILED':reasons.append('ANALYSIS_FAILED')
        if old['rule_version']!=VERSION:reasons.append('RULE_CHANGED')
        return dict(usable=not reasons,reasons=sorted(set(reasons)),warnings=warnings)
    def job(self,who,jid):
        a=self.a;a.role(who,'DATCO_OPERATOR');j=a.get(N.jobs,jid)
        if j['kind']!=KIND:raise Denied('OBJECT_NOT_FOUND',404)
        m=a.rows(S.manifests,job_id=jid)[0];self.target(who,m['version_id'])
        attempts=self.ordered(N.attempts,job_id=jid);runs=[r for t in attempts for r in a.rows(N.runs,attempt_id=t['id'])]
        expired=j['state']=='PROCESSING' and j['lease_until'] is not None and j['lease_until']<=datetime.now(timezone.utc)
        return dict(j,attempts=attempts,runs=runs,retry_allowed=j['state'] in ('FAILED','PARTIAL') or expired)
    def retry(self,who,jid,key,expected):
        a=self.a;j=self.job(who,jid);m=a.rows(S.manifests,job_id=jid)[0];self.target(who,m['version_id'],True);j=a.get(N.jobs,jid,True)
        if j['payload'].get('retry_key')==key:return self.job(who,jid)
        if j['state']=='PROCESSING' and j['lease_until'] is not None and j['lease_until']<=datetime.now(timezone.utc):
            for attempt in a.rows(N.attempts,job_id=jid):
                if attempt['state']=='PROCESSING':a.session.execute(update(N.attempts).where(N.attempts.c.id==attempt['id']).values(state='FAILED',error='INTERRUPTED_EXECUTION'))
            a.session.execute(update(N.jobs).where(N.jobs.c.id==jid).values(state='FAILED',error='INTERRUPTED_EXECUTION',lease_until=None))
            j=dict(j,state='FAILED')
        if j['state'] not in ('FAILED','PARTIAL') or len(a.rows(N.attempts,job_id=jid))!=expected:raise Denied('TRANSITION_NOT_ALLOWED',409)
        a.session.execute(update(N.jobs).where(N.jobs.c.id==jid).values(state='QUEUED',error=None,payload=dict(j['payload'],retry_key=key)))
        a.record(who,m['company_id'],'RETRY_IMPROVEMENT_ANALYSIS',improvement_version_id=m['version_id']);return self.job(who,jid)
    def run(self,who,rid):
        a=self.a;run,ctx,m=self.manifest_for_run(who,rid)
        candidates=[]
        for c in a.rows(N.candidates,run_id=rid):
            d=a.rows(S.details,candidate_id=c['id'])[0]
            reviews=[dict(x,note=a.get(N.reviews,x['review_id'])['note']) for x in self.ordered(S.reviews,candidate_id=c['id'])]
            candidates.append(dict(c,category=d['category'],data=d['data'],reviews=reviews))
        return dict(run=run,manifest=m,inputs=a.rows(S.inputs,manifest_id=m['id']),inspections=a.rows(S.inspections,run_id=rid),diagnostics=ctx['diagnostics'],status=ctx['status'],candidates=candidates,freshness=self.freshness(who,rid))
    def listing(self,who,vid):
        a=self.a;self.target(who,vid)
        return [self.run(who,c['run_id']) for m in a.rows(S.manifests,version_id=vid) for c in a.rows(S.contexts,manifest_id=m['id'])]
    def review(self,who,cid,key,expected,decision,note,question):
        a=self.a;a.role(who,'DATCO_OPERATOR');c=a.get(N.candidates,cid);_,_,m=self.manifest_for_run(who,c['run_id'],True)
        body=digest(dict(cid=cid,decision=decision,note=note,question=question,expected=expected))
        old=a.rows(S.reviews,actor_id=who.id,request_key=key)
        if old:
            if old[0]['body_hash']!=body:raise Denied('IDEMPOTENCY_CONFLICT',409)
            return old[0]
        if not self.freshness(who,c['run_id'])['usable']:raise Denied('STALE_ANALYSIS',409)
        if len(a.rows(S.reviews,candidate_id=cid))!=expected:raise Denied('STALE_REVIEW',409)
        r=a.add(N.reviews,candidate_id=cid,actor_id=who.id,analysis_kind=KIND,note=note)
        d=a.add(S.reviews,review_id=r['id'],candidate_id=cid,actor_id=who.id,ordinal=expected+1,decision=decision,question=question,request_key=key,body_hash=body)
        a.add(A.review_contexts,review_id=r['id'],improvement_review_id=d['id'])
        a.record(who,m['company_id'],'REVIEW_IMPROVEMENT_ANALYSIS',improvement_version_id=m['version_id']);return d
    def validate_selections(self,who,rid,ids):
        a=self.a;self.manifest_for_run(who,rid,True)
        if not self.freshness(who,rid)['usable']:raise Denied('STALE_ANALYSIS',409)
        if not ids or len(ids)!=len(set(ids)):raise Denied('INVALID_REVIEW_SELECTION',422)
        rows=[]
        for key in ids:
            r=a.get(S.reviews,key);c=a.get(N.candidates,r['candidate_id'])
            if c['run_id']!=rid:raise Denied('OBJECT_NOT_FOUND',404)
            if r['decision']!='USE_FOR_REQUEST' or self.ordered(S.reviews,candidate_id=c['id'])[-1]['id']!=key:raise Denied('STALE_REVIEW',409)
            rows.append(r)
        return rows
    def create_draft(self,who,rid,key,ids):
        a=self.a;_,_,m=self.manifest_for_run(who,rid,True);body=digest(dict(run=rid,ids=ids));old=a.rows(S.drafts,actor_id=who.id,request_key=key)
        if old:
            if old[0]['body_hash']!=body:raise Denied('IDEMPOTENCY_CONFLICT',409)
            return self.draft(who,old[0]['id'])
        selected=self.validate_selections(who,rid,ids)
        lines=[]
        for r in selected:
            c=a.get(N.candidates,r['candidate_id']);d=a.rows(S.details,candidate_id=c['id'])[0]
            lines.append((r['question'] or d['data'].get('question') or c['content'])+'\n요청 이유: '+c['reason'])
        draft=a.add(S.drafts,run_id=rid,company_id=m['company_id'],version_id=m['version_id'],actor_id=who.id,request_key=key,body_hash=body)
        self.save_draft(who,draft['id'],key,0,'개선요구 추가 확인 요청','\n\n'.join(lines),None,ids)
        return self.draft(who,draft['id'])
    def owned_draft(self,who,did):
        a=self.a;a.role(who,'DATCO_OPERATOR');d=a.get(S.drafts,did);self.target(who,d['version_id'],True)
        if d['actor_id']!=who.id:raise Denied('OBJECT_NOT_FOUND',404)
        return a.get(S.drafts,did,True)
    def draft(self,who,did):
        a=self.a;d=self.owned_draft(who,did);versions=self.ordered(S.draft_versions,draft_id=did)
        fresh=self.freshness(who,d['run_id'])
        for selection in a.rows(S.selections,draft_version_id=versions[-1]['id']):
            review=a.get(S.reviews,selection['analysis_review_id'])
            if self.ordered(S.reviews,candidate_id=review['candidate_id'])[-1]['id']!=review['id']:
                fresh['usable']=False
                if 'REVIEW_CHANGED' not in fresh['reasons']:fresh['reasons'].append('REVIEW_CHANGED')
        return dict(d,versions=[dict(v,review_ids=[s['analysis_review_id'] for s in a.rows(S.selections,draft_version_id=v['id'])]) for v in versions],deliveries=a.rows(S.deliveries,draft_id=did),freshness=fresh)
    def save_draft(self,who,did,key,expected,title,message,due,ids):
        a=self.a;d=self.owned_draft(who,did);body=digest(dict(did=did,expected=expected,title=title,message=message,due=due,ids=ids));old=a.rows(S.draft_versions,actor_id=who.id,request_key=key)
        if old:
            if old[0]['body_hash']!=body:raise Denied('IDEMPOTENCY_CONFLICT',409)
            return old[0]
        if a.rows(S.deliveries,draft_id=did) or len(a.rows(S.draft_versions,draft_id=did))!=expected:raise Denied('STALE_DRAFT_VERSION',409)
        self.validate_selections(who,d['run_id'],ids)
        if not title.strip() or not message.strip() or len(title)>300 or len(message)>10000:raise Denied('INVALID_REQUEST',422)
        if due:
            try:date.fromisoformat(due)
            except ValueError:raise Denied('INVALID_REQUEST',422) from None
        v=a.add(S.draft_versions,draft_id=did,actor_id=who.id,ordinal=expected+1,title=title.strip(),message=message.strip(),due_date=due,request_key=key,body_hash=body)
        for rid in ids:a.add(S.selections,draft_version_id=v['id'],analysis_review_id=rid)
        a.record(who,d['company_id'],'SAVE_ANALYSIS_REQUEST_DRAFT',improvement_version_id=d['version_id']);return v
    def send(self,who,did,expected):
        a=self.a;d=self.owned_draft(who,did);versions=self.ordered(S.draft_versions,draft_id=did);v=versions[-1];sent=a.rows(S.deliveries,draft_id=did)
        if v['ordinal']!=expected:raise Denied('STALE_DRAFT_VERSION',409)
        if sent:return sent[0]
        ids=[s['analysis_review_id'] for s in a.rows(S.selections,draft_version_id=v['id'])];self.validate_selections(who,d['run_id'],ids)
        r=a.information_create(who,d['company_id'],v['title'],v['message'],v['due_date'],improvement_version_id=d['version_id'])
        a.information_send(who,r['id'])
        return a.add(S.deliveries,draft_id=did,draft_version_id=v['id'],request_id=r['id'],actor_id=who.id)
