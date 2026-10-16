from datetime import datetime
from hashlib import sha256
from typing import Annotated,Literal
from fastapi import APIRouter,Depends,Request,Query
from pydantic import BaseModel,Field
from sqlalchemy.orm import Session
from app.api.notice import actor,trusted_origin,Command,errors
from app.infrastructure.database import get_session
from app.core.config import ROOT
from app.infrastructure.notice_documents import LocalPrivateFiles
from app.infrastructure.dmp_inventory import InventoryError,Feature,Metadata,EXPECTED_SHA256
from app.notice.domain import Denied
from app.capability.application import CapabilityApplication

router=APIRouter(prefix='/capability',tags=['Capability Catalog'])
def application(session): return CapabilityApplication(session,LocalPrivateFiles(ROOT/'storage/private/notice'))
class FeatureRecord(BaseModel):
    id:str
    feature_id:str
    ordinal:int
    digest:str
    data:Feature
    created_at:datetime
class ImportRecord(BaseModel):
    id:str
    digest:str
    metadata:Metadata
    created_at:datetime
class FeatureRoot(BaseModel):
    id:str
    external_id:str
    created_at:datetime
class FeatureDetail(BaseModel):
    root:FeatureRoot
    revisions:list[FeatureRecord]
class InventoryPage(BaseModel):
    items:list[FeatureRecord]
    total:int
    page:int
    limit:int
    import_:ImportRecord | None=Field(alias='import')
    systems:list[str]
    groups:list[str]
class Function(Command):
    revision_id:str=Field(min_length=36,max_length=36)
    role:str=Field(min_length=1,max_length=2000)
class CapabilityData(Command):
    service:str=Field(min_length=1,max_length=500)
    description:str=Field(default='',max_length=5000)
    functions:list[Function]=Field(min_length=1,max_length=649)
    problems:list[str]=Field(min_length=1,max_length=100)
    conditions:list[str]=Field(default_factory=list,max_length=100)
    exclusions:list[str]=Field(default_factory=list,max_length=100)
    prerequisites:list[str]=Field(default_factory=list,max_length=100)
    scope:str=Field(min_length=1,max_length=10000)
    evidence_note:str=Field(min_length=1,max_length=5000)
class SaveCapability(Command):
    data:CapabilityData
    idempotency_key:str=Field(min_length=1,max_length=100)
    expected_revision:int | None=Field(default=None,ge=1)
class Publish(Command):
    expected_revision:int=Field(ge=1)
    idempotency_key:str=Field(min_length=1,max_length=100)
class Receipt(BaseModel):
    id:str
    draft_revision:int | None=None
    capability_id:str | None=None
    ordinal:int | None=None
    version_id:str | None=None
    feature_count:int | None=None
    replay:bool | None=None
class CatalogItem(BaseModel):
    id:str
    current_ordinal:int
    version_id:str | None
    data:CapabilityData
    search_reasons:list[str]
class DetailResponse(BaseModel):
    root:dict
    versions:list[dict]
    assessments:list[dict]=Field(default_factory=list)
    capability_versions:list[dict]=Field(default_factory=list)
class Coverage(Command):
    requirement:str=Field(min_length=1,max_length=5000)
    capability_version_id:str=Field(min_length=36,max_length=36)
    feature_revision_ids:list[str]
    role:str=Field(min_length=1,max_length=2000)
    addressed_scope:str=Field(max_length=5000)
    unaddressed_scope:str=Field(max_length=5000)
    missing_information:list[str]=Field(default_factory=list)
class CompositionData(Command):
    name:str=Field(min_length=1,max_length=500)
    improvement_version_id:str=Field(min_length=1,max_length=100)
    capability_version_ids:list[str]=Field(min_length=1,max_length=100)
    excluded_feature_revision_ids:list[str]=Field(default_factory=list,max_length=649)
    coverage:list[Coverage]=Field(min_length=1,max_length=100)
    conditions:list[str]=Field(default_factory=list)
    unresolved:list[str]=Field(default_factory=list)
class SaveComposition(Command):
    data:CompositionData
    expected_version:str | None=None
    idempotency_key:str=Field(min_length=1,max_length=100)
class MatchRequest(Command):
    composition_version_id:str
    notice_id:str
    requirement_version_id:str
    idempotency_key:str=Field(min_length=1,max_length=100)
class CompletionItem(Command):
    task_id:str
    decision:Literal['CONFIRMED','NOT_APPLICABLE']
    note:str=Field(min_length=1,max_length=5000)
    proof_ids:list[str]=Field(min_length=1,max_length=100)
    notice_evidence_id:str|None=None

