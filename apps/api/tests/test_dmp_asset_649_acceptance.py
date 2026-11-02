"""Approved original 649 source: operation verification, not recommendation gold.

This private-input test intentionally requires the exact authorized local source.
It must not be substituted by CI synthetic data or copied into a public fixture.
All company inputs/actors are synthetic and use the normal API/Worker guards.
"""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import pytest
from sqlalchemy import select

from app.capability.application import CapabilityApplication, fingerprint
from app.capability.asset_catalog import catalog_snapshot
from app.capability.asset_composition import promotion_blockers
from app.capability.asset_solutions import generate
from app.company.improvement_rules import analyze
from app.core.config import ROOT
from app.infrastructure import capability_schema as K, dmp_asset_schema as D
from app.infrastructure.dmp_inventory import read_inventory, EXPECTED_SHA256
from app.notice.domain import Actor
from test_company_workflow import call
from test_dmp_asset_catalog import MemoryCatalog
from test_dmp_asset_pipeline import (
    pipeline_env, prepared, generated, composition_data, save_composition,
)

pytestmark = pytest.mark.integration
SOURCE = ROOT / "_local_inputs/dmp_features_649.json"
CASES = {
    "logistics_multi_module": (
        "창고 입출고를 기록하고 재고 수량을 조회하려고 합니다.", ""),
    "explicit_exclusion": (
        "재고 수량과 급여·근태·회계 자료를 조회하려고 합니다.", "급여와 근태 및 회계는 제외합니다."),
    "unsupported": (
        "양자중력 추진기관을 설계하고 우주선 항법을 최적화하려고 합니다.", ""),
    "unsupported_scope": (
        "불량 현황 조회와 불량 원인 규명을 원합니다.", ""),
    "zero_candidate": ("ZZZUNSUPPORTED649TASK", ""),
    "answer_in_original": (
        "창고 1개 사업장에서 엑셀과 수기로 입출고를 기록한다. 현재 재고 오차율은 8%이며 "
        "목표는 2%다. 입출고 기록과 재고 수량을 조회하려고 한다. 예산과 일정은 아직 미정이다.", ""),
}


@pytest.fixture(scope="module")
def approved_source():
    assert SOURCE.is_file(), "APPROVED_649_SOURCE_REQUIRED: no synthetic substitution"
    inventory, digest, matches = read_inventory(SOURCE)
    assert matches and digest == EXPECTED_SHA256, "APPROVED_SOURCE_HASH_MISMATCH"
    raw = SOURCE.read_bytes()
    assert sha256(raw).hexdigest() == digest
    return inventory, raw, digest


def memory_snapshot(inventory, digest):
    """Actual unmodified feature payloads through the production projection."""
    memory = MemoryCatalog()
    import_id = str(uuid5(NAMESPACE_URL, "649-import:" + digest))
    memory.tables[K.imports.name].append(dict(
        id=import_id, digest=digest, metadata=inventory.metadata.model_dump()))
    for item in inventory.features:
        data = item.model_dump()
        fid = str(uuid5(NAMESPACE_URL, "649-feature:" + item.feature_id))
        rid = str(uuid5(NAMESPACE_URL, "649-revision:" + item.feature_id))
        memory.tables[K.features.name].append(dict(id=fid, external_id=item.feature_id))
        memory.tables[K.revisions.name].append(dict(
            id=rid, feature_id=fid, ordinal=1, digest=fingerprint(data), data=data))
        memory.tables[K.members.name].append(dict(
            id=str(uuid5(NAMESPACE_URL, "649-member:" + item.feature_id)),
            import_id=import_id, feature_id=fid, revision_id=rid))
    return catalog_snapshot(memory)


def source_evidence(result, originals):
    """A hit must cite exact real source text; classification alone is insufficient."""
    for candidate in result["candidates"]:
        original = originals[candidate["external_id"]]
        assert candidate["name"] == original["name"]
        assert candidate["description"] == original["description"]
        assert candidate["provision_status"] == "NEEDS_CONFIRMATION"
        assert candidate["evidence"]
        for evidence in candidate["evidence"]:
            assert evidence["feature_revision_id"] == candidate["revision_id"]
            assert evidence["field"] in ("name", "description")
            assert evidence["quote"] == original[evidence["field"]]


