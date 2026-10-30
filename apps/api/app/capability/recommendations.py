"""Published-service retrieval; lexical candidates never confirm applicability."""
import re
from copy import deepcopy
from app.capability.search import search_reasons, query_terms
from app.notice.domain import Denied

VERSION = 'published-solutions-v1'
VOCABULARY = (
    ('재고', '입고', '출고', '입출고', '수불', '물류', '창고'),
    ('생산', '공정', '작업실적', '제조', 'mes'),
    ('품질', '불량', '검사', 'qms'),
    ('구매', '발주', '협력사', '공급망', 'scms'),
    ('인사', '근태', '급여', '휴가', 'hr'),
    ('회계', '전표', '결산', '세무', '매입', '매출'),
    ('문서', '전자결재', '결재', '협업', '그룹웨어'),
    ('센서', '설비데이터', '게이트웨이', 'iot'),
    ('영업', '수주', '고객관리'),
)
EXCLUDED = re.compile(r'불필요|필요\s*없|원하지\s*않|도입하지\s*않|대상[이은]?\s*아[닌님]|제외')
FIELDS = (('as_is', 'CURRENT_STATE'), ('problem', 'PROBLEM'), ('goal', 'GOAL'),
    ('to_be', 'GOAL'), ('required_functions', 'REQUIRED_FUNCTION'), ('constraints', 'CONSTRAINT'))


def clauses(text):
    value = re.sub(r'제외하고', '제외,', text)
    value = re.sub(r'불필요하고', '불필요,', value)
    value = re.sub(r'필요\s*없고', '필요 없음,', value)
    value = re.sub(r'아니라', '대상 아님,', value)
    return re.split(r'[\n,;.!?]', value)


def positive_text(text):
    # A business problem "재고가 맞지 않고" is not a product exclusion.
    return ' '.join(clause.strip() for clause in clauses(text) if not EXCLUDED.search(clause)).strip()


def expanded(text):
    value = positive_text(text)
    lower = value.lower().replace(' ', '')
    related = [word for group in VOCABULARY if any(word in lower for word in group) for word in group]
    return ' '.join([value, *related])


def groups_for(value):
    value = value.lower().replace(' ', '')
    return {index for index, group in enumerate(VOCABULARY) if any(word in value for word in group)}


def excluded_groups(context):
    texts = [context.get('original_text', '')]
    texts.extend(value for value in context.get('structured', {}).values() if isinstance(value, str))
    return {group for text in texts for clause in clauses(text) if EXCLUDED.search(clause)
            for group in groups_for(clause)}


def source_demands(context, reviewed=()):
    structured = context.get('structured', {})
    result, seen = [], set()
    for field, kind in FIELDS:
        text = structured.get(field, '')
        if not isinstance(text, str) or not text.strip():
            continue
        result.append(dict(id='improvement:' + field, kind=kind, text=text,
            evidence=[dict(kind='IMPROVEMENT_VERSION', version_id=context['improvement_version_id'],
                           field=field, quote=text)],
            uncertainty='확인된 개선요구 원문입니다. 서비스 해결범위 확정은 별도입니다.'))
        seen.add(text.strip())
    if not result and context.get('original_text', '').strip():
        result.append(dict(id='improvement:original_text', kind='PROBLEM', text=context['original_text'],
            evidence=[dict(kind='IMPROVEMENT_VERSION', version_id=context['improvement_version_id'],
                           field='original_text', quote=context['original_text'])],
            uncertainty='확인된 원문이며 원인·최종 요구사항의 별도 확정이 아닙니다.'))
        seen.add(context['original_text'].strip())
    for item in reviewed:
        if item['category'] != 'STRUCTURE' or item['content'].strip() in seen:
            continue
        result.append(dict(id='analysis:' + item['candidate_id'], kind='REQUIRED_FUNCTION',
            text=item['content'], evidence=deepcopy(item['evidence']),
            uncertainty='USE_FOR_REQUEST 검토 후보입니다. Confirmed Fact나 공식 요구 확정이 아닙니다.'))
        seen.add(item['content'].strip())
    return result


