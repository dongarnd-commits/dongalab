"""User E2E regression, field roles and literal provenance across businesses."""
from copy import deepcopy
import pytest
from app.company.improvement_rules import analyze, validate
from app.company.improvement_providers import execute_provider, AnalysisContext

CURRENT = "창고 입출고 내역을 엑셀과 수기로 관리하고, 재고 수량이 실제 재고와 일치하지 않는 경우가 발생합니다."
GOAL = "입출고 이력과 재고정보를 통합 관리하고, 데이터 입력 중복을 줄여 재고 현황을 신속하게 확인하는 것입니다."


def source(text, field, version="SUBMITTED_V1"):
    return dict(kind="IMPROVEMENT", version_id=version, field=field, quote=text)


def case(current=CURRENT, goal=GOAL):
    data = dict(as_is=current, problem=current, to_be=goal, goal=goal)
    return data, [source(value, field) for field, value in data.items()]


def test_user_case_roles_are_not_duplicated_or_goal_misclassified():
    data, spans = case()
    result = execute_provider("RULE", AnalysisContext("TEST_COMPANY", "SUBMITTED_V1", "f" * 64), data, spans)
    structures = [c for c in result.candidates if c["category"] == "STRUCTURE"]
    assert len([c for c in structures if c["content"] == GOAL]) == 1
    assert result.structure["goals"][0]["text"] == GOAL
    assert all(GOAL not in item["text"] for item in result.structure["problems"])
    assert any("일치하지" in item["text"] for item in result.structure["problems"])
    assert any("엑셀" in item["text"] for item in result.structure["current_state"])
    assert {c["data"]["subject"] for c in structures} <= {"as_is", "problem", "goal", "required_functions"}
    # Alias spans are retained, not erased to hide repeated output.
    assert {e["field"] for e in result.structure["goals"][0]["evidence"]} == {"goal", "to_be"}
    labels = {item["text"] for item in result.structure["required_functions"]}
    assert {"입출고 이력 관리", "재고 현황 관리", "중복 입력 감소 검토", "업무·데이터 연계 검토"} <= labels
    assert all(item["claim_kind"] == "INFERRED" for item in result.structure["required_functions"])
    assert result.structure["cause_candidates"] == []
    assert any(c["category"] == "MISSING_INFORMATION" and c["data"]["rule_id"] == "R04" for c in result.candidates)
    for candidate in result.candidates:
        validate(candidate, spans)
        if candidate["category"] == "STRUCTURE":
            assert any(candidate["content"] in e["quote"] for e in candidate["data"]["evidence"])
        assert candidate["data"]["claim_kind"] != "CONFIRMED_FACT"


@pytest.mark.parametrize("current,goal,label", [
    ("작업 실적이 분리되어 생산 현황을 확인하기 어렵다.", "생산 실적을 기록하고 조회하고 싶다.", "생산·작업 실적 관리"),
    ("검사 결과와 불량 현황을 수기로 집계한다.", "불량 현황을 조회하고 검사 이력을 관리한다.", "품질·불량 현황 관리"),
    ("근태 기록과 출퇴근 집계가 중복된다.", "근태 기록을 통합 관리하고 휴가 이력을 조회한다.", "근태·출퇴근 기록 관리"),
    ("회계 전표 입력이 중복되고 결산이 지연된다.", "전표 입력과 정산 처리를 관리한다.", "회계·전표 처리 관리"),
    ("문서공유와 결재 내역이 분리되어 누락된다.", "문서 공유와 결재 이력을 관리한다.", "문서·결재 흐름 관리"),
])
def test_other_business_roles_and_literal_function_evidence(current, goal, label):
    data, spans = case(current, goal)
    before = deepcopy(spans)
    output, _ = analyze(data, spans)
    assert len([c for c in output if c["category"] == "STRUCTURE" and c["content"] == goal]) == 1
    assert not any(c["data"]["subject"] == "problem" and goal == c["content"] for c in output)
    function = next(c for c in output if c["data"].get("function_label", c["content"]) == label)
    assert function["data"]["claim_kind"] == "INFERRED"
    assert function["data"]["derivation"]["matched_quotes"]
    for candidate in output:
        validate(candidate, spans)
    assert spans == before


