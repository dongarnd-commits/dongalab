from dataclasses import dataclass
from hashlib import sha256
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
import re
from pypdf import PdfReader
from app.notice.domain import Span, CandidateOutput, Denied

class LocalPrivateFiles:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def path(self, key):
        if not re.fullmatch(r"[a-f0-9]{64}", key):
            raise Denied("FILE_SCOPE_MISMATCH")
        return self.root / key

    def put(self, content):
        digest = sha256(content).hexdigest()
        self.root.mkdir(parents=True,exist_ok=True)
        path = self.path(digest)
        if not path.exists():
            with path.open("xb") as stream:
                stream.write(content)
        if sha256(path.read_bytes()).hexdigest()!=digest:
            raise Denied("REQUIRED_EVIDENCE_MISSING")
        return digest,digest

    def read(self,key,digest):
        try:
            data=self.path(key).read_bytes()
        except OSError:
            raise Denied("REQUIRED_EVIDENCE_MISSING") from None
        if sha256(data).hexdigest()!=digest:
            raise Denied("REQUIRED_EVIDENCE_MISSING")
        return data

    def verify_location(self,source,location):
        spans=extract(source,self.read(source["storage_key"],source["digest"]))
        if not evidence_exists(spans, Span(source["id"],location["descriptor"],location["text"],location["page"])):
            raise Denied("REQUIRED_EVIDENCE_MISSING")

class HTMLSections(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts=[]
        self.hidden=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style"):
            self.hidden+=1
        if tag in ("p","h1","h2","li","section","div"):
            self.parts.append("\n")
    def handle_endtag(self,tag):
        if tag in ("script","style"):
            self.hidden=max(0,self.hidden-1)
        if tag in ("p","h1","h2","li","section","div"):
            self.parts.append("\n")
    def handle_data(self,data):
        if not self.hidden:
            self.parts.append(data)

@dataclass(frozen=True)
class ExtractionResult:
    spans: list[Span]
    total_pages: int | None = None
    extracted_pages: tuple[int, ...] = ()
    unextractable_pages: tuple[int, ...] = ()
    limitation: str | None = None


def extract(source,content):
    return extract_document(source,content).spans


def extract_document(source,content):
    if source["media_type"]=="text/html":
        parser=HTMLSections()
        parser.feed(content.decode("utf-8",errors="strict"))
        return ExtractionResult([Span(source["id"],f"HTML text block {index}",line)
                for index,raw in enumerate("".join(parser.parts).splitlines(),1)
                if (line:=raw.strip())])
    if source["media_type"]=="application/pdf":
        reader=PdfReader(BytesIO(content),strict=True)
        if reader.is_encrypted:
            raise Denied("SOURCE_NEEDS_MANUAL_REVIEW")
        spans=[]; extracted_pages=[]; unextractable_pages=[]
        for page_no,page in enumerate(reader.pages,1):
            try:
                text=page.extract_text() or ""
            except Exception:
                text=""
            if text.strip():
                extracted_pages.append(page_no)
            else:
                unextractable_pages.append(page_no)
            for line_no,line in enumerate(text.splitlines(),1):
                if (line:=line.strip()):
                    spans.append(Span(source["id"],f"PDF page {page_no}, line {line_no}",line,page_no))
        return ExtractionResult(spans,len(reader.pages),tuple(extracted_pages),tuple(unextractable_pages),
            "Pages without extractable text require manual review; OCR is not available." if unextractable_pages else None)
    raise Denied("SOURCE_UNSUPPORTED")

class DeterministicAnalysis:
    # English labelled clauses and bounded Korean heading/body analysis.
    version="labelled-clauses-ko-v3"
    prefixes={
        "Eligibility:":"ELIGIBILITY_REQUIREMENT",
        "Support scope:":"SUPPORT_SCOPE",
        "Application period:":"APPLICATION_PERIOD",
        "Required document:":"REQUIRED_DOCUMENT",
        "Evaluation:":"EVALUATION_CRITERION",
    }
    def analyze(self,spans):
        outputs=[]
        for span in spans:
            for prefix,kind in self.prefixes.items():
                if span.text.startswith(prefix):
                    outputs.append(CandidateOutput(kind,span.text[len(prefix):].strip(),
                        f"Direct source clause labelled {prefix}; human verification required.",span))
        from app.infrastructure.notice_korean import analyze_korean
        return outputs + analyze_korean(spans)

    def diagnostics(self, spans, outputs):
        from app.infrastructure.notice_korean import diagnostics
        return diagnostics(spans, outputs)


def evidence_range(spans):
    """Keep exact extracted lines; never normalize the saved evidence."""
    if len(spans)==1:
        return spans[0]
    return Span(spans[0].source_id, spans[0].descriptor+" through "+spans[-1].descriptor,
        "\n".join(s.text for s in spans), spans[0].page)


def evidence_exists(spans, proposed):
    if proposed in spans:
        return True
    for start, span in enumerate(spans):
        if proposed.descriptor.startswith(span.descriptor+" through "):
            for end in range(start+1, min(len(spans),start+160)):
                last=spans[end]
                if last.source_id!=span.source_id or last.page!=span.page:
                    break
                if evidence_range(spans[start:end+1])==proposed:
                    return True
    return False
