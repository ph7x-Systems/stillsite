"""Deterministic builder: content in, byte-identical artifact out.

No wall-clock, no randomness, no dict-order dependence. Every date comes from
the content; every collection is sorted before rendering; asset URLs carry
content hashes computed from the asset bytes.
"""

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import format_datetime
from xml.sax.saxutils import escape

from cms_core import (
    SOURCE_LANGUAGE,
    Article,
    ArticleContent,
    CommentsProvider,
    ContentStatus,
    Language,
    Page,
    TranslationState,
)
from cms_validation import SiteContent

from cms_build import urls
from cms_build.config import SiteConfig
from cms_build.head import Head, build_head, hreflang_code
from cms_build.images import generate_derivatives
from cms_build.markdown import render_markdown
from cms_build.themes import Theme, create_theme
from cms_build.ui import format_date, ui_label

MEDIA_PREFIX = "media"


@dataclass(slots=True)
class Artifact:
    """The build output: a mapping of relative file paths to bytes."""

    files: dict[str, bytes] = field(default_factory=dict)

    def add(self, path: str, content: str | bytes) -> None:
        self.files[path] = content.encode("utf-8") if isinstance(content, str) else content

    def paths(self) -> list[str]:
        return sorted(self.files)

    def digest(self) -> str:
        overall = hashlib.sha256()
        for path in self.paths():
            overall.update(path.encode("utf-8"))
            overall.update(self.files[path])
        return overall.hexdigest()


class _SafeHtml(str):
    """Marks builder-produced HTML as safe for Jinja autoescape."""

    def __html__(self) -> str:
        return str(self)


def _live(entry: Article | Page, now: datetime) -> bool:
    """Published, not in the trash (ADR-0026), and its moment has come
    (ADR-0024): a future publish_at keeps the entry out of the artifact
    until a build runs past it."""
    if entry.status is not ContentStatus.PUBLISHED or entry.deleted_at is not None:
        return False
    return entry.publish_at is None or entry.publish_at <= now


def _published_articles(content: SiteContent, now: datetime) -> list[Article]:
    articles = [a for a in content.articles if _live(a, now)]
    return sorted(articles, key=lambda a: (a.created_at.isoformat(), a.id), reverse=True)


def _published_pages(content: SiteContent, now: datetime) -> list[Page]:
    pages = [p for p in content.pages if _live(p, now)]
    return sorted(pages, key=lambda p: p.id)


def _available(
    entry: Article | Page, language: Language, source: Language = SOURCE_LANGUAGE
) -> bool:
    return entry.translation_state(language, source=source) is TranslationState.COMPLETE


def _article_content(
    article: Article, language: Language, source: Language = SOURCE_LANGUAGE
) -> ArticleContent:
    if language == source:
        return article.source
    return article.translations[language].content


def _asset_urls(theme_assets: Mapping[str, bytes]) -> dict[str, str]:
    hashed: dict[str, str] = {}
    for path in sorted(theme_assets):
        digest = hashlib.sha256(theme_assets[path]).hexdigest()[:8]
        hashed[path] = f"/{path}?v={digest}"
    return hashed


def _json_ld(payload: Mapping[str, object]) -> str:
    rendered = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return rendered.replace("</", "<\\/")


def _chunk[T](items: list[T], size: int) -> list[list[T]]:
    return [items[start : start + size] for start in range(0, len(items), size)] or [[]]


COMMENTS_ISLAND_PATH = "assets/comments-island.js"
"""ADR-0031: where the provider's vendored island ships in the artifact."""

CONTENT_API_VERSION = 1
"""The ``api/v1`` envelope version (M6 headless output). Additive fields
may join within a version; renames or removals bump it — consumers pin
the path, not this constant."""


