"""Read-only navigation within existing editor/operator Company Scope. No Provider locks/writes."""
from app.infrastructure import company_schema as S
from app.notice.domain import Denied

def read_navigation(a,who,cid,site_id=None,improvement_id=None,version_id=None,site_ordinal=None):
 a.role(who,'COMPANY_EDITOR','DATCO_OPERATOR');company=a.scope(who,cid)
 sites=[]
 for s in a.rows(S.sites,company_id=cid):
  versions=[dict(ordinal=v['ordinal'],data={k:v['data'].get(k,'') for k in ('name','address','industry','process')}) for v in sorted(a.rows(S.site_versions,site_id=s['id']),key=lambda v:v['ordinal'])]
  sites.append(dict(id=s['id'],name=s['name'],current_ordinal=s['current_ordinal'],versions=versions))
 improvements=[]
 fields=('title','original_text','as_is','problem','impact','goal','to_be','required_functions','constraints','missing')
 for i in a.rows(S.improvements,company_id=cid):
  versions=[dict(id=v['id'],ordinal=v['ordinal'],site_ordinal=v['site_ordinal'],data={k:v['data'].get(k,'') for k in fields}) for v in sorted(a.rows(S.improvement_versions,improvement_id=i['id']),key=lambda v:v['ordinal'])]
  improvements.append(dict(id=i['id'],site_id=i['site_id'],title=i['title'],state=i['state'],current_ordinal=i['current_ordinal'],versions=versions))
 def one(items,key,value):
  found=next((x for x in items if x[key]==value),None)
  if found is None:raise Denied('OBJECT_NOT_FOUND',404)
  return found
 selected_version=selected_improvement=selected_site=None
 if version_id:
  selected_improvement=next((i for i in improvements if any(v['id']==version_id for v in i['versions'])),None)
  if selected_improvement is None:raise Denied('OBJECT_NOT_FOUND',404)
  if improvement_id and improvement_id!=selected_improvement['id']:raise Denied('OBJECT_NOT_FOUND',404)
  selected_version=one(selected_improvement['versions'],'id',version_id)
 elif improvement_id:selected_improvement=one(improvements,'id',improvement_id)
 if selected_improvement:
  if site_id and site_id!=selected_improvement['site_id']:raise Denied('OBJECT_NOT_FOUND',404)
  site_id=selected_improvement['site_id']
 if site_id:selected_site=one(sites,'id',site_id)
 elif len(sites)==1:selected_site=sites[0]
 elif site_ordinal is not None:raise Denied('OBJECT_NOT_FOUND',404)
 if selected_site and site_ordinal is not None:one(selected_site['versions'],'ordinal',site_ordinal)
 available=[i for i in improvements if selected_site and i['site_id']==selected_site['id']]
 if not selected_improvement and len(available)==1:selected_improvement=available[0]
 if selected_improvement and selected_version is None:selected_version=one(selected_improvement['versions'],'ordinal',selected_improvement['current_ordinal'])
 if selected_version:
  if site_ordinal is not None and site_ordinal!=selected_version['site_ordinal']:raise Denied('CONTEXT_VERSION_MISMATCH',409)
  site_ordinal=selected_version['site_ordinal']
 selected_site_version=None
 if selected_site:selected_site_version=one(selected_site['versions'],'ordinal',site_ordinal if site_ordinal is not None else selected_site['current_ordinal'])
 selection=dict(company_id=cid,site_id=selected_site['id'] if selected_site else None,site_ordinal=selected_site_version['ordinal'] if selected_site_version else None,improvement_id=selected_improvement['id'] if selected_improvement else None,improvement_version_id=selected_version['id'] if selected_version else None,improvement_ordinal=selected_version['ordinal'] if selected_version else None,is_latest_version=selected_version['ordinal']==selected_improvement['current_ordinal'] if selected_version else None)
 return dict(company={k:company[k] for k in ('id','name','current_ordinal')},sites=sites,improvements=improvements,selection=selection)
