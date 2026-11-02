"""Scoped persistence and validation for generated DMP technical alternatives.

No catalog publication, company confirmation or delivery happens here.
"""
from copy import deepcopy
from hashlib import sha256
from sqlalchemy import text
from app.notice.domain import Denied
from app.capability.application import fingerprint, frozen_json
from app.capability.recommendations import read_analysis, validate_basis, authority_basis
from app.infrastructure import dmp_asset_schema as D, capability_schema as S

REFERENCE_FIELDS = ("feature_revision_id", "asset_version_id", "system_version_id", "module_version_id")


def lock_catalog(service):
    # Same order as the existing approved inventory import and all asset writers.
    for value in (b"DATCO_DMP_INVENTORY", b"DATCO_DMP_ASSETS"):
        key = int.from_bytes(sha256(value).digest()[:8], "big", signed=True)
        service.session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})


def catalog(service):
    from app.capability.asset_catalog import catalog_snapshot
    return catalog_snapshot(service)


def is_asset(data):
    return data.get("source_mode", "CAPABILITY") == "DMP_ASSET"


def references(feature):
    return dict(feature_revision_id=feature["revision_id"],
                asset_version_id=feature.get("asset_version_id"),
                system_version_id=feature.get("system_version_id"),
                module_version_id=feature.get("module_version_id"))


def run_current(service, actor, row, context=None):
    context = context or service.context(actor, row["improvement_version_id"], require_current=False)
    reasons = []
    if context.get("current_valid") is not True or fingerprint(frozen_json(context)) != fingerprint(row["input"]["context"]):
        reasons.append("COMPANY_INPUT_CHANGED")
    try:
        validate_basis(service, actor, context, row["input"]["basis"])
    except Denied as exc:
        if exc.status in (403, 404, 503):
            raise
        reasons.append("ANALYSIS_OR_REVIEW_CHANGED")
    if catalog(service)["digest"] != row["input"]["catalog_digest"]:
        reasons.append("ASSET_CATALOG_CHANGED")
    from app.capability.asset_solutions import VERSION
    if row["rule_version"] != VERSION:
        reasons.append("SOLUTION_RULE_CHANGED")
    return reasons


def detail(service, actor, key):
    service.operator(actor)
    row = service.get(D.runs, key)
    context = service.context(actor, row["improvement_version_id"], require_current=False)
    if context["company_id"] != row["company_id"]:
        raise Denied("OBJECT_NOT_FOUND", 404)
    reasons = run_current(service, actor, row, context)
    return dict(row, current_valid=not reasons, stale_reasons=reasons)


def listing(service, actor, version_id):
    context = service.context(actor, version_id, require_current=False)
    rows = service.rows(D.runs, improvement_version_id=version_id)
    return [detail(service, actor, r["id"]) for r in sorted(rows, key=lambda r: (r["created_at"], r["id"]), reverse=True)
            if r["company_id"] == context["company_id"]]


def generate(service, actor, version_id, key):
    service.context(actor, version_id)
    def execute():
        lock_catalog(service)
        context = service.context(actor, version_id)
        basis, reviewed, limits = read_analysis(service, actor, context)
        limits = [("규칙 기반 원천 기술자산 후보입니다. 제공·적용성·공고 자격 확정은 아닙니다."
                   if v == "규칙 기반 발행 서비스 검색 후보입니다. 적용성·공고 자격 확정은 아닙니다." else v) for v in limits]
        if not basis.get("run_id") or not basis.get("review_ids"):
            raise Denied("ANALYSIS_REVIEW_REQUIRED")
        reviewed = validate_basis(service, actor, context, basis)
        basis = authority_basis(service, actor, context, basis)
        source = catalog(service)
        from app.capability.asset_solutions import VERSION, generate as build
        manifest = frozen_json(dict(context=context, basis=basis, catalog_digest=source["digest"]))
        digest = fingerprint(manifest)
        existing = service.rows(D.runs, improvement_version_id=version_id, input_digest=digest, rule_version=VERSION)
        if existing:
            return {"id": existing[0]["id"]}
        result = build(context, source, reviewed=reviewed, basis=basis, limits=limits)
        row = service.add(D.runs, company_id=context["company_id"], improvement_version_id=version_id,
                          analysis_run_id=basis["run_id"], actor_id=actor.id, input_digest=digest,
                          rule_version=VERSION, input=manifest, data=frozen_json(result))
        service.record(actor, "GENERATE_DMP_SOLUTIONS", recommendation_id=row["id"],
                       company_id=context["company_id"], improvement_version_id=version_id)
        return {"id": row["id"]}
    # Receipt stores the immutable result, while currentness is always recalculated.
    result = service.command(actor, key, ["DMP_ASSET_SOLUTIONS", version_id], execute)
    return detail(service, actor, result["id"])


