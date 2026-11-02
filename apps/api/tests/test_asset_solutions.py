"""Synthetic technical-asset scenarios; no published service, DB or external AI."""
from copy import deepcopy

import pytest

from app.capability.asset_solutions import generate, VERSION
from app.notice.domain import Denied


def context(text="", **fields):
    return dict(company_id="TEST_COMPANY_A", site_id="TEST_SITE_A",
        improvement_version_id="TEST_VERSION_A", original_text=text,
        structured={"as_is": text, **fields})


def feature(key, name, description, *, system="TEST_ERP", module="TEST_MODULE",
            availability="NEEDS_CONFIRMATION", **fields):
    return dict(feature_id="TEST_FEATURE_" + key, external_id="TEST_EXTERNAL_" + key,
        revision_id="TEST_REVISION_" + key, asset_version_id="TEST_ASSET_VERSION_" + key,
        system_version_id="TEST_SYSTEM_VERSION_" + system,
        module_version_id="TEST_MODULE_VERSION_" + module, system_id=system,
        module_id=module, system_name=system, module_name=module, name=name,
        description=description, business_areas=[], problems=[], prerequisites=[],
        exclusions=[], relations=[], availability=availability,
        availability_evidence="TEST source verification" if availability == "VERIFIED" else "",
        mapping_status="ADMIN_REGISTERED",
        source=dict(kind="TEST_SYNTHETIC", import_id="TEST_IMPORT", digest="a" * 64,
                    revision_digest="b" * 64), **fields)


def catalog():
    return dict(digest="TEST_CATALOG_DIGEST", systems=[], modules=[], features=[
        feature("STOCK", "재고현황", "재고 수량과 현재 재고 조회", module="TEST_STOCK"),
        feature("IN", "입고등록", "입고 처리 기록", module="TEST_PURCHASE"),
        feature("OUT", "출고등록", "출고 처리 기록", module="TEST_SALES"),
        feature("PROD", "작업실적등록", "생산 공정별 작업 실적 기록",
                system="TEST_MES", module="TEST_PRODUCTION"),
        feature("QUALITY", "불량현황", "품질 검사 기록과 불량 현황 조회",
                system="TEST_MES", module="TEST_QUALITY"),
        feature("HR", "근태등록", "직원 출퇴근 휴가 기록",
                system="TEST_HR", module="TEST_ATTENDANCE"),
        feature("PAY", "급여계산", "직원 급여와 임금 명세",
                system="TEST_HR", module="TEST_PAYROLL"),
        feature("ACC", "전표등록", "회계 전표 확인과 결산 처리",
                system="TEST_ACCOUNTING", module="TEST_LEDGER"),
        feature("DOC", "문서 기안", "전자결재 기안 문서 처리와 자료 검색",
                system="TEST_GROUPWARE", module="TEST_DOCUMENT"),
    ])


def names(result):
    return {f["name"] for f in result["candidates"]}


def test_duplicate_input_task_requires_literal_registered_compound_evidence():
    stock = feature("STOCK", "재고현황", "재고 수량 조회")
    explicit = feature("IN", "입출고 이력", "입출고 기록")
    explicit["problems"] = ["입출고 이력 통합과 중복 입력 감소"]
    cat = dict(features=[stock, explicit], systems=[], modules=[])
    for phrase in ("입력 중복", "중복 입력"):
        result = generate(context(phrase), cat)
        assert names(result) == {"입출고 이력"}
        assert result["candidates"][0]["evidence"][0]["quote"] == explicit["problems"][0]
        assert result["alternatives"][0]["coverage"][0]["status"] == "PARTIAL"
    assert not generate(context("중복 개선"), cat)["candidates"]
    explicit["problems"] = []
    assert not generate(context("입력 중복"), cat)["candidates"]


@pytest.mark.parametrize("text,expected", [
    ("창고 입출고를 기록하고 재고 수량을 조회하려고 합니다.", {"재고현황", "입고등록", "출고등록"}),
    ("생산 공정별 작업 실적을 기록하고 싶습니다.", {"작업실적등록"}),
    ("검사 기록과 불량 현황을 조회하려고 합니다.", {"불량현황"}),
    ("직원의 출퇴근과 휴가 기록을 조회하려고 합니다.", {"근태등록"}),
    ("회계 전표의 확인과 결산 처리가 중복됩니다.", {"전표등록"}),
    ("전자결재 문서 기안과 자료 검색을 개선하려고 합니다.", {"문서 기안"}),
    ("급여계산과 임금 명세를 관리하려고 합니다.", {"급여계산"}),
])
def test_six_business_areas_without_any_published_capability(text, expected):
    result = generate(context(text), catalog())
    assert names(result) == expected
    assert result["rule_version"] == VERSION
    assert result["alternatives"]
    assert all(c["review_status"] == "REVIEW_REQUIRED" for c in result["candidates"])
    for candidate in result["candidates"]:
        assert candidate["reasons"] and candidate["evidence"] and candidate["demand_ids"]
        assert all(e["feature_revision_id"] == candidate["revision_id"]
                   and e["quote"] in [candidate["name"], candidate["description"]]
                   for e in candidate["evidence"])


