"""Read-only validation of user-supplied DMP inventory. No generated features or DB import."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field, ValidationError

EXPECTED_SHA256 = "28b1967ed77360d0fcc6d5525f6d7395fd899865b2e01e358402edc347d1d368"
SYSTEM_COUNTS = {"공통 MSA":96,"SCMS MSA":124,"닷비(DAT-V) MSA":59,"ERP-회계":73,
    "ERP-물류":47,"ERP-생산(MES)":24,"ERP-인사":22,"그룹웨어 MSA":119,
    "Edge Gateway":54,"플랫폼 인프라":31}
KNOWN_IDS = {"DMP-D89936F06CA33048":("ERP-물류","재고관리","재고현황"),
    "DMP-A72B49E339A21D50":("ERP-물류","재고관리","재고수불부"),
    "DMP-757AF017E65ADE72":("ERP-물류","구매관리","입고등록"),
    "DMP-9942A5CC2A989A73":("ERP-물류","판매관리","출고등록"),
    "DMP-3B035A3C50B10091":("ERP-생산(MES)","생산관리","작업실적등록"),
    "DMP-B1C747746FD519C7":("ERP-생산(MES)","품질관리","불량현황"),
    "DMP-252D1F1613160F28":("그룹웨어 MSA","전자결재","문서 기안")}

class InventoryError(ValueError):
    """Safe diagnostic; never echoes source payload or filesystem paths."""

class SourceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=False)

class Feature(SourceModel):
    feature_id: str = Field(pattern=r"^DMP-[A-F0-9]{16}$")
    system: str = Field(min_length=1)
    feature_group: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str
    origin: str = Field(min_length=1)
    excel_row: int = Field(gt=0)
    availability: str = Field(min_length=1)
    availability_basis: str = Field(min_length=1)

class Metadata(SourceModel):
    schema_version: str
    artifact_kind: str = Field(min_length=1)
    source_workbook: str = Field(min_length=1)
    source_sheet: str = Field(min_length=1)
    source_display_date: str
    feature_count: int = Field(gt=0)
    system_count: int = Field(gt=0)
    group_count: int = Field(gt=0)
    uniqueness_rule: str = Field(min_length=1)
    system_counts: dict[str,int]
    prepared_date: str | None = None
    availability_assertion: str | None = None
    fields: list[str] | None = None

class Inventory(SourceModel):
    metadata: Metadata
    features: list[Feature] = Field(min_length=1)

def _object(pairs):
    result = {}
    for key,value in pairs:
        if key in result:
            raise InventoryError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result

def parse_inventory(content: bytes, *, require_649: bool = True) -> Inventory:
    try:
        data=json.loads(content.decode("utf-8-sig"), object_pairs_hook=_object)
        inventory=Inventory.model_validate(data)
    except InventoryError:
        raise
    except (ValueError, UnicodeError, ValidationError):
        raise InventoryError("INVALID_INVENTORY_SCHEMA") from None
    fs=inventory.features; meta=inventory.metadata
    if any(not value.strip() for f in fs for value in
           (f.system,f.feature_group,f.name,f.origin,f.availability,f.availability_basis)):
        raise InventoryError("BLANK_REQUIRED_VALUE")
    if len({f.feature_id for f in fs}) != len(fs):
        raise InventoryError("DUPLICATE_FEATURE_ID")
    counts=dict(Counter(f.system for f in fs))
    groups={(f.system,f.feature_group) for f in fs}
    if (meta.feature_count,meta.system_count,meta.group_count)!=(len(fs),len(counts),len(groups)) or meta.system_counts!=counts:
        raise InventoryError("METADATA_COUNT_MISMATCH")
    if require_649:
        if len(fs)!=649 or counts!=SYSTEM_COUNTS or len(groups)!=88 or len({f.feature_group for f in fs})!=81:
            raise InventoryError("SOURCE_649_COUNT_MISMATCH")
        if any(f.feature_id != "DMP-"+sha256("\x1f".join((f.system,f.feature_group,f.name)).encode()).hexdigest()[:16].upper() for f in fs):
            raise InventoryError("SOURCE_FEATURE_ID_MISMATCH")
        indexed={f.feature_id:f for f in fs}
        for key,identity in KNOWN_IDS.items():
            f=indexed.get(key)
            if f is None or (f.system,f.feature_group,f.name)!=identity:
                raise InventoryError("SOURCE_FEATURE_REFERENCE_MISMATCH")
    return inventory

def read_inventory(path: Path) -> tuple[Inventory,str,bool]:
    try:
        raw=path.read_bytes()
    except FileNotFoundError:
        raise InventoryError("BLOCKED_SOURCE_MISSING") from None
    digest=sha256(raw).hexdigest()
    # A mismatch is surfaced, not corrected or silently accepted for import.
    return parse_inventory(raw), digest, digest==EXPECTED_SHA256

def main():
    """Validate local source without importing, creating files or printing source values."""
    import argparse
    parser=argparse.ArgumentParser(description="Read-only DMP source validation; no DB writes")
    parser.add_argument("--source",type=Path,default=Path(__file__).resolve().parents[4]/"_local_inputs/dmp_features_649.json")
    args=parser.parse_args()
    try:
        inventory,digest,matches=read_inventory(args.source)
    except InventoryError as exc:
        print(json.dumps({"status":str(exc)},ensure_ascii=True))
        return 2
    result={"status":"VALIDATED" if matches else "SOURCE_HASH_MISMATCH",
        "sha256":digest,"expected_sha256":EXPECTED_SHA256,"hash_matches":matches,
        "feature_count":len(inventory.features),"system_count":inventory.metadata.system_count,
        "system_group_count":inventory.metadata.group_count,"db_imported":False}
    print(json.dumps(result,ensure_ascii=True))
    return 0 if matches else 2

if __name__=="__main__":
    raise SystemExit(main())
