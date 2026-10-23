"""NTS statement candidates: section + account code + label, never company-specific.
Pure extraction output; callers still require scoped human input/version saving.
"""
from decimal import Decimal,InvalidOperation,localcontext
from io import BytesIO
import re
from pypdf import PdfReader
from app.company.documents import DocumentError,Location,ParsedDocument,parse_document,MAX_TEXT

# Codes are meaningful only within the named NTS statement, never across tables.
ACCOUNTS={
 'current_assets':('balance','001',('유동자산',)),
 'noncurrent_assets':('balance','080',('비유동자산',)),
 'assets':('balance','228',('자산총계',)),
 'current_liabilities':('balance','229',('유동부채',)),
 'noncurrent_liabilities':('balance','284',('비유동부채',)),
 'liabilities':('balance','333',('부채총계',)),
 'capital':('balance','334',('자본금',)),
 'equity':('balance','382',('자본총계',)),
 'revenue':('income','001',('매출액',)),
 'operating_income':('income','129',('영업손익','영업이익','영업손실')),
 'net_income':('income','219',('당기순손익','당기순이익','당기순손실'))}

def compact(s):return re.sub(r'\s+','',s)
def flexible(s):return r'\s*'.join(re.escape(c) for c in s)

def layout_pdf(name,raw):
 parsed=parse_document(name,raw)
 if parsed.format!='pdf':raise DocumentError('BUSINESS_PDF_REQUIRED')
 reader=PdfReader(BytesIO(raw),strict=True);locations=[]
 for number,page in enumerate(reader.pages,1):
  text=page.extract_text(extraction_mode='layout') or ''
  if text.strip():locations.append(Location('PDF page '+str(number)+' / layout text',text,number))
 if sum(len(l.text) for l in locations)>MAX_TEXT:raise DocumentError('DOCUMENT_TEXT_LIMIT')
 return ParsedDocument(parsed.digest,'pdf',tuple(locations),parsed.limitations,'nts-business-layout-v1')

def won(value,unit):
 text=value.strip();negative=text.startswith(('△','▲','-','−')) or text.startswith('(')
 clean=re.sub(r'[(),\s△▲−-]','',text)
 if not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?',clean):return None
 try:
  with localcontext() as ctx:
   ctx.prec=max(100,len(clean)+10)
   amount=Decimal(clean)*({'원':1,'천원':1000,'백만원':1000000}[unit])*(-1 if negative else 1)
 except (InvalidOperation,KeyError):return None
 return str(int(amount)) if amount==amount.to_integral_value() else None

