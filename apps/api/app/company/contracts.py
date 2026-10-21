from typing import Literal
from datetime import date
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator

class Input(BaseModel):
 model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
class Financial(Input):
 year:int=Field(ge=1900,le=2200)
 revenue:str=Field(min_length=1,max_length=100)
 unit:str=Field(min_length=1,max_length=30)
 currency:str=Field(min_length=1,max_length=10)
 period:str=Field(min_length=1,max_length=100)
class History(Input):
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
