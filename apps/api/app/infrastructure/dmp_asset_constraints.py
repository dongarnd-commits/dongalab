"""Frozen-compatible SQL for typed asset, generated-draft and composition lineage."""
ASSET_LINK_BODY = r"""
DECLARE version_key text; expected jsonb; actual jsonb; payload jsonb;
BEGIN
 IF TG_TABLE_NAME IN ('capability_versions','service_composition_versions') THEN version_key=NEW.id;
 ELSE version_key=NEW.version_id; END IF;
 IF TG_TABLE_NAME IN ('capability_versions','capability_version_features') THEN
  SELECT jsonb_agg(jsonb_build_object('revision_id',f->>'revision_id','role',f->>'role') ORDER BY f->>'revision_id')
   INTO expected FROM capability_versions v CROSS JOIN LATERAL jsonb_array_elements(v.data->'functions') f WHERE v.id=version_key;
  SELECT jsonb_agg(jsonb_build_object('revision_id',revision_id,'role',role) ORDER BY revision_id)
   INTO actual FROM capability_version_features WHERE version_id=version_key;
 ELSE
  SELECT data INTO payload FROM service_composition_versions WHERE id=version_key;
  IF payload->>'source_mode'='DMP_ASSET' THEN
   IF jsonb_typeof(payload->'capability_version_ids') IS DISTINCT FROM 'array'
    OR payload->'capability_version_ids'<>'[]'::jsonb
    OR EXISTS(SELECT 1 FROM composition_capabilities WHERE version_id=version_key)
    THEN RAISE EXCEPTION 'ASSET_CAPABILITY_MODE_MISMATCH' USING ERRCODE='23514'; END IF;
   SELECT jsonb_agg(jsonb_build_object('feature_revision_id',f->>'feature_revision_id','asset_version_id',f->>'asset_version_id',
    'system_version_id',f->>'system_version_id','module_version_id',f->>'module_version_id','role',f->>'role')
    ORDER BY f->>'feature_revision_id') INTO expected FROM jsonb_array_elements(payload->'asset_selections') f;
   SELECT jsonb_agg(jsonb_build_object('feature_revision_id',feature_revision_id,'asset_version_id',asset_version_id,
    'system_version_id',system_version_id,'module_version_id',module_version_id,'role',role)
    ORDER BY feature_revision_id) INTO actual FROM composition_asset_features WHERE version_id=version_key;
  ELSE
   SELECT jsonb_agg(f ORDER BY f) INTO expected FROM service_composition_versions v
    CROSS JOIN LATERAL jsonb_array_elements_text(v.data->'capability_version_ids') f WHERE v.id=version_key;
   SELECT jsonb_agg(capability_version_id ORDER BY capability_version_id) INTO actual FROM composition_capabilities WHERE version_id=version_key;
  END IF;
 END IF;
 IF expected IS NULL OR expected IS DISTINCT FROM actual THEN
  RAISE EXCEPTION 'IMMUTABLE_VERSION_LINK_MISMATCH' USING ERRCODE='23514';
 END IF;
 RETURN NULL;
END
"""

