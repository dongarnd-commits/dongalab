"""Bounded heading/body rules. No eligibility decision, inferred values or OCR."""
import re
from itertools import groupby
from app.notice.domain import CandidateOutput
from app.infrastructure.notice_documents import evidence_range

ALIASES = {
    "ELIGIBILITY_REQUIREMENT": ("지원대상", "신청대상", "신청자격", "지원자격", "참여자격", "지원대상및자격", "지원대상및신청자격"),
    "APPLICATION_PERIOD": ("신청기간", "접수기간", "신청서제출기한", "접수기한"),
    "SUPPORT_SCOPE": ("지원내용", "지원분야", "지원대상분야", "지원규모및기간", "지원규모", "지원내용및규모"),
    "REQUIRED_DOCUMENT": ("제출서류", "제출서류사항", "구비서류", "필수제출서류", "신청서류"),
    "CONDITIONAL_REQUIREMENT": ("지원제외", "지원제외조건", "지원제외대상", "지원제외처리기준", "사전지원제외", "신청제외대상"),
    "EVALUATION_CRITERION": ("평가기준", "선정기준", "평가항목", "연구개발계획서평가항목", "평가기준(감점기준포함)"),
}
NUMBER = r"(?:\d+(?:-\d+)*[.)]|[가-하][.)]|[①-⑳]|붙임\s*\d+)\s*"
MARK = r"[□○◦●▪▸▶☞※*·-]\s*"

def compact(value):
    return re.sub(r"\s+", "", value)

def heading(value):
    value=re.sub(r"^(?:"+NUMBER+r"|"+MARK+r")+", "", value.strip())
    parts=re.split(r"[:：]",value,maxsplit=1)
    key=compact(parts[0])
    for kind, aliases in ALIASES.items():
        if key in aliases:
            return kind, parts[0], parts[1].strip() if len(parts)>1 else ""
    if key=="사업개요":
        return "OVERVIEW",parts[0],""
    return None

def boundary(value):
    value=re.split(r"[:：]",value,maxsplit=1)[0].strip()
    # Other numbered sections stop an active scope. Numbered exclusion/table rows do not.
    if re.match(r"^"+NUMBER,value) and len(compact(value))<50:
        return bool(re.search(r"(?:개요|목적|추진체계|유의사항|중복성제기|규정|문의처|징수기준|지원기준|지원분야및신청자격등|신청방법,신청서제출기한및접수처|문의처등)$",compact(value)))
    return compact(value) in {"사업신청방법","사업신청사이트","문의처","첨부파일","본문출력파일","#해시태그목록","소관부처·지자체","사업수행기관"} or "목차"==compact(value).strip("- ")

def substantive(kind, body):
    value=compact(body)
    if len(value)<5:
        return False
    if re.search(r"(?:자세한|상세한).*(?:참조|확인)|^(?:공고문|붙임\d*|별첨|홈페이지).*(?:참조|확인)$",value):
        return False
    if re.search(r"관련문의|대한문의|문의처|연락처|설명합니다|단어를검색",value):
        return False
    if kind=="APPLICATION_PERIOD":
        return bool(re.search(r"\d{2,4}[.년/-]\s*\d{1,2}|\d{1,2}월",body)) and bool(re.search(r"[~～∼]|부터|까지|마감|기한",body))
    if not re.search(r"[가-힣]",value):
        return False
    if kind=="ELIGIBILITY_REQUIREMENT":
        return bool(re.search(r"기업|기관|법인|사업자|대학|연구소|단체|조합|소상공인|창업자",value))
    if kind=="SUPPORT_SCOPE":
        return bool(re.search(r"개발|구축|사업화|과제|상금|억원|만원|비용|교육|컨설팅|장비|시스템|인건비|자금|융자|보조",value))
    if kind=="REQUIRED_DOCUMENT":
        return bool(re.search(r"서류|계획서|증명|등록증|확인서|동의|확약|재무제표|보고서|신청서|제출|업로드",value))
    if kind=="CONDITIONAL_REQUIREMENT":
        return bool(re.search(r"경우|제외|제한|부도|체납|파산|잠식|불이행",value))
    if kind=="EVALUATION_CRITERION":
        return bool(re.search(r"배점|점수|\d+점|적정성|타당성|가능성|이해도|감점",value))
    return False

