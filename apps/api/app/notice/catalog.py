"""Search the saved latest NoticeVersion, never a new collection or eligibility decision."""
from datetime import date
from sqlalchemy import select, func, or_
from app.infrastructure import notice_schema as N
from app.notice.domain import authorize


def saved_catalog(session, actor, query='', mode='', agency='', page=1, limit=20):
    authorize(actor)
    metadata = N.versions.c.metadata
    joined = N.notices.join(N.versions, (N.versions.c.notice_id == N.notices.c.id) & (N.versions.c.ordinal == N.notices.c.current_ordinal))
    conditions = []
    # Escape LIKE metacharacters: a user search remains literal, never a pattern contract.
    def literal(value):
        return '%' + value.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
    if query.strip():
        needle = literal(query.strip())
        conditions.append(or_(N.notices.c.title.ilike(needle, escape='\\'), metadata['target'].astext.ilike(needle, escape='\\'), metadata['summary'].astext.ilike(needle, escape='\\')))
    if mode:
        conditions.append(N.versions.c.mode == mode)
    if agency.strip():
        conditions.append(metadata['agency'].astext.ilike(literal(agency.strip()), escape='\\'))
    total = session.scalar(select(func.count()).select_from(joined).where(*conditions))
    stmt = select(N.notices.c.id, N.notices.c.title, N.versions.c.id.label('version_id'), N.versions.c.ordinal, N.versions.c.mode, N.versions.c.created_at, metadata).select_from(joined).where(*conditions).order_by(N.versions.c.created_at.desc(), N.notices.c.id).offset((page - 1) * limit).limit(limit)
    rows = list(session.execute(stmt).mappings())
    version_ids = [r['version_id'] for r in rows]
    confirmed = {}
    if version_ids:
        for r in session.execute(select(N.requirement_versions.c.id, N.requirement_versions.c.notice_version_id, N.requirement_versions.c.ordinal).where(N.requirement_versions.c.notice_version_id.in_(version_ids)).order_by(N.requirement_versions.c.ordinal)).mappings():
            confirmed[r['notice_version_id']] = r['id']
    items = []
    for r in rows:
        m = r['metadata']
        period = m.get('period_candidates')
        state = 'UNCONFIRMED'
        if isinstance(period, list) and len(period) == 2:
            try:
                start, end = (date.fromisoformat(value) for value in period)
                today = date.today()
                state = 'CLOSED' if end < today else 'UPCOMING' if start > today else 'WITHIN_RECORDED_PERIOD'
            except (ValueError, TypeError):
                pass
        items.append(dict(id=r['id'], title=r['title'], version_id=r['version_id'], ordinal=r['ordinal'],
                          mode=r['mode'], agency=m.get('agency', ''), target=m.get('target', ''),
                          summary=m.get('summary', ''), period_original=m.get('period_original', ''),
                          period_state=state, collected_at=m.get('collected_at'),
                          source_updated_original=m.get('source_updated_original'),
                          requirement_version_id=confirmed.get(r['version_id']),
                          requirement_state='REVIEWED_SCOPE' if r['version_id'] in confirmed else 'REVIEW_REQUIRED'))
    return dict(items=items, total=total, page=page, limit=limit,
                source='SAVED_NOTICE_VERSIONS', limitations=['저장 자료 조회이며 실시간 수집 결과가 아닙니다.', '기간은 저장된 원문 기준 후보입니다. 실제 모집 여부·기업 자격과 요건 전체 확정은 별도 검토가 필요합니다.'])
