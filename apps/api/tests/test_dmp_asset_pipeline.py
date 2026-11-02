"""Real API/Worker DMP-asset lineage in fresh runner-owned PostgreSQL schemas.

Only synthetic accounts and raw TEST asset metadata are prepared. Company facts,
analysis, reviews, confirmations, composition, matching and proposal decisions
all use the ordinary authenticated API/Worker, never pre-seeded result rows.
"""
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
from uuid import uuid4
from xml.etree import ElementTree
from zipfile import ZipFile

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi.testclient import TestClient
from pypdf import PdfReader
import pytest
from sqlalchemy import event, func, select
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.main import app
from app.company.application import CompanyApplication
from app.infrastructure.database import get_engine, get_session
from app.infrastructure.local_auth import hash_password
from app.infrastructure.notice_documents import LocalPrivateFiles
from app.infrastructure.notice_store import SqlNoticeStore
from app.infrastructure import capability_schema as K, dmp_asset_schema as D, proposal_schema as P
from isolation import require_test_database
from test_company_workflow import call
from test_mvp_analysis_lineage import (
    prepare_source, structure_and_confirm, reviewed_notice, review, finish,
)
from test_improvement_analysis import request
from v14_migration_chain import BEFORE_PROPOSAL, AFTER_COMPANY, load

pytestmark = pytest.mark.integration


def nonce():
    return str(uuid4())


@pytest.fixture
def pipeline_env(tmp_path, monkeypatch):
    """A truly empty catalog, independent of other tests' published services.

    Execute the real frozen migration chain, including deferred/invariant
    triggers. Do not use metadata.create_all or downgrade another test's schema.
    The outer isolated runner eventually removes its own disposable database.
    """
    require_test_database()
    schema = "test_dmp_pipeline_" + uuid4().hex
    engine = get_engine().execution_options(schema_translate_map={None: schema})
    def database_diagnostic(context):
        diagnostic = getattr(context.original_exception, "diag", None)
        if diagnostic:
            print("SYNTHETIC_PIPELINE_DATABASE_ERROR", diagnostic.sqlstate,
                  diagnostic.message_primary)
    event.listen(engine, "handle_error", database_diagnostic)
    migrations = (*BEFORE_PROPOSAL, "e863p0012026_proposal_production.py",
        "f974c0012026_company_workflow.py", *AFTER_COMPANY, "gh02a0012026_dmp_assets.py")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE SCHEMA " + schema)
        connection.exec_driver_sql("SET LOCAL search_path=" + schema + ",public")
        with Operations.context(MigrationContext.configure(connection)):
            for filename in migrations:
                load(filename).upgrade()
    factory = sessionmaker(bind=engine)
    # SQLAlchemy's schema_translate_map qualifies ORM tables, while the frozen
    # approval trigger also reads unqualified tables. Both must see this same
    # runner-owned schema, including in Worker and API transactions.
    @event.listens_for(factory, "after_begin")
    def transaction_schema(session, transaction, connection):
        connection.exec_driver_sql("SET LOCAL search_path=" + schema + ",public")
    files = LocalPrivateFiles(tmp_path / "synthetic-private")
    password, people, clients = "TEST-" + uuid4().hex, {}, {}
    with factory.begin() as session:
        for name, role in (("editor", "COMPANY_EDITOR"), ("operator", "DATCO_OPERATOR"),
                ("admin", "DATCO_ADMIN"), ("approver", "COMPANY_APPROVER"),
                ("other", "COMPANY_EDITOR"), ("foreign_operator", "DATCO_OPERATOR")):
            people[name] = SqlNoticeStore(session).add("actors",
                username="TEST_DMP_PIPELINE_" + name + "_" + uuid4().hex,
                role=role, password_hash=hash_password(password))
        assert session.scalar(select(func.count()).select_from(K.versions)) == 0
    previous_overrides = dict(app.dependency_overrides)
    def sessions():
        with factory() as session:
            yield session
    app.dependency_overrides[get_session] = sessions
    import app.api.company as company_api
    monkeypatch.setattr(company_api, "application", lambda session: CompanyApplication(session, files))
    try:
        for name, person in people.items():
            clients[name] = TestClient(app)
            response = clients[name].post("/notice/session",
                json={"username": person["username"], "password": password},
                headers={"Origin": get_settings().web_origin})
            assert response.status_code == 200
        yield dict(factory=factory, files=files, people=people, clients=clients, schema=schema)
    finally:
        for client in clients.values():
            client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        event.remove(engine, "handle_error", database_diagnostic)


