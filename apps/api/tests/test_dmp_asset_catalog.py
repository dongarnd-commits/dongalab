"""Synthetic metadata only. No real DMP 649 payload or company documents."""
from copy import deepcopy
from uuid import uuid4
import pytest
from app.capability.application import CapabilityApplication, fingerprint
from app.capability.asset_catalog import (
    AssetCatalogApplication, catalog_snapshot, normalize_data, validate_parent, validate_relations,
    bind_relation_versions)
from app.infrastructure import capability_schema as S, dmp_asset_schema as D
from app.infrastructure.dmp_inventory import Feature
from app.notice.domain import Actor, Denied


def data(name="TEST stock record", **changes):
    result = dict(name=name, description="SYNTHETIC TEST stock movement history", role="",
        business_areas=["TEST logistics"], problems=["TEST manual records"], conditions=[],
        exclusions=[], prerequisites=[], release="TEST-1", availability="NEEDS_CONFIRMATION",
        availability_evidence="", relations=[])
    result.update(changes)
    return result


class MemoryCatalog:
    """Read-only port fixture; every mutation fails."""
    def __init__(self):
        self.tables = {table.name: [] for table in (S.features, S.revisions, S.imports, S.members,
                                                    D.nodes, D.versions)}
    def rows(self, table, **filters):
        return [deepcopy(row) for row in self.tables[table.name]
                if all(row.get(key) == value for key, value in filters.items())]
    def authorize(self, actor, manage=False):
        CapabilityApplication.authorize(self, actor, manage)
    def command(self, *args, **kwargs):
        raise AssertionError("Read-only test must never execute a command")


def source(memory, feature_id="feature-1", external_id="DMP-0000000000000001", ordinal=1, **changes):
    if not any(r["id"] == feature_id for r in memory.tables[S.features.name]):
        memory.tables[S.features.name].append(dict(id=feature_id, external_id=external_id))
    payload = dict(feature_id=external_id, system="TEST ERP", feature_group="TEST stock module",
        name="TEST stock record", description="SYNTHETIC TEST movement history", origin="SYNTHETIC_TEST",
        excel_row=1, availability="AVAILABLE", availability_basis="SYNTHETIC_TEST_ONLY")
    payload.update(changes)
    revision = dict(id=feature_id + "-revision-" + str(ordinal), feature_id=feature_id,
                    ordinal=ordinal, digest=fingerprint(payload), data=payload)
    memory.tables[S.revisions.name].append(revision)
    return revision


def managed(memory, kind, node_id, parent_id=None, feature_id=None, source_id=None, **changes):
    payload = normalize_data(data(**dict({"name": "TEST " + kind}, **changes)))
    node = dict(id=node_id, kind=kind, feature_id=feature_id, current_ordinal=1)
    version = dict(id=node_id + "-v1", node_id=node_id, ordinal=1, parent_id=parent_id,
                   source_revision_id=source_id, parent_version_id=next((v["id"] for v in memory.tables[D.versions.name]
                       if v["node_id"] == parent_id), None),
                   digest=fingerprint(payload), data=payload, actor_id="TEST_ADMIN")
    memory.tables[D.nodes.name].append(node)
    memory.tables[D.versions.name].append(version)
    return node, version


def managed_memory():
    memory = MemoryCatalog()
    revision = source(memory)
    managed(memory, "SYSTEM", "system", availability="VERIFIED", availability_evidence="TEST system checked")
    managed(memory, "MODULE", "module", "system", availability="VERIFIED",
            availability_evidence="TEST module checked")
    managed(memory, "FEATURE", "asset-feature", "module", "feature-1", revision["id"],
            availability="VERIFIED", availability_evidence="TEST feature checked",
            business_areas=["TEST warehouse"], name="TEST stock record")
    return memory


def test_source_snapshot_is_read_only_and_does_not_promote_available():
    memory = MemoryCatalog()
    source(memory)
    before = deepcopy(memory.tables)
    result = catalog_snapshot(memory)
    assert memory.tables == before
    feature = result["features"][0]
    assert feature["availability"] == "NEEDS_CONFIRMATION"
    assert feature["asset_version_id"] is None
    assert feature["source_current"] is True
    assert feature["mapping_status"] == "SOURCE_CLASSIFICATION"
    assert feature["system_id"].startswith("source-system:")
    assert feature["module_id"].startswith("source-module:")
    assert all(item["mapping_status"] == "SOURCE_CLASSIFICATION"
               for item in result["systems"] + result["modules"])
    assert feature["source"]["revision_digest"] == before[S.revisions.name][0]["digest"]


