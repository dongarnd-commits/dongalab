"""Bounded, labelled business-input suggestions. No inference or Profile write."""
from dataclasses import replace
import re
from app.company.documents import parse_document,DocumentError

FIELDS={'finance':{'연도':'year','재무연도':'year','기준연도':'year','매출액':'revenue','단위':'unit','금액단위':'unit','통화':'currency','기간':'period','기준기간':'period'},'history':{'수행사업명':'name','사업명':'name','수행기간':'period','수행연도':'period','기간':'period','지원기관':'agency','주관기관':'agency','주요수행내용':'role','수행내용':'role','수행역할':'role'}}
def label(value):return re.sub(r'\s+','',value)

def parse_business(name,raw,kind):
    if kind not in FIELDS:raise DocumentError('INVALID_REQUEST')
    parsed=parse_document(name,raw)
    if parsed.format=='pdf' and any('OCR/manual' in x for x in parsed.limitations):
        from app.company.ocr import ocr_pdf
        present={l.page for l in parsed.locations}
        parsed=replace(parsed,locations=parsed.locations+tuple(l for l in ocr_pdf(raw) if l.page not in present))
    parsed=replace(parsed,parser_version='company-business-'+kind+'-labelled-v1')
    entries(parsed,kind)
    return parsed

def entries(parsed,kind):
    mapping=FIELDS[kind];records=[];current={};locations=parsed.locations
    def push():
        nonlocal current
        if current.get('revenue' if kind=='finance' else 'name'):records.append(current)
        current={}
    # XLSX header/value rows: raw cell values only, never cached formula results.
    sheets={}
    for loc in locations:
        m=re.fullmatch(r'XLSX sheet (.+) cell ([A-Z]+)([0-9]+)',loc.descriptor)
        if m:sheets.setdefault(m[1],{}).setdefault(int(m[3]),{})[m[2]]=loc.text
    for rows in sheets.values():
        headers={}
        for _,cells in sorted(rows.items()):
            found={col:mapping[label(v)] for col,v in cells.items() if label(v) in mapping}
            if ('revenue' if kind=='finance' else 'name') in found.values():headers=found;continue
            if headers:
                row={field:cells.get(col,'').strip() for col,field in headers.items() if cells.get(col) and not cells[col].startswith('FORMULA (not evaluated):')}
                if row.get('revenue' if kind=='finance' else 'name'):records.append(row)
    for loc in locations:
        if loc.descriptor.startswith('XLSX sheet '):continue
        for line in loc.text.splitlines():
            # Existing explicit financial context format is retained.
            m=re.fullmatch(r'\s*매출액\s*\(\s*([0-9]{4})\s*,\s*([^,()]+)\s*,\s*([^,()]+)\s*\)[:：]\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*',line)
            if kind=='finance' and m:
                push();records.append(dict(year=m[1],period=m[1],unit=m[2].strip(),currency=m[3].strip(),revenue=m[4]));continue
            m=re.fullmatch(r'\s*([^:：]{1,30})[:：]\s*(.{1,1000})\s*',line)
            if not m or label(m[1]) not in mapping:continue
            key=mapping[label(m[1])]
            if key==('year' if kind=='finance' else 'name') and current:push()
            if key in current and current[key]!=m[2].strip():push()
            current[key]=m[2].strip()
    push();result=[]
    if len(records)>100:raise DocumentError('DOCUMENT_RECORD_LIMIT')
    for row in records:
        if kind=='finance':
            year=str(row.get('year','')).strip()
            if not re.fullmatch(r'(19|20|21)[0-9]{2}|2200',year):continue
            row={'year':int(year),'revenue':row['revenue'],'period':row.get('period',year),'unit':row.get('unit',''),'currency':row.get('currency','')}
        else:row={key:row.get(key,'') for key in ('name','period','agency','role')}
        if row not in result:result.append(row)
    return result
