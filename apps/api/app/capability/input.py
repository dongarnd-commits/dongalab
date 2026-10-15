from typing import Protocol
from app.notice.domain import Actor,Denied

class ImprovementReader(Protocol):
    """Trusted reader validates Actor/Company/Site/File scope and returns exact
    version, confirmed and current_valid flags; browser IDs are not authority.
    Historical authorized reads may return current_valid=False.
    """
    def read(self, actor: Actor, version_id: str) -> dict: ...

class UnavailableImprovement:
    def read(self, actor: Actor, version_id: str) -> dict:
        # No asserted browser Company ID, role or raw text becomes authoritative input.
        raise Denied("IMPROVEMENT_PROVIDER_NOT_CONNECTED",503)
