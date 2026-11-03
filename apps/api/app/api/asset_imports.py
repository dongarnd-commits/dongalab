"""Administrator-only bounded XLSX source import; never a provision confirmation."""
from typing import Annotated
from urllib.parse import quote, unquote
from fastapi import APIRouter, Depends, Request, Response, Header
from pydantic import Field
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from app.api.notice import actor, trusted_origin, Command, errors
from app.api.capability import application as capability_application
from app.capability.workbook_import import WorkbookImportApplication, MAX_ROWS
from app.company.documents import MAX_UPLOAD
from app.infrastructure.database import get_session
from app.notice.domain import Denied

router = APIRouter(prefix="/capability/asset-imports", tags=["Asset workbook intake"])
DB = Annotated[Session, Depends(get_session)]

class Selection(Command):
    row_key: str = Field(min_length=1, max_length=40)
    resolution: str | None = Field(default=None, pattern=r"^(NEW|DMP-[A-F0-9]{16})$")

class ApplyWorkbook(Command):
    file_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    parser_version: str = Field(min_length=1, max_length=100)
    catalog_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    preview_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    selections: list[Selection] = Field(min_length=1, max_length=MAX_ROWS)
    idempotency_key: str = Field(min_length=1, max_length=100)

@router.post("/preview", response_model=dict, dependencies=[Depends(trusted_origin)], responses=errors(401,403,413,422))
async def preview(request: Request, session: DB, who=Depends(actor),
                  upload_name: str = Header(alias="X-Upload-Name", min_length=1, max_length=2400)):
    service = capability_application(session)
    service.authorize(who, True)
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_UPLOAD:
            raise Denied("UPLOAD_SIZE_INVALID", 413)
        chunks.append(chunk)
    try:
        filename = unquote(upload_name, encoding="utf-8", errors="strict")
    except UnicodeError:
        raise Denied("WORKBOOK_FILENAME_INVALID", 422) from None
    result = await run_in_threadpool(WorkbookImportApplication(service).preview, who, filename, b"".join(chunks))
    session.commit()
    return result

@router.post("/apply", response_model=dict, dependencies=[Depends(trusted_origin)], responses=errors(401,403,404,409,422))
def apply(body: ApplyWorkbook, session: DB, who=Depends(actor)):
    result = WorkbookImportApplication(capability_application(session)).apply(who,
        file_sha256=body.file_sha256, parser_version=body.parser_version, catalog_digest=body.catalog_digest,
        preview_digest=body.preview_digest, selections=[row.model_dump() for row in body.selections], key=body.idempotency_key)
    session.commit()
    return result

@router.get("/{file_sha256}/original", responses=errors(401,403,404,422))
def original(file_sha256: str, session: DB, who=Depends(actor)):
    if len(file_sha256) != 64 or any(c not in "0123456789abcdef" for c in file_sha256):
        raise Denied("OBJECT_NOT_FOUND", 404)
    content, name = WorkbookImportApplication(capability_application(session)).original(who, file_sha256)
    return Response(content, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename*=UTF-8''" + quote(name),
                 "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
