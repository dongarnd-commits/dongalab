"""Internal authorization evidence; never impersonates an approver identity."""
from datetime import datetime,timezone
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator,ValidationError
from app.notice.domain import Denied
class Authorization(BaseModel):
 model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
 actual_approver_name:str=Field(min_length=1,max_length=200)
 actual_approver_title:str=Field(min_length=1,max_length=200)
 approved_at:datetime
 method:Literal['ORAL','DOCUMENT']
 context:str=Field(default='',max_length=5000)
 file_id:str|None=None
 @model_validator(mode='after')
 def evidence(self):
  if self.approved_at.tzinfo is None or self.approved_at>datetime.now(timezone.utc):raise ValueError('AUTHORIZATION_TIME_INVALID')
  if self.method=='ORAL' and (not self.context or self.file_id):raise ValueError('ORAL_AUTHORIZATION_CONTEXT_REQUIRED')
  if self.method=='DOCUMENT' and not self.file_id:raise ValueError('AUTHORIZATION_DOCUMENT_REQUIRED')
  return self

def validate_authorization(service,actor,company_id,data,version_created_at):
 from app.company.application import CompanyApplication
 from app.infrastructure import company_schema as C
 try:proof=Authorization.model_validate(data).model_dump()
 except ValidationError:raise Denied('AUTHORIZATION_EVIDENCE_REQUIRED',422) from None
 if proof['approved_at']<version_created_at:raise Denied('AUTHORIZATION_TIME_INVALID',422)
 app=CompanyApplication(service.session,service.files);app.role(actor,'COMPANY_EDITOR');app.scope(actor,company_id)
 if proof['file_id']:
  f=app.get(C.files,proof['file_id'])
  if f['company_id']!=company_id:raise Denied('OBJECT_NOT_FOUND',404)
  app.active_file(f['id']);service.files.read(f['storage_key'],f['digest'])
 return proof
