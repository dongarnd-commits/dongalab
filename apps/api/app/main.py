from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.health import router
from app.api.notice import router as notice_router, ErrorResponse
from app.api.collection import router as collection_router
from app.notice.domain import Denied
from fastapi.responses import JSONResponse
from app.core.config import get_settings

app = FastAPI(title="DATCO Skeleton API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=[get_settings().web_origin], allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["Accept", "Content-Type"])
app.include_router(router)


@app.exception_handler(Denied)
async def denied_handler(request,exc):
    return JSONResponse(status_code=exc.status,content=ErrorResponse(reason=exc.reason).model_dump())

app.include_router(collection_router)
app.include_router(notice_router)

from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

@app.exception_handler(RequestValidationError)
async def input_error(request,exc):
    return JSONResponse(status_code=422,content=ErrorResponse(reason="INVALID_REQUEST").model_dump())

@app.exception_handler(SQLAlchemyError)
async def storage_error(request,exc):
    return JSONResponse(status_code=503,content=ErrorResponse(reason="STORAGE_UNAVAILABLE").model_dump())

from app.api.capability import router as capability_router
app.include_router(capability_router)

from app.api.proposal import router as proposal_router
app.include_router(proposal_router)

from app.api.company import router as company_router
app.include_router(company_router)

from app.api.workspace import router as workspace_router
app.include_router(workspace_router)

from app.api.improvement_analysis import router as improvement_analysis_router
app.include_router(improvement_analysis_router)

from app.api.admin import router as admin_router
app.include_router(admin_router)
