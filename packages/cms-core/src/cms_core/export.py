"""Deterministic portable export: a JSON index plus per-language Markdown files.

Same input always produces byte-identical output — articles are sorted by id,
JSON keys are sorted, and no timestamps are generated at export time.
"""

import json
from collections.abc import Iterable

from cms_core.languages import SOURCE_LANGUAGE, Language
from cms_core.models import SCHEMA_VERSION, Article, ArticleContent


def article_to_portable(article: Article) -> dict[str, object]:
    languages: dict[str, dict[str, str]] = {
        SOURCE_LANGUAGE.value: {
            "state": "complete",
            "title": article.source.title,
            "summary": article.source.summary,
        }
    }
    for language, translation in sorted(
        article.translations.items(), key=lambda item: item[0].value
    ):
        languages[language.value] = {
            "state": article.translation_state(language).value,
            "title": translation.content.title,
            "summary": translation.content.summary,
            "source_checksum": translation.source_checksum,
        }
    return {
        "id": article.id,
        "status": article.status.value,
        "created_at": article.created_at.isoformat(),
        "updated_at": article.updated_at.isoformat(),
        "languages": languages,
    }


def export_content_json(articles: Iterable[Article]) -> str:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "articles": [
            article_to_portable(article)
            for article in sorted(articles, key=lambda article: article.id)
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def export_markdown_files(articles: Iterable[Article]) -> dict[str, str]:
    """Map of relative file path -> Markdown content, one file per language."""
    files: dict[str, str] = {}
    for article in sorted(articles, key=lambda article: article.id):
        files[f"{article.id}/{SOURCE_LANGUAGE.value}.md"] = _render_markdown(article.source)
        for language, translation in sorted(
            article.translations.items(), key=lambda item: item[0].value
        ):
            files[f"{article.id}/{language.value}.md"] = _render_markdown(translation.content)
    return files


def _render_markdown(content: ArticleContent) -> str:
    lines = [f"# {content.title}", ""]
    if content.summary:
        lines.extend([f"> {content.summary}", ""])
    lines.append(content.body_markdown)
    return "\n".join(lines).rstrip() + "\n"


def languages_in_export(files: dict[str, str]) -> set[Language]:
    """Languages present in a Markdown export (used by parity checks)."""
    return {Language(path.rsplit("/", 1)[1].removesuffix(".md")) for path in files}
