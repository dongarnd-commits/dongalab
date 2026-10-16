"""Read-only Proposal entry guard. No draft, approval or document is created."""

def proposal_blockers(detail,service=None,actor=None):
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
    complete=False
    if service is not None and latest and latest['outcome']=='PROPOSABLE':
        from app.proposal.policy import verified_completion
        complete=verified_completion(service,actor,detail,latest)
    if candidate['fit']=='MISMATCH' or (not complete and (candidate['fit']=='NEED_MORE_INFO' or candidate['data']['missing'])):

        blockers.append('MISSING_REQUIRED_INFORMATION')
    return blockers


def preparation(application, actor, candidate_id):
    from app.infrastructure import capability_schema as S
    # Existing trusted Provider/role/Company/file/currentness checks run first.
    detail = application.match(actor, candidate_id)
    snapshot = detail['snapshot']
    cv = application.get(S.composition_versions, snapshot['composition_version_id'])
    blockers = proposal_blockers(detail,application,actor)
    evidence=[]; company_confirmed=False
    if getattr(application.inputs,'proposal_basis',None) is not None:
        from app.proposal.policy import basis
        context=snapshot['input']['company']; b=basis(application,actor,context['company_id'],context['improvement_version_id'])
        company_confirmed=b.company_confirmed and b.current_valid
        evidence=[dict(id=p.id,version_id=p.version_id,confirmed=p.confirmed,current_valid=p.current_valid) for p in b.proofs]
    return {
        'candidate_id': candidate_id,
        'source_summary': {'company_input': snapshot['input']['company'], 'service_composition':snapshot['input']['composition'],'notice':snapshot['input']['notice'],'comparisons':detail['candidate']['data']['dimensions']['eligibility'].get('comparisons',[])},
        'can_create': not blockers,
        'policy_blockers': blockers,
        'implementation_blockers': [],
        'review_evidence': evidence,
        'company_confirmed': company_confirmed,
        'review_tasks': __import__('app.proposal.policy',fromlist=['tasks']).tasks(detail),
        'source_refs': {
            'match_input_snapshot_id': snapshot['id'],
            'composition_version_id': cv['id'],
            'improvement_version_id': cv['improvement_version_id'],
            'notice_version_id': snapshot['input']['notice']['notice_version_id'],
            'requirement_version_id': snapshot['requirement_version_id'],
            'review_ids': [r['id'] for r in detail['reviews']],
        },
    }
