"""The head contract, generated in exactly one place.

Every rendered page receives a :class:`Head` computed from the content model:
canonical URL, the full hreflang cluster (only languages where the content
actually exists, plus x-default), Open Graph data and description. Templates
render it; they never assemble it.
"""

from dataclasses import dataclass, field

from cms_core import Language
from cms_core.language_packs import direction

from cms_build.config import SiteConfig
from cms_build.urls import absolute

_OG_LOCALES: dict[Language, str] = {
    Language.EN: "en_GB",
    Language.PT_PT: "pt_PT",
    Language.ES: "es_ES",
    Language.FR: "fr_FR",
    Language.DE: "de_DE",
}


def _og_locale(language: Language) -> str:
    """Bundled tags keep their curated Open Graph locales; pack tags
    derive one from the tag itself (ADR-0034)."""
    curated = _OG_LOCALES.get(language)
    if curated is not None:
        return curated
    parts = str(language).split("-")
    if len(parts) >= 2:
        return f"{parts[0]}_{parts[-1].upper()}"
    return parts[0]


@dataclass(frozen=True, slots=True)
class Alternate:
    hreflang: str
    href: str


@dataclass(frozen=True, slots=True)
class Head:
    title: str
    description: str
    canonical: str
    language: Language
    site_name: str
    og_type: str
    alternates: tuple[Alternate, ...]
    og_locale: str
    og_locale_alternates: tuple[str, ...]
    json_ld: str | None = None
    direction: str = "ltr"
    """Text direction of the page language (ADR-0034); themes put
    dir="rtl" on <html> when it says so."""
    paths_by_language: dict[Language, str] = field(default_factory=dict)
    """Site-relative path of this page in every language it exists in —
    the language switcher uses it to stay on the current page."""


def hreflang_code(language: Language) -> str:
    return "pt-PT" if language is Language.PT_PT else language.value


def build_head(
    config: SiteConfig,
    *,
    title: str,
    description: str,
    language: Language,
    paths_by_language: dict[Language, str],
    og_type: str = "website",
    json_ld: str | None = None,
) -> Head:
    ordered = [lang for lang in config.all_languages if lang in paths_by_language]
    alternates = [
        Alternate(hreflang=hreflang_code(lang), href=absolute(config, paths_by_language[lang]))
        for lang in ordered
    ]
    if config.source_language in paths_by_language:
        alternates.append(
            Alternate(
                hreflang="x-default",
                href=absolute(config, paths_by_language[config.source_language]),
            )
        )
    return Head(
        title=title,
        description=description,
        canonical=absolute(config, paths_by_language[language]),
        language=language,
        site_name=config.name,
        og_type=og_type,
        alternates=tuple(alternates),
        og_locale=_og_locale(language),
        og_locale_alternates=tuple(_og_locale(lang) for lang in ordered if lang is not language),
        json_ld=json_ld,
        direction=direction(language),
        paths_by_language=dict(paths_by_language),
    )
