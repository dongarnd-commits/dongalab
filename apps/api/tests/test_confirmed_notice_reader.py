"""Real PostgreSQL isolation reused from Notice slice; read adapter is not a Matching engine."""
import pytest
from test_notice_slice import context, prepare, detail, confirm
from app.worker import process_one
from app.infrastructure.notice_store import SqlNoticeStore
from app.infrastructure.confirmed_notice_reader import ConfirmedNoticeReader
from app.notice.domain import Actor,Denied

pytestmark=pytest.mark.integration

def confirmed(context):
    notice,version,job=prepare(context)
    factory,files,actor=context
    process_one(factory,files)
    all_candidates=detail(context,notice)['versions'][0]['runs'][0]['candidates']
    # Explicit distinct kinds: arbitrary UUID order may select two periods,
    # whose existing single-value confirmation correctly replaces the first.
    candidates=[next(c for c in all_candidates if c['kind']==kind)
        for kind in ('REQUIRED_DOCUMENT','ELIGIBILITY_REQUIREMENT')]
    first=confirm(context,version,candidates[0])
    second=confirm(context,version,candidates[1])
    return notice,version,candidates,first,second

def test_current_cumulative_items_verify_each_review_and_preserve_original(context):
    notice,version,candidates,first,second=confirmed(context)
    factory,files,actor=context
    with factory() as session:
        store=SqlNoticeStore(session)
        before=store.rows('audits')
        result=ConfirmedNoticeReader(store,files).read(actor,notice['id'],second['id'])
        assert result['current_valid'] and result['notice_version_id']==version['id']
        assert len(result['items'])==2
        for item in result['items']:
            assert item['review']['outcome']=='CONFIRM' and item['review']['official_verified']
            assert item['content'] in item['evidence']['text']
        assert store.rows('audits')==before
        with pytest.raises(Denied,match='STALE_INPUT_VERSION'):
            ConfirmedNoticeReader(store,files).read(actor,notice['id'],first['id'])

@pytest.mark.parametrize('role',['DATCO_ADMIN','COMPANY_EDITOR','COMPANY_APPROVER'])
def test_operator_permission_is_not_inherited(context,role):
    factory,files,actor=context
    with factory() as session:
        with pytest.raises(Denied,match='ACTION_NOT_AUTHORIZED'):
            ConfirmedNoticeReader(SqlNoticeStore(session),files).read(Actor(actor.id,role),'invalid','invalid')

def test_each_copied_item_review_must_be_official_confirm(context):
    notice,version,candidates,first,second=confirmed(context)
    factory,files,actor=context
    with factory.begin() as session:
        store=SqlNoticeStore(session)
        old_review=store.rows('reviews',candidate_id=candidates[0]['id'])[0]
        store.change('reviews',old_review['id'],official_verified=False)
        with pytest.raises(Denied,match='OFFICIAL_SOURCE_NOT_VERIFIED'):
            ConfirmedNoticeReader(store,files).read(actor,notice['id'],second['id'])

def test_cross_source_and_mutated_content_are_denied(context):
    notice,version,candidates,first,second=confirmed(context)
    factory,files,actor=context
    with factory.begin() as session:
        store=SqlNoticeStore(session)
        item=store.rows('items',version_id=second['id'])[0]
        store.change('items',item['id'],content='not in original source')
        with pytest.raises(Denied,match='REQUIRED_EVIDENCE_MISSING'):
            ConfirmedNoticeReader(store,files).read(actor,notice['id'],second['id'])

def test_new_notice_version_and_wrong_notice_are_denied(context):
    notice,version,candidates,first,second=confirmed(context)
    factory,files,actor=context
    with factory.begin() as session:
        store=SqlNoticeStore(session)
        other=store.add('notices',external_key='TEST_OTHER_READER',title='Other test notice',current_ordinal=1)
        reader=ConfirmedNoticeReader(store,files)
        with pytest.raises(Denied,match='TARGET_VERSION_MISMATCH'): reader.read(actor,other['id'],second['id'])
        store.change('notices',notice['id'],current_ordinal=2)
        with pytest.raises(Denied,match='STALE_INPUT_VERSION'): reader.read(actor,notice['id'],second['id'])
