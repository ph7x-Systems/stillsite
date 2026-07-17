"""Deterministic builder: URL tree, head contract, feeds and determinism."""

import json
import re
from datetime import UTC, datetime

from cms_build import SiteConfig, build_site
from cms_core import (
    ArticleContent,
    ContentStatus,
    Language,
    PageContent,
    Section,
    SectionContent,
    new_article,
    new_page,
)
from cms_validation import SiteContent

NOW = datetime(2026, 1, 15, 9, 0, tzinfo=UTC)

CONFIG = SiteConfig(
    name="Aurora Cartography",
    base_url="https://example.com",
    languages=(Language.PT_PT, Language.DE),
)


def make_content() -> SiteContent:
    home = new_page("home", PageContent(title="Home", description="D", slug="home"), now=NOW)
    home.set_translation(
        Language.PT_PT, PageContent(title="Início", description="D", slug="inicio")
    )
    home.set_translation(Language.DE, PageContent(title="Start", description="D", slug="start"))
    hero = Section(key="hero", kind="hero", source=SectionContent(fields={"heading": "Hi"}))
    hero.set_translation(Language.PT_PT, SectionContent(fields={"heading": "Olá"}))
    hero.set_translation(Language.DE, SectionContent(fields={"heading": "Hallo"}))
    home.sections.append(hero)
    home.status = ContentStatus.PUBLISHED

    article = new_article(
        "first-post",
        ArticleContent(title="First", summary="S", body_markdown="Hello **world**"),
        now=NOW,
    )
    article.set_translation(
        Language.PT_PT,
        ArticleContent(title="Primeiro", summary="S", body_markdown="Olá", slug="primeiro-post"),
    )
    article.status = ContentStatus.PUBLISHED
    return SiteContent(pages=[home], articles=[article])


def test_build_is_deterministic() -> None:
    first = build_site(CONFIG, make_content())
    second = build_site(CONFIG, make_content())
    assert first.digest() == second.digest()
    assert first.paths() == second.paths()


def test_url_tree_uses_localized_slugs() -> None:
    artifact = build_site(CONFIG, make_content())
    paths = artifact.paths()
    assert "index.html" in paths
    assert "pt-pt/index.html" in paths
    assert "blog/first-post/index.html" in paths
    assert "pt-pt/blog/primeiro-post/index.html" in paths
    # DE has no article translation: the article must not exist in German.
    assert not any(
        path.startswith("de/blog/") and "index.html" in path and path != "de/blog/index.html"
        for path in paths
    )


def test_head_contract_on_every_html_page() -> None:
    artifact = build_site(CONFIG, make_content())
    for path in artifact.paths():
        if not path.endswith(".html"):
            continue
        html = artifact.files[path].decode("utf-8")
        assert re.search(r'<link rel="canonical" href="https://example\.com/', html), path
        assert 'hreflang="x-default"' in html, path
        assert '<meta property="og:title"' in html, path
        assert '<meta name="description"' in html, path


def test_incomplete_language_is_excluded_from_alternates() -> None:
    artifact = build_site(CONFIG, make_content())
    article_html = artifact.files["blog/first-post/index.html"].decode("utf-8")
    assert 'hreflang="pt-PT"' in article_html
    assert 'hreflang="de"' not in article_html


def test_markdown_is_rendered_and_raw_html_escaped() -> None:
    content = make_content()
    article = content.articles[0]
    article.source = ArticleContent(
        title="First", summary="S", body_markdown="Hello <script>alert(1)</script> **bold**"
    )
    article.set_translation(Language.PT_PT, ArticleContent(title="P", summary="S"))
    artifact = build_site(CONFIG, SiteContent(pages=content.pages, articles=[article]))
    html = artifact.files["blog/first-post/index.html"].decode("utf-8")
    assert "<strong>bold</strong>" in html
    assert "<script>" not in html


def test_feeds_indexes_and_sitemap_present_per_language() -> None:
    artifact = build_site(CONFIG, make_content())
    for prefix in ("", "pt-pt/", "de/"):
        assert f"{prefix}blog/rss.xml" in artifact.paths()
        index = json.loads(artifact.files[f"{prefix}blog/search-index.json"])
        assert isinstance(index, list)
    sitemap = artifact.files["sitemap.xml"].decode("utf-8")
    assert "https://example.com/pt-pt/" in sitemap
    robots = artifact.files["robots.txt"].decode("utf-8")
    assert "Sitemap: https://example.com/sitemap.xml" in robots


def test_assets_are_hash_versioned() -> None:
    artifact = build_site(CONFIG, make_content())
    html = artifact.files["index.html"].decode("utf-8")
    assert re.search(r'href="/assets/site\.css\?v=[0-9a-f]{8}"', html)
    assert "assets/site.css" in artifact.paths()


def test_draft_content_never_builds() -> None:
    content = make_content()
    content.articles[0].status = ContentStatus.DRAFT
    artifact = build_site(CONFIG, content)
    assert not any("first-post" in path for path in artifact.paths())
