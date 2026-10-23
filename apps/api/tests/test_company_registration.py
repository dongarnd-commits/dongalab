"""Initial registration local checks and real synthetic Korean image OCR."""
from io import BytesIO
import pytest
from app.company.business_number import normalize_business_number,validate_business_number
from app.company.registration import preview,registration_candidates
from app.company.documents import parse_document
from registration_sources import scan,number

@pytest.mark.parametrize('prefix',['123456789','012345678','901234567'])
def test_canonical_format_check_digit_and_leading_zero(prefix):
    n=number(prefix);assert validate_business_number(n)==n
    assert validate_business_number(n[:3]+'-'+n[3:5]+'-'+n[5:])==n
    with pytest.raises(ValueError):validate_business_number(n[:-1]+str((int(n[-1])+1)%10))
    for invalid in ['0'*10,'123x567890','123-456-7890']:
        with pytest.raises(ValueError):validate_business_number(invalid)

def test_real_synthetic_korean_scan_ocr_and_source_locations():
    raw=scan();assert not parse_document('scan.pdf',raw).locations
    result=preview('scan.pdf',raw);assert result['error'] is None
    assert 'ocr' in result['parser_version']
    assert any(c['field']=='company_name' and c['value']=='합성검증기업' for c in result['candidates'])
    assert any(c['field']=='business_number' and c['value']==number('123456789') for c in result['candidates'])
    assert {c['source_label'] for c in result['candidates'] if c['field']=='industry'}=={'업태','종목'}
    assert all(c['page']==1 and c['value'] in c['text'] for c in result['candidates'])

def test_ocr_unavailable_retains_manual_registration_fallback(monkeypatch):
    from app.company import ocr
    from app.company.documents import DocumentError
    def unavailable(raw):raise DocumentError('OCR_UNAVAILABLE')
    monkeypatch.setattr(ocr,'ocr_pdf',unavailable)
    result=preview('scan.pdf',scan());assert result['error']=='OCR_UNAVAILABLE';assert result['candidates']==[]


def test_local_engine_limit_errors_remain_distinct_from_unavailable(monkeypatch):
    from types import SimpleNamespace
    from app.company import ocr
    from app.company.documents import DocumentError
    monkeypatch.setattr(ocr.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=0,stdout=b'{"error":"OCR_TIMEOUT"}'))
    with pytest.raises(DocumentError,match='^OCR_TIMEOUT$'):ocr.ocr_pdf(b'%PDF-test')


def test_industry_categories_preserve_multiple_values_and_same_row_labels():
    from dataclasses import replace
    from app.company.documents import Location
    parsed=parse_document('blank.pdf',scan())
    text='사업의 종류 : [업태] 제조업, 서비스업 [종목] 장비 제조, 유지보수\n업 태 : 도소매\n종 목 : 장비 판매'
    parsed=replace(parsed,locations=(Location(descriptor='PDF page 1',text=text,page=1),))
    found=registration_candidates(parsed)
    assert [(c['source_label'],c['value']) for c in found]==[('업태','제조업, 서비스업'),('종목','장비 제조, 유지보수'),('업태','도소매'),('종목','장비 판매')]
    assert all(c['text']==text and c['page']==1 and c['value'] in text for c in found)


def test_category_supplement_keeps_primary_sources_and_does_not_infer_core_fields(monkeypatch):
    from app.company import ocr
    from app.company.documents import Location
    raw=scan();calls=[]
    def recognize(raw,**options):
        calls.append(options)
        return (Location(descriptor='PDF page 1 / category table' if options.get('table') else 'PDF page 1 / OCR',page=1,text='상호 : 표의 잘못된 상호\n사업의 종류 : [업태] 제조업 [종목] 장비 제조' if options.get('table') else '상호 : 원문기업'),)
    monkeypatch.setattr(ocr,'ocr_pdf',recognize)
    result=preview('scan.pdf',raw)
    assert calls[1]['table'] is True
    assert [c['value'] for c in result['candidates'] if c['field']=='company_name']==['원문기업']
    assert {c['source_label'] for c in result['candidates'] if c['field']=='industry'}=={'업태','종목'}
    assert len(result['locations'])==2
