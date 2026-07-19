"""Site configuration — the single source for everything configurable.

Application code never hardcodes URLs, language sets or names; it reads them
from here. Loaded from `sardine.toml` by the CLI, or constructed directly
in tests.
"""

from cms_core import SOURCE_LANGUAGE, TARGET_LANGUAGES, Language
from pydantic import BaseModel, Field, HttpUrl, JsonValue, field_validator

SLUG = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


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
    """When set, the footer links to the admin panel (dimmed, nofollow)."""

    def category_label(self, slug: str, language: Language) -> str:
        labels = self.categories.get(slug, {})
        return labels.get(language) or labels.get(SOURCE_LANGUAGE) or slug

    @field_validator("languages")
    @classmethod
    def _source_language_not_required(cls, value: tuple[Language, ...]) -> tuple[Language, ...]:
        return tuple(language for language in value if language is not SOURCE_LANGUAGE)

    @property
    def all_languages(self) -> tuple[Language, ...]:
        return (SOURCE_LANGUAGE, *self.languages)

    @property
    def root(self) -> str:
        return str(self.base_url).rstrip("/")
