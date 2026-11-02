"""Small, explicitly whitelisted administrator projections, without mutations."""
from datetime import datetime, timezone
from sqlalchemy import select, func
from app.notice.domain import Denied
from app.infrastructure import company_schema as C, capability_schema as B, notice_schema as N
from app.company.improvement_providers import provider_status


class AdminProjection:
    def __init__(self, session):
        self.session = session

    @staticmethod
    def authorize(actor):
        if actor.role != 'DATCO_ADMIN':
            raise Denied('ACTION_NOT_AUTHORIZED', 403)

    def count(self, table):
        return self.session.scalar(select(func.count()).select_from(table))

    def overview(self, actor):
        self.authorize(actor)
        return dict(as_of=datetime.now(timezone.utc), source='POSTGRESQL_OPERATIONAL_PROJECTION',
                    accounts=self.count(N.actors), companies=self.count(C.companies),
                    features=self.count(B.features),
                    published_capabilities=self.session.scalar(select(func.count()).select_from(B.capabilities).where(B.capabilities.c.current_ordinal > 0)),
                    notices=self.count(N.notices),
                    collection_jobs=self.session.scalar(select(func.count()).select_from(N.jobs).where(N.jobs.c.kind == 'BIZINFO_COLLECTION')),
                    limitations=['집계는 업무 확정·품질 평가·서버 가동 상태를 의미하지 않습니다.',
                                 '관리자에게 기업 업무 검토·승인 권한을 부여하지 않습니다.'])

    def access(self, actor):
        self.authorize(actor)
        # Select a whitelist at SQL level: passwords, session tokens and hashes are never loaded.
        users = [dict(r) for r in self.session.execute(select(N.actors.c.id, N.actors.c.username, N.actors.c.role, N.actors.c.created_at).order_by(N.actors.c.username)).mappings()]
        companies = [dict(r) for r in self.session.execute(select(C.companies.c.id, C.companies.c.name).order_by(C.companies.c.name, C.companies.c.id)).mappings()]
        memberships = [dict(r) for r in self.session.execute(select(C.memberships.c.id, C.memberships.c.actor_id, C.memberships.c.company_id, C.memberships.c.granted_by, C.memberships.c.created_at).order_by(C.memberships.c.created_at, C.memberships.c.id)).mappings()]
        return dict(users=users, companies=companies, memberships=memberships,
                    allowed_actions=['GRANT_COMPANY_ACCESS'],
                    limitations=['계정 상태·최근 활동은 수집하지 않습니다.', '신규 계정·역할 변경·접근권한 삭제는 이 화면의 범위가 아닙니다.'])

    def connections(self, actor, configured):
        self.authorize(actor)
        rows = self.session.execute(select(N.jobs.c.id, N.jobs.c.created_at, N.jobs.c.state, N.jobs.c.error, N.jobs.c.payload).where(N.jobs.c.kind == 'BIZINFO_COLLECTION').order_by(N.jobs.c.created_at.desc(), N.jobs.c.id.desc()).limit(10)).mappings()
        jobs = [dict(id=r['id'], created_at=r['created_at'], state=r['state'], mode=r['payload'].get('mode'),
                     error=r['error'] if r['error'] and all(c.isupper() or c.isdigit() or c in '_:' for c in r['error']) else None) for r in rows]
        return dict(as_of=datetime.now(timezone.utc), analysis=provider_status(),
                    bizinfo=dict(status='CONFIGURED' if configured else 'NOT_CONFIGURED', jobs=jobs,
                                 validation='NOT_PROBED', note='설정 유무와 저장된 수집 기록만 조회합니다. 현재 연결 성공을 보장하지 않습니다.'),
                    worker=dict(status='UNMEASURED', note='가동 여부를 추정하지 않습니다. 저장된 Job 상태로 실행 결과를 확인하세요.'))
