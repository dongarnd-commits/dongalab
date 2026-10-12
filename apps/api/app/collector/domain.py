from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class NormalizedNotice:
    external_id: str
    title: str | None
    core: dict
    metadata: dict
    references: list[dict]
    warnings: list[str]

class CollectionInput(Protocol):
    origin: str
    def page(self, page: int, unit: int) -> dict: ...
    def acquire(self, reference: dict, external_id: str) -> tuple[bytes, str]: ...