def test_explicit_function_text_remains_direct_and_not_repeated_as_inference():
    data, spans = case()
    data["required_functions"] = "입출고 이력 관리"
    spans.append(source(data["required_functions"], "required_functions"))
    output, _ = analyze(data, spans)
    found = [c for c in output if c["content"] == "입출고 이력 관리"]
    assert len(found) == 1 and found[0]["data"]["claim_kind"] == "DIRECT_SOURCE"


def test_different_source_versions_and_document_evidence_are_not_merged():
    spans = [source("목표: 재고 현황 조회", "original_text", v) for v in ("V1", "V2")]
    spans += [dict(kind="DOCUMENT", file_id=f, evidence_id=f, quote="목표: 재고 현황 조회") for f in ("FILE_A", "FILE_B")]
    output, _ = analyze({}, spans)
    goals = [c for c in output if c["category"] == "STRUCTURE" and c["data"]["subject"] == "goal"]
    assert len(goals) == 4
    assert {e.get("version_id") or e["file_id"] for c in goals for e in c["data"]["evidence"]} == {"V1", "V2", "FILE_A", "FILE_B"}


@pytest.mark.parametrize("field,value", [
    ("content", "지원금 1억원 자동 확보"),
    ("derivation", {"id": "FAKE", "method": "BOUNDED_LITERAL_MAPPING", "matched_quotes": ["없는 인용"]}),
])
def test_inferred_function_cannot_fabricate_content_or_derivation(field, value):
    data, spans = case()
    output, _ = analyze(data, spans)
    candidate = deepcopy(next(c for c in output if c["data"].get("derivation")))
    if field == "content":
        candidate[field] = value
    else:
        candidate["data"][field] = value
    with pytest.raises(ValueError, match="INVALID_EXTRACTED_VALUE"):
        validate(candidate, spans)


def test_goal_with_issue_words_stays_goal_in_composed_original_text():
    data, spans = case()
    original = "현재 문제점 (As-Is)\n" + CURRENT + "\n희망 개선목표 (To-Be)\n" + GOAL
    spans.append(source(original, "original_text"))
    output, _ = analyze(data, spans)
    assert not any(c["data"]["subject"] == "problem" and GOAL in c["content"] for c in output)
    assert len([c for c in output if c["content"] == GOAL]) == 1


def test_excluded_function_is_not_generated_from_goal():
    data, spans = case("재고 차이 발생", "급여 계산은 제외하고 재고 현황을 조회한다.")
    output, _ = analyze(data, spans)
    assert any(c["data"].get("function_label") == "재고 현황 관리" for c in output)
    assert not any("급여" in c["content"] for c in output if c["data"]["subject"] == "required_functions")

def test_stated_site_count_and_existing_excel_are_not_asked_again():
    data, spans = case("창고 1개 사업장에서 엑셀과 수기로 입출고를 기록한다.", "기존 시스템과 입출고 이력을 연계한다.")
    output, diagnostics = analyze(data, spans)
    assert not any(c["category"] == "MISSING_INFORMATION" and c["data"]["rule_id"] in ("R04", "R05") for c in output)
    assert next(d for d in diagnostics if d["rule"] == "R04")["outcome"] == "FOUND"
    assert next(d for d in diagnostics if d["rule"] == "R05")["outcome"] == "FOUND"


def test_unread_attachment_and_reviewed_scope_answer_remain_distinct():
    data, spans = case()
    coverage=[dict(inspection_id="UNREAD",status="FAILED",origin="DIRECT_ATTACHMENT",locations=[])]
    output, _ = analyze(data, spans, coverage=coverage)
    assert not any(c["category"] == "MISSING_INFORMATION" for c in output)
    assert any(c["category"] == "PROCESSING_LIMITATION" and c["data"]["rule_id"] == "R04" for c in output)
    spans.append(dict(kind="RESPONSE",response_id="REPLY",review_id="VERIFIED_REVIEW",quote="적용 범위: 본사 창고 1개 사업장"))
    after, diagnostics = analyze(data, spans, coverage=coverage)
    assert not any(c["data"]["rule_id"] == "R04" for c in after)
    assert next(d for d in diagnostics if d["rule"] == "R04")["evidence"] == [spans[-1]]

def test_current_problem_cannot_override_excluded_future_function():
    data, spans = case("재고 현황을 조회하고 관리하기 어렵다.", "재고 현황 관리는 이번 개선에서 제외하고 근태 기록을 관리한다.")
    output, _ = analyze(data, spans)
    labels = {c["data"].get("function_label") for c in output}
    assert "재고 현황 관리" not in labels
    assert "근태·출퇴근 기록 관리" in labels

