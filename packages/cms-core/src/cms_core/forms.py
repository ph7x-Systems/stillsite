"""Form submissions (ADR-0039): optionally stored, never load-bearing.

Storage is a consumer of an accepted submission — the endpoint
validates, accepts and answers whether or not persistence is
configured, and a storage failure never reaches the visitor. The
operational fields (when, which form, which language) are queryable;
the visitor's values are an opaque payload — the schema never depends
on user-defined field keys.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class FormSubmission:
    id: str
    received_at: datetime
    page_id: str
    section_key: str
    language: str
    values: dict[str, str] = field(default_factory=dict)
