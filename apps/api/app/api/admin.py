"""Read-only MVP administration; existing Membership commands stay in Company."""
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.notice import actor, errors
from app.infrastructure.database import get_session
from app.operations.admin import AdminProjection
from app.core.config import get_settings

router = APIRouter(prefix='/admin', tags=['MVP administration'])
DB = Annotated[Session, Depends(get_session)]


@router.get('/overview', response_model=dict, responses=errors(401, 403, 503))
def overview(session: DB, who=Depends(actor)):
    return AdminProjection(session).overview(who)


@router.get('/access', response_model=dict, responses=errors(401, 403, 503))
def access(session: DB, who=Depends(actor)):
    return AdminProjection(session).access(who)


@router.get('/connections', response_model=dict, responses=errors(401, 403, 503))
def connections(session: DB, who=Depends(actor)):
    projection = AdminProjection(session)
    projection.authorize(who)
    configured = get_settings().bizinfo_api_key
    return projection.connections(who, bool(configured and configured.get_secret_value()))