class _SiteBuilder:
    def __init__(
        self,
        config: SiteConfig,
        content: SiteContent,
        theme: Theme,
        media_files: Mapping[str, bytes],
        now: datetime,
        comments_provider: CommentsProvider | None = None,
    ) -> None:
        self.config = config
        self.theme = theme
        self.artifact = Artifact()
        self.sitemap_urls: list[str] = []
        self.articles = _published_articles(content, now)
        self.pages = _published_pages(content, now)
        self.menu_items = sorted(content.menu, key=lambda item: (item.position, item.id))
        self.media_by_id = {asset.id: asset for asset in content.media}
        self.theme_assets = dict(theme.assets())
        # ADR-0031: the provider's island is a same-origin artifact asset,
        # hashed and shipped like any theme asset — no CDN, no third-party
        # request on page load.
        self.comments_provider = comments_provider if config.comments is not None else None
        if self.comments_provider is not None:
            self.theme_assets[COMMENTS_ISLAND_PATH] = self.comments_provider.island_js
        self.asset_urls = _asset_urls(self.theme_assets)
        self.media_files = dict(media_files)
        # ADR-0029: opt-in responsive derivatives extend the media set.
        self.image_variants = generate_derivatives(self.media_files, config.image_widths)
        self.articles_by_language: dict[Language, list[Article]] = {
            language: [a for a in self.articles if _available(a, language, config.source_language)]
            for language in config.all_languages
        }

    # Orchestration

    def _add_assets(self) -> None:
        for path, data in sorted(self.theme_assets.items()):
            self.artifact.add(path, data)
        for path, data in sorted(self.media_files.items()):
            self.artifact.add(f"{MEDIA_PREFIX}/{path}", data)

    def build(self) -> Artifact:
        self._add_assets()
        for language in self.config.all_languages:
            self._build_pages(language)
            self._build_articles(language)
            self._build_listings(language)
            self._build_category_and_tag_pages(language)
            self._build_feeds(language)
            if self.config.content_api:
                self._build_content_api(language)
        if self.config.content_api:
            self.artifact.add("api/v1/site.json", self._content_api_site())

        self._build_redirects()
        self._build_not_found()
        self.artifact.add("sitemap.xml", _sitemap(sorted(self.sitemap_urls)))
        self.artifact.add("robots.txt", _robots(self.config))
        return self.artifact

    def preview_entry(self, entry: Article | Page, language: Language) -> Artifact:
        """Render one entry through the real theme, regardless of workflow.

        The admin uses this for draft/autosave preview. Theme assets and
        referenced media accompany the HTML, but listings, feeds and utility
        pages are deliberately not rebuilt on every keystroke.
        """
        self._add_assets()
        if isinstance(entry, Article):
            self._render_article(entry, language)
        else:
            self._render_page(entry, language)
        return self.artifact

    # Rendering helpers

    def _render(self, kind: str, path: str, context: dict[str, object]) -> None:
        html = self.theme.render(kind, context)
        self.artifact.add(urls.output_file(path), html)
        self.sitemap_urls.append(urls.absolute(self.config, path))

    def _base_context(self, language: Language, head: Head) -> dict[str, object]:
        menu = self._menu(language)
        return {
            "head": head,
            "nav": {**_navigation(self.config, language, head.paths_by_language), "menu": menu},
            "footer": {
                "text": self.config.footer_text or self.config.name,
                "menu": menu,
                "admin_url": self.config.admin_url,
                "admin_label": ui_label(self.config, "admin", language),
            },
            "asset_urls": self.asset_urls,
        }

    def _menu(self, language: Language) -> list[dict[str, str]]:
        """Explicit menu items win (M6); with none defined, the menu
        derives from content: home-section anchors (sections with a
        `menu` field), then the blog, then every other published page."""
        if self.menu_items:
            return [{"label": item.label(language), "url": item.url} for item in self.menu_items]
        entries: list[dict[str, str]] = []
        home = next((p for p in self.pages if p.id == "home"), None)
        if home is not None and _available(home, language, self.config.source_language):
            home_path = urls.page_path(home, language, source=self.config.source_language)
            for section in home.sections:
                if language == self.config.source_language:
                    fields = section.source.fields
                else:
                    translation = section.translations.get(language)
                    fields = translation.content.fields if translation else section.source.fields
                label = fields.get("menu")
                if label:
                    entries.append({"label": label, "url": f"{home_path}#{section.key}"})
        entries.append(
            {
                "label": ui_label(self.config, "blog", language),
                "url": urls.blog_index_path(self.config, language),
            }
        )
        for page in self.pages:
            if page.id == "home" or not _available(page, language, self.config.source_language):
                continue
            body = (
                page.source
                if language == self.config.source_language
                else page.translations[language].content
            )
            url = urls.page_path(page, language, source=self.config.source_language)
            entries.append({"label": body.title, "url": url})
        return entries

    # Pages

    def _build_pages(self, language: Language) -> None:
        for page in self.pages:
            if not _available(page, language, self.config.source_language):
                continue
            self._render_page(page, language)

    def _render_page(self, page: Page, language: Language) -> None:
        path = urls.page_path(page, language, source=self.config.source_language)
        head = self._page_head(page, language)
        context = self._base_context(language, head)
        context["page"] = _page_context(page, language, self.config.source_language)
        context["sections"] = self._section_contexts(page, language)
        # Featured articles lead the home highlight; recency breaks ties
        # (M5). Listings, feeds and pagination keep pure recency.
        highlight = sorted(self.articles_by_language[language], key=lambda a: (not a.featured,))[:3]
        context["latest"] = self._listing_entries(highlight, language)
        self._render("page", path, context)

    def _page_head(self, page: Page, language: Language) -> Head:
        paths = {
            lang: urls.page_path(page, lang, source=self.config.source_language)
            for lang in self.config.all_languages
            if _available(page, lang, self.config.source_language)
        }
        body = (
            page.source
            if language == self.config.source_language
            else page.translations[language].content
        )
        json_ld = None
        if page.id == "home" and self.config.organization is not None:
            json_ld = _json_ld({"@context": "https://schema.org", **self.config.organization})
        return build_head(
            self.config,
            title=body.title,
            description=body.description,
            language=language,
            paths_by_language=paths,
            json_ld=json_ld,
        )

    def _section_contexts(self, page: Page, language: Language) -> list[dict[str, object]]:
        contexts: list[dict[str, object]] = []
        for section in page.sections:
            if language == self.config.source_language:
                body = section.source
            else:
                translation = section.translations.get(language)
                body = translation.content if translation else section.source
            images = []
            for media_id in body.media:
                image = self._media_image(media_id, language)
                if image is None:
                    continue
                images.append(image)
            contexts.append(
                {
                    "key": section.key,
                    "kind": section.kind,
                    "fields": sorted(body.fields.items()),
                    "data": dict(body.fields),
                    "images": images,
                }
            )
        return contexts

    # Articles

    def _build_articles(self, language: Language) -> None:
        for article in self.articles_by_language[language]:
            self._render_article(article, language)

    def _render_article(self, article: Article, language: Language) -> None:
        path = urls.article_path(self.config, article, language)
        body = _article_content(article, language, self.config.source_language)
        head = self._article_head(article, language)
        context = self._base_context(language, head)
        context["article"] = {
            "title": body.title,
            "summary": body.summary,
            "date_iso": article.created_at.date().isoformat(),
            "back_url": urls.blog_index_path(self.config, language),
            "back_label": ui_label(self.config, "back", language),
            "date_human": format_date(
                article.created_at.day,
                article.created_at.month,
                article.created_at.year,
                language,
            ),
            "minutes": _reading_minutes(body.body_markdown),
            "min_read_label": ui_label(self.config, "min-read", language),
            "category": self._category_context(article, language),
            "tags": [
                {"slug": tag, "url": urls.tag_path(self.config, tag, language)}
                for tag in article.tags
            ],
            "body_html": _SafeHtml(render_markdown(body.body_markdown)),
            "author": article.author,
            "featured": article.featured,
            "fields": dict(sorted(article.fields.items())),
        }
        if self.comments_provider is not None and self.config.comments is not None:
            # ADR-0031: a plain localized link is the no-JS surface; the
            # island upgrades it and contacts nothing before the reader acts.
            context["comments"] = {
                "label": ui_label(self.config, "comments", language),
                "thread_url": self.comments_provider.thread_url(
                    str(self.config.comments.url), urls.absolute(self.config, path)
                ),
                "island_url": self.asset_urls[COMMENTS_ISLAND_PATH],
            }
        self._render("article", path, context)

    def _category_context(self, article: Article, language: Language) -> dict[str, str] | None:
        if article.category is None:
            return None
        return {
            "slug": article.category,
            "label": self.config.category_label(article.category, language),
            "url": urls.category_path(self.config, article.category, language),
        }

    def _article_head(self, article: Article, language: Language) -> Head:
        paths = {
            lang: urls.article_path(self.config, article, lang)
            for lang in self.config.all_languages
            if _available(article, lang, self.config.source_language)
        }
        body = _article_content(article, language, self.config.source_language)
        json_ld = _json_ld(
            {
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": body.title,
                "description": body.summary,
                "datePublished": article.created_at.date().isoformat(),
                "inLanguage": hreflang_code(language),
                "mainEntityOfPage": urls.absolute(
                    self.config, urls.article_path(self.config, article, language)
                ),
            }
        )
        return build_head(
            self.config,
            title=body.title,
            description=body.summary,
            language=language,
            paths_by_language=paths,
            og_type="article",
            json_ld=json_ld,
        )

    # Listings, categories, tags

    def _listing_entries(
        self, articles: list[Article], language: Language
    ) -> list[dict[str, object]]:
        return [
            {
                "title": _article_content(a, language, self.config.source_language).title,
                "summary": _article_content(a, language, self.config.source_language).summary,
                "url": urls.article_path(self.config, a, language),
                "date_iso": a.created_at.date().isoformat(),
                "date_human": format_date(
                    a.created_at.day, a.created_at.month, a.created_at.year, language
                ),
                "minutes": _reading_minutes(
                    _article_content(a, language, self.config.source_language).body_markdown
                ),
                "min_read_label": ui_label(self.config, "min-read", language),
                "category": (
                    self.config.category_label(a.category, language) if a.category else None
                ),
                "thumb": self._media_image(a.cover, language),
                "featured": a.featured,
                "author": a.author,
            }
            for a in articles
        ]

    def _build_listings(self, language: Language) -> None:
        chunks = _chunk(self.articles_by_language[language], self.config.page_size)
        page_counts = {
            lang: len(_chunk(self.articles_by_language[lang], self.config.page_size))
            for lang in self.config.all_languages
        }
        blog_label = ui_label(self.config, "blog-title", language)
        blog_sub = ui_label(self.config, "blog-sub", language)
        for index, chunk in enumerate(chunks, start=1):
            path = urls.blog_page_path(self.config, language, index)
            paths = {
                lang: urls.blog_page_path(self.config, lang, index)
                for lang in self.config.all_languages
                if page_counts[lang] >= index
            }
            head = build_head(
                self.config,
                title=blog_label if index == 1 else f"{blog_label} — {index}",
                description=self.config.name,
                language=language,
                paths_by_language=paths,
            )
            context = self._base_context(language, head)
            context["listing"] = {
                "title": blog_label,
                "entries": self._listing_entries(chunk, language),
                "page": index,
                "pages": len(chunks),
                "previous_url": (
                    urls.blog_page_path(self.config, language, index - 1) if index > 1 else None
                ),
                "next_url": (
                    urls.blog_page_path(self.config, language, index + 1)
                    if index < len(chunks)
                    else None
                ),
                "search_index_url": self._search_index_url(language),
                "search_label": ui_label(self.config, "search", language),
                "view_cards_label": ui_label(self.config, "view-cards", language),
                "view_list_label": ui_label(self.config, "view-list", language),
                "eyebrow": ui_label(self.config, "blog-eyebrow", language),
                "sub": blog_sub,
                "filters": self._category_filters(language),
            }
            self._render("listing", path, context)

    def _build_category_and_tag_pages(self, language: Language) -> None:
        articles = self.articles_by_language[language]
        categories = sorted({a.category for a in articles if a.category is not None})
        for slug in categories:
            members = [a for a in articles if a.category == slug]
            path = urls.category_path(self.config, slug, language)
            self._build_taxonomy_page(
                language,
                path,
                title=self.config.category_label(slug, language),
                articles=members,
                paths_for=lambda lang, s=slug: urls.category_path(self.config, s, lang),
            )
        tags = sorted({tag for a in articles for tag in a.tags})
        for slug in tags:
            members = [a for a in articles if slug in a.tags]
            path = urls.tag_path(self.config, slug, language)
            self._build_taxonomy_page(
                language,
                path,
                title=slug,
                articles=members,
                paths_for=lambda lang, s=slug: urls.tag_path(self.config, s, lang),
            )

    def _build_taxonomy_page(
        self,
        language: Language,
        path: str,
        *,
        title: str,
        articles: list[Article],
        paths_for: Callable[[Language], str],
    ) -> None:
        paths = {
            lang: paths_for(lang)
            for lang in self.config.all_languages
            if any(a in self.articles_by_language[lang] for a in articles)
        }
        head = build_head(
            self.config,
            title=title,
            description=self.config.name,
            language=language,
            paths_by_language=paths,
        )
        context = self._base_context(language, head)
        context["listing"] = {
            "title": title,
            "entries": self._listing_entries(articles, language),
            "page": 1,
            "pages": 1,
            "previous_url": None,
            "next_url": None,
            "search_index_url": self._search_index_url(language),
            "search_label": ui_label(self.config, "search", language),
            "view_cards_label": ui_label(self.config, "view-cards", language),
            "view_list_label": ui_label(self.config, "view-list", language),
            "eyebrow": ui_label(self.config, "blog-eyebrow", language),
            "sub": None,
            "filters": self._category_filters(language),
        }
        self._render("listing", path, context)

    # Feeds and utility pages

    def _media_image(self, media_id: str | None, language: Language) -> dict[str, object] | None:
        if media_id is None:
            return None
        asset = self.media_by_id.get(media_id)
        if asset is None or not asset.is_image:
            return None
        image = {
            "url": f"/{MEDIA_PREFIX}/{asset.path}",
            "alt": asset.alt.get(language)
            or asset.alt.get(self.config.source_language)
            or next((text for text in asset.alt.values() if text.strip()), ""),
            "width": asset.width,
            "height": asset.height,
        }
        variants = self.image_variants.get(asset.path)
        if variants and asset.width:
            candidates = [
                f"/{MEDIA_PREFIX}/{path} {width}w" for width, path in sorted(variants.items())
            ]
            candidates.append(f"/{MEDIA_PREFIX}/{asset.path} {asset.width}w")
            image["srcset"] = ", ".join(candidates)
        return image

    def _category_filters(self, language: Language) -> list[dict[str, str]]:
        slugs = sorted(
            {a.category for a in self.articles_by_language[language] if a.category is not None}
        )
        return [
            {
                "label": self.config.category_label(slug, language),
                "url": urls.category_path(self.config, slug, language),
            }
            for slug in slugs
        ]

    def _search_index_url(self, language: Language) -> str:
        return urls.blog_index_path(self.config, language) + "search-index.json"

    def _build_feeds(self, language: Language) -> None:
        articles = self.articles_by_language[language]
        listing_file = urls.output_file(urls.blog_index_path(self.config, language))
        self.artifact.add(
            listing_file.replace("index.html", "search-index.json"),
            self._search_index(language, articles),
        )
        self.artifact.add(
            listing_file.replace("index.html", "rss.xml"), _rss(self.config, language, articles)
        )

    def _search_index(self, language: Language, articles: list[Article]) -> str:
        entries = [
            {
                "t": _article_content(a, language, self.config.source_language).title,
                "e": _article_content(a, language, self.config.source_language).summary,
                "u": urls.article_path(self.config, a, language),
                "d": a.created_at.date().isoformat(),
                "c": (
                    self.config.category_label(a.category, language)
                    if a.category is not None
                    else ""
                ),
            }
            for a in articles
        ]
        return json.dumps(entries, ensure_ascii=False, sort_keys=True) + "\n"

    # Content API (M6): versioned headless JSON, same rules as the HTML.

    def _content_api_site(self) -> str:
        payload: dict[str, object] = {
            "version": CONTENT_API_VERSION,
            "name": self.config.name,
            "base_url": str(self.config.base_url),
            "blog_path": self.config.blog_path,
            "languages": [language.value for language in self.config.all_languages],
            "categories": {
                slug: {code.value: label for code, label in labels.items()}
                for slug, labels in sorted(self.config.categories.items())
            },
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n"

    def _build_content_api(self, language: Language) -> None:
        """One file per language: exactly the entries the HTML build ships
        (published, out of the trash, past their moment, translation
        complete), with slugs, relationships and media metadata."""
        payload: dict[str, object] = {
            "version": CONTENT_API_VERSION,
            "language": language.value,
            "articles": [
                self._content_api_article(article, language)
                for article in self.articles_by_language[language]
            ],
            "pages": [
                self._content_api_page(page, language)
                for page in self.pages
                if _available(page, language, self.config.source_language)
            ],
        }
        self.artifact.add(
            f"api/v1/{language.value}/content.json",
            json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n",
        )

    def _content_api_article(self, article: Article, language: Language) -> dict[str, object]:
        body = _article_content(article, language, self.config.source_language)
        return {
            "id": article.id,
            "slug": body.slug,
            "url": urls.article_path(self.config, article, language),
            "title": body.title,
            "summary": body.summary,
            "body_html": render_markdown(body.body_markdown),
            "date": article.created_at.date().isoformat(),
            "author": article.author,
            "featured": article.featured,
            "category": self._category_context(article, language),
            "tags": [
                {"slug": tag, "url": urls.tag_path(self.config, tag, language)}
                for tag in article.tags
            ],
            "cover": self._media_image(article.cover, language),
            "fields": dict(sorted(article.fields.items())),
        }

    def _content_api_page(self, page: Page, language: Language) -> dict[str, object]:
        body = (
            page.source
            if language == self.config.source_language
            else page.translations[language].content
        )
        return {
            "id": page.id,
            "slug": body.slug,
            "url": urls.page_path(page, language, source=self.config.source_language),
            "title": body.title,
            "description": body.description,
            "sections": [
                {
                    "key": section["key"],
                    "kind": section["kind"],
                    "fields": section["data"],
                    "images": section["images"],
                }
                for section in self._section_contexts(page, language)
            ],
        }

    def _build_redirects(self) -> None:
        """Meta-refresh fallback pages for every configured redirect (M6):
        real 301s come from the target configs, but these make redirects
        work on any static host — and hold canonical for crawlers."""
        for source, destination in sorted(self.config.redirects.items()):
            html = (
                '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
                f'<meta http-equiv="refresh" content="0; url={escape(destination)}">\n'
                f'<link rel="canonical" href="{escape(destination)}">\n'
                '<meta name="robots" content="noindex">\n'
                f"<title>Redirecting</title>\n</head>\n<body>\n"
                f'<p><a href="{escape(destination)}">Moved here</a></p>\n</body>\n</html>\n'
            )
            self.artifact.add(urls.output_file(source), html)

    # ADR-0021: the error-page contract — every build ships these four,
    # every target serves them. All render through the not_found template.
    ERROR_PAGES: tuple[tuple[str, str], ...] = (
        ("401.html", "error-unauthorized"),
        ("403.html", "error-forbidden"),
        ("404.html", "not-found"),
        ("50x.html", "error-server"),
    )

    def _build_not_found(self) -> None:
        for filename, label in self.ERROR_PAGES:
            source = self.config.source_language
            head = build_head(
                self.config,
                title=ui_label(self.config, label, source),
                description=self.config.name,
                language=source,
                paths_by_language={source: f"/{filename}"},
            )
            context = self._base_context(source, head)
            context["not_found"] = {"home_url": "/"}
            self.artifact.add(filename, self.theme.render("not_found", context))


def build_site(
    config: SiteConfig,
    content: SiteContent,
    *,
    theme: Theme | None = None,
    media_files: Mapping[str, bytes] | None = None,
    now: datetime | None = None,
    comments_provider: CommentsProvider | None = None,
) -> Artifact:
    """Build the site. ``now`` is the scheduling clock (ADR-0024): the
    build stays deterministic for the same content and the same ``now``.
    Callers at the boundary (CLI, admin) pass the wall clock; tests pass
    fixed values. None falls back to the wall clock, consulted only when
    an entry actually carries ``publish_at``."""
    active_theme = theme or create_theme(config.theme)
    moment = now or datetime.now(tz=UTC)
    return _SiteBuilder(
        config, content, active_theme, media_files or {}, moment, comments_provider
    ).build()


def build_entry_preview(
    config: SiteConfig,
    content: SiteContent,
    entry: Article | Page,
    *,
    language: Language = SOURCE_LANGUAGE,
    theme: Theme | None = None,
    media_files: Mapping[str, bytes] | None = None,
    now: datetime | None = None,
    comments_provider: CommentsProvider | None = None,
) -> Artifact:
    """Render one saved or unsaved entry through the active real theme.

    Unlike a publish build, editorial preview intentionally includes drafts
    and future entries. Surrounding navigation/highlights still derive only
    from live content, preserving the site's real context.
    """
    active_theme = theme or create_theme(config.theme)
    moment = now or datetime.now(tz=UTC)
    return _SiteBuilder(
        config, content, active_theme, media_files or {}, moment, comments_provider
    ).preview_entry(entry, language)


def _reading_minutes(markdown: str) -> int:
    words = len(markdown.split())
    return max(1, round(words / 200))


def _navigation(
    config: SiteConfig,
    language: Language,
    paths_by_language: dict[Language, str] | None = None,
) -> dict[str, object]:
    """The switcher keeps the reader on the current page wherever it exists
    in the other language, and falls back to that language's home."""
    paths = paths_by_language or {}
    return {
        "home_url": urls.language_prefix(language) + "/",
        "languages": [
            {
                "code": lang.value.split("-")[0],
                "url": paths.get(lang, urls.language_prefix(lang) + "/"),
                "current": lang is language,
            }
            for lang in config.all_languages
        ],
    }


def _page_context(
    page: Page, language: Language, source: Language = SOURCE_LANGUAGE
) -> dict[str, str]:
    body = page.source if language == source else page.translations[language].content
    return {"title": body.title, "description": body.description}


def _rss(config: SiteConfig, language: Language, articles: list[Article]) -> str:
    items: list[str] = []
    for article in articles:
        body = _article_content(article, language, config.source_language)
        link = urls.absolute(config, urls.article_path(config, article, language))
        items.append(
            "<item>"
            f"<title>{escape(body.title)}</title>"
            f"<link>{escape(link)}</link>"
            f"<guid>{escape(link)}</guid>"
            f"<pubDate>{format_datetime(article.created_at)}</pubDate>"
            f"<description>{escape(body.summary)}</description>"
            "</item>"
        )
    channel_link = urls.absolute(config, urls.blog_index_path(config, language))
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rss version="2.0"><channel>'
        f"<title>{escape(config.name)}</title>"
        f"<link>{escape(channel_link)}</link>"
        f"<description>{escape(config.name)}</description>"
        f"<language>{hreflang_code(language)}</language>" + "".join(items) + "</channel></rss>\n"
    )


def _sitemap(locations: list[str]) -> str:
    entries = "".join(f"<url><loc>{escape(loc)}</loc></url>" for loc in locations)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + entries + "</urlset>\n"
    )


def _robots(config: SiteConfig) -> str:
    return f"User-agent: *\nAllow: /\nSitemap: {config.root}/sitemap.xml\n"
