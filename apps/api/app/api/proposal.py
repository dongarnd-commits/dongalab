from typing import Annotated,Literal
from fastapi import APIRouter,Depends,Response,Query
from pydantic import BaseModel,Field
from sqlalchemy.orm import Session
from app.api.notice import actor,trusted_origin,Command,errors
from app.infrastructure.database import get_session
from app.proposal.application import ProposalApplication
import app.api.capability as cap_api
router=APIRouter(prefix='/proposal',tags=['Proposal production'])
def application(session):return ProposalApplication(cap_api.application(session))
class Create(Command):
 candidate_id:str
 title:str=Field(min_length=1,max_length=500)
 idempotency_key:str=Field(min_length=1,max_length=100)
class Section(Command):
 heading:str
 body:str=Field(min_length=1,max_length=20000)
 evidence_refs:dict
class Save(Command):
 expected_version:str
 title:str=Field(min_length=1,max_length=500)
 sections:list[Section]=Field(min_length=11,max_length=11)
 candidate_id:str|None=None
 idempotency_key:str=Field(min_length=1,max_length=100)
class Review(Command):
 confirmed:bool
 note:str=Field(min_length=1,max_length=5000)
 idempotency_key:str=Field(min_length=1,max_length=100)
class Key(Command):
 idempotency_key:str=Field(min_length=1,max_length=100)
class Approval(Key):
 approval_mode:Literal['DIRECT_APPROVER','COMPANY_RECORDED_AUTHORIZATION']='DIRECT_APPROVER'
 recorder_id:str|None=None
class Decision(Key):
 authorization:dict|None=None
 outcome:Literal['APPROVE','REVISION_REQUEST','REJECT']
 reason:str=Field(min_length=1,max_length=5000)
class Export(Key):
 kind:Literal['DOCX','PDF']
@router.get('',response_model=list[dict],responses=errors(401,403,404,503))
def listing(company_id:str,improvement_version_id:str,session:Annotated[Session,Depends(get_session)],who=Depends(actor)):
 return application(session).listing(who,company_id,improvement_version_id)
@router.post('',response_model=dict,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422,503))
def create(body:Create,session:Annotated[Session,Depends(get_session)],who=Depends(actor)):
 result=application(session).create(who,body.candidate_id,body.title,body.idempotency_key);session.commit();return result
@router.get('/matches/{candidate_id}/evidence/{proof_id}/download',responses=errors(401,403,404,503))
def evidence(candidate_id:str,proof_id:str,session:Annotated[Session,Depends(get_session)],who=Depends(actor)):
 from app.proposal.policy import basis
 service=cap_api.application(session);service.operator(who);detail=service.match(who,candidate_id);context=detail['snapshot']['input']['company'];b=basis(service,who,context['company_id'],context['improvement_version_id'])
 proof=next((p for p in b.proofs if p.id==proof_id),None)
 from app.notice.domain import Denied
 if proof is None or proof.company_id!=b.company_id:raise Denied('OBJECT_NOT_FOUND',404)
 data=service.files.read(proof.storage_key,proof.digest);service.record(who,'READ_PROPOSAL_BASIS',proof_id=proof_id);session.commit()
 return Response(data,media_type='application/octet-stream',headers={'Content-Disposition':'attachment; filename="company-evidence"','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})
@router.get('/versions/{version_id}',response_model=dict,responses=errors(401,403,404,503))
def version(version_id:str,session:Annotated[Session,Depends(get_session)],who=Depends(actor)):return application(session).version(who,version_id)
@router.post('/versions/{version_id}/review',response_model=dict,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422,503))
def review(version_id:str,body:Review,session:Annotated[Session,Depends(get_session)],who=Depends(actor)):
 result=application(session).review(who,version_id,body.confirmed,body.note,body.idempotency_key);session.commit();return result
@router.post('/versions/{version_id}/approval',response_model=dict,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422,503))
def request_approval(version_id:str,body:Approval,session:Annotated[Session,Depends(get_session)],who=Depends(actor)):
 result=application(session).request(who,version_id,body.idempotency_key,body.approval_mode,body.recorder_id);session.commit();return result
@router.post('/approvals/{request_id}/decision',response_model=dict,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422,503))
def decide(request_id:str,body:Decision,session:Annotated[Session,Depends(get_session)],who=Depends(actor)):
 result=application(session).decide(who,request_id,body.outcome,body.reason,body.idempotency_key,body.authorization);session.commit();return result
@router.post('/versions/{version_id}/export',response_model=dict,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422,503))
def export(version_id:str,body:Export,session:Annotated[Session,Depends(get_session)],who=Depends(actor)):
 result=application(session).export(who,version_id,body.kind,body.idempotency_key);session.commit();return result
@router.get('/files/{file_id}/download',responses=errors(401,403,404,409,503))
def download(file_id:str,session:Annotated[Session,Depends(get_session)],who=Depends(actor)):
 f,data=application(session).download(who,file_id);session.commit()
 media='application/pdf' if f['kind']=='PDF' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
 return Response(data,media_type=media,headers={'Content-Disposition':'attachment; filename="proposal-'+f['version_id']+'.'+f['kind'].lower()+'"','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})
@router.get('/inbox/{company_id}',response_model=list[dict],responses=errors(401,403,404,503))
def company_inbox(company_id:str,session:Annotated[Session,Depends(get_session)],who=Depends(actor)):
 return application(session).company_inbox(who,company_id)
@router.get('/{proposal_id}',response_model=dict,responses=errors(401,403,404,503))
def detail(proposal_id:str,session:Annotated[Session,Depends(get_session)],who=Depends(actor)):return application(session).detail(who,proposal_id)
@router.post('/{proposal_id}/versions',response_model=dict,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422,503))
def save(proposal_id:str,body:Save,session:Annotated[Session,Depends(get_session)],who=Depends(actor)):
 result=application(session).save(who,proposal_id,body.expected_version,body.title,[s.model_dump() for s in body.sections],body.idempotency_key,body.candidate_id);session.commit();return result
