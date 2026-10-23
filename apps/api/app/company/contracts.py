from typing import Literal
from datetime import date
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator, model_serializer

class Input(BaseModel):
 model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
class BusinessSource(Input):
 @model_serializer(mode='wrap')
 def preserve_legacy_shape(self,handler):
  data=handler(self)
  for key in ('source_parse_id','source_index','current_assets','noncurrent_assets','assets','current_liabilities','noncurrent_liabilities','liabilities','capital','equity','operating_income','net_income'):
   if data.get(key) is None:data.pop(key,None)
  if not data.get('consistency_note'):data.pop('consistency_note',None)
  return data
 source_parse_id:str|None=Field(default=None,min_length=1,max_length=36)
 source_index:int|None=Field(default=None,ge=0,le=99)
 @model_validator(mode='after')
 def paired_source(self):
  if (self.source_parse_id is None)!=(self.source_index is None):raise ValueError('BUSINESS_SOURCE_PAIR_REQUIRED')
  return self
class Financial(BusinessSource):
 year:int=Field(ge=1900,le=2200)
 revenue:str=Field(min_length=1,max_length=100)
 unit:str=Field(min_length=1,max_length=30)
 currency:str=Field(min_length=1,max_length=10)
 period:str=Field(min_length=1,max_length=100)
 # Optional exact won amounts; old input rows retain their original units.
 current_assets:str|None=Field(default=None,pattern=r'^-?[0-9]{1,30}$')
 noncurrent_assets:str|None=Field(default=None,pattern=r'^-?[0-9]{1,30}$')
 assets:str|None=Field(default=None,pattern=r'^-?[0-9]{1,30}$')
 current_liabilities:str|None=Field(default=None,pattern=r'^-?[0-9]{1,30}$')
 noncurrent_liabilities:str|None=Field(default=None,pattern=r'^-?[0-9]{1,30}$')
 liabilities:str|None=Field(default=None,pattern=r'^-?[0-9]{1,30}$')
 capital:str|None=Field(default=None,pattern=r'^-?[0-9]{1,30}$')
 equity:str|None=Field(default=None,pattern=r'^-?[0-9]{1,30}$')
 operating_income:str|None=Field(default=None,pattern=r'^-?[0-9]{1,30}$')
 net_income:str|None=Field(default=None,pattern=r'^-?[0-9]{1,30}$')
 consistency_note:str=Field(default='',max_length=2000)
 @model_validator(mode='after')
 def exact_financials(self):
  from app.company.statement_documents import ACCOUNTS,financial_checks
  values={k:getattr(self,k,None) for k in ACCOUNTS}
  detailed=any(v is not None for k,v in values.items() if k!='revenue')
  if detailed:
   import re
   if self.unit!='원' or self.currency!='KRW' or not re.fullmatch(r'-?[0-9]{1,30}',self.revenue):raise ValueError('EXACT_WON_CONTEXT_REQUIRED')
   if any(financial_checks(values)[k] is False for k in ('balance','assets','liabilities')) and not self.consistency_note:raise ValueError('FINANCIAL_INCONSISTENCY_REVIEW_REQUIRED')
  return self
class History(BusinessSource):
 name:str=Field(min_length=1,max_length=500)
 period:str=Field(min_length=1,max_length=100)
 agency:str=Field(min_length=1,max_length=500)
 role:str=Field(default='',max_length=1000)
class Profile(Input):
 @field_validator('business_number',mode='before')
 @classmethod
 def canonical_number(cls,value):
  from app.company.business_number import normalize_business_number
  return normalize_business_number(value)
 name:str=Field(min_length=1,max_length=200)
 business_number:str=Field(pattern=r'^(?:[0-9]{10}|[0-9]{3}-[0-9]{2}-[0-9]{5})$')
 industry:str=Field(default='',max_length=500)
 representative:str=Field(default='',max_length=200)
 contact:str=Field(default='',max_length=1000)
 overview:str=Field(default='',max_length=10000)
 financials:list[Financial]=Field(default_factory=list,max_length=100)
 history:list[History]=Field(default_factory=list,max_length=100)
class Site(Input):
 name:str=Field(min_length=1,max_length=200)
 address:str=Field(min_length=1,max_length=1000)
 industry:str=Field(default='',max_length=500)
 process:str=Field(default='',max_length=5000)
class FactInput(Input):
 evidence_id:str
 site_id:str|None=None
 field:Literal['company_name','business_number','industry','representative','address','revenue','employees','assets','liabilities','support_history','problem','to_be','constraint']
 value:str=Field(min_length=1,max_length=10000)
 period:str=Field(default='',max_length=100)
 unit:str=Field(default='',max_length=100)
 currency:str=Field(default='',max_length=20)
 valid_from:date
 @model_validator(mode='after')
 def financial(self):
  if self.field in ('revenue','assets','liabilities') and not(self.period and self.unit and self.currency):raise ValueError('FINANCIAL_CONTEXT_REQUIRED')
  return self
class Improvement(Input):
 title:str=Field(min_length=1,max_length=500)
 original_text:str=Field(min_length=1,max_length=20000)
 as_is:str=Field(default='',max_length=10000)
 problem:str=Field(default='',max_length=10000)
 impact:str=Field(default='',max_length=10000)
 goal:str=Field(default='',max_length=10000)
 to_be:str=Field(default='',max_length=10000)
 required_functions:str=Field(default='',max_length=10000)
 constraints:str=Field(default='',max_length=10000)
 missing:str=Field(default='',max_length=10000)
 site_id:str
 fact_version_ids:list[str]=Field(default_factory=list,max_length=100)
 evidence_ids:list[str]=Field(default_factory=list,max_length=100)