def test_single_multi_and_cross_system_alternatives_are_populated():
    ctx = context("창고 입출고를 기록하고 재고 수량과 전자결재 문서 기안을 조회하려고 합니다.")
    result = generate(ctx, catalog())
    kinds = {a["kind"] for a in result["alternatives"]}
    assert {"SINGLE_MODULE", "MULTI_MODULE", "CROSS_SYSTEM"} <= kinds
    cross = next(a for a in result["alternatives"] if a["kind"] == "CROSS_SYSTEM")
    assert len(cross["systems"]) >= 2 and len(cross["modules"]) >= 2
    assert cross["feature_selections"] and cross["coverage"] and cross["integrations"]
    exact = {f["revision_id"]: f for f in catalog()["features"]}
    for alternative in result["alternatives"]:
        assert alternative["why"] and alternative["name"] and alternative["unresolved"]
        assert all(f == exact[f["revision_id"]] for f in alternative["features"])
        for selection in alternative["feature_selections"]:
            original = exact[selection["feature_revision_id"]]
            assert selection["asset_version_id"] == original["asset_version_id"]
            assert selection["role"]
        for row in alternative["coverage"]:
            assert row["requirement"] == ctx["structured"]["as_is"]
            assert row["evidence_refs"] and row["role"]
            assert row["status"] == "PARTIAL"
            assert row["addressed_scope"] and row["unaddressed_scope"]
            assert row["missing_information"]
            assert row["capability_version_id"] is None
        assert all(i["data"] and i["workflow"] and i["uncertainty"] for i in alternative["integrations"])


@pytest.mark.parametrize("text,fields,expected", [
    ("재고 관리는 제외하고 전자결재 문서 기안을 개선하려고 합니다.", {}, {"문서 기안"}),
    ("재고 수량이 맞지 않습니다.", {"constraints": "재고 업무는 이번 구축에서 제외합니다."}, set()),
    ("근태가 아니라 급여계산과 임금 명세를 개선하려고 합니다.", {}, {"급여계산"}),
    ("급여와 무관하며 근태 기록을 통합하려고 합니다.", {}, {"근태등록"}),
    ("자동 원인분석은 제외하고 불량현황을 조회하려고 합니다.", {}, {"불량현황"}),
])
def test_explicit_scope_exclusions_are_not_whole_domain_synonyms(text, fields, expected):
    result = generate(context(text, **fields), catalog())
    assert names(result) == expected
    assert any("명시 제외" in item for item in result["limitations"])


@pytest.mark.parametrize("availability", ["UNAVAILABLE", "RETIRED"])
def test_unavailable_and_retired_features_never_become_candidates(availability):
    c = catalog()
    c["features"] = [feature("STOCK", "재고현황", "재고 수량 조회", availability=availability)]
    result = generate(context("재고 수량을 조회합니다."), c)
    assert not result["candidates"] and not result["alternatives"]
    assert result["status"] == "NO_SOLUTION"


def test_source_group_and_unverified_provision_remain_visible_as_uncertain_candidates():
    c = catalog()
    c["features"] = [feature("STOCK", "재고현황", "재고 조회")]
    c["features"][0].update(asset_version_id=None, module_version_id=None,
                           availability="AVAILABLE", mapping_status="SOURCE_GROUP_ONLY")
    result = generate(context("재고 수량을 조회합니다."), c)
    candidate = result["candidates"][0]
    assert candidate["provision_status"] == "NEEDS_CONFIRMATION"
    assert any("원천 기능그룹" in text for text in candidate["limitations"])
    assert any("제공 가능" in text for text in candidate["limitations"])
    assert result["alternatives"][0]["coverage"][0]["status"] == "PARTIAL"


