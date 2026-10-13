"""TEST-01..13: semantic/evidence assertions, not merely nonzero counts."""
import os
from dataclasses import replace
from uuid import uuid4
import pytest
from test_notice_slice import context,detail,confirm
from app.core.config import ROOT
from app.infrastructure.database import get_session_factory
from app.infrastructure.notice_store import SqlNoticeStore
from app.infrastructure.notice_documents import LocalPrivateFiles,DeterministicAnalysis,extract_document,evidence_exists
from app.notice.application import NoticeApplication
from app.notice.domain import Span,Denied,CandidateOutput
from app.worker import process_one


def html(lines):
    return extract_document({'id':'synthetic','media_type':'text/html'},
        (''.join('<p>'+line+'</p>' for line in lines)).encode()).spans

@pytest.mark.parametrize('title,body,kind',[
    ('1. 지원대상',['○ 국내 중소기업 및 연구기관','- 법인사업자이어야 함'],'ELIGIBILITY_REQUIREMENT'),
    ('신청기간',['2026.10.19 ~','2026.11.10'],'APPLICATION_PERIOD'),
    ('2-1. 지원내용',['○ 공정 개선 기술개발 및 시스템 구축 지원'],'SUPPORT_SCOPE'),
    ('8. 제출 서류 사항',['1 사업자등록증 제출','2 연구개발계획서 제출'],'REQUIRED_DOCUMENT'),
    ('4-3. 지원제외 처리기준',['○ 국세 체납 기업은 제외','단, 승인된 회생기업은 예외'],'CONDITIONAL_REQUIREMENT'),
    ('5-2. 평가기준 (감점기준 포함)',['▪ 계획의 타당성 40점','▪ 수행 가능성 60점'],'EVALUATION_CRITERION'),
])
def test_01_to_05_korean_heading_body_kind_and_original_range(title,body,kind):
    spans=html([title,*body,'문의처','담당기관'])
    outputs=DeterministicAnalysis().analyze(spans)
    assert len(outputs)==1 and outputs[0].kind==kind
    o=outputs[0]
    assert o.content=='\n'.join(body) and o.content in o.span.text
    assert title in o.span.text and '담당기관' not in o.span.text
    assert evidence_exists(spans,o.span) and '사람 검토' in o.reason

@pytest.mark.parametrize('lines',[
    ['지원대상이라는 단어를 검색하세요','지원내용에 대한 문의가 많습니다'],
    ['1. 지원대상','2. 신청기간','3. 제출서류'], # TOC/heading-only
    ['지원대상','자세한 내용은 공고문 참조','문의처','기관'],
    ['8. 제출서류: 붙임2 참조','9. 기타 유의 사항: 붙임3 참조','10. 문의처 등','계획서 제출 문의'],
    ['사업개요','기업 지원대상에 대한 안내를 읽으세요'],
    ['평가기준','자세한 평가기준은 공고문 참조'],
    ['지원대상','기업 지원대상에 대한 문의는 담당부서로 하세요'],
    ['지원내용','지원내용이라는 용어를 설명합니다'],
    ['제출서류','제출서류 관련 문의는 담당부서로 하세요'],
    ['평가기준','평가기준을 설명합니다'],
])
def test_08_no_keyword_toc_reference_or_contact_candidates(lines):
    assert DeterministicAnalysis().analyze(html(lines))==[]


def test_07_english_regression():
    spans=html(['Eligibility: Manufacturing companies','Support scope: Process improvement',
        'Application period: 2026-10-01 to 2026-10-23','Required document: Business registration','Evaluation: Technical feasibility'])
    out=DeterministicAnalysis().analyze(spans)
    assert [o.kind for o in out]==['ELIGIBILITY_REQUIREMENT','SUPPORT_SCOPE','APPLICATION_PERIOD','REQUIRED_DOCUMENT','EVALUATION_CRITERION']
    assert out[0].content=='Manufacturing companies'
    assert all(o.span in spans for o in out)


def test_06_13_pdf_page_source_and_forged_evidence_guard():
    spans=[Span('a','PDF page 3, line 1','신청자격',3),Span('a','PDF page 3, line 2','국내 중소기업',3),
        Span('a','PDF page 3, line 3','단, 체납기업은 제외',3),Span('b','PDF page 3, line 1','제출서류',3)]
    o=DeterministicAnalysis().analyze(spans)[0]
    assert o.content=='국내 중소기업\n단, 체납기업은 제외'
    assert o.span.page==3 and o.span.source_id=='a' and evidence_exists(spans,o.span)
    assert not evidence_exists(spans,replace(o.span,text=o.span.text+' 서울 소재'))
    assert not evidence_exists(spans,replace(o.span,page=4))
    assert not evidence_exists(spans,replace(o.span,source_id='b'))
    assert not evidence_exists(spans,replace(o.span,descriptor='PDF page 3, line 1 through PDF page 3, line 99'))
    # A missing physical page must not inherit a heading from an earlier page.
    assert DeterministicAnalysis().analyze([spans[0],Span('a','PDF page 5, line 2','국내 중소기업',5)])==[]


