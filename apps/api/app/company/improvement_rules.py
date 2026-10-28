"""Bounded deterministic rules. No model, network, invented numbers or facts."""
import re

VERSION = 'improvement-rules-v1'
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
 ('R02','측정 기준',r'불량|생산성|소요시간|처리시간|비용\s*절감|측정|지표',r'측정\s*기준|기준기간|현재값|기준값','측정 지표의 정의·기준기간·현재값·단위를 확인해 주세요.'),
 ('R04','적용 범위',r'공정|업무|라인|사업장|부서',r'적용\s*범위\s*[:：]|대상\s*범위\s*[:：]','이번 개선 대상과 포함·제외 범위를 확인해 주세요.'),
 ('R05','설비·시스템',r'설비|시스템|연계|구축',r'기존\s*(설비|시스템)\s*[:：]|연계\s*대상\s*[:：]','기존 설비·시스템 구성과 연계 대상·제약을 확인해 주세요.'),
 ('R06','사업비',r'예산|투자|견적|사업비',r'(예산|사업비|견적)\s*[:：]\s*\S+','검토할 예산의 산정 범위·통화·포함 비용을 확인해 주세요.'),
 ('R07','일정',r'착수|완료일|납기|일정|기한',r'(착수|완료일|일정|기한)\s*[:：]\s*\S+','희망 일정의 기준일과 선행조건을 확인해 주세요.'),
)

def analyze(data, spans, *, incomplete=False):
    candidates=[]; diagnostics=[]
    def emit(category,subject,text,rule,evidence,claim='DIRECT_SOURCE',question=''):
        candidates.append(dict(category=category,content=text,reason='원문에 명시된 현황·목표·요구사항을 구조화한 후보입니다.' if category=='STRUCTURE' else REASONS[rule],
            data=dict(subject=subject,rule_id=rule,rule_version=VERSION,claim_kind=claim,evidence=evidence,
                uncertainty='사람 검토 필요; 확인된 기업 사실이 아님',question=question)))
    for field,label in FIELDS.items():
        if data.get(field,'').strip():
            span=next(s for s in spans if s.get('field')==field)
            emit('STRUCTURE',field,data[field],'R01' if field in ('as_is','problem','impact') else 'R03',[span])
    for source in spans:
        if source.get('kind') not in ('DOCUMENT','IMPROVEMENT','EVIDENCE'):continue
        for line in source['quote'].splitlines():
            m=re.fullmatch(r'\s*(현황|문제|개선 목표|필요 기능)\s*[:：]\s*(.{1,2000})\s*',line)
            if m and not any(c['content']==m[2] for c in candidates):
                emit('STRUCTURE',m[1],m[2],'R01' if m[1] in ('현황','문제') else 'R03',[source])
    if (data.get('as_is') or data.get('problem')) and not (data.get('goal') or data.get('to_be')) and not incomplete:
        basis=next(s for s in spans if s.get('field') in ('as_is','problem'))
        emit('MISSING_INFORMATION','개선 목표','검사 범위 내 개선 목표 추가 확인 후보','R03',[basis],'SEARCH_NOT_FOUND','이번 문제에서 기대하는 개선 결과를 확인해 주세요.')
    text='\n'.join(s['quote'] for s in spans)
    for rule,subject,applicable,present,question in RULES:
        # A common document can answer a question; it cannot invent task applicability.
        basis=next((s for s in spans if s.get('kind')=='IMPROVEMENT' and re.search(applicable,s['quote'])),None)
        if basis is None:
            diagnostics.append(dict(rule=rule,outcome='NOT_APPLICABLE',reason='명시된 적용조건 없음'));continue
        found=next((s for s in spans if re.search(present,s['quote'])),None)
        if found:
            diagnostics.append(dict(rule=rule,outcome='FOUND',reason='지원하는 명시 라벨 확인',evidence=[found]));continue
        if incomplete:
            diagnostics.append(dict(rule=rule,outcome='UNKNOWN',reason='자료 처리 범위 불충분; 누락 판단 보류'));continue
        emit('MISSING_INFORMATION',subject,f'검사 범위 내 {subject} 추가 확인 후보',rule,[basis],'SEARCH_NOT_FOUND',question)
        diagnostics.append(dict(rule=rule,outcome='NOT_FOUND_IN_SCOPE',reason='승인된 라벨 검사 범위에서 미확인'))
    # Only exact labelled same-context scalar conflicts; no free-form semantic comparison.
    values={}
    for span in spans:
        for line in span['quote'].splitlines():
            m=re.fullmatch(r'\s*(적용 범위|기존 시스템)\s*\(([^)]{1,100})\)\s*[:：]\s*(.{1,200})\s*',line)
            if m:values.setdefault((m[1],m[2]),{}).setdefault(m[3],span)
    for (label,context),found in values.items():
        if len(found)>1:emit('CONFLICT',label,f'{label}의 명시값이 서로 다릅니다.','R08',list(found.values()),'INFERRED',f'{label}의 적용 기준을 확인해 주세요.')
    return candidates,diagnostics

def validate(candidate,spans):
    if candidate['category'] not in ('STRUCTURE','MISSING_INFORMATION','CONFLICT','PROCESSING_LIMITATION'):
        raise ValueError('INVALID_ANALYSIS_OUTPUT')
    for ev in candidate['data']['evidence']:
        if ev not in spans or not ev.get('quote'):raise ValueError('INVALID_ANALYSIS_EVIDENCE')
    if candidate['category']=='STRUCTURE' and not any(candidate['content'] in e['quote'] for e in candidate['data']['evidence']):
        raise ValueError('INVALID_EXTRACTED_VALUE')
