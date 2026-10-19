"""Isolated browser accounts + synthetic source documents, no seeded company workflow."""
from pathlib import Path
from uuid import uuid4
from io import BytesIO
from zipfile import ZipFile
import os,json,secrets
from reportlab.pdfgen.canvas import Canvas
from PIL import Image,ImageDraw
from isolation import require_test_database
from app.infrastructure.database import get_session_factory
from app.infrastructure.notice_store import SqlNoticeStore
from app.infrastructure.local_auth import hash_password

def prepare():
 require_test_database();password=secrets.token_urlsafe(24);accounts={}
 with get_session_factory().begin() as s:
  for label,role in [('editor','COMPANY_EDITOR'),('operator','DATCO_OPERATOR'),('admin','DATCO_ADMIN'),('other','COMPANY_EDITOR')]:
   row=SqlNoticeStore(s).add('actors',username='TEST_W1_UI_'+uuid4().hex,role=role,password_hash=hash_password(password));accounts[label]=row['username']
 root=Path(os.environ['DATCO_TEST_FILES']).parent/'company-browser';root.mkdir(exist_ok=True)
 docx=root/'TEST-company.docx'
 with ZipFile(docx,'w') as z:z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>기업명: TEST Evidence Company</w:t></w:r></w:p><w:p><w:r><w:t>업종: manufacturing</w:t></w:r></w:p></w:body></w:document>')
 pdf=root/'TEST-company.pdf';canvas=Canvas(str(pdf));canvas.drawString(20,700,'TEST source page one');canvas.showPage();canvas.drawString(20,700,'TEST source page two');canvas.save()
 xlsx=root/'TEST-finance.xlsx'
 with ZipFile(xlsx,'w') as z:
  z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Finance" r:id="r1"/></sheets></workbook>')
  z.writestr('xl/_rels/workbook.xml.rels','<Relationships><Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
  z.writestr('xl/worksheets/sheet1.xml','<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row><c r="A1" t="inlineStr"><is><t>Revenue 2025 KRW million</t></is></c><c r="B1"><v>100</v></c></row></sheetData></worksheet>')
 image=root/'TEST-layout.png';picture=Image.new('RGB',(400,100),'white');ImageDraw.Draw(picture).text((10,20),'TEST inventory area',fill='black');picture.save(image)
 result=dict(accounts=accounts,password=password,documents=[str(docx),str(pdf),str(xlsx),str(image)])
 Path(os.environ['DATCO_TEST_COMPANY_READY']).write_text(json.dumps(result),encoding='utf-8')
 return result
