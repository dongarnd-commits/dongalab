import re
from datetime import date
from app.collector.domain import NormalizedNotice
from app.notice.domain import Denied

VERSION="bizinfo-fields-v1"
FIELDS={"pblancNm":"title","jrsdInsttNm":"agency","excInsttNm":"executing_agency",
    "reqstBeginEndDe":"period_original","trgetNm":"target","bsnsSumryCn":"summary",
    "reqstMthPapersCn":"application_method","refrncNm":"contact_reference",
    "pldirSportRealmLclasCodeNm":"major_category","pldirSportRealmMlsfcCodeNm":"minor_category",
    "hashtags":"tags_original","rceptEngnHmpgUrl":"application_reference_url",
    "pblancUrl":"detail_url","flpthNm":"attachment_url","fileNm":"attachment_name",
    "printFlpthNm":"print_url","printFileNm":"print_name"}

def parse_page(payload):
    if not isinstance(payload,dict) or not isinstance(payload.get("jsonArray"),list):
        raise Denied("INVALID_BIZINFO_WRAPPER")
    return payload["jsonArray"]

def normalize(item):
    if not isinstance(item,dict): raise Denied("INVALID_BIZINFO_ITEM")
    external=item.get("pblancId")
    if not isinstance(external,str) or not re.fullmatch(r"PBLN_[A-Za-z0-9_]{1,100}",external):
        raise Denied("EXTERNAL_ID_MISSING_OR_INVALID")
    core={}; warnings=[]
    for field,target in FIELDS.items():
        if field not in item or item[field] is None: continue
        if not isinstance(item[field],str):
            warnings.append("FIELD_TYPE_INVALID:"+field); continue
        core[target]=item[field].strip()
    period=core.get("period_original","")
    match=re.fullmatch(r"(\d{4})[-.](\d{2})[-.](\d{2})\s*~\s*(\d{4})[-.](\d{2})[-.](\d{2})",period)
    dates=None
    if match:
        try:
            values=list(map(int,match.groups())); begin=date(*values[:3]); end=date(*values[3:])
            if begin>end: raise ValueError()
            dates=[begin.isoformat(),end.isoformat()]
        except ValueError: pass
    if not dates: warnings.append("PERIOD_REQUIRES_HUMAN_REVIEW")
    if not core.get("title"): warnings.append("TITLE_MISSING")
    references=[]
    for field,name,media in [("pblancUrl","Detail HTML","text/html"),("flpthNm","Attachment","application/octet-stream"),("printFlpthNm","Print reference","application/octet-stream")]:
        value=item.get(field)
        if isinstance(value,str):
            references.append({"field":field,"url":value.strip(),"name":name,"media_type":media})
    metadata={"source_system":"BIZINFO","external_id":external,"normalizer_version":VERSION,
        "period_parse_status":"CANDIDATE" if dates else "UNCONFIRMED","period_candidates":dates,
        "source_created_original":item.get("creatPnttm") if isinstance(item.get("creatPnttm"),str) else None,
        "source_updated_original":item.get("updtPnttm") if isinstance(item.get("updtPnttm"),str) else None,
        "missing_fields":[f for f in FIELDS if f not in item or item[f] is None or not isinstance(item[f],str)]}
    return NormalizedNotice(external,core.get("title"),core,metadata,references,warnings)