def asset_data(name, *, verified=True, **extra):
    value = dict(name=name, description="SYNTHETIC TEST asset metadata, not an actual DATCO delivery claim.",
        role="TEST source role", release="TEST-1",
        availability="VERIFIED" if verified else "NEEDS_CONFIRMATION",
        availability_evidence="TEST administrator reviewed this synthetic source only" if verified else "")
    value.update(extra)
    return value


def create_asset(e, kind, data, parent=None):
    body = dict(kind=kind, data=data, idempotency_key=nonce())
    if parent is not None:
        body["parent_id"] = parent["id"]
    created = call(e, "admin", "/capability/assets", body)
    return dict(created, data=deepcopy(data))


def revise_asset(e, asset, **changes):
    data = dict(asset["data"], **changes)
    revised = call(e, "admin", "/capability/assets/" + asset["id"] + "/versions",
        dict(data=data, expected_version=asset["version_id"], idempotency_key=nonce()))
    return dict(revised, data=data)


def registered_assets(e, *, cross=False, include_document=False, unknown=False, dependency=False):
    """Create source metadata only via the real administrator routes."""
    system = create_asset(e, "SYSTEM", asset_data("TEST ERP " + nonce()[:8]))
    stock_module = create_asset(e, "MODULE", asset_data("TEST 입출고 재고 모듈"), system)
    second_system = (create_asset(e, "SYSTEM", asset_data("TEST 협업 " + nonce()[:8]))
                     if cross else system)
    document_module = None
    if include_document or dependency:
        document_module = create_asset(e, "MODULE", asset_data("TEST 문서 선행 모듈"), second_system)
        if cross or dependency:
            relation = dict(target_node_id=document_module["id"],
                target_version_id=document_module["version_id"],
                kind="DEPENDENCY" if dependency else "INTEGRATION",
                condition="TEST exact source identifier agreement and interface permission",
                verified=True, evidence="TEST exact target module integration review")
            stock_module = revise_asset(e, stock_module, relations=[relation])
    stock = create_asset(e, "FEATURE", asset_data("TEST 입출고 기록·재고 현황 조회",
        verified=not unknown, description="TEST 입고·출고 기록을 저장하고 재고 수량·현황을 조회합니다.",
        problems=["TEST 입출고 기록 및 재고 수량 확인 지연"],
        conditions=["TEST source identifiers have been checked"]), stock_module)
    document = None
    if include_document:
        document = create_asset(e, "FEATURE", asset_data("TEST 문서 기안",
            description="TEST 전자결재 문서 기안과 문서 조회"), document_module)
    return dict(system=system, module=stock_module, stock=stock,
                document_system=second_system, document_module=document_module, document=document)


def prepared(e, *, document_goal=False):
    item = prepare_source(e)
    if document_goal:
        # Explicit operator structuring + the real company's ACK, not an
        # inferred analysis claim or a direct database overwrite.
        item["values"].update(goal="문서 기안과 전자결재 업무를 개선하고 싶습니다.",
            to_be="문서 기안과 결재 기록을 조회합니다.",
            required_functions="입출고 기록과 재고 현황 조회 및 문서 기안")
    target = structure_and_confirm(e, item)
    return item, target


def generated(e, target, key=None):
    return call(e, "operator", "/capability/improvements/" + target["id"] + "/asset-solutions",
                dict(idempotency_key=key or nonce()))


