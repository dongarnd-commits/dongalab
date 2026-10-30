"""Prepare synthetic identities only; all business states follow actual APIs/UI."""
import json
import os
import secrets
from pathlib import Path
from app.core.config import ROOT
from app.infrastructure.database import get_session_factory
from app.infrastructure.notice_store import SqlNoticeStore
from app.infrastructure.local_auth import hash_password
from isolation import require_test_database
from registration_sources import number
from app.demo import load_input
from app.infrastructure.notice_documents import LocalPrivateFiles


def prepare():
    require_test_database()
    nonce = os.environ['DATCO_TEST_NONCE']
    target = Path(os.environ['DATCO_MVP_READY']).resolve()
    if not target.is_relative_to((ROOT / 'storage/private/runtime').resolve()):
        raise RuntimeError('MVP_FIXTURE_PATH_REJECTED')
    password = 'TEST-' + secrets.token_urlsafe(24)
    accounts, ids = {}, {}
    with get_session_factory().begin() as session:
        store = SqlNoticeStore(session)
        for label, role in [('editor', 'COMPANY_EDITOR'), ('operator', 'DATCO_OPERATOR'), ('admin', 'DATCO_ADMIN'), ('approver', 'COMPANY_APPROVER')]:
            username = 'TEST_MVP_' + label + '_' + nonce
            account = store.add('actors', username=username, role=role, password_hash=hash_password(password))
            accounts[label], ids[label] = username, account['id']
        # Only source input is prepared. The browser must request the actual Worker,
        # inspect its candidates and record the human requirement review itself.
        notice = load_input(store, LocalPrivateFiles(Path(os.environ['DATCO_TEST_FILES'])), 'normal', external_key='TEST_MVP_UNANALYSED_' + nonce)
        version = store.rows('versions', notice_id=notice['id'])[-1]
        notice_input = dict(id=notice['id'], version_id=version['id'], title=notice['title'])
    target.write_text(json.dumps(dict(accounts=accounts, ids=ids, password=password, nonce=nonce, business_number=number(), notice=notice_input)), encoding='utf-8')
    print('MVP_SYNTHETIC_IDENTITIES_READY')


if __name__ == '__main__':
    prepare()
