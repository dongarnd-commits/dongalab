"""Immutable matching inputs and complete version links; no new business state."""
IMMUTABLE = ('capability_match_snapshots','service_composition_versions','composition_capabilities',
             'capability_versions','capability_version_features','dmp_feature_revisions','dmp_features')
LINK_TABLES = ('capability_versions','capability_version_features','service_composition_versions','composition_capabilities')
LINK_BODY = r"""
DECLARE version_key text; expected jsonb; actual jsonb;
BEGIN
 IF TG_TABLE_NAME IN ('capability_versions','service_composition_versions') THEN version_key=NEW.id;
 ELSE version_key=NEW.version_id; END IF;
 IF TG_TABLE_NAME IN ('capability_versions','capability_version_features') THEN
  SELECT jsonb_agg(jsonb_build_object('revision_id',f->>'revision_id','role',f->>'role') ORDER BY f->>'revision_id')
   INTO expected FROM capability_versions v CROSS JOIN LATERAL jsonb_array_elements(v.data->'functions') f WHERE v.id=version_key;
  SELECT jsonb_agg(jsonb_build_object('revision_id',revision_id,'role',role) ORDER BY revision_id)
   INTO actual FROM capability_version_features WHERE version_id=version_key;
 ELSE
  SELECT jsonb_agg(f ORDER BY f) INTO expected FROM service_composition_versions v
   CROSS JOIN LATERAL jsonb_array_elements_text(v.data->'capability_version_ids') f WHERE v.id=version_key;
  SELECT jsonb_agg(capability_version_id ORDER BY capability_version_id) INTO actual FROM composition_capabilities WHERE version_id=version_key;
 END IF;
 IF expected IS NULL OR expected IS DISTINCT FROM actual THEN
  RAISE EXCEPTION 'IMMUTABLE_VERSION_LINK_MISMATCH' USING ERRCODE='23514';
 END IF;
 RETURN NULL;
END
"""

def install(connection, schema='public'):
    q=connection.dialect.identifier_preparer.quote; ns=q(schema)
    connection.exec_driver_sql('CREATE FUNCTION '+ns+".immutable_matching_input() RETURNS trigger LANGUAGE plpgsql AS $body$ BEGIN RAISE EXCEPTION 'IMMUTABLE_MATCHING_INPUT' USING ERRCODE='23514'; END $body$")
    for name in IMMUTABLE:
        connection.exec_driver_sql('CREATE TRIGGER immutable_matching_input BEFORE UPDATE OR DELETE ON '+ns+'.'+q(name)+' FOR EACH ROW EXECUTE FUNCTION '+ns+'.immutable_matching_input()')
    connection.exec_driver_sql('CREATE FUNCTION '+ns+'.validate_matching_version_links() RETURNS trigger LANGUAGE plpgsql SET search_path = '+ns+', pg_catalog AS $body$'+LINK_BODY+'$body$')
    for name in LINK_TABLES:
        connection.exec_driver_sql('CREATE CONSTRAINT TRIGGER ck_matching_version_links AFTER INSERT ON '+ns+'.'+q(name)+' DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION '+ns+'.validate_matching_version_links()')
