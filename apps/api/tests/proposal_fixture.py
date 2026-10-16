"""TEST-only authority consuming explicit company confirmation evidence, no fake MatchReview."""
from dataclasses import asdict
from uuid import uuid4
from app.proposal.policy import CompanyBasis,Proof,tasks
from app.notice.domain import Denied,Actor
from app.capability.application import CapabilityApplication
from app.infrastructure.notice_store import SqlNoticeStore
from app.infrastructure.local_auth import hash_password
from capability_scenario_fixture import ScenarioInputs
from confirmed_comparison_fixture import facts
from sqlalchemy import insert,select
class ProposalInputs(ScenarioInputs):
 def proposal_basis(self,actor,company_id,improvement_version_id):
  if self.env.memberships.get(actor.id)!=company_id:raise Denied('OBJECT_NOT_FOUND',404)
  value=self.env.contexts.get(improvement_version_id)
  if value is None or value['company_id']!=company_id:raise Denied('OBJECT_NOT_FOUND',404)
  with self.env.factory() as s:records=[r for r in s.execute(select(facts.c.data)).scalars() if r['version_id'] in value['fact_version_ids'] and r.get('attribute')=='proposal_company_confirmation']
  ps=tuple(Proof(r['version_id'],company_id,r['version_id'],r['evidence_refs'][0],r['evidence_refs'][0],r['review_id'],r['confirmed'],r['current_valid']) for r in records)
  return CompanyBasis(company_id,improvement_version_id,tuple(value['fact_version_ids']),bool(ps) and all(p.confirmed for p in ps),value['current_valid'],ps,self.env.accounts['approver']['id'])

def confirm_company(e):
 # A synthetic company user's explicit confirmation of its own supplied evidence.
 editor=e.accounts['company'];assert editor['role']=='COMPANY_EDITOR'
 e.memberships[editor['id']]='TEST_COMPANY_A'
 with e.factory.begin() as s:
  approver=SqlNoticeStore(s).add('actors',username='TEST_APPROVER_'+uuid4().hex,role='COMPANY_APPROVER',password_hash=hash_password(e.password));e.accounts['approver']=approver;e.memberships[approver['id']]='TEST_COMPANY_A'
  key,digest=e.files.put('TEST 기업이 제공하고 확인한 사업계획·재무·도입 자료. 실제 기업/정부 판정 아님.'.encode());version=str(uuid4())
  s.execute(insert(facts).values(id=version,reviewer_id=editor['id'],data=dict(version_id=version,attribute='proposal_company_confirmation',value='TEST_CONFIRMED',site_id='TEST_SITE_A',valid_from='2026-01-01',company_id='TEST_COMPANY_A',review_id=editor['id'],confirmed=True,current_valid=True,evidence_refs=[key])))
 for letter in ('A','B','C','D','E','G'):
  e.contexts['TEST_IMPROVEMENT_'+letter]['fact_version_ids']=[version];e.contexts['TEST_IMPROVEMENT_'+letter]['evidence_refs']=[key]
 from fastapi.testclient import TestClient
 from app.main import app
 e.clients['approver']=TestClient(app);e.call('approver','/notice/session',{'username':approver['username'],'password':e.password})
 e.inputs=ProposalInputs(e)

def completions(e,candidate_id):
 detail=e.call('operator','/capability/matches/'+candidate_id);context=detail['snapshot']['input']['company'];proof=context['fact_version_ids'][0]
 return [dict(task_id=t['id'],decision='CONFIRMED',note='TEST DATCO reviewed this specific source, scope, conditions and missing item; not an official selection.',proof_ids=[proof],notice_evidence_id=t.get('notice_evidence_id')) for t in tasks(detail)]
def proposable(e):
 r=e.compose('A',['A']);candidate=r['candidate']['candidate_id']
 body=dict(outcome='PROPOSABLE',note='TEST explicitly reviewed company/supplier/service and each notice requirement.',completion_items=completions(e,candidate),idempotency_key=e.nonce())
 review=e.call('operator','/capability/matches/'+candidate+'/review',body)
 assert e.call('operator','/capability/matches/'+candidate)['candidate']['fit']=='NEED_MORE_INFO'
 return r,review
