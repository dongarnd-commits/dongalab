from typing import Annotated,Literal
from datetime import datetime
from fastapi import APIRouter,Depends
from pydantic import Field,BaseModel
from sqlalchemy.orm import Session
from app.api.notice import actor,trusted_origin,Command,Retry,errors
from app.core.config import ROOT
from app.infrastructure.database import get_session
from app.infrastructure.notice_store import SqlNoticeStore
from app.infrastructure.notice_documents import LocalPrivateFiles
from app.collector.application import CollectionApplication
from app.infrastructure import collector_schema

router=APIRouter(prefix="/notice/collections",tags=["Bizinfo collection"])
class CollectionRequest(Command):
    mode: Literal["LIVE","SNAPSHOT"]
    idempotency_key: str=Field(min_length=1,max_length=100)
    page_unit: int=Field(default=2,ge=1,le=5)
    max_pages: int=Field(default=3,ge=1,le=5)
class RecordResponse(BaseModel):
    id: str
    position: int
    external_id: str | None
    notice_id: str | None
    notice_version_id: str | None
    outcome: str
    error: str | None
    acquisitions: list[dict]
class PageResponse(BaseModel):
    id: str
    page_number: int
    state: str
    error: str | None
    observed_count: int
    expected_total: int | None
    warnings: list[str]
    records: list[RecordResponse]
class AttemptResponse(BaseModel):
    id: str
    ordinal: int
    state: str
    error: str | None
    pages: list[PageResponse]
class CollectionJobResponse(BaseModel):
    historical_replay: bool = False
    current_valid: bool = True
    id: str
    created_at: datetime
    state: Literal["QUEUED","PROCESSING","SUCCEEDED","PARTIAL","FAILED"]
    error: str | None
    payload: dict
    attempts: list[AttemptResponse]=Field(default_factory=list)

def application(session):
    return CollectionApplication(SqlNoticeStore(session),LocalPrivateFiles(ROOT/"storage/private/notice"))
@router.post("",response_model=CollectionJobResponse,dependencies=[Depends(trusted_origin)],responses=errors(401,403,409,422,503))
def request_collection(body: CollectionRequest,session: Annotated[Session,Depends(get_session)],who=Depends(actor)):
    result=application(session).request(who,body.mode,body.idempotency_key,body.page_unit,body.max_pages)
    session.commit()
    return result
@router.get("",response_model=list[CollectionJobResponse],responses=errors(401,403,503))
def list_collections(session: Annotated[Session,Depends(get_session)],who=Depends(actor)):
    return application(session).list(who)
@router.get("/{job_id}",response_model=CollectionJobResponse,responses=errors(401,403,404,409,422,503))
def collection_detail(job_id: str,session: Annotated[Session,Depends(get_session)],who=Depends(actor)):
    return application(session).detail(who,job_id)
@router.post("/{job_id}/retry",response_model=CollectionJobResponse,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422,503))
def retry_collection(job_id: str,body: Retry,session: Annotated[Session,Depends(get_session)],who=Depends(actor)):
    result=application(session).retry(who,job_id,body.idempotency_key)
    session.commit()
    return result