def read_analysis(service, actor, context):
    """Newest exact-Version Run, latest USE_FOR_REQUEST reviews, no cross-version fallback."""
    from app.company.application import CompanyApplication
    from app.company.improvement_analysis import ImprovementAnalysis
    from app.infrastructure import company_schema as C
    a = CompanyApplication(service.session, service.files)
    analysis = ImprovementAnalysis(a)
    stored = context.get('structured', {}).get('analysis_basis')
    source_version_id = context['improvement_version_id']
    if stored:
        try:
            stored = analysis.validate_basis(actor, context['improvement_version_id'], stored)
        except Denied as exc:
            if exc.status in (403, 404, 503):
                raise
            return dict(run_id=None, review_ids=[]), [], ['구조화본에 연결된 분석 입력·검토가 변경되어 재검토가 필요합니다.']
        source_version_id = stored['source_version_id']
    # Legacy consumer contexts need not have a local submitted Version.
    if not a.rows(C.improvement_reviews, version_id=source_version_id, outcome='SUBMIT'):
        return dict(run_id=None, review_ids=[]), [], ['동일 제출 Version의 분석 실행·검토 근거가 없습니다.']
    runs = analysis.listing(actor, source_version_id)
    if not runs:
        return dict(run_id=None, review_ids=[]), [], ['이 제출 Version의 분석을 아직 실행하지 않았습니다.']
    latest = max(runs, key=lambda item: (item['run']['created_at'], item['run']['id']))
    if latest['manifest']['company_id'] != context['company_id']:
        raise Denied('OBJECT_NOT_FOUND', 404)
    if not latest['freshness']['usable']:
        return dict(run_id=None, review_ids=[]), [], ['최신 분석 입력·규칙·실행이 변경되어 재분석·재검토가 필요합니다.']
    selected, ids = [], []
    for candidate in latest['candidates']:
        reviews = candidate['reviews']
        review = max(reviews, key=lambda item: item['ordinal']) if reviews else None
        if not review or review['decision'] != 'USE_FOR_REQUEST':
            continue
        if stored and review['id'] not in stored['review_ids']:
            continue
        ids.append(review['id'])
        selected.append(dict(candidate_id=candidate['id'], review_id=review['id'],
            category=candidate['category'], content=candidate['content'], reason=candidate['reason'],
            subject=candidate['data'].get('subject', ''),
            evidence=deepcopy(candidate['data'].get('evidence', [])),
            uncertainty=candidate['data'].get('uncertainty', ''), review_note=review['note']))
    limits = ['규칙 기반 발행 서비스 검색 후보입니다. 적용성·공고 자격 확정은 아닙니다.']
    if not ids:
        limits.append('활용 검토한 분석 후보가 없어 확인된 개선요구 원문만 검색합니다.')
    if source_version_id != context['improvement_version_id']:
        limits.append('분석 입력 Version과 구조화·확정 Version이 다릅니다. 저장된 명시 연결만 활용합니다.')
    return dict(run_id=latest['run']['id'], review_ids=sorted(ids), source_version_id=source_version_id), selected, limits


def authority_basis(service, actor, context, basis):
    from app.company.application import CompanyApplication
    from app.company.improvement_analysis import ImprovementAnalysis
    return ImprovementAnalysis(CompanyApplication(service.session, service.files)).validate_basis(
        actor, context['improvement_version_id'], basis)


def validate_basis(service, actor, context, basis):
    if (not isinstance(basis, dict) or not {'run_id', 'review_ids'} <= set(basis)
            or set(basis) - {'run_id', 'review_ids', 'source_version_id'}):
        raise Denied('INVALID_ANALYSIS_BASIS', 422)
    requested = basis.get('review_ids', [])
    if not basis.get('run_id') or not requested or len(requested) != len(set(requested)):
        raise Denied('INVALID_ANALYSIS_BASIS', 422)
    normalized = authority_basis(service, actor, context, basis)
    current, reviewed, _ = read_analysis(service, actor, context)
    if normalized['source_version_id'] != current.get('source_version_id', context['improvement_version_id']):
        raise Denied('TARGET_VERSION_MISMATCH')
    if current['run_id'] != basis['run_id']:
        raise Denied('STALE_ANALYSIS', 409)
    if not set(requested) <= set(current['review_ids']):
        raise Denied('STALE_REVIEW', 409)
    return [item for item in reviewed if item['review_id'] in requested]


