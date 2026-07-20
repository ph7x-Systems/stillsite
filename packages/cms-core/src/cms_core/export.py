"""Deterministic portable export: a JSON index plus per-language Markdown files.

Same input always produces byte-identical output — articles are sorted by id,
JSON keys are sorted, and no timestamps are generated at export time.
"""

import json
from collections.abc import Iterable

from cms_core.languages import SOURCE_LANGUAGE, Language
from cms_core.media import MediaAsset
from cms_core.menus import MenuItem
from cms_core.models import SCHEMA_VERSION, Article, ArticleContent
from cms_core.pages import Page, Section


def article_to_portable(article: Article) -> dict[str, object]:
    languages: dict[str, dict[str, str | None]] = {
        SOURCE_LANGUAGE.value: {
            "state": "complete",
            "title": article.source.title,
            "summary": article.source.summary,
            "slug": article.source.slug,
        }
    }
    for language, translation in sorted(
        article.translations.items(), key=lambda item: item[0].value
    ):
        languages[language.value] = {
            "state": article.translation_state(language).value,
            "title": translation.content.title,
            "summary": translation.content.summary,
            "slug": translation.content.slug,
            "source_checksum": translation.source_checksum,
        }
    return {
        "id": article.id,
        "status": article.status.value,
        "created_at": article.created_at.isoformat(),
        "updated_at": article.updated_at.isoformat(),
        "publish_at": article.publish_at.isoformat() if article.publish_at else None,
        "featured": article.featured,
        "author": article.author,
        "fields": dict(sorted(article.fields.items())),
        "category": article.category,
        "tags": list(article.tags),
        "cover": article.cover,
        "deleted_at": article.deleted_at.isoformat() if article.deleted_at else None,
        "languages": languages,
    }


def section_to_portable(section: Section) -> dict[str, object]:
    languages: dict[str, dict[str, object]] = {
        SOURCE_LANGUAGE.value: {
            "state": "complete",
            "fields": dict(sorted(section.source.fields.items())),
            "media": list(section.source.media),
        }
    }
    for language, translation in sorted(
        section.translations.items(), key=lambda item: item[0].value
    ):
        languages[language.value] = {
            "state": section.translation_state(language).value,
            "fields": dict(sorted(translation.content.fields.items())),
            "media": list(translation.content.media),
            "source_checksum": translation.source_checksum,
        }
    return {"key": section.key, "kind": section.kind, "languages": languages}


def page_to_portable(page: Page) -> dict[str, object]:
    languages: dict[str, dict[str, str]] = {
        SOURCE_LANGUAGE.value: {
            "state": "complete",
            "title": page.source.title,
            "description": page.source.description,
            "slug": page.source.slug,
        }
    }
    for language, translation in sorted(page.translations.items(), key=lambda item: item[0].value):
        languages[language.value] = {
            "state": page.translation_state(language).value,
            "title": translation.content.title,
            "description": translation.content.description,
            "slug": translation.content.slug,
            "source_checksum": translation.source_checksum,
        }
    return {
        "id": page.id,
        "status": page.status.value,
        "created_at": page.created_at.isoformat(),
        "updated_at": page.updated_at.isoformat(),
        "publish_at": page.publish_at.isoformat() if page.publish_at else None,
        "deleted_at": page.deleted_at.isoformat() if page.deleted_at else None,
        "languages": languages,
        "sections": [section_to_portable(section) for section in page.sections],
    }


def media_to_portable(asset: MediaAsset) -> dict[str, object]:
    return {
        "id": asset.id,
        "path": asset.path,
        "mime_type": asset.mime_type,
        "width": asset.width,
        "height": asset.height,
        "alt": {
            language.value: text
            for language, text in sorted(asset.alt.items(), key=lambda item: item[0].value)
        },
    }


def menu_to_portable(item: MenuItem) -> dict[str, object]:
    return {
        "id": item.id,
        "url": item.url,
        "position": item.position,
        "labels": {
            language.value: label
            for language, label in sorted(item.labels.items(), key=lambda kv: kv[0].value)
        },
    }


def export_content_json(
    articles: Iterable[Article],
    pages: Iterable[Page] = (),
    media: Iterable[MediaAsset] = (),
    menu: Iterable[MenuItem] = (),
) -> str:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "articles": [
            article_to_portable(article)
            for article in sorted(articles, key=lambda article: article.id)
        ],
        "pages": [page_to_portable(page) for page in sorted(pages, key=lambda page: page.id)],
        "media": [media_to_portable(asset) for asset in sorted(media, key=lambda asset: asset.id)],
        "menu": [
            menu_to_portable(item)
            for item in sorted(menu, key=lambda item: (item.position, item.id))
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
