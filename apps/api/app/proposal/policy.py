"""Consumer-only authority contracts. No inferred DMP/Company API or mock runtime."""
from dataclasses import dataclass,asdict
from app.notice.domain import Denied
from app.capability.application import fingerprint
from app.infrastructure import proposal_schema as P

@dataclass(frozen=True)
class Proof:
 id:str
 company_id:str
 version_id:str
 storage_key:str
 digest:str
 confirmed_by:str
 confirmed:bool
 current_valid:bool

@dataclass(frozen=True)
class CompanyBasis:
 company_id:str
 improvement_version_id:str
 fact_version_ids:tuple[str,...]
 company_confirmed:bool
 current_valid:bool
 proofs:tuple[Proof,...]
 approver_id:str|None

def basis(service,actor,company_id,improvement_version_id):
 reader=getattr(service.inputs,'proposal_basis',None)
 if reader is None:raise Denied('COMPANY_PROVIDER_NOT_CONNECTED',503)
 result=reader(actor,company_id,improvement_version_id)
 if not isinstance(result,CompanyBasis) or result.company_id!=company_id or result.improvement_version_id!=improvement_version_id:raise Denied('OBJECT_NOT_FOUND',404)
 return result

def tasks(detail):
 items=[{'id':k,'label':k} for k in ('COMPANY_ELIGIBILITY','SUPPLIER_ELIGIBILITY','SERVICE_SCOPE')]
 items += [{'id':'notice:'+i['id'],'label':i['kind']+': '+i['content'],'notice_evidence_id':i['evidence']['id']} for i in detail['snapshot']['input']['notice']['items']]
 items += [{'id':'missing:'+k,'label':k} for k in detail['candidate']['data']['missing']]
 return items

def validate_completion(service,actor,detail,items):
 if not detail['current_valid']:raise Denied('STALE_INPUT_VERSION')
 if detail['lineage']['legacy']:raise Denied('LEGACY_ANALYSIS_REQUIRES_REANALYSIS')
 if detail['candidate']['fit']=='MISMATCH' or detail['candidate']['data']['opposing_evidence']:raise Denied('CONFIRMED_ELIGIBILITY_CONFLICT')
 context=detail['snapshot']['input']['company'];b=basis(service,actor,context['company_id'],context['improvement_version_id'])
 if not b.current_valid or not b.company_confirmed or set(b.fact_version_ids)!=set(context.get('fact_version_ids',[])):raise Denied('MISSING_REQUIRED_INFORMATION')
 required={t['id']:t for t in tasks(detail)}
 if len(items)!=len(required) or {i['task_id'] for i in items}!=set(required):raise Denied('MISSING_REQUIRED_INFORMATION')
 proofs={p.id:p for p in b.proofs}
 for i in items:
  if i['decision'] not in ('CONFIRMED','NOT_APPLICABLE') or not i['note'].strip() or not i['proof_ids']:raise Denied('MISSING_REQUIRED_INFORMATION')
  for key in i['proof_ids']:
   p=proofs.get(key)
   if p is None or p.company_id!=b.company_id or not p.confirmed or not p.current_valid or not p.confirmed_by or p.version_id not in {*b.fact_version_ids,b.improvement_version_id}:raise Denied('REQUIRED_EVIDENCE_MISSING')
   service.files.read(p.storage_key,p.digest)
  notice=required[i['task_id']].get('notice_evidence_id')
  if notice and i.get('notice_evidence_id')!=notice:raise Denied('REQUIRED_EVIDENCE_MISSING')
 frozen=asdict(b);frozen['fact_version_ids']=sorted(b.fact_version_ids);frozen['proofs']=sorted(frozen['proofs'],key=lambda p:p['id']);return frozen

def attach(service,actor,detail,review,items):
 frozen=validate_completion(service,actor,detail,items)
 service.add(P.completions,review_id=review['id'],basis=frozen,items=items)

def verified_completion(service,actor,detail,review):
 rows=service.rows(P.completions,review_id=review['id'])
 if len(rows)!=1:return False
 try:return fingerprint(rows[0]['basis'])==fingerprint(validate_completion(service,actor,detail,rows[0]['items']))
 except Denied as exc:
  if exc.status in (403,404,503):raise
  return False
