"""Run the same DB constraints at a savepoint fixture's commit boundary."""
from sqlalchemy import event
from app.infrastructure.analysis_constraints import install

def install_test_lineage(connection,schema,factory):
    install(connection,schema)
    from app.infrastructure.matching_constraints import install as install_matching
    install_matching(connection,schema)
    from app.infrastructure.proposal_constraints import install as install_proposal
    install_proposal(connection,schema)
    @event.listens_for(factory,'before_commit')
    def validate(session):
        session.flush()
        session.connection().exec_driver_sql('SET CONSTRAINTS ALL IMMEDIATE')
        session.connection().exec_driver_sql('SET CONSTRAINTS ALL DEFERRED')