def test_verified_provision_alone_does_not_confirm_company_coverage():
    c = catalog()
    c["features"] = [feature("STOCK", "재고현황", "재고 조회", availability="VERIFIED")]
    result = generate(context("재고 조회를 개선합니다."), c)
    assert result["candidates"][0]["provision_status"] == "VERIFIED"
    coverage = result["alternatives"][0]["coverage"][0]
    assert coverage["status"] == "PARTIAL" and coverage["missing_information"]


def test_system_or_module_name_alone_is_not_function_evidence():
    c = catalog()
    c["features"] = [feature("WRONG", "직원 근태", "출퇴근 기록",
                            system="재고 물류", module="입고 출고")]
    result = generate(context("재고 입출고 수량 불일치"), c)
    assert result["candidates"] == [] and result["alternatives"] == []


@pytest.mark.parametrize("text,status", [
    ("의료 영상 질환 진단 정확도가 낮습니다.", "NO_SOLUTION"),
    ("업무를 확인하고 개선하고 싶습니다.", "INPUT_INSUFFICIENT"),
    ("", "INPUT_INSUFFICIENT"),
])
def test_no_solution_and_insufficient_input_are_normal_empty_results(text, status):
    result = generate(context(text), catalog())
    assert result["status"] == status
    assert result["candidates"] == [] and result["alternatives"] == []


def test_missing_unrelated_requirement_stays_explicitly_unresolved():
    result = generate(context("재고 수량을 조회합니다.", required_functions="의료 영상 질환 진단"),
                      catalog())
    assert result["uncovered_demands"] == ["improvement:required_functions"]
    for alternative in result["alternatives"]:
        assert alternative["kind"] == "PARTIAL"
        row = next(c for c in alternative["coverage"] if c["demand_id"] == "improvement:required_functions")
        assert row["status"] == "UNRESOLVED" and row["feature_revision_ids"] == []
        assert row["addressed_scope"] == "" and row["missing_information"]


def test_exact_aliases_deduplicate_but_preserve_all_literal_evidence():
    ctx = context("재고 수량 불일치", problem="재고 수량 불일치",
                  goal="재고 오차율을 2% 이하로 낮춘다.", to_be="재고 오차율을 2% 이하로 낮춘다.")
    result = generate(ctx, catalog())
    assert len(result["demands"]) == 2
    assert {e["field"] for e in result["demands"][0]["evidence"]} == {"as_is", "problem"}
    assert {e["field"] for e in result["demands"][1]["evidence"]} == {"goal", "to_be"}
    assert all(e["version_id"] == "TEST_VERSION_A" for d in result["demands"] for e in d["evidence"])


def test_reviewed_response_evidence_and_original_numbers_are_never_rewritten():
    quote = "현재 재고 오차율은 8%이며 목표는 2%이다."
    reviewed = [dict(candidate_id="TEST_C", review_id="TEST_R", category="STRUCTURE",
        subject="goal", content=quote, evidence=[dict(kind="RESPONSE", response_id="TEST_RESPONSE",
            review_id="TEST_VERIFIED_RESPONSE_REVIEW", quote=quote)], uncertainty="검토 후보")]
    result = generate(context("재고 수량 불일치"), catalog(), reviewed)
    demand = next(d for d in result["demands"] if d["id"] == "analysis:TEST_C")
    assert demand["kind"] == "GOAL" and demand["text"] == quote
    assert demand["evidence"] == reviewed[0]["evidence"]
    for alternative in result["alternatives"]:
        row = next(r for r in alternative["coverage"] if r["demand_id"] == demand["id"])
        assert row["requirement"] == quote and row["evidence_refs"] == reviewed[0]["evidence"]
        assert row["status"] != "ADDRESSED"


def test_already_answered_tools_scope_budget_are_not_asked_again():
    ctx = context("재고를 Excel로 기록하고 바코드 리더기를 사용한다.",
        constraints="본사 창고 한 곳에만 적용한다. Excel은 유지한다. 사업비와 일정은 별도 산정한다.")
    result = generate(ctx, catalog(), limits=["TEST verified reply already answers tools"])
    assert result["alternatives"]
    for alternative in result["alternatives"]:
        assert ctx["structured"]["constraints"] in alternative["conditions"]
        missing = "\n".join(text for c in alternative["coverage"] for text in c["missing_information"])
        for question in ("기존 시스템이 무엇", "사업장은 몇", "사업비는 얼마", "일정은 언제"):
            assert question not in missing
    assert "TEST verified reply already answers tools" in result["limitations"]


