"""Synthetic, local unit tests. No business DB, external AI or private fixtures."""
from io import BytesIO
from zipfile import ZipFile
import pytest
from pypdf import PdfWriter
from app.company.documents import parse_document, DocumentError
from app.company.analysis import AnalysisInput, AnalysisError, UnavailableAnalysis, analyze


def zipped(files):
    out = BytesIO()
    with ZipFile(out, 'w') as z:
        for name, content in files.items():
            z.writestr(name, content)
    return out.getvalue()


def test_docx_paragraph_locations_preserve_text():
    raw = zipped({'word/document.xml': '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>TEST company</w:t></w:r></w:p><w:p/><w:p><w:r><w:t>revenue 100</w:t></w:r></w:p></w:body></w:document>'})
    result = parse_document('test.docx', raw)
    assert [(x.descriptor, x.text) for x in result.locations] == [('DOCX paragraph 1', 'TEST company'), ('DOCX paragraph 3', 'revenue 100')]
    assert result.limitations and not result.ai_executed


def test_xlsx_shared_inline_raw_and_formula_are_distinct():
    raw = zipped({
      'xl/workbook.xml': '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Finance" r:id="r1"/></sheets></workbook>',
      'xl/_rels/workbook.xml.rels': '<Relationships><Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
      'xl/sharedStrings.xml': '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><t>Revenue</t></si></sst>',
      'xl/worksheets/sheet1.xml': '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row><c r="A1" t="s"><v>0</v></c><c r="B1"><v>100</v></c><c r="C1" t="inlineStr"><is><t>2025 KRW</t></is></c><c r="D1"><f>B1*2</f><v>200</v></c></row></sheetData></worksheet>'})
    result = parse_document('test.xlsx', raw)
    assert [x.text for x in result.locations] == ['Revenue', '100', '2025 KRW', 'FORMULA (not evaluated): B1*2']
    assert result.locations[1].descriptor == 'XLSX sheet Finance cell B1'
    assert result.limitations


def test_scanned_pdf_requires_manual_review():
    writer = PdfWriter(); writer.add_blank_page(width=100, height=100)
    out = BytesIO(); writer.write(out)
    result = parse_document('scan.pdf', out.getvalue())
    assert not result.locations and 'page 1' in result.limitations[0]
    assert not result.ai_executed


def test_text_pdf_preserves_page_evidence():
    from reportlab.pdfgen.canvas import Canvas
    out = BytesIO(); c = Canvas(out)
    c.drawString(20, 700, 'TEST page one'); c.showPage()
    c.drawString(20, 700, 'TEST page two'); c.save()
    result = parse_document('report.pdf', out.getvalue())
    assert [l.page for l in result.locations] == [1, 2]
    assert 'TEST page two' in result.locations[1].text


@pytest.mark.parametrize('name,raw,code', [
 ('bad.pdf', b'not a pdf', 'FORMAT_MISMATCH'),
 ('bad.pdf', b'%PDF-broken', 'DOCUMENT_PARSE_FAILED'),
 ('bad.docx', b'not a zip', 'FORMAT_MISMATCH'),
 ('test.exe', b'abc', 'UNSUPPORTED_FORMAT'),
 ('test.txt', b'\xff\xfe', 'DOCUMENT_PARSE_FAILED'),
 ('test.txt', b'abc\x00', 'INVALID_TEXT'),
 ('bad.png', b'not an image', 'FORMAT_MISMATCH'),
 ('empty.txt', b'', 'UPLOAD_SIZE_INVALID'),
])
def test_invalid_input_has_safe_reason(name, raw, code):
    with pytest.raises(DocumentError, match=code): parse_document(name, raw)


def test_package_entities_and_traversal_are_rejected():
    for files in [
        {'word/document.xml': '<!DOCTYPE x [<!ENTITY secret "private">]><x>&secret;</x>'},
        {'../outside': 'private', 'word/document.xml': '<x/>'},
        {'word/vbaProject.bin': 'macro', 'word/document.xml': '<x/>'},
    ]:
        with pytest.raises(DocumentError, match='UNSAFE_'): parse_document('test.docx', zipped(files))


def test_package_expansion_limit(monkeypatch):
    import app.company.documents as parser
    monkeypatch.setattr(parser, 'MAX_EXPANDED', 5)
    with pytest.raises(DocumentError, match='DOCUMENT_EXPANSION_LIMIT'):
        parse_document('test.docx', zipped({'word/document.xml': 'too much'}))