class Review(Command):
    completion_items:list[CompletionItem]|None=None
    outcome:Literal['PROPOSABLE','REQUEST_MORE_INFO','HOLD','EXCLUDE']
    note:str=Field(min_length=1,max_length=5000)
    idempotency_key:str=Field(min_length=1,max_length=100)
class CandidateReceipt(BaseModel):
    snapshot_id:str
    candidate_id:str
    fit:Literal['FIT','PARTIAL_FIT','NEED_MORE_INFO','MISMATCH']
    data:dict
class MatchDetail(BaseModel):
    candidate:dict
    snapshot:dict
    reviews:list[dict]
    current_valid:bool
    lineage:dict
class ReviewReceipt(BaseModel):
    id:str
    outcome:str
class CandidateSearch(BaseModel):
    context:dict
    candidates:list[CatalogItem]

@router.get('/features',response_model=InventoryPage,responses=errors(401,403,503))
def features(session:Annotated[Session,Depends(get_session)],who=Depends(actor),q:str=Query(default='',max_length=2000),system:str='',group:str='',page:int=Query(default=1,ge=1),limit:int=Query(default=25,ge=1,le=100),import_id:str | None=None):
    return application(session).inventory(who,q,system,group,page,limit,import_id)
@router.get('/features/{feature_id}',response_model=FeatureDetail,responses=errors(401,403,404))
def feature(feature_id:str,session:Annotated[Session,Depends(get_session)],who=Depends(actor)):
    return application(session).feature(who,feature_id)
@router.post('/imports',response_model=Receipt,dependencies=[Depends(trusted_origin)],responses=errors(401,403,409,422,503))
def import_source(session:Annotated[Session,Depends(get_session)],who=Depends(actor)):
    service=application(session); service.authorize(who,True)
    try:
        source=ROOT/'_local_inputs/dmp_features_649.json'
        raw=source.read_bytes()
        if sha256(raw).hexdigest()!=EXPECTED_SHA256: raise Denied('SOURCE_HASH_MISMATCH')
        result=service.import_inventory(raw,who)
    except FileNotFoundError: raise Denied('BLOCKED_SOURCE_MISSING',422) from None
    except InventoryError as exc: raise Denied(str(exc),422) from None
    session.commit(); return result
@router.get('/catalog',response_model=list[CatalogItem],responses=errors(401,403,503))
def catalog(session:Annotated[Session,Depends(get_session)],who=Depends(actor),q:str=Query(default='',max_length=2000)):
    return application(session).catalog(who,q)
@router.get('/catalog/{capability_id}',response_model=DetailResponse,responses=errors(401,403,404))
def capability(capability_id:str,session:Annotated[Session,Depends(get_session)],who=Depends(actor)):
    return application(session).capability(who,capability_id)
@router.post('/catalog',response_model=Receipt,dependencies=[Depends(trusted_origin)],responses=errors(401,403,409,422))
def create(body:SaveCapability,session:Annotated[Session,Depends(get_session)],who=Depends(actor)):
    result=application(session).save_capability(who,body.data.model_dump(),body.idempotency_key)
    session.commit(); return result
@router.post('/catalog/{capability_id}/draft',response_model=Receipt,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422))
def draft(capability_id:str,body:SaveCapability,session:Annotated[Session,Depends(get_session)],who=Depends(actor)):
    result=application(session).save_capability(who,body.data.model_dump(),body.idempotency_key,capability_id,body.expected_revision)
    session.commit(); return result
@router.post('/catalog/{capability_id}/publish',response_model=Receipt,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422))
def publish(capability_id:str,body:Publish,session:Annotated[Session,Depends(get_session)],who=Depends(actor)):
    result=application(session).publish(who,capability_id,body.expected_revision,body.idempotency_key)
    session.commit(); return result
@router.get('/improvements/{version_id}/candidates',response_model=CandidateSearch,responses=errors(401,403,404,503))
def candidates(version_id:str,session:Annotated[Session,Depends(get_session)],who=Depends(actor)):
    return application(session).candidates(who,version_id)
@router.post('/compositions',response_model=Receipt,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422,503))
def compose(body:SaveComposition,session:Annotated[Session,Depends(get_session)],who=Depends(actor)):
    result=application(session).save_composition(who,body.data.model_dump(),body.idempotency_key)
    session.commit(); return result
