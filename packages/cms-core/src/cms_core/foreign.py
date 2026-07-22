"""Adapters for foreign content formats.

Foreign namespaces are protocol identifiers, not network locations.  They
live only in this adapter; parsing performs no I/O and rejects DTD/entity
declarations before the standard-library XML parser sees the document.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import Any

from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException

from cms_core.models import Article, ArticleContent, new_article
from cms_core.states import ContentStatus

CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"
DC_NS = "http://purl.org/dc/elements/1.1/"
EXCERPT_NS = "http://wordpress.org/export/1.2/excerpt/"
WP_NS = "http://wordpress.org/export/1.2/"


@dataclass(frozen=True)
class WxrImport:
    """The supported part of a WXR 1.2 blog export."""

    articles: tuple[Article, ...]
    skipped: int


@dataclass(frozen=True)
class WxrNote:
    """One item the migration leaves behind, and why."""

    kind: str
    title: str
    reason: str


@dataclass(frozen=True)
class WxrReport:
    """What a WXR 1.2 export contains, computed without writing anything.

    Every channel item is either importable or listed in ``left_behind``
    with a reason — nothing is silently dropped. Comments are not channel
    items; they are counted separately and do not enter the fidelity
    percentage (ADR-0043).
    """

    posts: int
    authors: tuple[str, ...]
    categories: tuple[str, ...]
    tags: tuple[str, ...]
    media_urls: tuple[str, ...]
    comments: int
    left_behind: tuple[WxrNote, ...]

    @property
    def total_items(self) -> int:
        return self.posts + len(self.left_behind)

    @property
    def fidelity(self) -> float:
        """Percentage of channel items the migration imports."""
        if not self.total_items:
            return 100.0
        return self.posts * 100.0 / self.total_items


class _MarkdownParser(HTMLParser):
    """Conservative dependency-free HTML-to-Markdown conversion."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.links: list[str] = []
        self.in_pre = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag in {"p", "div"}:
            self.parts.append("\n\n")
        elif tag == "br":
            self.parts.append("  \n")
        elif tag in {"strong", "b"}:
            self.parts.append("**")
        elif tag in {"em", "i"}:
            self.parts.append("*")
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.parts.append(f"\n\n{'#' * int(tag[1])} ")
        elif tag == "li":
            self.parts.append("\n- ")
        elif tag == "blockquote":
            self.parts.append("\n\n> ")
        elif tag == "pre":
            self.in_pre = True
            self.parts.append("\n\n```\n")
        elif tag == "code" and not self.in_pre:
            self.parts.append("`")
        elif tag == "a":
            self.parts.append("[")
            self.links.append(values.get("href") or "")
        elif tag == "img":
            source = values.get("src") or ""
            if source:
                self.parts.append(f"![{values.get('alt') or ''}]({source})")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"strong", "b"}:
            self.parts.append("**")
        elif tag in {"em", "i"}:
            self.parts.append("*")
        elif tag in {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote"}:
            self.parts.append("\n\n")
        elif tag == "pre":
            self.in_pre = False
            self.parts.append("\n```\n\n")
        elif tag == "code" and not self.in_pre:
            self.parts.append("`")
        elif tag == "a":
            target = self.links.pop() if self.links else ""
            self.parts.append(f"]({target})" if target else "]")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def markdown(self) -> str:
        text = "".join(self.parts).replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def _markdown(value: str) -> str:
    parser = _MarkdownParser()
    parser.feed(value)
    parser.close()
    return parser.markdown()


def _slug(value: str, fallback: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
    return slug or fallback


def _date(item: Any) -> datetime:
    foreign_date = (item.findtext(f"{{{WP_NS}}}post_date_gmt") or "").strip()
    if foreign_date and foreign_date != "0000-00-00 00:00:00":
        try:
            return datetime.strptime(foreign_date, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
        except ValueError:
            pass
    published = (item.findtext("pubDate") or "").strip()
    if published:
        try:
            parsed = parsedate_to_datetime(published)
            return parsed.replace(tzinfo=parsed.tzinfo or UTC).astimezone(UTC)
        except (TypeError, ValueError):
            pass
    # Deterministic fallback: malformed/missing foreign dates must not make
    # two imports of the same file produce different portable dumps.
    return datetime(1970, 1, 1, tzinfo=UTC)


def _status(value: str) -> ContentStatus:
    return {
        "publish": ContentStatus.PUBLISHED,
        "pending": ContentStatus.REVIEW,
        "future": ContentStatus.PUBLISHED,
    }.get(value, ContentStatus.DRAFT)


def _document(payload: bytes | str) -> Any:
    raw = payload.encode() if isinstance(payload, str) else payload
    upper = raw.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise ValueError("WXR must not contain DTD or entity declarations")
    try:
        return ET.fromstring(raw)
    except DefusedXmlException as error:
        raise ValueError("WXR must not contain DTD or entity declarations") from error
    except ET.ParseError as error:
        raise ValueError(f"invalid WXR XML: {error}") from error


_LEFT_BEHIND_REASONS = {
    "page": "pages are not migrated; rebuild them as page sections",
    "attachment": "media files are not fetched by the importer",
    "nav_menu_item": "navigation belongs to the target site",
}


def inspect_wxr(payload: bytes | str) -> WxrReport:
    """Report what a WXR 1.2 document contains without writing anything."""

    root = _document(payload)
    posts = 0
    authors: set[str] = set()
    categories: set[str] = set()
    tags: set[str] = set()
    media: set[str] = set()
    comments = 0
    left_behind: list[WxrNote] = []
    for item in root.findall("./channel/item"):
        comments += len(item.findall(f"{{{WP_NS}}}comment"))
        kind = (item.findtext(f"{{{WP_NS}}}post_type") or "post").strip()
        title = (item.findtext("title") or "").strip() or "(untitled)"
        if kind == "attachment":
            url = (item.findtext(f"{{{WP_NS}}}attachment_url") or "").strip()
            if url:
                media.add(url)
        if kind != "post":
            reason = _LEFT_BEHIND_REASONS.get(kind, f"unsupported item type {kind!r}")
            left_behind.append(WxrNote(kind=kind, title=title, reason=reason))
            continue
        if title == "(untitled)":
            left_behind.append(WxrNote(kind="post", title=title, reason="post has no title"))
            continue
        posts += 1
        author = (item.findtext(f"{{{DC_NS}}}creator") or "").strip()
        if author:
            authors.add(author)
        for term in item.findall("category"):
            value = _slug(term.get("nicename") or (term.text or ""), "")
            if not value:
                continue
            if term.get("domain") == "category":
                categories.add(value)
            elif term.get("domain") == "post_tag":
                tags.add(value)
        body = item.findtext(f"{{{CONTENT_NS}}}encoded") or ""
        for source in re.findall(r"<img[^>]*\ssrc=[\"']([^\"']+)", body, flags=re.IGNORECASE):
            media.add(source)
    return WxrReport(
        posts=posts,
        authors=tuple(sorted(authors)),
        categories=tuple(sorted(categories)),
        tags=tuple(sorted(tags)),
        media_urls=tuple(sorted(media)),
        comments=comments,
        left_behind=tuple(left_behind),
    )


def import_wxr(payload: bytes | str) -> WxrImport:
    """Convert posts from a WXR 1.2 document into articles.

    Pages, attachments, navigation items and comments are intentionally
    skipped: this is a blog importer, and silently inventing page-section or
    media semantics would make the migration look more complete than it is.
    """

    root = _document(payload)

    articles: list[Article] = []
    used_ids: set[str] = set()
    skipped = 0
    for position, item in enumerate(root.findall("./channel/item"), start=1):
        if (item.findtext(f"{{{WP_NS}}}post_type") or "post").strip() != "post":
            skipped += 1
            continue
        title = (item.findtext("title") or "").strip()
        if not title:
            skipped += 1
            continue
        foreign_id = (item.findtext(f"{{{WP_NS}}}post_id") or str(position)).strip()
        base_id = _slug(
            (item.findtext(f"{{{WP_NS}}}post_name") or title).strip(),
            f"wxr-{_slug(foreign_id, str(position))}",
        )
        article_id = base_id
        suffix = 2
        while article_id in used_ids:
            article_id = f"{base_id}-{suffix}"
            suffix += 1
        used_ids.add(article_id)

        created_at = _date(item)
        foreign_status = (item.findtext(f"{{{WP_NS}}}status") or "draft").strip()
        body = _markdown(item.findtext(f"{{{CONTENT_NS}}}encoded") or "")
        summary = _markdown(item.findtext(f"{{{EXCERPT_NS}}}encoded") or "")
        categories: list[str] = []
        tags: list[str] = []
        for term in item.findall("category"):
            nicename = term.get("nicename") or (term.text or "")
            value = _slug(nicename, "")
            if not value:
                continue
            if term.get("domain") == "category":
                categories.append(value)
            elif term.get("domain") == "post_tag":
                tags.append(value)

        article = new_article(
            article_id,
            ArticleContent(title=title, summary=summary, body_markdown=body, slug=article_id),
            now=created_at,
        )
        article.status = _status(foreign_status)
        article.category = categories[0] if categories else None
        article.tags = tuple(sorted(set(tags)))
        article.author = (item.findtext(f"{{{DC_NS}}}creator") or "").strip() or None
        article.fields = {"wxr_post_id": foreign_id}
        if foreign_status == "future":
            article.publish_at = created_at
        articles.append(article)

    return WxrImport(articles=tuple(articles), skipped=skipped)
