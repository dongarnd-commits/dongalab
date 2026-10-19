"""Frozen migration consumes this SQL once; runtime metadata contains no DDL hooks."""
BODY=r"""
DECLARE good boolean; cid varchar; sid varchar; actor_role varchar;
BEGIN
 IF TG_TABLE_NAME='company_fact_candidates' THEN
  SELECT e.company_id=NEW.company_id AND (e.site_id IS NULL OR e.site_id IS NOT DISTINCT FROM NEW.site_id) AND position(NEW.value in e.text)>0 INTO good FROM company_evidence e WHERE e.id=NEW.evidence_id;
 ELSIF TG_TABLE_NAME='company_evidence' THEN
  IF NEW.file_id IS NOT NULL THEN
   SELECT company_id=NEW.company_id AND (site_id IS NULL OR site_id IS NOT DISTINCT FROM NEW.site_id) INTO good FROM company_files WHERE id=NEW.file_id;
   IF NEW.parse_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM company_document_parses WHERE id=NEW.parse_id AND file_id=NEW.file_id AND error IS NULL) THEN good=false; END IF;
  ELSE SELECT company_id=NEW.company_id INTO good FROM company_input_versions WHERE id=NEW.input_version_id; END IF;
 ELSIF TG_TABLE_NAME='company_fact_acknowledgements' THEN
  SELECT c.company_id INTO cid FROM company_fact_candidates c WHERE c.id=NEW.candidate_id;
  SELECT role INTO actor_role FROM local_actors WHERE id=NEW.actor_id;
  good=actor_role='COMPANY_EDITOR' AND EXISTS(SELECT 1 FROM company_memberships WHERE company_id=cid AND actor_id=NEW.actor_id);
 ELSIF TG_TABLE_NAME='company_fact_reviews' THEN
  SELECT company_id INTO cid FROM company_fact_candidates WHERE id=NEW.candidate_id;
  SELECT role INTO actor_role FROM local_actors WHERE id=NEW.actor_id;
  good=actor_role='DATCO_OPERATOR' AND EXISTS(SELECT 1 FROM company_memberships WHERE company_id=cid AND actor_id=NEW.actor_id);
  IF NEW.existing_version_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM company_fact_versions v JOIN company_facts f ON f.id=v.fact_id JOIN company_fact_candidates c ON c.id=NEW.candidate_id WHERE v.id=NEW.existing_version_id AND f.company_id=c.company_id AND f.site_id IS NOT DISTINCT FROM c.site_id AND f.field=c.field AND f.period=c.period AND f.unit=c.unit AND f.currency=c.currency) THEN good=false; END IF;
  IF NEW.outcome LIKE 'CONFIRM%' AND COALESCE((SELECT a.agreed FROM company_fact_acknowledgements a WHERE a.candidate_id=NEW.candidate_id ORDER BY a.created_at DESC,a.id DESC LIMIT 1),false) IS DISTINCT FROM true THEN good=false; END IF;
  IF NEW.outcome='CONFIRM_EXISTING_VALUE' AND NOT EXISTS(SELECT 1 FROM company_fact_versions v JOIN company_fact_candidates c ON c.id=NEW.candidate_id WHERE v.id=NEW.existing_version_id AND v.value=c.value) THEN good=false; END IF;
 ELSIF TG_TABLE_NAME='company_fact_versions' THEN
  SELECT f.company_id=c.company_id AND f.site_id IS NOT DISTINCT FROM c.site_id AND f.field=c.field AND f.period=c.period AND f.unit=c.unit AND f.currency=c.currency AND NEW.value=c.value AND NEW.valid_from=c.valid_from AND NEW.evidence_id=c.evidence_id AND r.candidate_id=c.id AND r.outcome='CONFIRM_NEW_VALUE' AND COALESCE((SELECT a.agreed FROM company_fact_acknowledgements a WHERE a.candidate_id=c.id ORDER BY a.created_at DESC,a.id DESC LIMIT 1),false) INTO good FROM company_facts f,company_fact_candidates c,company_fact_reviews r WHERE f.id=NEW.fact_id AND c.id=NEW.candidate_id AND r.id=NEW.review_id;
 ELSIF TG_TABLE_NAME='company_improvement_facts' THEN
  SELECT i.company_id=f.company_id AND (f.site_id IS NULL OR f.site_id IS NOT DISTINCT FROM i.site_id) INTO good FROM company_improvement_versions v JOIN company_improvements i ON i.id=v.improvement_id,company_fact_versions fv JOIN company_facts f ON f.id=fv.fact_id WHERE v.id=NEW.version_id AND fv.id=NEW.fact_version_id;
 ELSIF TG_TABLE_NAME='company_improvement_evidence' THEN
  SELECT i.company_id=e.company_id AND (e.site_id IS NULL OR e.site_id IS NOT DISTINCT FROM i.site_id) INTO good FROM company_improvement_versions v JOIN company_improvements i ON i.id=v.improvement_id,company_evidence e WHERE v.id=NEW.version_id AND e.id=NEW.evidence_id;
 ELSIF TG_TABLE_NAME='company_improvement_reviews' THEN
  SELECT i.company_id INTO cid FROM company_improvement_versions v JOIN company_improvements i ON i.id=v.improvement_id WHERE v.id=NEW.version_id;
  SELECT role INTO actor_role FROM local_actors WHERE id=NEW.actor_id;
  good=EXISTS(SELECT 1 FROM company_memberships WHERE company_id=cid AND actor_id=NEW.actor_id) AND ((NEW.outcome IN ('SUBMIT','ACKNOWLEDGE') AND actor_role='COMPANY_EDITOR') OR (NEW.outcome IN ('CONFIRM','REQUEST_REVISION','MANUAL_STRUCTURE') AND actor_role='DATCO_OPERATOR'));
 ELSE RETURN NEW;
 END IF;
 IF good IS DISTINCT FROM true THEN RAISE EXCEPTION 'COMPANY_SCOPE_OR_REVIEW_MISMATCH' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END
"""
GUARDED=('company_fact_candidates','company_evidence','company_fact_acknowledgements','company_fact_reviews','company_fact_versions','company_improvement_facts','company_improvement_evidence','company_improvement_reviews')

