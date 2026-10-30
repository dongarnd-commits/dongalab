"""Versioned sixteen-section template, grounded in frozen reviewed inputs."""
import json
from app.notice.domain import Denied

TEMPLATE = 'MVP_16'
HEADINGS = (
    '1. 제안 개요 및 요약', '2. 기업 및 사업장 현황',
    '3. As-Is 업무·시스템·문제', '4. 개선요구 및 원인 후보',
    '5. 개선목표 및 To-Be', '6. 솔루션 구성',
    '7. 상세 제공 기능', '8. 시스템·데이터 연계',
    '9. 개선 전후 업무 흐름', '10. 적용 범위·제외·산출물',
    '11. 구축 단계 및 일정', '12. 역할 및 협조사항',
    '13. 기대효과 및 성과지표', '14. 정부지원사업 활용',
    '15. 사업비·위험·제약·의사결정', '16. 출처·검토·Version',
)
NEEDS_CHECK = '확인 필요'


def dump(value):
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def lines(values):
    return '\n'.join(str(value) for value in values if value is not None and str(value).strip()) or NEEDS_CHECK


def draft(manifest):
    source = manifest['input']
    company, composition, notice = source['company'], source['composition'], source['notice']
    structured = company.get('structured', {})
    caps = manifest['capability_versions']
    names = {c['id']: c['data']['service'] for c in caps}
    checked = manifest.get('reviewed_analysis', [])
    basis = composition.get('basis')
    basis_note = ('분석 후보의 USE_FOR_REQUEST 검토를 출처로 활용합니다. 공식 사실·요구 확정이나 서비스 적합성 확정과 구분합니다.'
                  if basis and checked else '검토된 분석 후보 연결 없음: 개선요구·구성 기록을 바탕으로 작성했으며 분석 관련 항목은 사람 확인이 필요합니다.')
    facts = company.get('fact_details', source.get('comparison', {}).get('facts', []))
    fact_lines = []
    for fact in facts:
        if fact.get('current_valid') is not True:
            continue
        fact_lines.append(lines([str(fact.get('field', fact.get('attribute', '항목'))) + ': ' + str(fact.get('value', NEEDS_CHECK)),
            '기간: ' + str(fact.get('period', fact.get('valid_from', NEEDS_CHECK))),
            '단위: ' + str(fact.get('unit') or NEEDS_CHECK),
            'FactVersion: ' + str(fact.get('version_id') or NEEDS_CHECK)]))
    service_lines, conditions = [], []
    for cap in caps:
        d = cap['data']
        service_lines.append(lines([d['service'], d.get('description', ''), '제공범위: ' + d['scope'],
            'CapabilityVersion: ' + cap['id'],
            *['연결 기능 역할: ' + f['role'] for f in d['functions']]]))
        for label, key in (('적용조건', 'conditions'), ('선행요건', 'prerequisites'), ('제외범위', 'exclusions')):
            conditions.extend(label + ': ' + value for value in d.get(key, []))
    coverage_lines, scope_lines = [], []
    status_labels = {'ADDRESSED': '구성안에서 대응', 'PARTIAL': '부분 대응', 'UNRESOLVED': '미해결'}
    for item in composition['coverage']:
        status = status_labels.get(item.get('status'), '해결수준 별도 확인 필요')
        content = lines(['요구: ' + item['requirement'],
            '서비스: ' + names.get(item['capability_version_id'], NEEDS_CHECK),
            '역할: ' + item['role'], '구성 검토 수준: ' + status,
            '대응범위: ' + (item['addressed_scope'] or NEEDS_CHECK),
            '미해결·제외: ' + (item['unaddressed_scope'] or '기록 없음 — 전체 해결 확정 아님'),
            *['추가 확인: ' + text for text in item['missing_information']]])
        coverage_lines.append(content)
        scope_lines.append(content)
    excluded = set(composition.get('excluded_feature_revision_ids', []))
    active = {f['revision_id'] for cap in caps for f in cap['data']['functions']} - excluded
    feature_lines = []
    for feature in manifest['feature_revisions']:
        if feature['id'] not in active:
            continue
        d = feature['data']
        feature_lines.append(lines([d['name'], d.get('description', ''),
            '원천 분류: ' + d['system'] + ' / ' + d.get('feature_group', NEEDS_CHECK),
            'FeatureRevision: ' + feature['id'], '원천 Feature: ' + d['feature_id']]))
    # A shared FeatureRevision is displayed once even if two services link it.
    feature_lines = list(dict.fromkeys(feature_lines))
    integrations = []
    for link in composition.get('integrations', []):
        integrations.append(lines([
            names.get(link['from_capability_version_id'], NEEDS_CHECK) + ' → ' + names.get(link['to_capability_version_id'], NEEDS_CHECK),
            '연계 데이터: ' + link['data'], '업무 흐름: ' + link['workflow'],
            *['전제조건: ' + value for value in link.get('prerequisites', [])],
            '불확실성·확인사항: ' + link['uncertainty']]))
    if not integrations:
        integrations = ['구체적인 시스템 간 데이터·업무 연계는 등록되지 않았습니다. 연계 대상·방향·인터페이스·실현 가능성 확인 필요.']
    analysis_lines = [lines(['검토된 ' + item['category'] + ' 후보: ' + item['content'],
                            '불확실성: ' + (item.get('uncertainty') or NEEDS_CHECK)])
                      for item in checked if item['category'] == 'STRUCTURE']
    missing_lines = [item['content'] for item in checked if item['category'] != 'STRUCTURE']
    as_is = structured.get('as_is') or company['original_text']
    problem = structured.get('problem') or '문제의 적용 범위·원인 구분 확인 필요.'
    goal = structured.get('goal') or structured.get('to_be') or '기업의 구체적인 개선목표 확인 필요.'
    to_be = structured.get('to_be') or '목표 업무 흐름은 기업·운영자 검토 후 확인 필요.'
    support = [item['content'] for item in notice['items'] if item['kind'] == 'SUPPORT_SCOPE']
    eligibility = [item['content'] for item in notice['items'] if item['kind'] != 'SUPPORT_SCOPE']
    program = lines(['공고: ' + manifest.get('notice_title', notice['notice_id']),
        'NoticeVersion: ' + notice['notice_version_id'], 'RequirementVersion: ' + notice['requirement_version_id'],
        *support, *eligibility, '담당자 MatchReview: ' + manifest['match_review']['outcome'],
        '관련성·항목별 검토는 공식 적격·지원금·선정 보장이 아닙니다. 미확인 조건과 공고 최신성을 다시 확인하세요.'])
    bodies = (
        lines(['제안 구성안: ' + composition['name'],
            '수요기업의 확인된 개선요구와 발행 서비스·공고 원문을 연결한 검토 제안입니다.',
            '선택 서비스: ' + ', '.join(names.values()), '요약 목표: ' + goal, basis_note]),
        lines(['기업 식별: ' + company['company_id'], '사업장 식별: ' + str(company.get('site_id') or NEEDS_CHECK),
            *fact_lines] if fact_lines else ['기업 식별: ' + company['company_id'],
            '사업장 식별: ' + str(company.get('site_id') or NEEDS_CHECK), '확인된 기업 현황 값·기간·단위 추가 확인 필요.']),
        lines(['As-Is: ' + as_is, '문제: ' + problem]),
        lines(['기업 개선요구: ' + company['original_text'], *analysis_lines,
            '원인 후보: 근거가 확인된 분석·현장 검토가 필요합니다. 문제와 원인의 인과관계를 자동 확정하지 않습니다.',
            basis_note]),
        lines(['개선목표: ' + goal, 'To-Be: ' + to_be,
            '정량 목표의 기준값·단위·기간과 달성 여부는 별도 확인합니다.']),
        lines([*service_lines, *coverage_lines]),
        lines(feature_lines or ['실제 선택 기능의 상세 설명 확인 필요.']),
        lines(integrations),
        lines(['개선 전: ' + as_is, '개선 후 목표: ' + to_be,
            *['등록된 연계 업무안: ' + link['workflow'] for link in composition.get('integrations', [])],
            '세부 담당자·승인·데이터 처리 순서와 예외 흐름 확인 필요.']),
        lines([*scope_lines, *conditions,
            '산출물의 명세·형식·완료 및 인수 기준: 확인 필요. 원천 기능 전체가 구축범위로 확정된 것은 아닙니다.']),
        lines(['구축 단계·순서·담당자·착수 및 종료 기준: 확인 필요.',
            '시작일·완료일·소요기간: 확인 필요. 확정되지 않은 기간을 산정하지 않습니다.',
            *['구성 선행조건: ' + value for value in composition.get('conditions', [])]]),
        lines(['서비스별 역할은 6절의 운영자 구성 검토안을 따릅니다.',
            '기업 협조 범위·담당자·자료 제공·검수 책임: 확인 필요.',
            'DATCO 수행 범위·담당자·개발 및 연계 책임: 확인 필요.',
            *['연계 전제: ' + value for link in composition.get('integrations', []) for value in link.get('prerequisites', [])]]),
        lines(['기업이 제시한 개선목표: ' + goal,
            '기대효과는 목표이며 달성 보장이 아닙니다. 기준값·산식·단위·측정기간·검증 책임 확인 필요.',
            '원문에 없는 개선율·절감액·성과 수치를 생성하지 않습니다.']),
        program,
        lines(['사업비·견적 범위·통화·부가세·지원금·기업부담: 확인 필요.',
            '일정·비용·선정확률을 추정하여 확정값으로 기재하지 않습니다.',
            '기업 제약: ' + (structured.get('constraints') or NEEDS_CHECK),
            *conditions, *['구성 미해결사항: ' + value for value in composition.get('unresolved', [])],
            *['검토된 추가 확인 후보: ' + value for value in missing_lines]]),
        lines(['문서 템플릿: ' + TEMPLATE, basis_note,
            '분석 후보 검토, 개선요구 공식 확인, MatchReview, 제안내용 검토, 기업 승인·재승인은 별도 기록입니다.',
            '이 문서의 기업 승인·전달 여부는 정확한 ProposalVersion의 요청·결정 이력에서 확인합니다.',
            dump(manifest['refs'])]),
    )
    return [dict(heading=heading, body=body, evidence_refs=manifest['refs'])
            for heading, body in zip(HEADINGS, bodies)]


def validate(sections):
    if len(sections) != len(HEADINGS):
        raise Denied('REQUIRED_DATA_MISSING', 422)
    for item, heading in zip(sections, HEADINGS):
        if (set(item) != {'heading', 'body', 'evidence_refs'} or item['heading'] != heading
                or not isinstance(item['body'], str) or not item['body'].strip() or len(item['body']) > 20000):
            raise Denied('REQUIRED_DATA_MISSING', 422)
