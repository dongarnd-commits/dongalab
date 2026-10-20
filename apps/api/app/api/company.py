from typing import Annotated, Literal
from urllib.parse import quote,unquote
from fastapi import APIRouter,Depends,Request,Response,Query,Header
from sqlalchemy.orm import Session
from pydantic import Field
from app.api.notice import actor,trusted_origin,Command,errors
from app.infrastructure.database import get_session
from app.infrastructure import company_schema as S
from app.company.application import CompanyApplication
from app.company.contracts import Profile,Site,FactInput,Improvement
from app.company.documents import MAX_UPLOAD
from app.notice.domain import Denied

router=APIRouter(prefix='/company',tags=['Company intake'])
def application(session):
 from app.api import notice
 return CompanyApplication(session,notice.application(session).files)
DB=Annotated[Session,Depends(get_session)]
class ProfileSave(Command):
 data:Profile
 expected_ordinal:int=Field(ge=0)
class SiteSave(Command):
 data:Site
 site_id:str|None=None
 expected_ordinal:int=Field(default=0,ge=0)
class Grant(Command):
 username:str=Field(min_length=1,max_length=80)
class Evidence(Command):
 file_id:str
 site_id:str|None=None
 descriptor:str=Field(min_length=1,max_length=1000)
 transcription:str=Field(min_length=1,max_length=10000)
class Ack(Command):
 agreed:bool
 note:str=Field(min_length=1,max_length=5000)
class Review(Command):
 outcome:Literal['CONFIRM_NEW_VALUE','CONFIRM_EXISTING_VALUE','CONFLICT','REQUEST_MORE_INFORMATION','REJECT_CANDIDATE']
 note:str=Field(min_length=1,max_length=5000)
 existing_version_id:str|None=None
class ImprovementSave(Command):
 data:Improvement
 improvement_id:str|None=None
 expected_ordinal:int=Field(default=0,ge=0)
class ImprovementAction(Command):
 action:Literal['SUBMIT','ACKNOWLEDGE','CONFIRM','REQUEST_REVISION']
 note:str=Field(min_length=1,max_length=5000)

@router.get('',response_model=list[dict],responses=errors(401,403))
def listing(session:DB,who=Depends(actor),q:str=Query(default='',max_length=200)):
 return application(session).listing(who,q)
@router.get('/access',response_model=list[dict],responses=errors(401,403))
def access(session:DB,who=Depends(actor)):
 a=application(session);a.role(who,'DATCO_ADMIN');return [{'id':c['id'],'name':c['name']} for c in a.rows(S.companies)]
@router.post('',response_model=dict,dependencies=[Depends(trusted_origin)],responses=errors(401,403,409,422))
def register(body:Profile,session:DB,who=Depends(actor)):
 r=application(session).register(who,body.model_dump());session.commit();return r
@router.get('/{company_id}',response_model=dict,responses=errors(401,403,404))
def detail(company_id:str,session:DB,who=Depends(actor)):
 return application(session).detail(who,company_id)
@router.post('/{company_id}/access',response_model=dict,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,422))
def grant(company_id:str,body:Grant,session:DB,who=Depends(actor)):
 r=application(session).grant(who,company_id,body.username);session.commit();return r
@router.post('/{company_id}/profile',response_model=dict,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422))
def profile(company_id:str,body:ProfileSave,session:DB,who=Depends(actor)):
 r=application(session).save_profile(who,company_id,body.data.model_dump(),body.expected_ordinal);session.commit();return r
@router.post('/{company_id}/sites',response_model=dict,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422))
def site(company_id:str,body:SiteSave,session:DB,who=Depends(actor)):
 r=application(session).save_site(who,company_id,body.data.model_dump(),body.site_id,body.expected_ordinal);session.commit();return r
@router.post('/{company_id}/files',response_model=dict,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,413,422))
async def upload(company_id:str,request:Request,session:DB,who=Depends(actor),upload_name:str=Header(alias='X-Upload-Name',min_length=1,max_length=2400),site_id:str|None=None):
 a=application(session);a.role(who,'COMPANY_EDITOR');a.scope(who,company_id,True)
 parts=[];size=0
 async for chunk in request.stream():
  size+=len(chunk)
  if size>MAX_UPLOAD:raise Denied('UPLOAD_SIZE_INVALID',413)
  parts.append(chunk)
 try:name=unquote(upload_name,encoding='utf-8',errors='strict')
 except UnicodeDecodeError:raise Denied('INVALID_FILENAME',422) from None
 r=a.upload(who,company_id,name,b''.join(parts),site_id);session.commit();return r
@router.get('/files/{file_id}/download',responses=errors(401,403,404))
def download(file_id:str,session:DB,who=Depends(actor)):
 f,raw=application(session).download(who,file_id)
 return Response(raw,media_type=f['media_type'],headers={'Content-Disposition':"attachment; filename*=UTF-8''"+quote(f['name'],safe=''),'X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'none'; sandbox",'Cache-Control':'no-store'})
@router.post('/files/{file_id}/parse',response_model=dict,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404))
def parse(file_id:str,session:DB,who=Depends(actor)):
 r=application(session).parse(who,file_id);session.commit();return r
@router.post('/{company_id}/evidence',response_model=dict,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,422))
def evidence(company_id:str,body:Evidence,session:DB,who=Depends(actor)):
 r=application(session).manual_evidence(who,company_id,body.file_id,body.site_id,body.descriptor,body.transcription);session.commit();return r
@router.post('/{company_id}/candidates',response_model=dict,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,422))
def candidate(company_id:str,body:FactInput,session:DB,who=Depends(actor)):
 r=application(session).new_candidate(who,company_id,body.model_dump(mode='json'));session.commit();return r
@router.post('/candidates/{candidate_id}/acknowledge',response_model=dict,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404))
def acknowledge(candidate_id:str,body:Ack,session:DB,who=Depends(actor)):
 r=application(session).acknowledge(who,candidate_id,body.agreed,body.note);session.commit();return r
@router.post('/candidates/{candidate_id}/review',response_model=dict,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422))
def review(candidate_id:str,body:Review,session:DB,who=Depends(actor)):
 r=application(session).review(who,candidate_id,body.outcome,body.note,body.existing_version_id);session.commit();return r
@router.post('/{company_id}/improvements',response_model=dict,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422))
def improvement(company_id:str,body:ImprovementSave,session:DB,who=Depends(actor)):
 r=application(session).save_improvement(who,company_id,body.data.model_dump(),body.improvement_id,body.expected_ordinal);session.commit();return r
@router.post('/improvements/{version_id}/actions',response_model=dict,dependencies=[Depends(trusted_origin)],responses=errors(401,403,404,409,422))
def improvement_action(version_id:str,body:ImprovementAction,session:DB,who=Depends(actor)):
 r=application(session).improvement_action(who,version_id,body.action,body.note);session.commit();return r
@router.get('/improvements/{version_id}/context',response_model=dict,responses=errors(401,403,404))
def context(version_id:str,session:DB,who=Depends(actor)):
 return application(session).read_context(who,version_id)

@router.get('/{company_id}/navigation',response_model=dict,responses=errors(401,403,404,409,422))
def navigation(company_id:str,session:DB,who=Depends(actor),site_id:str|None=Query(default=None,max_length=36),improvement_id:str|None=Query(default=None,max_length=36),version_id:str|None=Query(default=None,max_length=36),site_ordinal:int|None=Query(default=None,ge=1)):
 from app.company.navigation import read_navigation
 return read_navigation(application(session),who,company_id,site_id,improvement_id,version_id,site_ordinal)
