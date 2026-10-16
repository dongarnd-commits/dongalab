"""DB guards mirrored as frozen SQL by the Proposal migration."""
IMMUTABLE=('proposal_versions','proposal_content_reviews','proposal_approval_decisions','proposal_document_files','match_review_completions')
LINK_BODY=r"""
DECLARE good boolean;
BEGIN
 IF TG_TABLE_NAME='proposal_versions' THEN
  SELECT p.company_id=s.input->'company'->>'company_id' AND r.candidate_id=c.id AND c.snapshot_id=s.id AND r.outcome='PROPOSABLE' AND EXISTS(SELECT 1 FROM match_review_completions x WHERE x.review_id=r.id) AND NEW.manifest->'refs'->>'match_review_id'=r.id AND NEW.manifest->'refs'->>'match_snapshot_id'=s.id INTO good
  FROM proposals p,capability_match_snapshots s,capability_match_reviews r,capability_match_candidates c
  WHERE p.id=NEW.proposal_id AND s.id=NEW.match_snapshot_id AND r.id=NEW.match_review_id AND c.id=r.candidate_id;
 ELSIF TG_TABLE_NAME='proposal_document_files' THEN
  SELECT version_id=NEW.version_id AND confirmed INTO good FROM proposal_content_reviews WHERE id=NEW.content_review_id;
 ELSIF TG_TABLE_NAME='match_review_completions' THEN
  SELECT outcome='PROPOSABLE' INTO good FROM capability_match_reviews WHERE id=NEW.review_id;
 ELSE RETURN NEW;
 END IF;
 IF good IS DISTINCT FROM true THEN RAISE EXCEPTION 'PROPOSAL_LINK_MISMATCH' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END
"""
REQUEST_BODY=r"""
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'IMMUTABLE_APPROVAL_HISTORY' USING ERRCODE='23514'; END IF;
 IF (NEW.id,NEW.created_at,NEW.version_id,NEW.intended_approver,NEW.requested_by) IS DISTINCT FROM (OLD.id,OLD.created_at,OLD.version_id,OLD.intended_approver,OLD.requested_by)
 OR OLD.state<>'OPEN' OR NEW.state<>'CLOSED' THEN RAISE EXCEPTION 'IMMUTABLE_APPROVAL_HISTORY' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END
"""
def install(connection,schema='public'):
 q=connection.dialect.identifier_preparer.quote;ns=q(schema)
 connection.exec_driver_sql('CREATE FUNCTION '+ns+".immutable_proposal_record() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'IMMUTABLE_PROPOSAL_RECORD' USING ERRCODE='23514'; END $$")
 for name in IMMUTABLE:connection.exec_driver_sql('CREATE TRIGGER immutable_proposal_record BEFORE UPDATE OR DELETE ON '+ns+'.'+q(name)+' FOR EACH ROW EXECUTE FUNCTION '+ns+'.immutable_proposal_record()')
 connection.exec_driver_sql('CREATE FUNCTION '+ns+'.validate_proposal_links() RETURNS trigger LANGUAGE plpgsql SET search_path='+ns+',pg_catalog AS $$'+LINK_BODY+'$$')
 for name in ('proposal_versions','proposal_document_files','match_review_completions'):connection.exec_driver_sql('CREATE TRIGGER validate_proposal_links BEFORE INSERT ON '+ns+'.'+q(name)+' FOR EACH ROW EXECUTE FUNCTION '+ns+'.validate_proposal_links()')
 connection.exec_driver_sql('CREATE FUNCTION '+ns+'.guard_proposal_request() RETURNS trigger LANGUAGE plpgsql AS $$'+REQUEST_BODY+'$$')
 connection.exec_driver_sql('CREATE TRIGGER guard_proposal_request BEFORE UPDATE OR DELETE ON '+ns+'.proposal_approval_requests FOR EACH ROW EXECUTE FUNCTION '+ns+'.guard_proposal_request()')
