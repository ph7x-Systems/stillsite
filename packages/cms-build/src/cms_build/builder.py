"""Deterministic builder: content in, byte-identical artifact out.

No wall-clock, no randomness, no dict-order dependence. Every date comes from
the content; every collection is sorted before rendering; asset URLs carry
content hashes computed from the asset bytes.
"""

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from email.utils import format_datetime
from xml.sax.saxutils import escape

from cms_core import (
    SOURCE_LANGUAGE,
    Article,
    ArticleContent,
    ContentStatus,
    Language,
    Page,
    TranslationState,
)
from cms_validation import SiteContent

from cms_build import urls
from cms_build.config import SiteConfig
from cms_build.head import Head, build_head, hreflang_code
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


def _published_articles(content: SiteContent) -> list[Article]:
    articles = [a for a in content.articles if a.status is ContentStatus.PUBLISHED]
    return sorted(articles, key=lambda a: (a.created_at.isoformat(), a.id), reverse=True)


def _published_pages(content: SiteContent) -> list[Page]:
    pages = [p for p in content.pages if p.status is ContentStatus.PUBLISHED]
    return sorted(pages, key=lambda p: p.id)


def _available(entry: Article | Page, language: Language) -> bool:
    return entry.translation_state(language) is TranslationState.COMPLETE


def _article_content(article: Article, language: Language) -> ArticleContent:
    if language is SOURCE_LANGUAGE:
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


