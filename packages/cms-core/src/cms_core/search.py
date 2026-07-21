"""Admin content search (#129): one query, every editable thing.

The hit is deliberately tiny — kind, identifier, a human title and a
matched-in detail — because the admin's grouped results page is the
consumer, not an API. Trashed entries never match: the search finds
what the lists show.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SearchHit:
    kind: str
    """``article`` | ``page`` | ``section`` | ``media``."""
    id: str
    """The entry id; for sections, ``page_id/key``."""
    title: str
    """What the results list shows."""
    detail: str = ""
    """Where it matched (a field name, a language, a path)."""


LIKE_ESCAPE = "!"
"""The LIKE escape character every engine accepts literally (a backslash
would itself need escaping on MySQL)."""


def like_pattern(needle: str) -> str:
    """A contains-match LIKE pattern with user input made literal;
    pair with ``ESCAPE '!'``."""
    escaped = needle.replace("!", "!!").replace("%", "!%").replace("_", "!_")
    return f"%{escaped.lower()}%"
