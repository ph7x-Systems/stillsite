"""Deterministic static site generator."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _dist_version

from cms_build.builder import Artifact, build_entry_preview, build_site
from cms_build.config import CommentsSettings, SiteConfig
from cms_build.head import Head, build_head
from cms_build.markdown import render_markdown
from cms_build.targets import Target, available_targets, create_target, register_target
from cms_build.themes import Theme, available_themes, create_theme, register_theme

try:
    __version__ = _dist_version("sardine-cms-build")
except PackageNotFoundError:  # running from a source tree without install
    __version__ = "0+unknown"

__all__ = [
    "Artifact",
    "CommentsSettings",
    "Head",
    "SiteConfig",
    "Target",
    "Theme",
    "available_targets",
    "available_themes",
    "build_entry_preview",
    "build_head",
    "build_site",
    "create_target",
    "create_theme",
    "register_target",
    "register_theme",
    "render_markdown",
]
