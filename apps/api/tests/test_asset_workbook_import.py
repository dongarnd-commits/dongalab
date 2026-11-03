"""Synthetic XLSX only; no private workbook or actual company data is used."""
from copy import deepcopy
from io import BytesIO
from uuid import uuid4
from xml.sax.saxutils import escape
from zipfile import ZipFile
import pytest
from app.capability.application import CapabilityApplication, fingerprint
from app.capability.asset_catalog import catalog_snapshot
from app.capability.workbook_import import WorkbookImportApplication, parse_workbook, compare_workbook, current_features, PARSER
from app.infrastructure import capability_schema as S, dmp_asset_schema as D
from app.infrastructure.notice_documents import LocalPrivateFiles
from app.notice.domain import Actor, Denied

ADMIN = Actor("test-admin", "DATCO_ADMIN")
OTHER = Actor("other-admin", "DATCO_ADMIN")

def workbook(rows, *, merged=(), formula=None, drawing=False, sheet="TEST source"):
    def cell(address, value):
        if formula and address == formula[0]:
            return f'<c r="{address}"><f>{escape(formula[1])}</f><v>999</v></c>'
        return f'<c r="{address}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'
    content = '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
    for number, row in enumerate(rows, 1):
        content += f'<row r="{number}">' + ''.join(cell(chr(65+i)+str(number), v) for i,v in enumerate(row) if v is not None) + '</row>'
    content += '</sheetData>'
    if merged: content += '<mergeCells>' + ''.join(f'<mergeCell ref="{span}"/>' for span in merged) + '</mergeCells>'
    if drawing: content += '<drawing/>'
    content += '</worksheet>'
    output=BytesIO()
    with ZipFile(output,'w') as z:
        z.writestr('xl/workbook.xml',f'<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="{escape(sheet)}" r:id="r1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels','<Relationships><Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr('xl/worksheets/sheet1.xml',content)
    return output.getvalue()

HEADER=['system','feature_group','name','description','feature_id']
ROWS=[HEADER,['TEST ERP','TEST stock','TEST receipts','TEST receive records',''],['TEST ERP','TEST stock','TEST issues','TEST dispatch records','']]

class Memory:
    def __init__(self, tmp_path):
        self.files=LocalPrivateFiles(tmp_path)
        self.tables={table.name:[] for table in (S.features,S.revisions,S.imports,S.members,S.audit,S.receipts,D.nodes,D.versions)}
        self.session=self
    def execute(self,*args): pass  # Pure tests only; PostgreSQL lock behavior is tested separately.
    def authorize(self,actor,manage=False): CapabilityApplication.authorize(self,actor,manage)
    def rows(self,table,**filters):
        return [deepcopy(row) for row in self.tables[table.name] if all(row.get(key)==value for key,value in filters.items())]
    def add(self,table,**data):
        data.setdefault('id',str(uuid4()));data.setdefault('created_at','2026-11-03T00:00:00Z')
        self.tables[table.name].append(deepcopy(data));return deepcopy(data)
    def record(self,actor,action,**targets): return self.add(S.audit,actor_id=actor.id,action=action,targets=targets)
    def command(self,actor,key,payload,execute):
        old=self.rows(S.receipts,actor_id=actor.id,key=key)
        if old:
            if old[0]['fingerprint']!=fingerprint(payload):raise Denied('IDEMPOTENCY_TARGET_MISMATCH',409)
            return old[0]['result']
        result=execute();self.add(S.receipts,actor_id=actor.id,key=key,fingerprint=fingerprint(payload),result=result);return result


def apply(app, preview, keys=None, resolutions=None, key=None):
    keys=keys if keys is not None else [row['row_key'] for row in preview['rows']]
    return app.apply(ADMIN,file_sha256=preview['file_sha256'],parser_version=preview['parser_version'],catalog_digest=preview['catalog_digest'],preview_digest=preview['preview_digest'],selections=[dict(row_key=row,resolution=(resolutions or {}).get(row)) for row in keys],key=key or str(uuid4()))


def test_workbook_parser_explicit_merge_locations_and_unsupported():
    raw=workbook([HEADER,['TEST ERP','TEST stock','TEST first','TEST one',''],[None,None,'TEST second','TEST two',''],[None,None,'TEST third','TEST three','']],merged=['A2:A3','B2:B3'],drawing=True)
    parsed=parse_workbook('개발 자료.xlsx',raw)
    assert parsed['filename']=='개발 자료.xlsx'
    assert len(parsed['rows'])==2
    second=parsed['rows'][1]
    assert second['data']['system']=='TEST ERP' and second['cells']['system']==dict(cell='A2',merged_range='A2:A3')
    assert second['cells']['name']==dict(cell='C3')
    assert any(row['row']==4 for row in parsed['unsupported'])
    assert any('WORKBOOK_DRAWING_UNSUPPORTED' in row['reason_codes'] for row in parsed['unsupported'])
    formula=parse_workbook('TEST.xlsx',workbook(ROWS,formula=('D2','1+2')))
    assert [r['row'] for r in formula['rows']]==[3]
    assert any('WORKBOOK_FORMULA_UNSUPPORTED' in r['reason_codes'] for r in formula['unsupported'])
    with pytest.raises(Denied):parse_workbook('../TEST.xlsx',raw)
    with pytest.raises(Denied):parse_workbook('TEST.xls',raw)
    with pytest.raises(Denied):parse_workbook('TEST.xlsx',b'not an Excel file')


def test_workbook_selected_apply_partial_reupload_rowmove_and_no_delete(tmp_path):
    service=Memory(tmp_path);app=WorkbookImportApplication(service)
    preview=app.preview(ADMIN,'TEST.xlsx',workbook(ROWS));first=apply(app,preview,[preview['rows'][0]['row_key']])
    assert first['changed']==1 and len(service.rows(S.features))==1
    second_preview=app.preview(ADMIN,'TEST.xlsx',workbook(ROWS));assert [r['status'] for r in second_preview['rows']]==['SAME','NEW']
    retained_revision=service.rows(S.revisions)[0]
    second=apply(app,second_preview);assert second['changed']==1 and second['unchanged']==1
    mixed_audit=[record for record in service.rows(S.audit) if record['action']=='APPLY_ASSET_WORKBOOK'][-1]['targets']
    current=current_features(service)
    assert mixed_audit['selected_scope']==[dict(row_key=row['row_key'],sheet=row['sheet'],row=row['row'],cells=row['cells'],
        target_feature_id=next(key for key,item in current.items() if item['data']['name']==row['data']['name']),
        applied_revision_id=next(item['revision']['id'] for item in current.values() if item['data']['name']==row['data']['name']),
        changed=row['status']=='NEW') for row in second_preview['rows']]
    assert mixed_audit['selected_scope'][0]['applied_revision_id']==retained_revision['id']
    assert len(service.rows(S.imports)[-1]['metadata']['workbook_provenance']['rows'])==1
    digest=catalog_snapshot(service)['digest'];counts={table.name:len(service.rows(table)) for table in (S.imports,S.features,S.revisions,S.members)}
    replay=app.preview(ADMIN,'TEST.xlsx',workbook(ROWS));result=apply(app,replay)
    assert result['changed']==0 and catalog_snapshot(service)['digest']==digest
    assert counts=={table.name:len(service.rows(table)) for table in (S.imports,S.features,S.revisions,S.members)}
    moved=app.preview(ADMIN,'TEST moved.xlsx',workbook([HEADER,ROWS[2],[],ROWS[1]]))
    assert all(row['status']=='SAME' for row in moved['rows'])
    assert apply(app,moved)['changed']==0 and catalog_snapshot(service)['digest']==digest
    unchanged_audit=[record for record in service.rows(S.audit) if record['action']=='APPLY_ASSET_WORKBOOK_NO_CHANGE'][-1]['targets']
    assert unchanged_audit['selected_scope']==[dict(row_key=row['row_key'],sheet=row['sheet'],row=row['row'],cells=row['cells'],
        target_feature_id=row['target_feature_id'],applied_revision_id=current[row['target_feature_id']]['revision']['id'],
        changed=False) for row in moved['rows']]
    assert unchanged_audit['selected_scope'][1]['applied_revision_id']==retained_revision['id']
    assert unchanged_audit['selected_scope'][1]['cells']['name']['cell']=='C4'
    same=app.preview(ADMIN,'TEST.xlsx',workbook(ROWS))
    with pytest.raises(Denied,match='INVALID_WORKBOOK_SELECTION'):apply(app,same,['0:2'],resolutions={'0:2':'NEW'})
    missing=app.preview(ADMIN,'TEST missing.xlsx',workbook([HEADER,ROWS[1]]));apply(app,missing)
    assert len(service.rows(S.features))==2 and catalog_snapshot(service)['digest']==digest
    assert app.original(ADMIN,preview['file_sha256'])[0]==workbook(ROWS)
    source=catalog_snapshot(service)['features'][0]['source'];assert source['kind']=='ADMIN_WORKBOOK'
    assert source['workbook']['location']['cells']['name']['cell'] in ('C2','C3')
    assert 'storage_key' not in source['workbook']


def test_workbook_review_explicit_changed_target_history_and_idempotency(tmp_path):
    service=Memory(tmp_path);app=WorkbookImportApplication(service)
    first=app.preview(ADMIN,'TEST.xlsx',workbook(ROWS));apply(app,first)
    before=deepcopy(service.rows(S.revisions));known=current_features(service);target=next(key for key,value in known.items() if value['data']['name']=='TEST receipts')
    changed=[HEADER,['TEST other','TEST moved','TEST renamed','TEST receive records','']]
    preview=app.preview(ADMIN,'TEST changed.xlsx',workbook(changed));assert preview['rows'][0]['status']=='DUPLICATE_SUSPECT'
    with pytest.raises(Denied,match='WORKBOOK_REVIEW_REQUIRED'):apply(app,preview)
    key=str(uuid4());result=apply(app,preview,resolutions={'0:2':target},key=key)
    assert result['changed']==1 and len(service.rows(S.features))==2
    assert service.rows(S.revisions)[:2]==before
    assert apply(app,preview,resolutions={'0:2':target},key=key)==result
    with pytest.raises(Denied,match='IDEMPOTENCY_TARGET_MISMATCH'):apply(app,preview,resolutions={'0:2':'NEW'},key=key)
    # A deliberate reversion appends a new exact source snapshot, retaining A and B.
    reverted=app.preview(ADMIN,'TEST revert.xlsx',workbook([HEADER,[*ROWS[1][:4],target]]))
    assert reverted['rows'][0]['status']=='CHANGED'
    assert apply(app,reverted)['changed']==1
    assert len(service.rows(S.features))==2 and len(service.rows(S.revisions))==4


def test_workbook_scope_stale_preview_duplicate_selection_and_unknown_id(tmp_path):
    service=Memory(tmp_path);app=WorkbookImportApplication(service)
    raw=workbook(ROWS);preview=app.preview(ADMIN,'TEST.xlsx',raw)
    for role in ('DATCO_OPERATOR','COMPANY_EDITOR','COMPANY_APPROVER'):
        who=Actor(role,role)
        with pytest.raises(Denied):app.preview(who,'TEST.xlsx',raw)
        with pytest.raises(Denied):app.original(who,preview['file_sha256'])
    with pytest.raises(Denied,match='OBJECT_NOT_FOUND'):app.original(OTHER,preview['file_sha256'])
    apply(app,preview,[preview['rows'][0]['row_key']])
    with pytest.raises(Denied,match='STALE_WORKBOOK_PREVIEW'):apply(app,preview,[preview['rows'][1]['row_key']])
    latest=app.preview(ADMIN,'TEST.xlsx',raw)
    with pytest.raises(Denied,match='INVALID_WORKBOOK_SELECTION'):apply(app,latest,['0:2','0:2'])
    duplicate=app.preview(ADMIN,'TEST dup.xlsx',workbook([HEADER,ROWS[1],ROWS[1]]))
    assert all(row['status']=='DUPLICATE_SUSPECT' for row in duplicate['rows'])
    different_description=deepcopy(ROWS[1]);different_description[3]='TEST separate description'
    conflicting=app.preview(ADMIN,'TEST conflicting.xlsx',workbook([HEADER,ROWS[1],different_description]))
    assert all(row['status']=='DUPLICATE_SUSPECT' for row in conflicting['rows'])
    unrelated=app.preview(ADMIN,'TEST empty descriptions.xlsx',workbook([HEADER,['TEST A','TEST group','TEST separate A','',''],['TEST B','TEST group','TEST separate B','','']]))
    assert all(row['status']=='NEW' for row in unrelated['rows'])
    unknown=app.preview(ADMIN,'TEST unknown.xlsx',workbook([HEADER,[*ROWS[1][:4],'DMP-FFFFFFFFFFFFFFFF']]))
    assert unknown['rows'][0]['status']=='UNKNOWN_ID'
    with pytest.raises(Denied,match='WORKBOOK_REVIEW_REQUIRED'):apply(app,unknown)



def test_workbook_korean_headers_and_explicit_classification_merge():
    korean=['시스템','모듈','기능명','기능설명','원천기능ID']
    rows=[korean,['TEST 시스템','TEST 모듈','TEST 입고','TEST 입고 기록',''],[None,None,'TEST 출고','TEST 출고 기록','']]
    parsed=parse_workbook('개발 자료.xlsx',workbook(rows,merged=['A2:A3','B2:B3'],sheet='기술원천'))
    assert len(parsed['rows'])==2 and parsed['unsupported']==[]
    assert parsed['rows'][1]['data']['system']=='TEST 시스템'
    assert parsed['rows'][1]['cells']['feature_group']==dict(cell='B2',merged_range='B2:B3')
    assert parsed['rows'][1]['sheet']=='기술원천'
    duplicate=[['시스템','system','기능그룹','기능','설명'],['TEST 시스템','TEST 시스템','TEST 그룹','TEST 기능','TEST 설명']]
    with pytest.raises(Denied,match='WORKBOOK_DUPLICATE_HEADER'):parse_workbook('중복.xlsx',workbook(duplicate))


def test_workbook_rejects_duplicate_or_blank_sheet_names_without_location_aliasing():
    from app.company.documents import parse_document
    from collections import Counter
    original=workbook(ROWS)
    output=BytesIO()
    with ZipFile(BytesIO(original)) as source, ZipFile(output,'w') as target:
        for name in source.namelist():
            content=source.read(name)
            if name=='xl/workbook.xml':
                content=content.replace(b'</sheets>',b'<sheet name="TEST source" r:id="r2"/></sheets>')
            if name=='xl/_rels/workbook.xml.rels':
                content=content.replace(b'</Relationships>',b'<Relationship Id="r2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/></Relationships>')
            target.writestr(name,content)
        target.writestr('xl/worksheets/sheet2.xml',source.read('xl/worksheets/sheet1.xml').replace(b'TEST receipts',b'TEST shadow'))
    duplicate=output.getvalue()
    # The generic parser accepts this malformed workbook; this intake must not
    # collapse the two sources into one sheet-name dictionary.
    generic=parse_document('TEST.xlsx',duplicate)
    assert max(Counter(location.descriptor for location in generic.locations).values())==2
    with pytest.raises(Denied,match='WORKBOOK_SHEET_NAME_INVALID'):
        parse_workbook('TEST.xlsx',duplicate)
    with pytest.raises(Denied,match='WORKBOOK_SHEET_NAME_INVALID'):
        parse_workbook('TEST.xlsx',workbook(ROWS,sheet=''))