def test_integrations_use_only_registered_verified_relation_evidence():
    c = catalog()
    c["features"] = [c["features"][0], c["features"][-1]]
    c["features"][0]["relations"] = [dict(target_node_id="TEST_DOCUMENT", kind="INTEGRATION",
        condition="TEST approved interface contract", verified=True, evidence="TEST interface review A")]
    result = generate(context("재고 조회와 전자결재 문서 기안을 통합합니다."), c)
    cross = next(a for a in result["alternatives"] if a["kind"] == "CROSS_SYSTEM")
    link = cross["integrations"][0]
    assert link["verification"] == "VERIFIED"
    assert link["evidence_note"] == "TEST interface review A"
    assert link["prerequisites"] == ["TEST approved interface contract"]
    c["features"][0]["relations"][0]["evidence"] = ""
    result = generate(context("재고 조회와 전자결재 문서 기안을 통합합니다."), c)
    assert next(a for a in result["alternatives"] if a["kind"] == "CROSS_SYSTEM")["integrations"][0]["verification"] == "UNVERIFIED"


def test_revision_conflicts_fail_closed_and_duplicate_exact_rows_do_not_duplicate_alternatives():
    c = catalog()
    c["features"] = [c["features"][0], deepcopy(c["features"][0])]
    result = generate(context("재고 수량 조회"), c)
    assert len(result["candidates"]) == 1 and len(result["alternatives"]) == 1
    c["features"][1]["description"] = "different immutable source"
    with pytest.raises(Denied, match="ASSET_REVISION_CONFLICT"):
        generate(context("재고 수량 조회"), c)


def test_deterministic_output_and_separate_company_version_identity_without_mutations():
    ctx, cat = context("재고 조회와 문서 기안"), catalog()
    initial = deepcopy((ctx, cat))
    first = generate(ctx, cat)
    assert first == generate(ctx, dict(cat, features=list(reversed(cat["features"]))))
    assert len({a["id"] for a in first["alternatives"]}) == len(first["alternatives"])
    other = dict(ctx, company_id="TEST_COMPANY_B", improvement_version_id="TEST_VERSION_B")
    assert {a["id"] for a in first["alternatives"]}.isdisjoint(
        a["id"] for a in generate(other, cat)["alternatives"])
    assert (ctx, cat) == initial


def test_different_numeric_literals_are_not_collapsed_as_aliases():
    result = generate(context("재고 불일치", goal="오차율 1.5%가 목표다.",
                              to_be="오차율 15%가 목표다."), catalog())
    goals = [d["text"] for d in result["demands"] if d["kind"] == "GOAL"]
    assert goals == ["오차율 1.5%가 목표다.", "오차율 15%가 목표다."]


def test_only_constraints_do_not_hide_the_original_requirement():
    ctx = context("재고 수량 불일치", constraints="본사 창고에만 적용")
    ctx["structured"].pop("as_is")
    result = generate(ctx, catalog())
    assert names(result) == {"재고현황"}
    row = next(d for d in result["demands"] if d["id"] == "improvement:original_text")
    assert row["evidence"][0]["quote"] == ctx["original_text"]


def test_registered_business_problem_is_traceable_literal_source():
    c = catalog()
    c["features"] = [feature("BUSINESS", "TEST 원천 기능", "TEST role")]
    c["features"][0]["business_areas"] = ["회계 전표 기록"]
    result = generate(context("회계 전표를 기록하려고 합니다."), c)
    candidate = result["candidates"][0]
    assert any(e["field"] == "business_areas" and e["quote"] == "회계 전표 기록"
               for e in candidate["evidence"])
    assert candidate["provision_status"] == "NEEDS_CONFIRMATION"


def test_feature_declared_exclusion_blocks_compound_demand_without_removing_other_supported_scope():
    c = catalog()
    c["features"] = [feature("MIXED", "급여계산과 근태등록", "직원 근태 기록과 급여 계산")]
    c["features"][0]["exclusions"] = ["급여계산"]
    assert generate(context("급여계산을 개선합니다."), c)["candidates"] == []
    result = generate(context("근태 기록을 관리합니다."), c)
    assert names(result) == {"급여계산과 근태등록"}
    assert "급여계산" in result["candidates"][0]["limitations"]


def test_managed_asset_version_change_changes_alternative_identity():
    c = catalog()
    before = generate(context("재고 수량 조회"), c)
    c["features"][0]["asset_version_id"] = "TEST_NEW_ASSET_VERSION"
    after = generate(context("재고 수량 조회"), c)
    assert {a["id"] for a in before["alternatives"]}.isdisjoint(a["id"] for a in after["alternatives"])
    assert before["candidates"][0]["revision_id"] == after["candidates"][0]["revision_id"]