def composition_data(run, alternative=None, *, reviewed=False):
    alternative = alternative or run["data"]["alternatives"][0]
    data = dict(source_mode="DMP_ASSET", name=alternative["name"],
        improvement_version_id=run["improvement_version_id"], capability_version_ids=[],
        basis=deepcopy(run["input"]["basis"]),
        asset_basis=dict(recommendation_id=run["id"], alternative_id=alternative["id"]),
        asset_selections=deepcopy(alternative["feature_selections"]),
        asset_integrations=deepcopy(alternative["integrations"]),
        asset_review_note="TEST operator explicitly reviewed exact source functions and this alternative",
        coverage=deepcopy(alternative["coverage"]), conditions=deepcopy(alternative["conditions"]),
        unresolved=deepcopy(alternative["unresolved"]), integrations=[], excluded_feature_revision_ids=[])
    if reviewed:
        assert all(row["feature_revision_ids"] for row in data["coverage"])
        for row in data["coverage"]:
            row.update(status="ADDRESSED", addressed_scope="TEST human reviewed scope: " + row["addressed_scope"],
                       unaddressed_scope="", missing_information=[])
        data["unresolved"] = []
    return data


def save_composition(e, data, previous=None):
    body = dict(data=data, idempotency_key=nonce())
    path = "/capability/compositions"
    if previous is not None:
        body["expected_version"] = previous["version_id"]
        path += "/" + previous["id"] + "/versions"
    return call(e, "operator", path, body)


def matching(e, saved, notice):
    return call(e, "operator", "/capability/matches", dict(
        composition_version_id=saved["version_id"], notice_id=notice["notice_id"],
        requirement_version_id=notice["requirement_version_id"], idempotency_key=nonce()))


def completion_items(e, item, match):
    preparation = call(e, "operator", "/capability/matches/" + match["candidate_id"] + "/proposal-preparation")
    evidence_id = item["values"]["evidence_ids"][0]
    assert any(p["id"] == evidence_id and p["confirmed"] and p["current_valid"]
               for p in preparation["review_evidence"])
    return [dict(task_id=task["id"], decision="CONFIRMED",
        note="TEST human checked this exact synthetic source item: " + task["label"],
        proof_ids=[evidence_id], notice_evidence_id=task.get("notice_evidence_id"))
        for task in preparation["review_tasks"]]


def propose_review(e, item, match, *, status=200):
    return call(e, "operator", "/capability/matches/" + match["candidate_id"] + "/review",
        dict(outcome="PROPOSABLE", note="TEST separate scope, company, supplier and notice review",
             completion_items=completion_items(e, item, match), idempotency_key=nonce()), status=status)


def count(e, table, **filters):
    with e["factory"]() as session:
        return session.scalar(select(func.count()).select_from(table).where(
            *(table.c[key] == value for key, value in filters.items())))