class _SiteBuilder:
    def __init__(
        self,
        config: SiteConfig,
        content: SiteContent,
        theme: Theme,
        media_files: Mapping[str, bytes],
    ) -> None:
        self.config = config
        self.theme = theme
        self.artifact = Artifact()
        self.sitemap_urls: list[str] = []
        self.articles = _published_articles(content)
        self.pages = _published_pages(content)
        self.media_by_id = {asset.id: asset for asset in content.media}
        self.theme_assets = dict(theme.assets())
        self.asset_urls = _asset_urls(self.theme_assets)
        self.media_files = media_files
        self.articles_by_language: dict[Language, list[Article]] = {
            language: [a for a in self.articles if _available(a, language)]
            for language in config.all_languages
        }

    # Orchestration

    def build(self) -> Artifact:
        for path, data in sorted(self.theme_assets.items()):
            self.artifact.add(path, data)
        for path, data in sorted(self.media_files.items()):
            self.artifact.add(f"{MEDIA_PREFIX}/{path}", data)

        for language in self.config.all_languages:
            self._build_pages(language)
            self._build_articles(language)
            self._build_listings(language)
            self._build_category_and_tag_pages(language)
            self._build_feeds(language)

        self._build_not_found()
        self.artifact.add("sitemap.xml", _sitemap(sorted(self.sitemap_urls)))
        self.artifact.add("robots.txt", _robots(self.config))
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
            "nav": {**_navigation(self.config, language), "menu": menu},
            "footer": {
                "text": self.config.footer_text or self.config.name,
                "menu": menu,
                "admin_url": self.config.admin_url,
                "admin_label": ui_label(self.config, "admin", language),
            },
            "asset_urls": self.asset_urls,
        }

    def _menu(self, language: Language) -> list[dict[str, str]]:
        """Site menu: home-section anchors (sections with a `menu` field),
        then the blog, then every other published page."""
        entries: list[dict[str, str]] = []
        home = next((p for p in self.pages if p.id == "home"), None)
        if home is not None and _available(home, language):
            home_path = urls.page_path(home, language)
            for section in home.sections:
                if language is SOURCE_LANGUAGE:
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
            if page.id == "home" or not _available(page, language):
                continue
            body = (
                page.source if language is SOURCE_LANGUAGE else page.translations[language].content
            )
            entries.append({"label": body.title, "url": urls.page_path(page, language)})
        return entries

    # Pages

    def _build_pages(self, language: Language) -> None:
        for page in self.pages:
            if not _available(page, language):
                continue
            path = urls.page_path(page, language)
            head = self._page_head(page, language)
            context = self._base_context(language, head)
            context["page"] = _page_context(page, language)
            context["sections"] = self._section_contexts(page, language)
            context["latest"] = self._listing_entries(
                self.articles_by_language[language][:3], language
            )
            self._render("page", path, context)

    def _page_head(self, page: Page, language: Language) -> Head:
        paths = {
            lang: urls.page_path(page, lang)
            for lang in self.config.all_languages
            if _available(page, lang)
        }
        body = page.source if language is SOURCE_LANGUAGE else page.translations[language].content
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
            if language is SOURCE_LANGUAGE:
                body = section.source
            else:
                translation = section.translations.get(language)
                body = translation.content if translation else section.source
            images = []
            for media_id in body.media:
                asset = self.media_by_id.get(media_id)
                if asset is None or not asset.is_image:
                    continue
                alt = asset.alt.get(language) or asset.alt[SOURCE_LANGUAGE]
                images.append(
                    {
                        "url": f"/{MEDIA_PREFIX}/{asset.path}",
                        "alt": alt,
                        "width": asset.width,
                        "height": asset.height,
                    }
                )
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
            path = urls.article_path(self.config, article, language)
            body = _article_content(article, language)
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
            if _available(article, lang)
        }
        body = _article_content(article, language)
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
                "title": _article_content(a, language).title,
                "summary": _article_content(a, language).summary,
                "url": urls.article_path(self.config, a, language),
                "date_iso": a.created_at.date().isoformat(),
                "date_human": format_date(
                    a.created_at.day, a.created_at.month, a.created_at.year, language
                ),
                "minutes": _reading_minutes(_article_content(a, language).body_markdown),
                "min_read_label": ui_label(self.config, "min-read", language),
                "category": (
                    self.config.category_label(a.category, language) if a.category else None
                ),
                "thumb": self._media_image(a.cover, language),
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
        return {
            "url": f"/{MEDIA_PREFIX}/{asset.path}",
            "alt": asset.alt.get(language) or asset.alt[SOURCE_LANGUAGE],
            "width": asset.width,
            "height": asset.height,
        }

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
                "t": _article_content(a, language).title,
                "e": _article_content(a, language).summary,
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

    def _build_not_found(self) -> None:
        head = build_head(
            self.config,
            title=ui_label(self.config, "not-found", SOURCE_LANGUAGE),
            description=self.config.name,
            language=SOURCE_LANGUAGE,
            paths_by_language={SOURCE_LANGUAGE: "/404.html"},
        )
        context = self._base_context(SOURCE_LANGUAGE, head)
        context["not_found"] = {"home_url": "/"}
        html = self.theme.render("not_found", context)
        self.artifact.add("404.html", html)


def build_site(
    config: SiteConfig,
    content: SiteContent,
    *,
    theme: Theme | None = None,
    media_files: Mapping[str, bytes] | None = None,
) -> Artifact:
    active_theme = theme or create_theme(config.theme)
    return _SiteBuilder(config, content, active_theme, media_files or {}).build()


def _reading_minutes(markdown: str) -> int:
    words = len(markdown.split())
    return max(1, round(words / 200))


def _navigation(config: SiteConfig, language: Language) -> dict[str, object]:
    return {
        "home_url": urls.language_prefix(language) + "/",
        "languages": [
            {
                "code": lang.value.split("-")[0],
                "url": urls.language_prefix(lang) + "/",
                "current": lang is language,
            }
            for lang in config.all_languages
        ],
    }


def _page_context(page: Page, language: Language) -> dict[str, str]:
    body = page.source if language is SOURCE_LANGUAGE else page.translations[language].content
    return {"title": body.title, "description": body.description}


def _rss(config: SiteConfig, language: Language, articles: list[Article]) -> str:
    items: list[str] = []
    for article in articles:
        body = _article_content(article, language)
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
