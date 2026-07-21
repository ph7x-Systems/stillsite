"""Explicit navigation menus (M6).

A menu item carries per-language labels and a URL (internal path or
external). When a project defines menu items, the builder renders exactly
them; when none exist, the menu derives from content as before (home
section anchors + blog + published pages) — nothing breaks by upgrading.
"""

from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

from cms_core.languages import SOURCE_LANGUAGE, Language

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


def validate_navigation_url(value: str) -> str:
    """Allow explicit web/contact links and safe site-relative references."""
    if not value or any(ord(char) <= 0x20 or ord(char) == 0x7F for char in value):
        raise ValueError("URL must not be empty or contain control/space characters")
    if "\\" in value:
        raise ValueError("URL must use forward slashes")
    if value.startswith("/"):
        if value.startswith("//") or ".." in urlsplit(value).path.split("/"):
            raise ValueError("site-relative URL must not be scheme-relative or traverse")
        return value
    if value.startswith("#"):
        return value
    parsed = urlsplit(value)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return value
    if parsed.scheme in {"mailto", "tel"} and parsed.path:
        return value
    raise ValueError("URL must be site-relative or use http, https, mailto or tel")


class MenuItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=SLUG_PATTERN)
    url: str = Field(min_length=1)
    position: int = 0
    labels: dict[Language, str] = Field(default_factory=dict)
    """Label per language; the source language is the fallback."""

    @field_validator("url")
    @classmethod
    def _safe_url(cls, value: str) -> str:
        return validate_navigation_url(value)

    def label(self, language: Language, source: Language | None = None) -> str:
        fallback = source if source is not None else SOURCE_LANGUAGE
        return self.labels.get(language) or self.labels.get(fallback) or self.id
