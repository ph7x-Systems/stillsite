"""Shared translation machinery for every translatable content type.

Any content model that subclasses :class:`ChecksummedContent` gains checksum
tracking, and any entity that subclasses :class:`TranslatableModel` gains the
full ``missing / outdated / complete`` state logic derived from those
checksums — articles, pages and sections all share this one implementation.
"""

import hashlib
from collections.abc import Iterable

from pydantic import BaseModel, Field

from cms_core.languages import SOURCE_LANGUAGE, TARGET_LANGUAGES, Language
from cms_core.states import TranslationState


class ChecksummedContent(BaseModel):
    def checksum_payload(self) -> tuple[str, ...]:
        raise NotImplementedError

    def checksum(self) -> str:
        joined = "\x1f".join(self.checksum_payload())
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()


class Translation[ContentT: ChecksummedContent](BaseModel):
    content: ContentT
    source_checksum: str


class TranslatableModel[ContentT: ChecksummedContent](BaseModel):
    source: ContentT
    translations: dict[Language, Translation[ContentT]] = Field(default_factory=dict)

    def translation_state(
        self, language: Language, *, source: Language | None = None
    ) -> TranslationState:
        """``source`` names the language the ``source`` content is in
        (ADR-0034); None keeps the historical default (``en``). A stored
        translation always wins over the source shortcut, so a project
        whose source is not ``en`` can still target ``en`` correctly."""
        translation = self.translations.get(language)
        if translation is not None:
            if translation.source_checksum != self.source.checksum():
                return TranslationState.OUTDATED
            return TranslationState.COMPLETE
        if language == (source if source is not None else SOURCE_LANGUAGE):
            return TranslationState.COMPLETE
        return TranslationState.MISSING

    def translation_states(
        self,
        languages: tuple[Language, ...] = TARGET_LANGUAGES,
        *,
        source: Language | None = None,
    ) -> dict[Language, TranslationState]:
        return {language: self.translation_state(language, source=source) for language in languages}

    def incomplete_languages(
        self,
        languages: tuple[Language, ...] = TARGET_LANGUAGES,
        *,
        source: Language | None = None,
    ) -> tuple[Language, ...]:
        return tuple(
            language
            for language, state in self.translation_states(languages, source=source).items()
            if state is not TranslationState.COMPLETE
        )

    def can_publish(self, required_languages: tuple[Language, ...] = TARGET_LANGUAGES) -> bool:
        return all(
            self.translation_state(language) is TranslationState.COMPLETE
            for language in required_languages
        )

    def set_translation(
        self, language: Language, content: ContentT, *, source: Language | None = None
    ) -> None:
        if language == (source if source is not None else SOURCE_LANGUAGE):
            raise ValueError("the source language is edited through 'source', not as a translation")
        self.translations[language] = Translation[ContentT](
            content=content, source_checksum=self.source.checksum()
        )


_SEVERITY = {
    TranslationState.COMPLETE: 0,
    TranslationState.OUTDATED: 1,
    TranslationState.MISSING: 2,
}


def worst_state(states: Iterable[TranslationState]) -> TranslationState:
    """Aggregate state of a composite: the least-complete state wins."""
    return max(states, key=_SEVERITY.__getitem__, default=TranslationState.COMPLETE)
