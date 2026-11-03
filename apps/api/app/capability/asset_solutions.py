"""Pure, source-bound technical-asset retrieval and review-draft generation.

This is bounded lexical retrieval, not general AI or delivery certification.
The caller supplies authorized immutable inputs and persists the returned draft.
No DB, provider, filesystem, network, business transition or publish is invoked.
"""
from copy import deepcopy
from hashlib import sha256
import json

from app.capability import recommendations as R
from app.capability.search import compact, query_terms, GENERAL, PARTICLES
from app.company.improvement_structure import normalized
from app.notice.domain import Denied

VERSION = "asset-solutions-v4"
MAX_MODULE_FEATURES = 8
MAX_COMPOSITE_MODULES = 6
MAX_ALTERNATIVES = 8
_REVIEW = "기업 업무의 실제 적용범위·예외·성과는 운영자 검토가 필요합니다."
_KIND = {"as_is": "CURRENT_STATE", "현황": "CURRENT_STATE", "현재 업무": "CURRENT_STATE",
         "problem": "PROBLEM", "문제": "PROBLEM", "문제점": "PROBLEM",
         "goal": "GOAL", "to_be": "GOAL", "목표": "GOAL", "개선 목표": "GOAL",
         "required_functions": "REQUIRED_FUNCTION", "필요 기능": "REQUIRED_FUNCTION",
         "constraints": "CONSTRAINT", "제약사항": "CONSTRAINT", "적용 범위": "CONSTRAINT"}
_SEARCH_FIELDS = (("name", "기능명"), ("description", "기능 설명"),
                  ("business_areas", "적용 업무"), ("problems", "등록된 문제"))


def _unique(values):
    return list(dict.fromkeys(value for value in values if value))


def _texts(value):
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [v for v in value or [] if isinstance(v, str) and v.strip()]


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":")).encode()).hexdigest()


def _label(value, maximum):
    # Only synthesized presentation labels are shortened. Literal names, demand
    # text, quoted evidence and registered metadata remain in the detailed data.
    suffix = "… (전체 명칭·내용은 상세 참조)"
    return value if len(value) <= maximum else value[:maximum - len(suffix)] + suffix


def _prerequisites(values, required=()):
    ordered = _unique([*required, *values])
    if len(ordered) <= 100:
        return ordered
    # Preserve every remaining exact original condition in one explicitly
    # labelled overflow item. A verified relation's exact condition stays first
    # as its own item so the authority validator can match it without parsing.
    return [*ordered[:99], "추가 조건 원문 전체(항목별 순서 유지):\n"
            + "\n".join("• " + value for value in ordered[99:])]


def _demands(context, reviewed):
    # Keep the old published-service helper untouched. Its same-role aliases are
    # projected once here, retaining every supplied source/evidence dictionary.
    values = R.source_demands(context)
    if not any(v["kind"] != "CONSTRAINT" for v in values) and context.get("original_text", "").strip():
        values.append(dict(id="improvement:original_text", kind="PROBLEM", text=context["original_text"],
            evidence=[dict(kind="IMPROVEMENT_VERSION", version_id=context["improvement_version_id"],
                           field="original_text", quote=context["original_text"])],
            uncertainty="기업 원문이며 기능 적합성은 별도 검토해야 합니다."))
    for item in reviewed:
        if item.get("category") != "STRUCTURE":
            continue
        subject = item.get("subject", "")
        if subject in ("원인 후보", "cause", "impact"):
            continue
        values.append(dict(id="analysis:" + item["candidate_id"],
            kind=_KIND.get(subject, "REQUIRED_FUNCTION"), text=item["content"],
            evidence=deepcopy(item.get("evidence", [])),
            uncertainty=item.get("uncertainty") or
                "검토하여 활용한 분석 후보이며 확정 사실·제공 보장이 아닙니다."))
    result, indexed = [], {}
    for item in values:
        # as_is/problem with exactly the same text are stored input aliases.
        role = "CURRENT_CONTEXT" if item["kind"] in ("CURRENT_STATE", "PROBLEM") else item["kind"]
        key = (role, normalized(item["text"]))
        if key in indexed:
            existing = indexed[key]
            for evidence in item["evidence"]:
                if evidence not in existing["evidence"]:
                    existing["evidence"].append(deepcopy(evidence))
            existing["source_ids"] = _unique([*existing["source_ids"], item["id"]])
            existing["roles"] = _unique([*existing["roles"], item["kind"]])
        else:
            copied = deepcopy(item)
            copied.update(source_ids=[item["id"]], roles=[item["kind"]])
            indexed[key] = copied
            result.append(copied)
    return result


