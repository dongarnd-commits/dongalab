"""Saved Notice search retains exact version, mode and human-reviewed scope."""
from copy import deepcopy
import pytest
from sqlalchemy import select, func
from app.notice.catalog import saved_catalog
from app.notice.domain import Actor, Denied
from app.infrastructure import notice_schema as N
from app.infrastructure.bizinfo import BizinfoSnapshot
from app.collector.worker import process_collection_one
from app.infrastructure.notice_store import SqlNoticeStore
from test_notice_slice import context, detail, confirm
from test_bizinfo import request_collection, first_record
from app.notice.application import NoticeApplication
from app.worker import process_one
from uuid import uuid4

pytestmark = pytest.mark.integration


def test_saved_catalog_paging_search_literal_mode_and_no_hidden_collection(context):
    factory, files, actor = context
    provider = BizinfoSnapshot()
    first_input = deepcopy(provider.data['jsonArray'][0])
    second_input = deepcopy(first_input)
    second_input.update(pblancId='PBLN_TEST_SECOND_SAVED', pblancNm='TEST distinct saved notice', pblancUrl=None, flpthNm=None, printFlpthNm=None)
    provider.data['jsonArray'] = [first_input, second_input]
    job = request_collection(context)
    process_collection_one(factory, files, provider)
    with factory() as session:
        before_jobs = session.scalar(select(func.count()).select_from(N.jobs))
        first = saved_catalog(session, actor, page=1, limit=1)
        second = saved_catalog(session, actor, page=2, limit=1)
        assert first['total'] == 2 and len(first['items']) == len(second['items']) == 1
        assert first['items'][0]['id'] != second['items'][0]['id']
        row = first['items'][0]
        assert row['version_id'] and row['ordinal'] == 1 and row['mode'] == 'SANITIZED_SNAPSHOT'
        assert row['requirement_version_id'] is None and row['requirement_state'] == 'REVIEW_REQUIRED'
        assert saved_catalog(session, actor, query=row['title'])['total'] == 1
        assert saved_catalog(session, actor, agency=row['agency'])['total'] >= 1
        assert saved_catalog(session, actor, mode='LIVE')['total'] == 0
        assert saved_catalog(session, actor, query='%')['total'] == 0
        assert saved_catalog(session, actor, query='_')['total'] == 0
        assert saved_catalog(session, actor, query='TEST no matching actual notice')['total'] == 0
        assert saved_catalog(session, actor, page=999)['items'] == []
        assert session.scalar(select(func.count()).select_from(N.jobs)) == before_jobs
        assert 'raw_reference' not in str(first) and 'storage_key' not in str(first)
        for role in ('DATCO_ADMIN', 'COMPANY_EDITOR', 'COMPANY_APPROVER'):
            with pytest.raises(Denied) as denied:
                saved_catalog(session, Actor(actor.id, role))
            assert denied.value.status == 403


def test_new_saved_version_does_not_borrow_old_reviewed_requirement(context):
    factory, files, actor = context
    job = request_collection(context)
    process_collection_one(factory, files)
    record = first_record(context, job)
    with factory.begin() as session:
        NoticeApplication(SqlNoticeStore(session), files).request(actor, record['notice_version_id'], str(uuid4()))
    process_one(factory, files)
    version = detail(context, {'id': record['notice_id']})['versions'][0]
    candidate = next(c for c in version['runs'][0]['candidates'] if c['kind'] == 'REQUIRED_DOCUMENT')
    reviewed = confirm(context, version, candidate)
    with factory() as session:
        old = next(r for r in saved_catalog(session, actor)['items'] if r['id'] == record['notice_id'])
        assert old['requirement_version_id'] == reviewed['id']
    changed = BizinfoSnapshot()
    changed.data = deepcopy(changed.data)
    changed.data['jsonArray'][0]['pblancNm'] += ' TEST amended'
    second = request_collection(context)
    process_collection_one(factory, files, changed)
    with factory() as session:
        new = next(r for r in saved_catalog(session, actor)['items'] if r['id'] == record['notice_id'])
        assert new['ordinal'] == 2 and new['version_id'] != old['version_id']
        assert new['requirement_version_id'] is None and new['requirement_state'] == 'REVIEW_REQUIRED'
        assert session.scalar(select(func.count()).select_from(N.requirement_versions).where(N.requirement_versions.c.id == reviewed['id'])) == 1