def test_snapshot_digest_ignores_database_row_order_but_detects_new_sources_and_metadata():
    memory = MemoryCatalog()
    source(memory)
    source(memory, "feature-2", "DMP-0000000000000002", name="TEST payroll")
    first = catalog_snapshot(memory)["digest"]
    for rows in memory.tables.values():
        rows.reverse()
    assert catalog_snapshot(memory)["digest"] == first
    source(memory, ordinal=2, description="SYNTHETIC changed function")
    assert catalog_snapshot(memory)["digest"] != first
    prior = catalog_snapshot(memory)["digest"]
    managed(memory, "SYSTEM", "new-system")
    assert catalog_snapshot(memory)["digest"] != prior


def test_managed_snapshot_has_exact_parent_versions_and_source_reference():
    result = catalog_snapshot(managed_memory())
    feature = result["features"][0]
    assert (feature["asset_version_id"], feature["module_version_id"], feature["system_version_id"]) == (
        "asset-feature-v1", "module-v1", "system-v1")
    assert feature["revision_id"] == "feature-1-revision-1"
    assert feature["availability"] == "VERIFIED"
    assert feature["business_areas"] == ["TEST warehouse"]
    assert feature["mapping_status"] == "MANAGED"


@pytest.mark.parametrize("parent_kind,status", [("SYSTEM", "RETIRED"), ("MODULE", "UNAVAILABLE"),
                                               ("MODULE", "NEEDS_CONFIRMATION")])
def test_parent_state_cannot_leave_descendant_feature_verified(parent_kind, status):
    memory = managed_memory()
    for version in memory.tables[D.versions.name]:
        if version["node_id"] == parent_kind.lower():
            version["data"]["availability"] = status
    feature = catalog_snapshot(memory)["features"][0]
    assert feature["availability"] == status
    assert feature["declared_availability"] == "VERIFIED"


def test_new_raw_revision_does_not_relabel_old_managed_reference_current():
    memory = managed_memory()
    before = catalog_snapshot(memory)
    source(memory, ordinal=2, description="SYNTHETIC source revision changed")
    after = catalog_snapshot(memory)
    feature = after["features"][0]
    assert after["digest"] != before["digest"]
    assert feature["revision_id"] == "feature-1-revision-1"
    assert feature["latest_source_revision_id"] == "feature-1-revision-2"
    assert feature["source_current"] is False
    assert feature["mapping_status"] == "SOURCE_REVISION_CHANGED"
    assert feature["availability"] == "NEEDS_CONFIRMATION"


def test_source_detail_preserves_all_history_and_external_id_search():
    memory = MemoryCatalog()
    first = source(memory)
    second = source(memory, ordinal=2, description="SYNTHETIC changed")
    app = AssetCatalogApplication(memory)
    operator = Actor("operator", "DATCO_OPERATOR")
    result = app.list_assets(operator, kind="FEATURE", q="DMP-0000000000000001")
    assert result["total"] == 1
    detailed = app.detail(operator, "DMP-0000000000000001")
    assert detailed["root"]["managed"] is False
    assert detailed["source_revisions"] == [first, second]
    assert detailed["versions"] == [first, second]


def test_catalog_filters_business_status_parent_and_pagination():
    memory = managed_memory()
    source(memory, "feature-2", "DMP-0000000000000002", name="TEST payroll")
    app = AssetCatalogApplication(memory)
    operator = Actor("operator", "DATCO_OPERATOR")
    assert app.list_assets(operator, kind="FEATURE", q="warehouse")["total"] == 1
    assert app.list_assets(operator, kind="FEATURE", status="VERIFIED")["total"] == 1
    assert app.list_assets(operator, kind="FEATURE", system="system", module="module")["total"] == 1
    assert app.list_assets(operator, kind="FEATURE", q="definitely absent")["total"] == 0
    page1 = app.list_assets(operator, kind="FEATURE", limit=1)
    page2 = app.list_assets(operator, kind="FEATURE", page=2, limit=1)
    assert page1["items"][0]["id"] != page2["items"][0]["id"]