def test_exclusion_in_another_version_does_not_override_the_exact_input():
    spans=[source("재고 현황을 조회하고 관리한다.","to_be","V1"),
           source("재고 현황 관리는 제외한다.","to_be","V2")]
    output,_=analyze({},spans)
    functions=[c for c in output if c["data"].get("function_label")=="재고 현황 관리"]
    assert len(functions)==1
    assert {e["version_id"] for e in functions[0]["data"]["evidence"]}=={"V1"}


def test_composed_original_goal_number_is_not_a_current_measurement():
    data,spans=case("업무 처리시간을 개선해야 한다.","처리시간을 5분으로 줄인다.")
    spans.append(source("현재 문제점 (As-Is)\n"+data["as_is"]+"\n희망 개선목표 (To-Be)\n"+data["to_be"],"original_text"))
    output,diagnostics=analyze(data,spans)
    assert any(c["category"]=="MISSING_INFORMATION" and c["data"]["rule_id"]=="R02" for c in output)
    assert next(d for d in diagnostics if d["rule"]=="R02")["outcome"]=="NOT_FOUND_IN_SCOPE"


def test_goal_with_word_current_does_not_fabricate_observed_value():
    data,spans=case("업무 처리시간을 개선해야 한다.","현재 대비 처리시간을 5분으로 단축하는 것이 목표다.")
    output,diagnostics=analyze(data,spans)
    assert any(c["data"]["rule_id"]=="R02" and c["category"]=="MISSING_INFORMATION" for c in output)


def test_explicit_later_budget_schedule_estimation_is_not_repeated_question():
    data,spans=case("업무 개선을 검토한다.","사업비와 일정은 근거 확인 후 별도 산정한다.")
    output,diagnostics=analyze(data,spans)
    assert not any(c["data"]["rule_id"] in ("R06","R07") for c in output)
    assert all(next(d for d in diagnostics if d["rule"]==rule)["outcome"]=="DECLARED_UNKNOWN" for rule in ("R06","R07"))


@pytest.mark.parametrize("current,excluded,label", [
    ("회계 전표 입력을 수기로 처리해 오류가 발생합니다.", "회계 업무는 이번 개선 대상에서 제외합니다.", "회계·전표 처리 관리"),
    ("재고 현황을 조회하고 관리하기 어렵습니다.", "재고 업무는 이번 개선 대상에서 제외합니다.", "재고 현황 관리"),
    ("근태 기록을 수기로 관리해 집계가 지연됩니다.", "근태 업무는 이번 개선 대상에서 제외합니다.", "근태·출퇴근 기록 관리"),
])
def test_explicit_excluded_business_area_suppresses_current_function_hypothesis(current, excluded, label):
    data, spans=case(current,excluded)
    output,_=analyze(data,spans)
    assert label not in {c["data"].get("function_label") for c in output}
    assert any(c["category"]=="STRUCTURE" and current==c["content"] for c in output)


# Fresh synthetic cases for the 2026-11-04 text-only requirements defect.
# These paragraphs are independent of the running acceptance environment.
@pytest.mark.parametrize("current", [
    "입력 오류가 발생합니다.",
    "진행현황을 확인하기 어렵습니다.",
    "진행현황을 확인하기 어려워요.",
])
def test_single_issue_sentence_is_problem_without_duplicate_current_state(current):
    data,spans=case(current,"기록을 조회한다.")
    output,_=analyze(data,spans)
    problems=[c for c in output if c["category"]=="STRUCTURE" and c["data"]["subject"]=="problem"]
    assert [c["content"] for c in problems]==[current]
    assert not any(c["data"]["subject"]=="as_is" for c in output)
    assert {e["field"] for e in problems[0]["data"]["evidence"]}=={"as_is","problem"}
    for candidate in output:validate(candidate,spans)


def test_activity_and_issue_are_distinct_literal_ranges_and_goal_is_not_repeated():
    current="주문을 수기로 접수합니다. 작업 배정 기록이 누락됩니다."
    goal="담당자별 작업 이력을 조회하고 같은 정보를 여러 번 입력하는 일을 줄입니다."
    data,spans=case(current,goal)
    output,_=analyze(data,spans)
    current_items=[c["content"] for c in output if c["data"]["subject"]=="as_is"]
    problem_items=[c["content"] for c in output if c["data"]["subject"]=="problem"]
    assert current_items==["주문을 수기로 접수합니다"]
    assert problem_items==["작업 배정 기록이 누락됩니다"]
    assert not set(current_items)&set(problem_items)
    assert sum(c["category"]=="STRUCTURE" and c["content"]==goal for c in output)==1
    for candidate in output:validate(candidate,spans)


