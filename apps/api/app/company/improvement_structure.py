"""Role-aware literal extraction and bounded function hypotheses, never facts/services."""
import re
import unicodedata
from app.company.improvement_language import active_match

ALIASES = {"to_be": "goal", "현황": "as_is", "현재 업무": "as_is",
           "현재 문제점": "as_is", "문제": "problem", "문제점": "problem",
           "목표": "goal", "개선 목표": "goal", "희망 개선목표": "goal",
           "필요 기능": "required_functions", "요구 기능": "required_functions",
           "제약사항": "constraints", "원인": "원인 후보"}
ISSUE = r"불일치|일치하지|누락|오류|지연|중복|분리|불량|하자|어려|불편|일치하지"
FUNCTIONS = (
    ("STOCK_HISTORY", "입출고 이력 관리", r"(?:입출고|입고|출고).{0,25}(?:이력|기록|등록|관리)"),
    ("STOCK_STATUS", "재고 현황 관리", r"재고.{0,35}(?:현황|확인|조회|파악|일치|관리)"),
    ("DUPLICATE_ENTRY", "중복 입력 감소 검토", r"(?:입력|기록|집계).{0,12}중복|중복.{0,12}(?:입력|기록|집계)"),
    ("DATA_LINK", "업무·데이터 연계 검토", r"(?:이력|정보|데이터|기록).{0,35}(?:통합|연계|연동)|(?:통합|연계|연동).{0,25}(?:이력|정보|데이터|기록)"),
    ("PRODUCTION_RECORD", "생산·작업 실적 관리", r"(?:생산|작업).{0,15}(?:실적|진행|이력).{0,15}(?:기록|조회|집계|관리|확인)"),
    ("QUALITY_RECORD", "품질·불량 현황 관리", r"(?:불량|검사|품질).{0,20}(?:이력|현황|집계|기록|조회|관리)"),
    ("ATTENDANCE", "근태·출퇴근 기록 관리", r"(?:근태|출퇴근|출근|퇴근|휴가).{0,20}(?:기록|집계|조회|확인|관리)"),
    ("ACCOUNTING_RECORD", "회계·전표 처리 관리", r"(?:전표|회계|결산|정산).{0,20}(?:입력|기록|조회|집계|처리|관리)"),
    ("DOCUMENT_FLOW", "문서·결재 흐름 관리", r"(?:문서|결재).{0,20}(?:공유|처리|조회|이력|관리)"),
)

FUNCTION_SCOPE = {
    "STOCK_HISTORY": r"입출고|입고|출고", "STOCK_STATUS": r"재고",
    "DUPLICATE_ENTRY": r"중복\s*입력|입력\s*중복",
    "DATA_LINK": r"연계|연동|통합", "PRODUCTION_RECORD": r"생산|작업실적",
    "QUALITY_RECORD": r"품질|불량|검사", "ATTENDANCE": r"근태|출퇴근|출근|퇴근|휴가",
    "ACCOUNTING_RECORD": r"회계|전표|결산|정산", "DOCUMENT_FLOW": r"문서|결재",
}



def normalized(text):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text)).strip("。.!?;；")


def origin(source):
    # Aliased fields in one submitted version are one source. Different document
    # evidence, response reviews and versions must remain independently reviewable.
    if source.get("kind") == "IMPROVEMENT":
        return ("IMPROVEMENT", source.get("version_id"))
    return tuple(source.get(k) for k in ("kind", "version_id", "evidence_id",
                 "file_id", "inspection_id", "response_id", "review_id", "page", "descriptor"))


def function_derivation(content, derivation, evidence):
    for identifier, label, pattern in FUNCTIONS:
        if content != label or derivation.get("id") != identifier:
            continue
        matched = [active_match(e["quote"], pattern) for e in evidence]
        fragments = [m.group(0) for m in matched if m]
        return (derivation.get("method") == "BOUNDED_LITERAL_MAPPING"
                and bool(fragments) and derivation.get("matched_quotes") == fragments)
    return False


