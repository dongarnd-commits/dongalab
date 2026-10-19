from typing import Annotated, Literal
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from app.core.config import ROOT,get_settings
from app.infrastructure.database import get_session
from app.infrastructure.notice_store import SqlNoticeStore
from app.infrastructure.notice_documents import LocalPrivateFiles
from app.infrastructure.local_auth import login,authenticated
from app.notice.application import NoticeApplication
from app.notice.domain import Denied

router=APIRouter(prefix="/notice",tags=["Notice review"])

class ErrorResponse(BaseModel):
    reason: str


def errors(*statuses):
    return {status:{"model":ErrorResponse} for status in statuses}


class Command(BaseModel):
    model_config=ConfigDict(extra="forbid")

class Login(Command):
    username: str=Field(min_length=1,max_length=80)
    password: str=Field(min_length=1,max_length=256)

class AnalysisRequest(Command):
    expected_version: str=Field(min_length=36,max_length=36)
    idempotency_key: str=Field(min_length=1,max_length=100)

class Retry(Command):
    idempotency_key: str=Field(min_length=1,max_length=100)

class Confirm(Command):
    expected_version: str=Field(min_length=36,max_length=36)
    official_verified: bool
    note: str=Field(min_length=1,max_length=2000)
    scope: str=Field(min_length=1,max_length=2000)
    conflict_resolution: str=Field(default="",max_length=2000)

class MoreSource(Command):
    expected_version: str=Field(min_length=36,max_length=36)
    note: str=Field(min_length=1,max_length=2000)

class ActorResponse(BaseModel):
    id: str
    role: str

class NoticeSummary(BaseModel):
    id: str
    title: str
    current_ordinal: int

class JobResponse(BaseModel):
    historical_replay: bool = False
    current_valid: bool = True
    id: str
    version_id: str
    state: Literal["QUEUED","PROCESSING","SUCCEEDED","PARTIAL","FAILED"]
    error: str | None

class LocationResponse(BaseModel):
    id: str
    source_id: str
    page: int | None
    descriptor: str
    text: str

class CandidateResponse(BaseModel):
    id: str
    kind: str
    content: str
    reason: str
    evidence: LocationResponse
    reviews: list[dict]

class RunResponse(BaseModel):
    id: str
    version_id: str
    provider_version: str
    extractor_version: str
    missing: list[dict]
    conflicts: list[dict]
    candidates: list[CandidateResponse]

class SourceResponse(BaseModel):
    id: str
    name: str
    media_type: str
    provenance: str

class RequirementResponse(BaseModel):
    historical_replay: bool = False
    current_valid: bool = True
    id: str
    notice_version_id: str
    ordinal: int
    scope: str

class ConfirmedResponse(RequirementResponse):
    review: dict
    items: list[dict]

class VersionResponse(BaseModel):
    id: str
    ordinal: int
    mode: str
    metadata: dict
    sources: list[SourceResponse]
    jobs: list[JobResponse]
    runs: list[RunResponse]
    confirmed: list[ConfirmedResponse]

class NoticeDetail(NoticeSummary):
    versions: list[VersionResponse]

def actor(request: Request,session: Annotated[Session,Depends(get_session)]):
    return authenticated(SqlNoticeStore(session),request.cookies.get("datco_session"))

def trusted_origin(request: Request):
    if request.headers.get("origin")!=get_settings().web_origin:
        raise Denied("UNTRUSTED_ORIGIN",403)

def application(session):
    return NoticeApplication(SqlNoticeStore(session),LocalPrivateFiles(ROOT/"storage/private/notice"))

@router.post("/session",response_model=ActorResponse,dependencies=[Depends(trusted_origin)],responses=errors(401,403,422,503))
def create_session(body: Login,response: Response,session: Annotated[Session,Depends(get_session)]):
    store=SqlNoticeStore(session)
    token=login(store,body.username,body.password)
    session.commit()
    response.set_cookie("datco_session",token,httponly=True,samesite="strict",secure=False,max_age=28800,path="/")
    return authenticated(store,token)

@router.get("/session",response_model=ActorResponse,responses=errors(401,503))
def session_actor(who=Depends(actor)):
    return who

@router.post('/session/logout',response_model=dict,dependencies=[Depends(trusted_origin)],responses=errors(401,403,503))
def end_session(request:Request,response:Response,session:Annotated[Session,Depends(get_session)]):
    from app.infrastructure.local_auth import logout
    logout(SqlNoticeStore(session),request.cookies.get('datco_session'))
    session.commit()
    response.delete_cookie('datco_session',path='/',httponly=True,samesite='strict')
    response.headers['Cache-Control']='no-store'
    return {'logged_out':True}

@router.get("",response_model=list[NoticeSummary],responses=errors(401,403,503))
def notice_list(session: Annotated[Session,Depends(get_session)],who=Depends(actor)):
    from app.notice.domain import authorize
    authorize(who)
    return SqlNoticeStore(session).rows("notices")

@router.get("/{notice_id}",response_model=NoticeDetail,responses=errors(401,403,404,422,503))
def detail(notice_id: str,session: Annotated[Session,Depends(get_session)],who=Depends(actor)):
    return application(session).detail(who,notice_id)

@router.post("/analysis",response_model=JobResponse,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422,503))
def request_analysis(body: AnalysisRequest,session: Annotated[Session,Depends(get_session)],who=Depends(actor)):
    result=application(session).request(who,body.expected_version,body.idempotency_key)
    session.commit()
    return result

@router.post("/jobs/{job_id}/retry",response_model=JobResponse,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422,503))
def retry(job_id: str,body: Retry,session: Annotated[Session,Depends(get_session)],who=Depends(actor)):
    result=application(session).retry(who,job_id,body.idempotency_key)
    session.commit()
    return result

@router.post("/candidates/{candidate_id}/confirm",response_model=RequirementResponse,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422,503))
def confirm(candidate_id: str,body: Confirm,session: Annotated[Session,Depends(get_session)],who=Depends(actor)):
    result=application(session).confirm(who,body.expected_version,candidate_id,body.official_verified,
        body.note,body.scope,body.conflict_resolution)
    session.commit()
    return result

@router.post("/candidates/{candidate_id}/more-source",response_model=dict,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422,503))
def more_source(candidate_id: str,body: MoreSource,session: Annotated[Session,Depends(get_session)],who=Depends(actor)):
    result=application(session).more_source(who,body.expected_version,candidate_id,body.note)
    session.commit()
    return result

@router.get("/sources/{source_id}/download",responses=errors(401,403,404,409,422,503))
def download(source_id: str,session: Annotated[Session,Depends(get_session)],who=Depends(actor)):
    source,content=application(session).download(who,source_id)
    session.commit()
    return Response(content,media_type=source["media_type"],headers={
        "Content-Disposition":"attachment; filename=notice-source",
        "X-Content-Type-Options":"nosniff","Content-Security-Policy":"sandbox","Cache-Control":"no-store"})