def test_explicit_task_list_has_separate_bounded_function_hypotheses():
    current="주문과 작업 배정 내역이 다른 문서에 있어 진행현황을 확인하기 어렵습니다."
    goal="주문 접수, 작업 배정, 진행현황, 검수 결과, 출하, 담당자별 이력을 한 곳에서 조회하고 같은 정보를 여러 번 입력하는 일을 줄입니다."
    data,spans=case(current,goal)
    data["constraints"]="기존 회계 프로그램은 유지합니다. 인사급여와 신규 센서 및 생산설비 연계는 제외합니다."
    spans.append(source(data["constraints"],"constraints"))
    output,_=analyze(data,spans)
    labels={c["data"].get("function_label") for c in output}
    assert {"주문 접수·조회","담당자·작업 배정","작업 진행현황 조회","검수 결과·이력 관리",
            "출하·배송 이력 관리","담당자별 업무 이력 조회","중복 입력 감소 검토"}<=labels
    assert "문서·결재 흐름 관리" not in labels
    assert "회계·전표 처리 관리" not in labels
    for c in output:
        validate(c,spans)
        if c["data"].get("function_label"):
            assert c["data"]["claim_kind"]=="INFERRED"
            assert c["data"]["derivation"]["method"]=="BOUNDED_LITERAL_MAPPING"
            assert "제공" in c["data"]["uncertainty"] and "확인 필요" in c["data"]["uncertainty"]


@pytest.mark.parametrize("goal,label", [
    ("수주 내용을 접수하고 조회합니다.","주문 접수·조회"),
    ("업무를 담당자에게 할당합니다.","담당자·작업 배정"),
    ("작업 진척을 파악하고 공유합니다.","작업 진행현황 조회"),
    ("검품 결과를 기록하고 조회합니다.","검수 결과·이력 관리"),
    ("배송 내역을 등록하고 확인합니다.","출하·배송 이력 관리"),
    ("작업자 기준으로 처리 이력을 검색합니다.","담당자별 업무 이력 조회"),
    ("동일한 자료를 반복 입력하는 일을 줄입니다.","중복 입력 감소 검토"),
])
def test_equivalent_task_expressions_keep_quotes_and_do_not_claim_catalog_availability(goal,label):
    data,spans=case("현재 자료는 종이에 보관합니다.",goal)
    output,_=analyze(data,spans)
    found=next(c for c in output if c["data"].get("function_label")==label)
    assert found["content"] in goal
    assert all(e in spans for e in found["data"]["evidence"])
    assert found["data"]["claim_kind"]=="INFERRED"
    assert "VERIFIED" not in str(found["data"])
    validate(found,spans)


@pytest.mark.parametrize("excluded,label", [
    ("주문 접수는 이번 대상에서 제외합니다.","주문 접수·조회"),
    ("담당자 작업 배정은 필요 없습니다.","담당자·작업 배정"),
    ("작업 진행현황 조회를 원하지 않습니다.","작업 진행현황 조회"),
    ("검수 결과를 등록하지 않습니다.","검수 결과·이력 관리"),
    ("출하 이력 관리는 도입하지 않습니다.","출하·배송 이력 관리"),
    ("담당자별 이력 조회는 제외합니다.","담당자별 업무 이력 조회"),
])
def test_excluded_or_opposed_task_is_not_a_function_requirement(excluded,label):
    data,spans=case("주문 접수와 작업 배정, 검수 결과, 출하 이력 및 담당자별 이력을 조회합니다.",excluded)
    output,_=analyze(data,spans)
    assert label not in {c["data"].get("function_label") for c in output}
    for candidate in output:validate(candidate,spans)


def test_positive_task_is_not_suppressed_by_another_business_exclusion():
    data,spans=case("종이 자료로 현황을 확인합니다.","검수 결과를 조회하고 인사 급여는 제외합니다.")
    output,_=analyze(data,spans)
    assert "검수 결과·이력 관리" in {c["data"].get("function_label") for c in output}
    assert not any(c["data"].get("function_label")=="근태·출퇴근 기록 관리" for c in output)