def _meaningful(term):
    stem = term
    for particle in PARTICLES:
        if stem.endswith(particle) and len(stem) - len(particle) >= 2:
            stem = stem[:-len(particle)]
            break
    return stem not in GENERAL | {"직원", "담당자", "사업장", "사람", "부서",
        "싶다", "하려고", "원한다", "있습니다"}


def _query(demand, excluded):
    words = R.business_words(R.positive_text(demand["text"]))
    if words and not words - excluded:
        return []
    terms = query_terms(R.expanded(demand["text"]))
    # The shared published-service search intentionally drops generic "중복".
    # Preserve only this concrete task compound, in either conventional order;
    # _match still requires the whole phrase in registered source metadata.
    if R.re.search(r"중복\s*입력|입력\s*중복", R.positive_text(demand["text"])):
        terms.extend(["중복 입력", "입력 중복"])
    return _unique(term for term in terms if _meaningful(term)
                   and not any(compact(e) in compact(term) for e in excluded))


def _node_metadata(node):
    return node.get("data", node)


def _holders(features, nodes):
    holders = {}
    for feature in features:
        owner = feature.get("id") or feature["feature_id"]
        holders.setdefault(owner, (owner, feature))
        for key in ("module_id", "system_id"):
            node = nodes.get(feature[key])
            if node:
                holders.setdefault(node["id"], (node["id"], node))
    return list(holders.values())


def _parent_values(feature, nodes, field):
    return [value for key in ("module_id", "system_id") if feature[key] in nodes
            for value in _texts(_node_metadata(nodes[feature[key]]).get(field))]


def _availability(feature, nodes=None):
    nodes = nodes or {}
    parents = [nodes[feature[key]] for key in ("module_id", "system_id") if feature[key] in nodes]
    if any(parent.get("availability", _node_metadata(parent).get("availability"))
           != "VERIFIED" for parent in parents):
        return "NEEDS_CONFIRMATION"
    # Source inventory AVAILABLE is provenance, not a verified current offer.
    if (feature.get("availability") == "VERIFIED"
            and _texts(feature.get("availability_evidence"))):
        return "VERIFIED"
    return "NEEDS_CONFIRMATION"


def _limits(feature, nodes=None):
    nodes = nodes or {}
    values = [value for field in ("conditions", "prerequisites", "exclusions")
              for value in [*_texts(feature.get(field)), *_parent_values(feature, nodes, field)]]
    for _, holder in _holders([feature], nodes):
        metadata = _node_metadata(holder)
        for relation in holder.get("relations", metadata.get("relations", [])):
            if relation.get("kind") == "DEPENDENCY" and relation.get("condition"):
                values.append("선행 의존조건: " + relation["condition"])
    if _availability(feature, nodes) != "VERIFIED":
        values.append(feature["name"] + ": 현재 제공 가능 상태와 검증 근거 확인 필요.")
    if not feature.get("module_version_id"):
        values.append(feature["module_name"] + ": 원천 기능그룹 분류이며 관리자가 확인한 모듈 구성은 아닙니다.")
    return _unique(values)


