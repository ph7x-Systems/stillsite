"""Site configuration — the single source for everything configurable.

Application code never hardcodes URLs, language sets or names; it reads them
from here. Loaded from `stillsite.toml` by the CLI, or constructed directly
in tests.
"""

from cms_core import SOURCE_LANGUAGE, TARGET_LANGUAGES, Language
from pydantic import BaseModel, Field, HttpUrl, field_validator


class SiteConfig(BaseModel):
    name: str = Field(min_length=1)
    base_url: HttpUrl
    languages: tuple[Language, ...] = TARGET_LANGUAGES
    blog_path: str = Field(default="blog", pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    theme: str = "default"

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
