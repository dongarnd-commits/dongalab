from dataclasses import dataclass
from typing import Protocol

class Denied(Exception):
    def __init__(self, reason: str, status: int = 409):
        self.reason, self.status = reason, status

@dataclass(frozen=True)
class Actor:
    id: str
    role: str

def authorize(actor: Actor):
    if actor.role != "DATCO_OPERATOR":
        raise Denied("ACTION_NOT_AUTHORIZED", 403)

@dataclass(frozen=True)
class Span:
    source_id: str
    descriptor: str
    text: str
    page: int | None = None

@dataclass(frozen=True)
class CandidateOutput:
    kind: str
    content: str
    reason: str
    span: Span

class AnalysisProvider(Protocol):
    version: str
    def analyze(self, spans: list[Span]) -> list[CandidateOutput]: ...

class FileProvider(Protocol):
    def put(self, content: bytes) -> tuple[str, str]: ...
    def read(self, storage_key: str, digest: str) -> bytes: ...
    def verify_location(self, source: dict, location: dict) -> None: ...

class NoticeStore(Protocol):
    def lock_identity(self, key: str) -> None: ...
    def get(self, table, identity: str, lock: bool = False) -> dict: ...
    def rows(self, table, **filters) -> list[dict]: ...
    def add(self, table, **values) -> dict: ...
    def change(self, table, identity: str, **values): ...
