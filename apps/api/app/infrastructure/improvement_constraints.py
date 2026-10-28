"""Deferred typed lineage checks and append-only Slice 2 history."""
BODY = r"""
BEGIN
 IF TG_OP='INSERT' AND (
 EXISTS(SELECT 1 FROM improvement_analysis_inputs x JOIN improvement_analysis_manifests m ON m.id=x.manifest_id WHERE TG_TABLE_NAME='improvement_analysis_inputs' AND x.id=NEW.id AND x.xmin<>m.xmin)
 OR EXISTS(SELECT 1 FROM analysis_improvement_contexts c JOIN analysis_runs r ON r.id=c.run_id WHERE TG_TABLE_NAME='analysis_improvement_contexts' AND c.id=NEW.id AND c.xmin<>r.xmin)
 OR EXISTS(SELECT 1 FROM improvement_analysis_inspections s JOIN analysis_runs r ON r.id=s.run_id WHERE TG_TABLE_NAME='improvement_analysis_inspections' AND s.id=NEW.id AND s.xmin<>r.xmin)
 OR EXISTS(SELECT 1 FROM improvement_analysis_candidate_details d JOIN analysis_candidates a ON a.id=d.candidate_id WHERE TG_TABLE_NAME='improvement_analysis_candidate_details' AND d.id=NEW.id AND d.xmin<>a.xmin)
 OR EXISTS(SELECT 1 FROM analysis_candidates a JOIN analysis_runs r ON r.id=a.run_id WHERE TG_TABLE_NAME='analysis_candidates' AND a.id=NEW.id AND a.analysis_kind='IMPROVEMENT_ANALYSIS' AND a.xmin<>r.xmin)
 OR EXISTS(SELECT 1 FROM improvement_request_draft_selections s JOIN improvement_request_draft_versions v ON v.id=s.draft_version_id WHERE TG_TABLE_NAME='improvement_request_draft_selections' AND s.id=NEW.id AND s.xmin<>v.xmin))
 THEN RAISE EXCEPTION 'IMPROVEMENT_FROZEN_CHILD_INSERT' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT 1 FROM background_jobs j WHERE j.kind='IMPROVEMENT_ANALYSIS' AND (SELECT count(*) FROM improvement_analysis_manifests m WHERE m.job_id=j.id)<>1)
 OR EXISTS(SELECT 1 FROM improvement_analysis_manifests m JOIN background_jobs j ON j.id=m.job_id JOIN company_improvement_versions v ON v.id=m.version_id JOIN company_improvements i ON i.id=v.improvement_id JOIN company_improvement_reviews s ON s.id=m.submit_review_id JOIN company_input_versions p ON p.id=m.input_version_id JOIN company_site_versions sv ON sv.id=m.site_version_id WHERE j.kind<>'IMPROVEMENT_ANALYSIS' OR i.company_id<>m.company_id OR s.version_id<>v.id OR s.outcome<>'SUBMIT' OR p.company_id<>m.company_id OR sv.site_id<>i.site_id OR sv.ordinal<>v.site_ordinal)
 THEN RAISE EXCEPTION 'IMPROVEMENT_MANIFEST_MISMATCH' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT 1 FROM improvement_analysis_inputs x JOIN improvement_analysis_manifests m ON m.id=x.manifest_id JOIN company_improvement_versions v ON v.id=m.version_id JOIN company_improvements i ON i.id=v.improvement_id LEFT JOIN company_files f ON f.id=x.file_id LEFT JOIN company_evidence e ON e.id=x.evidence_id LEFT JOIN company_fact_versions fv ON fv.id=x.fact_version_id LEFT JOIN company_facts ft ON ft.id=fv.fact_id LEFT JOIN company_document_parses p ON p.id=x.parse_id WHERE
 (f.id IS NOT NULL AND (f.company_id<>m.company_id OR (f.site_id IS NOT NULL AND f.site_id<>i.site_id) OR f.digest IS DISTINCT FROM x.data->>'digest')) OR
 (e.id IS NOT NULL AND (e.company_id<>m.company_id OR (e.site_id IS NOT NULL AND e.site_id<>i.site_id))) OR
 (ft.id IS NOT NULL AND (ft.company_id<>m.company_id OR (ft.site_id IS NOT NULL AND ft.site_id<>i.site_id))) OR
 (x.parse_id IS NOT NULL AND (p.file_id IS DISTINCT FROM f.id OR p.error IS NOT NULL)) OR
 (x.fact_review_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM company_fact_reviews fr WHERE fr.id=x.fact_review_id AND (fr.id=fv.review_id OR fr.existing_version_id=fv.id))))
 THEN RAISE EXCEPTION 'IMPROVEMENT_INPUT_SCOPE_MISMATCH' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT 1 FROM analysis_runs r WHERE r.analysis_kind='IMPROVEMENT_ANALYSIS' AND (SELECT count(*) FROM analysis_improvement_contexts c WHERE c.run_id=r.id)<>1)
 OR EXISTS(SELECT 1 FROM analysis_improvement_contexts c JOIN analysis_runs r ON r.id=c.run_id JOIN job_attempts a ON a.id=r.attempt_id JOIN improvement_analysis_manifests m ON m.id=c.manifest_id JOIN background_jobs j ON j.id=a.job_id WHERE r.analysis_kind<>'IMPROVEMENT_ANALYSIS' OR a.job_id<>m.job_id OR j.actor_id<>r.actor_id)
 THEN RAISE EXCEPTION 'IMPROVEMENT_RUN_MISMATCH' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT 1 FROM analysis_improvement_contexts c WHERE (c.diagnostics->>'candidate_count')::integer IS DISTINCT FROM (SELECT count(*)::integer FROM analysis_candidates a WHERE a.run_id=c.run_id) OR (c.status='FAILED' AND EXISTS(SELECT 1 FROM analysis_candidates a WHERE a.run_id=c.run_id)))
 THEN RAISE EXCEPTION 'IMPROVEMENT_CANDIDATE_COUNT_MISMATCH' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT 1 FROM improvement_analysis_inspections s JOIN analysis_improvement_contexts c ON c.run_id=s.run_id JOIN improvement_analysis_inputs x ON x.id=s.input_id LEFT JOIN company_document_parses p ON p.id=s.parse_id WHERE x.manifest_id<>c.manifest_id OR (p.id IS NOT NULL AND (p.file_id IS DISTINCT FROM x.file_id OR p.parser_version IS DISTINCT FROM s.data->>'parser_version')))
 THEN RAISE EXCEPTION 'IMPROVEMENT_INSPECTION_MISMATCH' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT 1 FROM analysis_candidates a WHERE a.analysis_kind='IMPROVEMENT_ANALYSIS' AND (SELECT count(*) FROM improvement_analysis_candidate_details d WHERE d.candidate_id=a.id)<>1)
 OR EXISTS(SELECT 1 FROM improvement_analysis_candidate_details d JOIN analysis_candidates a ON a.id=d.candidate_id WHERE a.analysis_kind<>'IMPROVEMENT_ANALYSIS' OR a.kind<>d.category OR length(a.reason)=0 OR d.data->>'rule_version' IS NULL)
 THEN RAISE EXCEPTION 'IMPROVEMENT_CANDIDATE_MISMATCH' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT 1 FROM improvement_analysis_candidate_details d JOIN analysis_candidates a ON a.id=d.candidate_id JOIN analysis_improvement_contexts c ON c.run_id=a.run_id JOIN improvement_analysis_manifests m ON m.id=c.manifest_id, jsonb_array_elements(d.data->'evidence') ev WHERE
 CASE WHEN ev->>'kind'='IMPROVEMENT' THEN NOT EXISTS(SELECT 1 FROM company_improvement_versions v WHERE v.id=m.version_id AND ev->>'version_id'=v.id AND ev->>'field' IN ('original_text','as_is','problem','impact','goal','to_be','required_functions','constraints','missing') AND length(ev->>'quote')>0 AND strpos(v.data->>(ev->>'field'),ev->>'quote')>0)
 WHEN ev->>'kind'='DOCUMENT' THEN NOT EXISTS(SELECT 1 FROM improvement_analysis_inspections s JOIN improvement_analysis_inputs x ON x.id=s.input_id JOIN company_evidence e ON e.id=ev->>'evidence_id' WHERE s.run_id=a.run_id AND s.id=ev->>'inspection_id' AND e.parse_id=s.parse_id AND e.file_id=x.file_id AND e.company_id=m.company_id AND length(ev->>'quote')>0 AND strpos(e.text,ev->>'quote')>0)
 WHEN ev->>'kind'='COMPANY_INPUT' THEN NOT EXISTS(SELECT 1 FROM company_input_versions p WHERE p.id=m.input_version_id AND ev->>'version_id'=p.id AND ev->>'field'='overview' AND length(ev->>'quote')>0 AND strpos(p.data->>'overview',ev->>'quote')>0)
 WHEN ev->>'kind'='SITE' THEN NOT EXISTS(SELECT 1 FROM company_site_versions s WHERE s.id=m.site_version_id AND ev->>'version_id'=s.id AND ev->>'field'='process' AND length(ev->>'quote')>0 AND strpos(s.data->>'process',ev->>'quote')>0)
 WHEN ev->>'kind'='FACT' THEN NOT EXISTS(SELECT 1 FROM improvement_analysis_inputs x JOIN company_fact_versions v ON v.id=x.fact_version_id WHERE x.manifest_id=m.id AND v.id=ev->>'version_id' AND x.fact_review_id=ev->>'review_id' AND x.data->>'evidence_id'=ev->>'evidence_id' AND length(ev->>'quote')>0 AND strpos(v.value,ev->>'quote')>0)
 WHEN ev->>'kind'='EVIDENCE' THEN NOT EXISTS(SELECT 1 FROM improvement_analysis_inputs x JOIN company_evidence e ON e.id=x.evidence_id WHERE x.manifest_id=m.id AND e.id=ev->>'evidence_id' AND e.company_id=m.company_id AND length(ev->>'quote')>0 AND strpos(e.text,ev->>'quote')>0)
 ELSE TRUE END)
 OR EXISTS(SELECT 1 FROM improvement_analysis_candidate_details d WHERE d.category IN ('STRUCTURE','CONFLICT') AND jsonb_array_length(d.data->'evidence') < CASE WHEN d.category='CONFLICT' THEN 2 ELSE 1 END)
 THEN RAISE EXCEPTION 'IMPROVEMENT_EVIDENCE_MISMATCH' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT 1 FROM improvement_analysis_candidate_details d JOIN analysis_candidates a ON a.id=d.candidate_id WHERE d.category='STRUCTURE' AND NOT EXISTS(SELECT 1 FROM jsonb_array_elements(d.data->'evidence') ev WHERE strpos(ev->>'quote',a.content)>0))
 OR EXISTS(SELECT 1 FROM improvement_analysis_candidate_details d JOIN analysis_candidates a ON a.id=d.candidate_id, jsonb_array_elements_text(d.data->'inspection_ids') sid WHERE NOT EXISTS(SELECT 1 FROM improvement_analysis_inspections s WHERE s.id=sid AND s.run_id=a.run_id))
 THEN RAISE EXCEPTION 'IMPROVEMENT_EVIDENCE_MISMATCH' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT 1 FROM improvement_analysis_reviews d JOIN analysis_reviews r ON r.id=d.review_id JOIN analysis_candidates a ON a.id=d.candidate_id WHERE r.candidate_id<>a.id OR r.analysis_kind<>'IMPROVEMENT_ANALYSIS' OR r.actor_id<>d.actor_id OR length(r.note)=0)
 OR EXISTS(SELECT 1 FROM analysis_domain_review_contexts x JOIN analysis_reviews r ON r.id=x.review_id LEFT JOIN improvement_analysis_reviews d ON d.id=x.improvement_review_id WHERE x.improvement_review_id IS NOT NULL AND (r.analysis_kind<>'IMPROVEMENT_ANALYSIS' OR d.review_id<>r.id))
 THEN RAISE EXCEPTION 'IMPROVEMENT_REVIEW_MISMATCH' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT 1 FROM improvement_request_drafts d JOIN analysis_improvement_contexts c ON c.run_id=d.run_id JOIN improvement_analysis_manifests m ON m.id=c.manifest_id WHERE d.company_id<>m.company_id OR d.version_id<>m.version_id)
 OR EXISTS(SELECT 1 FROM improvement_request_drafts d WHERE NOT EXISTS(SELECT 1 FROM improvement_request_draft_versions v WHERE v.draft_id=d.id))
 OR EXISTS(SELECT 1 FROM improvement_request_draft_versions v JOIN improvement_request_deliveries z ON z.draft_id=v.draft_id JOIN improvement_request_draft_versions sent ON sent.id=z.draft_version_id WHERE v.ordinal>sent.ordinal)
 OR EXISTS(SELECT 1 FROM improvement_request_draft_versions v JOIN improvement_request_drafts d ON d.id=v.draft_id WHERE v.actor_id<>d.actor_id OR length(v.title)=0 OR length(v.message)=0)
 OR EXISTS(SELECT 1 FROM improvement_request_draft_selections s JOIN improvement_request_draft_versions v ON v.id=s.draft_version_id JOIN improvement_request_drafts d ON d.id=v.draft_id JOIN improvement_analysis_reviews r ON r.id=s.analysis_review_id JOIN analysis_candidates a ON a.id=r.candidate_id WHERE a.run_id<>d.run_id OR r.decision<>'USE_FOR_REQUEST')
 OR EXISTS(SELECT 1 FROM improvement_request_deliveries z JOIN improvement_request_drafts d ON d.id=z.draft_id JOIN improvement_request_draft_versions v ON v.id=z.draft_version_id JOIN company_information_requests r ON r.id=z.request_id WHERE v.draft_id<>d.id OR z.actor_id<>d.actor_id OR r.company_id<>d.company_id OR r.improvement_version_id IS DISTINCT FROM d.version_id OR r.title<>v.title OR r.message<>v.message OR r.due_date IS DISTINCT FROM v.due_date OR r.state='DRAFT')
 THEN RAISE EXCEPTION 'IMPROVEMENT_DRAFT_MISMATCH' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END
"""
