"""Pure version-bound document production; no approval or eligibility inference."""
import json,os,zipfile
from pathlib import Path
from io import BytesIO
from html import escape
from hashlib import sha256
from xml.sax.saxutils import escape as xml_escape
from app.notice.domain import Denied
HEADINGS=('수요기업 개요','기업의 개선 요구 및 현재 문제','개선 목표','DATCO 제안 서비스','맞춤형 서비스 구성','적용 범위 및 전제조건','추천 정부지원사업','자격조건 검토','추진 방향과 수행 내용','예상효과 및 후속 절차','출처 및 생성·검토 정보')

def text(value):return json.dumps(value,ensure_ascii=False,indent=2,default=str)
def legacy_draft(manifest):
 source=manifest['input'];company=source['company'];composition=source['composition'];notice=source['notice'];caps=manifest['capability_versions']
 facts=[f for f in source.get('comparison',{}).get('facts',[]) if f.get('confirmed') is True and f.get('current_valid') is True]
 overview=['기업 식별: '+company['company_id'],'사업장 식별: '+str(company.get('site_id') or '확인 필요')]
 overview += [str(f['attribute'])+': '+str(f['value'])+' (확인 FactVersion '+f['version_id']+' / 유효 시작 '+str(f.get('valid_from') or '확인 필요')+' / 유효 종료 '+str(f.get('valid_until') or '별도 확인')+')' for f in facts]
 if not facts:overview.append('확인된 기업 현황 값은 제공된 원천 근거에서 추가 확인이 필요합니다.')
 services=[];limits=[]
 for cap in caps:
  d=cap['data'];services.extend([d['service'],d.get('description',''),'제공범위: '+d['scope'],'연결 기능: '+', '.join(f['role'] for f in d['functions'])])
  for label,key in [('적용조건','conditions'),('선행요건','prerequisites'),('제외범위','exclusions')]:
   limits += [label+': '+v for v in d.get(key,[])]
 coverage=[]
 for c in composition['coverage']:
  coverage.extend(['기업 요구: '+c['requirement'],'서비스 역할: '+c['role'],'해결범위: '+c['addressed_scope'],'미해결·제외범위: '+(c['unaddressed_scope'] or '추가 확인 필요')])
  limits += ['추가 확인항목: '+v for v in c['missing_information']]
 limits += ['조합 전제조건: '+v for v in composition.get('conditions',[])]+['원천에 기록된 검토사항: '+v for v in composition.get('unresolved',[])]
 programs=['공고명: '+manifest.get('notice_title',notice['notice_id']),'공고 Version: '+notice['notice_version_id']]
 programs += [i['content'] for i in notice['items'] if i['kind']=='SUPPORT_SCOPE']
 eligibility=[i['content'] for i in notice['items'] if i['kind'] in ('ELIGIBILITY_REQUIREMENT','CONDITIONAL_REQUIREMENT','APPLICATION_PERIOD','REQUIRED_DOCUMENT')]
 eligibility += ['항목별 사람 검토: '+manifest['match_review']['outcome'],'검토 식별자: '+manifest['match_review']['id'],'기업·공급자격·서비스·공고 항목의 확인 근거는 시스템 검토 이력에서 추적합니다. 공식 적격·선정 확정을 의미하지 않습니다.']
 work=['담당자 제안 수행안 — 일정·금액·책임의 최종 합의가 필요합니다.']+['서비스별 수행 검토: '+c['addressed_scope'] for c in composition['coverage']]
 work += ['기업 협조사항: 적용 대상 원천자료·현장 조건을 확인하고 변경사항을 공유합니다.','DATCO 수행 책임·일정: 담당자와 기업의 검토·합의 후 확정합니다.']
 bodies=['\n'.join(overview),company['original_text'],'담당자 제안: 다음 기업 요구의 개선을 목표로 합니다. 정량 목표는 확인 필요.\n'+company['original_text'],
 '\n'.join(services),composition['name']+'\n'+'\n'.join(coverage),'\n'.join(limits) or '추가 전제조건의 확인이 필요합니다.','\n'.join(programs),'\n'.join(eligibility),'\n'.join(work),
 '예상효과(미확정): 제안 서비스의 적용을 통한 수기 업무와 확인된 문제의 개선 가능성을 검토합니다. 성과 수치·사업비·기업부담·지원금·선정확률은 확인 필요입니다. 후속 절차는 제안내용 검토와 기업 승인, 별도 신청 준비입니다.',text(manifest['refs'])]
 return [{'heading':h,'body':body,'evidence_refs':manifest['refs']} for h,body in zip(HEADINGS,bodies)]
def legacy_validate(sections):
 if len(sections)!=11:raise Denied('REQUIRED_DATA_MISSING',422)
 for section,heading in zip(sections,HEADINGS):
  if set(section)!={'heading','body','evidence_refs'} or section['heading']!=heading or not isinstance(section['body'],str) or not section['body'].strip() or len(section['body'])>20000:raise Denied('REQUIRED_DATA_MISSING',422)

TEMPLATES=('LEGACY_11','MVP_16')
def template_version(manifest):
 value=manifest.get('template_version','LEGACY_11')
 if value not in TEMPLATES:raise Denied('INVALID_PROPOSAL_TEMPLATE',422)
 return value

