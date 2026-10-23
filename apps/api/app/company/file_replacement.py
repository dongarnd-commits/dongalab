"""A confirmed file replacement may append one draft attachment revision.

This never redirects existing Evidence, extracted facts, or submitted versions.
The caller owns the Company transaction/lock and appends the lifecycle event.
"""
from copy import deepcopy
from app.infrastructure import company_schema as S
from app.infrastructure import company_business_schema as B
from app.notice.domain import Denied


def draft_attachment_target(app,old,replacement):
 targets=[]
 proofs={e['id']:e for e in app.rows(S.evidence,company_id=old['company_id'])}
 for root in app.rows(S.improvements,company_id=old['company_id']):
  version=next(v for v in app.rows(S.improvement_versions,improvement_id=root['id']) if v['ordinal']==root['current_ordinal'])
  attached=[proofs[eid] for eid in version['data']['evidence_ids'] if proofs[eid]['file_id']==old['id']]
  if attached:targets.append((root,version,attached))
 if len(targets)>1:raise Denied('FILE_REPLACEMENT_SHARED_BUSINESS',409)
 if not targets:return None
 root,version,attached=targets[0]
 if root['state']!='DRAFT':return None
 if replacement['site_id'] and replacement['site_id']!=root['site_id']:raise Denied('FILE_REPLACEMENT_SITE_MISMATCH',409)
 if any(e['mode']!='MANUAL_REVIEW' or e['parse_id'] or e['descriptor']!='개선요구 첨부자료' for e in attached):
  raise Denied('FILE_REPLACEMENT_EVIDENCE_REVIEW_REQUIRED',409)
 file_evidence={e['id'] for e in proofs.values() if e['file_id']==old['id']}
 # A finance/history/request/Fact source is not an interchangeable attachment.
 if (app.rows(B.extractions,file_id=old['id']) or app.rows(B.requests,file_id=old['id'])
   or app.rows(B.response_files,file_id=old['id'])
   or any(c['evidence_id'] in file_evidence for c in app.rows(S.candidates,company_id=old['company_id']))):
  raise Denied('FILE_REPLACEMENT_SHARED_BUSINESS',409)
 return root,version,attached


def replace_draft_attachment(app,who,old,replacement):
 target=draft_attachment_target(app,old,replacement)
 if target is None:return None
 root,version,attached=target
 proof=app.manual_evidence(who,old['company_id'],replacement['id'],root['site_id'],
  '개선요구 첨부자료','사용자가 개선요구 관련 자료로 교체한 원본 파일: '+replacement['name'])
 previous={e['id'] for e in attached}
 data=deepcopy(version['data'])
 data['evidence_ids']=list(dict.fromkeys(proof['id'] if eid in previous else eid for eid in data['evidence_ids']))
 return app.save_improvement(who,old['company_id'],data,root['id'],root['current_ordinal'])
