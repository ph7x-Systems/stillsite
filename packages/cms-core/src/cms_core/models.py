"""Article content model with per-language translations.

Translation freshness is tracked by checksum (see :mod:`cms_core.translatable`):
every translation records the checksum of the source (EN) content it was
translated from, so a source edit automatically marks translations outdated.
"""

import re
from datetime import UTC, datetime

from pydantic import Field, field_validator, model_validator

from cms_core.states import ContentStatus
from cms_core.translatable import ChecksummedContent, Seo, TranslatableModel

SCHEMA_VERSION = 2

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class ArticleContent(ChecksummedContent):
    title: str = Field(min_length=1)
    summary: str = ""
    body_markdown: str = ""
    slug: str | None = Field(default=None, pattern=SLUG_PATTERN)
    seo: Seo = Field(default_factory=Seo)

    def checksum_payload(self) -> tuple[str, ...]:
        base = (self.title, self.summary, self.body_markdown, self.slug or "")
        # A default Seo keeps the pre-ADR-0041 checksum: adding the
        # field must not flip existing translations to outdated.
        return base if self.seo.is_default else (*base, self.seo.checksum_fragment())


class Article(TranslatableModel[ArticleContent]):
    id: str = Field(pattern=SLUG_PATTERN)
    status: ContentStatus = ContentStatus.DRAFT
    created_at: datetime
    updated_at: datetime
    publish_at: datetime | None = None
    """UTC moment before which a published entry stays out of builds
    (ADR-0024); None publishes immediately once published."""
    unpublish_at: datetime | None = None
    """UTC moment after which a published entry leaves the builds
    (#133) — the symmetric end of ADR-0024's window. None means it
    stays. Must fall after ``publish_at`` when both are set."""
    deleted_at: datetime | None = None
    """Set = in the trash (ADR-0026): invisible to builds, validation,
    export and the admin lists until restored or purged."""
    category: str | None = Field(default=None, pattern=SLUG_PATTERN)

    @model_validator(mode="after")
    def _window_makes_sense(self) -> "Article":
        if (
            self.publish_at is not None
            and self.unpublish_at is not None
            and self.unpublish_at <= self.publish_at
        ):
            raise ValueError("unpublish_at must fall after publish_at")
        return self

    cover: str | None = Field(default=None, pattern=SLUG_PATTERN)
    tags: tuple[str, ...] = ()
    featured: bool = False
    """Pinned/priority content — themes decide the placement (M5)."""
    fields: dict[str, str] = Field(default_factory=dict)
    """Free-form custom fields (ADR-0028): the framework carries them,
    projects/extensions/themes agree on the keys."""
    author: str | None = None
    """Editorial byline (free text); themes render it when present."""

    @field_validator("tags")
    @classmethod
    def _tags_are_slugs(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        for tag in value:
            if not re.fullmatch(SLUG_PATTERN, tag):
                raise ValueError(f"tag {tag!r} is not a valid slug")
        return tuple(sorted(set(value)))


def new_article(article_id: str, source: ArticleContent, *, now: datetime | None = None) -> Article:
    timestamp = now or datetime.now(tz=UTC)
    return Article(id=article_id, created_at=timestamp, updated_at=timestamp, source=source)