def _match(feature, demand, excluded, nodes):
    terms = _query(demand, excluded)
    if not terms:
        return None
    declared_exclusions = [*_texts(feature.get("exclusions")),
                           *_parent_values(feature, nodes, "exclusions")]
    own_excluded, _ = R.exclusions({"structured": {
        "constraints": "\n".join(value + " 제외" for value in declared_exclusions)}})
    for value in declared_exclusions:
        partial = list(R.PARTIAL_SCOPE.finditer(value))
        # Excluding causal inference/optimization does not exclude a literal
        # status view in the same business area.
        scope = (" ".join(match.group(0) for match in partial)
                 if partial and not R.re.search(r"전체|모든", value) else value)
        own_excluded.update(term for term in query_terms(R.EXCLUDED.sub(" ", scope))
                            if _meaningful(term))
    terms = [term for term in terms if not any(compact(e) in compact(term) for e in own_excluded)]
    if not terms:
        return None
    original_words = R.business_words(R.positive_text(demand["text"])) - excluded - own_excluded
    relevant_groups = R.groups_for(" ".join(original_words))
    feature_text = " ".join(text for field, _ in _SEARCH_FIELDS
                            for text in _texts(feature.get(field)))
    feature_groups = R.groups_for(feature_text)
    # Same-domain classification is not function evidence: employee terminology
    # must not turn attendance into payroll, or vice versa.
    task_words = R.business_words(" ".join(terms)) - excluded - own_excluded
    if task_words and not task_words.intersection(R.business_words(feature_text)):
        return None
    if relevant_groups and feature_groups and not relevant_groups & feature_groups:
        return None
    evidence, found, reasons, score = [], [], [], 0
    for field, label in _SEARCH_FIELDS:
        for quote in _texts(feature.get(field)):
            hits = [term for term in terms if compact(term) in compact(quote)]
            if not hits:
                continue
            found.extend(hits)
            reasons.append(label + ": " + ", ".join(hits))
            evidence.append(dict(feature_revision_id=feature["revision_id"],
                asset_version_id=feature.get("asset_version_id"),
                field=field, quote=quote, matched_terms=hits))
            score += len(hits) * (3 if field == "name" else 1)
    if not found:
        return None
    return dict(terms=_unique(found), evidence=evidence, reasons=_unique(reasons), score=score)


def _feature_order(feature):
    return (feature["system_name"], feature["module_name"], feature["name"], feature["revision_id"])


def _candidate_order(candidate):
    return (-candidate["retrieval_score"], *_feature_order(candidate))


def _tokens(candidates):
    return {(key, term) for candidate in candidates
            for key, terms in candidate["demand_terms"].items() for term in terms}


def _module_groups(candidates):
    groups = {}
    for candidate in candidates:
        groups.setdefault(candidate["module_id"], []).append(candidate)
    return {key: sorted(value, key=_candidate_order)[:MAX_MODULE_FEATURES]
            for key, value in groups.items()}


def _group_order(item):
    key, candidates = item
    return (-len({d for c in candidates for d in c["demand_ids"]}),
            -len(_tokens(candidates)), -sum(c["retrieval_score"] for c in candidates),
            _feature_order(candidates[0]), key)


def _coverage_units(candidates):
    # Count concrete source-backed task concepts, never spelling variants or
    # repeated lexical hits. Inbound and outbound remain distinct operations.
    aliases = {"근태": "근태", "출퇴근": "근태", "급여": "급여", "임금": "급여",
               "생산실적": "작업실적", "작업실적": "작업실적",
               "mes": "생산", "qms": "품질", "hr": "인사", "scms": "공급망",
               "전자결재": "결재", "기안": "결재", "분개": "전표"}
    units = set()
    for candidate in candidates:
        for demand, terms in candidate["demand_terms"].items():
            for term in terms:
                words = R.business_words(term)
                # Conventional task compounds must retain their precise role.
                if "실적" in term and words & {"생산", "작업실적"}:
                    words = (words - {"생산"}) | {"작업실적"}
                if "입출고" in words:
                    words = (words - {"입출고"}) | {"입고", "출고"}
                units.update((demand, aliases.get(word, word)) for word in words)
                if not words:
                    units.add((demand, compact(term)))
    return units


def _greedy(groups):
    chosen, covered, covered_demands = [], set(), set()
    remaining = sorted(groups.items(), key=_group_order)
    while remaining and len(chosen) < MAX_COMPOSITE_MODULES:
        ranked = sorted(remaining, key=lambda item: (
            -len({d for c in item[1] for d in c["demand_ids"]} - covered_demands),
            -len(_coverage_units(item[1]) - covered), _group_order(item)))
        key, candidates = ranked[0]
        new = _coverage_units(candidates) - covered
        if chosen and not new:
            break
        chosen.append((key, candidates))
        covered.update(new)
        covered_demands.update(d for c in candidates for d in c["demand_ids"])
        remaining = [item for item in remaining if item[0] != key]
    return chosen


def _relations(left, right, nodes):
    targets = {f.get("id") for f in right} | {f["feature_id"] for f in right} | {
        f["module_id"] for f in right} | {f["system_id"] for f in right}
    found = []
    for owner, holder in _holders(left, nodes):
        for relation in holder.get("relations", _node_metadata(holder).get("relations", [])):
            if relation.get("target_node_id") in targets:
                found.append(dict(relation, from_asset_id=owner))
    return found


