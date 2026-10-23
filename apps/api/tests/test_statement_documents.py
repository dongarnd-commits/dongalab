from dataclasses import replace
from io import BytesIO
from pathlib import Path
import pytest
from app.company.documents import ParsedDocument,Location,DocumentError
from app.company.statement_documents import layout_pdf,statement_entries,financial_checks,revenue_growth,history_candidates

def parsed(*pages):return ParsedDocument('a'*64,'pdf',tuple(Location('PDF page '+str(i),t,i) for i,t in enumerate(pages,1)),())

def pages(unit='원'):
 return ['표준재무제표증명',
 '표준재무상태표\n2024년12월31일 현재\n(단위: '+unit+')\n유동자산 001 1,500\n비유동자산 080 2,500\n자산총계(Ⅰ+Ⅱ) 228 4,000\n유동부채 229 300\n비유동부채 284 700\n부채총계(Ⅰ+Ⅱ) 333 1,000\n자본금 334 100',
 '표준재무상태표\n2024년12월31일 현재\n(단위: '+unit+')\n자본총계(Ⅲ+～Ⅶ) 382 3,000',
 '2024년01월01일 부터\n표준손익계산서\n2024년12월31일 까지\n(단위: '+unit+')\n매출액 001 9,000\n영업손익 129 600\n당기순손익 219 -200',
 '제조원가명세서\n2024년12월31일 까지\n(단위: 원)\n매출액 001 999,999']

def test_section_code_label_and_continued_pages_are_independent():
 row=statement_entries(parsed(*pages()))[0]
 assert row['year']==2024 and row['period']=='2024-01-01 ~ 2024-12-31'
 assert row['values']==dict(current_assets='1500',noncurrent_assets='2500',assets='4000',current_liabilities='300',noncurrent_liabilities='700',liabilities='1000',capital='100',equity='3000',revenue='9000',operating_income='600',net_income='-200')
 assert row['sources']['equity'][0]['page']==3 and row['sources']['revenue'][0]['statement']=='income'
 assert row['checks']['balance'] and row['checks']['assets'] and row['checks']['liabilities']
 assert row['checks']['debt_ratio']=='33.33' and row['checks']['current_ratio']=='500.00'

def test_units_precision_missing_and_conflicts_do_not_get_corrected():
 row=statement_entries(parsed(*pages('천원')))[0];assert row['values']['revenue']=='9000000'
 p=pages();p[1]=p[1].replace('4,000','9,007,199,254,740,993');row=statement_entries(parsed(*p))[0];assert row['values']['assets']=='9007199254740993' and row['checks']['balance'] is False
 p=pages();p[2]+='\n자산총계 228 4,001';row=statement_entries(parsed(*p))[0];assert row['values']['assets'] is None and row['issues']
 p=pages();p[3]=p[3].replace('매출액 001 9,000','매출액 228 9,000');row=statement_entries(parsed(*p))[0];assert row['values']['revenue'] is None
 v={key:None for key in row['values']};v.update(liabilities='100',equity='0',current_assets='10',current_liabilities='0');checks=financial_checks(v);assert checks['debt_ratio'] is None and checks['current_ratio'] is None and checks['complete_capital_erosion'] is True
 assert revenue_growth([dict(year=2024,values={'revenue':'100'}),dict(year=2025,values={'revenue':'125'})])[2025]=='25.00'
 assert revenue_growth([dict(year=2024,values={'revenue':'0'}),dict(year=2025,values={'revenue':'125'})])[2025] is None

def test_history_business_year_is_not_performance_year_and_agencies_require_review():
 p=parsed('2025년 TEST 지역산업사업\nAI 보급지원 사업 결과보고서\n지원프로그램 [TEST 기술기관] AI 도입', '사업기간 2026. 06. 01 ~ 2026. 08. 31\n도입기업  TEST 수요기업  공급기업  TEST 공급기업')
 r=history_candidates(p);assert r['name'].startswith('2025년') and r['period']=='2026-06-01 ~ 2026-08-31';assert r['agency']=='TEST기술기관' and r['completion_confirmed'] is False
 assert {p['role'] for p in r['participants']}=={'도입기업','공급기업'}
 r=history_candidates(replace(p,locations=p.locations+(Location('PDF page 3','지원기관: OTHER 기관',3),)));assert r['agency']=='' and len(r['agency_candidates'])==2
 r=history_candidates(parsed('2025년 TEST 지역산업사업\nAI 보급지원 사업 사업계획서'));assert r['document_kind']=='사업계획서' and r['completion_confirmed'] is False and r['period']==''

def test_real_synthetic_pdf_layout_and_issuance_date():
 from reportlab.pdfgen.canvas import Canvas
 from reportlab.pdfbase import pdfmetrics
 from reportlab.pdfbase.ttfonts import TTFont
 font=next(p for p in [Path('C:/Windows/Fonts/malgun.ttf'),Path('/usr/share/fonts/truetype/nanum/NanumGothic.ttf')] if p.exists());pdfmetrics.registerFont(TTFont('TEST_NTS',str(font)));out=BytesIO();c=Canvas(out)
 for text in pages():
  c.setFont('TEST_NTS',10)
  for i,line in enumerate(text.splitlines()):c.drawString(25,800-i*22,line)
  c.drawString(25,80,'발급일 2026년10월22일');c.showPage()
 c.save();p=layout_pdf('TEST-statements.pdf',out.getvalue());r=statement_entries(p)[0];assert r['year']==2024 and r['values']['assets']=='4000' and r['values']['revenue']=='9000'
 with pytest.raises(DocumentError):layout_pdf('bad.pdf',b'%PDF-broken')
 with pytest.raises(DocumentError):statement_entries(parsed('기업 안내문'))


def test_percent_exact_large_integer_and_half_even_rounding():
 from app.company.statement_documents import percent
 assert percent('1','32')=='3.12'
 assert percent('3','32')=='9.38'
 assert percent('-3','32')=='-9.38'
 assert percent('999999999999999999999999999999','1')=='99999999999999999999999999999900.00'


def test_won_conversion_preserves_all_integer_digits():
 from app.company.statement_documents import won
 assert won('999999999999999999999999999999','천원')=='999999999999999999999999999999000'
 assert won('(9007199254740993)','원')=='-9007199254740993'
