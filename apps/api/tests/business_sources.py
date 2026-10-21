"""Sanitized, synthetic business inputs shared by local and CI tests."""
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
from xml.sax.saxutils import escape

def sources(directory):
    directory=Path(directory);directory.mkdir(exist_ok=True)
    financial=directory/'TEST-financial.xlsx'
    rows=[['연도','매출액','단위','통화','기준기간'],['2024','12000000','원','KRW','2024'],['2025','14000000','원','KRW','2025']]
    xml='<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'+''.join('<row r="'+str(i)+'">'+''.join('<c r="'+chr(65+j)+str(i)+'" t="inlineStr"><is><t>'+escape(v)+'</t></is></c>' for j,v in enumerate(row))+'</row>' for i,row in enumerate(rows,1))+'</sheetData></worksheet>'
    with ZipFile(financial,'w') as z:
        z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="TEST 재무" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr('xl/worksheets/sheet1.xml',xml)
    history=directory/'TEST-history.docx'
    lines=['수행사업명: TEST 스마트 생산 지원','수행기간: 2023','지원기관: TEST 합성 기관','주요 수행내용: TEST 이력 증빙']
    with ZipFile(history,'w') as z:z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+''.join('<w:p><w:r><w:t>'+escape(l)+'</w:t></w:r></w:p>' for l in lines)+'</w:body></w:document>')
    attachment=directory/'TEST-improvement.txt';attachment.write_text('TEST 작업실적과 불량 자료. 실제 기업 정보 없음.',encoding='utf-8')
    return dict(financial=str(financial),history=str(history),attachment=str(attachment))

def financial_scan():
    from PIL import Image,ImageDraw,ImageFont
    font=next(p for p in [Path('C:/Windows/Fonts/malgun.ttf'),Path('/usr/share/fonts/truetype/nanum/NanumGothic.ttf')] if p.exists())
    image=Image.new('RGB',(1654,2339),'white');draw=ImageDraw.Draw(image);f=ImageFont.truetype(str(font),44)
    for i,line in enumerate(['TEST 합성 재무자료','연도 : 2023','매출액 : 12340000','기준기간 : 2023','단위 : 원','통화 : KRW']):draw.text((100,120+i*160),line,font=f,fill='black')
    out=BytesIO();image.save(out,format='PDF',resolution=200);image.close();return out.getvalue()