def _integration(left, right, nodes):
    linked = _relations(left, right, nodes)
    if not linked and _relations(right, left, nodes):
        left, right = right, left
        linked = _relations(left, right, nodes)
    valid = [r for r in linked if r.get("kind") == "INTEGRATION"
             and r.get("verified") is True and r.get("current_valid") is not False
             and str(r.get("condition", "")).strip() and _texts(r.get("evidence"))]
    ordered = sorted(valid or linked, key=lambda r: (
        r["from_asset_id"], r["target_node_id"], r.get("condition", ""), r.get("evidence", "")))
    selected = ordered[0] if ordered else None
    verified = bool(valid)
    conditions = _unique(r["condition"] for r in linked if r.get("condition"))
    first, second = left[0], right[0]
    feature_names = " · ".join(_unique(f["name"] for f in [*left, *right]))
    return dict(from_asset_id=selected["from_asset_id"] if selected else first["module_id"],
        to_asset_id=selected["target_node_id"] if selected else second["module_id"],
        data=_label(feature_names + ": 실제 데이터 항목·공통 식별자·형식은 확인 필요.", 5000),
        workflow=_label(first["module_name"] + " / " + second["module_name"]
                  + " 기능을 연결하는 업무 초안입니다. 처리 순서·책임·예외는 기업과 검토하세요.", 5000),
        prerequisites=_prerequisites([*conditions, *[v for f in [*left, *right]
            for v in [*_texts(f.get("prerequisites")), *_parent_values(f, nodes, "prerequisites")]]],
            required=[selected["condition"]] if selected and selected.get("condition") else []),
        verification="VERIFIED" if verified else "UNVERIFIED",
        evidence_note=(selected["evidence"] if selected and selected.get("evidence") else
                       "확인된 모듈 간 연계 근거가 등록되지 않았습니다."),
        uncertainty=("등록된 조건 범위의 연계 근거입니다. 기업 환경의 실제 적용성은 별도 검토해야 합니다."
                     if verified else "연계가 검증되지 않은 구성 초안이며 실제 연동을 보장하지 않습니다."))


def _integration_graph(chosen, nodes):
    # Preserve registered relationships even when neither endpoint happens to
    # be the first selected module. Add only enough unknown links to connect the
    # remaining groups, explicitly as unverified workflow review drafts.
    indexed = {key: candidates for key, candidates in chosen}
    keys = sorted(indexed)
    components = {key: key for key in keys}
    def component(key):
        while components[key] != key:
            key = components[key]
        return key
    pairs = [(left, right) for i, left in enumerate(keys) for right in keys[i + 1:]]
    known = [pair for pair in pairs if _relations(indexed[pair[0]], indexed[pair[1]], nodes)
             or _relations(indexed[pair[1]], indexed[pair[0]], nodes)]
    result = []
    for left, right in [*known, *[pair for pair in pairs if pair not in known]]:
        if (left, right) not in known and component(left) == component(right):
            continue
        result.append(_integration(indexed[left], indexed[right], nodes))
        components[component(right)] = component(left)
    unique = {}
    for link in sorted(result, key=lambda link: link["verification"] != "VERIFIED"):
        unique.setdefault((link["from_asset_id"], link["to_asset_id"]), link)
    return list(unique.values())


