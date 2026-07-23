"""A fixture extension for the Extensions screen tests."""

from cms_core.extensions import Extension

extension = Extension(name="fixture", section_kinds={"fixture-hero": ("title", "body")})
