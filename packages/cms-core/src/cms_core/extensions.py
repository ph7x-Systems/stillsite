"""The extension contract (ADR-0028).

An extension is a package exposing one :class:`Extension` object through
the ``sardine.extensions`` entry-point group (or referenced by dotted
path). Its contributions reuse the registries that already exist —
validation rules, deterministic build steps, deployment targets, storage
backends, themes, a CLI mount and section-kind hints for the admin.

Activation is explicit: a project lists what it trusts in
``sardine.toml`` (``extensions = ["name"]``). Nothing activates just by
being installed.
"""

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from importlib import import_module, metadata

ENTRY_POINT_GROUP = "sardine.extensions"

# Loose on purpose (ADR-0028): contributions are consumed by the layers
# that own them, so this module depends on none of them.
BuildStep = Callable[..., None]
"""``(config, content, artifact) -> None`` — post-artifact, deterministic."""


@dataclass(frozen=True)
class CommentsProvider:
    """A consent-first comments integration an extension offers (ADR-0031).

    The island script is vendored bytes served same-origin from the built
    artifact — never a CDN reference — and must make no request before an
    explicit reader action. ``thread_url`` maps ``(configured base URL,
    page URL)`` to the entry's discussion URL, deterministically."""

    island_js: bytes
    thread_url: Callable[[str, str], str]


@dataclass(frozen=True)
class Extension:
    """Everything a package may contribute; every field optional."""

    name: str
    validation_rules: Sequence[object] = ()
    build_steps: Sequence[BuildStep] = ()
    targets: Mapping[str, Callable[[], object]] = field(default_factory=dict)
    storage_backends: Mapping[str, Callable[..., object]] = field(default_factory=dict)
    themes: Mapping[str, Callable[[], object]] = field(default_factory=dict)
    cli: object | None = None
    """A ``typer.Typer`` mounted as ``cms x <name>``."""
    section_kinds: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    """kind -> suggested field names, advertised in the admin editor."""
    comments_providers: Mapping[str, CommentsProvider] = field(default_factory=dict)
    """name -> provider (ADR-0031); selected by ``[comments]`` in
    ``sardine.toml``, never active by mere installation."""


class ExtensionError(RuntimeError):
    """A listed extension could not be loaded — loudly, never silently."""


def _from_entry_point(name: str) -> Extension | None:
    for entry in metadata.entry_points(group=ENTRY_POINT_GROUP):
        if entry.name == name:
            loaded = entry.load()
            if not isinstance(loaded, Extension):
                raise ExtensionError(f"entry point {name!r} is not an Extension")
            return loaded
    return None


def _from_dotted_path(name: str) -> Extension:
    module_name, _, attribute = name.partition(":")
    try:
        module = import_module(module_name)
    except ImportError as error:
        raise ExtensionError(f"extension {name!r} not found") from error
    loaded = getattr(module, attribute or "extension", None)
    if not isinstance(loaded, Extension):
        raise ExtensionError(f"{name!r} does not expose an Extension object")
    return loaded


def load_extensions(names: Iterable[str]) -> list[Extension]:
    """Resolve each activation entry: entry-point name first, then dotted
    path (``package.module:attribute``) — the latter also keeps tests and
    private project extensions simple."""
    extensions: list[Extension] = []
    for name in names:
        found = _from_entry_point(name)
        extensions.append(found if found is not None else _from_dotted_path(name))
    return extensions
