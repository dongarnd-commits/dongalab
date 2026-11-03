"""Bounded deterministic rules. No model, network, invented numbers or facts."""
import re
from app.company.improvement_language import active_match,answer_span,classify_domains,scalar_observations
from app.company.improvement_structure import extract as extract_structure, function_derivation

VERSION = 'improvement-rules-v5'
REASONS = {
 'R02':'개선 전후 효과를 비교하려면 측정 지표·기준기간·현재값·단위를 확인해야 합니다.',
 'R03':'기업이 기대하는 개선 결과를 구체화하기 위한 확인입니다.',
 'R04':'수행 범위를 정하려면 적용 대상과 포함·제외 범위를 확인해야 합니다.',
 'R05':'구축·연계 범위를 검토하려면 기존 구성과 연계 대상·제약을 확인해야 합니다.',
 'R06':'예산 검토에는 산정 범위와 통화·포함 비용의 확인이 필요합니다.',
 'R07':'실행 가능한 일정을 검토하려면 기준일과 선행조건을 확인해야 합니다.',
 'R08':'같은 명시 비교 맥락의 자료 값이 달라 적용 기준을 확인해야 합니다.',
}
FIELDS = {'as_is':'현황','problem':'문제','impact':'영향','goal':'개선 목표','to_be':'개선 목표','required_functions':'필요 기능','constraints':'제약사항'}
RULES = (
 ('R02','측정 기준',r'불량|생산성|소요시간|처리시간|비용\s*절감|측정|지표|재고.{0,15}(?:불일치|일치하지|오차)',r'측정\s*기준|기준기간|현재값|기준값','측정 지표의 정의·기준기간·현재값·단위를 확인해 주세요.'),
 ('R04','적용 범위',r'공정|업무|라인|사업장|부서|(?:창고|입출고|재고).{0,25}(?:관리|통합|구축)',r'적용\s*범위\s*[:：]|대상\s*범위\s*[:：]','이번 개선 대상과 포함·제외 범위를 확인해 주세요.'),
 ('R05','설비·시스템',r'설비|시스템|연계|구축',r'기존\s*(설비|시스템)\s*[:：]|연계\s*대상\s*[:：]','기존 설비·시스템 구성과 연계 대상·제약을 확인해 주세요.'),
 ('R06','사업비',r'예산|투자|견적|사업비',r'(예산|사업비|견적)\s*[:：]\s*\S+','검토할 예산의 산정 범위·통화·포함 비용을 확인해 주세요.'),
 ('R07','일정',r'착수|완료일|납기|일정|기한|도입\s*(?:시기|시점)',r'(착수|완료일|일정|기한)\s*[:：]\s*\S+','희망 일정의 기준일과 선행조건을 확인해 주세요.'),
)

