"""Deterministic builder: content in, byte-identical artifact out.

No wall-clock, no randomness, no dict-order dependence. Every date comes from
the content; every collection is sorted before rendering; asset URLs carry
content hashes computed from the asset bytes.
"""

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from email.utils import format_datetime
from xml.sax.saxutils import escape

from cms_core import (
    SOURCE_LANGUAGE,
    Article,
    ArticleContent,
    ContentStatus,
    Language,
    MediaAsset,
    Page,
    TranslationState,
)
from cms_validation import SiteContent

from cms_build import urls
from cms_build.config import SiteConfig
from cms_build.head import Head, build_head, hreflang_code
from cms_build.markdown import render_markdown
from cms_build.themes import Theme, create_theme


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


def build_site(config: SiteConfig, content: SiteContent, *, theme: Theme | None = None) -> Artifact:
    active_theme = theme or create_theme(config.theme)
    artifact = Artifact()
    theme_assets = dict(active_theme.assets())
    asset_urls = _asset_urls(theme_assets)
    for path, data in sorted(theme_assets.items()):
        artifact.add(path, data)

    articles = _published_articles(content)
    pages = _published_pages(content)
    media_by_id = {asset.id: asset for asset in content.media}
    sitemap_urls: list[str] = []

    for language in config.all_languages:
        lang_articles = [a for a in articles if _available(a, language)]
        lang_pages = [p for p in pages if _available(p, language)]
        nav = _navigation(config, language)
        footer = {"text": config.name}

        for page in lang_pages:
            path = urls.page_path(page, language)
            head = _page_head(config, page, language)
            html = active_theme.render(
                "page",
                {
                    "head": head,
                    "nav": nav,
                    "footer": footer,
                    "asset_urls": asset_urls,
                    "page": _page_context(page, language),
                    "sections": _section_contexts(page, language, media_by_id),
                },
            )
            artifact.add(urls.output_file(path), html)
            sitemap_urls.append(urls.absolute(config, path))

        for article in lang_articles:
            path = urls.article_path(config, article, language)
            head = _article_head(config, article, language)
            body = _article_content(article, language)
            html = active_theme.render(
                "article",
                {
                    "head": head,
                    "nav": nav,
                    "footer": footer,
                    "asset_urls": asset_urls,
                    "article": {
                        "title": body.title,
                        "summary": body.summary,
                        "date_iso": article.created_at.date().isoformat(),
                        "body_html": _safe_html(render_markdown(body.body_markdown)),
                    },
                },
            )
            artifact.add(urls.output_file(path), html)
            sitemap_urls.append(urls.absolute(config, path))

        listing_path = urls.blog_index_path(config, language)
        entries = [
            {
                "title": _article_content(a, language).title,
                "summary": _article_content(a, language).summary,
                "url": urls.article_path(config, a, language),
                "date_iso": a.created_at.date().isoformat(),
            }
            for a in lang_articles
        ]
        listing_html = active_theme.render(
            "listing",
            {
                "head": _listing_head(config, language, lang_articles),
                "nav": nav,
                "footer": footer,
                "asset_urls": asset_urls,
                "listing": {"title": "Blog", "entries": entries},
            },
        )
        artifact.add(urls.output_file(listing_path), listing_html)
        sitemap_urls.append(urls.absolute(config, listing_path))

        artifact.add(
            urls.output_file(listing_path).replace("index.html", "search-index.json"),
            _search_index(config, language, lang_articles),
        )
        artifact.add(
            urls.output_file(listing_path).replace("index.html", "rss.xml"),
            _rss(config, language, lang_articles),
        )

    artifact.add("sitemap.xml", _sitemap(sorted(sitemap_urls)))
    artifact.add("robots.txt", _robots(config))
    return artifact


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


class _SafeHtml(str):
    """Marks builder-produced HTML as safe for Jinja autoescape."""

    def __html__(self) -> str:
        return str(self)


def _safe_html(html: str) -> _SafeHtml:
    return _SafeHtml(html)


def _page_head(config: SiteConfig, page: Page, language: Language) -> Head:
    paths = {
        lang: urls.page_path(page, lang) for lang in config.all_languages if _available(page, lang)
    }
    body = page.source if language is SOURCE_LANGUAGE else page.translations[language].content
    return build_head(
        config,
        title=body.title,
        description=body.description,
        language=language,
        paths_by_language=paths,
    )


def _article_head(config: SiteConfig, article: Article, language: Language) -> Head:
    paths = {
        lang: urls.article_path(config, article, lang)
        for lang in config.all_languages
        if _available(article, lang)
    }
    body = _article_content(article, language)
    return build_head(
        config,
        title=body.title,
        description=body.summary,
        language=language,
        paths_by_language=paths,
        og_type="article",
    )


def _listing_head(config: SiteConfig, language: Language, articles: list[Article]) -> Head:
    paths = {lang: urls.blog_index_path(config, lang) for lang in config.all_languages}
    return build_head(
        config,
        title="Blog",
        description=config.name,
        language=language,
        paths_by_language=paths,
    )


def _page_context(page: Page, language: Language) -> dict[str, str]:
    body = page.source if language is SOURCE_LANGUAGE else page.translations[language].content
    return {"title": body.title, "description": body.description}


def _section_contexts(
    page: Page, language: Language, media_by_id: Mapping[str, MediaAsset]
) -> list[dict[str, object]]:
    contexts: list[dict[str, object]] = []
    for section in page.sections:
        if language is SOURCE_LANGUAGE:
            body = section.source
        else:
            translation = section.translations.get(language)
            body = translation.content if translation else section.source
        images = []
        for media_id in body.media:
            asset = media_by_id.get(media_id)
            if asset is None or not asset.is_image:
                continue
            alt = asset.alt.get(language) or asset.alt[SOURCE_LANGUAGE]
            images.append(
                {
                    "url": f"/{asset.path}",
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
                "images": images,
            }
        )
    return contexts


def _search_index(config: SiteConfig, language: Language, articles: list[Article]) -> str:
    entries = [
        {
            "t": _article_content(a, language).title,
            "e": _article_content(a, language).summary,
            "u": urls.article_path(config, a, language),
            "d": a.created_at.date().isoformat(),
        }
        for a in articles
    ]
    return json.dumps(entries, ensure_ascii=False, sort_keys=True) + "\n"


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
