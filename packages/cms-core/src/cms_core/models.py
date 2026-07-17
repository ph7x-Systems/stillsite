"""Article content model with per-language translations.

Translation freshness is tracked by checksum (see :mod:`cms_core.translatable`):
every translation records the checksum of the source (EN) content it was
translated from, so a source edit automatically marks translations outdated.
"""

from datetime import UTC, datetime

from pydantic import Field

from cms_core.states import ContentStatus
from cms_core.translatable import ChecksummedContent, TranslatableModel

SCHEMA_VERSION = 2

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class ArticleContent(ChecksummedContent):
    title: str = Field(min_length=1)
    summary: str = ""
    body_markdown: str = ""
    slug: str | None = Field(default=None, pattern=SLUG_PATTERN)

    def checksum_payload(self) -> tuple[str, ...]:
        return (self.title, self.summary, self.body_markdown, self.slug or "")


class Article(TranslatableModel[ArticleContent]):
    id: str = Field(pattern=SLUG_PATTERN)
    status: ContentStatus = ContentStatus.DRAFT
    created_at: datetime
    updated_at: datetime


def new_article(article_id: str, source: ArticleContent, *, now: datetime | None = None) -> Article:
    timestamp = now or datetime.now(tz=UTC)
    return Article(id=article_id, created_at=timestamp, updated_at=timestamp, source=source)
