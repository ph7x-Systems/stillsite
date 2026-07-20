"""Site configuration — the single source for everything configurable.

Application code never hardcodes URLs, language sets or names; it reads them
from here. Loaded from `sardine.toml` by the CLI, or constructed directly
in tests.
"""

import re
from urllib.parse import urlsplit

from cms_core import SOURCE_LANGUAGE, TARGET_LANGUAGES, Language
from cms_core.menus import validate_navigation_url
from pydantic import BaseModel, Field, HttpUrl, JsonValue, field_validator

SLUG = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class CommentsSettings(BaseModel):
    """The ``[comments]`` table (ADR-0031): which extension-registered
    provider carries the discussions, and where they live. HTTPS only —
    a comments endpoint is third-party code territory."""

    provider: str = Field(min_length=1)
    url: HttpUrl

    @field_validator("url")
    @classmethod
    def _https_only(cls, value: HttpUrl) -> HttpUrl:
        if value.scheme != "https":
            raise ValueError("the comments URL must use https")
        return value


class SiteConfig(BaseModel):
    name: str = Field(min_length=1)
    base_url: HttpUrl
    languages: tuple[Language, ...] = TARGET_LANGUAGES
    blog_path: str = Field(default="blog", pattern=SLUG)
    theme: str = "default"
    page_size: int = Field(default=10, ge=1)
    categories: dict[str, dict[Language, str]] = Field(default_factory=dict)
    labels: dict[str, dict[Language, str]] = Field(default_factory=dict)
    organization: dict[str, JsonValue] | None = None
    footer_text: str | None = None
    """Footer line (e.g. a copyright notice); the site name when unset."""
    admin_url: str | None = None
    image_widths: tuple[int, ...] = ()
    """Responsive derivative widths (ADR-0029); empty disables."""
    redirects: dict[str, str] = Field(default_factory=dict)
    """Old path -> new URL (M6): targets emit real 301s, the builder
    ships meta-refresh fallback pages so every host redirects."""
    comments: CommentsSettings | None = None
    """ADR-0031: absent means no comments anywhere — builds are
    byte-identical to a comments-less configuration."""
    """When set, the footer links to the admin panel (dimmed, nofollow)."""

    def category_label(self, slug: str, language: Language) -> str:
        labels = self.categories.get(slug, {})
        return labels.get(language) or labels.get(SOURCE_LANGUAGE) or slug

    @field_validator("languages")
    @classmethod
    def _source_language_not_required(cls, value: tuple[Language, ...]) -> tuple[Language, ...]:
        return tuple(language for language in value if language is not SOURCE_LANGUAGE)

    @field_validator("admin_url")
    @classmethod
    def _safe_admin_url(cls, value: str | None) -> str | None:
        return validate_navigation_url(value) if value is not None else None

    @field_validator("redirects")
    @classmethod
    def _safe_redirects(cls, value: dict[str, str]) -> dict[str, str]:
        safe_source = re.compile(r"^/[A-Za-z0-9._~!()*+,=:@%/-]*$")
        unsafe_destination = re.compile(r"[\s\\;{}\"'$]")
        for source, destination in value.items():
            source_path = urlsplit(source).path
            if (
                not safe_source.fullmatch(source)
                or source.startswith("//")
                or ".." in source_path.split("/")
            ):
                raise ValueError(f"unsafe redirect source {source!r}")
            validate_navigation_url(destination)
            parsed = urlsplit(destination)
            if parsed.scheme not in {"", "http", "https"} or destination.startswith("#"):
                raise ValueError(f"unsafe redirect destination {destination!r}")
            if unsafe_destination.search(destination):
                raise ValueError(f"unsafe redirect destination {destination!r}")
        return value

    @property
    def all_languages(self) -> tuple[Language, ...]:
        return (SOURCE_LANGUAGE, *self.languages)

    @property
    def root(self) -> str:
        return str(self.base_url).rstrip("/")
