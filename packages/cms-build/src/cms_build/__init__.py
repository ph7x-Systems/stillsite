"""Deterministic static site generator."""

from cms_build.builder import Artifact, build_site
from cms_build.config import SiteConfig
from cms_build.head import Head, build_head
from cms_build.markdown import render_markdown
from cms_build.targets import Target, available_targets, create_target, register_target
from cms_build.themes import Theme, available_themes, create_theme, register_theme

__version__ = "0.1.0"

__all__ = [
    "Artifact",
    "Head",
    "SiteConfig",
    "Target",
    "Theme",
    "available_targets",
    "available_themes",
    "build_head",
    "build_site",
    "create_target",
    "create_theme",
    "register_target",
    "register_theme",
    "render_markdown",
]