def test_zero_published_services_real_worker_to_asset_composition_mvp16_and_company_decision(
        pipeline_env, monkeypatch):
    e = pipeline_env
    assets = registered_assets(e)
    item, target = prepared(e)
    assert call(e, "operator", "/capability/catalog") == []
    assert count(e, K.versions) == 0
    assert sum(p["status"] == "NOT_CONFIGURED" for p in
               call(e, "operator", "/company/analysis/providers")["providers"]) == 4
    key = nonce()
    run = generated(e, target, key)
    assert generated(e, target, key)["id"] == generated(e, target)["id"] == run["id"]
    assert count(e, D.runs, improvement_version_id=target["id"]) == 1
    assert run["input"]["basis"] == item["basis"] and run["analysis_run_id"] == item["run"]["run"]["id"]
    assert run["data"]["candidates"] and run["current_valid"]
    alternative = next(a for a in run["data"]["alternatives"]
                       if a["kind"] == "SINGLE_MODULE" and
                       assets["stock"]["version_id"] in
                       {f["asset_version_id"] for f in a["feature_selections"]})
    assert all(row["status"] == "PARTIAL" and row["role"] and row["addressed_scope"]
               and row["unaddressed_scope"] and row["missing_information"]
               for row in alternative["coverage"])
    original_run = deepcopy(run["data"])
    pending = save_composition(e, composition_data(run, alternative))
    notice = reviewed_notice(e, monkeypatch)
    pending_match = matching(e, pending, notice)
    propose_review(e, item, pending_match, status=409)
    confirmed_data = composition_data(run, alternative, reviewed=True)
    saved = save_composition(e, confirmed_data, pending)
    detail = call(e, "operator", "/capability/compositions/" + saved["id"])
    assert len(detail["versions"]) == 2 and detail["versions"][0]["id"] == pending["version_id"]
    assert detail["versions"][-1]["data"]["asset_features"][0]["source"]["kind"] == "ADMIN_MANAGED"
    assert count(e, K.versions) == 0 and count(e, K.composition_links, version_id=saved["version_id"]) == 0
    assert count(e, D.composition_features, version_id=saved["version_id"]) == len(confirmed_data["asset_selections"])
    match = matching(e, saved, notice)
    assert call(e, "operator", "/capability/matches/" + match["candidate_id"])["current_valid"]
    call(e, "operator", "/proposal", dict(candidate_id=match["candidate_id"], title="TEST missing match review",
        template_version="MVP_16", idempotency_key=nonce()), status=409)
    checked = propose_review(e, item, match)
    call(e, "operator", "/proposal", dict(candidate_id=match["candidate_id"], title="TEST legacy incompatible",
        template_version="LEGACY_11", idempotency_key=nonce()), status=422)
    created = call(e, "operator", "/proposal", dict(candidate_id=match["candidate_id"],
        title="TEST 원천 기술자산 자동 조합 제안", template_version="MVP_16", idempotency_key=nonce()))
    version_id = created["version_id"]
    proposal = call(e, "operator", "/proposal/versions/" + version_id)
    assert len(proposal["sections"]) == 16 and proposal["manifest"]["capability_versions"] == []
    refs = proposal["manifest"]["refs"]
    assert refs["analysis_source_version_id"] == item["source"]["id"]
    assert refs["improvement_version_id"] == target["id"]
    assert refs["analysis_run_id"] == item["run"]["run"]["id"]
    assert refs["analysis_review_ids"] == [item["review"]["id"]]
    assert refs["composition_version_id"] == saved["version_id"] and refs["match_review_id"] == checked["id"]
    assert refs["asset_recommendation_id"] == run["id"]
    assert assets["stock"]["version_id"] in refs["asset_version_ids"]
    assert assets["module"]["version_id"] in refs["asset_version_ids"]
    assert assets["system"]["version_id"] in refs["asset_version_ids"]
    assert all(row["capability_version_id"] is None for row in
               proposal["manifest"]["input"]["composition"]["coverage"])
    call(e, "operator", "/proposal/versions/" + version_id + "/export",
        dict(kind="PDF", idempotency_key=nonce()), status=409)
    assert count(e, P.requests, version_id=version_id) == 0
    call(e, "operator", "/proposal/versions/" + version_id + "/review",
        dict(confirmed=True, note="TEST all sixteen sections explicitly reviewed", idempotency_key=nonce()))
    outputs = []
    for kind in ("DOCX", "PDF"):
        receipt = call(e, "operator", "/proposal/versions/" + version_id + "/export",
                       dict(kind=kind, idempotency_key=nonce()))
        response = e["clients"]["operator"].get("/proposal/files/" + receipt["id"] + "/download")
        assert response.status_code == 200 and sha256(response.content).hexdigest() == receipt["digest"]
        if kind == "DOCX":
            text = "".join(ElementTree.fromstring(ZipFile(BytesIO(response.content)).read("word/document.xml")).itertext())
        else:
            text = "".join(page.extract_text() for page in PdfReader(BytesIO(response.content)).pages)
        compact = "".join(text.split())
        for value in (version_id, target["id"], item["source"]["id"], run["id"], assets["stock"]["version_id"]):
            assert value in compact
        assert "".join(assets["stock"]["data"]["name"].split()) in compact
        assert all("".join(section["heading"].split()) in compact for section in proposal["sections"])
        call(e, "approver", "/proposal/files/" + receipt["id"] + "/download", status=404)
        outputs.append(receipt)
    assert count(e, P.requests, version_id=version_id) == 0
    send_body = dict(idempotency_key=nonce())
    sent = call(e, "operator", "/proposal/versions/" + version_id + "/approval", send_body)
    assert call(e, "operator", "/proposal/versions/" + version_id + "/approval", send_body) == sent
    inbox = call(e, "approver", "/proposal/inbox/" + item["company"]["id"])
    assert len(inbox) == 1 and inbox[0]["version_id"] == version_id
    assert "manifest" not in inbox[0]
    for output in outputs:
        response = e["clients"]["approver"].get("/proposal/files/" + output["id"] + "/download")
        assert response.status_code == 200 and sha256(response.content).hexdigest() == output["digest"]
        call(e, "other", "/proposal/files/" + output["id"] + "/download", status=404)
    decision_body = dict(outcome="REVISION_REQUEST", reason="TEST exact source module scope amendment requested",
                         idempotency_key=nonce())
    decision = call(e, "approver", "/proposal/approvals/" + sent["id"] + "/decision", decision_body)
    assert call(e, "approver", "/proposal/approvals/" + sent["id"] + "/decision", decision_body) == decision
    assert decision["outcome"] == "REVISION_REQUEST" and count(e, P.decisions, version_id=version_id) == 1
    assert call(e, "operator", "/proposal/versions/" + version_id) == proposal
    assert call(e, "operator", "/capability/asset-solutions/" + run["id"])["data"] == original_run
    # Last, a new source release makes future work stale without changing the
    # already delivered proposal or the old generation snapshot.
    revise_asset(e, assets["stock"], description="TEST revised 입출고 기록·재고 조회 source", release="TEST-2")
    stale = call(e, "operator", "/capability/asset-solutions/" + run["id"])
    assert not stale["current_valid"] and "ASSET_CATALOG_CHANGED" in stale["stale_reasons"]
    assert stale["data"] == original_run
    assert not call(e, "operator", "/capability/matches/" + match["candidate_id"])["current_valid"]
    assert call(e, "operator", "/proposal/versions/" + version_id) == proposal


