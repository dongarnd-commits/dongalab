"""Actual Korean DOCX/PDF and legacy coexistence, using synthetic frozen sources."""
from copy import deepcopy
import io
import zipfile
from xml.etree import ElementTree as ET
import pytest
from pypdf import PdfReader
from app.notice.domain import Denied
from app.proposal.documents import draft, render, validate, template_version, HEADINGS as LEGACY_HEADINGS
from app.proposal.mvp_template import HEADINGS
from app.api.proposal import Create, Save


def manifest():
    feature = dict(id='TEST_FEATURE_REV_1', data=dict(feature_id='DMP-0000000000000001',
        system='TEST_MES', feature_group='TEST_QUALITY', name='품질 불량 현황',
        description='TEST 검사별 기록을 조회합니다.'))
    excluded = dict(id='TEST_EXCLUDED_REV', data=dict(feature_id='DMP-0000000000000002',
        system='TEST_MES', feature_group='TEST', name='제외 기능', description='TEST_EXCLUDED_SECRET_DESCRIPTION'))
    caps = [dict(id='TEST_CAP_A', data=dict(service='TEST 품질 관리', description='TEST 불량 기록 관리',
        scope='검사별 현황 조회', functions=[dict(revision_id=feature['id'], role='검사 기록 역할'),
            dict(revision_id=excluded['id'], role='TEST excluded role')], conditions=['TEST 작업 식별 필요'],
        prerequisites=['TEST 수집 방식 검토'], exclusions=['자동 원인 확정 제외']))]
    coverage = [dict(requirement='검사 기록이 흩어져 있습니다.', capability_version_id='TEST_CAP_A',
        feature_revision_ids=[feature['id']], role='현황 정리', addressed_scope='검사 기록 조회',
        unaddressed_scope='자동 원인 분석 미해결', missing_information=['TEST 원천 정의'], status='PARTIAL')]
    integration = dict(from_capability_version_id='TEST_CAP_A', to_capability_version_id='TEST_CAP_B',
        data='TEST 검사 식별자 및 결재 상태', workflow='TEST 검사 등록 후 문서 검토',
        prerequisites=['TEST 식별자 매핑 확인'], uncertainty='TEST 인터페이스 상세 확인 필요')
    refs = dict(company_id='TEST_COMPANY', improvement_version_id='TEST_IMPROVEMENT',
        feature_revision_ids=[feature['id'], excluded['id']], analysis_run_id='TEST_RUN',
        analysis_review_ids=['TEST_REVIEW'], composition_version_id='TEST_COMPOSITION')
    return dict(template_version='MVP_16', refs=refs, notice_title='TEST 실제 저장경로 합성 공고',
        capability_versions=caps, feature_revisions=[feature, excluded], match_review=dict(outcome='PROPOSABLE', id='TEST_MATCH_REVIEW'),
        reviewed_analysis=[dict(category='STRUCTURE', content='TEST 검토된 기능 요구', uncertainty='사람 확인 후보',
            review_note='TEST_PRIVATE_REVIEW_NOTE')],
        input=dict(company=dict(company_id='TEST_COMPANY', site_id='TEST_SITE',
            original_text='검사 기록이 흩어져 있습니다.', structured=dict(as_is='TEST 수기 검사 기록',
            problem='TEST 검사 기록 분산', goal='TEST 검사 현황 통합', to_be='TEST 검토 후 통합',
            constraints='TEST 데이터 정의 협의'), fact_details=[dict(field='company_name', value='TEST 합성기업',
                version_id='TEST_FACT', current_valid=True, unit='', period='2026')]),
            composition=dict(name='TEST 품질·협업 조합', coverage=coverage,
                excluded_feature_revision_ids=[excluded['id']], basis=dict(run_id='TEST_RUN', review_ids=['TEST_REVIEW']),
                integrations=[integration], conditions=['TEST 데이터 사전 확인'], unresolved=['TEST 추가 현장 검토']),
            notice=dict(notice_id='TEST_NOTICE', notice_version_id='TEST_NOTICE_V', requirement_version_id='TEST_REQ_V',
                items=[dict(kind='SUPPORT_SCOPE', content='TEST 확인된 지원범위'),
                    dict(kind='ELIGIBILITY_REQUIREMENT', content='TEST 자격조건은 별도 검토')])))