class Fixture:
    mode = 'TEST_FIXTURE'
    def __init__(self, changes=None, candidate_changes=None):
        self.changes = changes or {}; self.candidate_changes = candidate_changes or {}; self.called = False
    def analyze(self, source):
        self.called = True
        candidate = dict(field='company_name', value='TEST', descriptor='TEXT line 1', quote='TEST company', claim='EXTRACTED', reason='TEST exact source', uncertainty='TEST candidate needs human review')
        candidate.update(self.candidate_changes)
        data = dict(company_id=source.company_id, source_version_id=source.source_version_id, digest=source.document.digest, provider='TEST', model_version='TEST-v1', prompt_version='TEST-v1', mode=self.mode, candidates=[candidate])
        data.update(self.changes)
        return data


def source(): return AnalysisInput('TEST-COMPANY-A', 'TEST-VERSION-A', parse_document('test.txt', b'TEST company'))


def test_provider_absent_and_external_transfer_block_before_call():
    with pytest.raises(AnalysisError, match='AI_PROVIDER_NOT_CONNECTED'): analyze(source())
    p = Fixture(); p.mode = 'REAL_AI'
    with pytest.raises(AnalysisError, match='EXTERNAL_AI_TRANSFER_NOT_APPROVED'): analyze(source(), p)
    assert not p.called


def test_fixture_is_not_real_ai_or_confirmed_fact():
    output = analyze(source(), Fixture())
    assert output.mode == 'TEST_FIXTURE'
    assert 'confirmed' not in output.model_dump()
    assert output.candidates[0].quote == 'TEST company'


@pytest.mark.parametrize('changes', [{'company_id': 'OTHER'}, {'source_version_id': 'OTHER'}, {'digest': '0'*64}, {'mode': 'REAL_AI'}])
def test_provider_cannot_replace_scope_version_digest_or_mode(changes):
    with pytest.raises(AnalysisError, match='ANALYSIS_SOURCE_MISMATCH'): analyze(source(), Fixture(changes))


@pytest.mark.parametrize('changes,code', [
    ({'descriptor': 'TEXT line 999'}, 'EVIDENCE_QUOTE_NOT_FOUND'),
    ({'quote': 'invented'}, 'EVIDENCE_QUOTE_NOT_FOUND'),
    ({'value': 'invented'}, 'EXTRACTED_VALUE_NOT_IN_EVIDENCE'),
    ({'field': 'revenue', 'period': None, 'unit': None}, 'AI_EXECUTION_OR_OUTPUT_INVALID'),
    ({'confirmed': True}, 'AI_EXECUTION_OR_OUTPUT_INVALID'),
])
def test_invalid_output_never_becomes_normal_candidate(changes, code):
    with pytest.raises(AnalysisError, match=code): analyze(source(), Fixture(candidate_changes=changes))


def test_provider_error_does_not_expose_private_content():
    class Broken(Fixture):
        def analyze(self, source): raise RuntimeError('PRIVATE_SECRET_TEST')
    with pytest.raises(AnalysisError) as e: analyze(source(), Broken())
    assert str(e.value) == 'AI_EXECUTION_OR_OUTPUT_INVALID'
    assert 'PRIVATE' not in str(e.value)


def test_unknown_provider_mode_is_blocked_before_call():
    provider = Fixture(); provider.mode = 'UNKNOWN'
    with pytest.raises(AnalysisError, match='AI_PROVIDER_MODE_INVALID'): analyze(source(), provider)
    assert not provider.called


def test_utf8_korean_and_original_line_numbers():
    raw = '회사: 가상기업\n\n매출: 100원'.encode('utf-8')
    parsed = parse_document('company.txt', raw)
    assert parsed.locations[0].text == '회사: 가상기업'
    assert parsed.locations[1].descriptor == 'TEXT line 3'
    assert parsed.locations[1].text == '매출: 100원'


def test_encrypted_pdf_is_not_analyzed():
    writer = PdfWriter(); writer.add_blank_page(width=100, height=100); writer.encrypt('TEST_ONLY')
    out = BytesIO(); writer.write(out)
    with pytest.raises(DocumentError, match='ENCRYPTED_DOCUMENT'): parse_document('locked.pdf', out.getvalue())


def test_no_file_is_written_by_path_shaped_filename(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    parsed = parse_document('../../private/company.txt', b'TEST company')
    assert parsed.locations[0].text == 'TEST company'
    assert list(tmp_path.iterdir()) == []


def test_utf16_entity_declaration_cannot_bypass_xml_guard():
    raw = '<!DOCTYPE x [<!ENTITY secret "private">]><x>&secret;</x>'.encode('utf-16-le')
    with pytest.raises(DocumentError, match='UNSAFE_XML'):
        parse_document('test.docx', zipped({'word/document.xml': raw}))


def test_explicit_unavailable_adapter_has_same_safe_reason():
    with pytest.raises(AnalysisError, match='AI_PROVIDER_NOT_CONNECTED'):
        analyze(source(), UnavailableAnalysis())
