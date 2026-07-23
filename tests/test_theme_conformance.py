"""Certification: both bundled themes pass the public conformance
contract (ADR-0053) — plus repo-specific checks that are not part of it."""

from pathlib import Path

import pytest
from cms_build import build_site, create_theme
from cms_build.theme_conformance import (
    conformance_checks,
    physical_offenders,
    sample_config,
    sample_content,
)
from cms_build.themes import Theme

THEMES = ("default", "ph7x-reference")

CONFIG = sample_config()
make_content = sample_content


@pytest.fixture(params=THEMES)
def theme(request: pytest.FixtureRequest) -> Theme:
    return create_theme(request.param)


@pytest.mark.parametrize(("check_name", "check"), conformance_checks())
def test_bundled_themes_are_certified(theme: Theme, check_name: str, check: object) -> None:
    """Every bundled theme passes every check of the public contract —
    the suite is proven useful, not theoretical."""
    check(theme)  # type: ignore[operator]


def test_comments_contract_renders_in_both_themes(theme: Theme) -> None:
    """ADR-0031: with a provider configured, every article gets the no-JS
    link plus the same-origin island — and nothing references a third
    party at load time."""
    from cms_build import CommentsSettings
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


def test_admin_css_is_flow_relative() -> None:
    """The panel holds the same bar (vendored bundles excluded — they are
    upstream's). Overriding a vendored *physical* property is the one
    licit use of one: the override must name what upstream names."""
    import cms_admin

    css_path = Path(cms_admin.__file__).parent / "static" / "admin.css"
    allowed = {"border-left-color", "border-right-color"}  # EasyMDE/CodeMirror overrides
    found = physical_offenders(css_path.read_text(encoding="utf-8"))
    offenders = [offender for offender in found if offender not in allowed]
    assert not offenders, offenders