ROOT_BODY=r"""
BEGIN
 IF NEW.id IS DISTINCT FROM OLD.id OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN RAISE EXCEPTION 'IMMUTABLE_COMPANY_IDENTITY' USING ERRCODE='23514'; END IF;
 IF TG_TABLE_NAME='companies' THEN
  IF NEW.business_number IS DISTINCT FROM OLD.business_number THEN RAISE EXCEPTION 'IMMUTABLE_COMPANY_IDENTITY' USING ERRCODE='23514'; END IF;
 ELSE
  IF NEW.company_id IS DISTINCT FROM OLD.company_id THEN RAISE EXCEPTION 'IMMUTABLE_COMPANY_SCOPE' USING ERRCODE='23514'; END IF;
  IF TG_TABLE_NAME IN ('company_facts','company_improvements') THEN
   IF NEW.site_id IS DISTINCT FROM OLD.site_id THEN RAISE EXCEPTION 'IMMUTABLE_COMPANY_SCOPE' USING ERRCODE='23514'; END IF;
  END IF;
  IF TG_TABLE_NAME='company_facts' THEN
   IF (NEW.field,NEW.period,NEW.unit,NEW.currency) IS DISTINCT FROM (OLD.field,OLD.period,OLD.unit,OLD.currency) THEN RAISE EXCEPTION 'IMMUTABLE_FACT_MEANING' USING ERRCODE='23514'; END IF;
  END IF;
 END IF;
 IF NEW.current_ordinal<OLD.current_ordinal OR NEW.current_ordinal>OLD.current_ordinal+1 THEN RAISE EXCEPTION 'INVALID_COMPANY_VERSION_TRANSITION' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END
"""