@pytest.mark.parametrize("role", ["COMPANY_EDITOR", "COMPANY_APPROVER"])
def test_company_cannot_read_or_mutate_internal_asset_catalog(role):
    app = AssetCatalogApplication(MemoryCatalog())
    actor = Actor("test-actor", role)
    with pytest.raises(Denied, match="ACTION_NOT_AUTHORIZED"):
        app.list_assets(actor)
    with pytest.raises(Denied, match="ACTION_NOT_AUTHORIZED"):
        app.detail(actor, "anything")
    with pytest.raises(Denied, match="ACTION_NOT_AUTHORIZED"):
        app.create(actor, kind="SYSTEM", data=data(), key="not-authorized")


def test_operator_cannot_create_or_revise_assets():
    app = AssetCatalogApplication(MemoryCatalog())
    actor = Actor("test-operator", "DATCO_OPERATOR")
    with pytest.raises(Denied, match="ACTION_NOT_AUTHORIZED"):
        app.create(actor, kind="SYSTEM", data=data(), key="not-authorized")
    with pytest.raises(Denied, match="ACTION_NOT_AUTHORIZED"):
        app.revise(actor, "system", expected_version="v1", data=data(), key="not-authorized")


@pytest.mark.parametrize("payload,reason", [
    ({"name": " "}, "REQUIRED_DATA_MISSING"),
    ({"name": "TEST", "availability": "AVAILABLE"}, "INVALID_ASSET_STATUS"),
    ({"name": "TEST", "availability": "VERIFIED", "availability_evidence": " "}, "AVAILABILITY_EVIDENCE_REQUIRED"),
    ({"name": "TEST", "business_areas": [""]}, "INVALID_ASSET_DATA"),
    ({"name": "TEST", "secret": "unaccepted field"}, "INVALID_ASSET_DATA"),
    ({"name": "TEST", "relations": [{"target_node_id": "b", "kind": "INTEGRATION",
        "condition": "TEST", "verified": True}]}, "RELATION_EVIDENCE_REQUIRED"),
    ({"name": "TEST", "relations": [{"target_node_id": "b", "kind": "INTEGRATION",
        "condition": "TEST", "verified": "true"}]}, "INVALID_ASSET_RELATION"),
])
def test_direct_application_validation_rejects_unverified_assertions(payload, reason):
    with pytest.raises(Denied, match=reason):
        normalize_data(payload)


def test_hierarchy_accepts_only_registered_parent_of_correct_kind():
    memory = managed_memory()
    nodes = {n["id"]: n for n in memory.tables[D.nodes.name]}
    current = {v["node_id"]: v for v in memory.tables[D.versions.name]}
    validate_parent("SYSTEM", None, nodes, current)
    validate_parent("MODULE", "system", nodes, current)
    validate_parent("FEATURE", "module", nodes, current)
    for kind, parent in (("MODULE", "source-system:unregistered"), ("FEATURE", "system"),
                         ("SYSTEM", "module"), ("MODULE", None)):
        with pytest.raises(Denied, match="ASSET_PARENT_KIND_MISMATCH"):
            validate_parent(kind, parent, nodes, current)


def relation(target, kind="DEPENDENCY"):
    return dict(target_node_id=target, kind=kind, condition="TEST actual prerequisite",
                verified=False, evidence="")


