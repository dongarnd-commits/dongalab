"""Local parsing only. The caller must authorize Company/File scope before reading.

No network, storage writes, OCR, image understanding or fact confirmation occurs here.
Locations refer to the immutable input digest, never to a guessed document role.
"""
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import PurePath
import re
import struct
import xml.etree.ElementTree as ET
from zipfile import BadZipFile, ZipFile

from pypdf import PdfReader
from pypdf.errors import PyPdfError

MAX_UPLOAD = 20 * 1024 * 1024
MAX_EXPANDED = 64 * 1024 * 1024
MAX_ENTRIES = 2000
MAX_LOCATIONS = 20000
MAX_TEXT = 2_000_000
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
S = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
ALLOWED = {'.pdf', '.docx', '.xlsx', '.jpg', '.jpeg', '.png', '.txt'}


class DocumentError(ValueError):
    """A bounded public error code; parser exceptions/source text are never exposed."""


@dataclass(frozen=True)
class Location:
    descriptor: str
    text: str
    page: int | None = None


@dataclass(frozen=True)
class ParsedDocument:
    digest: str
    format: str
    locations: tuple[Location, ...]
    limitations: tuple[str, ...]
    parser_version: str = 'company-local-parser-v1'
    ai_executed: bool = False


def xml(data):
    # stdlib XML expands internal entities; prohibit declarations before parsing.
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise DocumentError('UNSAFE_XML')
    # Only UTF-8 OOXML is accepted, avoiding UTF-16 declaration bypasses.
    text = data.decode('utf-8-sig', errors='strict')
    if '\x00' in text:
        raise DocumentError('UNSAFE_XML')
    return ET.fromstring(text)


def package(content):
    z = ZipFile(BytesIO(content))
    infos = z.infolist()
    if len(infos) > MAX_ENTRIES or sum(i.file_size for i in infos) > MAX_EXPANDED:
        z.close()
        raise DocumentError('DOCUMENT_EXPANSION_LIMIT')
    names = [i.filename for i in infos]
    if len(names) != len(set(names)) or any(i.flag_bits & 1 for i in infos):
        z.close()
        raise DocumentError('UNSAFE_PACKAGE')
    for name in names:
        if name.startswith(('/', '\\')) or '..' in name.replace('\\', '/').split('/') or 'vbaproject' in name.lower():
            z.close()
            raise DocumentError('UNSAFE_PACKAGE')
    return z


def parse_docx(content):
    with package(content) as z:
        root = xml(z.read('word/document.xml'))
        if root.tag != W + 'document':
            raise DocumentError('FORMAT_MISMATCH')
        result = []
        for n, paragraph in enumerate(root.iter(W + 'p'), 1):
            text = ''.join(node.text or '' for node in paragraph.iter(W + 't'))
            if text.strip():
                result.append(Location(f'DOCX paragraph {n}', text))
        return result, ['DOCX pagination, headers, footers and drawings are not extracted']


def parse_xlsx(content):
    with package(content) as z:
        workbook = xml(z.read('xl/workbook.xml'))
        if workbook.tag != S + 'workbook':
            raise DocumentError('FORMAT_MISMATCH')
        relationships = {r.attrib['Id']: r.attrib for r in xml(z.read('xl/_rels/workbook.xml.rels'))}
        strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            strings = [''.join(n.text or '' for n in item.iter(S+'t')) for item in xml(z.read('xl/sharedStrings.xml'))]
        result = []
        for sheet in workbook.iter(S + 'sheet'):
            rel_id = sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
            rel = relationships.get(rel_id, {})
            target = rel.get('Target', '')
            if rel.get('TargetMode') == 'External' or not rel.get('Type', '').endswith('/worksheet'):
                raise DocumentError('UNSUPPORTED_SHEET_RELATIONSHIP')
            path = target.lstrip('/') if target.startswith('/xl/') else 'xl/' + target
            if not re.fullmatch(r'xl/worksheets/[A-Za-z0-9_.-]+\.xml', path):
                raise DocumentError('UNSAFE_PACKAGE')
            root = xml(z.read(path))
            for cell in root.iter(S+'c'):
                address = cell.get('r', '')
                if not re.fullmatch(r'[A-Z]{1,3}[1-9][0-9]{0,6}', address):
                    raise DocumentError('INVALID_CELL_LOCATION')
                kind = cell.get('t')
                value = cell.findtext(S+'v', default='')
                formula = cell.find(S+'f')
                if formula is not None:
                    # A cached formula result may be stale; never emit it as a fact value.
                    value = 'FORMULA (not evaluated): ' + (formula.text or '')
                elif kind == 's':
                    if not value.isdigit() or int(value) >= len(strings):
                        raise DocumentError('INVALID_SHARED_STRING')
                    value = strings[int(value)]
                elif kind == 'inlineStr':
                    value = ''.join(t.text or '' for t in cell.iter(S+'t'))
                if value:
                    result.append(Location(f'XLSX sheet {sheet.get("name", "")} cell {address}', value))
        return result, ['XLSX raw values only; styles, dates, units, formula results and drawings require review']