def prepare_html(context,lines):
    factory,files,actor=context
    with factory.begin() as s:
        st=SqlNoticeStore(s)
        n=st.add('notices',external_key='KO_TEST_'+str(uuid4()),title='DEMO/TEST 한국어 요건',current_ordinal=1)
        v=st.add('versions',notice_id=n['id'],ordinal=1,mode='DEMO_TEST',metadata={})
        key,digest=files.put((''.join('<p>'+line+'</p>' for line in lines)).encode())
        st.add('sources',version_id=v['id'],name='html',media_type='text/html',provenance='SYNTHETIC DEMO/TEST',storage_key=key,digest=digest)
        j=NoticeApplication(st,files).request(actor,v['id'],str(uuid4()))
    return n,v,j

@pytest.mark.integration
def test_09_10_11_12_worker_partial_human_review_history_and_reanalysis(context):
    factory,files,actor=context
    n,v,j=prepare_html(context,['지원대상','국내 중소기업','제출서류','사업자등록증 제출'])
    with factory.begin() as s:
        st=SqlNoticeStore(s)
        st.add('sources',version_id=v['id'],name='missing.hwp',media_type='application/octet-stream',provenance='DEMO missing',storage_key=None,digest=None)
    assert process_one(factory,files)
    out=detail(context,n)['versions'][0]; run=out['runs'][0]
    assert out['jobs'][0]['state']=='PARTIAL' and not out['confirmed']
    assert any(m['reason']=='SOURCE_NOT_ACQUIRED' for m in run['missing'])
    assert any(m.get('extraction_succeeded') for m in run['missing'])
    candidate=next(c for c in run['candidates'] if c['kind']=='REQUIRED_DOCUMENT')
    with pytest.raises(Denied):
        confirm(context,v,candidate,official=False)
    rv=confirm(context,v,candidate)
    with factory.begin() as s:
        st=SqlNoticeStore(s)
        original_reviews=st.rows('reviews',candidate_id=candidate['id'])
        NoticeApplication(st,files).request(actor,v['id'],str(uuid4()))
    assert process_one(factory,files)
    out=detail(context,n)['versions'][0]
    assert len(out['runs'])==2 and len(out['confirmed'])==1 and out['confirmed'][0]['id']==rv['id']
    semantic=lambda r: sorted((c['kind'],c['content'],c['evidence']['descriptor'],c['evidence']['text']) for c in r['candidates'])
    assert semantic(out['runs'][0])==semantic(out['runs'][1])
    with factory.begin() as s:
        st=SqlNoticeStore(s)
        assert st.rows('reviews',candidate_id=candidate['id'])==original_reviews
        st.add('versions',notice_id=n['id'],ordinal=2,mode='DEMO_TEST',metadata={})
        st.change('notices',n['id'],current_ordinal=2)
    refreshed=detail(context,n)
    assert refreshed['versions'][0]['confirmed'][0]['id']==rv['id']
    with pytest.raises(Denied):
        new_run=next(r for r in out['runs'] if r['id']!=run['id'])
        confirm(context,v,new_run['candidates'][0])

@pytest.mark.integration
@pytest.mark.parametrize('lines,reason',[(['일반 소개 문장만 있습니다'],'REQUIREMENT_STRUCTURE_NOT_RECOGNIZED'),([], 'TEXT_EXTRACTION_EMPTY')])
def test_failure_preserves_extraction_diagnostics_without_candidates(context,lines,reason):
    n,v,j=prepare_html(context,lines)
    assert process_one(context[0],context[1])
    out=detail(context,n)['versions'][0]
    assert out['jobs'][0]['state']=='FAILED' and out['jobs'][0]['error']=='NO_VALID_REQUIREMENT_CANDIDATE'
    assert out['runs'][0]['candidates']==[] and out['confirmed']==[]
    assert reason in {m['reason'] for m in out['runs'][0]['missing']}


@pytest.mark.parametrize('values,expected',[
    (["2026-10-19 ~ 2026-11-10", "2026.10.19 ~\n2026.11.10", "’26.10.19.(월) ~ 11.10.(화) 18:00 까지"],False),
    (["2026-10-19 ~ 2026-11-10", "2026-10-19 ~ 2026-11-11"],True),
    (["2026-10-19 ~ 2026-11-10 17:00", "’26.10.19.(월) ~ 11.10.(화) 18:00 까지"],True),
    (["2026-10-19 ~ 2026-11-10", "2026-10-19 ~ 2026-11-10 연장 예정"],True),
    (["2026-10-19 ~ 2026-11-10", "2026-10-19 ~ 2026-11-10 24:00"],True),
    (["2026-10-19 ~ 2026-11-10", "공고기간 2026-10-19 ~ 2026-11-10"],True),
])
def test_accuracy_period_comparison_retains_dates_times_and_uncertainty(values,expected):
    from app.infrastructure.notice_korean import has_period_conflict
    original=list(values)
    assert has_period_conflict(values) is expected
    assert values==original


