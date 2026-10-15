"""PostgreSQL deferred cross-record invariants; also installed in disposable test schemas."""
FUNCTION_BODY = r"""
BEGIN
 IF EXISTS (
  SELECT 1 FROM analysis_runs r WHERE
   (r.analysis_kind='NOTICE_REQUIREMENT_ANALYSIS' AND (EXISTS(SELECT 1 FROM analysis_capability_contexts c WHERE c.run_id=r.id) OR EXISTS(SELECT 1 FROM analysis_match_contexts c WHERE c.run_id=r.id))) OR
   (r.analysis_kind='CAPABILITY_ASSESSMENT' AND ((SELECT count(*) FROM analysis_capability_contexts c WHERE c.run_id=r.id)<>1 OR EXISTS(SELECT 1 FROM analysis_match_contexts c WHERE c.run_id=r.id))) OR
   (r.analysis_kind='SUPPORT_MATCHING' AND ((SELECT count(*) FROM analysis_match_contexts c WHERE c.run_id=r.id)<>1 OR EXISTS(SELECT 1 FROM analysis_capability_contexts c WHERE c.run_id=r.id))) OR
   (r.analysis_kind<>'NOTICE_REQUIREMENT_ANALYSIS' AND NOT EXISTS(SELECT 1 FROM analysis_candidates c WHERE c.run_id=r.id))
 ) THEN RAISE EXCEPTION 'ANALYSIS_RUN_CONTEXT_MISMATCH' USING ERRCODE='23514'; END IF;
 IF EXISTS (
  SELECT 1 FROM analysis_capability_contexts c JOIN analysis_runs r ON r.id=c.run_id JOIN capability_assessments a ON a.id=c.assessment_id
  WHERE r.analysis_kind<>'CAPABILITY_ASSESSMENT' OR c.capability_version_id<>a.capability_version_id OR c.company_id<>a.company_id OR c.improvement_version_id<>a.improvement_version_id
   OR c.input->'context'->>'company_id' IS DISTINCT FROM a.company_id OR c.input->'context'->>'improvement_version_id' IS DISTINCT FROM a.improvement_version_id
   OR (c.previous_assessment_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM capability_assessments p WHERE p.id=c.previous_assessment_id AND p.company_id=c.company_id))
   OR (c.composition_version_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM service_composition_versions v JOIN service_compositions s ON s.id=v.composition_id JOIN composition_capabilities l ON l.version_id=v.id WHERE v.id=c.composition_version_id AND s.company_id=c.company_id AND v.improvement_version_id=c.improvement_version_id AND l.assessment_id=a.id AND l.capability_version_id=c.capability_version_id))
 ) THEN RAISE EXCEPTION 'ASSESSMENT_CONTEXT_MISMATCH' USING ERRCODE='23514'; END IF;
 IF EXISTS (
  SELECT 1 FROM analysis_match_contexts c JOIN analysis_runs r ON r.id=c.run_id JOIN capability_match_candidates m ON m.id=c.match_candidate_id JOIN capability_match_snapshots s ON s.id=c.snapshot_id JOIN service_composition_versions v ON v.id=s.composition_version_id JOIN service_compositions p ON p.id=v.composition_id
  WHERE r.analysis_kind<>'SUPPORT_MATCHING' OR m.snapshot_id<>s.id OR s.input->'company'->>'company_id' IS DISTINCT FROM p.company_id OR s.input->'company'->>'improvement_version_id' IS DISTINCT FROM v.improvement_version_id
   OR s.input->'notice'->>'requirement_version_id' IS DISTINCT FROM s.requirement_version_id
 ) THEN RAISE EXCEPTION 'MATCH_CONTEXT_MISMATCH' USING ERRCODE='23514'; END IF;
 IF EXISTS (
  SELECT 1 FROM analysis_candidates c JOIN analysis_runs r ON r.id=c.run_id
  LEFT JOIN source_locations l ON l.id=c.location_id LEFT JOIN notice_sources s ON s.id=l.source_id
  WHERE c.analysis_kind<>r.analysis_kind
   OR (c.analysis_kind='NOTICE_REQUIREMENT_ANALYSIS' AND (l.run_id<>r.id OR s.version_id<>r.version_id))
   OR (c.analysis_kind='CAPABILITY_ASSESSMENT' AND (c.kind<>'CAPABILITY_ASSESSMENT' OR NOT EXISTS(SELECT 1 FROM analysis_capability_contexts x WHERE x.run_id=r.id AND x.assessment_id=c.assessment_id)))
   OR (c.analysis_kind='SUPPORT_MATCHING' AND (c.kind<>'SUPPORT_MATCHING' OR NOT EXISTS(SELECT 1 FROM analysis_match_contexts x WHERE x.run_id=r.id AND x.match_candidate_id=c.match_candidate_id)))
 ) THEN RAISE EXCEPTION 'ANALYSIS_CANDIDATE_TARGET_MISMATCH' USING ERRCODE='23514'; END IF;
 IF EXISTS (SELECT 1 FROM capability_assessments a WHERE NOT a.legacy_lineage AND NOT EXISTS(SELECT 1 FROM analysis_capability_contexts x JOIN analysis_candidates c ON c.run_id=x.run_id WHERE x.run_id=a.analysis_run_id AND x.assessment_id=a.id AND c.assessment_id=a.id))
 OR EXISTS (SELECT 1 FROM capability_match_candidates m WHERE NOT m.legacy_lineage AND NOT EXISTS(SELECT 1 FROM analysis_match_contexts x JOIN analysis_candidates c ON c.run_id=x.run_id WHERE x.run_id=m.analysis_run_id AND x.match_candidate_id=m.id AND c.match_candidate_id=m.id))
 THEN RAISE EXCEPTION 'DOMAIN_CANDIDATE_LINEAGE_MISSING' USING ERRCODE='23514'; END IF;
 IF EXISTS (
  SELECT 1 FROM analysis_reviews r JOIN analysis_candidates c ON c.id=r.candidate_id
  WHERE r.analysis_kind<>c.analysis_kind OR
    (r.analysis_kind='NOTICE_REQUIREMENT_ANALYSIS' AND EXISTS(SELECT 1 FROM analysis_domain_review_contexts x WHERE x.review_id=r.id)) OR
    (r.analysis_kind<>'NOTICE_REQUIREMENT_ANALYSIS' AND (SELECT count(*) FROM analysis_domain_review_contexts x WHERE x.review_id=r.id)<>1)
 ) THEN RAISE EXCEPTION 'ANALYSIS_REVIEW_KIND_MISMATCH' USING ERRCODE='23514'; END IF;
 IF EXISTS (
  SELECT 1 FROM analysis_domain_review_contexts x JOIN analysis_reviews r ON r.id=x.review_id JOIN analysis_candidates c ON c.id=r.candidate_id
  LEFT JOIN capability_assessment_reviews a ON a.id=x.assessment_review_id LEFT JOIN capability_match_reviews m ON m.id=x.match_review_id
  WHERE (x.assessment_review_id IS NOT NULL AND (r.analysis_kind<>'CAPABILITY_ASSESSMENT' OR a.assessment_id IS DISTINCT FROM c.assessment_id OR a.analysis_review_id IS DISTINCT FROM r.id OR a.actor_id<>r.actor_id OR a.note<>r.note OR a.created_at<>r.created_at))
     OR (x.match_review_id IS NOT NULL AND (r.analysis_kind<>'SUPPORT_MATCHING' OR m.candidate_id IS DISTINCT FROM c.match_candidate_id OR m.analysis_review_id IS DISTINCT FROM r.id OR m.actor_id<>r.actor_id OR m.note<>r.note OR m.created_at<>r.created_at))
 ) THEN RAISE EXCEPTION 'DOMAIN_REVIEW_TARGET_MISMATCH' USING ERRCODE='23514'; END IF;
 IF EXISTS (SELECT 1 FROM capability_match_reviews m WHERE NOT m.legacy_lineage AND NOT EXISTS(SELECT 1 FROM analysis_domain_review_contexts x WHERE x.match_review_id=m.id AND x.review_id=m.analysis_review_id))
 OR EXISTS (SELECT 1 FROM capability_assessment_reviews a WHERE NOT EXISTS(SELECT 1 FROM analysis_domain_review_contexts x WHERE x.assessment_review_id=a.id AND x.review_id=a.analysis_review_id))
 THEN RAISE EXCEPTION 'DOMAIN_REVIEW_LINEAGE_MISSING' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END
"""
TABLES=('analysis_runs','analysis_capability_contexts','analysis_match_contexts','analysis_candidates','analysis_reviews','analysis_domain_review_contexts','capability_assessments','capability_match_candidates','capability_match_reviews','capability_assessment_reviews','composition_capabilities','capability_match_snapshots','service_composition_versions','service_compositions','source_locations','notice_sources')
IMMUTABLE=('analysis_runs','analysis_capability_contexts','analysis_match_contexts','analysis_candidates','analysis_reviews','analysis_domain_review_contexts','capability_assessment_reviews')
def install(connection,schema='public'):
    quote=connection.dialect.identifier_preparer.quote
    namespace=quote(schema)
    connection.exec_driver_sql('CREATE FUNCTION '+namespace+'.validate_common_analysis_lineage() RETURNS trigger LANGUAGE plpgsql SET search_path = '+namespace+', pg_catalog AS $body$'+FUNCTION_BODY+'$body$')
    connection.exec_driver_sql('CREATE FUNCTION '+namespace+".immutable_common_analysis() RETURNS trigger LANGUAGE plpgsql AS $body$ BEGIN RAISE EXCEPTION 'IMMUTABLE_ANALYSIS_HISTORY' USING ERRCODE='23514'; END $body$")
    for name in TABLES:
        connection.exec_driver_sql('CREATE CONSTRAINT TRIGGER ck_common_lineage AFTER INSERT OR UPDATE OR DELETE ON '+namespace+'.'+quote(name)+' DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION '+namespace+'.validate_common_analysis_lineage()')
    for name in IMMUTABLE:
        connection.exec_driver_sql('CREATE TRIGGER immutable_analysis_history BEFORE UPDATE OR DELETE ON '+namespace+'.'+quote(name)+' FOR EACH ROW EXECUTE FUNCTION '+namespace+'.immutable_common_analysis()')

