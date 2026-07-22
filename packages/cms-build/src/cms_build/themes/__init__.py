"""Theme contract and registry.

A theme renders template kinds ("page", "article", "listing",
"not_found") from contexts the builder prepares, and contributes static
assets. Themes plug in via :func:`register_theme`; the built-in
``default`` theme is intentionally minimal — the polished
``ph7x-reference`` theme ships as its own package.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
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


@dataclass(frozen=True)
class ThemeInfo:
    """One discoverable theme, described entirely by its packaging
    (ADR-0049) — no theme code runs to produce this."""

    name: str
    distribution: str = ""
    version: str = ""
    description: str = ""
    author: str = ""
    license: str = ""
    homepage: str = ""
    compatible: bool | None = None
    """Whether the package's own sardine-cms-build range accepts the
    installed version; None when the theme declares no range (bundled)."""
    screenshot: Path | None = None


_BUILTIN_INFO = {
    "default": ThemeInfo(
        name="default",
        description="Minimal single-stylesheet theme; the fallback every install has.",
        license="Apache-2.0",
        compatible=True,
    ),
}

_SCREENSHOT_NAMES = ("theme-screenshot.png", "theme-screenshot.jpg", "theme-screenshot.webp")


def _compatible(requires: list[str] | None) -> bool | None:
    """Evaluate the package's declared sardine-cms-build range against
    the installed version — the same range the installer enforces."""
    if not requires:
        return None
    from importlib.metadata import version as installed_version

    from packaging.requirements import Requirement

    for raw in requires:
        try:
            requirement = Requirement(raw)
        except Exception:
            continue
        if requirement.name == "sardine-cms-build":
            return requirement.specifier.contains(
                installed_version("sardine-cms-build"), prereleases=True
            )
    return None


def _screenshot_beside_module(module: str) -> Path | None:
    from importlib.util import find_spec

    try:
        spec = find_spec(module.partition(":")[0].partition(".")[0])
    except (ImportError, ValueError):
        return None
    if spec is None or not spec.origin:
        return None
    package_dir = Path(spec.origin).parent
    for name in _SCREENSHOT_NAMES:
        candidate = package_dir / name
        if candidate.is_file():
            return candidate
    return None


def discovered_themes() -> tuple[ThemeInfo, ...]:
    """Every theme this environment can activate (ADR-0048).

    Bundled registrations plus everything the ``sardine.themes``
    entry-point group declares — no code is loaded or executed here;
    every card field comes from the distribution's metadata (ADR-0049).
    """
    from importlib.metadata import entry_points

    infos = {name: _BUILTIN_INFO.get(name, ThemeInfo(name=name)) for name in _REGISTRY}
    for entry_point in entry_points(group="sardine.themes"):
        dist = entry_point.dist
        if dist is None:
            infos[entry_point.name] = ThemeInfo(name=entry_point.name)
            continue
        meta = dist.metadata
        homepage = ""
        for raw in meta.get_all("Project-URL") or []:
            label, _, url = raw.partition(",")
            if label.strip().lower() == "homepage":
                homepage = url.strip()
                break
        screenshot = None
        for candidate in dist.files or []:
            if candidate.name in _SCREENSHOT_NAMES:
                located = Path(str(dist.locate_file(candidate)))
                if located.is_file():
                    screenshot = located
                    break
        if screenshot is None:
            # Editable installs list no package data; locate the module
            # without executing it and look next to its source.
            screenshot = _screenshot_beside_module(entry_point.module)
        infos[entry_point.name] = ThemeInfo(
            name=entry_point.name,
            distribution=dist.name,
            version=dist.version,
            description=meta.get("Summary") or "",
            author=meta.get("Author") or meta.get("Author-email") or "",
            license=meta.get("License-Expression") or meta.get("License") or "",
            homepage=homepage,
            compatible=_compatible(dist.requires),
            screenshot=screenshot,
        )
    return tuple(sorted(infos.values(), key=lambda info: info.name))


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
