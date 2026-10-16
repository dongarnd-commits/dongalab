"""Small explicit synthetic fixtures; never claims validation of actual 649 source."""
import json
from copy import deepcopy
from pathlib import Path
import pytest
from app.infrastructure.dmp_inventory import InventoryError, parse_inventory, read_inventory, EXPECTED_SHA256

@pytest.fixture
def payload():
    return {"metadata":{"schema_version":"1","artifact_kind":"SYNTHETIC_TEST",
        "source_workbook":"synthetic.xlsx","source_sheet":"test","source_display_date":"2026-10-14",
        "feature_count":1,"system_count":1,"group_count":1,"uniqueness_rule":"feature_id",
        "system_counts":{"TEST":1}},"features":[{"feature_id":"DMP-0000000000000001",
        "system":"TEST","feature_group":"TEST_GROUP","name":"재고 테스트",
        "description":"입출고 기록의 합성 테스트 설명","origin":"SYNTHETIC_TEST","excel_row":2,
        "availability":"TEST_ONLY","availability_basis":"SYNTHETIC_TEST"}]}

def raw(payload):
    return json.dumps(payload,ensure_ascii=False).encode()

def test_small_fixture_preserves_source_without_invented_features(payload):
    result=parse_inventory(raw(payload),require_649=False)
    assert result.model_dump(exclude_none=True)==payload
    assert result.features[0].description==payload['features'][0]['description']

def test_duplicate_feature_id_is_rejected(payload):
    payload['features'].append(deepcopy(payload['features'][0]))
    with pytest.raises(InventoryError,match='DUPLICATE_FEATURE_ID'):
        parse_inventory(raw(payload),require_649=False)

@pytest.mark.parametrize('mutate,reason',[
    (lambda p:p['metadata'].update(feature_count=649),'METADATA_COUNT_MISMATCH'),
    (lambda p:p['metadata'].update(group_count=88),'METADATA_COUNT_MISMATCH'),
    (lambda p:p['metadata'].update(system_counts={'TEST':2}),'METADATA_COUNT_MISMATCH'),
    (lambda p:p['features'][0].update(name='   '),'BLANK_REQUIRED_VALUE'),
    (lambda p:p['features'][0].update(excel_row=True),'INVALID_INVENTORY_SCHEMA'),
    (lambda p:p['features'][0].update(feature_id='made-up'),'INVALID_INVENTORY_SCHEMA'),
    (lambda p:p['features'][0].update(extra='unsupported'),'INVALID_INVENTORY_SCHEMA'),
    (lambda p:p['features'][0].pop('origin'),'INVALID_INVENTORY_SCHEMA'),
])
def test_invalid_source_not_silently_coerced(payload,mutate,reason):
    mutate(payload)
    with pytest.raises(InventoryError,match=reason): parse_inventory(raw(payload),require_649=False)

def test_small_fixture_never_passes_actual_649_contract(payload):
    with pytest.raises(InventoryError,match='SOURCE_649_COUNT_MISMATCH'): parse_inventory(raw(payload))

@pytest.mark.parametrize('content',[b'{"metadata":{},"metadata":{}}',b'not json',b'\xff'])
def test_invalid_json_safe_errors(content):
    with pytest.raises(InventoryError): parse_inventory(content)

def test_missing_file_has_explicit_blocker_without_creating_file(tmp_path):
    source=tmp_path/'missing.json'
    with pytest.raises(InventoryError,match='BLOCKED_SOURCE_MISSING'): read_inventory(source)
    assert not source.exists()

def test_actual_user_source_if_supplied():
    source=Path(__file__).resolve().parents[3]/'_local_inputs/dmp_features_649.json'
    if not source.is_file(): pytest.skip('BLOCKED_SOURCE_MISSING: actual user data not supplied')
    inventory,digest,matches=read_inventory(source)
    assert len(inventory.features)==649
    assert matches, 'SOURCE_HASH_MISMATCH: compare actual file; never rewrite source'