def parse_document(filename: str, content: bytes) -> ParsedDocument:
    if not content or len(content) > MAX_UPLOAD:
        raise DocumentError('UPLOAD_SIZE_INVALID')
    # Name is display metadata only; no path is ever opened or extracted from it.
    suffix = PurePath(filename.replace('\\', '/')).suffix.lower()
    if suffix not in ALLOWED:
        raise DocumentError('UNSUPPORTED_FORMAT')
    limitations = []
    locations = []
    try:
        if suffix in ('.docx', '.xlsx'):
            if not content.startswith(b'PK\x03\x04'):
                raise DocumentError('FORMAT_MISMATCH')
            locations, limitations = (parse_docx if suffix == '.docx' else parse_xlsx)(content)
        elif suffix == '.pdf':
            if not content.startswith(b'%PDF-'):
                raise DocumentError('FORMAT_MISMATCH')
            reader = PdfReader(BytesIO(content), strict=True)
            if reader.is_encrypted:
                raise DocumentError('ENCRYPTED_DOCUMENT')
            if len(reader.pages) > 500:
                raise DocumentError('DOCUMENT_PAGE_LIMIT')
            for number, page in enumerate(reader.pages, 1):
                value = page.extract_text() or ''
                if value.strip():
                    locations.append(Location(f'PDF page {number}', value, number))
                else:
                    limitations.append(f'PDF page {number}: OCR/manual review required')
        elif suffix == '.txt':
            value = content.decode('utf-8-sig', errors='strict')
            if any(ord(c) < 32 and c not in '\n\r\t' for c in value):
                raise DocumentError('INVALID_TEXT')
            locations = [Location(f'TEXT line {n}', line) for n, line in enumerate(value.splitlines(), 1) if line.strip()]
        else:
            png = suffix == '.png'
            if png:
                valid = len(content) >= 33 and content.startswith(b'\x89PNG\r\n\x1a\n') and content[12:16] == b'IHDR'
                if valid:
                    width, height = struct.unpack('>II', content[16:24])
                    valid = 0 < width <= 20000 and 0 < height <= 20000
            else:
                valid = len(content) >= 4 and content.startswith(b'\xff\xd8\xff') and content.endswith(b'\xff\xd9')
            if not valid:
                raise DocumentError('FORMAT_MISMATCH')
            limitations = ['Image signature checked only; image decoding, OCR and visual understanding are not implemented; manual review required']
    except DocumentError:
        raise
    except (BadZipFile, KeyError, ValueError, ET.ParseError, OSError, IndexError, RuntimeError, PyPdfError):
        raise DocumentError('DOCUMENT_PARSE_FAILED') from None
    if len(locations) > MAX_LOCATIONS or sum(len(l.text) for l in locations) > MAX_TEXT:
        raise DocumentError('DOCUMENT_TEXT_LIMIT')
    if not locations and not limitations:
        limitations = ['No extractable text; manual review required']
    return ParsedDocument(sha256(content).hexdigest(), suffix[1:], tuple(locations), tuple(limitations))
