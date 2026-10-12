from sqlalchemy import select, insert, update
from app.notice.domain import Denied
from app.infrastructure.notice_schema import identity, TABLES

class SqlNoticeStore:
    def __init__(self, session):
        self.session = session

    def get(self, entity, identity, lock=False):
        table = TABLES[entity]
        stmt = select(table).where(table.c.id == identity)
        if lock:
            stmt = stmt.with_for_update()
        row = self.session.execute(stmt).mappings().first()
        if row is None:
            raise Denied("OBJECT_NOT_FOUND", 404)
        return dict(row)

    def rows(self, entity, **filters):
        table = TABLES[entity]
        conditions = [table.c[key] == value for key,value in filters.items()]
        return [dict(r) for r in self.session.execute(
            select(table).where(*conditions).order_by(table.c.created_at,table.c.id)).mappings()]

    def add(self, entity, **values):
        table = TABLES[entity]
        values.setdefault("id", identity())
        return dict(self.session.execute(insert(table).values(**values).returning(table)).mappings().one())

    def change(self, entity, identity, **values):
        table = TABLES[entity]
        self.session.execute(update(table).where(table.c.id==identity).values(**values))
