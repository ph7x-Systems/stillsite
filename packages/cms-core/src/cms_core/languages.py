"""Supported languages. English is the canonical source language."""

from enum import StrEnum


class Language(StrEnum):
    EN = "en"
    PT_PT = "pt-pt"
    ES = "es"
    FR = "fr"
    DE = "de"


SOURCE_LANGUAGE = Language.EN
TARGET_LANGUAGES: tuple[Language, ...] = tuple(
    language for language in Language if language is not SOURCE_LANGUAGE
)
