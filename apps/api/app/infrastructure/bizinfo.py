from pathlib import Path
from io import BytesIO
import json,re,socket,ipaddress,time
from urllib.parse import urlsplit,parse_qs,urlencode,quote,unquote_to_bytes
from urllib.request import Request,urlopen,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError,URLError
from pypdf import PdfReader
from app.core.config import ROOT,get_settings
from app.notice.domain import Denied

ENDPOINT="https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"
HOSTS={"www.bizinfo.go.kr","bizinfo.go.kr"}
FIXTURES=ROOT/"apps/api/fixtures/bizinfo"

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None

def safe_url(url,external_id=None,field=None):
    try:
        parts=urlsplit(url)
        if parts.scheme!="https" or parts.hostname not in HOSTS or parts.port not in (None,443) or parts.username or parts.password or parts.fragment:
            raise ValueError()
        query=parse_qs(parts.query)
        if any(re.search(r"key|token|password|secret",name,re.I) for name in query): raise ValueError()
        if field=="pblancUrl" and query.get("pblancId")!=[external_id]: raise ValueError()
    except (ValueError,TypeError): raise Denied("SOURCE_URL_REJECTED") from None
    return url

def validate_content(content,media_type,external_id=None):
    if media_type=="application/octet-stream":
        if not content.startswith(b"%PDF-"): raise Denied("SOURCE_FORMAT_UNSUPPORTED")
        media_type="application/pdf"
    if media_type=="application/pdf":
        if not content.startswith(b"%PDF-") or b"%%EOF" not in content[-1024:]: raise Denied("SOURCE_NOT_VALID_PDF")
        try:
            reader=PdfReader(BytesIO(content),strict=True)
            if reader.is_encrypted or not reader.pages: raise ValueError()
        except Exception: raise Denied("SOURCE_NEEDS_MANUAL_REVIEW") from None
    elif media_type=="text/html":
        try: text=content.decode("utf-8",errors="strict")
        except UnicodeError: raise Denied("SOURCE_ENCODING_UNSUPPORTED") from None
        if not re.search(r"<(?:html|body|div|p)\b",text,re.I) or (external_id and external_id not in text):
            raise Denied("DETAIL_ID_OR_FORMAT_MISMATCH")
    else: raise Denied("SOURCE_UNSUPPORTED")
    return content,media_type

class BizinfoLive:
    origin="BIZINFO_LIVE_API"
    def __init__(self,key=None,opener=None,resolver=None,timeout=15,max_bytes=8*1024*1024):
        configured=get_settings().bizinfo_api_key
        self.key=key if key is not None else (configured.get_secret_value() if configured else "")
        self.opener=opener or build_opener(NoRedirect())
        self.resolver=resolver or socket.getaddrinfo
        self.timeout,self.max_bytes=timeout,max_bytes
        self.deadline=time.monotonic()+120
        self.calls=0
    def reject_secrets(self,content):
        if not self.key: return
        variants=(self.key.encode(),quote(self.key,safe="").encode())
        for _ in range(3):
            if any(value in content for value in variants): raise Denied("SECRET_REFLECTION_BLOCKED")
            content=unquote_to_bytes(content)
    def get(self,url,limit=None):
        parts=urlsplit(url)
        if parts.scheme!="https" or parts.hostname not in HOSTS or parts.port not in (None,443): raise Denied("SOURCE_URL_REJECTED")
        try:
            addresses=self.resolver(parts.hostname,443,type=socket.SOCK_STREAM)
            if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses): raise Denied("SOURCE_HOST_REJECTED")
        except (OSError,ValueError): raise Denied("SOURCE_HOST_UNAVAILABLE") from None
        for attempt in range(2):
            if time.monotonic()>=self.deadline: raise Denied("COLLECTION_TIME_LIMIT")
            try:
                self.calls+=1
                request=Request(url,headers={"Accept":"application/json,text/html,application/pdf,*/*","User-Agent":"DATCO-Phase1/0.1"})
                with self.opener.open(request,timeout=min(self.timeout,max(0.1,self.deadline-time.monotonic()))) as response:
                    if response.status!=200: raise Denied("BIZINFO_HTTP_ERROR")
                    chunks=[]; size=0
                    while True:
                        if time.monotonic()>=self.deadline: raise Denied("COLLECTION_TIME_LIMIT")
                        chunk=response.read(65536)
                        if not chunk: break
                        size+=len(chunk)
                        if size>(limit or self.max_bytes): raise Denied("SOURCE_SIZE_LIMIT")
                        chunks.append(chunk)
                    content=b"".join(chunks)
                    self.reject_secrets(content)
                    return content,response.headers.get("Content-Type","")
            except HTTPError as exc:
                if exc.code>=500 and attempt==0: continue
                raise Denied("BIZINFO_HTTP_"+str(exc.code)) from None
            except (URLError,TimeoutError,OSError):
                if attempt==0: continue
                raise Denied("BIZINFO_NETWORK_TIMEOUT") from None
        raise Denied("BIZINFO_REQUEST_FAILED")
    def page(self,page,unit):
        if not self.key: raise Denied("BIZINFO_KEY_NOT_CONFIGURED")
        url=ENDPOINT+"?"+urlencode({"crtfcKey":self.key,"dataType":"json","searchCnt":0,"pageUnit":unit,"pageIndex":page})
        content,_=self.get(url,1024*1024)
        try: payload=json.loads(content)
        except (ValueError,UnicodeError): raise Denied("BIZINFO_INVALID_JSON") from None
        self.reject_secrets(json.dumps(payload,ensure_ascii=True).encode())
        return payload
    def acquire(self,reference,external_id):
        url=safe_url(reference["url"],external_id,reference["field"])
        self.reject_secrets(url.encode())
        content,media=self.get(url)
        expected=reference["media_type"]
        if expected=="text/html" and "text/html" not in media.lower(): raise Denied("SOURCE_UNSUPPORTED")
        return validate_content(content,expected,external_id if expected=="text/html" else None)

class BizinfoSnapshot:
    origin="SANITIZED_SYNTHETIC_DEMO_V1"
    def __init__(self):
        configured=get_settings().bizinfo_api_key
        self.key=configured.get_secret_value() if configured else ""
        content=(FIXTURES/"demo.json").read_bytes()
        self.reject_secrets(content)
        self.data=json.loads(content)
        if self.data.get("sanitized") is not True or self.data.get("synthetic") is not True: raise Denied("SNAPSHOT_NOT_SANITIZED")
    def reject_secrets(self,content):
        BizinfoLive.reject_secrets(self,content)
    def page(self,page,unit):
        start=(page-1)*unit
        return {"jsonArray":self.data["jsonArray"][start:start+unit]}
    def acquire(self,reference,external_id):
        safe_url(reference["url"],external_id,reference["field"])
        name=self.data["assets"].get(reference["url"])
        if not name: raise Denied("SNAPSHOT_SOURCE_MISSING")
        path=(FIXTURES/name).resolve()
        if not path.is_relative_to(FIXTURES.resolve()): raise Denied("SOURCE_URL_REJECTED")
        try: content=path.read_bytes()
        except OSError: raise Denied("SNAPSHOT_SOURCE_MISSING") from None
        return validate_content(content,reference["media_type"],external_id if reference["media_type"]=="text/html" else None)