def analyze_korean(spans):
    outputs=[]
    # Sources never share context. Carry a section only onto the next physical PDF page.
    for source_id, source_iter in groupby(spans,key=lambda s:s.source_id):
        source=list(source_iter); active=None; previous_page=None
        for page, page_iter in groupby(source,key=lambda s:s.page):
            lines=list(page_iter)
            if page is None or previous_page is None or page!=previous_page+1:
                active=None
            previous_page=page
            block=[]; title_span=None
            def flush():
                if not active or not block:
                    return
                kind,title=active
                body="\n".join(s.text for s in block)
                if kind=="OVERVIEW":
                    # Only explicit arrow/bullet summary clauses; never the invitation/introduction.
                    for sp in block:
                        if not re.match(r"^\s*[☞-]",sp.text):
                            continue
                        val=compact(sp.text)
                        selected="SUPPORT_SCOPE" if re.search(r"상금지원|연구개발지원|지원$",val) else "ELIGIBILITY_REQUIREMENT"
                        if substantive(selected,sp.text):
                            outputs.append(CandidateOutput(selected,sp.text,
                                "사업개요의 명시적 요약 항목. 적용대상·예외는 원문과 함께 사람 검토 필요.",sp))
                    return
                if substantive(kind,body):
                    outputs.append(CandidateOutput(kind,body,
                        f"한국어 절 ‘{title}’에 연결된 원문 본문. 추론 없이 원문을 보존한 후보이며 조건·예외·표 및 페이지 경계는 사람 검토 필요.",evidence_range(([title_span] if title_span else [])+block)))
            for sp in lines:
                # Page numbers are never requirement content.
                if re.fullmatch(r"-\s*\d+\s*-",sp.text):
                    flush(); block=[]; title_span=None
                    continue
                found=heading(sp.text)
                if found:
                    flush(); block=[]
                    if found[2] and re.fullmatch(r"(?:붙임\d+|별첨|공고문).*참조",compact(found[2])):
                        active=None; title_span=None
                        continue
                    active=(found[0],found[1]); title_span=sp
                    if found[2]:
                        # Preserve a single-line heading/value verbatim, including its separator.
                        block=[sp]; title_span=None
                    continue
                if boundary(sp.text):
                    flush(); active=None; block=[]; title_span=None
                    continue
                if active:
                    block.append(sp)
                    # Very large/ambiguous sections are not truncated into confident clauses.
                    if len(block)>120:
                        active=None; block=[]; title_span=None
            flush()
    return outputs

def diagnostics(spans, outputs):
    result=[]
    for source_id in dict.fromkeys(s.source_id for s in spans):
        selected=[s for s in spans if s.source_id==source_id]
        if not any(re.search(r"[가-힣]",s.text) for s in selected):
            continue
        if any(o.span.source_id==source_id and o.reason.startswith("Direct source clause labelled") for o in outputs) and not any(heading(s.text) for s in selected):
            # A Korean noun inside an English labelled fixture is not a new Korean analysis scope.
            continue
        kinds=sorted({o.kind for o in outputs if o.span.source_id==source_id})
        result.append({"source_id":source_id,"reason":"RULE_ANALYSIS_LIMITED" if kinds else "REQUIREMENT_STRUCTURE_NOT_RECOGNIZED",
            "extraction_succeeded":True,"extracted_span_count":len(selected),"recognized_kinds":kinds,
            "unrecognized_kinds":sorted(set(ALIASES)-set(kinds)),
            "limitation":"제목과 연결된 명시적 본문만 분석합니다. 미인식은 부적격이 아닙니다. 표의 셀 관계, 페이지를 넘는 조건·예외, 미지원 형식과 전체 요건은 사람이 원문을 확인해야 합니다."})
    return result


def _period_details(value):
    """Comparison only. Published content and evidence remain byte-for-byte unchanged."""
    from datetime import date
    if re.search(r"공고기간|제기기간|이의신청|사업기간|연장|변경|예정|조건부",value):
        return None
    def part(prefix):
        return (rf"(?:(?P<{prefix}y>\d{{4}}|[’‘']\d{{2}})\s*(?:[./-]|년)\s*)?"
            rf"(?P<{prefix}m>\d{{1,2}})\s*(?:[./-]|월)\s*(?P<{prefix}d>\d{{1,2}})(?:일|\.)?"
            rf"(?:\s*\((?P<{prefix}w>[월화수목금토일])(?:요일)?\))?"
            rf"(?:\s*(?P<{prefix}h>\d{{1,2}}):(?P<{prefix}min>\d{{2}}))?")
    matches=list(re.finditer(part('s')+r"\s*(?:~|～|∼|to|부터|–)\s*"+part('e'),value))
    if len(matches)!=1:
        return None
    match=matches[0]
    if not match['sy']:
        return None
    # More dates/times outside the range may express other deadlines or qualifications.
    remainder=value[:match.start()]+value[match.end():]
    if re.search(r"\d{2,4}\s*[.년/-]\s*\d{1,2}|\d{1,2}:\d{2}",remainder):
        return None
    try:
        def year(raw):
            if raw[0] in "’‘'":
                short=int(raw[1:])
                if short>=70: raise ValueError('Ambiguous century')
                return 2000+short
            return int(raw)
        start_year=year(match['sy'])
        dates=[]; times=[]
        for prefix in ('s','e'):
            current=date(year(match[prefix+'y']) if match[prefix+'y'] else start_year,
                int(match[prefix+'m']),int(match[prefix+'d']))
            weekday=match[prefix+'w']
            if weekday and current.weekday()!='월화수목금토일'.index(weekday):return None
            hour=match[prefix+'h']; minute=match[prefix+'min']
            time=None if hour is None else (int(hour),int(minute))
            if time and not (0<=time[0]<24 and 0<=time[1]<60):return None
            dates.append(current); times.append(time)
        if dates[1]<dates[0]:return None
        return tuple(dates),tuple(times)
    except ValueError:
        return None


def has_period_conflict(values):
    from itertools import combinations
    for left,right in combinations(values,2):
        if left==right:continue
        a,b=_period_details(left),_period_details(right)
        if a is None or b is None or a[0]!=b[0]:return True
        # Missing time means unknown, not a conflicting midnight deadline.
        if any(x is not None and y is not None and x!=y for x,y in zip(a[1],b[1])):return True
    return False
