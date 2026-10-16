"""Real editable OOXML and embedded-font PDF; no DB/eligibility shortcuts."""
import io,zipfile
from xml.etree import ElementTree as ET
import pytest
from pypdf import PdfReader
from app.proposal.documents import render,HEADINGS
from app.notice.domain import Denied

def sample():
 return dict(id='TEST_VERSION_123',ordinal=7,title='한글 맞춤형 제안서 <검토>',content_digest='a'*64,manifest={'refs':{'source':'TEST_EVIDENCE_1'}},sections=[{'heading':h,'body':'검증된 기업 원문과 담당자 제안은 구분합니다. 금액은 확인 필요.','evidence_refs':{'source':'TEST_EVIDENCE_1'}} for h in HEADINGS])

def test_docx_is_editable_xml_and_exact_version_content():
 v=sample();data=render(v,'DOCX');z=zipfile.ZipFile(io.BytesIO(data));root=ET.fromstring(z.read('word/document.xml'));content=''.join(root.itertext())
 assert v['title'] in content and v['id'] in content and v['sections'][0]['body'] in content
 assert '[Content_Types].xml' in z.namelist() and root.find('.//{*}tbl') is not None

def test_pdf_embeds_font_and_preserves_korean_and_version():
 v=sample();data=render(v,'PDF');reader=PdfReader(io.BytesIO(data));content=''.join(p.extract_text() for p in reader.pages)
 assert v['title'] in content and v['id'] in content and '금액은 확인 필요' in content
 fonts=[f.get_object() for p in reader.pages for f in p['/Resources']['/Font'].values()]
 assert any('/FontDescriptor' in f and '/FontFile2' in f['/FontDescriptor'].get_object() for f in fonts)

def test_pdf_explicit_missing_font_fails(monkeypatch):
 monkeypatch.setenv('DATCO_PROPOSAL_FONT','/nonexistent-test-font.ttf')
 with pytest.raises(Denied,match='PROPOSAL_KOREAN_FONT_UNAVAILABLE'):render(sample(),'PDF')

def test_invalid_document_content_is_not_reported_as_success():
 v=sample();v['sections']=[]
 with pytest.raises(Denied):render(v,'DOCX')


def test_invalid_xml_text_never_produces_corrupt_document():
 v=sample();v['sections'][0]['body']='TEST\x01invalid'
 with pytest.raises(Denied,match='PROPOSAL_INVALID_DOCUMENT_TEXT'):render(v,'DOCX')


@pytest.mark.parametrize('kind',['DOCX','PDF'])
def test_retry_of_same_version_is_byte_stable(kind):
 import time
 v=sample();first=render(v,kind)
 # Move the renderer wall clock without sleeping; content/Version are identical.
 from unittest.mock import patch
 with patch('time.time',return_value=time.time()+10):second=render(v,kind)
 assert first==second


def test_pdf_preserves_large_valid_feature_reference_table_across_pages():
 v=sample();refs=[str(i).zfill(36) for i in range(150)]
 v['manifest']['refs']['feature_revision_ids']=refs
 reader=PdfReader(io.BytesIO(render(v,'PDF')));content=''.join(p.extract_text() for p in reader.pages)
 assert len(reader.pages)>1
 assert all(ref in content for ref in refs)
 assert all(section['heading'] in content and section['body'] in content for section in v['sections'])
