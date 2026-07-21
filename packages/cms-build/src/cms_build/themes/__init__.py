"""Theme contract and registry.

A theme renders template kinds ("page", "article", "listing",
"not_found") from contexts the builder prepares, and contributes static
assets. Themes plug in via :func:`register_theme`; the built-in
``default`` theme is intentionally minimal — the polished
``ph7x-reference`` theme ships as its own package.
"""

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Protocol, runtime_checkable

from cms_core.section_kinds import SectionKindSpec as SectionKindSpec

SECTION_KIND_SPECS: dict[str, SectionKindSpec] = {
    "contact": SectionKindSpec(fields=("kicker", "heading", "accent", "button")),
    "cta": SectionKindSpec(
        fields=("kicker", "heading", "body", "button", "url"), markdown=("body",)
    ),
    "expertise": SectionKindSpec(fields=("kicker", "heading"), items=("no", "title", "detail")),
    "faq": SectionKindSpec(fields=("kicker", "heading"), items=("question", "answer")),
    "form": SectionKindSpec(
        fields=(
            "heading",
            "intro",
            "submit_label",
            "consent_label",
            "success_heading",
            "success_text",
        ),
        markdown=("intro",),
        items=("key", "type", "label", "required"),
    ),
    "gallery": SectionKindSpec(fields=("kicker", "heading")),
    "hero": SectionKindSpec(fields=("kicker", "lead", "heading", "accent")),
    "latest-articles": SectionKindSpec(fields=("kicker", "heading")),
    "quote": SectionKindSpec(fields=("quote", "attribution", "role")),
    "story": SectionKindSpec(
        fields=("kicker", "heading", "body"), markdown=("body",), items=("label", "value")
    ),
}
"""The bundled section-kind gallery: kind -> its spec (ADR-0037 v2).

This is the authoring contract both bundled themes implement (THEME_GUIDE
documents each kind) and the source of the admin editor's field
suggestions. Extensions add kinds through ``Extension.section_kinds`` —
plain field-name tuples or full :class:`SectionKindSpec` values both
work (ADR-0028); themes must render unknown kinds generically, never
crash. Repetition is the section's ``items`` group, unbounded; the old
numbered-field convention (``q1``…, ``row1*``…) is retired, and the
builder maps legacy numbered fields into items at render time so
existing content keeps rendering.
"""

SECTION_KIND_GALLERY: dict[str, tuple[str, ...]] = {
    kind: spec.fields for kind, spec in SECTION_KIND_SPECS.items()
}
"""Derived v1 view (kind -> flat field names), kept for compatibility."""


def resolve_kind_spec(kind: str, extension_kinds: Mapping[str, object] = {}) -> SectionKindSpec:
    """The spec for a kind: bundled first, then extension-provided —
    which may be a bare field tuple (v1) or a full spec (v2)."""
    spec = SECTION_KIND_SPECS.get(kind)
    if spec is not None:
        return spec
    raw = extension_kinds.get(kind)
    if isinstance(raw, SectionKindSpec):
        return raw
    if isinstance(raw, tuple):
        return SectionKindSpec(fields=raw)
    return SectionKindSpec()


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
