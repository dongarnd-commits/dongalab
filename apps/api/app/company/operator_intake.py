"""Operator receipt projection from immutable SUBMIT records; no new state or writes."""
from app.infrastructure import company_schema as S
from app.notice.domain import Denied
from sqlalchemy import select
from app.infrastructure import company_business_schema as B


def request_items(a, who, companies):
 """Read-only bounded-scope projection; never one browser request per company."""
 a.role(who, 'DATCO_OPERATOR')
 allowed={c['id']:c['name'] for c in companies}
 if not allowed:return []
 rows=[dict(r) for r in a.session.execute(select(B.requests, S.improvement_versions.c.ordinal.label('version_ordinal'),
    S.improvement_versions.c.data.label('version_data')).outerjoin(S.improvement_versions,
    B.requests.c.improvement_version_id==S.improvement_versions.c.id).where(B.requests.c.company_id.in_(allowed))).mappings()]
 ids=[r['id'] for r in rows];latest={}
 if ids:
  for r in a.session.execute(select(B.responses).where(B.responses.c.request_id.in_(ids))).mappings():
   if r['request_id'] not in latest or r['ordinal']>latest[r['request_id']]['ordinal']:latest[r['request_id']]=r
 return [dict(id=r['id'],company_id=r['company_id'],company_name=allowed[r['company_id']],title=r['title'],
    improvement_version_id=r['improvement_version_id'],version_ordinal=r['version_ordinal'],
    improvement_title=(r['version_data'] or {}).get('title'),state=r['state'],due_date=r['due_date'],created_at=r['created_at'],
    response_id=latest[r['id']]['id'] if r['id'] in latest and latest[r['id']]['submitted'] else None,
    response_ordinal=r['response_ordinal']) for r in rows]


def receipts(a, who, cid):
 a.role(who, 'DATCO_OPERATOR'); a.scope(who, cid)
 result=[]
 for root in a.rows(S.improvements, company_id=cid):
  for version in a.rows(S.improvement_versions, improvement_id=root['id']):
   submitted=a.rows(S.improvement_reviews, version_id=version['id'], outcome='SUBMIT')
   if submitted:
    from app.company.submission_review import SubmissionReview
    result.append(dict(root_id=root['id'], version_id=version['id'], ordinal=version['ordinal'], site_id=root['site_id'], site_ordinal=version['site_ordinal'], title=version['data']['title'], submitted_at=submitted[0]['created_at'], current_state=root['state'],work=SubmissionReview(a).projection(who,version['id'])))
 return sorted(result, key=lambda r:(r['submitted_at'],r['version_id']), reverse=True)


def overview(a, who):
 a.role(who, 'DATCO_OPERATOR')
 companies=a.listing(who,''); items=[]
 for company in companies:
  rows=receipts(a,who,company['id'])
  items.append(dict(company=company,receipts=rows))
 requests=request_items(a,who,companies)
 latest=[next(r for r in i['receipts'] if r['root_id']==root) for i in items for root in {r['root_id'] for r in i['receipts']}]
 counts=dict(review_roots=sum(r['work']['status'] in ('NEW_RECEIPT','NEEDS_REVIEW') for r in latest),
    recheck_roots=sum(r['work']['status'] in ('NEEDS_CHECK','REREVIEW') for r in latest),
    waiting_requests=sum(r['state'] in ('WAITING_RESPONSE','REVISION_REQUESTED') for r in requests),
    review_requests=sum(r['state']=='REVIEW_REQUIRED' for r in requests))
 return dict(companies=items,company_count=len(items),submitted_count=sum(len(i['receipts']) for i in items),submitted_root_count=len(latest),request_items=requests,work_counts=counts)


def detail(a, who, cid, version_id=None):
 rows=receipts(a,who,cid)
 chosen=next((r for r in rows if r['version_id']==version_id),None) if version_id else (rows[0] if rows else None)
 if version_id and chosen is None:raise Denied('OBJECT_NOT_FOUND',404)
 data=a.detail(who,cid)
 # Only saved provenance is a confirmed grouping hint; filenames and an attempted
 # parser purpose alone never classify a document.
 from app.infrastructure import company_business_schema as B
 sources=a.rows(B.sources,company_id=cid);extractions={e['id']:e for e in a.rows(B.extractions,company_id=cid)}
 for file in data['files']:
  groups={source['kind'].upper() for source in sources if source['extraction_id'] in extractions and extractions[source['extraction_id']]['file_id']==file['id']}
  file['material_groups']=sorted(groups) or ['UNCLASSIFIED']
 # Keep current company input explicitly separate from exact submitted improvement/site.
 # No historical company profile snapshot is invented: SUBMIT has no such FK.
 submitted={r['version_id'] for r in rows}
 data['improvements']=[dict(i,versions=[v for v in i['versions'] if v['id'] in submitted]) for i in data['improvements'] if any(v['id'] in submitted for v in i['versions'])]
 for item in data['improvements']:
  latest=max(item['versions'],key=lambda v:v['ordinal']);item['title']=latest['data']['title']
 data['receipts']=rows; data['selection']=chosen
 if chosen:
  site=next(s for s in data['sites'] if s['id']==chosen['site_id'])
  data['submitted_site']=next(v for v in site['versions'] if v['ordinal']==chosen['site_ordinal'])
 else:data['submitted_site']=None
 return data
