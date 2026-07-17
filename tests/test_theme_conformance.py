"""Theme conformance suite: the mechanical DESIGN_RULES checks, every theme.

Every shipped theme must pass unchanged; third-party themes are invited to
run this file against their own package (ECOSYSTEM.md listing gate).
"""

import re

import pytest
from cms_build import build_site, create_theme
from cms_build.themes import Theme
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
