"""The project redirect map: safe merging and config writing.

The map lives in the project's ``[redirects]`` table; the builder emits
fallback pages and target rules from it. These helpers are shared by
every writer of that table (the panel's slug-change flow, the migration
importer): chains flatten, self-redirects never survive, and an address
that becomes live again drops its stale redirect — the live page wins.
"""

from pathlib import Path
from typing import Any

from cms_build import urls
from cms_build.config import SiteConfig


def merge_redirects(existing: dict[str, str], changes: dict[str, str]) -> dict[str, str]:
    """Fold address changes into the redirect map, flattened and safe."""
    merged = dict(existing)
    for old, new in changes.items():
        for source, destination in list(merged.items()):
            if destination == old:
                merged[source] = new  # flatten: A→old, old→new becomes A→new
        merged[old] = new
    live = set(changes.values())
    return {
        source: destination
        for source, destination in merged.items()
        if source != destination and source not in live
    }


def write_redirects(project_file: Path, redirects: dict[str, str]) -> None:
    """Rewrite the ``[redirects]`` table; the rest of the file is
    left exactly as the owner wrote it."""
    text = project_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    kept: list[str] = []
    in_table = False
    for line in lines:
        stripped = line.strip()
        if stripped == "[redirects]":
            in_table = True
            continue
        if in_table and stripped.startswith("["):
            in_table = False
        if not in_table:
            kept.append(line)
    while kept and not kept[-1].strip():
        kept.pop()
    if redirects:
        kept.extend(["", "[redirects]"])
        kept.extend(
            f'"{source}" = "{destination}"' for source, destination in sorted(redirects.items())
        )
    project_file.write_text("\n".join(kept) + "\n", encoding="utf-8")


def migration_redirect_changes(
    config: SiteConfig,
    articles: list[Any],
    renamed: list[tuple[Any, Any]],
) -> dict[str, str]:
    """Address changes a migration implies (ADR-0046).

    Renames first (an upstream slug change moves the old site address),
    then source permalinks that differ from the entity's address here.
    Sorted processing keeps the result deterministic.
    """
    changes: dict[str, str] = {}
    for prior, current in sorted(renamed, key=lambda pair: pair[1].id):
        old_path = urls.article_path(config, prior, config.source_language)
        new_path = urls.article_path(config, current, config.source_language)
        if old_path != new_path:
            changes[old_path] = new_path
    for article in sorted(articles, key=lambda a: a.id):
        source_path = article.fields.get("wxr_source_path", "")
        if not source_path:
            continue
        target = urls.article_path(config, article, config.source_language)
        if source_path.rstrip("/") != target.rstrip("/"):
            changes[source_path] = target
    return changes