def version(template='MVP_16'):
    m = manifest()
    m['template_version'] = template
    return dict(id='TEST_PROPOSAL_VERSION', ordinal=3, title='TEST 한글 맞춤형 개선 제안서',
                content_digest='a' * 64, manifest=m, sections=draft(m))


def test_all_sixteen_sections_use_sources_and_preserve_uncertainty():
    v = version()
    assert tuple(s['heading'] for s in v['sections']) == HEADINGS
    body = '\n'.join(s['body'] for s in v['sections'])
    assert all(text in body for text in ['TEST 수기 검사 기록', 'TEST 검토된 기능 요구',
        '품질 불량 현황', 'TEST 검사 식별자 및 결재 상태', 'TEST 검사 등록 후 문서 검토',
        '부분 대응', '자동 원인 분석 미해결', 'TEST 데이터 사전 확인', 'TEST_RUN'])
    assert 'TEST_PRIVATE_REVIEW_NOTE' not in body
    assert 'TEST_EXCLUDED_SECRET_DESCRIPTION' not in body
    assert '기준값·산식·단위·측정기간' in body and '사업비·견적 범위' in body
    assert not any(text in body for text in ['30%', '3개월', '1억원', '선정 확률 90'])
    assert all(s['evidence_refs'] == v['manifest']['refs'] for s in v['sections'])


@pytest.mark.parametrize('kind', ['DOCX', 'PDF'])
def test_exact_korean_sixteen_sections_version_and_content_in_real_documents(kind):
    v = version()
    data = render(v, kind)
    if kind == 'DOCX':
        archive = zipfile.ZipFile(io.BytesIO(data))
        root = ET.fromstring(archive.read('word/document.xml'))
        content = ''.join(root.itertext())
    else:
        reader = PdfReader(io.BytesIO(data))
        content = ''.join(page.extract_text() for page in reader.pages)
        assert all(abs(float(page.mediabox.width) - 595.28) < 1 and abs(float(page.mediabox.height) - 841.89) < 1 for page in reader.pages)
        for page in reader.pages:
            assert page.extract_text().strip().splitlines()[-1].strip() not in HEADINGS
    assert v['id'] in content and v['title'] in content
    for section in v['sections']:
        assert section['heading'] in content
        # PDF extractors place linebreaks at wrapping boundaries.
        normalize = lambda text: ''.join(text.split())
        assert normalize(section['body']) in normalize(content)
    assert render(v, kind) == data


def test_old_eleven_section_template_stays_readable_and_distinct():
    legacy = version('LEGACY_11')
    assert tuple(s['heading'] for s in legacy['sections']) == LEGACY_HEADINGS
    legacy['manifest'].pop('template_version')
    assert template_version(legacy['manifest']) == 'LEGACY_11'
    assert render(legacy, 'DOCX').startswith(b'PK')
    with pytest.raises(Denied):
        validate(legacy['sections'], 'MVP_16')
    with pytest.raises(Denied):
        validate(version()['sections'], 'LEGACY_11')


def test_missing_analysis_and_integration_are_explicit_needs_check_not_fabricated():
    m = manifest()
    m.pop('reviewed_analysis')
    m['input']['composition'].pop('basis')
    m['input']['composition']['integrations'] = []
    sections = draft(m)
    assert '검토된 분석 후보 연결 없음' in sections[0]['body']
    assert '등록되지 않았습니다' in sections[7]['body']
    assert '확인 필요' in sections[10]['body']


def test_template_api_defaults_and_explicit_new_version_upgrade():
    assert Create(candidate_id='TEST', title='TEST', idempotency_key='TEST').template_version == 'LEGACY_11'
    value = Save(expected_version='TEST', title='TEST', template_version='MVP_16', sections=None, idempotency_key='TEST')
    assert value.sections is None and value.template_version == 'MVP_16'
    with pytest.raises(ValueError):
        Create(candidate_id='TEST', title='TEST', template_version='UNVERIFIED', idempotency_key='TEST')
    broken = version()
    broken['sections'][0]['heading'] = 'TEST fake heading'
    with pytest.raises(Denied):
        render(broken, 'DOCX')