def test_no_assets_no_services_is_an_immutable_zero_candidate_run(pipeline_env):
    e = pipeline_env
    item, target = prepared(e)
    assert call(e, "operator", "/capability/catalog") == []
    assert call(e, "operator", "/capability/assets")["total"] == 0
    before = count(e, D.runs)
    assert call(e, "operator", "/capability/improvements/" + target["id"] + "/asset-solutions") == []
    assert count(e, D.runs) == before
    run = generated(e, target)
    assert run["data"]["status"] == "NO_SOLUTION"
    assert run["data"]["alternatives"] == [] and run["data"]["candidates"] == []
    assert run["data"]["uncovered_demands"] and run["current_valid"]
    assert run["input"]["basis"] == item["basis"]
    assert generated(e, target)["id"] == run["id"]
    assert len(call(e, "operator", "/capability/improvements/" + target["id"] + "/asset-solutions")) == 1
    assert count(e, K.compositions) == 0 and count(e, P.requests) == 0


def test_roles_company_scope_exact_demand_and_forged_snapshots_are_enforced(pipeline_env):
    e = pipeline_env
    assets = registered_assets(e, include_document=True)
    unrelated_module = create_asset(e, "MODULE", asset_data("TEST 근태 전용 모듈"), assets["system"])
    unrelated = create_asset(e, "FEATURE", asset_data("TEST 출퇴근 근태 조회",
        description="TEST 근태와 휴가 조회"), unrelated_module)
    item, target = prepared(e, document_goal=True)
    run = generated(e, target)
    alt = next(a for a in run["data"]["alternatives"] if len(a["feature_selections"]) > 1)
    data = composition_data(run, alt)
    path = "/capability/improvements/" + target["id"] + "/asset-solutions"
    for who in ("editor", "approver", "admin", "other"):
        call(e, who, path, dict(idempotency_key=nonce()), status=403)
        call(e, who, "/capability/asset-solutions/" + run["id"], status=403)
    call(e, "foreign_operator", path, dict(idempotency_key=nonce()), status=404)
    call(e, "foreign_operator", "/capability/asset-solutions/" + run["id"], status=404)
    with TestClient(app) as client:
        assert client.get("/capability/asset-solutions/" + run["id"],
                          headers={"X-Role": "DATCO_OPERATOR"}).status_code == 401
    good_body = dict(data=deepcopy(data), idempotency_key=nonce())
    response = e["clients"]["operator"].post("/capability/compositions", json=good_body,
                                            headers={"Origin": "https://untrusted.invalid"})
    assert response.status_code == 403 and count(e, K.compositions) == 0

    bad = deepcopy(data)
    current = call(e, "operator", "/capability/assets/" + unrelated["id"])["current"]
    bad["asset_selections"].append(dict(feature_revision_id=current["revision_id"],
        asset_version_id=current["asset_version_id"], system_version_id=current["system_version_id"],
        module_version_id=current["module_version_id"], role="TEST unsupported candidate forgery"))
    call(e, "operator", "/capability/compositions", dict(data=bad, idempotency_key=nonce()), status=409)

    stock = next(c for c in run["data"]["candidates"] if c["id"] == assets["stock"]["id"])
    document = next(c for c in run["data"]["candidates"] if c["id"] == assets["document"]["id"])
    stock_row = next(row for row in data["coverage"] if row["demand_id"] in stock["demand_ids"]
                     and row["demand_id"] not in document["demand_ids"])
    bad = deepcopy(data)
    next(row for row in bad["coverage"] if row["demand_id"] == stock_row["demand_id"])["feature_revision_ids"] = [document["revision_id"]]
    call(e, "operator", "/capability/compositions", dict(data=bad, idempotency_key=nonce()), status=409)

    for forgery in ("EVIDENCE", "VERSION", "ALTERNATIVE", "COVERAGE_OMITTED", "DUPLICATE"):
        bad = deepcopy(data)
        if forgery == "EVIDENCE":
            bad["coverage"][0]["evidence_refs"][0]["quote"] = "TEST invented source quote"
        elif forgery == "VERSION":
            bad["asset_selections"][0]["module_version_id"] = nonce()
        elif forgery == "ALTERNATIVE":
            bad["asset_basis"]["alternative_id"] = "TEST nonexistent alternative"
        elif forgery == "COVERAGE_OMITTED":
            bad["coverage"] = bad["coverage"][:-1]
        else:
            bad["asset_selections"].append(deepcopy(bad["asset_selections"][0]))
        call(e, "operator", "/capability/compositions", dict(data=bad, idempotency_key=nonce()), status=409)
    assert count(e, K.compositions) == 0

    # These fields are server-owned even if a malicious client supplies copies.
    data.update(asset_catalog_digest="TEST forged digest", asset_generation_rule="TEST forged rule",
                asset_features=[dict(name="TEST forged server snapshot")])
    saved = save_composition(e, data)
    persisted = call(e, "operator", "/capability/compositions/" + saved["id"])["versions"][-1]["data"]
    assert persisted["asset_catalog_digest"] == run["input"]["catalog_digest"]
    assert persisted["asset_generation_rule"] == run["rule_version"]
    assert "TEST forged server snapshot" not in json.dumps(persisted)
    assert {f["id"] for f in persisted["asset_features"]} == {assets["stock"]["id"], assets["document"]["id"]}

    other_item, other_target = prepared(e)
    other_run = generated(e, other_target)
    bad = deepcopy(data)
    bad["asset_basis"] = dict(recommendation_id=other_run["id"],
                             alternative_id=other_run["data"]["alternatives"][0]["id"])
    call(e, "operator", "/capability/compositions", dict(data=bad, idempotency_key=nonce()), status=409)
    assert count(e, K.compositions) == 1 and count(e, D.runs, improvement_version_id=target["id"]) == 1