def test_relation_targets_replacement_kind_and_directed_cycles_are_validated():
    nodes = {"a": {"kind": "MODULE"}, "b": {"kind": "MODULE"}, "system": {"kind": "SYSTEM"}}
    current = {"a": {"data": {"relations": [relation("b")]}},
               "b": {"data": {"relations": []}}, "system": {"data": {"relations": []}}}
    with pytest.raises(Denied, match="ASSET_RELATION_CYCLE"):
        validate_relations("b", "MODULE", [relation("a")], nodes, current)
    with pytest.raises(Denied, match="ASSET_SELF_RELATION"):
        validate_relations("a", "MODULE", [relation("a")], nodes, current)
    with pytest.raises(Denied, match="ASSET_RELATION_TARGET_NOT_FOUND"):
        validate_relations("a", "MODULE", [relation("missing")], nodes, current)
    with pytest.raises(Denied, match="ASSET_REPLACEMENT_KIND_MISMATCH"):
        validate_relations("a", "MODULE", [relation("system", "REPLACEMENT")], nodes, current)
    current["a"]["data"]["relations"] = [relation("b", "REPLACEMENT")]
    with pytest.raises(Denied, match="ASSET_RELATION_CYCLE"):
        validate_relations("b", "MODULE", [relation("a", "REPLACEMENT")], nodes, current)
    # Bidirectional integration is not a dependency cycle or a proven integration.
    validate_relations("b", "MODULE", [relation("a", "INTEGRATION")], nodes, current)


def test_api_dto_forbids_unknown_fields_and_requires_exact_version():
    from pydantic import ValidationError
    from app.api.dmp_assets import CreateAsset, ReviseAsset
    with pytest.raises(ValidationError):
        CreateAsset.model_validate(dict(kind="SYSTEM", data=data(), idempotency_key="key", admin=True))
    with pytest.raises(ValidationError):
        ReviseAsset.model_validate(dict(data=data(), idempotency_key="key", expected_version="wrong"))
    assert CreateAsset.model_validate(dict(kind="SYSTEM", data=data(), idempotency_key="key")).data.availability == "NEEDS_CONFIRMATION"


@pytest.fixture
def asset_context(tmp_path):
    # Import the DB harness only when integration tests actually run.
    from test_notice_slice import context
    yield from context.__wrapped__(tmp_path)


@pytest.fixture
def asset_env(asset_context):
    from app.infrastructure.local_auth import hash_password
    from app.infrastructure.notice_store import SqlNoticeStore
    factory, files, operator = asset_context
    with factory.begin() as session:
        user = SqlNoticeStore(session).add("actors", username="TEST_ASSET_ADMIN_" + uuid4().hex,
            role="DATCO_ADMIN", password_hash=hash_password("test-only-password"))
        admin = Actor(user["id"], user["role"])
    return factory, files, operator, admin


def hierarchy(service, admin):
    app = AssetCatalogApplication(service)
    system = app.create(admin, kind="SYSTEM", data=data("TEST asset ERP"), key=uuid4().hex)
    module = app.create(admin, kind="MODULE", parent_id=system["id"],
                        data=data("TEST asset stock"), key=uuid4().hex)
    return app, system, module


@pytest.mark.integration
def test_pg_admin_create_revision_idempotency_and_old_source_preservation(asset_env):
    factory, files, operator, admin = asset_env
    with factory.begin() as session:
        service = CapabilityApplication(session, files)
        app, system, module = hierarchy(service, admin)
        original_data = data("TEST asset movement")
        command_key = uuid4().hex
        created = app.create(admin, kind="FEATURE", parent_id=module["id"],
                             data=original_data, key=command_key)
        assert app.create(admin, kind="FEATURE", parent_id=module["id"],
                          data=original_data, key=command_key) == created
        first = app.detail(operator, created["id"])
        original_revision = deepcopy(first["source_revisions"][0])
        assert Feature.model_validate(original_revision["data"]).origin.startswith("ADMIN_MANAGED_ASSET")
        assert first["current"]["availability"] == "NEEDS_CONFIRMATION"
        assert first["current"]["source"]["kind"] == "ADMIN_MANAGED"
        assert len(service.rows(S.imports)) == 0  # Managed metadata is not an original649 import.
        changed = data("TEST asset movement", description="SYNTHETIC additional transaction detail",
                       availability="VERIFIED", availability_evidence="TEST reviewed capability evidence")
        revised = app.revise(admin, created["id"], expected_version=created["version_id"],
                             data=changed, key=uuid4().hex)
        assert revised["ordinal"] == 2
        detailed = app.detail(operator, created["id"])
        assert detailed["source_revisions"][0] == original_revision
        assert len(detailed["source_revisions"]) == len(detailed["versions"]) == 2
        assert detailed["versions"][0]["data"] == normalize_data(original_data)
        assert Feature.model_validate(detailed["source_revisions"][-1]["data"]).name == changed["name"]
        assert app.revise(admin, created["id"], expected_version=revised["version_id"],
                          data=changed, key=uuid4().hex) == revised
        with pytest.raises(Denied, match="STALE_INPUT_VERSION"):
            app.revise(admin, created["id"], expected_version=created["version_id"],
                       data=changed, key=uuid4().hex)
        with pytest.raises(Denied, match="IDEMPOTENCY_TARGET_MISMATCH"):
            app.create(admin, kind="SYSTEM", data=data("TEST different"), key=command_key)


