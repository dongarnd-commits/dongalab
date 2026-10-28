"""Frozen migration against existing synthetic Company/Request history."""
from uuid import uuid4
import pytest
from sqlalchemy import text,inspect
from sqlalchemy.orm import Session
from alembic.operations import Operations
from alembic.migration import MigrationContext
from v14_migration_chain import load,BEFORE_PROPOSAL
from isolation import require_test_database
from registration_sources import number
from app.infrastructure.database import get_engine,Base
from app.infrastructure.notice_store import SqlNoticeStore
from app.infrastructure.notice_documents import LocalPrivateFiles
from app.infrastructure import company_schema as C
from app.company.application import CompanyApplication
from app.notice.domain import Actor
pytestmark=pytest.mark.integration

def test_slice2_upgrade_preserves_existing_request_content_and_guard(tmp_path):
    require_test_database();schema='test_slice2_migration_'+uuid4().hex
    c=get_engine().connect().execution_options(schema_translate_map={None:schema});outer=c.begin()
    c.exec_driver_sql('CREATE SCHEMA '+schema);c.exec_driver_sql('SET LOCAL search_path='+schema+', public')
    session=Session(c,join_transaction_mode='create_savepoint')
    try:
        with Operations.context(MigrationContext.configure(c)):
            for filename in (*BEFORE_PROPOSAL,'e863p0012026_proposal_production.py','f974c0012026_company_workflow.py','fa85b0012026_company_business_sources.py','fb96c0012026_information_requests.py','fc07d0012026_recorded_authorization.py','fd18e0012026_company_file_reregistration.py'):load(filename).upgrade()
            store=SqlNoticeStore(session);editor=store.add('actors',username='TEST editor',role='COMPANY_EDITOR',password_hash='TEST_NO_LOGIN');operator=store.add('actors',username='TEST operator',role='DATCO_OPERATOR',password_hash='TEST_NO_LOGIN')
            a=CompanyApplication(session,LocalPrivateFiles(tmp_path));company=a.register(Actor(editor['id'],'COMPANY_EDITOR'),dict(name='TEST preserved company',business_number=number()))
            a.add(C.memberships,company_id=company['id'],actor_id=operator['id'],granted_by=editor['id'])
            who=Actor(operator['id'],'DATCO_OPERATOR');request=a.information_create(who,company['id'],'TEST preserved request','TEST immutable original');a.information_send(who,request['id']);session.commit()
            c.exec_driver_sql('SET CONSTRAINTS ALL IMMEDIATE');c.exec_driver_sql('SET CONSTRAINTS ALL DEFERRED')
            names=['companies','company_input_versions','company_evidence','company_information_requests','company_audit']
            before={n:[dict(r) for r in c.execute(text('SELECT * FROM '+n)).mappings()] for n in names}
            function=text("SELECT pg_get_functiondef(oid) FROM pg_proc WHERE proname='guard_company_information_request' AND pronamespace=current_schema()::regnamespace")
            config=text("SELECT proconfig FROM pg_proc WHERE proname='validate_common_analysis_lineage' AND pronamespace=current_schema()::regnamespace")
            settings=c.scalar(config)
            guard=c.scalar(function);increment=load('fe29s0022026_improvement_analysis.py');increment.upgrade()
            assert c.scalar(function)==guard
            assert c.scalar(config)==settings
            for n,rows in before.items():assert [dict(r) for r in c.execute(text('SELECT * FROM '+n)).mappings()]==rows
            for n,t in Base.metadata.tables.items():assert {x['name'] for x in inspect(c).get_columns(n,schema=schema)}==set(t.c.keys())
            increment.downgrade();assert c.scalar(function)==guard;increment.upgrade()
    finally:session.close();outer.rollback();c.close()