def stored_inputs():
    # Opt-in local regression: public document content stays in ignored private storage.
    if os.environ.get('DATCO_TEST_STORED_KO')!='1':
        pytest.skip('Set DATCO_TEST_STORED_KO=1 with the stored Korean Live sources to validate real documents')
    result=[]; files=LocalPrivateFiles(ROOT/'storage/private/notice')
    with get_session_factory()() as s:
        st=SqlNoticeStore(s)
        for n in st.rows('notices'):
            if not (n['title'].startswith('2026년 연구개발특구') or n['title'].startswith('2026년 에너지기술')):
                continue
            for v in st.rows('versions',notice_id=n['id']):
                if v['mode']!='LIVE': continue
                sources=st.rows('sources',version_id=v['id'])
                result.append((n,v,[(r,files.read(r['storage_key'],r['digest']) if r['storage_key'] else None) for r in sources]))
    assert len(result)==2, 'Both real Korean notices must be available; do not fabricate a pass'
    return result

@pytest.mark.integration
def test_real_korean_sources_worker_content_and_review_in_isolated_schema(context):
    factory,files,actor=context
    for original,version,inputs in stored_inputs():
        with factory.begin() as s:
            st=SqlNoticeStore(s)
            n=st.add('notices',external_key='KO_COPY_'+str(uuid4()),title='DEMO/TEST isolated copy: '+original['title'],current_ordinal=1)
            v=st.add('versions',notice_id=n['id'],ordinal=1,mode='DEMO_TEST',metadata=version['metadata'])
            sources=[]
            for source,data in inputs:
                key,digest=files.put(data) if data else (None,None)
                r=st.add('sources',version_id=v['id'],name=source['name'],media_type=source['media_type'],provenance='ISOLATED COPY OF STORED PUBLIC SOURCE',storage_key=key,digest=digest)
                sources.append((r,data))
            NoticeApplication(st,files).request(actor,v['id'],str(uuid4()))
        assert process_one(factory,files)
        out=detail(context,n)['versions'][0]; run=out['runs'][0]
        assert not out['confirmed'] and out['jobs'][0]['state']=='PARTIAL'
        assert out['jobs'][0]['attempts'][0]['state']=='PARTIAL'
        assert run['conflicts']==[], 'Equivalent source periods must not become conflicts'
        if original['title'].startswith('2026년 연구개발특구'):
            scoped=next(c for c in run['candidates'] if 'TLO' in c['content'])
            assert '(사업화 지원 부문)' in scoped['content'] and '(사업화 지원 부문)' in scoped['evidence']['text']
        for source,data in sources:
            if not data: continue
            extracted=extract_document(source,data)
            candidates=[c for c in run['candidates'] if c['evidence']['source_id']==source['id']]
            assert candidates
            for c in candidates:
                loc=c['evidence']
                assert c['content'] in loc['text']
                assert evidence_exists(extracted.spans,Span(source['id'],loc['descriptor'],loc['text'],loc['page']))
                files.verify_location(source,loc)
            if source['media_type']=='text/html':
                period=next(c for c in candidates if c['kind']=='APPLICATION_PERIOD')
                assert '2026.10.' in period['content'] and '2026.11.' in period['content']
                assert all('문의' not in c['content'] for c in candidates)
            else:
                assert extracted.total_pages==18 and len(extracted.spans)==605
                allowed={c['kind'] for c in candidates}
                assert allowed=={'APPLICATION_PERIOD','ELIGIBILITY_REQUIREMENT','SUPPORT_SCOPE','REQUIRED_DOCUMENT','CONDITIONAL_REQUIREMENT','EVALUATION_CRITERION'}
                doc=next(c for c in candidates if c['kind']=='REQUIRED_DOCUMENT' and c['evidence']['page']==15)
                assert '사업자등록증' in doc['content'] and '연구개발계획서' in doc['content']
                eligibility=next(c for c in candidates if c['kind']=='ELIGIBILITY_REQUIREMENT')
                assert eligibility['evidence']['page']==5 and '법인사업자이어야 함' in eligibility['content']
                assert any(c['kind']=='EVALUATION_CRITERION' and c['evidence']['page']==9 and '70점' in c['content'] for c in candidates)
                assert all('문의' not in c['content'] for c in candidates)
                period=next(c for c in candidates if c['kind']=='APPLICATION_PERIOD')
                assert '18:00' in period['content'] and '18:00' in period['evidence']['text']
        chosen=next(c for c in run['candidates'] if c['kind']=='ELIGIBILITY_REQUIREMENT')
        rv=confirm(context,v,chosen,resolution='Test-only isolated source review; all period source differences preserved')
        assert detail(context,n)['versions'][0]['confirmed'][0]['id']==rv['id']
