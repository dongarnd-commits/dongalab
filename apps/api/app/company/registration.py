"""Stateless initial PDF analysis. No Company or temporary File identity."""
from dataclasses import asdict,replace
import re
from app.company.documents import parse_document,DocumentError

LABELS={'상호(법인명)':'company_name','법인명(상호)':'company_name','상호':'company_name','상호명':'company_name','법인명':'company_name','법인명(단체명)':'company_name','회사명':'company_name','기업명':'company_name','사업자등록번호':'business_number','사업자번호':'business_number','등록번호':'business_number','대표자성명':'representative','대표자(성명)':'representative','대표자':'representative','성명':'representative','사업장소재지':'address','본점소재지':'address','소재지':'address','업태':'industry','종목':'industry','업종':'industry','개업연월일':'opened_on','개업일':'opened_on'}

def registration_candidates(parsed):
    result=[]
    # Labels are source anchored; do not infer fields from names or filenames.
    for loc in parsed.locations:
        lines=[line.strip() for line in loc.text.splitlines() if line.strip()]
        for line in lines:
            field=None;value=None
            for label,target in sorted(LABELS.items(),key=lambda item:-len(item[0])):
                pattern=r'^\s*'+r'\s*'.join(re.escape(c) for c in label)+r'(?:\s*\([^)]{1,20}\))?\s*(?:[:：|]\s*|\s+)(.{1,500})$'
                m=re.match(pattern,line)
                if m:field=target;value=m[1].strip();break
            if not field:continue
            # Keep exact OCR/source value; canonical number is user/server validated.
            result.append(dict(field=field,value=value,page=loc.page,descriptor=loc.descriptor,text=loc.text))
    return result

def parse_registration(name,raw,*,ocr=True):
    if not name.lower().endswith('.pdf'):raise DocumentError('REGISTRATION_PDF_REQUIRED')
    parsed=parse_document(name,raw)
    if len(parsed.locations)>10:raise DocumentError('OCR_PAGE_LIMIT')
    needs_ocr=any('OCR/manual' in note for note in parsed.limitations)
    if needs_ocr and ocr:
        from app.company.ocr import ocr_pdf
        locations=ocr_pdf(raw)
        # Preserve text extraction on existing text pages, OCR only fills absent pages.
        present={l.page for l in parsed.locations}
        parsed=replace(parsed,locations=parsed.locations+tuple(l for l in locations if l.page not in present),limitations=('OCR is a candidate; original PDF and human review required',),parser_version='company-registration-local-ocr-v1')
    return parsed

def preview(name,raw):
    # OCR unavailability must not destroy a usable direct-input fallback.
    try:
        parsed=parse_registration(name,raw)
        return dict(digest=parsed.digest,parser_version=parsed.parser_version,limitations=list(parsed.limitations),locations=[asdict(l) for l in parsed.locations],candidates=registration_candidates(parsed),error=None)
    except DocumentError as e:
        if str(e).startswith('OCR_'):
            parsed=parse_registration(name,raw,ocr=False)
            return dict(digest=parsed.digest,parser_version=parsed.parser_version,limitations=list(parsed.limitations),locations=[asdict(l) for l in parsed.locations],candidates=registration_candidates(parsed),error=str(e))
        raise