def _alternative(context, demands, chosen, excluded_clauses, catalog_features, nodes):
    candidates = sorted({c["revision_id"]: c for _, cs in chosen for c in cs}.values(),
                        key=_feature_order)
    revisions = {c["revision_id"] for c in candidates}
    features = [deepcopy(catalog_features[c["revision_id"]]) for c in candidates]
    systems = list({f["system_id"]: dict(id=f["system_id"], name=f["system_name"],
                         version_id=f.get("system_version_id")) for f in features}.values())
    modules = list({f["module_id"]: dict(id=f["module_id"], name=f["module_name"],
                         version_id=f.get("module_version_id")) for f in features}.values())
    coverage, uncovered = [], []
    for demand in demands:
        if demand["kind"] == "CONSTRAINT":
            continue
        matched = [c for c in candidates if demand["id"] in c["demand_ids"]]
        if matched:
            missing = _unique([_REVIEW, *[value for c in matched for value in _limits(c, nodes)]])
            if R.PARTIAL_SCOPE.search(R.positive_text(demand["text"])):
                missing.append("원인 규명·예측·자동 판정·최적화는 원천 기능의 명시 범위와 별도로 확인해야 합니다.")
            coverage.append(dict(demand_id=demand["id"], requirement=demand["text"],
                evidence_refs=deepcopy(demand["evidence"]), status="PARTIAL",
                capability_version_id=None,
                feature_revision_ids=[c["revision_id"] for c in matched],
                role=_label("요구 원문: " + demand["text"] + " / 적용 검토 모듈: "
                    + " · ".join(_unique(c["module_name"] for c in matched)), 2000),
                addressed_scope=_label("등록된 제공범위 원문: " + " / ".join(_unique(
                    e["quote"] for c in matched for e in c["evidence"]
                    if any(term in c["demand_terms"].get(demand["id"], [])
                           for term in e["matched_terms"]))), 5000),
                unaddressed_scope="요구 전체의 해결·실제 적용성·효과는 아직 검증하지 않았습니다.",
                missing_information=missing))
        else:
            uncovered.append(demand["id"])
            coverage.append(dict(demand_id=demand["id"], requirement=demand["text"],
                evidence_refs=deepcopy(demand["evidence"]), status="UNRESOLVED",
                capability_version_id=None, feature_revision_ids=[],
                role="현재 확인된 원천 기능에서 대응 근거를 찾지 못했습니다.",
                addressed_scope="", unaddressed_scope="이 요구의 해결 기능과 적용범위는 미확인입니다.",
                missing_information=["이 요구에 대응 가능한 실제 기능·적용범위를 추가 검토해야 합니다."]))
    kind = ("CROSS_SYSTEM" if len(systems) > 1 else
            "MULTI_MODULE" if len(modules) > 1 else "SINGLE_MODULE")
    topology = kind
    if uncovered:
        kind = "PARTIAL"
    name = " / ".join(system["name"] for system in systems) + " — " + " · ".join(
        module["name"] for module in modules) + " 검토 초안"
    integrations = _integration_graph(chosen, nodes)
    unknown = [c for c in candidates if _availability(c, nodes) != "VERIFIED"]
    conditions = _unique([*[d["text"] for d in demands if d["kind"] == "CONSTRAINT"],
                          *[v for f in features for field in ("conditions", "prerequisites")
                            for v in [*_texts(f.get(field)), *_parent_values(f, nodes, field)]]])
    unresolved = _unique([*[row["requirement"] + ": 대응 근거 없음."
                            for row in coverage if row["status"] == "UNRESOLVED"],
                           *[f["name"] + ": 제공 가능 검증 필요." for f in unknown],
                           *["명시 제외·한계(원문): " + value for value in excluded_clauses],
                           *[link["uncertainty"] for link in integrations if link["verification"] != "VERIFIED"],
                           _REVIEW])
    identity = dict(company_id=context["company_id"], improvement_version_id=context["improvement_version_id"],
                    rule_version=VERSION, revisions=sorted(revisions),
                    asset_versions=sorted((f["revision_id"], f.get("asset_version_id"),
                        f.get("system_version_id"), f.get("module_version_id")) for f in features))
    return dict(id="asset-alt-" + _digest(identity)[:24], name=_label(name, 500), kind=kind,
        topology_kind=topology,
        why="기업 요구의 양성 업무 표현이 실제 기능 원문과 연결됩니다. 기능별 근거를 확인한 후 선택하세요.",
        systems=systems, modules=modules,
        feature_selections=[dict(feature_revision_id=f["revision_id"],
            asset_version_id=f.get("asset_version_id"), system_version_id=f.get("system_version_id"),
            module_version_id=f.get("module_version_id"), role=_label(f["name"] + " 기능 적용 검토", 2000)) for f in features],
        features=features, coverage=coverage, integrations=integrations,
        conditions=conditions, unresolved=unresolved, review_status="REVIEW_REQUIRED")


