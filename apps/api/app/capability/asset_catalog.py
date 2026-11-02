"""Versioned local DMP metadata; raw source records remain immutable evidence."""
from copy import deepcopy
from hashlib import sha256
from uuid import uuid4
import unicodedata
from sqlalchemy import update, text
from app.capability.application import fingerprint
from app.infrastructure import capability_schema as S
from app.infrastructure import dmp_asset_schema as D
from app.notice.domain import Denied

KINDS = ("SYSTEM", "MODULE", "FEATURE")
STATUSES = ("NEEDS_CONFIRMATION", "VERIFIED", "UNAVAILABLE", "RETIRED")
RELATION_KINDS = ("DEPENDENCY", "INTEGRATION", "REPLACEMENT")
TEXT_FIELDS = ("description", "role", "release", "availability_evidence")
LIST_FIELDS = ("business_areas", "problems", "conditions", "exclusions", "prerequisites")
DATA_FIELDS = {"name", "availability", "relations", *TEXT_FIELDS, *LIST_FIELDS}
SOURCE_MAPPING = "SOURCE_CLASSIFICATION"
_PARENT_UNSET = object()


def normalize_data(data):
    """Validate direct application callers as well as the HTTP DTO."""
    if not isinstance(data, dict) or set(data) - DATA_FIELDS:
        raise Denied("INVALID_ASSET_DATA", 422)
    result = {}
    for key in ("name", *TEXT_FIELDS):
        value = data.get(key, "")
        if not isinstance(value, str) or len(value) > (500 if key == "name" else 10000):
            raise Denied("INVALID_ASSET_DATA", 422)
        result[key] = value.strip()
    if not result["name"]:
        raise Denied("REQUIRED_DATA_MISSING", 422)
    result["availability"] = data.get("availability", "NEEDS_CONFIRMATION")
    if result["availability"] not in STATUSES:
        raise Denied("INVALID_ASSET_STATUS", 422)
    if result["availability"] == "VERIFIED" and not result["availability_evidence"]:
        raise Denied("AVAILABILITY_EVIDENCE_REQUIRED", 422)
    for key in LIST_FIELDS:
        values = data.get(key, [])
        if not isinstance(values, list) or len(values) > 100 or any(
                not isinstance(v, str) or not v.strip() or len(v) > 5000 for v in values):
            raise Denied("INVALID_ASSET_DATA", 422)
        result[key] = list(dict.fromkeys(v.strip() for v in values))
    relations = data.get("relations", [])
    if not isinstance(relations, list) or len(relations) > 100:
        raise Denied("INVALID_ASSET_RELATION", 422)
    result["relations"] = []
    seen = set()
    for relation in relations:
        if not isinstance(relation, dict) or set(relation) - {
                "target_node_id", "target_version_id", "kind", "condition", "verified", "evidence"}:
            raise Denied("INVALID_ASSET_RELATION", 422)
        target, kind = relation.get("target_node_id"), relation.get("kind")
        condition, evidence = relation.get("condition", ""), relation.get("evidence", "")
        verified = relation.get("verified", False)
        if (not isinstance(target, str) or not target or kind not in RELATION_KINDS
                or not isinstance(condition, str) or not condition.strip() or len(condition) > 10000
                or not isinstance(evidence, str) or len(evidence) > 10000 or type(verified) is not bool):
            raise Denied("INVALID_ASSET_RELATION", 422)
        if verified and not evidence.strip():
            raise Denied("RELATION_EVIDENCE_REQUIRED", 422)
        if (target, kind) in seen:
            raise Denied("DUPLICATE_ASSET_RELATION", 422)
        seen.add((target, kind))
        value = dict(target_node_id=target, kind=kind,
            condition=condition.strip(), verified=verified, evidence=evidence.strip())
        target_version = relation.get("target_version_id")
        if target_version is not None:
            if not isinstance(target_version, str) or not target_version or len(target_version) > 100:
                raise Denied("INVALID_ASSET_RELATION", 422)
            value["target_version_id"] = target_version
        result["relations"].append(value)
    result["relations"].sort(key=lambda r: (r["kind"], r["target_node_id"]))
    return result


def _current(service):
    nodes = {n["id"]: n for n in service.rows(D.nodes)}
    all_versions = service.rows(D.versions)
    versions = {v["node_id"]: v for v in all_versions
                if nodes.get(v["node_id"], {}).get("current_ordinal") == v["ordinal"]}
    return nodes, versions