LINEAGE_BODY = r"""
BEGIN
 IF TG_TABLE_NAME='dmp_asset_relations' AND TG_OP='INSERT' AND
  EXISTS(SELECT 1 FROM dmp_asset_relations r JOIN dmp_asset_versions v ON v.id=r.version_id WHERE r.id=NEW.id AND v.xmin<>r.xmin)
 THEN RAISE EXCEPTION 'ASSET_FROZEN_CHILD_INSERT' USING ERRCODE='23514'; END IF;
 IF TG_TABLE_NAME='composition_asset_features' AND TG_OP='INSERT' AND
  EXISTS(SELECT 1 FROM composition_asset_features c JOIN service_composition_versions v ON v.id=c.version_id WHERE c.id=NEW.id AND v.xmin<>c.xmin)
 THEN RAISE EXCEPTION 'ASSET_FROZEN_CHILD_INSERT' USING ERRCODE='23514'; END IF;
 IF TG_TABLE_NAME='composition_asset_contexts' AND TG_OP='INSERT' AND
  EXISTS(SELECT 1 FROM composition_asset_contexts c JOIN service_composition_versions v ON v.id=c.version_id WHERE c.id=NEW.id AND v.xmin<>c.xmin)
 THEN RAISE EXCEPTION 'ASSET_FROZEN_CHILD_INSERT' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT 1 FROM dmp_asset_nodes n WHERE n.current_ordinal IS DISTINCT FROM
  (SELECT max(v.ordinal) FROM dmp_asset_versions v WHERE v.node_id=n.id))
 THEN RAISE EXCEPTION 'ASSET_CURRENT_VERSION_MISMATCH' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT 1 FROM dmp_asset_versions v JOIN dmp_asset_nodes n ON n.id=v.node_id
  LEFT JOIN dmp_asset_nodes p ON p.id=v.parent_id LEFT JOIN dmp_feature_revisions r ON r.id=v.source_revision_id
  LEFT JOIN dmp_asset_versions pv ON pv.id=v.parent_version_id JOIN local_actors actor ON actor.id=v.actor_id
  WHERE (n.kind='SYSTEM' AND (v.parent_id IS NOT NULL OR v.source_revision_id IS NOT NULL OR v.parent_version_id IS NOT NULL))
   OR (n.kind='MODULE' AND (p.kind IS DISTINCT FROM 'SYSTEM' OR v.source_revision_id IS NOT NULL))
   OR (n.kind='FEATURE' AND (p.kind IS DISTINCT FROM 'MODULE' OR r.feature_id IS DISTINCT FROM n.feature_id))
   OR (n.kind IN ('MODULE','FEATURE') AND pv.node_id IS DISTINCT FROM v.parent_id)
   OR actor.role<>'DATCO_ADMIN'
   OR COALESCE(v.data->>'availability','') NOT IN ('NEEDS_CONFIRMATION','VERIFIED','UNAVAILABLE','RETIRED')
   OR (v.data->>'availability'='VERIFIED' AND length(btrim(COALESCE(v.data->>'availability_evidence','')))=0))
 THEN RAISE EXCEPTION 'ASSET_TYPED_PARENT_OR_SOURCE_MISMATCH' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT 1 FROM dmp_asset_relations r JOIN dmp_asset_versions v ON v.id=r.version_id WHERE r.target_node_id=v.node_id)
 THEN RAISE EXCEPTION 'ASSET_SELF_DEPENDENCY' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT 1 FROM dmp_asset_relations r JOIN dmp_asset_versions t ON t.id=r.target_version_id WHERE t.node_id<>r.target_node_id)
 THEN RAISE EXCEPTION 'ASSET_RELATION_VERSION_MISMATCH' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT 1 FROM dmp_asset_versions v WHERE
  (SELECT COALESCE(jsonb_agg(jsonb_build_object('target_node_id',r->>'target_node_id','target_version_id',r->>'target_version_id',
    'kind',r->>'kind','condition',r->>'condition','verified',COALESCE((r->>'verified')::boolean,false),'evidence',COALESCE(r->>'evidence',''))
    ORDER BY r->>'target_node_id',r->>'kind'),'[]'::jsonb) FROM jsonb_array_elements(COALESCE(v.data->'relations','[]'::jsonb)) r)
  IS DISTINCT FROM
  (SELECT COALESCE(jsonb_agg(jsonb_build_object('target_node_id',r.target_node_id,'target_version_id',r.target_version_id,
    'kind',r.kind,'condition',r.condition,'verified',r.verified,'evidence',r.evidence)
    ORDER BY r.target_node_id,r.kind),'[]'::jsonb) FROM dmp_asset_relations r WHERE r.version_id=v.id))
 THEN RAISE EXCEPTION 'ASSET_RELATION_LINK_MISMATCH' USING ERRCODE='23514'; END IF;
 IF EXISTS(WITH RECURSIVE reach(start_id,node_id) AS (
   SELECT v.node_id,r.target_node_id FROM dmp_asset_relations r JOIN dmp_asset_versions v ON v.id=r.version_id
    JOIN dmp_asset_nodes n ON n.id=v.node_id AND n.current_ordinal=v.ordinal WHERE r.kind IN ('DEPENDENCY','REPLACEMENT')
   UNION SELECT g.start_id,r.target_node_id FROM reach g JOIN dmp_asset_nodes n ON n.id=g.node_id
    JOIN dmp_asset_versions v ON v.node_id=n.id AND v.ordinal=n.current_ordinal
    JOIN dmp_asset_relations r ON r.version_id=v.id WHERE r.kind IN ('DEPENDENCY','REPLACEMENT'))
   SELECT 1 FROM reach WHERE start_id=node_id)
 THEN RAISE EXCEPTION 'ASSET_DEPENDENCY_CYCLE' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT 1 FROM dmp_solution_runs s JOIN company_improvement_versions v ON v.id=s.improvement_version_id
  JOIN company_improvements i ON i.id=v.improvement_id
  WHERE i.company_id<>s.company_id OR s.input->'context'->>'company_id' IS DISTINCT FROM s.company_id
   OR s.input->'context'->>'improvement_version_id' IS DISTINCT FROM s.improvement_version_id
   OR s.input->'basis'->>'run_id' IS DISTINCT FROM s.analysis_run_id
   OR NOT EXISTS(SELECT 1 FROM analysis_improvement_contexts c JOIN improvement_analysis_manifests m ON m.id=c.manifest_id
     JOIN company_improvement_versions a ON a.id=m.version_id WHERE c.run_id=s.analysis_run_id AND m.company_id=s.company_id
     AND a.improvement_id=v.improvement_id AND a.id=s.input->'basis'->>'source_version_id'))
 THEN RAISE EXCEPTION 'ASSET_SOLUTION_SCOPE_MISMATCH' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT 1 FROM composition_asset_features f JOIN service_composition_versions v ON v.id=f.version_id
  LEFT JOIN dmp_asset_versions av ON av.id=f.asset_version_id LEFT JOIN dmp_asset_nodes an ON an.id=av.node_id
  LEFT JOIN dmp_asset_versions mv ON mv.id=f.module_version_id LEFT JOIN dmp_asset_nodes mn ON mn.id=mv.node_id
  LEFT JOIN dmp_asset_versions sv ON sv.id=f.system_version_id LEFT JOIN dmp_asset_nodes sn ON sn.id=sv.node_id
  WHERE v.data->>'source_mode' IS DISTINCT FROM 'DMP_ASSET'
   OR (f.asset_version_id IS NOT NULL AND (an.kind IS DISTINCT FROM 'FEATURE' OR av.source_revision_id IS DISTINCT FROM f.feature_revision_id
      OR mn.kind IS DISTINCT FROM 'MODULE' OR sn.kind IS DISTINCT FROM 'SYSTEM'
      OR av.parent_id IS DISTINCT FROM mv.node_id OR mv.parent_id IS DISTINCT FROM sv.node_id
      OR av.parent_version_id IS DISTINCT FROM f.module_version_id OR mv.parent_version_id IS DISTINCT FROM f.system_version_id))
   OR (f.asset_version_id IS NULL AND (f.module_version_id IS NOT NULL OR f.system_version_id IS NOT NULL)))
 THEN RAISE EXCEPTION 'ASSET_COMPOSITION_REF_MISMATCH' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT 1 FROM service_composition_versions v WHERE v.data->>'source_mode'='DMP_ASSET'
   AND (SELECT count(*) FROM composition_asset_contexts c WHERE c.version_id=v.id)<>1)
 OR EXISTS(SELECT 1 FROM composition_asset_contexts c JOIN service_composition_versions v ON v.id=c.version_id
  JOIN dmp_solution_runs r ON r.id=c.recommendation_id
  WHERE v.data->>'source_mode' IS DISTINCT FROM 'DMP_ASSET'
   OR v.context->>'company_id' IS DISTINCT FROM r.company_id OR v.improvement_version_id<>r.improvement_version_id
   OR v.data->'asset_basis'->>'recommendation_id' IS DISTINCT FROM r.id
   OR v.data->'asset_basis'->>'alternative_id' IS DISTINCT FROM c.alternative_id
   OR v.data->>'asset_review_note' IS DISTINCT FROM c.review_note
   OR v.data->>'asset_catalog_digest' IS DISTINCT FROM c.catalog_digest
   OR r.input->>'catalog_digest' IS DISTINCT FROM c.catalog_digest
   OR NOT EXISTS(SELECT 1 FROM jsonb_array_elements(r.data->'alternatives') a WHERE a->>'id'=c.alternative_id))
 THEN RAISE EXCEPTION 'ASSET_REVIEW_COMPOSITION_SCOPE_MISMATCH' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END
"""
