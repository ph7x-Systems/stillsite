"""Theme contract and registry.

A theme renders template kinds ("page", "article", "listing") from contexts
the builder prepares, and contributes static assets. Themes plug in via
:func:`register_theme`; the built-in ``default`` theme is intentionally
minimal (the polished reference theme is Milestone 4).
"""

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Protocol, runtime_checkable


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
        known = ", ".join(available_themes())
        raise ValueError(f"unknown theme {name!r} (known themes: {known})")
    return factory(overrides)


def _register_builtin() -> None:
    from cms_build.themes.default import DefaultTheme

    register_theme("default", DefaultTheme)


_register_builtin()
