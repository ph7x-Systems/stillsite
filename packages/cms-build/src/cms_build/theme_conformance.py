"""The theme conformance suite as a public contract (ADR-0053).

This module defines, executably, what "being a Sardine theme" means.
Every bundled theme passes it unchanged; third-party themes prove
conformance by running it against their own package:

    import pytest
    from cms_build import create_theme
    from cms_build.theme_conformance import conformance_checks

    @pytest.mark.parametrize(("name", "check"), conformance_checks())
    def test_conformance(name, check):
        check(create_theme("my-theme"))

The checks build a small fictional site; no network, no filesystem.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import UTC, datetime

from cms_core import ContentStatus, Language, MediaAsset
from cms_core.models import ArticleContent, new_article
from cms_core.pages import PageContent, Section, SectionContent, new_page
from cms_validation import SiteContent

from cms_build import build_site
from cms_build.config import SiteConfig
from cms_build.themes import SECTION_KIND_GALLERY, Theme

CONFORMANCE_VERSION = 1

JS_BUDGET_BYTES = 20 * 1024  # DESIGN_RULES §5

NOW = datetime(2026, 1, 15, 9, 0, tzinfo=UTC)

_LOCAL_REF = re.compile(r'(?:href|src)="(/[^"]*)"')


def sample_config() -> SiteConfig:
    return SiteConfig(
        name="Aurora",
        base_url="https://example.com",
        languages=(Language.PT_PT, Language.DE),
        page_size=1,
        categories={"field-notes": {Language.EN: "Field notes"}},
        organization={"@type": "Organization", "name": "Aurora"},
        forms_endpoint="https://forms.example/submit",
    )


def sample_content() -> SiteContent:
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
            slug, ArticleContent(title=slug.title(), summary="S", body_markdown="Body"), now=NOW
        )
        article.set_translation(Language.PT_PT, ArticleContent(title=f"{slug}-pt", summary="S"))
        article.set_translation(Language.DE, ArticleContent(title=f"{slug}-de", summary="S"))
        article.status = ContentStatus.PUBLISHED
        article.category = "field-notes"
        article.tags = ("maps",)
        articles.append(article)
    return SiteContent(pages=[home], articles=articles)


def _css_assets(theme: Theme) -> dict[str, str]:
    return {
        path: data.decode("utf-8") for path, data in theme.assets().items() if path.endswith(".css")
    }


def _resolves(path: str, paths: set[str]) -> bool:
    clean = path.split("?", 1)[0].split("#", 1)[0]
    candidates = [clean.lstrip("/")]
    if clean.endswith("/"):
        candidates = [f"{clean.lstrip('/')}index.html"]
    return any(candidate in paths for candidate in candidates)


def _built_page(theme: Theme, section: Section | None, body_markdown: str = "") -> str:
    page = new_page(
        "probe", PageContent(title="Probe", slug="probe", body_markdown=body_markdown), now=NOW
    )
    if section is not None:
        page.sections.append(section)
    page.status = ContentStatus.PUBLISHED
    base = sample_content()
    content = SiteContent(
        articles=base.articles, pages=[*base.pages, page], media=base.media, menu=base.menu
    )
    artifact = build_site(sample_config(), content, theme=theme)
    return artifact.files["probe/index.html"].decode("utf-8")


def check_hidden_rule_is_first(theme: Theme) -> None:
    css = _css_assets(theme)["assets/site.css"]
    stripped = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL).lstrip()
    assert re.match(r"\[hidden\]\s*\{\s*display:\s*none\s*!important;?\s*\}", stripped), theme.name


def check_no_external_requests_in_assets(theme: Theme) -> None:
    namespace_only = re.compile(r"^http://www\.w3\.org/")
    for path, data in theme.assets().items():
        if path.endswith((".css", ".js")):
            text = data.decode("utf-8")
            for match in re.findall(r"https?://[^\s\"')<]+", text):
                assert namespace_only.match(match), f"{theme.name}:{path} references {match}"


def check_no_inline_styles(theme: Theme) -> None:
    artifact = build_site(sample_config(), sample_content(), theme=theme)
    for path in artifact.paths():
        if path.endswith(".html"):
            html = artifact.files[path].decode("utf-8")
            assert 'style="' not in html, f"{theme.name}:{path} has inline styles"


def check_images_carry_dimensions(theme: Theme) -> None:
    artifact = build_site(sample_config(), sample_content(), theme=theme)
    for path in artifact.paths():
        if not path.endswith(".html"):
            continue
        html = artifact.files[path].decode("utf-8")
        for tag in re.findall(r"<img [^>]+>", html):
            assert 'width="' in tag and 'height="' in tag, f"{theme.name}:{path}: {tag}"


def check_animations_honor_reduced_motion(theme: Theme) -> None:
    for path, css in _css_assets(theme).items():
        if "@keyframes" in css or "animation-timeline" in css:
            assert "prefers-reduced-motion" in css, f"{theme.name}:{path}"


def check_javascript_budget(theme: Theme) -> None:
    total = sum(len(data) for path, data in theme.assets().items() if path.endswith(".js"))
    assert total <= JS_BUDGET_BYTES, f"{theme.name}: {total} bytes of JS"


def check_font_urls_resolve(theme: Theme) -> None:
    assets = theme.assets()
    for path, css in _css_assets(theme).items():
        base = path.rsplit("/", 1)[0]
        for reference in re.findall(r"url\(\"?([^\")]+\.woff2)\"?\)", css):
            resolved = f"{base}/{reference}"
            assert resolved in assets, f"{theme.name}: {resolved} not shipped"


def check_local_references_resolve(theme: Theme) -> None:
    artifact = build_site(sample_config(), sample_content(), theme=theme)
    paths = set(artifact.paths())
    for path in artifact.paths():
        if not path.endswith(".html"):
            continue
        html = artifact.files[path].decode("utf-8")
        for reference in _LOCAL_REF.findall(html):
            assert _resolves(reference, paths), f"{theme.name}:{path}: {reference}"


def check_gallery_kinds_render_every_field(theme: Theme) -> None:
    page = new_page(
        "showcase", PageContent(title="Showcase", description="D", slug="showcase"), now=NOW
    )
    expected: list[str] = []
    for kind, fields in SECTION_KIND_GALLERY.items():
        data: dict[str, str] = {}
        for name in fields:
            sentinel = f"XK{kind}{name}QZ".replace("-", "")
            data[name] = sentinel
            expected.append(sentinel)
        media = ["shot"] if kind == "gallery" else []
        page.sections.append(
            Section(key=f"s-{kind}", kind=kind, source=SectionContent(fields=data, media=media))
        )
    page.status = ContentStatus.PUBLISHED
    shot = MediaAsset(
        id="shot",
        path="images/shot.svg",
        mime_type="image/svg+xml",
        width=1200,
        height=675,
        alt={Language.EN: "XKgalleryimagealtQZ"},
    )
    artifact = build_site(sample_config(), SiteContent(pages=[page], media=[shot]), theme=theme)
    html = artifact.files["showcase/index.html"].decode("utf-8")
    for sentinel in expected:
        assert sentinel in html, (theme.name, sentinel)
    assert "XKgalleryimagealtQZ" in html, theme.name


def check_unknown_kinds_degrade_gracefully(theme: Theme) -> None:
    page = new_page("odd", PageContent(title="Odd", description="D", slug="odd"), now=NOW)
    page.sections.append(
        Section(
            key="mystery",
            kind="mystery-widget",
            source=SectionContent(fields={"note": "XKmysterynoteQZ"}),
        )
    )
    page.status = ContentStatus.PUBLISHED
    artifact = build_site(sample_config(), SiteContent(pages=[page]), theme=theme)
    html = artifact.files["odd/index.html"].decode("utf-8")
    assert "XKmysterynoteQZ" in html, theme.name
    assert "section-mystery-widget" in html, theme.name


PHYSICAL_CSS = re.compile(
    r"(?:margin|padding|border)-(?:left|right)(?:-[a-z]+)*\b"
    r"|text-align:\s*(?:left|right)\b"
    r"|float:\s*(?:left|right)\b"
    r"|(?<![-a-z])(?:left|right)\s*:"
)
ASYMMETRIC_SHORTHAND = re.compile(
    r"(?:margin|padding):\s*([^;}\s]+)\s+([^;}\s]+)\s+([^;}\s]+)\s+([^;}\s]+)\s*[;}]"
)


def physical_offenders(css: str) -> list[str]:
    stripped = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    offenders = [match.group(0) for match in PHYSICAL_CSS.finditer(stripped)]
    offenders += [
        match.group(0).rstrip(";}").strip()
        for match in ASYMMETRIC_SHORTHAND.finditer(stripped)
        if match.group(2) != match.group(4)
    ]
    return offenders


def check_css_is_flow_relative(theme: Theme) -> None:
    for path, css in _css_assets(theme).items():
        offenders = physical_offenders(css)
        assert not offenders, (theme.name, path, offenders)


def check_section_items_render_unbounded(theme: Theme) -> None:
    faq = Section(
        key="faq",
        kind="faq",
        source=SectionContent(
            fields={"heading": "Questions"},
            items=[{"question": f"Question {n}?", "answer": f"Answer {n}."} for n in range(1, 11)],
        ),
    )
    html = _built_page(theme, faq)
    for n in range(1, 11):
        assert f"Question {n}?" in html, (theme.name, n)


def check_legacy_numbered_fields_render(theme: Theme) -> None:
    fields = {"heading": "Questions"}
    for n in range(1, 8):
        fields[f"q{n}"] = f"Old question {n}?"
        fields[f"a{n}"] = f"Old answer {n}."
    html = _built_page(theme, Section(key="faq", kind="faq", source=SectionContent(fields=fields)))
    for n in range(1, 8):
        assert f"Old question {n}?" in html, (theme.name, n)


def check_markdown_fields_render_safely(theme: Theme) -> None:
    story = Section(
        key="story",
        kind="story",
        source=SectionContent(
            fields={"heading": "H", "body": "A **bold** [link](/x) <script>alert(1)</script>"}
        ),
    )
    html = _built_page(theme, story)
    assert "<strong>bold</strong>" in html, theme.name
    assert '<a href="/x">link</a>' in html, theme.name
    assert "<script>alert(1)</script>" not in html, theme.name


def check_page_body_renders_as_prose(theme: Theme) -> None:
    html = _built_page(theme, None, body_markdown="Long-form **prose** here.")
    assert "<strong>prose</strong>" in html, theme.name


def conformance_checks() -> tuple[tuple[str, Callable[[Theme], None]], ...]:
    """Every check in the contract, named — parametrize your tests over
    this and run each against your theme."""
    return (
        ("hidden-rule-first", check_hidden_rule_is_first),
        ("no-external-requests", check_no_external_requests_in_assets),
        ("no-inline-styles", check_no_inline_styles),
        ("images-carry-dimensions", check_images_carry_dimensions),
        ("reduced-motion", check_animations_honor_reduced_motion),
        ("javascript-budget", check_javascript_budget),
        ("fonts-resolve", check_font_urls_resolve),
        ("local-references-resolve", check_local_references_resolve),
        ("gallery-kinds-render", check_gallery_kinds_render_every_field),
        ("unknown-kinds-degrade", check_unknown_kinds_degrade_gracefully),
        ("css-flow-relative", check_css_is_flow_relative),
        ("items-unbounded", check_section_items_render_unbounded),
        ("legacy-numbered-fields", check_legacy_numbered_fields_render),
        ("markdown-fields-safe", check_markdown_fields_render_safely),
        ("page-body-prose", check_page_body_renders_as_prose),
    )