def validate_parent(kind, parent_id, nodes, current):
    expected = {"SYSTEM": None, "MODULE": "SYSTEM", "FEATURE": "MODULE"}.get(kind)
    if kind not in KINDS:
        raise Denied("INVALID_ASSET_KIND", 422)
    if expected is None:
        if parent_id is not None:
            raise Denied("ASSET_PARENT_KIND_MISMATCH", 422)
    elif (parent_id not in nodes or parent_id not in current
          or nodes[parent_id]["kind"] != expected):
        raise Denied("ASSET_PARENT_KIND_MISMATCH", 422)


def validate_relations(node_id, kind, relations, nodes, current):
    """Only dependencies/replacements are directed acyclic obligations."""
    for relation in relations:
        target = relation["target_node_id"]
        if target == node_id:
            raise Denied("ASSET_SELF_RELATION", 422)
        if target not in nodes or target not in current:
            raise Denied("ASSET_RELATION_TARGET_NOT_FOUND", 422)
        if relation["kind"] == "REPLACEMENT" and nodes[target]["kind"] != kind:
            raise Denied("ASSET_REPLACEMENT_KIND_MISMATCH", 422)
    obligations = {"DEPENDENCY", "REPLACEMENT"}
    graph = {key: [r["target_node_id"] for r in version["data"].get("relations", [])
                   if r["kind"] in obligations]
             for key, version in current.items()}
    graph[node_id] = [r["target_node_id"] for r in relations if r["kind"] in obligations]
    pending, visited = list(graph[node_id]), set()
    while pending:
        target = pending.pop()
        if target == node_id:
            raise Denied("ASSET_RELATION_CYCLE", 422)
        if target not in visited:
            visited.add(target)
            pending.extend(graph.get(target, []))


def bind_relation_versions(data, current):
    """Capture exact reviewed target versions; never retarget an old declaration silently."""
    result = deepcopy(data)
    for relation in result["relations"]:
        actual = current[relation["target_node_id"]]["id"]
        if relation.get("target_version_id") not in (None, actual):
            raise Denied("STALE_ASSET_RELATION_VERSION", 409)
        relation["target_version_id"] = actual
    return result


def _pseudo(kind, *parts):
    return "source-" + kind + ":" + sha256("\x1f".join(parts).encode()).hexdigest()[:24]


def _raw_source(revision, member_by_revision, imports, asset_version=None):
    member = member_by_revision.get(revision["id"])
    imported = imports.get(member["import_id"]) if member else None
    return dict(kind="DMP_IMPORT" if imported else "ADMIN_MANAGED",
        import_id=imported["id"] if imported else None,
        digest=imported["digest"] if imported else
            (asset_version["digest"] if asset_version else revision["digest"]),
        revision_digest=revision["digest"])


def _project_node(node, version):
    data = deepcopy(version["data"])
    return dict(id=node["id"], kind=node["kind"], name=data["name"],
        parent_id=version["parent_id"], parent_version_id=version.get("parent_version_id"), version_id=version["id"],
        asset_version_id=version["id"], current_ordinal=version["ordinal"],
        data=data, availability=data["availability"],
        declared_availability=data["availability"],
        availability_evidence=data.get("availability_evidence", ""),
        mapping_status="MANAGED", source=dict(kind="ADMIN_MANAGED",
            import_id=None, digest=version["digest"], revision_digest=None))