def extract(data, spans):
    records, index = [], {}
    def emit(subject, text, sources, claim="DIRECT_SOURCE", derivation=None):
        text = text.strip()
        if not text:
            return
        subject = ALIASES.get(subject, subject)
        key = (subject, normalized(text), origin(sources[0]), (derivation or {}).get("id"))
        if key in index:
            old = index[key]
            for source in sources:
                if source not in old["evidence"]:
                    old["evidence"].append(source)
            return
        record = dict(subject=subject, text=text, evidence=list(sources), claim_kind=claim)
        if derivation:
            record["derivation"] = derivation
        records.append(record)
        index[key] = record

    def current(text, sources):
        clauses = [s.strip() for s in re.split(r"[,，。.!?;；\n]", text) if s.strip()]
        emit("as_is", text, sources)
        for clause in clauses:
            if re.search(ISSUE, clause) and normalized(clause) != normalized(text):
                emit("problem", clause, sources)

    typed = [s for s in spans if s.get("kind") == "IMPROVEMENT"
             and s.get("field") in ("as_is", "problem", "impact", "goal", "to_be", "required_functions", "constraints")]
    consumed = set()
    for source in typed:
        field, value = source["field"], source["quote"]
        group = [s for s in typed if origin(s) == origin(source)
                 and normalized(s["quote"]) == normalized(value)
                 and (s["field"] in ("as_is", "problem") if field in ("as_is", "problem")
                      else ALIASES.get(s["field"], s["field"]) == ALIASES.get(field, field))]
        group_key = (origin(source), normalized(value), "current" if field in ("as_is", "problem") else ALIASES.get(field, field))
        if group_key in consumed:
            continue
        consumed.add(group_key)
        if any(s["field"] == "as_is" for s in group):
            current(value, group)
        else:
            emit(field, value, group)

    labels = r"현황|현재 업무|문제|문제점|개선 목표|목표|필요 기능|요구 기능|원인 후보|원인"
    for source in spans:
        if source.get("kind") not in ("DOCUMENT", "IMPROVEMENT", "EVIDENCE", "RESPONSE"):
            continue
        for line in source["quote"].splitlines():
            match = re.fullmatch(r"\s*(" + labels + r")\s*[:：]\s*(.{1,2000})\s*", line)
            if match:
                subject = ALIASES.get(match[1], match[1])
                if subject == "as_is":
                    current(match[2], [source])
                else:
                    emit(subject, match[2], [source], "INFERRED" if subject == "원인 후보" else "DIRECT_SOURCE")
        if source.get("kind") == "IMPROVEMENT" and source.get("field") == "original_text" and not typed:
            # Unlabelled prose has no reliable goal/current role: classify only
            # explicit issue clauses; do not call every automation/goal a problem.
            for clause in re.split(r"[。.!?;；\n]", source["quote"]):
                clause = clause.strip()
                if (6 <= len(clause) <= 2000 and re.search(ISSUE, clause)
                        and not re.search(r"목표|희망|줄이|줄여|낮추|개선하고|원합|필요|제외", clause)
                        and not re.match(r"\s*(?:" + labels + r")\s*[:：]", clause)):
                    emit("problem", clause, [source])

    # Function names are hypotheses from explicit task expressions, never a claim
    # that a published service exists or can cover the task.
    sources = [s for s in typed if s["field"] in ("as_is", "problem", "goal", "to_be", "required_functions")]
    if not sources:
        sources = [s for s in spans if s.get("kind") == "IMPROVEMENT" and s.get("field") == "original_text"]
    for identifier, label, pattern in FUNCTIONS:
        intent = [s for s in typed if s["field"] in ("goal", "to_be", "required_functions", "constraints")]
        groups = {}
        for source in sources:
            match = active_match(source["quote"], pattern)
            if match:
                groups.setdefault(origin(source), []).append(source)
        for source_group in groups.values():
            same_input = [s for s in intent if origin(s) == origin(source_group[0])]
            if any(re.search(FUNCTION_SCOPE[identifier],s["quote"]) and not active_match(s["quote"],FUNCTION_SCOPE[identifier]) for s in same_input):
                continue
            if any(r["subject"] == "required_functions" and normalized(label) in normalized(r["text"])
                   and origin(r["evidence"][0]) == origin(source_group[0]) for r in records):
                continue
            # Exact aliases share one hypothesis but retain all contributing spans.
            fragments = [active_match(s["quote"], pattern).group(0) for s in source_group]
            emit("required_functions", fragments[0], source_group, "INFERRED",
                 dict(id=identifier, method="BOUNDED_LITERAL_MAPPING", matched_quotes=fragments))
            records[-1]["function_label"] = label
    return records
