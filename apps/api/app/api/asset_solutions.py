"""Explicitly generated technical drafts; read endpoints have no side effects."""
from typing import Annotated
from fastapi import APIRouter, Depends
from pydantic import Field
from sqlalchemy.orm import Session
from app.api.notice import actor, trusted_origin, Command, errors
from app.api.capability import application
from app.infrastructure.database import get_session
from app.capability import asset_composition

router = APIRouter(prefix="/capability", tags=["DMP solution drafts"])

class Generate(Command):
    idempotency_key: str = Field(min_length=1, max_length=100)

@router.post("/improvements/{version_id}/asset-solutions", response_model=dict,
             dependencies=[Depends(trusted_origin)], responses=errors(401,403,404,409,422,503))
def generate(version_id: str, body: Generate, session: Annotated[Session, Depends(get_session)], who=Depends(actor)):
    result = asset_composition.generate(application(session), who, version_id, body.idempotency_key)
    session.commit()
    return result

@router.get("/improvements/{version_id}/asset-solutions", response_model=list[dict], responses=errors(401,403,404,409,503))
def listing(version_id: str, session: Annotated[Session, Depends(get_session)], who=Depends(actor)):
    return asset_composition.listing(application(session), who, version_id)

@router.get("/asset-solutions/{recommendation_id}", response_model=dict, responses=errors(401,403,404,409,503))
def detail(recommendation_id: str, session: Annotated[Session, Depends(get_session)], who=Depends(actor)):
    return asset_composition.detail(application(session), who, recommendation_id)