@pytest.mark.parametrize("goal", [
    "사무실 문서에 지난 담당자 이름과 이력이 적혀 있습니다.",
    "주문과 검수라는 단어의 뜻을 설명합니다.",
    "배송이라는 제목을 검토합니다.",
])
def test_unrelated_words_without_task_action_do_not_create_new_task_functions(goal):
    data,spans=case("회사 자료를 보관합니다.",goal)
    output,_=analyze(data,spans)
    new_ids={"ORDER_INTAKE","WORK_ASSIGNMENT","WORK_PROGRESS","ACCEPTANCE_RECORD","SHIPMENT_RECORD","PERSON_HISTORY"}
    assert not any(c["data"].get("derivation",{}).get("id") in new_ids for c in output)


def test_new_function_exclusion_is_scoped_to_the_exact_source_version():
    spans=[source("검수 결과를 조회합니다.","to_be","V1"),source("검수 업무는 제외합니다.","constraints","V2")]
    output,_=analyze({},spans)
    found=next(c for c in output if c["data"].get("function_label")=="검수 결과·이력 관리")
    assert {e["version_id"] for e in found["data"]["evidence"]}=={"V1"}


def test_separate_future_workflow_and_explicit_outcome_keep_distinct_literal_sources():
    workflow="주문을 등록하고 작업을 배정하며 검수 결과와 출하 이력을 조회합니다."
    outcome="중복 기록과 자료를 찾는 작업을 줄이는 것이 목표입니다."
    data,spans=case("주문을 수기로 정리합니다. 담당자 기록이 누락됩니다.",workflow+" "+outcome)
    output,_=analyze(data,spans)
    goals=[c for c in output if c["category"]=="STRUCTURE" and c["data"]["subject"]=="goal"]
    futures=[c for c in output if c["category"]=="STRUCTURE" and c["data"]["subject"]=="to_be"]
    assert [c["content"] for c in goals]==[outcome]
    assert [c["content"] for c in futures]==[workflow]
    assert {e["field"] for e in futures[0]["data"]["evidence"]}=={"goal","to_be"}
    assert not {c["content"] for c in goals}&{c["content"] for c in futures}
    for candidate in output:validate(candidate,spans)


def test_company_three_field_input_does_not_need_legacy_problem_or_goal_aliases():
    data=dict(as_is="주문은 종이에 정리합니다. 작업 배정이 누락됩니다.",
              to_be="주문을 등록하고 담당자를 배정합니다. 중복 기록을 줄이고 싶습니다.",
              constraints="인사급여와 설비 연계는 제외합니다.")
    spans=[source(value,field) for field,value in data.items()]
    output,_=analyze(data,spans)
    for subject in ("as_is","problem","goal","to_be"):
        assert any(c["category"]=="STRUCTURE" and c["data"]["subject"]==subject for c in output)
    for candidate in output:validate(candidate,spans)


def test_single_parallel_feature_list_is_not_copied_into_both_future_roles():
    text="주문 접수, 작업 배정, 검수 이력, 출하 이력을 조회합니다."
    data,spans=case("현황을 확인하기 어렵습니다.",text)
    output,_=analyze(data,spans)
    goals=[c["content"] for c in output if c["category"]=="STRUCTURE" and c["data"]["subject"] in ("goal","to_be")]
    assert goals==[text]


@pytest.mark.parametrize("current", [
    "주문 기록에 누락이 없습니다.",
    "검수 기록은 오류 없이 보관합니다.",
    "진행현황을 확인하기 어렵지 않습니다.",
])
def test_explicit_absence_of_an_issue_is_not_classified_as_a_problem(current):
    data,spans=case(current,"담당자별 이력을 조회합니다.")
    output,_=analyze(data,spans)
    assert not any(c["category"]=="STRUCTURE" and c["data"]["subject"]=="problem" for c in output)
    assert any(c["category"]=="STRUCTURE" and c["data"]["subject"]=="as_is" and c["content"]==current for c in output)


def test_explicit_exclusion_header_suppresses_the_matching_task_only():
    data,spans=case("검수 결과와 출하 이력을 조회합니다.","출하 이력을 조회하고 싶습니다.")
    spans.append(source("제외 범위: 검수 결과 관리","constraints"))
    output,_=analyze(data,spans)
    labels={c["data"].get("function_label") for c in output}
    assert "검수 결과·이력 관리" not in labels
    assert "출하·배송 이력 관리" in labels