def current(service, data):
    """Internal exact frozen-ref check. Does not grant catalog access to company actors."""
    if not is_asset(data):
        return True
    source = catalog(service)
    if source["digest"] != data.get("asset_catalog_digest"):
        return False
    indexed = {f["revision_id"]: f for f in source["features"]}
    for selected in data.get("asset_selections", []):
        feature = indexed.get(selected["feature_revision_id"])
        if feature is None or feature.get("source_current") is False or feature.get("availability") in ("UNAVAILABLE", "RETIRED"):
            return False
        if any(selected.get(k) != references(feature)[k] for k in REFERENCE_FIELDS):
            return False
    return bool(data.get("asset_selections"))


def validate(service, actor, context, data):
    lock_catalog(service)
    if not is_asset(data):
        raise Denied("INVALID_COMPOSITION_SOURCE", 422)
    if data.get("capability_version_ids") or data.get("integrations") or data.get("excluded_feature_revision_ids"):
        raise Denied("INVALID_COMPOSITION_SOURCE", 422)
    if not data.get("name", "").strip() or not data.get("asset_review_note", "").strip():
        raise Denied("REQUIRED_DATA_MISSING")
    basis = data.get("asset_basis", {})
    row = detail(service, actor, basis.get("recommendation_id", ""))
    if row["improvement_version_id"] != context["improvement_version_id"] or row["company_id"] != context["company_id"]:
        raise Denied("TARGET_VERSION_MISMATCH")
    if not row["current_valid"]:
        raise Denied("STALE_INPUT_VERSION")
    alternative = next((a for a in row["data"]["alternatives"] if a["id"] == basis.get("alternative_id")), None)
    if alternative is None:
        raise Denied("TARGET_VERSION_MISMATCH")
    if data.get("basis") != row["input"]["basis"]:
        raise Denied("INVALID_ANALYSIS_BASIS", 422)
    validate_basis(service, actor, context, data["basis"])
    source = catalog(service)
    indexed = {f["revision_id"]: f for f in source["features"]}
    selections = data.get("asset_selections", [])
    ids = [s["feature_revision_id"] for s in selections]
    if not ids or len(ids) != len(set(ids)):
        raise Denied("REQUIRED_DATA_MISSING")
    candidates = {f["revision_id"]: f for f in row["data"]["candidates"]}
    if not set(ids) <= set(candidates):
        raise Denied("UNSUPPORTED_ASSET_DEMAND")
    chosen = []
    for selected in selections:
        feature = indexed.get(selected["feature_revision_id"])
        if feature is None or feature.get("source_current") is False:
            raise Denied("STALE_INPUT_VERSION")
        if feature["availability"] in ("UNAVAILABLE", "RETIRED"):
            raise Denied("ASSET_NOT_AVAILABLE")
        if any(selected.get(k) != references(feature)[k] for k in REFERENCE_FIELDS):
            raise Denied("TARGET_VERSION_MISMATCH")
        if not selected.get("role", "").strip():
            raise Denied("REQUIRED_DATA_MISSING")
        chosen.append(feature)
    demands = {d["id"]: d for d in row["data"]["demands"]}
    seen = set()
    for item in data.get("coverage", []):
        demand = demands.get(item.get("demand_id"))
        if demand is None or item["requirement"] != demand["text"] or item.get("capability_version_id") is not None:
            raise Denied("TARGET_VERSION_MISMATCH")
        if not item.get("evidence_refs") or any(ev not in demand["evidence"] for ev in item["evidence_refs"]):
            raise Denied("REQUIRED_EVIDENCE_MISSING")
        if item["demand_id"] in seen or not set(item["feature_revision_ids"]) <= set(ids):
            raise Denied("TARGET_VERSION_MISMATCH")
        seen.add(item["demand_id"])
        if any(item["demand_id"] not in candidates[revision]["demand_ids"] for revision in item["feature_revision_ids"]):
            raise Denied("UNSUPPORTED_ASSET_DEMAND")
        status = item.get("status")
        addressed = bool(item["addressed_scope"].strip())
        unresolved = bool(item["unaddressed_scope"].strip() or item["missing_information"])
        if (status not in ("ADDRESSED", "PARTIAL", "UNRESOLVED") or not item.get("role", "").strip()
                or status == "ADDRESSED" and (not addressed or unresolved or not item["feature_revision_ids"])
                or status == "PARTIAL" and (not addressed or not unresolved or not item["feature_revision_ids"])
                or status == "UNRESOLVED" and (addressed or not unresolved)):
            raise Denied("INVALID_COVERAGE_STATUS", 422)
        if status == "ADDRESSED" and any(indexed[v]["availability"] != "VERIFIED" for v in item["feature_revision_ids"]):
            raise Denied("ASSET_AVAILABILITY_UNVERIFIED")
    expected = {d["id"] for d in demands.values() if d["kind"] != "CONSTRAINT"}
    if not expected <= seen:
        raise Denied("MISSING_REQUIRED_INFORMATION")
    allowed = {f.get(k) for f in chosen for k in ("id", "feature_id", "system_id", "module_id")} - {None}
    parent_items = {p["id"]: p for p in [*source.get("systems", []), *source.get("modules", [])]}
    relation_sources = []
    for feature in chosen:
        for key in ("id", "feature_id"):
            if feature.get(key):
                relation_sources.append((feature[key], feature.get("relations", [])))
        for key in ("system_id", "module_id"):
            parent = parent_items.get(feature.get(key))
            if parent:
                relation_sources.append((parent["id"], parent.get("relations", parent.get("data", {}).get("relations", []))))
    current_versions = {p["id"]: p.get("version_id") for p in [*parent_items.values(), *chosen]}
    links_seen = set()
    for link in data.get("asset_integrations", []):
        pair = (link["from_asset_id"], link["to_asset_id"])
        if pair[0] == pair[1] or not set(pair) <= allowed or pair in links_seen:
            raise Denied("TARGET_VERSION_MISMATCH")
        links_seen.add(pair)
        if not link["data"].strip() or not link["workflow"].strip() or not link["uncertainty"].strip():
            raise Denied("REQUIRED_DATA_MISSING")
        if link["verification"] == "VERIFIED":
            valid = any(r["kind"] == "INTEGRATION" and r["verified"] and r.get("current_valid") is not False
                        and r["target_node_id"] == pair[1] and r.get("target_version_id") is not None
                        and r["target_version_id"] == current_versions.get(pair[1])
                        and r["evidence"] == link["evidence_note"] and r["condition"] in link["prerequisites"]
                        for source_id, relations in relation_sources if source_id == pair[0] for r in relations)
            if not valid:
                raise Denied("UNVERIFIED_ASSET_INTEGRATION")
    # These are server-owned snapshots; supplied copies are ignored/replaced.
    data["asset_catalog_digest"] = source["digest"]
    data["asset_features"] = deepcopy(chosen)
    data["asset_generation_rule"] = row["rule_version"]
    return row