def statement_entries(parsed):
 if '표준재무제표증명' not in compact(' '.join(l.text for l in parsed.locations)):raise DocumentError('STANDARD_FINANCIAL_CERTIFICATE_REQUIRED')
 rows={}
 for loc in parsed.locations:
  normalized=compact(loc.text);header=compact(' '.join(loc.text.splitlines()[:15]))
  section='balance' if '표준재무상태표' in header else 'income' if '표준손익계산서' in header else None
  if not section:continue
  date_pattern=r'((?:19|20|21)[0-9]{2}|2200)년\s*([0-9]{1,2})월\s*([0-9]{1,2})일'
  dated=list(re.finditer(date_pattern+(r'\s*현재' if section=='balance' else r'\s*(부터|까지)'),loc.text))
  ends=[m for m in dated if section=='balance' or m[4]=='까지']
  if not ends:continue
  from datetime import date
  try:closing=date(*map(int,ends[0].groups()[:3]))
  except ValueError:continue
  dates=[m.groups()[:3] for m in dated];year=closing.year;end=closing.isoformat()
  row=rows.setdefault(year,dict(year=year,period=end+' 기준',unit='원',currency='KRW',values={k:None for k in ACCOUNTS},sources={},issues=[]))
  year_source=dict(page=loc.page,descriptor=loc.descriptor,statement=section,label='결산 기준일',text=ends[0][0])
  if year_source not in row['sources'].setdefault('year',[]):row['sources']['year'].append(year_source)
  if section=='income':
   starts=[m for m in dated if m[4]=='부터']
   if starts:
    try:opening=date(*map(int,starts[0].groups()[:3]))
    except ValueError:opening=None
    if opening and opening<=closing:row['period']=opening.isoformat()+' ~ '+end
  unit_match=re.search(r'단위[:：](백만원|천원|원)',normalized)
  if not unit_match:row['issues'].append('금액 단위 확인 필요');continue
  unit=unit_match[1]
  for field,(kind,code,labels) in ACCOUNTS.items():
   if kind!=section:continue
   for line in loc.text.splitlines():
    for label in labels:
     pattern=flexible(label)+r'(?:\s*\([^)]*\))?\s*'+code+r'\s+([△▲−-]?\s*[0-9][0-9,]*(?:\.[0-9]+)?|\([0-9][0-9,]*\))'
     for m in re.finditer(pattern,line):
      amount=won(m[1],unit)
      if amount is None:continue
      if label.endswith('손실') and not amount.startswith('-'):amount='-'+amount
      source=dict(page=loc.page,descriptor=loc.descriptor,statement=section,code=code,label=label,text=line.strip(),raw_amount=m[1],source_unit=unit,won=amount)
      if row['values'][field] is not None and row['values'][field]!=amount:
       row['issues'].append(field+' 값 충돌: 원문 확인 필요');row['values'][field]=None
      elif not any(i.startswith(field+' 값 충돌') for i in row['issues']):row['values'][field]=amount
      if source not in row['sources'].setdefault(field,[]):row['sources'][field].append(source)
 return [dict(row,checks=financial_checks(row['values'])) for _,row in sorted(rows.items()) if any(v is not None for v in row['values'].values())]

def percent(numerator,denominator):
 with localcontext() as ctx:
  ctx.prec=100
  return str((Decimal(numerator)/Decimal(denominator)*100).quantize(Decimal('0.01')))

def financial_checks(v):
 def compare(total,a,b):return None if any(v.get(k) is None for k in (total,a,b)) else int(v[total])==int(v[a])+int(v[b])
 def ratio(a,b):
  if v.get(a) is None or v.get(b) is None or Decimal(v[b])==0:return None
  return percent(v[a],v[b])
 return dict(balance=compare('assets','liabilities','equity'),assets=compare('assets','current_assets','noncurrent_assets'),liabilities=compare('liabilities','current_liabilities','noncurrent_liabilities'),debt_ratio=ratio('liabilities','equity'),current_ratio=ratio('current_assets','current_liabilities'),capital_erosion=None if v.get('equity') is None or v.get('capital') is None else int(v['equity'])<int(v['capital']),complete_capital_erosion=None if v.get('equity') is None else int(v['equity'])<=0)

def revenue_growth(rows):
 by_year={}
 for r in rows:by_year.setdefault(r['year'],[]).append(r)
 result={}
 for year,current in by_year.items():
  previous=by_year.get(year-1,[])
  a=current[0]['values'].get('revenue') if len(current)==1 else None;b=previous[0]['values'].get('revenue') if len(previous)==1 else None
  result[year]=None if a is None or b is None or Decimal(b)==0 else percent(int(a)-int(b),b)
 return result