@pytest.mark.parametrize("change", ["FEATURE", "MODULE", "COMPANY", "REVIEW", "REANALYSIS", "NEW_DRAFT"])
def test_source_company_review_and_version_changes_stale_only_new_work_preserving_history(pipeline_env, change):
    e = pipeline_env
    assets = registered_assets(e)
    item, target = prepared(e)
    run = generated(e, target)
    data = composition_data(run)
    saved = save_composition(e, data)
    frozen = deepcopy(run["data"])
    previous = call(e, "operator", "/capability/compositions/" + saved["id"])["versions"][0]
    if change == "FEATURE":
        revise_asset(e, assets["stock"], availability="RETIRED", availability_evidence="TEST retired")
    elif change == "MODULE":
        revise_asset(e, assets["module"], release="TEST-2")
    elif change == "COMPANY":
        call(e, "editor", "/company/" + item["company"]["id"] + "/profile",
             dict(data=dict(item["profile"], overview="TEST new company input"), expected_ordinal=1))
    elif change == "REVIEW":
        review(e, item["candidate"], decision="NEEDS_CHECK", ordinal=1)
    elif change == "REANALYSIS":
        request(e, item["source"]["id"])
        assert finish(e, item["source"]["id"])["run"]["id"] != item["run"]["run"]["id"]
    else:
        call(e, "editor", "/company/" + item["company"]["id"] + "/improvements",
             dict(data=dict(item["values"], title="TEST new unsubmitted draft"),
                  improvement_id=item["source"]["improvement_id"], expected_ordinal=2))
    stale = call(e, "operator", "/capability/asset-solutions/" + run["id"])
    assert not stale["current_valid"] and stale["stale_reasons"]
    assert stale["data"] == frozen
    call(e, "operator", "/capability/compositions/" + saved["id"] + "/versions",
         dict(data=data, expected_version=saved["version_id"], idempotency_key=nonce()), status=409)
    assert call(e, "operator", "/capability/compositions/" + saved["id"])["versions"] == [previous]
    if change in ("FEATURE", "MODULE"):
        newer = generated(e, target)
        assert newer["id"] != run["id"] and newer["data"]["alternatives"] == []
        assert count(e, D.runs, improvement_version_id=target["id"]) == 2