DOMAIN_TABLES=('capability_assessments','capability_match_candidates','capability_match_reviews')
DOMAIN_BODY=r"""
BEGIN
 IF TG_OP='INSERT' THEN
  IF NEW.legacy_lineage THEN RAISE EXCEPTION 'NEW_LEGACY_LINEAGE_FORBIDDEN' USING ERRCODE='23514'; END IF;
  RETURN NEW;
 END IF;
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'IMMUTABLE_DOMAIN_ANALYSIS_HISTORY' USING ERRCODE='23514'; END IF;
 IF TG_TABLE_NAME='capability_assessments' AND (to_jsonb(NEW)-'state')=(to_jsonb(OLD)-'state') THEN RETURN NEW; END IF;
 RAISE EXCEPTION 'IMMUTABLE_DOMAIN_ANALYSIS_HISTORY' USING ERRCODE='23514';
END
"""
_install_common=install
def install(connection,schema='public'):
    _install_common(connection,schema)
    quote=connection.dialect.identifier_preparer.quote;namespace=quote(schema)
    connection.exec_driver_sql('CREATE FUNCTION '+namespace+'.guard_domain_analysis_history() RETURNS trigger LANGUAGE plpgsql AS $body$'+DOMAIN_BODY+'$body$')
    for name in DOMAIN_TABLES:
        connection.exec_driver_sql('CREATE TRIGGER guard_domain_analysis_history BEFORE INSERT OR UPDATE OR DELETE ON '+namespace+'.'+quote(name)+' FOR EACH ROW EXECUTE FUNCTION '+namespace+'.guard_domain_analysis_history()')
