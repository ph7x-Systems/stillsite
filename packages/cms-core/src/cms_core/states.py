"""Translation states and the editorial content workflow."""

from enum import StrEnum


class TranslationState(StrEnum):
    MISSING = "missing"
    OUTDATED = "outdated"
    COMPLETE = "complete"


class ContentStatus(StrEnum):
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    ARCHIVED = "archived"
