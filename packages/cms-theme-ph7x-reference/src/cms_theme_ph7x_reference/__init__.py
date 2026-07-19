"""Sardine CMS reference theme (dark editorial design system)."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _dist_version
from pathlib import Path

from cms_build.themes.jinja import JinjaTheme

try:
    __version__ = _dist_version("sardine-cms-theme-ph7x-reference")
except PackageNotFoundError:  # running from a source tree without install
    __version__ = "0+unknown"


class ReferenceTheme(JinjaTheme):
    """Layers over the default theme: only changed templates/assets ship here."""

    name = "ph7x-reference"

    def __init__(self, overrides: Path | None = None) -> None:
        super().__init__(
            layers=("cms_theme_ph7x_reference", "cms_build.themes.default"),
            overrides=overrides,
        )