def analyze(data, spans, *, incomplete=False, coverage=()):
    candidates=[]; diagnostics=[]
    def emit(category,subject,text,rule,evidence,claim='DIRECT_SOURCE',question=''):
        candidates.append(dict(category=category,content=text,reason='원문에 명시된 현황·목표·요구사항을 구조화한 후보입니다.' if category=='STRUCTURE' else REASONS[rule],
            data=dict(subject=subject,rule_id=rule,rule_version=VERSION,claim_kind=claim,evidence=evidence,
                uncertainty='사람 검토 필요; 확인된 기업 사실이 아님',question=question)))
    for record in extract_structure(data, spans):
        subject = record["subject"]
        emit("STRUCTURE", subject, record["text"],
             "R01" if subject in ("as_is", "problem", "impact", "원인 후보") else "R03",
             record["evidence"], record["claim_kind"])
        if record.get("derivation"):
            candidates[-1]["data"]["derivation"] = record["derivation"]
            candidates[-1]["data"]["function_label"] = record["function_label"]
            candidates[-1]["data"]["uncertainty"] = "원문 업무 표현에서 제안한 기능 검토 후보; 실제 서비스 제공·구축 가능성 확인 필요"
        elif subject == "원인 후보":
            candidates[-1]["data"]["uncertainty"] = "기업 원문의 원인 설명 후보; 인과관계나 확정 사실이 아님"
    def missing(rule,subject,basis,question,present):
        found,answer_state=answer_span(rule,spans,present)
        scope=[dict(inspection_id=c['inspection_id'],status=c['status'],origin=c['origin'],
                    locations=c['locations'],exclude_reason=c.get('exclude_reason','')) for c in coverage]
        # Excluding a common reference explicitly bounds the search. Direct evidence
        # remains relevant even when excluded. Never guess relevance from filenames.
        unknown=[c['inspection_id'] for c in coverage if c['status']!='COMPLETE' and
                 not (c['status'] in ('EXCLUDED','NOT_SELECTED') and c['origin']=='COMMON_REFERENCE')]
        if found:
            diagnostics.append(dict(rule=rule,outcome=answer_state,reason='명시 라벨 또는 지원하는 동등 표현/기존 검토 답변 확인; 미정 응답을 수치로 해석하지 않음',evidence=[found],scope=scope));return
        if incomplete and not coverage:
            diagnostics.append(dict(rule=rule,outcome='UNKNOWN',reason='자료 처리 범위 불충분; 누락 판단 보류'));return
        uncertain=bool(unknown)
        emit('PROCESSING_LIMITATION' if uncertain else 'MISSING_INFORMATION',subject,
             f'{subject}: 미검사 자료 추가 검토 필요' if uncertain else f'검사 범위 내 {subject} 추가 확인 후보',
             rule,[basis],'INFERRED' if uncertain else 'SEARCH_NOT_FOUND',
             f'미검사 자료에서 {subject}를 먼저 확인해 주세요. 확인 후 필요한 경우: {question}' if uncertain else question)
        candidates[-1]['data'].update(search_scope=scope,uninspected_ids=unknown,
            assessment='NEEDS_SOURCE_REVIEW' if uncertain else 'NOT_FOUND_IN_SCOPE',
            uncertainty='미검사 자료에 정보가 있을 수 있음; 정보 부재 판단 아님' if uncertain else '명시 라벨 검사 범위에서만 미확인; 제외 자료 및 의미상 동등 표현은 확인하지 않음')
        diagnostics.append(dict(rule=rule,outcome='NEEDS_SOURCE_REVIEW' if uncertain else 'NOT_FOUND_IN_SCOPE',
                                evidence=[basis],scope=scope,uninspected_ids=unknown))
    if (data.get('as_is') or data.get('problem')) and not (data.get('goal') or data.get('to_be')):
        basis=next(s for s in spans if s.get('field') in ('as_is','problem'))
        missing('R03','개선 목표',basis,'이번 문제에서 기대하는 개선 결과를 확인해 주세요.',r'개선\s*목표\s*[:：]\s*\S+')
    for rule,subject,applicable,present,question in RULES:
        # A common document can answer a question; it cannot invent task applicability.
        basis=next((s for s in spans if s.get('kind')=='IMPROVEMENT' and active_match(s['quote'],applicable)),None)
        if basis is None:
            diagnostics.append(dict(rule=rule,outcome='NOT_APPLICABLE',reason='명시된 적용조건 없음'));continue
        missing(rule,subject,basis,question,present)
    # Only exact labelled same-context scalar conflicts; no free-form semantic comparison.
    values={}
    for span in spans:
        for line in span['quote'].splitlines():
            m=re.fullmatch(r'\s*(적용 범위|기존 시스템)\s*\(([^)]{1,100})\)\s*[:：]\s*(.{1,200})\s*',line)
            if m:values.setdefault((m[1],m[2]),{}).setdefault(m[3],span)
    for (label,context),found in values.items():
        if len(found)>1:emit('CONFLICT',label,f'{label}의 명시값이 서로 다릅니다.','R08',list(found.values()),'INFERRED',f'{label}의 적용 기준을 확인해 주세요.')
    for (label,context,dimension),found in scalar_observations(spans).items():
        if len(found)>1:
            emit('CONFLICT',label,f'{label}의 같은 기간·범위·호환 단위 값이 서로 다릅니다.','R08',list(found.values()),'INFERRED',f'{context}의 {label} 적용 기준을 확인해 주세요.')
            candidates[-1]['data']['comparison']=dict(context=context,dimension=dimension,method='EXPLICIT_DECIMAL_UNIT_COMPARISON')
    return candidates,diagnostics

def validate(candidate,spans):
    if candidate['category'] not in ('STRUCTURE','MISSING_INFORMATION','CONFLICT','PROCESSING_LIMITATION'):
        raise ValueError('INVALID_ANALYSIS_OUTPUT')
    if candidate['category']=='MISSING_INFORMATION' and candidate['data'].get('uninspected_ids'):
        raise ValueError('UNINSPECTED_SOURCE_IS_NOT_ABSENCE')
    for ev in candidate['data']['evidence']:
        if ev not in spans or not ev.get('quote'):raise ValueError('INVALID_ANALYSIS_EVIDENCE')
    if candidate['category']=='STRUCTURE' and not any(candidate['content'] in e['quote'] for e in candidate['data']['evidence']):
        raise ValueError('INVALID_EXTRACTED_VALUE')
    if candidate['data'].get('derivation'):
        inferred = candidate['data'].get('claim_kind') == 'INFERRED' and candidate['data'].get('subject') == 'required_functions'
        if not inferred or not function_derivation(candidate['data'].get('function_label'), candidate['data']['derivation'], candidate['data']['evidence']):
            raise ValueError('INVALID_EXTRACTED_VALUE')
