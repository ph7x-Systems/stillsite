"""Automatic redirects when a published entry's address changes.

Renaming a slug on published content breaks every existing link; the
panel records the old address in the project's redirect map instead
(the builder emits fallback pages and target configs from it). Chains
flatten (anything pointing at the old address points at the new one),
self-redirects never survive, and an address that becomes live again
drops its stale redirect — the live page wins.
"""

import logging

from cms_build import urls
from cms_build.redirects import merge_redirects, write_redirects
from cms_core import Article, ContentStatus, Page
from fastapi import Request

from cms_admin.publishing import _project

logger = logging.getLogger("cms_admin.redirects")


def _entry_paths(project: object, entry: Article | Page) -> dict[str, str]:
    config = project.site  # type: ignore[attr-defined]
    paths: dict[str, str] = {}
    languages = [config.source_language, *config.languages]
    for language in languages:
        if isinstance(entry, Article):
            if language != config.source_language and language not in entry.translations:
                continue
            paths[language.value] = urls.article_path(config, entry, language)
        else:
            if language != config.source_language and language not in entry.translations:
                continue
            paths[language.value] = urls.page_path(entry, language, source=config.source_language)
    return paths


async def record_slug_redirects(
    request: Request, before: Article | Page, after: Article | Page
) -> None:
    """Compare a published entry's addresses before and after a save and
    persist any change as a redirect. Never blocks the save."""
    try:
        if before.status is not ContentStatus.PUBLISHED:
            return
        project = _project(request)
        if project is None:
            return
        old_paths = _entry_paths(project, before)
        new_paths = _entry_paths(project, after)
        changes = {
            old: new_paths[code]
            for code, old in old_paths.items()
            if code in new_paths and (new := new_paths[code]) != old
        }
        if not changes:
            return
        merged = merge_redirects(dict(project.site.redirects), changes)
        write_redirects(project.directory / "sardine.toml", merged)
        from cms_admin.audit import record as audit_record

        for old, new in sorted(changes.items()):
            await audit_record(request, "system", "redirected", "url", old, new)
    except Exception:  # pragma: no cover - never break the editorial save
        logger.exception("recording slug redirects failed")
