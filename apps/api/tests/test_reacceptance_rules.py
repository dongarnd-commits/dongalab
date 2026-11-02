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