@router.post('/compositions/{composition_id}/versions',response_model=Receipt,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422,503))
def revise(composition_id:str,body:SaveComposition,session:Annotated[Session,Depends(get_session)],who=Depends(actor)):
    result=application(session).save_composition(who,body.data.model_dump(),body.idempotency_key,composition_id,body.expected_version)
    session.commit(); return result
@router.get('/compositions/{composition_id}',response_model=DetailResponse,responses=errors(401,403,404,503))
def composition(composition_id:str,session:Annotated[Session,Depends(get_session)],who=Depends(actor)):
    return application(session).composition(who,composition_id)
@router.post('/matches',response_model=CandidateReceipt,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422,503))
def match(body:MatchRequest,session:Annotated[Session,Depends(get_session)],who=Depends(actor)):
    result=application(session).prepare_match(who,body.composition_version_id,body.notice_id,body.requirement_version_id,body.idempotency_key)
    session.commit(); return result
@router.get('/matches/{candidate_id}',response_model=MatchDetail,responses=errors(401,403,404,503))
def match_detail(candidate_id:str,session:Annotated[Session,Depends(get_session)],who=Depends(actor)):
    return application(session).match(who,candidate_id)
@router.post('/matches/{candidate_id}/review',response_model=ReviewReceipt,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422,503))
def review(candidate_id:str,body:Review,session:Annotated[Session,Depends(get_session)],who=Depends(actor)):
    result=application(session).review_match(who,candidate_id,body.outcome,body.note,body.idempotency_key,[i.model_dump() for i in body.completion_items] if body.completion_items is not None else None)
    session.commit(); return result

class AssessmentReview(Command):
    decision:Literal['CONFIRMED','REVISION_REQUIRED']
    note:str=Field(min_length=1,max_length=5000)
    idempotency_key:str=Field(min_length=1,max_length=100)
class AssessmentReceipt(BaseModel):
    id:str
    state:Literal['CONFIRMED','REVISION_REQUIRED']
    fit:Literal['FIT','PARTIAL_FIT','NEED_MORE_INFO','MISMATCH']
@router.get('/assessments/{assessment_id}',response_model=dict,responses=errors(401,403,404,503))
def assessment(assessment_id:str,session:Annotated[Session,Depends(get_session)],who=Depends(actor)):
    return application(session).assessment(who,assessment_id)
@router.post('/assessments/{assessment_id}/review',response_model=AssessmentReceipt,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422,503))
def assessment_review(assessment_id:str,body:AssessmentReview,session:Annotated[Session,Depends(get_session)],who=Depends(actor)):
    result=application(session).review_assessment(who,assessment_id,body.decision,body.note,body.idempotency_key)
    session.commit(); return result

class AssessmentRequest(Command):
    improvement_version_id:str=Field(min_length=1,max_length=100)
    capability_version_id:str=Field(min_length=36,max_length=36)
    idempotency_key:str=Field(min_length=1,max_length=100)
class AssessmentCreated(BaseModel):
    id:str
    state:Literal['REVIEW_REQUIRED']
    fit:Literal['FIT','PARTIAL_FIT','NEED_MORE_INFO','MISMATCH']
    analysis_run_id:str
@router.post('/assessments',response_model=AssessmentCreated,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422,503))
def create_assessment(body:AssessmentRequest,session:Annotated[Session,Depends(get_session)],who=Depends(actor)):
    result=application(session).request_assessment(who,body.improvement_version_id,body.capability_version_id,body.idempotency_key)
    session.commit();return result
@router.post('/assessments/{assessment_id}/reassess',response_model=AssessmentCreated,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422,503))
def reassess(assessment_id:str,body:AssessmentRequest,session:Annotated[Session,Depends(get_session)],who=Depends(actor)):
    result=application(session).request_assessment(who,body.improvement_version_id,body.capability_version_id,body.idempotency_key,assessment_id)
    session.commit();return result


class ProposalPreparation(BaseModel):
    candidate_id: str
    can_create: bool
    policy_blockers: list[str]
    implementation_blockers: list[str]
    source_refs: dict
    source_summary:dict
    review_tasks:list[dict]
    review_evidence:list[dict]
    company_confirmed:bool

@router.get('/matches/{candidate_id}/proposal-preparation', response_model=ProposalPreparation,
            responses=errors(401,403,404,503))
def proposal_preparation(candidate_id: str, session: Annotated[Session, Depends(get_session)], who=Depends(actor)):
    from app.capability.proposal import preparation
    return preparation(application(session), who, candidate_id)
