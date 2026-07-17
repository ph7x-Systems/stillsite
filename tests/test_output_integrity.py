"""Anti-drift for generated HTML/CSS/JS: every local reference must resolve.

Walks the built artifact and asserts that every local href/src in HTML and
every url() in CSS points at a file that actually exists in the artifact —
a broken stylesheet path, image or internal link fails the build's tests
instead of shipping.
"""

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
    name="Aurora",
    base_url="https://example.com",
    languages=(Language.PT_PT, Language.DE),
    page_size=1,
    categories={"field-notes": {Language.EN: "Field notes"}},
    organization={"@type": "Organization", "name": "Aurora"},
)

_LOCAL_REF = re.compile(r'(?:href|src)="(/[^"]*)"')
_CSS_URL = re.compile(r"url\(['\"]?(/[^'\")]+)['\"]?\)")


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
    articles = []
    for slug in ("alpha", "beta"):
        article = new_article(
            slug,
            ArticleContent(title=slug.title(), summary="S", body_markdown="Body"),
            now=NOW,
        )
        article.set_translation(Language.PT_PT, ArticleContent(title=f"{slug}-pt", summary="S"))
        article.set_translation(Language.DE, ArticleContent(title=f"{slug}-de", summary="S"))
        article.status = ContentStatus.PUBLISHED
        article.category = "field-notes"
        article.tags = ("maps",)
        articles.append(article)
    return SiteContent(pages=[home], articles=articles)


def test_fixture_content_is_valid() -> None:
    """The integrity fixture must represent a validated site — the builder's
    reference-completeness guarantees hold for content that passes validation."""
    from cms_validation import RuleSet, ValidationContext, default_ruleset

    context = ValidationContext(
        required_languages=CONFIG.languages, known_categories=tuple(CONFIG.categories)
    )
    report = RuleSet(rules=default_ruleset()).run(make_content(), context)
    assert report.ok, [str(issue) for issue in report.issues]


def _resolves(path: str, paths: set[str]) -> bool:
    clean = path.split("?", 1)[0].split("#", 1)[0]
    candidates = [clean.lstrip("/")]
    if clean.endswith("/"):
        candidates = [f"{clean.lstrip('/')}index.html"]
    return any(candidate in paths for candidate in candidates)


def test_every_local_reference_in_html_resolves() -> None:
    artifact = build_site(CONFIG, make_content())
    paths = set(artifact.paths())
    checked = 0
    for path in artifact.paths():
        if not path.endswith(".html"):
            continue
        html = artifact.files[path].decode("utf-8")
        for reference in _LOCAL_REF.findall(html):
            assert _resolves(reference, paths), f"{path}: broken local reference {reference}"
            checked += 1
    assert checked > 0


def test_every_css_url_resolves() -> None:
    artifact = build_site(CONFIG, make_content())
    paths = set(artifact.paths())
    for path in artifact.paths():
        if not path.endswith(".css"):
            continue
        css = artifact.files[path].decode("utf-8")
        for reference in _CSS_URL.findall(css):
            assert _resolves(reference, paths), f"{path}: broken url() reference {reference}"


def test_templates_only_reference_existing_theme_assets() -> None:
    from importlib import resources

    templates_dir = resources.files("cms_build.themes.default") / "templates"
    from cms_build import create_theme

    theme_assets = set(create_theme("default").assets())
    referenced = set()
    for entry in templates_dir.iterdir():
        if entry.name.endswith(".j2"):
            referenced.update(re.findall(r"asset_urls\['([^']+)'\]", entry.read_text()))
    assert referenced, "no asset references found in templates"
    missing = referenced - theme_assets
    assert not missing, f"templates reference missing theme assets: {sorted(missing)}"