@pytest.mark.integration
def test_pg_existing_source_management_reuses_exact_revision_and_blocks_duplicate_mapping(asset_env):
    factory, files, operator, admin = asset_env
    with factory.begin() as session:
        service = CapabilityApplication(session, files)
        app, _, module = hierarchy(service, admin)
        memory = MemoryCatalog()
        raw = source(memory)["data"]
        root = service.add(S.features, external_id=raw["feature_id"])
        revision = service.add(S.revisions, feature_id=root["id"], ordinal=1,
                               digest=fingerprint(raw), data=raw)
        created = app.create(admin, kind="FEATURE", feature_id=root["id"], parent_id=module["id"],
            data=data(raw["name"], description=raw["description"]), key=uuid4().hex)
        detail = app.detail(operator, raw["feature_id"])
        assert detail["root"]["id"] == created["id"]
        assert detail["versions"][0]["source_revision_id"] == revision["id"]
        assert detail["source_revisions"] == [revision]
        with pytest.raises(Denied, match="ASSET_ALREADY_MANAGED"):
            app.create(admin, kind="FEATURE", feature_id=root["id"], parent_id=module["id"],
                data=data(raw["name"], description=raw["description"]), key=uuid4().hex)


@pytest.mark.integration
def test_pg_relationship_history_and_cycle_blocking(asset_env):
    factory, files, operator, admin = asset_env
    with factory.begin() as session:
        service = CapabilityApplication(session, files)
        app, system, a = hierarchy(service, admin)
        b = app.create(admin, kind="MODULE", parent_id=system["id"], data=data("TEST second module"),
                       key=uuid4().hex)
        a2 = app.revise(admin, a["id"], expected_version=a["version_id"], data=data("TEST asset stock",
            relations=[relation(b["id"])]), key=uuid4().hex)
        assert service.rows(D.relations, version_id=a2["version_id"])[0]["target_node_id"] == b["id"]
        with pytest.raises(Denied, match="ASSET_RELATION_CYCLE"):
            app.revise(admin, b["id"], expected_version=b["version_id"], data=data("TEST second module",
                relations=[relation(a["id"])]), key=uuid4().hex)
        history = app.detail(operator, a["id"])["versions"]
        assert history[0]["data"]["relations"] == [] and history[1]["data"]["relations"]


