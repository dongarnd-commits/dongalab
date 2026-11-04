"""Role-aware literal extraction and bounded function hypotheses, never facts/services."""
import re
import unicodedata
from app.company.improvement_language import active_match

ALIASES = {"to_be": "goal", "현황": "as_is", "현재 업무": "as_is",
           "현재 문제점": "as_is", "문제": "problem", "문제점": "problem",
           "목표": "goal", "개선 목표": "goal", "희망 개선목표": "goal",
           "필요 기능": "required_functions", "요구 기능": "required_functions",
           "제약사항": "constraints", "제약 사항": "constraints", "제약": "constraints",
           "제외범위": "constraints", "제외 범위": "constraints", "적용 범위": "constraints", "원인": "원인 후보"}
ISSUE = r"불일치|일치하지|누락|오류|지연|중복|분리|불량|하자|어려|어렵|불편"
FUNCTIONS = (
    ("STOCK_HISTORY", "입출고 이력 관리", r"(?:입출고|입고|출고).{0,25}(?:이력|기록|등록|관리)"),
    ("STOCK_STATUS", "재고 현황 관리", r"재고.{0,35}(?:현황|확인|조회|파악|일치|관리)"),
    ("DUPLICATE_ENTRY", "중복 입력 감소 검토", r"(?:입력|기록|집계).{0,12}중복|중복.{0,12}(?:입력|기록|집계)|(?:반복|재)\s*입력|(?:같은|동일한?)\s*(?:정보|자료|내용|데이터)[^。.!?;；\n]{0,15}?(?:여러\s*번|반복)[^。.!?;；\n]{0,12}?입력"),
    ("DATA_LINK", "업무·데이터 연계 검토", r"(?:이력|정보|데이터|기록).{0,35}(?:통합|연계|연동)|(?:통합|연계|연동).{0,25}(?:이력|정보|데이터|기록)"),
    ("PRODUCTION_RECORD", "생산·작업 실적 관리", r"(?:생산|작업).{0,15}(?:실적|진행|이력).{0,15}(?:기록|조회|집계|관리|확인)"),
    ("QUALITY_RECORD", "품질·불량 현황 관리", r"(?:불량|검사|품질).{0,20}(?:이력|현황|집계|기록|조회|관리)"),
    ("ATTENDANCE", "근태·출퇴근 기록 관리", r"(?:근태|출퇴근|출근|퇴근|휴가).{0,20}(?:기록|집계|조회|확인|관리)"),
    ("ACCOUNTING_RECORD", "회계·전표 처리 관리", r"(?:전표|회계|결산|정산).{0,20}(?:입력|기록|조회|집계|처리|관리)"),
    ("DOCUMENT_FLOW", "문서·결재 흐름 관리", r"문서(?:를|의|는|은)?\s*(?:공유|처리|조회|이력|관리)|결재[^。.!?;；\n]{0,20}?(?:공유|처리|조회|이력|관리)"),
    ("ORDER_INTAKE", "주문 접수·조회", r"(?:주문|수주)(?:\s*(?:정보|내역|내용|건))?[^,，。.!?;；\n]{0,18}?(?:접수|등록|입력|조회|관리)"),
    ("WORK_ASSIGNMENT", "담당자·작업 배정", r"(?:작업|업무|담당자|작업자|인력)[^,，。.!?;；\n]{0,18}?(?:배정|할당|배분|배치)"),
    ("WORK_PROGRESS", "작업 진행현황 조회", r"(?:진행\s*(?:현황|상태)|작업\s*(?:진척|현황|상태)|업무\s*(?:진행|진척))[^。.!?;；\n]{0,70}?(?:조회|확인|파악|공유|추적|관리)"),
    ("ACCEPTANCE_RECORD", "검수 결과·이력 관리", r"(?:검수|검품)[^。.!?;；\n]{0,65}?(?:기록|등록|조회|확인|관리|추적)"),
    ("SHIPMENT_RECORD", "출하·배송 이력 관리", r"(?:출하|배송)[^。.!?;；\n]{0,55}?(?:기록|등록|조회|확인|관리|추적)"),
    ("PERSON_HISTORY", "담당자별 업무 이력 조회", r"(?:담당자|작업자|담당|직원)(?:\s*별|\s*기준(?:으로)?|\s*에\s*따른)[^。.!?;；\n]{0,25}?(?:이력|기록|내역)[^。.!?;；\n]{0,30}?(?:조회|확인|검색|추적|관리)"),
)