def test_registered_exact_cross_system_integration_cannot_be_forged_or_removed_to_promote(
        pipeline_env, monkeypatch):
    e = pipeline_env
    assets = registered_assets(e, cross=True, include_document=True)
    item, target = prepared(e, document_goal=True)
    run = generated(e, target)
    alt = next(a for a in run["data"]["alternatives"] if a["kind"] == "CROSS_SYSTEM")
    assert alt["integrations"] and all(i["verification"] == "VERIFIED" for i in alt["integrations"])
    data = composition_data(run, alt, reviewed=True)
    for change in ("EVIDENCE", "CONDITION"):
        bad = deepcopy(data)
        if change == "EVIDENCE":
            bad["asset_integrations"][0]["evidence_note"] = "TEST forged interface review"
        else:
            bad["asset_integrations"][0]["prerequisites"] = []
        call(e, "operator", "/capability/compositions", dict(data=bad, idempotency_key=nonce()), status=409)
    removed = deepcopy(data)
    removed["asset_integrations"] = []
    saved = save_composition(e, removed)
    notice = reviewed_notice(e, monkeypatch)
    blocked = matching(e, saved, notice)
    propose_review(e, item, blocked, status=409)
    corrected = save_composition(e, data, saved)
    matched = matching(e, corrected, notice)
    propose_review(e, item, matched)
    # The exact registered target revision is not silently advanced.
    before = call(e, "admin", "/capability/assets/" + assets["module"]["id"])
    revise_asset(e, assets["document_module"], release="TEST-2")
    current = call(e, "admin", "/capability/assets/" + assets["module"]["id"])
    assert current["versions"] == before["versions"]
    assert current["current"]["relations"][0]["verified"] is False
    assert current["current"]["relations"][0]["declared_verified"] is True
    assert not call(e, "operator", "/capability/matches/" + matched["candidate_id"])["current_valid"]
    assert call(e, "operator", "/capability/asset-solutions/" + run["id"])["data"] == run["data"]


def test_missing_registered_dependency_cannot_be_cleared_by_reviewing_coverage_only(
        pipeline_env, monkeypatch):
    e = pipeline_env
    registered_assets(e, dependency=True)
    item, target = prepared(e)
    run = generated(e, target)
    alt = next(a for a in run["data"]["alternatives"] if a["kind"] == "SINGLE_MODULE")
    data = composition_data(run, alt, reviewed=True)
    assert data["asset_integrations"] == []
    saved = save_composition(e, data)
    notice = reviewed_notice(e, monkeypatch)
    matched = matching(e, saved, notice)
    propose_review(e, item, matched, status=409)
