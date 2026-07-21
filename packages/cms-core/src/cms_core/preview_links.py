"""External preview links (ADR-0042): recorded, expiring, revocable.

The record is the revocation authority; the token itself is signed and
never stored — a database leak reveals no usable links.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class PreviewLink:
    id: str
    entry_kind: str
    """``article`` | ``page``."""
    entry_id: str
    created_at: datetime
    expires_at: datetime
    revoked: bool = False
