"""Localized UI chrome labels (never editorial content).

Small strings the theme chrome needs ("Blog", "Search", …). Defaults ship
per language; projects override any of them via ``[site.labels]`` in
configuration — templates and builder code never hardcode UI text.
"""

from cms_core import SOURCE_LANGUAGE, Language, language_pack

from cms_build.config import SiteConfig

LABEL_KEYS: tuple[str, ...] = (
    "blog",
    "search",
    "admin",
    "comments",
    "view-cards",
    "view-list",
    "back",
    "blog-title",
    "blog-eyebrow",
    "blog-sub",
    "min-read",
    "not-found",
    "error-unauthorized",
    "error-forbidden",
    "error-server",
)
"""The chrome label keys themes may ask for. The texts live in each
language's pack (ADR-0034: no language data outside packs); projects
override any of them via ``[site.labels]``."""


def format_date(day: int, month: int, year: int, language: Language) -> str:
    """One uniform path (ADR-0034): months and pattern come from the
    language's pack; a pack without months borrows the source pack's."""
    pack = language_pack(language)
    months = pack.month_names if pack is not None and pack.month_names else None
    if months is None:
        source = language_pack(SOURCE_LANGUAGE)
        assert source is not None and source.month_names  # bundled EN pack
        months = source.month_names
        pattern = source.date_pattern
    else:
        pattern = pack.date_pattern if pack is not None else "{day} {month} {year}"
    return pattern.format(day=day, month=months[month - 1], year=year)


def ui_label(config: SiteConfig, key: str, language: Language) -> str:
    """Project override wins; then the language's pack; then the source
    pack; the key itself is the loud last resort."""
    overrides = config.labels.get(key, {})
    pack = language_pack(language)
    source = language_pack(SOURCE_LANGUAGE)
    return (
        overrides.get(language)
        or overrides.get(SOURCE_LANGUAGE)
        or (pack.site_labels.get(key) if pack is not None else None)
        or (source.site_labels.get(key) if source is not None else None)
        or key
    )
