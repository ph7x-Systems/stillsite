"""Portable round-trip (M6): read the JSON/Markdown dump back into models.

`export.export_content_json` + `export.export_markdown_files` write the
portable source of truth; this module is the exact inverse. The proof is
the round-trip test: dump → import → dump produces identical bytes.
"""

import json
from datetime import datetime
from typing import Any

from cms_core.languages import SOURCE_LANGUAGE, Language
from cms_core.media import MediaAsset
from cms_core.menus import MenuItem
from cms_core.models import Article, ArticleContent
from cms_core.pages import Page, PageContent, Section, SectionContent
from cms_core.translatable import Seo, Translation


def _moment(value: Any) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _body_from_markdown(rendered: str, title: str, summary: str) -> str:
    """Strip exactly the prefix ``export._render_markdown`` wrote — the
    title and summary come from the JSON, so a body that itself starts
    with a blockquote is never eaten."""
    prefix = f"# {title}\n\n"
    if summary:
        prefix += f"> {summary}\n\n"
    return rendered.removeprefix(prefix).rstrip("\n")


def _seo_from_portable(raw: dict[str, Any]) -> Seo:
    data = raw.get("seo")
    return Seo(**data) if data else Seo()


def article_from_portable(data: dict[str, Any], bodies: dict[str, str]) -> Article:
    """``bodies`` maps language code -> Markdown body (the .md files)."""
    languages: dict[str, Any] = data["languages"]
    source_raw = languages[SOURCE_LANGUAGE.value]
    source = ArticleContent(
        title=source_raw["title"],
        summary=source_raw.get("summary", ""),
        body_markdown=_body_from_markdown(
            bodies.get(SOURCE_LANGUAGE.value, ""),
            source_raw["title"],
            source_raw.get("summary", ""),
        ),
        slug=source_raw.get("slug"),
        seo=_seo_from_portable(source_raw),
    )
    translations: dict[Language, Translation[ArticleContent]] = {}
    for code, raw in languages.items():
        if code == SOURCE_LANGUAGE.value:
            continue
        translations[Language(code)] = Translation[ArticleContent](
            content=ArticleContent(
                title=raw["title"],
                summary=raw.get("summary", ""),
                body_markdown=_body_from_markdown(
                    bodies.get(code, ""), raw["title"], raw.get("summary", "")
                ),
                slug=raw.get("slug"),
                seo=_seo_from_portable(raw),
            ),
            source_checksum=raw["source_checksum"],
        )
    return Article(
        id=data["id"],
        status=data["status"],
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
        publish_at=_moment(data.get("publish_at")),
        unpublish_at=_moment(data.get("unpublish_at")),
        deleted_at=_moment(data.get("deleted_at")),
        featured=bool(data.get("featured", False)),
        author=data.get("author"),
        fields=dict(data.get("fields", {})),
        category=data.get("category"),
        tags=tuple(data.get("tags", [])),
        cover=data.get("cover"),
        source=source,
        translations=translations,
    )


def section_from_portable(data: dict[str, Any]) -> Section:
    languages: dict[str, Any] = data["languages"]
    source_raw = languages[SOURCE_LANGUAGE.value]
    translations: dict[Language, Translation[SectionContent]] = {}
    for code, raw in languages.items():
        if code == SOURCE_LANGUAGE.value:
            continue
        translations[Language(code)] = Translation[SectionContent](
            content=SectionContent(
                fields=dict(raw["fields"]),
                media=list(raw.get("media", [])),
                items=[dict(item) for item in raw.get("items", [])],
            ),
            source_checksum=raw["source_checksum"],
        )
    return Section(
        key=data["key"],
        kind=data["kind"],
        hidden=bool(data.get("hidden", False)),
        source=SectionContent(
            fields=dict(source_raw["fields"]),
            media=list(source_raw.get("media", [])),
            items=[dict(item) for item in source_raw.get("items", [])],
        ),
        translations=translations,
    )


def page_from_portable(data: dict[str, Any]) -> Page:
    languages: dict[str, Any] = data["languages"]
    source_raw = languages[SOURCE_LANGUAGE.value]
    translations: dict[Language, Translation[PageContent]] = {}
    for code, raw in languages.items():
        if code == SOURCE_LANGUAGE.value:
            continue
        translations[Language(code)] = Translation[PageContent](
            content=PageContent(
                title=raw["title"],
                description=raw.get("description", ""),
                slug=raw["slug"],
                body_markdown=raw.get("body_markdown", ""),
                seo=_seo_from_portable(raw),
            ),
            source_checksum=raw["source_checksum"],
        )
    return Page(
        id=data["id"],
        status=data["status"],
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
        publish_at=_moment(data.get("publish_at")),
        unpublish_at=_moment(data.get("unpublish_at")),
        deleted_at=_moment(data.get("deleted_at")),
        source=PageContent(
            title=source_raw["title"],
            description=source_raw.get("description", ""),
            slug=source_raw["slug"],
            body_markdown=source_raw.get("body_markdown", ""),
            seo=_seo_from_portable(source_raw),
        ),
        translations=translations,
        sections=[section_from_portable(raw) for raw in data.get("sections", [])],
    )


def media_from_portable(data: dict[str, Any]) -> MediaAsset:
    return MediaAsset(
        id=data["id"],
        path=data["path"],
        mime_type=data["mime_type"],
        width=data.get("width"),
        height=data.get("height"),
        alt={Language(code): text for code, text in data.get("alt", {}).items()},
        collection=str(data.get("collection", "")),
        content_hash=str(data.get("content_hash", "")),
        crop=str(data.get("crop", "")),
        focal=str(data.get("focal", "")),
    )


def menu_from_portable(data: dict[str, Any]) -> MenuItem:
    return MenuItem(
        id=data["id"],
        url=data["url"],
        position=int(data.get("position", 0)),
        labels={Language(code): label for code, label in data.get("labels", {}).items()},
    )


def import_content_json(
    payload: str, markdown_files: dict[str, str]
) -> tuple[list[Article], list[Page], list[MediaAsset], list[MenuItem]]:
    """The inverse of ``export_content_json`` + ``export_markdown_files``."""
    data = json.loads(payload)
    articles = []
    for raw in data.get("articles", []):
        prefix = f"{raw['id']}/"
        bodies = {
            path.removeprefix(prefix).removesuffix(".md"): body
            for path, body in markdown_files.items()
            if path.startswith(prefix)
        }
        articles.append(article_from_portable(raw, bodies))
    pages = [page_from_portable(raw) for raw in data.get("pages", [])]
    media = [media_from_portable(raw) for raw in data.get("media", [])]
    menu = [menu_from_portable(raw) for raw in data.get("menu", [])]
    return articles, pages, media, menu
