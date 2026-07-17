"""Article content model with per-language translations.

Translation freshness is tracked by checksum: every translation records the
checksum of the source (EN) content it was translated from. When the source
changes, the recorded checksum no longer matches and the translation becomes
``outdated`` without any manual bookkeeping.
"""

import hashlib
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from cms_core.languages import SOURCE_LANGUAGE, TARGET_LANGUAGES, Language
from cms_core.states import ContentStatus, TranslationState

SCHEMA_VERSION = 1

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class ArticleContent(BaseModel):
    title: str = Field(min_length=1)
    summary: str = ""
    body_markdown: str = ""

    def checksum(self) -> str:
        payload = "\x1f".join((self.title, self.summary, self.body_markdown))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class Translation(BaseModel):
    content: ArticleContent
    source_checksum: str


class Article(BaseModel):
    id: str = Field(pattern=SLUG_PATTERN)
    status: ContentStatus = ContentStatus.DRAFT
    created_at: datetime
    updated_at: datetime
    source: ArticleContent
    translations: dict[Language, Translation] = Field(default_factory=dict)

    def translation_state(self, language: Language) -> TranslationState:
        if language is SOURCE_LANGUAGE:
            return TranslationState.COMPLETE
        translation = self.translations.get(language)
        if translation is None:
            return TranslationState.MISSING
        if translation.source_checksum != self.source.checksum():
            return TranslationState.OUTDATED
        return TranslationState.COMPLETE

    def translation_states(self) -> dict[Language, TranslationState]:
        return {language: self.translation_state(language) for language in TARGET_LANGUAGES}

    def incomplete_languages(self) -> tuple[Language, ...]:
        return tuple(
            language
            for language, state in self.translation_states().items()
            if state is not TranslationState.COMPLETE
        )

    def can_publish(self, required_languages: tuple[Language, ...] = TARGET_LANGUAGES) -> bool:
        return all(
            self.translation_state(language) is TranslationState.COMPLETE
            for language in required_languages
        )

    def set_translation(self, language: Language, content: ArticleContent) -> None:
        if language is SOURCE_LANGUAGE:
            raise ValueError("the source language is edited through 'source', not as a translation")
        self.translations[language] = Translation(
            content=content, source_checksum=self.source.checksum()
        )


def new_article(article_id: str, source: ArticleContent, *, now: datetime | None = None) -> Article:
    timestamp = now or datetime.now(tz=UTC)
    return Article(id=article_id, created_at=timestamp, updated_at=timestamp, source=source)
