"""Committed multi-session fixture only in the runner-owned test database."""
from contextlib import contextmanager
from uuid import uuid4
from sqlalchemy.orm import sessionmaker
from app.infrastructure.database import Base,get_engine,get_session
from app.infrastructure.analysis_constraints import install
from app.infrastructure.matching_constraints import install as install_inputs
from app.infrastructure.notice_documents import LocalPrivateFiles
from app.infrastructure.notice_store import SqlNoticeStore
from app.notice.application import NoticeApplication
from app.capability.application import CapabilityApplication
from app.main import app
import app.api.capability as cap_api
import app.api.notice as notice_api
from capability_scenario_fixture import ScenarioEnvironment,ScenarioInputs
from confirmed_comparison_fixture import metadata
from isolation import require_test_database

@contextmanager
def committed_environment(directory,protect_inputs=True):
    require_test_database()
    schema='test_committed_cap_'+uuid4().hex
    engine=get_engine().execution_options(schema_translate_map={None:schema})
    with engine.begin() as connection:
        connection.exec_driver_sql('CREATE SCHEMA '+schema)
        Base.metadata.create_all(connection);metadata.create_all(connection)
        install(connection,schema)
        if protect_inputs:install_inputs(connection,schema)
    factory=sessionmaker(bind=engine)
    directory.mkdir(parents=True,exist_ok=True)
    e=ScenarioEnvironment(factory,LocalPrivateFiles(directory/'sources'),directory)
    e.schema=schema;e.engine=engine
    overrides=dict(app.dependency_overrides);old_cap,old_notice=cap_api.application,notice_api.application
    def sessions():
        with factory() as session:yield session
    app.dependency_overrides[get_session]=sessions
    cap_api.application=lambda s:CapabilityApplication(s,e.files,ScenarioInputs(e))
    notice_api.application=lambda s:NoticeApplication(SqlNoticeStore(s),e.files)
    try:
        e.prepare();yield e
    finally:
        for c in e.clients.values():c.close()
        cap_api.application,notice_api.application=old_cap,old_notice
        app.dependency_overrides.clear();app.dependency_overrides.update(overrides)
        # The owning isolated runner removes this schema with its nonce database.
