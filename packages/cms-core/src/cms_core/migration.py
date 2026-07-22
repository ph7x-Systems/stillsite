"""Applying a foreign import to storage: one loop, two interfaces.

The CLI and the admin panel both consume this (ADR-0047); the matching
semantics (ADR-0043) live nowhere else. Imports are idempotent by the
``wxr_post_id`` field: a match never duplicates, matched entries stay
untouched unless ``update`` opts into source-wins, and the entity id
survives an upstream slug change.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from cms_core.models import Article


@dataclass
class WxrApplyResult:
    """What one application run did — every article accounted for."""

    new: int = 0
    updated: int = 0
    matched: int = 0
    landed: list[Article] = field(default_factory=list)
    """Every entity this run touched or matched, as stored."""
    renamed: list[tuple[Article, Article]] = field(default_factory=list)
    """(prior, current) pairs for updated entities — redirect input."""


def apply_wxr_import(
    storage: object, articles: Iterable[Article], *, update: bool = False
) -> WxrApplyResult:
    """Write imported articles into storage, idempotently by source id."""
    known = {
        article.fields["wxr_post_id"]: article.id
        for article in storage.load_all_articles()  # type: ignore[attr-defined]
        if article.fields.get("wxr_post_id")
    }
    result = WxrApplyResult()
    for article in articles:
        existing_id = known.get(article.fields.get("wxr_post_id", ""))
        if existing_id is None:
            storage.save_article(article)  # type: ignore[attr-defined]
            result.landed.append(article)
            result.new += 1
        elif update:
            prior = storage.load_article(existing_id)  # type: ignore[attr-defined]
            article.id = existing_id
            storage.save_article(article)  # type: ignore[attr-defined]
            result.landed.append(article)
            if prior is not None:
                result.renamed.append((prior, article))
            result.updated += 1
        else:
            kept = storage.load_article(existing_id)  # type: ignore[attr-defined]
            if kept is not None:
                result.landed.append(kept)
            result.matched += 1
    return result
