from app.company.business_documents import entries,parse_business
from app.company.documents import ParsedDocument,Location

def parsed(*lines):return ParsedDocument('a'*64,'txt',tuple(Location('TEXT line '+str(i),line) for i,line in enumerate(lines,1)),())
def test_explicit_financial_context_and_unknown_fields_are_not_invented():
    assert entries(parsed('매출액(2025, 원, KRW): 1,234'),'finance')==[dict(year=2025,revenue='1,234',unit='원',currency='KRW',period='2025')]
    assert entries(parsed('매출액: 0'),'finance')==[]
    assert entries(parsed('연도: 2024','매출액: 0'),'finance')==[dict(year=2024,revenue='0',unit='',currency='',period='2024')]

def test_multiple_histories_keep_actual_labels_without_unsupported_amount():
    rows=entries(parsed('수행사업명: TEST A','수행기간: 2023','지원기관: TEST 기관','지원금액: 100','수행사업명: TEST B','수행기간: 2024','주요 수행내용: TEST 직접 수행'),'history')
    assert rows==[dict(name='TEST A',period='2023',agency='TEST 기관',role=''),dict(name='TEST B',period='2024',agency='',role='TEST 직접 수행')]

def test_xlsx_header_columns_formula_and_year_bounds():
    p=ParsedDocument('a'*64,'xlsx',tuple(Location('XLSX sheet TEST cell '+cell,value) for cell,value in [('A1','연도'),('B1','매출액'),('C1','단위'),('D1','통화'),('A2','2024'),('B2','123'),('C2','원'),('D2','KRW'),('A3','2025'),('B3','FORMULA (not evaluated): SUM(B2)'),('A4','9999'),('B4','400')]),())
    assert entries(p,'finance')==[dict(year=2024,revenue='123',unit='원',currency='KRW',period='2024')]

def test_plain_parser_keeps_source_and_separates_analysis_from_profile():
    raw='연도: 2025\n매출액: 900\n단위: 원\n통화: KRW'.encode()
    p=parse_business('TEST.txt',raw,'finance');assert p.locations[0].text=='연도: 2025';assert p.parser_version=='company-business-finance-labelled-v1'
    assert entries(p,'finance')[0]['revenue']=='900'


def test_actual_financial_korean_scan_uses_existing_local_ocr():
    from business_sources import financial_scan
    p=parse_business('TEST-finance-scan.pdf',financial_scan(),'finance');r=entries(p,'finance')
    assert r and r[0]['year']==2023 and r[0]['revenue']=='12340000'
    assert any(l.page==1 and 'OCR' in l.descriptor for l in p.locations)