def test_unsupported_causal_subscope_does_not_remove_source_backed_status_view():
    c = catalog()
    c["features"] = [feature("QUALITY", "품질현황", "품질 검사 기록과 불량 현황")]
    c["features"][0]["exclusions"] = ["품질 원인분석과 예측"]
    result = generate(context("품질 현황을 조회합니다."), c)
    assert names(result) == {"품질현황"}
    assert "품질 원인분석과 예측" in result["candidates"][0]["limitations"]


def test_verified_label_without_registered_provision_evidence_is_not_certified():
    c = catalog()
    c["features"] = [feature("STOCK", "재고현황", "재고 조회", availability="VERIFIED")]
    c["features"][0]["availability_evidence"] = ""
    result = generate(context("재고 수량 조회"), c)
    assert result["candidates"][0]["provision_status"] == "NEEDS_CONFIRMATION"
    assert any("제공 가능" in text for text in result["candidates"][0]["limitations"])


def managed_module(key, **data):
    return dict(id=key, name=key, kind="MODULE", version_id="TEST_MODULE_VERSION_" + key,
                availability="VERIFIED", relations=data.pop("relations", []),
                data=dict(availability="VERIFIED", **data))


def test_outdated_managed_source_mapping_is_not_a_recommendation_candidate():
    c = catalog()
    c["features"] = [c["features"][0]]
    c["features"][0]["source_current"] = False
    result = generate(context("재고 수량 조회"), c)
    assert result["candidates"] == [] and result["alternatives"] == []


def test_parent_module_exclusions_and_preconditions_are_honored_and_preserved():
    c = catalog()
    c["features"] = [c["features"][0]]
    c["modules"] = [managed_module("TEST_STOCK", exclusions=["재고 수량 조회"])]
    assert generate(context("재고 수량 조회"), c)["candidates"] == []
    c["modules"] = [managed_module("TEST_STOCK", conditions=["TEST 적용 업무 확인"],
                                  prerequisites=["TEST 필수 원천 키"])]
    result = generate(context("재고 수량 조회"), c)
    assert "TEST 적용 업무 확인" in result["alternatives"][0]["conditions"]
    assert "TEST 필수 원천 키" in result["alternatives"][0]["conditions"]
    assert "TEST 필수 원천 키" in result["candidates"][0]["limitations"]


def test_parent_module_unavailable_status_blocks_otherwise_verified_feature():
    c = catalog()
    c["features"] = [c["features"][0]]
    c["modules"] = [dict(managed_module("TEST_STOCK"), availability="RETIRED")]
    assert generate(context("재고 수량 조회"), c)["candidates"] == []


def test_projected_module_relation_takes_priority_and_stale_target_is_unverified():
    c = catalog()
    c["features"] = [c["features"][0], c["features"][-1]]
    relation = dict(kind="INTEGRATION", target_node_id="TEST_DOCUMENT",
                    target_version_id="TEST_MODULE_VERSION_TEST_DOCUMENT",
                    condition="TEST actual module interface", verified=True, current_valid=True,
                    evidence="TEST module verification record")
    node = managed_module("TEST_STOCK", relations=[relation])
    node["data"]["relations"] = [dict(relation, verified=False)]
    c["modules"] = [node, managed_module("TEST_DOCUMENT")]
    result = generate(context("재고 조회와 문서 기안"), c)
    cross = next(a for a in result["alternatives"] if a["kind"] == "CROSS_SYSTEM")
    link = cross["integrations"][0]
    assert link["verification"] == "VERIFIED"
    assert link["evidence_note"] == relation["evidence"] and relation["condition"] in link["prerequisites"]
    node["relations"][0]["current_valid"] = False
    result = generate(context("재고 조회와 문서 기안"), c)
    assert next(a for a in result["alternatives"] if a["kind"] == "CROSS_SYSTEM")["integrations"][0]["verification"] == "UNVERIFIED"


def test_dependency_is_preserved_as_precondition_and_not_a_verified_integration():
    c = catalog()
    c["features"] = [c["features"][0], c["features"][-1]]
    c["modules"] = [managed_module("TEST_STOCK", relations=[dict(kind="DEPENDENCY",
        target_node_id="TEST_DOCUMENT", condition="TEST predecessor task",
        verified=True, evidence="TEST dependency record")]), managed_module("TEST_DOCUMENT")]
    result = generate(context("재고 조회와 문서 기안"), c)
    cross = next(a for a in result["alternatives"] if a["kind"] == "CROSS_SYSTEM")
    assert cross["integrations"][0]["verification"] == "UNVERIFIED"
    assert "TEST predecessor task" in cross["integrations"][0]["prerequisites"]
    assert "선행 의존조건: TEST predecessor task" in next(c for c in result["candidates"] if c["name"] == "재고현황")["limitations"]