@pytest.mark.integration
def test_pg_api_session_origin_roles_and_reads_never_create_assets(asset_env, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.infrastructure.database import get_session
    from app.infrastructure.local_auth import hash_password
    from app.infrastructure.notice_store import SqlNoticeStore
    import app.api.dmp_assets as api
    factory, files, operator, admin = asset_env
    def sessions():
        with factory() as session:
            yield session
    app.dependency_overrides[get_session] = sessions
    monkeypatch.setattr(api, "application", lambda session:
        AssetCatalogApplication(CapabilityApplication(session, files)))
    origin = {"Origin": "http://localhost:3000"}
    payload = dict(kind="SYSTEM", data=data("TEST HTTP asset"), idempotency_key=uuid4().hex)
    try:
        with TestClient(app) as client:
            assert client.get("/capability/assets").status_code == 401
            assert client.get("/capability/assets", headers={"X-Role": "DATCO_ADMIN"}).status_code == 401
            with factory() as session:
                admin_name = SqlNoticeStore(session).get("actors", admin.id)["username"]
            assert client.post("/notice/session", json=dict(username=admin_name,
                password="test-only-password"), headers=origin).status_code == 200
            with factory() as session:
                before = {table.name: len(CapabilityApplication(session).rows(table))
                          for table in (D.nodes, D.versions, S.features, S.revisions)}
            page = client.get("/capability/assets")
            assert page.status_code == 200 and page.json()["total"] == 0
            assert client.post("/capability/assets", json=payload,
                headers={"Origin": "https://untrusted.example"}).status_code == 403
            with factory() as session:
                assert before == {table.name: len(CapabilityApplication(session).rows(table))
                                  for table in (D.nodes, D.versions, S.features, S.revisions)}
            created = client.post("/capability/assets", json=payload, headers=origin)
            assert created.status_code == 200
            assert client.post("/capability/assets", json=payload, headers=origin).json() == created.json()
            detail = client.get("/capability/assets/" + created.json()["id"])
            assert detail.status_code == 200 and len(detail.json()["versions"]) == 1
            assert client.get("/capability/assets?limit=10000").status_code == 422
            for role in ("DATCO_OPERATOR", "COMPANY_EDITOR", "COMPANY_APPROVER"):
                with factory.begin() as session:
                    username = "TEST_ASSET_" + uuid4().hex
                    SqlNoticeStore(session).add("actors", username=username, role=role,
                        password_hash=hash_password("test-only-password"))
                client.cookies.clear()
                assert client.post("/notice/session", json=dict(username=username,
                    password="test-only-password"), headers=origin).status_code == 200
                assert client.get("/capability/assets").status_code == (200 if role == "DATCO_OPERATOR" else 403)
                assert client.get("/capability/assets/" + created.json()["id"]).status_code == (
                    200 if role == "DATCO_OPERATOR" else 403)
                assert client.post("/capability/assets", json=payload, headers=origin).status_code == 403
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.parametrize("changed_node", ["system", "module"])
def test_parent_release_change_never_inherits_old_feature_verification(changed_node):
    memory = managed_memory()
    old = catalog_snapshot(memory)
    node = next(n for n in memory.tables[D.nodes.name] if n["id"] == changed_node)
    version = next(v for v in memory.tables[D.versions.name] if v["node_id"] == changed_node)
    node["current_ordinal"] = 2
    revised = deepcopy(version)
    revised.update(id=changed_node + "-v2", ordinal=2, digest="synthetic-new-release-digest")
    revised["data"]["release"] = "TEST-2"
    memory.tables[D.versions.name].append(revised)
    result = catalog_snapshot(memory)
    feature = result["features"][0]
    assert result["digest"] != old["digest"]
    assert feature["source_current"] is False
    assert feature["mapping_status"] == "PARENT_VERSION_CHANGED"
    assert feature["availability"] == "NEEDS_CONFIRMATION"
    assert feature["declared_availability"] == "VERIFIED"
    original = next(v for v in memory.tables[D.versions.name] if v["node_id"] == "asset-feature")
    assert original["parent_version_id"] == "module-v1"
    assert original["data"]["availability"] == "VERIFIED"


def test_relation_exact_target_version_is_bound_and_old_verified_record_is_preserved():
    memory = managed_memory()
    managed(memory, "MODULE", "target-module", "system")
    node_versions = {v["node_id"]: v for v in memory.tables[D.versions.name]}
    declared = relation("target-module", "INTEGRATION")
    declared.update(verified=True, evidence="TEST integration checked against exact target release")
    bound = bind_relation_versions(normalize_data(data(relations=[declared])), node_versions)
    assert bound["relations"][0]["target_version_id"] == "target-module-v1"
    wrong = deepcopy(bound)
    wrong["relations"][0]["target_version_id"] = "not-current-target"
    with pytest.raises(Denied, match="STALE_ASSET_RELATION_VERSION"):
        bind_relation_versions(wrong, node_versions)
    own = node_versions["module"]
    own["data"]["relations"] = bound["relations"]
    before = next(r for r in catalog_snapshot(memory)["modules"] if r["id"] == "module")
    assert before["relations"][0]["verified"] is True
    target = next(n for n in memory.tables[D.nodes.name] if n["id"] == "target-module")
    target["current_ordinal"] = 2
    changed = deepcopy(node_versions["target-module"])
    changed.update(id="target-module-v2", ordinal=2, digest="TEST-target-release-2")
    memory.tables[D.versions.name].append(changed)
    after = next(r for r in catalog_snapshot(memory)["modules"] if r["id"] == "module")
    assert after["relations"][0]["verified"] is False
    assert after["relations"][0]["declared_verified"] is True
    assert after["relations"][0]["current_valid"] is False
    assert after["relations"][0]["target_version_id"] == "target-module-v1"
    assert after["relations"][0]["target_current_version_id"] == "target-module-v2"
    assert after["data"]["relations"][0]["verified"] is True


@pytest.mark.integration
def test_pg_exact_parent_and_target_release_references_require_explicit_rebase(asset_env):
    factory, files, operator, admin = asset_env
    with factory.begin() as session:
        service = CapabilityApplication(session, files)
        app, system, module = hierarchy(service, admin)
        target = app.create(admin, kind="MODULE", parent_id=system["id"],
            data=data("TEST integration target"), key=uuid4().hex)
        original = data("TEST parent-sensitive function")
        declared = relation(target["id"], "INTEGRATION")
        declared.update(verified=True, evidence="TEST exact integration target checked")
        original["relations"] = [declared]
        feature = app.create(admin, kind="FEATURE", parent_id=module["id"], data=original, key=uuid4().hex)
        first = app.detail(operator, feature["id"])
        assert first["versions"][0]["parent_version_id"] == module["version_id"]
        assert first["versions"][0]["data"]["relations"][0]["target_version_id"] == target["version_id"]
        relation_row = service.rows(D.relations, version_id=feature["version_id"])[0]
        assert relation_row["target_version_id"] == target["version_id"]
        target2 = app.revise(admin, target["id"], expected_version=target["version_id"],
            data=data("TEST integration target", release="TEST-2"), key=uuid4().hex)
        stale = app.detail(operator, feature["id"])
        assert stale["current"]["relations"][0]["verified"] is False
        assert stale["versions"][0]["data"]["relations"][0]["verified"] is True
        stale_payload = deepcopy(first["versions"][0]["data"])
        with pytest.raises(Denied, match="STALE_ASSET_RELATION_VERSION"):
            app.revise(admin, feature["id"], expected_version=feature["version_id"],
                data=stale_payload, key=uuid4().hex)
        # Re-review is explicit; new target metadata is not automatically verified.
        stale_payload["relations"][0].update(target_version_id=target2["version_id"], verified=False, evidence="")
        reviewed = app.revise(admin, feature["id"], expected_version=feature["version_id"],
            data=stale_payload, key=uuid4().hex)
        parent2 = app.revise(admin, module["id"], expected_version=module["version_id"],
            data=data("TEST asset stock", release="TEST-2"), key=uuid4().hex)
        assert app.detail(operator, feature["id"])["current"]["source_current"] is False
        rebased = app.revise(admin, feature["id"], expected_version=reviewed["version_id"],
            data=stale_payload, key=uuid4().hex)
        final = app.detail(operator, feature["id"])
        assert final["current"]["source_current"] is True
        assert final["versions"][-1]["parent_version_id"] == parent2["version_id"]
        assert len(final["source_revisions"]) == 1
        assert rebased["ordinal"] == 3


@pytest.mark.parametrize("existing_kind,new_kind", [
    ("DEPENDENCY", "REPLACEMENT"), ("REPLACEMENT", "DEPENDENCY")])
def test_mixed_dependency_replacement_cycles_match_database_guard(existing_kind, new_kind):
    nodes = {"a": {"kind": "MODULE"}, "b": {"kind": "MODULE"}}
    original = relation("b", existing_kind)
    original["target_version_id"] = "b-v1"
    current = {"a": {"id": "a-v1", "data": {"relations": [original]}},
               "b": {"id": "b-v1", "data": {"relations": []}}}
    proposed = relation("a", new_kind)
    proposed["target_version_id"] = "a-v1"
    with pytest.raises(Denied, match="ASSET_RELATION_CYCLE"):
        validate_relations("b", "MODULE", [proposed], nodes, current)
    # Failed validation never rewrites the exact target release declaration.
    assert current["a"]["data"]["relations"][0]["target_version_id"] == "b-v1"
    assert proposed["target_version_id"] == "a-v1"
