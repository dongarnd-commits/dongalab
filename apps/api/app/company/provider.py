"""Authoritative local Company adapter for existing B/C consumer ports."""
from app.infrastructure import company_schema as S
from app.infrastructure.notice_schema import actors
from app.notice.domain import Denied

class CompanyProvider:
 def __init__(self,application):self.app=application
 def read(self,who,version_id):
  a=self.app;v=a.get(S.improvement_versions,version_id);root=a.get(S.improvements,v['improvement_id']);a.scope(who,root['company_id']);a.get(S.companies,root['company_id'],True);root=a.get(S.improvements,root['id'])
  links=a.rows(S.improvement_facts,version_id=version_id);confirmed=bool(a.rows(S.improvement_reviews,version_id=version_id,outcome='CONFIRM'))
  current=confirmed and root['state']=='CONFIRMED' and root['current_ordinal']==v['ordinal'] and a.get(S.sites,root['site_id'])['current_ordinal']==v['site_ordinal'] and all(a.current_fact(l['fact_version_id'])[2] for l in links) and all(a.evidence_current(e['evidence_id']) for e in a.rows(S.improvement_evidence,version_id=version_id))
  fact_details=[]
  for link in links:
   fv,fact,valid=a.current_fact(link['fact_version_id']);eid,review_id=a.fact_evidence(fv)
   fact_details.append(dict(version_id=fv['id'],company_id=fact['company_id'],site_id=fact['site_id'],field=fact['field'],value=fv['value'],period=fact['period'],unit=fact['unit'],currency=fact['currency'],valid_from=fv['valid_from'],review_id=review_id,evidence_id=eid,current_valid=valid))
  return dict(company_id=root['company_id'],site_id=root['site_id'],improvement_version_id=version_id,original_text=v['data']['original_text'],structured=v['data'],fact_details=fact_details,confirmed=confirmed,current_valid=current,fact_version_ids=sorted(l['fact_version_id'] for l in links),evidence_refs=sorted(e['evidence_id'] for e in a.rows(S.improvement_evidence,version_id=version_id)))
 def read_comparison_inputs(self,who,context,notice):
  from app.capability.comparison import ComparisonInputs,ConfirmedFact
  a=self.app;actual=self.read(who,context['improvement_version_id'])
  if actual['company_id']!=context['company_id']:raise Denied('OBJECT_NOT_FOUND',404)
  result=[]
  for key in actual['fact_version_ids']:
   v,f,current=a.current_fact(key)
   if f['field'] in ('revenue','assets','liabilities','employees','support_history'):continue
   eid,review_id=a.fact_evidence(v)
   result.append(ConfirmedFact(v['id'],f['company_id'],f['site_id'],f['field'],v['value'],review_id,(eid,),True,current,v['valid_from']))
  # No new Notice condition normalizer: existing R07 unsupported semantics stay UNKNOWN.
  return ComparisonInputs(tuple(result),())
 def proposal_basis(self,who,company_id,improvement_version_id):
  from app.proposal.policy import CompanyBasis,Proof
  a=self.app;context=self.read(who,improvement_version_id)
  if context['company_id']!=company_id:raise Denied('OBJECT_NOT_FOUND',404)
  proofs=[]
  for key in context['fact_version_ids']:
   v,f,current=a.current_fact(key);eid,review_id=a.fact_evidence(v);e=a.get(S.evidence,eid)
   # Only actual Private File evidence satisfies the existing Proposal proof contract.
   if e['file_id']:
    file=a.get(S.files,e['file_id']);review=a.get(S.reviews,review_id);a.files.read(file['storage_key'],file['digest'])
    proofs.append(Proof(e['id'],company_id,key,file['storage_key'],file['digest'],review['actor_id'],True,current))
  approvers=[]
  for m in a.rows(S.memberships,company_id=company_id):
   if a.get(actors,m['actor_id'])['role']=='COMPANY_APPROVER':approvers.append(m['actor_id'])
  ack=bool(a.rows(S.improvement_reviews,version_id=improvement_version_id,outcome='ACKNOWLEDGE'))
  return CompanyBasis(company_id,improvement_version_id,tuple(context['fact_version_ids']),ack,context['current_valid'],tuple(proofs),approvers[0] if len(approvers)==1 else None)
