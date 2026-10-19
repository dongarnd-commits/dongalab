"""Read-only, scoped projections for W0 navigation; no business decisions."""
from typing import Annotated
from fastapi import APIRouter,Depends
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.api.notice import actor,errors
from app.api.company import application
from app.infrastructure.database import get_session
from app.infrastructure import company_schema as C,capability_schema as B,proposal_schema as P,notice_schema as N
router=APIRouter(prefix='/workspace',tags=['Workspace navigation'])
@router.get('',response_model=dict,responses=errors(401,403,503))
def dashboard(session:Annotated[Session,Depends(get_session)],who=Depends(actor)):
 a=application(session);a.role(who,'COMPANY_EDITOR','COMPANY_APPROVER','DATCO_OPERATOR','DATCO_ADMIN')
 username=session.execute(select(N.actors.c.username).where(N.actors.c.id==who.id)).scalar_one()
 result=dict(actor=dict(id=who.id,role=who.role,username=username),companies=[],compositions=[],matches=[],proposals=[],catalog=None)
 if who.role=='DATCO_ADMIN':
  result['companies']=[dict(id=c['id'],name=c['name']) for c in a.rows(C.companies)]
  result['catalog']=dict(features=session.scalar(select(func.count()).select_from(B.features)),published=session.scalar(select(func.count()).select_from(B.capabilities).where(B.capabilities.c.current_ordinal>0)))
  return result
 for company in a.listing(who):
  cid=company['id'];d=a.detail(who,cid)
  result['companies'].append(dict(id=cid,name=company['name'],sites=[dict(id=s['id'],name=s['name']) for s in d['sites']],improvements=[dict(id=i['id'],title=i['title'],state=i['state'],version_id=i['versions'][-1]['id'],site_id=i['site_id']) for i in d['improvements'] if i['versions']],counts=dict(files=len(d['files']),candidates=len(d['candidates']),facts=len(d['facts']),pending_facts=sum(not c['reviews'] for c in d['candidates']),improvements=len(d['improvements']))))
  if who.role=='DATCO_OPERATOR':
   for root in a.rows(B.compositions,company_id=cid):
    vs=a.rows(B.composition_versions,composition_id=root['id']);v=next((v for v in vs if v['ordinal']==root['current_ordinal']),None)
    if not v:continue
    result['compositions'].append(dict(id=root['id'],version_id=v['id'],ordinal=v['ordinal'],company_id=cid,improvement_version_id=v['improvement_version_id'],name=v['data']['name']))
    for snap in a.rows(B.match_snapshots,composition_version_id=v['id']):
     for candidate in a.rows(B.match_candidates,snapshot_id=snap['id']):
      result['matches'].append(dict(id=candidate['id'],company_id=cid,improvement_version_id=v['improvement_version_id'],composition_id=root['id'],name=v['data']['name'],fit=candidate['fit']))
  if who.role in ('DATCO_OPERATOR','COMPANY_APPROVER'):
   for root in a.rows(P.roots,company_id=cid):
    vs=a.rows(P.versions,proposal_id=root['id']);v=next((v for v in vs if v['ordinal']==root['current_ordinal']),None)
    if not v:continue
    requests=a.rows(P.requests,version_id=v['id'])
    if who.role=='COMPANY_APPROVER' and not any(q['intended_approver']==who.id for q in requests):continue
    result['proposals'].append(dict(id=root['id'],company_id=cid,title=v['title'],ordinal=v['ordinal'],improvement_version_id=v['manifest']['refs']['improvement_version_id'],pending=any(q['state']=='OPEN' for q in requests)))
 return result
