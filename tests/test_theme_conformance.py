"""Theme conformance suite: the mechanical DESIGN_RULES checks, every theme.

Every shipped theme must pass unchanged; third-party themes are invited to
run this file against their own package (ECOSYSTEM.md listing gate).
"""

import re
from pathlib import Path

import pytest
from cms_build import build_site, create_theme
from cms_build.themes import Theme
from cms_core.pages import Section
from test_output_integrity import CONFIG, make_content

THEMES = ("default", "ph7x-reference")

JS_BUDGET_BYTES = 20 * 1024  # DESIGN_RULES §5


@pytest.fixture(params=THEMES)
def theme(request: pytest.FixtureRequest) -> Theme:
    return create_theme(request.param)


def _css_assets(theme: Theme) -> dict[str, str]:
    return {
        path: data.decode("utf-8") for path, data in theme.assets().items() if path.endswith(".css")
    }


def test_hidden_rule_is_first(theme: Theme) -> None:
    css = _css_assets(theme)["assets/site.css"]
    stripped = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL).lstrip()
    assert re.match(r"\[hidden\]\s*\{\s*display:\s*none\s*!important;?\s*\}", stripped), theme.name


def test_no_external_requests_in_assets(theme: Theme) -> None:
    # XML namespace identifiers (xmlns) are not network requests.
    namespace_only = re.compile(r"^http://www\.w3\.org/")
    for path, data in theme.assets().items():
        if path.endswith((".css", ".js")):
            text = data.decode("utf-8")
            for match in re.findall(r"https?://[^\s\"')<]+", text):
                if not namespace_only.match(match):
                    pytest.fail(f"{theme.name}:{path} references external URL {match}")


def test_no_inline_styles_in_rendered_pages(theme: Theme) -> None:
    artifact = build_site(CONFIG, make_content(), theme=theme)
    for path in artifact.paths():
        if path.endswith(".html"):
            html = artifact.files[path].decode("utf-8")
            assert 'style="' not in html, f"{theme.name}:{path} has inline styles"


def test_images_carry_dimensions(theme: Theme) -> None:
    artifact = build_site(CONFIG, make_content(), theme=theme)
    for path in artifact.paths():
        if not path.endswith(".html"):
            continue
        html = artifact.files[path].decode("utf-8")
        for tag in re.findall(r"<img [^>]+>", html):
            assert 'width="' in tag and 'height="' in tag, f"{theme.name}:{path}: {tag}"


def test_animations_honor_reduced_motion(theme: Theme) -> None:
    for path, css in _css_assets(theme).items():
        if "@keyframes" in css or "animation-timeline" in css:
            assert "prefers-reduced-motion" in css, f"{theme.name}:{path}"


def test_javascript_budget(theme: Theme) -> None:
    total = sum(len(data) for path, data in theme.assets().items() if path.endswith(".js"))
    assert total <= JS_BUDGET_BYTES, f"{theme.name}: {total} bytes of JS"


def test_font_urls_resolve_to_shipped_assets(theme: Theme) -> None:
    assets = theme.assets()
    for path, css in _css_assets(theme).items():
        base = path.rsplit("/", 1)[0]
        for reference in re.findall(r"url\(\"?([^\")]+\.woff2)\"?\)", css):
            resolved = f"{base}/{reference}"
            assert resolved in assets, f"{theme.name}: {resolved} not shipped"


def test_local_references_resolve_with_this_theme(theme: Theme) -> None:
    from test_output_integrity import _LOCAL_REF, _resolves

    artifact = build_site(CONFIG, make_content(), theme=theme)
    paths = set(artifact.paths())
    for path in artifact.paths():
        if not path.endswith(".html"):
            continue
        html = artifact.files[path].decode("utf-8")
        for reference in _LOCAL_REF.findall(html):
            assert _resolves(reference, paths), f"{theme.name}:{path}: {reference}"


