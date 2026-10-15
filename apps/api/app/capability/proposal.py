"""Read-only Proposal entry guard. No draft, approval or document is created."""

def proposal_blockers(detail):
    blockers = []
    if not detail['current_valid']:
        blockers.append('STALE_INPUT_VERSION')
    if detail['lineage']['legacy']:
        blockers.append('LEGACY_ANALYSIS_REQUIRES_REANALYSIS')
    reviews = detail['reviews']
    latest = max(reviews, key=lambda r: (r['created_at'], r['id'])) if reviews else None
    if latest is None or latest['outcome'] != 'PROPOSABLE':
        blockers.append('MATCH_NOT_PROPOSABLE')
    candidate = detail['candidate']
    if candidate['fit'] in ('NEED_MORE_INFO', 'MISMATCH') or candidate['data']['missing']:
        blockers.append('MISSING_REQUIRED_INFORMATION')
    return blockers


def preparation(application, actor, candidate_id):
    from app.infrastructure import capability_schema as S
    # Existing trusted Provider/role/Company/file/currentness checks run first.
    detail = application.match(actor, candidate_id)
    snapshot = detail['snapshot']
    cv = application.get(S.composition_versions, snapshot['composition_version_id'])
    blockers = proposal_blockers(detail)
    return {
        'candidate_id': candidate_id,
        'can_create': False,
        'policy_blockers': blockers,
        'implementation_blockers': ['PROPOSAL_PERSISTENCE_CONTRACT_PENDING', 'PROPOSAL_OUTPUT_FORMAT_PENDING'],
        'source_refs': {
            'match_input_snapshot_id': snapshot['id'],
            'composition_version_id': cv['id'],
            'improvement_version_id': cv['improvement_version_id'],
            'notice_version_id': snapshot['input']['notice']['notice_version_id'],
            'requirement_version_id': snapshot['requirement_version_id'],
            'review_ids': [r['id'] for r in detail['reviews']],
        },
    }
