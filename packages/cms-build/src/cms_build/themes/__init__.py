"""Theme contract and registry.

A theme renders template kinds ("page", "article", "listing") from contexts
the builder prepares, and contributes static assets. Themes plug in via
:func:`register_theme`; the built-in ``default`` theme is intentionally
minimal (the polished reference theme is Milestone 4).
"""

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Protocol, runtime_checkable

SECTION_KIND_GALLERY: dict[str, tuple[str, ...]] = {
    "contact": ("kicker", "heading", "accent", "button"),
    "cta": ("kicker", "heading", "body", "button", "url"),
    "expertise": ("kicker", "heading", "row1no", "row1t", "row1d"),
    "faq": ("kicker", "heading", "q1", "a1", "q2", "a2"),
    "gallery": ("kicker", "heading"),
    "hero": ("kicker", "lead", "heading", "accent"),
    "latest-articles": ("kicker", "heading"),
    "quote": ("quote", "attribution", "role"),
    "story": ("kicker", "heading", "body"),
}
"""The bundled section-kind gallery: kind -> the field names it consumes.

This is the authoring contract both bundled themes implement (THEME_GUIDE
documents each kind) and the source of the admin editor's field
suggestions. Extensions add kinds through ``Extension.section_kinds``
(ADR-0028); themes must render unknown kinds generically, never crash.
``expertise`` repeats its row fields up to ``row8*``; ``faq`` repeats its
pairs up to ``q6``/``a6``; ``gallery`` and ``story`` render the section's
media list; ``quote`` needs no heading — the quote is the content.
"""


@runtime_checkable
class Theme(Protocol):
    name: str

    def render(self, kind: str, context: Mapping[str, object]) -> str: ...

    def assets(self) -> Mapping[str, bytes]: ...


ThemeFactory = Callable[[Path | None], Theme]
"""A factory receives the project's overrides directory (or None)."""

_REGISTRY: dict[str, ThemeFactory] = {}


def register_theme(name: str, factory: ThemeFactory) -> None:
    _REGISTRY[name] = factory


def available_themes() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


def create_theme(name: str, overrides: Path | None = None) -> Theme:
    factory = _REGISTRY.get(name)
    if factory is None:
        _load_entry_point(name)
        factory = _REGISTRY.get(name)
    if factory is None:
        known = ", ".join(available_themes())
        raise ValueError(f"unknown theme {name!r} (known themes: {known})")
    return factory(overrides)


def _load_entry_point(name: str) -> None:
    """Lazily resolve an installed theme package by name (ADR-0012)."""
    from importlib.metadata import entry_points

    for entry_point in entry_points(group="sardine.themes", name=name):
        register_theme(name, entry_point.load())


def _register_builtin() -> None:
    from cms_build.themes.default import DefaultTheme

    register_theme("default", DefaultTheme)


_register_builtin()
