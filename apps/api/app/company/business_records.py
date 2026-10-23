"""Approved provenance and file lifecycle commands, within Company scope."""
from app.infrastructure import company_schema as S
from app.infrastructure import company_business_schema as B
from app.notice.domain import Denied
import re

class BusinessRecords:
 def active_file(self,file_id):
  f=self.get(S.files,file_id,True)
  if self.rows(B.file_events,file_id=file_id):raise Denied('COMPANY_FILE_INACTIVE',409)
  return f
 def file_event(self,who,file_id,kind,note,replacement_id=None):
  self.role(who,'COMPANY_EDITOR');f=self.get(S.files,file_id);self.scope(who,f['company_id'],True);self.active_file(file_id)
  if kind not in ('REPLACED','CANCELLED') or not note.strip() or len(note)>2000:raise Denied('INVALID_REQUEST',422)
  if kind=='REPLACED':
   replacement=self.get(S.files,replacement_id)
   if replacement['company_id']!=f['company_id']:raise Denied('OBJECT_NOT_FOUND',404)
   self.active_file(replacement_id)
   if replacement_id==file_id:raise Denied('INVALID_REPLACEMENT',422)
   from app.company.file_replacement import replace_draft_attachment
   replace_draft_attachment(self,who,f,replacement)
  elif replacement_id is not None:raise Denied('INVALID_REPLACEMENT',422)
  event=self.add(B.file_events,company_id=f['company_id'],file_id=file_id,replacement_id=replacement_id,actor_id=who.id,kind=kind,note=note.strip())
  self.record(who,f['company_id'],'COMPANY_FILE_'+kind,file_id=file_id)
  return event
 def link_business_sources(self,who,cid,version,data):
  previous=next((v['data'] for v in self.rows(S.inputs,company_id=cid) if v['ordinal']==version['ordinal']-1),{})
  for kind,key in (('finance','financials'),('history','history')):
   for index,row in enumerate(data[key]):
    pid=row.get('source_parse_id');source_index=row.get('source_index')
    if pid is None:continue
    matches=self.rows(B.extractions,parse_id=pid)
    if not matches or matches[0]['company_id']!=cid:raise Denied('OBJECT_NOT_FOUND',404)
    extracted=matches[0]
    if extracted['kind']!=kind or source_index>=len(extracted['entries']):raise Denied('INVALID_BUSINESS_SOURCE',422)
    if self.rows(B.file_events,file_id=extracted['file_id']):
     # An unchanged historical source may be carried; no new occurrence or
     # changed business value may acquire an inactive source.
     if data[key][:index+1].count(row)>previous.get(key,[]).count(row):raise Denied('COMPANY_FILE_INACTIVE',409)
    else:self.active_file(extracted['file_id'])
    source=extracted['entries'][source_index];proofs=self.rows(S.evidence,parse_id=pid)
    values=dict(source.get('values',{}),year=source.get('year')) if kind=='finance' else {k:source.get(k) for k in ('name','period','agency')}
    locations=source.get('sources',{})
    for field,value in values.items():
     if value is None or value=='':continue
     refs=locations.get(field,[]) if isinstance(locations,dict) else [r for r in locations if r.get('field')==field]
     for ref in refs:
      candidates=[p for p in proofs if p['page']==ref.get('page') and (not ref.get('descriptor') or p['descriptor']==ref['descriptor']) and re.sub(r'\s+','',ref.get('text','')) in re.sub(r'\s+','',p['text'])]
      if not candidates:raise Denied('BUSINESS_SOURCE_EVIDENCE_MISSING',409)
      self.add(B.sources,company_id=cid,input_version_id=version['id'],extraction_id=extracted['id'],evidence_id=candidates[0]['id'],kind=kind,row_index=index,source_index=source_index,field=field,original_value=value,saved_value=row.get(field))
 def standard_business_parse(self,who,f,purpose):
  self.role(who,'COMPANY_EDITOR');self.active_file(f['id'])
  from app.company.statement_documents import analyze_financial_pdf,layout_pdf,history_candidates
  from app.company.documents import DocumentError
  raw=self.files.read(f['storage_key'],f['digest'])
  try:
   if purpose=='finance':parsed,entries=analyze_financial_pdf(f['name'],raw)
   else:
    parsed=layout_pdf(f['name'],raw);candidate=history_candidates(parsed);entries=[candidate] if any(candidate[k] for k in ('name','period','agency')) else []
   run=self.add(S.parses,file_id=f['id'],actor_id=who.id,parser_version=parsed.parser_version,error=None,limitations=list(parsed.limitations))
  except DocumentError as e:return self.add(S.parses,file_id=f['id'],actor_id=who.id,parser_version='standard-business-v1',error=str(e),limitations=[])
  for loc in parsed.locations:self.add(S.evidence,actor_id=who.id,company_id=f['company_id'],site_id=f['site_id'],file_id=f['id'],input_version_id=None,parse_id=run['id'],descriptor=loc.descriptor,page=loc.page,text=loc.text,mode='RULE_BASED_EXTRACTION')
  self.add(B.extractions,parse_id=run['id'],company_id=f['company_id'],file_id=f['id'],kind=purpose,entries=entries)
  visible=[]
  for index,entry in enumerate(entries):
   fields=dict(year=entry['year'],period=entry['period'],unit=entry['unit'],currency=entry['currency'],**entry['values']) if purpose=='finance' else {k:entry.get(k,'') for k in ('name','period','agency')}
   visible.append(dict(fields,source_parse_id=run['id'],source_index=index))
  self.record(who,f['company_id'],'PARSE_COMPANY_FILE',file_id=f['id'])
  return dict(run,entries=visible,extraction=entries)
