"""PoC-parity features: categories, tags, pagination, 404, JSON-LD, media,
theme overrides and the init scaffold."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cms_build import SiteConfig, build_site
from cms_build.themes.default import DefaultTheme
from cms_core import (
    Article,
    ArticleContent,
    ContentStatus,
    Language,
    MediaAsset,
    PageContent,
    Section,
    SectionContent,
    new_article,
    new_page,
)
from cms_core.storage import create_storage
from cms_validation import RuleSet, SiteContent, ValidationContext, default_ruleset

NOW = datetime(2026, 1, 15, 9, 0, tzinfo=UTC)

CONFIG = SiteConfig(
    name="Aurora",
    base_url="https://example.com",
    languages=(Language.PT_PT,),
    page_size=1,
    categories={"field-notes": {Language.EN: "Field notes", Language.PT_PT: "Notas de campo"}},
    organization={"@type": "Organization", "name": "Aurora"},
)


def make_article(article_id: str, *, days: int = 0, category: str | None = None) -> Article:
    article = new_article(
        article_id,
        ArticleContent(title=article_id.title(), summary="S", body_markdown="Body"),
        now=NOW + timedelta(days=days),
    )
    article.set_translation(Language.PT_PT, ArticleContent(title=f"{article_id}-pt", summary="S"))
    article.status = ContentStatus.PUBLISHED
    article.category = category
    return article


def make_content() -> SiteContent:
    home = new_page("home", PageContent(title="Home", description="D", slug="home"), now=NOW)
    home.set_translation(
        Language.PT_PT, PageContent(title="Início", description="D", slug="inicio")
    )
    home.status = ContentStatus.PUBLISHED
    first = make_article("alpha", days=0, category="field-notes")
    second = make_article("beta", days=1)
    second.tags = ("maps",)
    return SiteContent(pages=[home], articles=[first, second])


def test_pagination_splits_listing_pages() -> None:
    artifact = build_site(CONFIG, make_content())
    assert "blog/index.html" in artifact.paths()
    assert "blog/page/2/index.html" in artifact.paths()
    first = artifact.files["blog/index.html"].decode("utf-8")
    assert 'rel="next" href="/blog/page/2/"' in first
    second = artifact.files["blog/page/2/index.html"].decode("utf-8")
    assert 'rel="prev" href="/blog/"' in second


def test_category_page_uses_localized_label() -> None:
    artifact = build_site(CONFIG, make_content())
    en = artifact.files["blog/category/field-notes/index.html"].decode("utf-8")
    pt = artifact.files["pt-pt/blog/category/field-notes/index.html"].decode("utf-8")
    assert "Field notes" in en
    assert "Notas de campo" in pt


def test_tag_pages_exist_per_language() -> None:
    artifact = build_site(CONFIG, make_content())
    assert "blog/tag/maps/index.html" in artifact.paths()
    assert "pt-pt/blog/tag/maps/index.html" in artifact.paths()


def test_not_found_page_is_emitted_once_at_root() -> None:
    artifact = build_site(CONFIG, make_content())
    assert "404.html" in artifact.paths()
    assert not any(path.endswith("404.html") and path != "404.html" for path in artifact.paths())


def test_json_ld_on_home_and_articles() -> None:
    artifact = build_site(CONFIG, make_content())
    home = artifact.files["index.html"].decode("utf-8")
    assert '"@type": "Organization"' in home
    article = artifact.files["blog/alpha/index.html"].decode("utf-8")
    assert '"@type": "Article"' in article
    assert '"datePublished": "2026-01-15"' in article


def test_media_files_are_copied_and_referenced() -> None:
    asset = MediaAsset(
        id="hero-image",
        path="images/hero.svg",
        mime_type="image/svg+xml",
        width=100,
        height=50,
        alt={Language.EN: "Hero", Language.PT_PT: "Herói"},
    )
    home = new_page("home", PageContent(title="Home", description="D", slug="home"), now=NOW)
    home.set_translation(
        Language.PT_PT, PageContent(title="Início", description="D", slug="inicio")
    )
    hero = Section(key="hero", kind="hero", source=SectionContent(media=["hero-image"]))
    hero.set_translation(Language.PT_PT, SectionContent(media=["hero-image"]))
    home.sections.append(hero)
    home.status = ContentStatus.PUBLISHED
    content = SiteContent(pages=[home], media=[asset])
    artifact = build_site(CONFIG, content, media_files={"images/hero.svg": b"<svg/>"})
    assert artifact.files["media/images/hero.svg"] == b"<svg/>"
    html = artifact.files["index.html"].decode("utf-8")
    assert '<img src="/media/images/hero.svg" alt="Hero" width="100" height="50">' in html


def test_theme_template_and_asset_overrides(tmp_path: Path) -> None:
    (tmp_path / "templates").mkdir()
    (tmp_path / "assets").mkdir()
    (tmp_path / "templates" / "not_found.html.j2").write_text(
        "{% extends 'base.html.j2' %}{% block main %}<p>custom-404</p>{% endblock %}",
        encoding="utf-8",
    )
    (tmp_path / "assets" / "site.css").write_text(":root { --bg: black; }", encoding="utf-8")
    theme = DefaultTheme(overrides=tmp_path)
    artifact = build_site(CONFIG, make_content(), theme=theme)
    assert "custom-404" in artifact.files["404.html"].decode("utf-8")
    assert artifact.files["assets/site.css"] == b":root { --bg: black; }"


def test_unknown_category_fails_validation() -> None:
    content = SiteContent(articles=[make_article("alpha", category="nope")])
    context = ValidationContext(
        required_languages=(Language.PT_PT,), known_categories=("field-notes",)
    )
    report = RuleSet(rules=default_ruleset()).run(content, context)
    assert any(issue.code == "known-categories" for issue in report.errors)


def test_article_tags_validated_and_persisted(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not a valid slug"):
        Article(
            id="post",
            created_at=NOW,
            updated_at=NOW,
            source=ArticleContent(title="P"),
            tags=("Bad Tag",),
        )

    backend = create_storage(f"sqlite:///{tmp_path / 'cms.sqlite3'}")
    article = make_article("gamma", category="field-notes")
    article.tags = ("zulu", "alpha")
    backend.save_article(article)
    loaded = backend.load_article("gamma")
    assert loaded is not None
    assert loaded.category == "field-notes"
    assert loaded.tags == ("alpha", "zulu")


def test_search_index_carries_category_label() -> None:
    artifact = build_site(CONFIG, make_content())
    index = json.loads(artifact.files["pt-pt/blog/search-index.json"])
    labels = {entry["c"] for entry in index}
    assert "Notas de campo" in labels
