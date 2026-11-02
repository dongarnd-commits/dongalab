"""Internal DMP asset catalog. Administrator mutations never deploy DMP code."""
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, Query
from pydantic import Field
from sqlalchemy.orm import Session
from app.api.capability import application as capability_application
from app.api.notice import actor, trusted_origin, Command, errors
from app.capability.asset_catalog import AssetCatalogApplication
from app.infrastructure.database import get_session

router = APIRouter(prefix="/capability", tags=["DMP technical assets"])


def application(session):
    return AssetCatalogApplication(capability_application(session))


class AssetRelation(Command):
    target_node_id: str = Field(min_length=36, max_length=36)
    target_version_id: str | None = Field(default=None, min_length=36, max_length=36)
    kind: Literal["DEPENDENCY", "INTEGRATION", "REPLACEMENT"]
    condition: str = Field(min_length=1, max_length=10000)
    verified: bool = False
    evidence: str = Field(default="", max_length=10000)


class AssetData(Command):
    name: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=10000)
    role: str = Field(default="", max_length=10000)
    business_areas: list[str] = Field(default_factory=list, max_length=100)
    problems: list[str] = Field(default_factory=list, max_length=100)
    conditions: list[str] = Field(default_factory=list, max_length=100)
    exclusions: list[str] = Field(default_factory=list, max_length=100)
    prerequisites: list[str] = Field(default_factory=list, max_length=100)
    release: str = Field(default="", max_length=10000)
    availability: Literal["NEEDS_CONFIRMATION", "VERIFIED", "UNAVAILABLE", "RETIRED"] = "NEEDS_CONFIRMATION"
    availability_evidence: str = Field(default="", max_length=10000)
    relations: list[AssetRelation] = Field(default_factory=list, max_length=100)


class CreateAsset(Command):
    kind: Literal["SYSTEM", "MODULE", "FEATURE"]
    parent_id: str | None = Field(default=None, min_length=36, max_length=36)
    feature_id: str | None = Field(default=None, min_length=36, max_length=36)
    data: AssetData
    idempotency_key: str = Field(min_length=1, max_length=100)


class ReviseAsset(Command):
    parent_id: str | None = Field(default=None, min_length=36, max_length=36)
    expected_version: str = Field(min_length=36, max_length=36)
    data: AssetData
    idempotency_key: str = Field(min_length=1, max_length=100)


@router.get("/assets", response_model=dict, responses=errors(401, 403, 422))
def assets(session: Annotated[Session, Depends(get_session)], who=Depends(actor),
           kind: str = Query(default="", max_length=20),
           system: str = Query(default="", max_length=100),
           module: str = Query(default="", max_length=100),
           q: str = Query(default="", max_length=2000),
           status: str = Query(default="", max_length=30),
           page: int = Query(default=1, ge=1), limit: int = Query(default=25, ge=1, le=100)):
    return application(session).list_assets(who, kind=kind, system=system, module=module,
                                           q=q, status=status, page=page, limit=limit)


@router.get("/assets/{asset_id}", response_model=dict, responses=errors(401, 403, 404))
def asset(asset_id: str, session: Annotated[Session, Depends(get_session)], who=Depends(actor)):
    return application(session).detail(who, asset_id)


@router.post("/assets", response_model=dict, dependencies=[Depends(trusted_origin)],
             responses=errors(401, 403, 404, 409, 422))
def create_asset(body: CreateAsset, session: Annotated[Session, Depends(get_session)], who=Depends(actor)):
    result = application(session).create(who, kind=body.kind, parent_id=body.parent_id,
        feature_id=body.feature_id, data=body.data.model_dump(), key=body.idempotency_key)
    session.commit()
    return result


@router.post("/assets/{asset_id}/versions", response_model=dict, dependencies=[Depends(trusted_origin)],
             responses=errors(401, 403, 404, 409, 422))
def revise_asset(asset_id: str, body: ReviseAsset,
                 session: Annotated[Session, Depends(get_session)], who=Depends(actor)):
    kwargs = {"parent_id": body.parent_id} if "parent_id" in body.model_fields_set else {}
    result = application(session).revise(who, asset_id, expected_version=body.expected_version,
        data=body.data.model_dump(), key=body.idempotency_key, **kwargs)
    session.commit()
    return result
