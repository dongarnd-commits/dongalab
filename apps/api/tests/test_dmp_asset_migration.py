"""New frozen migration preserves existing data and protects typed asset lineage."""
from uuid import uuid4
from copy import deepcopy
import pytest
from sqlalchemy import text, update, insert
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from alembic.operations import Operations
from alembic.migration import MigrationContext
from v14_migration_chain import load, BEFORE_PROPOSAL, AFTER_COMPANY
from isolation import require_test_database
from app.infrastructure.database import get_engine
from app.infrastructure.notice_store import SqlNoticeStore
from app.infrastructure.notice_documents import LocalPrivateFiles
from app.infrastructure import dmp_asset_schema as D
from app.capability.application import CapabilityApplication, fingerprint
from app.capability.asset_catalog import AssetCatalogApplication
from app.notice.domain import Actor

pytestmark = pytest.mark.integration


def rows_digest(connection, names):
    result = {}
    for name in names:
        rows = [dict(r) for r in connection.execute(text("SELECT * FROM "+name+" ORDER BY id")).mappings()]
        result[name] = (len(rows), fingerprint(rows))
    return result


def test_asset_upgrade_empty_downgrade_history_refusal_and_original_guards(tmp_path):
    require_test_database()
    schema = "test_dmp_migration_"+uuid4().hex
    connection = get_engine().connect().execution_options(schema_translate_map={None:schema})
    transaction = connection.begin()
    connection.exec_driver_sql("CREATE SCHEMA "+schema)
    connection.exec_driver_sql("SET LOCAL search_path="+schema+", public")
    session = Session(connection, join_transaction_mode="create_savepoint")
    try:
        with Operations.context(MigrationContext.configure(connection)):
            for name in (*BEFORE_PROPOSAL, "e863p0012026_proposal_production.py",
                         "f974c0012026_company_workflow.py", *AFTER_COMPANY):
                load(name).upgrade()
            store = SqlNoticeStore(session)
            admin = store.add("actors", username="TEST migration admin", role="DATCO_ADMIN", password_hash="TEST_NO_LOGIN")
            session.commit()
            tables = list(connection.execute(text("SELECT tablename FROM pg_tables WHERE schemaname=current_schema() ORDER BY tablename")).scalars())
            baseline = rows_digest(connection, tables)
            function_query = text("SELECT proname,pg_get_functiondef(oid),proconfig FROM pg_proc WHERE pronamespace=current_schema()::regnamespace ORDER BY proname")
            functions = {r[0]:(r[1],r[2]) for r in connection.execute(function_query)}
            triggers = list(connection.execute(text("SELECT tgname,tgrelid::regclass::text,pg_get_triggerdef(oid) FROM pg_trigger WHERE NOT tgisinternal AND tgrelid IN (SELECT oid FROM pg_class WHERE relnamespace=current_schema()::regnamespace) ORDER BY tgname,tgrelid::regclass::text")))
            increment = load("gh02a0012026_dmp_assets.py")
            increment.upgrade()
            assert rows_digest(connection,tables)==baseline
            current = {r[0]:(r[1],r[2]) for r in connection.execute(function_query)}
            for name,value in functions.items():
                assert current[name][1]==value[1]
                if name!="validate_matching_version_links":
                    assert current[name]==value
            now = list(connection.execute(text("SELECT tgname,tgrelid::regclass::text,pg_get_triggerdef(oid) FROM pg_trigger WHERE NOT tgisinternal AND tgrelid IN (SELECT oid FROM pg_class WHERE relnamespace=current_schema()::regnamespace) ORDER BY tgname,tgrelid::regclass::text")))
            assert all(row in now for row in triggers)
            increment.downgrade()
            assert rows_digest(connection,tables)==baseline
            restored = {r[0]:(r[1],r[2]) for r in connection.execute(function_query)}
            assert restored==functions
            increment.upgrade()
            application = AssetCatalogApplication(CapabilityApplication(session,LocalPrivateFiles(tmp_path)))
            created = application.create(Actor(admin["id"],"DATCO_ADMIN"),kind="SYSTEM",
                data=dict(name="TEST version-preserved system",availability="NEEDS_CONFIRMATION"),
                key=uuid4().hex)
            session.commit()
            connection.exec_driver_sql("SET CONSTRAINTS ALL IMMEDIATE")
            connection.exec_driver_sql("SET CONSTRAINTS ALL DEFERRED")
            version = connection.execute(text("SELECT data FROM dmp_asset_versions WHERE id=:id"),{"id":created["version_id"]}).scalar_one()
            with pytest.raises(IntegrityError,match="IMMUTABLE_MATCHING_INPUT"):
                with session.begin_nested():
                    session.execute(update(D.versions).where(D.versions.c.id==created["version_id"]).values(data=dict(version,name="TEST forbidden")))
            with pytest.raises(RuntimeError,match="DMP_ASSET_HISTORY_EXISTS"):
                increment.downgrade()
            assert connection.scalar(text("SELECT count(*) FROM dmp_asset_versions"))==1
            assert rows_digest(connection,tables)["local_actors"]==baseline["local_actors"]
            assert set(t.name for t in D.TABLES)<=set(connection.execute(text("SELECT tablename FROM pg_tables WHERE schemaname=current_schema()")).scalars())
    finally:
        session.close()
        transaction.rollback()
        connection.close()
