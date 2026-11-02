"""Operator-only Slice 2 commands; commit only complete domain transactions."""
from typing import Annotated, Literal
from fastapi import APIRouter, Depends
from pydantic import Field
from sqlalchemy.orm import Session
from app.api.notice import actor, trusted_origin, Command, errors
from app.infrastructure.database import get_session
from app.company.improvement_analysis import ImprovementAnalysis

router=APIRouter(prefix='/company',tags=['Improvement analysis'])
DB=Annotated[Session,Depends(get_session)]
def service(session):
    from app.api.company import application
    return ImprovementAnalysis(application(session))
class Key(Command):
    idempotency_key:str=Field(min_length=1,max_length=100)
class AnalysisRequest(Key):
    provider:Literal['RULE','GPT','GEMINI','CLAUDE','GROK']='RULE'
    selection_token:str=Field(pattern='^[a-f0-9]{64}$')
    excluded_files:dict[str,str]=Field(default_factory=dict,max_length=100)
    reason:str=Field(min_length=1,max_length=1000)
    common_file_ids:list[str]=Field(default_factory=list,max_length=100)
    mode:Literal['MANUAL','ENSURE']='MANUAL'
class Retry(Key):
    expected_attempt:int=Field(ge=0)
class Review(Key):
    expected_review_ordinal:int=Field(ge=0)
    decision:Literal['USE_FOR_REQUEST','EXCLUDE','NEEDS_CHECK']
    note:str=Field(min_length=1,max_length=5000)
    question:str=Field(default='',max_length=5000)
class DraftCreate(Key):
    run_id:str
    review_ids:list[str]=Field(min_length=1,max_length=100)
class DraftSave(Key):
    expected_ordinal:int=Field(ge=1)
    title:str=Field(min_length=1,max_length=300)
    message:str=Field(min_length=1,max_length=10000)
    due_date:str|None=None
    review_ids:list[str]=Field(min_length=1,max_length=100)
class Send(Command):
    expected_ordinal:int=Field(ge=1)
class SubmissionJudgement(Key):
    expected_ordinal:int=Field(ge=0)
    decision:Literal['COMPLETED','NEEDS_CHECK','PREPARE_REQUEST']
    note:str=Field(min_length=1,max_length=5000)
    run_id:str|None=None
    job_id:str|None=None
    draft_id:str|None=None
    analysis_limit:str=Field(default='',max_length=5000)

@router.get('/improvements/{vid}/submission-reviews',response_model=dict,responses=errors(401,403,404))
def submission_reviews(vid:str,session:DB,who=Depends(actor)):
    from app.company.submission_review import SubmissionReview
    svc=SubmissionReview(service(session).a)
    return dict(history=svc.history(who,vid),projection=svc.projection(who,vid))

@router.post('/improvements/{vid}/submission-reviews',response_model=dict,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422))
def judge_submission(vid:str,body:SubmissionJudgement,session:DB,who=Depends(actor)):
    from app.company.submission_review import SubmissionReview
    result=SubmissionReview(service(session).a).save(who,vid,body.idempotency_key,body.expected_ordinal,body.decision,body.note,body.run_id,body.job_id,body.draft_id,body.analysis_limit)
    session.commit();return result

@router.get('/analysis/providers',response_model=dict,responses=errors(401,403))
def providers(session:DB,who=Depends(actor)):
    service(session).a.role(who,'DATCO_OPERATOR')
    from app.company.improvement_providers import provider_status
    return provider_status()

@router.get('/improvements/{vid}/analysis-inputs',response_model=dict,responses=errors(401,403,404))
def inputs(vid:str,session:DB,who=Depends(actor)):return service(session).sources(who,vid)
@router.post('/improvements/{vid}/analysis-jobs',response_model=dict,status_code=202,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422))
def request(vid:str,body:AnalysisRequest,session:DB,who=Depends(actor)):
    svc=service(session);result=svc.request(who,vid,body.idempotency_key,body.selection_token,body.excluded_files,body.reason,body.common_file_ids,body.mode=='ENSURE',body.provider);session.commit();return svc.job(who,result['id'])
@router.get('/analysis-jobs/{jid}',response_model=dict,responses=errors(401,403,404))
def job(jid:str,session:DB,who=Depends(actor)):return service(session).job(who,jid)
@router.post('/analysis-jobs/{jid}/retry',response_model=dict,status_code=202,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409))
def retry(jid:str,body:Retry,session:DB,who=Depends(actor)):
    result=service(session).retry(who,jid,body.idempotency_key,body.expected_attempt);session.commit();return result
@router.get('/improvements/{vid}/analysis-runs',response_model=list[dict],responses=errors(401,403,404))
def runs(vid:str,session:DB,who=Depends(actor)):return service(session).listing(who,vid)
@router.get('/analysis-runs/{rid}',response_model=dict,responses=errors(401,403,404))
def run(rid:str,session:DB,who=Depends(actor)):return service(session).run(who,rid)
@router.post('/analysis-candidates/{cid}/reviews',response_model=dict,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422))
def review(cid:str,body:Review,session:DB,who=Depends(actor)):
    result=service(session).review(who,cid,body.idempotency_key,body.expected_review_ordinal,body.decision,body.note,body.question);session.commit();return result
@router.get('/improvements/{vid}/analysis-drafts',response_model=list[dict],responses=errors(401,403,404))
def drafts(vid:str,session:DB,who=Depends(actor)):
    from app.infrastructure import improvement_schema as S
    svc=service(session);svc.target(who,vid)
    return [svc.draft(who,d['id']) for d in svc.a.rows(S.drafts,version_id=vid,actor_id=who.id)]
@router.post('/analysis-drafts',response_model=dict,status_code=201,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422))
def draft_create(body:DraftCreate,session:DB,who=Depends(actor)):
    result=service(session).create_draft(who,body.run_id,body.idempotency_key,body.review_ids);session.commit();return result
@router.get('/analysis-drafts/{did}',response_model=dict,responses=errors(401,403,404))
def draft(did:str,session:DB,who=Depends(actor)):return service(session).draft(who,did)
@router.post('/analysis-drafts/{did}/versions',response_model=dict,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422))
def draft_save(did:str,body:DraftSave,session:DB,who=Depends(actor)):
    result=service(session).save_draft(who,did,body.idempotency_key,body.expected_ordinal,body.title,body.message,body.due_date,body.review_ids);session.commit();return result
@router.post('/analysis-drafts/{did}/send',response_model=dict,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422))
def send(did:str,body:Send,session:DB,who=Depends(actor)):
    result=service(session).send(who,did,body.expected_ordinal);session.commit();return result