def save(service, actor, data, key, composition_id=None, expected_version=None):
    context = service.context(actor, data["improvement_version_id"], require_current=False)
    if composition_id:
        prior = service.get(S.compositions, composition_id)
        if prior["company_id"] != context["company_id"]:
            raise Denied("OBJECT_NOT_FOUND", 404)
    original = deepcopy(data)
    def execute():
        # Global asset lock precedes the composition root on every new asset path.
        lock_catalog(service)
        context = service.context(actor, data["improvement_version_id"])
        row = validate(service, actor, context, data)
        if composition_id:
            root = service.get(S.compositions, composition_id, True)
            previous = service.get(S.composition_versions, expected_version)
            if root["company_id"] != context["company_id"]:
                raise Denied("OBJECT_NOT_FOUND", 404)
            if previous["composition_id"] != root["id"] or previous["ordinal"] != root["current_ordinal"]:
                raise Denied("STALE_INPUT_VERSION")
            ordinal = root["current_ordinal"] + 1
            from sqlalchemy import update
            service.session.execute(update(S.compositions).where(S.compositions.c.id == root["id"]).values(current_ordinal=ordinal))
        else:
            root = service.add(S.compositions, company_id=context["company_id"], current_ordinal=1)
            ordinal = 1
        version = service.add(S.composition_versions, composition_id=root["id"], ordinal=ordinal,
                              improvement_version_id=context["improvement_version_id"], context=frozen_json(context),
                              data=frozen_json(data), actor_id=actor.id)
        for selected in data["asset_selections"]:
            service.add(D.composition_features, version_id=version["id"], **selected)
        service.add(D.composition_contexts, version_id=version["id"], recommendation_id=row["id"],
                    alternative_id=data["asset_basis"]["alternative_id"], review_note=data["asset_review_note"],
                    catalog_digest=data["asset_catalog_digest"])
        service.record(actor, "REVIEW_AND_SAVE_DMP_COMPOSITION", version_id=version["id"],
                       recommendation_id=row["id"], note=data["asset_review_note"])
        return dict(id=root["id"], version_id=version["id"], ordinal=ordinal)
    return service.command(actor, key, ["DMP_ASSET_COMPOSITION", composition_id, expected_version, original], execute)


