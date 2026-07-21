"""Language packs (ADR-0034): everything a locale needs, as data.

A pack carries the locale's identity (tag), its text direction, the
site-facing UI labels, deterministic date formatting and optionally an
admin catalog. The five bundled languages are registered here with
direction only — their labels and date tables still live where they
always did (`cms_build.ui`) and migrate into packs in the ADR's theme
phase; packs already carry the full data for every NEW tag, which is
what makes a third-party language work end to end today.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

from cms_core.languages import Language


@dataclass(frozen=True)
class LanguagePack:
    tag: str
    direction: Literal["ltr", "rtl"] = "ltr"
    site_labels: Mapping[str, str] = field(default_factory=dict)
    """UI label key -> text (the keys `cms_build.ui` documents)."""
    month_names: tuple[str, ...] = ()
    """Twelve month names for date formatting; empty falls back to EN."""
    date_pattern: str = "{day} {month} {year}"
    """Deterministic pattern with `{day}`, `{month}`, `{year}`."""
    admin_catalog: bytes | None = None
    """Optional gettext ``.po`` content for the admin panel (used in the
    ADR's admin phase)."""

    def __post_init__(self) -> None:
        if self.month_names and len(self.month_names) != 12:
            raise ValueError("month_names must have exactly 12 entries")


_PACKS: dict[str, LanguagePack] = {}


def register_language_pack(pack: LanguagePack) -> Language:
    """Register the pack and its tag; idempotent by tag, loud on
    conflicting re-registration."""
    existing = _PACKS.get(pack.tag)
    if existing is not None and existing != pack:
        raise ValueError(f"language pack for {pack.tag!r} is already registered differently")
    language = Language.register(pack.tag)
    _PACKS[pack.tag] = pack
    return language


def language_pack(tag: str) -> LanguagePack | None:
    return _PACKS.get(str(tag))


def direction(tag: str) -> Literal["ltr", "rtl"]:
    pack = language_pack(tag)
    return pack.direction if pack is not None else "ltr"


# The bundled five: identity and direction here; labels and date tables
# remain in cms_build.ui until the ADR-0034 theme phase migrates them.
for _tag in ("en", "pt-pt", "es", "fr", "de"):
    register_language_pack(LanguagePack(tag=_tag))
