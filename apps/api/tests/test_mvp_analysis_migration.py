"""MVP-only additive migration, real isolated PostgreSQL; immutable history preserved."""
from uuid import uuid4
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import ProgrammingError
from alembic.operations import Operations
from alembic.migration import MigrationContext
from v14_migration_chain import load, BEFORE_PROPOSAL, AFTER_COMPANY
from isolation import require_test_database
from registration_sources import number
from app.infrastructure.database import get_engine
from app.infrastructure.notice_store import SqlNoticeStore
from app.infrastructure.notice_documents import LocalPrivateFiles
from app.infrastructure import company_schema as C
from app.company.application import CompanyApplication
from app.notice.domain import Actor

pytestmark=pytest.mark.integration

def test_mvp_upgrade_preserves_history_function_configuration_and_request_guard(tmp_path):
    require_test_database()
    schema='test_mvp_migration_'+uuid4().hex
    c=get_engine().connect().execution_options(schema_translate_map={None:schema})
    outer=c.begin()
    c.exec_driver_sql('CREATE SCHEMA '+schema)
    c.exec_driver_sql('SET LOCAL search_path='+schema+', public')
    session=Session(c,join_transaction_mode='create_savepoint')
    try:
        with Operations.context(MigrationContext.configure(c)):
            for name in (*BEFORE_PROPOSAL,'e863p0012026_proposal_production.py','f974c0012026_company_workflow.py',*AFTER_COMPANY[:-1]):
                load(name).upgrade()
            store=SqlNoticeStore(session)
            editor=store.add('actors',username='TEST editor',role='COMPANY_EDITOR',password_hash='TEST_NO_LOGIN')
            operator=store.add('actors',username='TEST operator',role='DATCO_OPERATOR',password_hash='TEST_NO_LOGIN')
            a=CompanyApplication(session,LocalPrivateFiles(tmp_path))
            company=a.register(Actor(editor['id'],'COMPANY_EDITOR'),dict(name='TEST preserved MVP company',business_number=number()))
            a.add(C.memberships,company_id=company['id'],actor_id=operator['id'],granted_by=editor['id'])
            who=Actor(operator['id'],'DATCO_OPERATOR')
            request=a.information_create(who,company['id'],'TEST preserved request','TEST immutable original')
            a.information_send(who,request['id'])
            session.commit()
            c.exec_driver_sql('SET CONSTRAINTS ALL IMMEDIATE')
            c.exec_driver_sql('SET CONSTRAINTS ALL DEFERRED')
            tables=['companies','company_input_versions','company_evidence','company_information_requests','company_audit','notices','analysis_runs','capability_versions','match_results','proposal_versions']
            # Existing table names are obtained from the catalogue rather than assuming missing tables.
            available=set(c.execute(text("SELECT tablename FROM pg_tables WHERE schemaname=current_schema()")).scalars())
            tables=[name for name in tables if name in available]
            before={name:[dict(row) for row in c.execute(text('SELECT * FROM '+name+' ORDER BY id')).mappings()] for name in tables}
            query=text("SELECT pg_get_functiondef(oid) FROM pg_proc WHERE proname=:name AND pronamespace=current_schema()::regnamespace")
            request_guard=c.scalar(query,dict(name='guard_company_information_request'))
            config=c.scalar(text("SELECT proconfig FROM pg_proc WHERE proname='validate_improvement_lineage' AND pronamespace=current_schema()::regnamespace"))
            assert config and any('search_path' in value for value in config)
            increment=load('fg31m0012026_mvp_analysis_lineage.py')
            increment.upgrade()
            assert c.scalar(query,dict(name='guard_company_information_request'))==request_guard
            assert c.scalar(text("SELECT proconfig FROM pg_proc WHERE proname='validate_improvement_lineage' AND pronamespace=current_schema()::regnamespace"))==config
            for name,rows in before.items():
                assert [dict(row) for row in c.execute(text('SELECT * FROM '+name+' ORDER BY id')).mappings()]==rows
            trigger=text("SELECT count(*) FROM pg_trigger WHERE tgname='ck_mvp_structure_basis' AND tgrelid='company_improvement_versions'::regclass")
            assert c.scalar(trigger)==1
            with pytest.raises(ProgrammingError,match='INFORMATION_REQUEST_CONTENT_IS_IMMUTABLE'):
                with session.begin_nested():
                    session.execute(text("UPDATE company_information_requests SET message='TEST forbidden' WHERE id=:id"),dict(id=request['id']))
            increment.downgrade()
            assert c.scalar(trigger)==0
            assert c.scalar(query,dict(name='guard_company_information_request'))==request_guard
            increment.upgrade()
            assert c.scalar(trigger)==1
    finally:
        session.close()
        outer.rollback()
        c.close()