def test_long_labels_fit_composition_contract_without_losing_source_text_or_conditions():
    ctx = context("재고 수량 조회와 입고 기록 " * 500, goal="문서 기안과 전자결재 " * 500)
    c = dict(digest="TEST long inputs", systems=[], modules=[], features=[])
    for prefix, task, system, module in (
            ("STOCK", "재고 현황 조회", "TEST_ERP", "TEST_STOCK"),
            ("INPUT", "입고 등록 기록", "TEST_ERP", "TEST_INPUT"),
            ("DOC", "문서 기안 결재", "TEST_GROUPWARE", "TEST_DOCUMENT")):
        for i in range(9):
            f = feature(prefix + str(i), task + str(i) + "명" * 480, "TEST " + task,
                        system=system, module=module, availability="VERIFIED")
            f["system_name"] = system + "체" * 480
            f["module_name"] = module + "듈" * 480
            f["prerequisites"] = ["TEST " + prefix + str(i) + " condition " + str(j) for j in range(20)]
            c["features"].append(f)
    required = "TEST exact reviewed interface condition " + "건" * 500
    c["features"][0]["relations"] = [dict(kind="INTEGRATION", target_node_id="TEST_DOCUMENT",
        target_version_id="TEST_MODULE_VERSION_TEST_DOCUMENT", condition=required,
        verified=True, current_valid=True, evidence="TEST exact integration proof")]
    original = deepcopy(c)
    result = generate(ctx, c)
    cross = next(a for a in result["alternatives"] if a["topology_kind"] == "CROSS_SYSTEM")
    assert len(cross["name"]) <= 500 and "상세" in cross["name"]
    raw = {f["revision_id"]: f for f in original["features"]}
    assert all(f == raw[f["revision_id"]] for f in cross["features"])
    assert max(len(row["role"]) for row in cross["coverage"]) <= 2000
    assert max(len(row["addressed_scope"]) for row in cross["coverage"]) <= 5000
    assert any("상세" in row["addressed_scope"] for row in cross["coverage"])
    original_demands = {ctx["structured"]["as_is"], ctx["structured"]["goal"]}
    assert {row["requirement"] for row in cross["coverage"]} == original_demands
    assert all(e["quote"] in original_demands for row in cross["coverage"] for e in row["evidence_refs"])
    for link in cross["integrations"]:
        assert len(link["data"]) <= 5000 and len(link["workflow"]) <= 5000
        assert len(link["prerequisites"]) <= 100
        if link["verification"] == "VERIFIED":
            assert link["prerequisites"][0] == required
            assert link["evidence_note"] == "TEST exact integration proof"
            # The two endpoint modules contribute sixteen selected features.
            endpoint_features = [f for f in cross["features"]
                                 if f["module_id"] in {link["from_asset_id"], link["to_asset_id"]}]
            expected = [value for f in endpoint_features for value in f["prerequisites"]]
            assert len(expected) > 100
            assert all(any(value in entry for entry in link["prerequisites"]) for value in expected)
            assert link["prerequisites"][-1].startswith("추가 조건 원문 전체")
    assert c == original


def test_verified_condition_keeps_exact_separate_item_when_other_conditions_overflow():
    c = catalog()
    c["features"] = [c["features"][0], c["features"][-1]]
    c["features"][0]["prerequisites"] = ["TEST original condition " + str(i) for i in range(120)]
    c["features"][0]["relations"] = [dict(kind="INTEGRATION", target_node_id="TEST_DOCUMENT",
        condition="TEST exact authority condition", verified=True, current_valid=True,
        evidence="TEST exact authority evidence")]
    result = generate(context("재고 수량 조회와 문서 기안"), c)
    link = next(a for a in result["alternatives"] if a["kind"] == "CROSS_SYSTEM")["integrations"][0]
    assert link["verification"] == "VERIFIED"
    assert len(link["prerequisites"]) == 100
    assert link["prerequisites"][0] == "TEST exact authority condition"
    assert all(any(condition in entry for entry in link["prerequisites"])
               for condition in c["features"][0]["prerequisites"])