def test_gallery_kinds_render_every_advertised_field(theme: Theme) -> None:
    """THEME_GUIDE: the bundled gallery is a real contract — each kind's
    advertised fields all reach the rendered page, in both bundled themes."""
    from datetime import UTC, datetime

    from cms_build import build_site
    from cms_build.themes import SECTION_KIND_GALLERY
    from cms_core import (
        ContentStatus,
        Language,
        MediaAsset,
        PageContent,
        Section,
        SectionContent,
        new_page,
    )
    from cms_validation import SiteContent

    now = datetime(2026, 1, 15, 9, 0, tzinfo=UTC)
    page = new_page(
        "showcase", PageContent(title="Showcase", description="D", slug="showcase"), now=now
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
    artifact = build_site(CONFIG, SiteContent(pages=[page], media=[shot]), theme=theme)
    html = artifact.files["showcase/index.html"].decode("utf-8")
    for sentinel in expected:
        assert sentinel in html, (theme.name, sentinel)
    assert "XKgalleryimagealtQZ" in html, theme.name  # gallery renders its media


def test_unknown_section_kinds_degrade_gracefully(theme: Theme) -> None:
    """THEME_GUIDE: a kind the theme has never heard of still renders its
    fields generically — extensions can invent kinds without crashing."""
    from datetime import UTC, datetime

    from cms_build import build_site
    from cms_core import ContentStatus, PageContent, Section, SectionContent, new_page
    from cms_validation import SiteContent

    now = datetime(2026, 1, 15, 9, 0, tzinfo=UTC)
    page = new_page("odd", PageContent(title="Odd", description="D", slug="odd"), now=now)
    page.sections.append(
        Section(
            key="mystery",
            kind="mystery-widget",
            source=SectionContent(fields={"note": "XKmysterynoteQZ"}),
        )
    )
    page.status = ContentStatus.PUBLISHED
    artifact = build_site(CONFIG, SiteContent(pages=[page]), theme=theme)
    html = artifact.files["odd/index.html"].decode("utf-8")
    assert "XKmysterynoteQZ" in html, theme.name
    assert "section-mystery-widget" in html, theme.name


def test_comments_contract_renders_in_both_themes(theme: Theme) -> None:
    """ADR-0031: with a provider configured, every article gets the no-JS
    link plus the same-origin island — and nothing references a third
    party at load time."""
    from cms_build import CommentsSettings, build_site
    from cms_build.builder import COMMENTS_ISLAND_PATH
    from cms_core import CommentsProvider

    config = CONFIG.model_copy(
        update={"comments": CommentsSettings(provider="fishbowl", url="https://discuss.example")}
    )
    provider = CommentsProvider(
        island_js=b"customElements.define('site-comments', class extends HTMLElement {});\n",
        thread_url=lambda base, page: f"{base.rstrip('/')}/threads?page={page}",
    )
    artifact = build_site(config, make_content(), theme=theme, comments_provider=provider)
    assert artifact.files[COMMENTS_ISLAND_PATH] == provider.island_js
    article = artifact.files["blog/alpha/index.html"].decode("utf-8")
    assert "https://discuss.example/threads?page=" in article
    assert "<site-comments" in article
    assert f'type="module" src="/{COMMENTS_ISLAND_PATH}?v=' in article
    assert 'script type="module" src="https://' not in article


PHYSICAL_CSS = re.compile(
    r"(?:margin|padding|border)-(?:left|right)(?:-[a-z]+)*\b"
    r"|text-align:\s*(?:left|right)\b"
    r"|float:\s*(?:left|right)\b"
    r"|(?<![-a-z])(?:left|right)\s*:"
)
ASYMMETRIC_SHORTHAND = re.compile(
    r"(?:margin|padding):\s*([^;}\s]+)\s+([^;}\s]+)\s+([^;}\s]+)\s+([^;}\s]+)\s*[;}]"
)


def _physical_offenders(css: str) -> list[str]:
    stripped = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    offenders = [match.group(0) for match in PHYSICAL_CSS.finditer(stripped)]
    offenders += [
        match.group(0).rstrip(";}").strip()
        for match in ASYMMETRIC_SHORTHAND.finditer(stripped)
        if match.group(2) != match.group(4)
    ]
    return offenders


def test_css_is_flow_relative(theme: Theme) -> None:
    """ADR-0034: any pack may declare ``rtl``, so themes may not encode
    writing direction — logical properties only (``margin-inline-start``,
    ``text-align: start``, ``inset-inline-end`` …), and no four-value
    margin/padding shorthand with different start/end values."""
    for path, css in _css_assets(theme).items():
        offenders = _physical_offenders(css)
        assert not offenders, (theme.name, path, offenders)


def test_admin_css_is_flow_relative() -> None:
    """The panel holds the same bar (vendored bundles excluded — they are
    upstream's). Overriding a vendored *physical* property is the one
    licit use of one: the override must name what upstream names."""
    import cms_admin

    css_path = Path(cms_admin.__file__).parent / "static" / "admin.css"
    allowed = {"border-left-color", "border-right-color"}  # EasyMDE/CodeMirror overrides
    found = _physical_offenders(css_path.read_text(encoding="utf-8"))
    offenders = [offender for offender in found if offender not in allowed]
    assert not offenders, offenders


def _built_page(theme: Theme, section: "Section | None", body_markdown: str = "") -> str:
    from cms_core import ContentStatus
    from cms_core.pages import PageContent, new_page
    from cms_validation import SiteContent
    from test_output_integrity import NOW

    page = new_page(
        "probe",
        PageContent(title="Probe", slug="probe", body_markdown=body_markdown),
        now=NOW,
    )
    if section is not None:
        page.sections.append(section)
    page.status = ContentStatus.PUBLISHED
    base = make_content()
    content = SiteContent(
        articles=base.articles, pages=[*base.pages, page], media=base.media, menu=base.menu
    )
    artifact = build_site(CONFIG, content, theme=theme)
    return artifact.files["probe/index.html"].decode("utf-8")


def test_section_items_render_unbounded(theme: Theme) -> None:
    """ADR-0037: repetition has no cap — a 10-item FAQ renders all 10.
    The old numbered convention stopped at six."""
    from cms_core.pages import Section, SectionContent

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


def test_legacy_numbered_fields_still_render(theme: Theme) -> None:
    """Pre-items content keeps rendering: numbered fields map into the
    items group at render time — beyond the old template caps too."""
    from cms_core.pages import Section, SectionContent

    fields = {"heading": "Questions"}
    for n in range(1, 8):
        fields[f"q{n}"] = f"Old question {n}?"
        fields[f"a{n}"] = f"Old answer {n}."
    html = _built_page(theme, Section(key="faq", kind="faq", source=SectionContent(fields=fields)))
    for n in range(1, 8):
        assert f"Old question {n}?" in html, (theme.name, n)


def test_markdown_fields_render_safely(theme: Theme) -> None:
    """A kind's declared Markdown fields render through the safe
    renderer: emphasis works, raw HTML never survives."""
    from cms_core.pages import Section, SectionContent

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


def test_page_body_renders_as_prose(theme: Theme) -> None:
    """ADR-0037: a page can be a document — body_markdown renders
    between the header and the sections."""
    html = _built_page(theme, None, body_markdown="Long-form **prose** here.")
    assert "<strong>prose</strong>" in html, theme.name