def history_candidates(parsed):
 """Keep programme, task, performance dates and institutions as distinct candidates."""
 locations=[l for l in parsed.locations if (l.page or 1)<=5];names=[];periods=[];agencies=[];programs=[];tasks=[];sources=[];participants=[]
 for loc in locations:
  lines=loc.text.splitlines()
  for index,line in enumerate(lines):
   text=' '.join(line.split())
   m=re.fullmatch(r'(20[0-9]{2}년 .{2,180}?사업)',text)
   if m and index<8:
    name=m[1]
    if index+1<len(lines) and re.search(r'결과보고서|사업계획서',lines[index+1]):
     subtitle=re.sub(r'(?:사업\s*)?(?:결과보고서|사업계획서)\s*$','',' '.join(lines[index+1].split())).strip()
     if subtitle:name+=' / '+subtitle
    names.append(name);sources.append(dict(field='name',page=loc.page,text='\n'.join(lines[index:index+2])))
   m=re.search(flexible('수행사업명')+r'[:：]\s*(.+)',line) or re.search(flexible('사업명')+r'[:：]\s*(.+)',line)
   if m:names.append(m[1].strip());sources.append(dict(field='name',page=loc.page,text=line))
   if re.search(flexible('사업기간')+'|'+flexible('수행기간'),line):
    window=' '.join(lines[index:index+2]);dates=re.findall(r'(20[0-9]{2})[.년/-]\s*([0-9]{1,2})[.월/-]\s*([0-9]{1,2})[.일]?',window)
    if len(dates)>=2:
     from datetime import date
     try:a,b=[date(*map(int,d)) for d in dates[:2]]
     except ValueError:continue
     if a<=b:periods.append(a.isoformat()+' ~ '+b.isoformat());sources.append(dict(field='period',page=loc.page,text=window))
   if re.search(flexible('지원프로그램'),line):
    programs.append(text);m=re.search(r'\[([^]]{2,120})\]',line)
    if m:agencies.append(compact(m[1]));sources.append(dict(field='agency',page=loc.page,text=line))
   m=re.search(r'(?:'+flexible('지원기관')+'|'+flexible('전담기관')+r')\s*[:：]\s*(.{2,150})',line)
   if m:agencies.append(m[1].strip());sources.append(dict(field='agency',page=loc.page,text=line))
   if re.search(flexible('과제명'),line):tasks.append(text)
   m=re.match(r'\s*'+flexible('도입기업')+r'\s+(.+?)\s{2,}'+flexible('공급기업')+r'\s+(.+?)\s*$',line)
   if m:participants.extend([dict(role='도입기업',name=' '.join(m[1].split()),page=loc.page),dict(role='공급기업',name=' '.join(m[2].split()),page=loc.page)])
 unique=lambda x:list(dict.fromkeys(x));names,periods,agencies=map(unique,(names,periods,agencies));full=compact(' '.join(l.text for l in locations))
 return dict(name=names[0] if len(names)==1 else '',period=periods[0] if len(periods)==1 else '',agency=agencies[0] if len(agencies)==1 else '',name_candidates=names,period_candidates=periods,agency_candidates=agencies,program_candidates=unique(programs),task_candidates=unique(tasks),participants=participants,sources=sources,document_kind='결과보고서' if '결과보고서' in full else '사업계획서' if '사업계획서' in full else '확인 필요',completion_confirmed=False)


def analyze_financial_pdf(name,raw):
 """Use embedded text first; bounded OCR only for missing statement pages/fields."""
 parsed=layout_pdf(name,raw)
 try:rows=statement_entries(parsed)
 except DocumentError:
  if parsed.locations:raise
  rows=[]
 if rows and all(all(v is not None for v in row['values'].values()) for row in rows):return parsed,rows
 reader=PdfReader(BytesIO(raw),strict=True);present={l.page for l in parsed.locations}
 selected=[n for n in range(1,len(reader.pages)+1) if n not in present]
 if rows:
  selected+= [l.page for l in parsed.locations if '표준재무상태표' in compact(l.text[:500]) or '표준손익계산서' in compact(l.text[:500])]
 selected=sorted(set(selected))
 if not selected:return parsed,rows
 if len(selected)>10:raise DocumentError('OCR_PAGE_LIMIT')
 from pypdf import PdfWriter
 from app.company.ocr import ocr_pdf
 from dataclasses import replace
 writer=PdfWriter()
 for n in selected:writer.add_page(reader.pages[n-1])
 out=BytesIO();writer.write(out);ocr=ocr_pdf(out.getvalue());locations=list(parsed.locations)
 for loc in ocr:
  number=selected[(loc.page or 1)-1];descriptor=re.sub(r'^PDF page [0-9]+','PDF page '+str(number),loc.descriptor)
  locations.append(Location(descriptor,loc.text,number))
 parsed=replace(parsed,locations=tuple(locations),parser_version='nts-business-layout-ocr-v1')
 return parsed,statement_entries(parsed)
