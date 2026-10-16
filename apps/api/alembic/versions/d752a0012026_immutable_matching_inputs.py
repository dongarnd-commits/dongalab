"""P1: immutable snapshots and referenced version inputs. Frozen SQL."""
from alembic import op
import sqlalchemy as sa
revision='d752a0012026'
down_revision='c941a0042026'
branch_labels=None
depends_on=None
IMMUTABLE=('capability_match_snapshots', 'service_composition_versions', 'composition_capabilities', 'capability_versions', 'capability_version_features', 'dmp_feature_revisions', 'dmp_features')
LINK_TABLES=('capability_versions', 'capability_version_features', 'service_composition_versions', 'composition_capabilities')
LINK_BODY="\nDECLARE version_key text; expected jsonb; actual jsonb;\nBEGIN\n IF TG_TABLE_NAME IN ('capability_versions','service_composition_versions') THEN version_key=NEW.id;\n ELSE version_key=NEW.version_id; END IF;\n IF TG_TABLE_NAME IN ('capability_versions','capability_version_features') THEN\n  SELECT jsonb_agg(jsonb_build_object('revision_id',f->>'revision_id','role',f->>'role') ORDER BY f->>'revision_id')\n   INTO expected FROM capability_versions v CROSS JOIN LATERAL jsonb_array_elements(v.data->'functions') f WHERE v.id=version_key;\n  SELECT jsonb_agg(jsonb_build_object('revision_id',revision_id,'role',role) ORDER BY revision_id)\n   INTO actual FROM capability_version_features WHERE version_id=version_key;\n ELSE\n  SELECT jsonb_agg(f ORDER BY f) INTO expected FROM service_composition_versions v\n   CROSS JOIN LATERAL jsonb_array_elements_text(v.data->'capability_version_ids') f WHERE v.id=version_key;\n  SELECT jsonb_agg(capability_version_id ORDER BY capability_version_id) INTO actual FROM composition_capabilities WHERE version_id=version_key;\n END IF;\n IF expected IS NULL OR expected IS DISTINCT FROM actual THEN\n  RAISE EXCEPTION 'IMMUTABLE_VERSION_LINK_MISMATCH' USING ERRCODE='23514';\n END IF;\n RETURN NULL;\nEND\n"

def upgrade():
    bind=op.get_bind();q=bind.dialect.identifier_preparer.quote
    schema=bind.execute(sa.text('SELECT current_schema()')).scalar_one();ns=q(schema)
    op.execute('CREATE FUNCTION '+ns+".immutable_matching_input() RETURNS trigger LANGUAGE plpgsql AS $body$ BEGIN RAISE EXCEPTION 'IMMUTABLE_MATCHING_INPUT' USING ERRCODE='23514'; END $body$")
    for name in IMMUTABLE:
        op.execute('CREATE TRIGGER immutable_matching_input BEFORE UPDATE OR DELETE ON '+ns+'.'+q(name)+' FOR EACH ROW EXECUTE FUNCTION '+ns+'.immutable_matching_input()')
    op.execute('CREATE FUNCTION '+ns+'.validate_matching_version_links() RETURNS trigger LANGUAGE plpgsql SET search_path = '+ns+', pg_catalog AS $body$'+LINK_BODY+'$body$')
    for name in LINK_TABLES:
        op.execute('CREATE CONSTRAINT TRIGGER ck_matching_version_links AFTER INSERT ON '+ns+'.'+q(name)+' DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION '+ns+'.validate_matching_version_links()')

def downgrade():
    if op.get_bind().execute(sa.text('SELECT EXISTS(SELECT 1 FROM capability_match_snapshots)')).scalar():
        raise RuntimeError('Matching snapshots exist; reviewed downgrade required. No data deleted.')
    for name in LINK_TABLES:op.execute('DROP TRIGGER ck_matching_version_links ON '+name)
    op.execute('DROP FUNCTION validate_matching_version_links()')
    for name in IMMUTABLE:op.execute('DROP TRIGGER immutable_matching_input ON '+name)
    op.execute('DROP FUNCTION immutable_matching_input()')
