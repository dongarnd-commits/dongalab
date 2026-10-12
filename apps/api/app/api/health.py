from typing import Annotated, Literal
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.infrastructure.database import get_session

router = APIRouter()

class HealthResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    service: Literal["api", "database"]

@router.get("/health", response_model=HealthResponse, operation_id="application_health")
def health() -> HealthResponse:
    return HealthResponse(status="ready", service="api")

@router.get("/health/db", response_model=HealthResponse, responses={503: {"model": HealthResponse}}, operation_id="database_health")
def database_health(session: Annotated[Session, Depends(get_session)]):
    try:
        if session.execute(text("SELECT 1")).scalar_one() == 1:
            return HealthResponse(status="ready", service="database")
    except SQLAlchemyError:
        # Do not expose driver exceptions or credentials.
        pass
    return JSONResponse(status_code=503, content=HealthResponse(status="not_ready", service="database").model_dump())