FUNCTION_SCOPE = {
    "STOCK_HISTORY": r"입출고|입고|출고", "STOCK_STATUS": r"재고",
    "DUPLICATE_ENTRY": r"중복\s*입력|입력\s*중복|반복\s*입력|재입력",
    "DATA_LINK": r"연계|연동|통합", "PRODUCTION_RECORD": r"생산|작업실적",
    "QUALITY_RECORD": r"품질|불량|검사", "ATTENDANCE": r"근태|출퇴근|출근|퇴근|휴가",
    "ACCOUNTING_RECORD": r"회계|전표|결산|정산", "DOCUMENT_FLOW": r"문서|결재",
    "ORDER_INTAKE": r"주문|수주", "WORK_ASSIGNMENT": r"(?:작업|업무|담당자|작업자|인력).{0,12}(?:배정|할당|배분|배치)",
    "WORK_PROGRESS": r"진행\s*(?:현황|상태)|작업\s*(?:진척|현황|상태)",
    "ACCEPTANCE_RECORD": r"검수|검품", "SHIPMENT_RECORD": r"출하|배송",
    "PERSON_HISTORY": r"(?:담당자|작업자|담당|직원)\s*(?:별|기준).{0,15}(?:이력|기록|내역)",
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


def has_issue(text):
    for match in re.finditer(ISSUE, text):
        tail = text[match.end():match.end() + 24]
        if re.match(r"(?:은|는|이|가)?\s*(?:없|발생하지\s*않)", tail):
            continue
        if match.group(0) in ("어려", "어렵", "불편") and re.match(r"(?:지|하지)\s*않", tail):
            continue
        return True
    return False


def extract(data, spans):
    records, index = [], {}
    def emit(subject, text, sources, claim="DIRECT_SOURCE", derivation=None):
        text = text.strip()
        if not text:
            return
        subject = subject if subject == "to_be" else ALIASES.get(subject, subject)
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
        # Preserve literal ranges; a single issue sentence is a problem too.
        # Do not invent a current activity when the source states only an issue.
        clauses = [s.strip() for s in re.split(
            r"[,，。.!?;；\n]|(?<=있어)\s+", text) if s.strip()]
        issues = [clause for clause in clauses if has_issue(clause)]
        if not issues:
            emit("as_is", text, sources)
            return
        if len(clauses) == 1:
            emit("problem", text, sources)
            return
        for clause in clauses:
            emit("problem" if has_issue(clause) else "as_is", clause, sources)

    def future(text, sources):
        # Separate only independently stated workflow and outcome sentences.
        # A list of features, or an inseparable mixed sentence, is not two claims.
        clauses = [m.group(0).strip() for m in re.finditer(r"[^。.!?;；\n]+[。.!?;；]?", text) if m.group(0).strip()]
        outcome = r"줄이|줄여|줄입|줄일|줄어|줄인|감소|단축|낮추|높이|향상|(?:개선\s*목표|목표는|목표로)"
        workflow = r"접수|등록|배정|할당|조회|확인|검색|기록|관리|처리|공유|검수|출하"
        roles = ["goal" if re.search(outcome, clause) else "to_be" if re.search(workflow, clause) else None for clause in clauses]
        if "goal" in roles and "to_be" in roles:
            for clause, role in zip(clauses, roles):
                if role:
                    emit(role, clause, sources)
        else:
            emit("goal", text, sources)

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
        elif ALIASES.get(field, field) == "goal":
            future(value, group)
        else:
            emit(field, value, group)

    labels = r"현황|현재 업무|문제|문제점|개선 목표|목표|필요 기능|요구 기능|제약사항|제약 사항|제약|제외범위|제외 범위|적용 범위|원인 후보|원인"
    for source in spans:
        if source.get("kind") not in ("DOCUMENT", "IMPROVEMENT", "EVIDENCE", "RESPONSE"):
            continue
        for line in source["quote"].splitlines():
            match = re.fullmatch(r"\s*(" + labels + r")\s*[:：]\s*(.{1,2000})\s*", line)
            if match:
                subject = ALIASES.get(match[1], match[1])
                # Typed fields already provide this role and literal source.
                # The composed original_text mirrors them; parsing its label again
                # must not add a second shortened claim from the same version.
                if any(origin(item) == origin(source)
                       and ALIASES.get(item["field"], item["field"]) == subject
                       and normalized(line) in normalized(item["quote"]) for item in typed):
                    continue
                if subject == "as_is":
                    current(match[2], [source])
                else:
                    emit(subject, match[2], [source], "INFERRED" if subject == "원인 후보" else "DIRECT_SOURCE")
        if source.get("kind") == "IMPROVEMENT" and source.get("field") == "original_text" and not typed:
            # Unlabelled prose has no reliable goal/current role: classify only
            # explicit issue clauses; do not call every automation/goal a problem.
            for clause in re.split(r"[。.!?;；\n]", source["quote"]):
                clause = clause.strip()
                if (6 <= len(clause) <= 2000 and has_issue(clause)
                        and not re.search(r"목표|희망|줄이|줄여|낮추|개선하고|원합|필요|제외", clause)
                        and not re.match(r"\s*(?:" + labels + r")\s*[:：]", clause)):
                    emit("problem", clause, [source])

    # Function names are hypotheses from explicit task expressions, never a claim
    # that a published service exists or can cover the task.
    sources = [s for s in typed if s["field"] in ("as_is", "problem", "goal", "to_be", "required_functions")]
    if not sources:
        sources = [s for s in spans if s.get("kind") == "IMPROVEMENT" and s.get("field") == "original_text"]
    # One hypothesis retains all matching spans, but quotes the explicit future
    # requirement first instead of an incidental historical entry operation.
    sources = sorted(sources, key=lambda source: source.get("field") not in ("goal", "to_be", "required_functions"))
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