def test_original649_projection_exclusions_answers_and_zero_are_distinct(approved_source, tmp_path):
    inventory, raw, digest = approved_source
    original_payloads = {item.feature_id: item.model_dump() for item in inventory.features}
    snapshot = memory_snapshot(inventory, digest)
    before = deepcopy(snapshot)
    assert len(snapshot["features"]) == 649
    assert Counter(item["availability"] for item in snapshot["features"]) == {"NEEDS_CONFIRMATION": 649}
    assert all(not item["data"]["release"] and not item["relations"]
               for item in snapshot["features"])
    summaries = {}
    for name, (text, constraints) in CASES.items():
        context = dict(company_id="TEST_649_COMPANY", site_id="TEST_649_SITE",
            improvement_version_id="TEST_649_VERSION", original_text=text,
            structured=dict(as_is=text, constraints=constraints))
        result = generate(context, snapshot)
        source_evidence(result, original_payloads)
        summaries[name] = dict(status=result["status"],
            candidates=len(result["candidates"]), alternatives=len(result["alternatives"]),
            module_counts=sorted({len(a["modules"]) for a in result["alternatives"]}))
        if name in ("unsupported", "zero_candidate"):
            assert result["status"] == "NO_SOLUTION"
            assert result["candidates"] == result["alternatives"] == []
            assert result["uncovered_demands"]
        else:
            assert result["status"] == "CANDIDATES" and result["candidates"]
        if name == "explicit_exclusion":
            control = generate(dict(context, structured=dict(as_is=text)), snapshot)
            assert any(item["system_name"] in ("ERP-인사", "ERP-회계")
                       for item in control["candidates"])
            assert all(item["system_name"] not in ("ERP-인사", "ERP-회계")
                       for item in result["candidates"])
        if name == "logistics_multi_module":
            assert len({item["module_id"] for item in result["candidates"]}) > 1
            assert any(len(item["modules"]) > 1 for item in result["alternatives"])
        if name == "unsupported_scope":
            assert all(row["status"] != "ADDRESSED" for alternative in result["alternatives"]
                       for row in alternative["coverage"])
            assert any("원인 규명" in missing for alternative in result["alternatives"]
                       for row in alternative["coverage"] for missing in row["missing_information"])
        if name == "answer_in_original":
            data = dict(as_is=text, goal="입출고 기록과 재고 수량을 조회하려고 한다.")
            spans = [dict(kind="IMPROVEMENT", version_id="TEST_649_VERSION", field=k, quote=v)
                     for k, v in data.items()]
            candidates, diagnostics = analyze(data, spans)
            assert not any(c["category"] == "MISSING_INFORMATION"
                and c["data"]["rule_id"] in ("R04", "R05") for c in candidates)
            assert next(d for d in diagnostics if d["rule"] == "R04")["outcome"] == "FOUND"
    assert snapshot == before
    assert SOURCE.read_bytes() == raw
    proof = dict(source_hash=digest, source_features=649, systems=10, system_groups=88,
        raw_available=649, projected_needs_confirmation=649,
        source_availability_basis_present=sum(bool(f.availability_basis.strip()) for f in inventory.features),
        source_availability_assertion=inventory.metadata.availability_assertion,
        source_description_present=sum(bool(f.description.strip()) for f in inventory.features),
        source_release_fields=0, registered_relation_fields=0, cases=summaries,
        scope="SYSTEM_OPERATION_ONLY_NOT_RECOMMENDATION_QUALITY_OR_DELIVERY_VALIDATION")
    out = Path(os.environ.get("DATCO_649_PROOF_DIR", tmp_path))
    out.mkdir(parents=True, exist_ok=True)
    (out / "source-649-operation-scope.json").write_text(
        json.dumps(proof, ensure_ascii=False, indent=2), encoding="utf-8")


def test_original649_real_worker_generate_draft_save_and_reload(pipeline_env, approved_source):
    e = pipeline_env
    inventory, raw, digest = approved_source
    with e["factory"].begin() as session:
        service = CapabilityApplication(session, e["files"])
        actor = Actor(e["people"]["admin"]["id"], "DATCO_ADMIN")
        receipt = service.import_inventory(raw, actor)
        assert receipt["feature_count"] == 649 and not receipt["replay"]
        assert service.import_inventory(raw, actor)["replay"]
        assert service.rows(D.nodes) == []
        originals = {row["id"]: deepcopy(row) for row in service.rows(K.revisions)}
        assert len(originals) == 649 and len(service.rows(K.members)) == 649
        assert service.rows(K.imports)[0]["digest"] == digest
    _, target = prepared(e)
    run = generated(e, target)
    assert run["current_valid"] and run["data"]["candidates"]
    source_evidence(run["data"], {f.feature_id: f.model_dump() for f in inventory.features})
    alternative = next(a for a in run["data"]["alternatives"] if len(a["modules"]) > 1)
    assert all(f["availability"] == "NEEDS_CONFIRMATION" for f in alternative["features"])
    assert all(link["verification"] == "UNVERIFIED" for link in alternative["integrations"])
    data = composition_data(run, alternative)
    saved = save_composition(e, data)
    reloaded = call(e, "operator", "/capability/compositions/" + saved["id"])
    stored = reloaded["versions"][0]
    assert stored["id"] == saved["version_id"] and stored["data"]["asset_basis"] == data["asset_basis"]
    assert stored["data"]["asset_selections"] == data["asset_selections"]
    assert stored["data"]["coverage"] == data["coverage"]
    assert call(e, "operator", "/capability/asset-solutions/" + run["id"])["data"] == run["data"]
    assert generated(e, target)["id"] == run["id"]
    with e["factory"]() as session:
        service = CapabilityApplication(session, e["files"])
        assert "ASSET_AVAILABILITY_UNVERIFIED" in promotion_blockers(service, stored["data"])
        assert {row["id"]: row for row in service.rows(K.revisions)} == originals
        assert len(service.rows(K.features)) == len(service.rows(K.members)) == 649
        assert len(service.rows(K.imports)) == 1
        assert service.rows(D.nodes) == service.rows(K.versions) == []
        assert len(list(session.execute(select(D.composition_features)))) == len(data["asset_selections"])
    assert SOURCE.read_bytes() == raw