def draft(manifest):
 if template_version(manifest)=='MVP_16':
  from app.proposal.mvp_template import draft as build
  return build(manifest)
 return legacy_draft(manifest)

def validate(sections,template='LEGACY_11'):
 if template not in TEMPLATES:raise Denied('INVALID_PROPOSAL_TEMPLATE',422)
 if template=='MVP_16':
  from app.proposal.mvp_template import validate as check
  return check(sections)
 return legacy_validate(sections)

def render(version,kind):
 template=template_version(version['manifest']);validate(version['sections'],template);title=version['title'];info='ProposalVersion '+version['id']+' / '+str(version['ordinal'])+' / '+version['content_digest']
 paragraphs=[title,info]
 for s in version['sections']:paragraphs.extend([s['heading'],s['body']])
 paragraphs+=['생성 근거 식별자',text(version['manifest']['refs'])]
 if any((ord(c)<32 and c not in '\n\r\t') or 0xD800<=ord(c)<=0xDFFF or ord(c) in (0xFFFE,0xFFFF) for p in paragraphs for c in p):raise Denied('PROPOSAL_INVALID_DOCUMENT_TEXT',422)
 if kind=='DOCX':
  b=BytesIO()
  headings={section['heading'] for section in version['sections']}
  def para(value):
   emphasis=template=='MVP_16' and (value==title or value in headings)
   size='<w:b/><w:sz w:val="28"/>' if emphasis else ''
   spacing='<w:pPr><w:spacing w:before="160" w:after="100"/><w:keepNext/></w:pPr>' if emphasis else ''
   return '<w:p>'+spacing+'<w:r><w:rPr><w:rFonts w:ascii="Malgun Gothic" w:eastAsia="맑은 고딕"/>'+size+'</w:rPr><w:t xml:space="preserve">'+xml_escape(value)+'</w:t></w:r></w:p>'
  with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
   def write(name,data):
    # ZIP timestamps must not create another blob after a rolled-back export.
    info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
    z.writestr(info,data)
   write('[Content_Types].xml','<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
   write('_rels/.rels','<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
   body=''.join(para(line) for p in paragraphs for line in p.splitlines())
   # Editable source-reference table as part of the same version's content.
   table='<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/></w:tblPr>'+''.join('<w:tr><w:tc>'+para(k)+'</w:tc><w:tc>'+para(text(v))+'</w:tc></w:tr>' for k,v in version['manifest']['refs'].items())+'</w:tbl>'
   page='<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/></w:sectPr>' if template=='MVP_16' else '<w:sectPr/>'
   write('word/document.xml','<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+body+table+page+'</w:body></w:document>')
  return b.getvalue()
 if kind!='PDF':raise Denied('INVALID_REQUEST',422)
 try:
  from reportlab.pdfbase import pdfmetrics
  from reportlab.pdfbase.ttfonts import TTFont
  from reportlab.lib.styles import ParagraphStyle
  from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
  choices=[os.environ['DATCO_PROPOSAL_FONT']] if os.environ.get('DATCO_PROPOSAL_FONT') else ['C:/Windows/Fonts/malgun.ttf','/usr/share/fonts/truetype/nanum/NanumGothic.ttf']
  font=next((Path(p) for p in choices if p and Path(p).is_file()),None)
  if font is None:raise Denied('PROPOSAL_KOREAN_FONT_UNAVAILABLE',503)
  fontname='DATCO_'+sha256(font.read_bytes()).hexdigest()[:12]
  if fontname not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont(fontname,str(font)))
  face=pdfmetrics.getFont(fontname).face
  if any(ord(c)>32 and ord(c) not in face.charToGlyph for p in paragraphs for c in p):raise Denied('PROPOSAL_FONT_GLYPH_MISSING',503)
  style=ParagraphStyle('proposal',fontName=fontname,fontSize=10,leading=16,wordWrap='CJK')
  heading_style=ParagraphStyle('heading',parent=style,fontSize=13,leading=19,spaceBefore=12,spaceAfter=7,keepWithNext=True)
  title_style=ParagraphStyle('title',parent=heading_style,fontSize=17,leading=24,spaceAfter=14)
  headings={section['heading'] for section in version['sections']}
  story=[]
  for p in paragraphs:
   chosen=(title_style if p==title else heading_style if p in headings else style) if template=='MVP_16' else style
   for line in p.splitlines() or ['']:story.extend([Paragraph(escape(line) or ' ',chosen),Spacer(1,4)])
  # Each reference gets a bounded row so long lists can flow across pages.
  rows=[[Paragraph(escape(k),style),Paragraph(escape(text(item)),style)]
        for k,value in version['manifest']['refs'].items()
        for item in (value if isinstance(value,list) and value else [value])]
  if rows:story.append(Table(rows,colWidths=[145,330],style=TableStyle([('VALIGN',(0,0),(-1,-1),'TOP')]),splitByRow=1))
  b=BytesIO();SimpleDocTemplate(b,title=title,author='DATCO',rightMargin=50,leftMargin=50,invariant=1).build(story);return b.getvalue()
 except Denied:raise
 except Exception:raise Denied('PROPOSAL_DOCUMENT_GENERATION_FAILED',503) from None