def catalog_snapshot(service):
    """Internal trusted port: no auth and absolutely no writes/imports."""
    nodes, current = _current(service)
    raw_roots = {r["id"]: r for r in service.rows(S.features)}
    revisions = service.rows(S.revisions)
    revisions_by_id = {r["id"]: r for r in revisions}
    latest = {}
    for revision in revisions:
        previous = latest.get(revision["feature_id"])
        if previous is None or revision["ordinal"] > previous["ordinal"]:
            latest[revision["feature_id"]] = revision
    imports = {r["id"]: r for r in service.rows(S.imports)}
    members = sorted(service.rows(S.members), key=lambda r: str(r.get("created_at", "")) + r["id"])
    member_by_revision = {r["revision_id"]: r for r in members}
    projected = {key: _project_node(node, current[key])
                 for key, node in nodes.items() if key in current}
    # A verification declaration belongs to its exact parent/target releases.
    for key, item in projected.items():
        version = current[key]
        parent_id = version["parent_id"]
        parent_version = current.get(parent_id)
        item["source_current"] = parent_id is None or (
            parent_version is not None and version.get("parent_version_id") == parent_version["id"])
    for item in projected.values():
        if item["kind"] != "MODULE":
            continue
        parent = projected.get(item["parent_id"])
        parent_status = parent["availability"] if parent else "NEEDS_CONFIRMATION"
        if not item["source_current"]:
            item["mapping_status"] = "PARENT_VERSION_CHANGED"
        if parent_status in ("RETIRED", "UNAVAILABLE"):
            item["availability"] = parent_status
        elif item["availability"] == "VERIFIED" and (
                parent_status == "NEEDS_CONFIRMATION" or not item["source_current"]):
            item["availability"] = "NEEDS_CONFIRMATION"
    for key, item in projected.items():
        if item["kind"] == "FEATURE":
            parent = projected.get(item["parent_id"])
            latest_revision = latest.get(nodes[key]["feature_id"])
            item["source_current"] = bool(item["source_current"] and parent and parent["source_current"]
                and latest_revision and current[key]["source_revision_id"] == latest_revision["id"])
    for item in projected.values():
        item["relations"] = []
        for original in item["data"].get("relations", []):
            relation = deepcopy(original)
            target = projected.get(relation["target_node_id"])
            fresh = target is not None and target["version_id"] == relation.get("target_version_id") and target["source_current"]
            relation.update(declared_verified=relation["verified"],
                verified=relation["verified"] and fresh, current_valid=fresh,
                target_current_version_id=target["version_id"] if target else None)
            item["relations"].append(relation)
    systems = {key: row for key, row in projected.items() if row["kind"] == "SYSTEM"}
    modules = {key: row for key, row in projected.items() if row["kind"] == "MODULE"}
    managed_features = {n["feature_id"]: (n, current[n["id"]])
                        for n in nodes.values() if n["kind"] == "FEATURE" and n["id"] in current}
    features = []
    for feature_id, root in sorted(raw_roots.items()):
        latest_revision = latest.get(feature_id)
        if latest_revision is None:
            continue
        managed = managed_features.get(feature_id)
        node, version = managed if managed else (None, None)
        revision = revisions_by_id.get(version["source_revision_id"]) if version else latest_revision
        if revision is None or revision["feature_id"] != feature_id:
            raise Denied("ASSET_SOURCE_REVISION_MISMATCH", 409)
        raw = revision["data"]
        if version:
            item = deepcopy(projected[node["id"]])
            module = modules.get(version["parent_id"])
            system = systems.get(module["parent_id"]) if module else None
            if module is None or system is None:
                raise Denied("ASSET_PARENT_KIND_MISMATCH", 409)
            raw_current = revision["id"] == latest_revision["id"]
            source_current = (raw_current and item["source_current"] and module["source_current"])
            parent_statuses = [system["availability"], module["availability"]]
            declared = item["availability"]
            if "RETIRED" in parent_statuses:
                item["availability"] = "RETIRED"
            elif "UNAVAILABLE" in parent_statuses:
                item["availability"] = "UNAVAILABLE"
            elif declared == "VERIFIED" and ("NEEDS_CONFIRMATION" in parent_statuses or not source_current):
                item["availability"] = "NEEDS_CONFIRMATION"
            if not raw_current:
                item["mapping_status"] = "SOURCE_REVISION_CHANGED"
            elif not source_current:
                item["mapping_status"] = "PARENT_VERSION_CHANGED"
            system_id, module_id = system["id"], module["id"]
            system_name, module_name = system["name"], module["name"]
        else:
            system_name, module_name = raw["system"], raw["feature_group"]
            system_id, module_id = _pseudo("system", system_name), _pseudo("module", system_name, module_name)
            for target, kind, name, key, parent in (
                    (systems, "SYSTEM", system_name, system_id, None),
                    (modules, "MODULE", module_name, module_id, system_id)):
                if key not in target:
                    data = dict(name=name, description="원천 분류이며 관리 등록·제공 검증된 모듈이 아닙니다.",
                        role="", release="", business_areas=[], problems=[], conditions=[],
                        exclusions=[], prerequisites=[], availability="NEEDS_CONFIRMATION",
                        availability_evidence="", relations=[])
                    target[key] = dict(id=key, kind=kind, name=name, parent_id=parent,
                        version_id=None, asset_version_id=None, current_ordinal=0, data=data,
                        availability="NEEDS_CONFIRMATION", declared_availability="NEEDS_CONFIRMATION",
                        availability_evidence="", mapping_status=SOURCE_MAPPING,
                        source=dict(kind="SOURCE_CLASSIFICATION", import_id=None, digest=None, revision_digest=None))
            source_current = True
            status = raw.get("availability", "").upper()
            status = status if status in ("UNAVAILABLE", "RETIRED") else "NEEDS_CONFIRMATION"
            data = dict(name=raw["name"], description=raw.get("description", ""), role="",
                release="", business_areas=[], problems=[], conditions=[], exclusions=[], prerequisites=[],
                availability=status, availability_evidence="", relations=[])
            item = dict(id=feature_id, kind="FEATURE", name=data["name"], parent_id=module_id,
                version_id=None, asset_version_id=None, current_ordinal=revision["ordinal"],
                data=data, availability=status, declared_availability=status,
                availability_evidence="", mapping_status=SOURCE_MAPPING)
        item.update(feature_id=feature_id, external_id=root["external_id"], revision_id=revision["id"],
            latest_source_revision_id=latest_revision["id"], source_current=source_current,
            system_id=system_id, module_id=module_id, system_name=system_name, module_name=module_name,
            system_version_id=systems[system_id]["version_id"], module_version_id=modules[module_id]["version_id"],
            description=item["data"].get("description", ""), role=item["data"].get("role", ""),
            business_areas=item["data"].get("business_areas", []), problems=item["data"].get("problems", []),
            conditions=item["data"].get("conditions", []), prerequisites=item["data"].get("prerequisites", []),
            exclusions=item["data"].get("exclusions", []), relations=item.get("relations", item["data"].get("relations", [])),
            source=_raw_source(revision, member_by_revision, imports, version))
        features.append(item)
    # Fingerprint immutable current content only; ordering and timestamps never affect it.
    digest = fingerprint(dict(
        raw=[dict(feature_id=r["feature_id"], id=r["id"], ordinal=r["ordinal"],
                  digest=r["digest"], data=r["data"]) for r in sorted(latest.values(), key=lambda r: r["feature_id"])],
        imports=[dict(id=r["id"], digest=r["digest"], metadata=r["metadata"])
                 for r in sorted(imports.values(), key=lambda r: r["id"])],
        managed=[dict(node_id=key, kind=nodes[key]["kind"], feature_id=nodes[key].get("feature_id"),
                      id=v["id"], ordinal=v["ordinal"], parent_id=v["parent_id"], parent_version_id=v.get("parent_version_id"),
                      source_revision_id=v["source_revision_id"], digest=v["digest"], data=v["data"])
                 for key, v in sorted(current.items())]))
    order = lambda item: (item["name"].casefold(), item["id"])
    return dict(digest=digest, systems=sorted(systems.values(), key=order),
                modules=sorted(modules.values(), key=order), features=sorted(features, key=order))