def _registered_integration_options(features, parents):
    """Known interface choices between the final selected module groups.

    The original alternative is not the final selection after feature additions
    or module replacement. Reuse the generator's registered-relation projection,
    but do not synthesize its unknown spanning links here: an unregistered pair
    does not establish either a required interface or an independent exemption.
    Multiple registered directions/interfaces remain choices for the same pair.
    """
    from app.capability.asset_solutions import _relations
    modules = {}
    aliases = {}
    for feature in features:
        modules.setdefault(feature["module_id"], []).append(feature)
        owner = feature.get("id") or feature["feature_id"]
        aliases[owner] = {owner, feature["feature_id"]}
    keys = sorted(modules)
    requirements = []
    for index, left in enumerate(keys):
        for right in keys[index + 1:]:
            relations = [*_relations(modules[left], modules[right], parents),
                         *_relations(modules[right], modules[left], parents)]
            options = {(alias, relation["target_node_id"])
                for relation in relations if relation["kind"] == "INTEGRATION"
                for alias in aliases.get(relation["from_asset_id"], {relation["from_asset_id"]})}
            if options:
                requirements.append(frozenset(options))
    return requirements


def promotion_blockers(service, data):
    if not is_asset(data):
        return []
    blockers = []
    if not current(service, data):
        blockers.append("STALE_INPUT_VERSION")
    if any(f["availability"] != "VERIFIED" for f in data.get("asset_features", [])):
        blockers.append("ASSET_AVAILABILITY_UNVERIFIED")
    if any(c.get("status") != "ADDRESSED" for c in data.get("coverage", [])) or data.get("unresolved"):
        blockers.append("ASSET_SCOPE_REVIEW_REQUIRED")
    if any(i["verification"] != "VERIFIED" for i in data.get("asset_integrations", [])):
        blockers.append("ASSET_INTEGRATION_UNVERIFIED")
    features = data.get("asset_features", [])
    selected_ids = {f.get(k) for f in features for k in ("id", "feature_id", "system_id", "module_id")} - {None}
    run = service.get(D.runs, data["asset_basis"]["recommendation_id"])
    alternative = next((a for a in run["data"]["alternatives"] if a["id"] == data["asset_basis"]["alternative_id"]), None)
    required_pairs = {(i["from_asset_id"], i["to_asset_id"]) for i in alternative["integrations"]
                      if {i["from_asset_id"], i["to_asset_id"]} <= selected_ids} if alternative else set()
    actual_pairs = {(i["from_asset_id"], i["to_asset_id"]) for i in data.get("asset_integrations", [])}
    if not alternative or not required_pairs <= actual_pairs:
        blockers.append("ASSET_INTEGRATION_REVIEW_REQUIRED")
    source = catalog(service)
    parents = {p["id"]: p for p in [*source.get("systems", []), *source.get("modules", [])]}
    # A single-module alternative has no original pairs. Adding/replacing a
    # module must nevertheless review a known registered interface in the final
    # selection. validate() already checks exact version/evidence for VERIFIED
    # links; an explicit UNVERIFIED working draft is still allowed to save.
    if any(not options.intersection(actual_pairs)
           for options in _registered_integration_options(features, parents)):
        blockers.append("ASSET_INTEGRATION_REVIEW_REQUIRED")
    relation_sets = [f.get("relations", []) for f in features]
    relation_sets.extend(p.get("relations", p.get("data", {}).get("relations", []))
                         for key,p in parents.items() if key in selected_ids)
    for relations in relation_sets:
        for relation in relations:
            if relation["kind"] != "DEPENDENCY":
                continue
            if relation["target_node_id"] not in selected_ids:
                blockers.append("ASSET_DEPENDENCY_MISSING")
            elif not relation["verified"] or relation.get("current_valid") is False:
                blockers.append("ASSET_DEPENDENCY_UNVERIFIED")
    return list(dict.fromkeys(blockers))