def generate(context, catalog, reviewed=(), basis=None, limits=()):
    """Return deterministic technical candidates and populated review alternatives.

    The caller alone authenticates, validates currentness, fixes an input manifest
    and persists this projection. No unreviewed result is a confirmed service.
    """
    demands = _demands(context, reviewed)
    excluded, excluded_clauses = R.exclusions(context, reviewed)
    active = [d for d in demands if d["kind"] != "CONSTRAINT"]
    nodes = {node["id"]: node for kind in ("systems", "modules") for node in catalog.get(kind, [])}
    features, candidates = {}, []
    for feature in catalog.get("features", []):
        rid = feature["revision_id"]
        if rid in features and features[rid] != feature:
            raise Denied("ASSET_REVISION_CONFLICT", 422)
        features[rid] = feature
    for feature in sorted(features.values(), key=_feature_order):
        parent_statuses = [nodes[feature[key]].get("availability",
            _node_metadata(nodes[feature[key]]).get("availability"))
            for key in ("module_id", "system_id") if feature[key] in nodes]
        if (feature.get("source_current") is False or feature.get("availability") in ("UNAVAILABLE", "RETIRED")
                or any(value in ("UNAVAILABLE", "RETIRED") for value in parent_statuses)):
            continue
        matches = [(d, found) for d in active if (found := _match(feature, d, excluded, nodes))]
        if not matches:
            continue
        candidate = deepcopy(feature)
        candidate.update(demand_ids=[d["id"] for d, _ in matches],
            matched_terms=_unique(term for _, found in matches for term in found["terms"]),
            demand_terms={d["id"]: found["terms"] for d, found in matches},
            reasons=_unique(d["id"] + ": " + why for d, found in matches for why in found["reasons"]),
            evidence=[e for _, found in matches for e in found["evidence"]],
            limitations=_unique([*_limits(feature, nodes), _REVIEW]),
            provision_status=_availability(feature, nodes), review_status="REVIEW_REQUIRED",
            retrieval_score=sum(found["score"] for _, found in matches))
        candidates.append(candidate)
    candidates.sort(key=_candidate_order)
    groups = _module_groups(candidates)
    chosen_options = [[item] for item in sorted(groups.items(), key=_group_order)]
    systems = sorted({cs[0]["system_id"] for cs in groups.values()})
    for system in systems:
        chosen = _greedy({key: cs for key, cs in groups.items() if cs[0]["system_id"] == system})
        if len(chosen) > 1:
            chosen_options.append(chosen)
    all_chosen = _greedy(groups)
    if len({cs[0]["system_id"] for _, cs in all_chosen}) > 1:
        chosen_options.append(all_chosen)
    alternatives = {}
    for chosen in chosen_options:
        value = _alternative(context, demands, chosen, excluded_clauses, features, nodes)
        alternatives.setdefault(value["id"], value)
    ordered = sorted(alternatives.values(), key=lambda a: (
        -len({row["demand_id"] for row in a["coverage"] if row["feature_revision_ids"]}),
        -len(_coverage_units([c for c in candidates
             if c["revision_id"] in {f["feature_revision_id"] for f in a["feature_selections"]}])),
        len(a["modules"]), len(a["feature_selections"]), a["name"], a["id"]))[:MAX_ALTERNATIVES]
    covered = {d for candidate in candidates for d in candidate["demand_ids"]}
    limitations = _unique([*limits,
        "등록된 기능 표현을 이용한 제한된 규칙 검색·조합 초안이며 범용 AI 의미분석이 아닙니다.",
        "자동 초안은 사람 검토 전 상태이며 제공 가능성·실제 해결·지원사업 자격을 확정하지 않습니다.",
        *["명시 제외·한계(원문): " + value for value in excluded_clauses]])
    concrete = any(_query(d, excluded) for d in active)
    status = "CANDIDATES" if candidates else "NO_SOLUTION" if concrete else "INPUT_INSUFFICIENT"
    if not candidates:
        limitations.append("현재 확인된 솔루션 없음." if concrete else "구체적인 양성 업무 요구가 부족하여 후보를 생성하지 않았습니다.")
    if any(len([c for c in candidates if c["module_id"] == key]) > MAX_MODULE_FEATURES for key in groups):
        limitations.append("모듈별 자동 초안의 기능 수에는 제한이 있습니다. 나머지 실제 후보는 상세에서 검토하세요.")
    if len(alternatives) > MAX_ALTERNATIVES:
        limitations.append("자동 비교안 수에는 제한이 있습니다. 선택하지 않은 원천 기능의 부재를 뜻하지 않습니다.")
    return dict(rule_version=VERSION, status=status, demands=demands, candidates=candidates,
        alternatives=ordered, uncovered_demands=[d["id"] for d in active if d["id"] not in covered],
        limitations=limitations)