def _catalog_lock(service):
    for label in (b"DATCO_DMP_INVENTORY", b"DATCO_DMP_ASSETS"):
        token = int.from_bytes(sha256(label).digest()[:8], "big", signed=True)
        service.session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": token})


class AssetCatalogApplication:
    def __init__(self, service):
        self.service = service

    def list_assets(self, actor, *, kind="", system="", module="", q="", status="", page=1, limit=25):
        self.service.authorize(actor)
        if kind and kind not in KINDS or status and status not in STATUSES:
            raise Denied("INVALID_ASSET_FILTER", 422)
        if (not all(isinstance(v, str) for v in (kind, system, module, q, status))
                or len(q) > 2000 or type(page) is not int or type(limit) is not int
                or page < 1 or not 1 <= limit <= 100):
            raise Denied("INVALID_ASSET_FILTER", 422)
        snapshot = catalog_snapshot(self.service)
        items = snapshot["systems"] + snapshot["modules"] + snapshot["features"]
        if kind:
            items = [r for r in items if r["kind"] == kind]
        if system:
            items = [r for r in items if (r["kind"] == "SYSTEM" and r["id"] == system)
                     or (r["kind"] == "MODULE" and r["parent_id"] == system)
                     or (r["kind"] == "FEATURE" and r["system_id"] == system)]
        if module:
            items = [r for r in items if (r["kind"] == "MODULE" and r["id"] == module)
                     or (r["kind"] == "FEATURE" and r["module_id"] == module)]
        if status:
            items = [r for r in items if r["availability"] == status]
        query = unicodedata.normalize("NFKC", q).casefold().strip()
        if query:
            def matches(row):
                values = [row["name"], row.get("external_id", ""), row["data"].get("description", ""),
                          row["data"].get("role", ""), *row["data"].get("business_areas", []),
                          *row["data"].get("problems", [])]
                return any(query in unicodedata.normalize("NFKC", value).casefold() for value in values)
            items = [r for r in items if matches(r)]
        items.sort(key=lambda r: (KINDS.index(r["kind"]), r["name"].casefold(), r["id"]))
        return dict(items=items[(page - 1) * limit:page * limit], total=len(items), page=page, limit=limit,
                    systems=snapshot["systems"], modules=snapshot["modules"], digest=snapshot["digest"])

    def detail(self, actor, key):
        service = self.service
        service.authorize(actor)
        snapshot = catalog_snapshot(service)
        all_items = snapshot["systems"] + snapshot["modules"] + snapshot["features"]
        item = next((r for r in all_items if r["id"] == key or
                     r.get("external_id") == key or r.get("feature_id") == key), None)
        if item is None:
            raise Denied("OBJECT_NOT_FOUND", 404)
        nodes = {n["id"]: n for n in service.rows(D.nodes)}
        raw_revisions = sorted(service.rows(S.revisions, feature_id=item["feature_id"]),
                               key=lambda r: r["ordinal"]) if item["kind"] == "FEATURE" else []
        if item["id"] in nodes:
            root = dict(nodes[item["id"]], managed=True)
            versions = sorted(service.rows(D.versions, node_id=item["id"]), key=lambda r: r["ordinal"])
            versions = [dict(v, relations=deepcopy(v["data"].get("relations", []))) for v in versions]
        else:
            root = dict(id=item["id"], kind=item["kind"], managed=False,
                        feature_id=item.get("feature_id"), current_ordinal=item["current_ordinal"])
            versions = raw_revisions
        return dict(root=root, current=item, versions=versions, source_revisions=raw_revisions)

    def create(self, actor, *, kind, data, key, parent_id=None, feature_id=None):
        service = self.service
        service.authorize(actor, True)
        normalized = normalize_data(data)
        if not isinstance(key, str) or not key.strip() or len(key) > 100:
            raise Denied("INVALID_IDEMPOTENCY_KEY", 422)
        if kind not in KINDS or feature_id is not None and kind != "FEATURE":
            raise Denied("INVALID_ASSET_KIND", 422)
        def execute():
            _catalog_lock(service)
            nodes, current = _current(service)
            validate_parent(kind, parent_id, nodes, current)
            node_id = str(uuid4())
            validate_relations(node_id, kind, normalized["relations"], nodes, current)
            bound = bind_relation_versions(normalized, current)
            source = None
            if kind == "FEATURE":
                if feature_id:
                    root = service.get(S.features, feature_id, True)
                    if any(n.get("feature_id") == feature_id for n in nodes.values()):
                        raise Denied("ASSET_ALREADY_MANAGED", 409)
                    previous = service.rows(S.revisions, feature_id=root["id"])
                    if not previous:
                        raise Denied("ASSET_SOURCE_REVISION_MISMATCH", 409)
                    source = max(previous, key=lambda r: r["ordinal"])
                    if (source["data"]["name"], source["data"].get("description", "")) != (
                            normalized["name"], normalized["description"]):
                        source = self._feature_revision(root["id"], normalized, parent_id, current, nodes, source)
                else:
                    root = service.add(S.features, external_id="DMP-" + uuid4().hex[:16].upper())
                    feature_id_created = root["id"]
                    source = self._feature_revision(feature_id_created, normalized, parent_id, current, nodes)
                feature_ref = root["id"]
            else:
                feature_ref = None
            node = service.add(D.nodes, id=node_id, kind=kind, feature_id=feature_ref, current_ordinal=0)
            return self._append(actor, node, parent_id, source, bound)
        return service.command(actor, key, ["ASSET_CREATE", kind, parent_id, feature_id, normalized], execute)

    def revise(self, actor, asset_id, *, expected_version, data, key, parent_id=_PARENT_UNSET):
        service = self.service
        service.authorize(actor, True)
        normalized = normalize_data(data)
        if not isinstance(key, str) or not key.strip() or len(key) > 100:
            raise Denied("INVALID_IDEMPOTENCY_KEY", 422)
        def execute():
            _catalog_lock(service)
            node = service.get(D.nodes, asset_id, True)
            nodes, current = _current(service)
            previous = current.get(asset_id)
            if previous is None or previous["id"] != expected_version:
                raise Denied("STALE_INPUT_VERSION", 409)
            selected_parent = previous["parent_id"] if parent_id is _PARENT_UNSET else parent_id
            validate_parent(node["kind"], selected_parent, nodes, current)
            validate_relations(asset_id, node["kind"], normalized["relations"], nodes, current)
            bound = bind_relation_versions(normalized, current)
            source = service.get(S.revisions, previous["source_revision_id"]) if previous["source_revision_id"] else None
            if node["kind"] == "FEATURE":
                all_sources = service.rows(S.revisions, feature_id=node["feature_id"])
                latest = max(all_sources, key=lambda r: r["ordinal"])
                # An explicit save re-verifies the exact latest source. Old history remains readable.
                source = latest
                if (latest["data"]["name"], latest["data"].get("description", "")) != (
                        normalized["name"], normalized["description"]):
                    source = self._feature_revision(node["feature_id"], normalized, selected_parent, current, nodes, latest)
            parent_version_id = current[selected_parent]["id"] if selected_parent else None
            digest = fingerprint(dict(parent_id=selected_parent, parent_version_id=parent_version_id,
                                      source_revision_id=source["id"] if source else None, data=bound))
            if digest == previous["digest"]:
                return dict(id=asset_id, version_id=previous["id"], ordinal=previous["ordinal"])
            if any(v["digest"] == digest for v in service.rows(D.versions, node_id=asset_id)):
                # The unique historical snapshot is retained; an exact reversion requires distinct release metadata.
                raise Denied("ASSET_VERSION_ALREADY_EXISTS", 409)
            return self._append(actor, node, selected_parent, source, bound)
        requested_parent = "PRESERVE_PARENT" if parent_id is _PARENT_UNSET else parent_id
        return service.command(actor, key, ["ASSET_REVISE", asset_id, expected_version, requested_parent, normalized], execute)

    def _feature_revision(self, feature_id, data, parent_id, current, nodes, previous=None):
        service = self.service
        module = current[parent_id]
        system = current[module["parent_id"]]
        root = service.get(S.features, feature_id)
        existing = service.rows(S.revisions, feature_id=feature_id)
        ordinal = max((r["ordinal"] for r in existing), default=0) + 1
        raw = dict(feature_id=root["external_id"], system=system["data"]["name"],
            feature_group=module["data"]["name"], name=data["name"], description=data["description"],
            origin="ADMIN_MANAGED_ASSET_METADATA_NOT_ORIGINAL_WORKBOOK:revision=" + str(ordinal), excel_row=1,
            availability=data["availability"],
            availability_basis=data["availability_evidence"] or "ADMIN_METADATA_REQUIRES_CONFIRMATION")
        digest = fingerprint(raw)
        return service.add(S.revisions, feature_id=feature_id, ordinal=ordinal, digest=digest, data=raw)

    def _append(self, actor, node, parent_id, source, data):
        service = self.service
        _, current = _current(service)
        parent_version_id = current[parent_id]["id"] if parent_id else None
        digest = fingerprint(dict(parent_id=parent_id, parent_version_id=parent_version_id,
                                  source_revision_id=source["id"] if source else None, data=data))
        version = service.add(D.versions, node_id=node["id"], ordinal=node["current_ordinal"] + 1,
            parent_id=parent_id, parent_version_id=parent_version_id, source_revision_id=source["id"] if source else None,
            digest=digest, data=deepcopy(data), actor_id=actor.id)
        for relation in data["relations"]:
            service.add(D.relations, version_id=version["id"], **relation)
        service.session.execute(update(D.nodes).where(D.nodes.c.id == node["id"]).values(
            current_ordinal=version["ordinal"]))
        service.record(actor, "SAVE_DMP_ASSET_VERSION", asset_id=node["id"], version_id=version["id"],
                       ordinal=version["ordinal"], source_revision_id=source["id"] if source else None)
        return dict(id=node["id"], version_id=version["id"], ordinal=version["ordinal"])