def retrieve(context, catalog, feature_reader, reviewed=()):
    demands = source_demands(context, reviewed)
    result, covered = [], set()
    excluded = excluded_groups(context)
    for item in catalog:
        if not item.get('version_id'):
            continue
        features = [(f, feature_reader(f['revision_id'])) for f in item['data']['functions']]
        catalog_text = ' '.join([item['data']['service'], item['data'].get('description', ''),
            *item['data']['problems'], *[feature['data']['name'] + ' ' + feature['data']['description']
                                       for _, feature in features]])
        catalog_groups = groups_for(catalog_text)
        reasons, demand_ids, matched = [], [], {}
        for demand in demands:
            if demand['kind'] == 'CONSTRAINT':
                continue
            query = expanded(demand['text'])
            original_groups = groups_for(positive_text(demand['text']))
            demand_groups = original_groups - excluded
            if original_groups and not demand_groups:
                continue
            if demand_groups and catalog_groups and not demand_groups & catalog_groups:
                continue
            for group in excluded:
                for term in VOCABULARY[group]:
                    query = query.replace(term, '')
            if not demand_groups:
                weak = ('확인', '개선', '통합', '중복', '분산', '현재', '체계적', '정리')
                query = ' '.join(term for term in query_terms(query) if not term.startswith(weak))
            hits = search_reasons(query, item['data'], [f['data'] for _, f in features]) if query.strip() else []
            if not hits:
                continue
            demand_ids.append(demand['id'])
            reasons.extend(demand['id'] + ': ' + reason for reason in hits)
            for _, feature in features:
                if search_reasons(query, dict(service='', description='', problems=[], functions=[]), [feature['data']]):
                    matched[feature['id']] = dict(revision_id=feature['id'],
                        feature_id=feature['data']['feature_id'], system=feature['data']['system'],
                        name=feature['data']['name'])
        if not demand_ids:
            continue
        covered.update(demand_ids)
        limits = ['검색 근거는 적합성 확정이 아닙니다. 적용조건·제외범위와 기능 역할을 검토하세요.']
        limits.extend(item['data'].get('prerequisites', []))
        limits.extend(item['data'].get('exclusions', []))
        result.append(dict(item, search_reasons=list(dict.fromkeys(reasons))[:30],
            demand_ids=demand_ids, reasons=list(dict.fromkeys(reasons))[:30],
            matched_features=list(matched.values()), limitations=limits))
    uncovered = [d['id'] for d in demands if d['kind'] != 'CONSTRAINT' and d['id'] not in covered]
    return demands, result, uncovered


def recommendations(service, actor, version_id):
    context = service.context(actor, version_id)
    basis, reviewed, limits = read_analysis(service, actor, context)
    from app.infrastructure import capability_schema as S
    demands, candidates, uncovered = retrieve(context, service.catalog(actor),
        lambda key: service.get(S.revisions, key), reviewed)
    if not candidates:
        limits.append('발행 서비스에서 근거 있는 후보가 없습니다. 제공 가능한 서비스를 만들어내지 않습니다.')
    return dict(context=context, analysis_basis=basis, demands=demands,
        candidates=candidates, uncovered_demands=uncovered, limitations=limits, rule_version=VERSION)


def validate_extensions(service, actor, context, data):
    basis = data.get('basis')
    reviewed = validate_basis(service, actor, context, basis) if basis else []
    if basis:
        data['basis'] = authority_basis(service, actor, context, basis)
    demands = {d['id']: d for d in source_demands(context, reviewed)}
    for item in data['coverage']:
        demand_id, evidence = item.get('demand_id'), item.get('evidence_refs', [])
        if demand_id:
            demand = demands.get(demand_id)
            if demand is None or item['requirement'] != demand['text']:
                raise Denied('TARGET_VERSION_MISMATCH')
            if not evidence or any(ev not in demand['evidence'] for ev in evidence):
                raise Denied('REQUIRED_EVIDENCE_MISSING')
        elif evidence:
            raise Denied('INVALID_ANALYSIS_BASIS', 422)
        status = item.get('status')
        addressed = bool(item['addressed_scope'].strip())
        unresolved = bool(item['unaddressed_scope'].strip() or item['missing_information'])
        if status and (status not in ('ADDRESSED', 'PARTIAL', 'UNRESOLVED')
                or status == 'ADDRESSED' and (not addressed or unresolved)
                or status == 'PARTIAL' and (not addressed or not unresolved)
                or status == 'UNRESOLVED' and (addressed or not unresolved)):
            raise Denied('INVALID_COVERAGE_STATUS', 422)
    selected, seen = set(data['capability_version_ids']), set()
    for link in data.get('integrations', []):
        pair = (link['from_capability_version_id'], link['to_capability_version_id'])
        if pair[0] == pair[1] or not set(pair) <= selected or pair in seen:
            raise Denied('TARGET_VERSION_MISMATCH')
        if not link['data'].strip() or not link['workflow'].strip() or not link['uncertainty'].strip():
            raise Denied('REQUIRED_DATA_MISSING')
        seen.add(pair)


def basis_current(service, actor, context, composition):
    if not composition.get('basis'):
        return True
    try:
        validate_basis(service, actor, context, composition['basis'])
        return True
    except Denied as exc:
        if exc.status in (403, 404, 503):
            raise
        return False
