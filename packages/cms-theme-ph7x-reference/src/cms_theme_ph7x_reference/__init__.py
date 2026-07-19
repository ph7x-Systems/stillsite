"""Sardine CMS reference theme (dark editorial design system)."""

from pathlib import Path

from cms_build.themes.jinja import JinjaTheme

__version__ = "0.1.0"


class ReferenceTheme(JinjaTheme):
    """Layers over the default theme: only changed templates/assets ship here."""

    name = "ph7x-reference"

    def __init__(self, overrides: Path | None = None) -> None:
        super().__init__(
            layers=("cms_theme_ph7x_reference", "cms_build.themes.default"),
            overrides=overrides,
        )
