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

from cms_core.section_kinds import SectionKindSpec

ENTRY_POINT_GROUP = "sardine.extensions"

# Loose on purpose (ADR-0028): contributions are consumed by the layers
# that own them, so this module depends on none of them.
BuildStep = Callable[..., None]
"""``(config, content, artifact) -> None`` — post-artifact, deterministic."""

MailSender = Callable[[str, str, str], None]
"""``(to, subject, body) -> None`` — deliver one plain-text message
(ADR-0032). Transports read their own configuration (OAuth tokens,
tenant ids…) from the environment; the factory below may raise at
startup when misconfigured — loudly, never at send time."""


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
    section_kinds: Mapping[str, tuple[str, ...] | SectionKindSpec] = field(default_factory=dict)
    deploy_providers: Mapping[str, Callable[..., object]] = field(default_factory=dict)
    forms_providers: Mapping[str, Callable[..., object]] = field(default_factory=dict)
    """Forms providers by name (ADR-0040): a factory ``() ->
    FormsProvider``. Registered on activation; a new destination never
    touches the endpoint or the editorial flow."""
    translation_providers: Mapping[str, Callable[..., object]] = field(default_factory=dict)
    """Translation providers by name (ADR-0054): a factory ``() ->
    TranslationProvider``. Registered on activation; a new provider
    never touches the editorial flow — suggestions land as draft."""
    """Deployment providers by name (#156): a factory ``(settings,
    project_dir) -> DeployProvider``. Registered on activation; adding
    a destination never touches the core, the editor or the flow."""
    """kind -> suggested field names, advertised in the admin editor."""
    comments_providers: Mapping[str, CommentsProvider] = field(default_factory=dict)
    """name -> provider (ADR-0031); selected by ``[comments]`` in
    ``sardine.toml``, never active by mere installation."""
    mail_transports: Mapping[str, Callable[[], MailSender]] = field(default_factory=dict)
    """name -> factory building a configured sender (ADR-0032); selected
    by ``SARDINE_MAIL_TRANSPORT``, never active by mere installation."""
    language_packs: Sequence[object] = ()
    """``LanguagePack`` contributions (ADR-0034); registered on project
    load — the tag becomes a valid content language for the project."""
    settings_schema: "SettingsSchema | None" = None
    """Optional declared settings (ADR-0052): versioned, plain data.
    Values persist in the project's [extension_settings.<name>] table;
    fields with env set are secrets the panel never touches."""
    configure: Callable[[Mapping[str, object]], None] | None = None
    """Optional hook receiving resolved settings at load time (ADR-0052);
    contained like every extension call."""
    migrate_settings: Callable[[int, Mapping[str, object]], Mapping[str, object]] | None = None
    """Optional migration between settings-schema versions (ADR-0052);
    runs contained at read time."""
    health_check: Callable[[], Sequence["HealthCheck"]] | None = None
    """Optional self-diagnosis (ADR-0051): returns HealthCheck results.
    Run on demand by the panel and by ``cms doctor``; contained — a
    raising check is a failed check, never a crash. Never gates."""


@dataclass(frozen=True)
class ExtensionInfo:
    """One discoverable extension, described by its packaging alone
    (ADR-0050) — nothing is imported to produce this."""

    name: str
    distribution: str = ""
    version: str = ""
    description: str = ""
    author: str = ""
    license: str = ""
    homepage: str = ""
    compatible: bool | None = None


def _compatible_with_core(requires: list[str] | None) -> bool | None:
    if not requires:
        return None
    from packaging.requirements import Requirement

    for raw in requires:
        try:
            requirement = Requirement(raw)
        except Exception:
            continue
        if requirement.name == "sardine-cms-core":
            return requirement.specifier.contains(
                metadata.version("sardine-cms-core"), prereleases=True
            )
    return None


def discovered_extensions() -> tuple[ExtensionInfo, ...]:
    """Every extension the environment offers (ADR-0050), described by
    distribution metadata — no extension code runs here."""
    infos: dict[str, ExtensionInfo] = {}
    for entry in metadata.entry_points(group=ENTRY_POINT_GROUP):
        dist = entry.dist
        if dist is None:
            infos[entry.name] = ExtensionInfo(name=entry.name)
            continue
        meta = dist.metadata
        homepage = ""
        for raw in meta.get_all("Project-URL") or []:
            label, _, url = raw.partition(",")
            if label.strip().lower() == "homepage":
                homepage = url.strip()
                break
        infos[entry.name] = ExtensionInfo(
            name=entry.name,
            distribution=dist.name,
            version=dist.version,
            description=meta.get("Summary") or "",
            author=meta.get("Author") or meta.get("Author-email") or "",
            license=meta.get("License-Expression") or meta.get("License") or "",
            homepage=homepage,
            compatible=_compatible_with_core(dist.requires),
        )
    return tuple(sorted(infos.values(), key=lambda info: info.name))


SETTINGS_TYPES = ("string", "integer", "boolean", "choice")


@dataclass(frozen=True)
class SettingsField:
    """One declared setting (ADR-0052) — plain data, never code."""

    key: str
    type: str = "string"
    label: str = ""
    default: object = None
    required: bool = False
    choices: tuple[str, ...] = ()
    env: str = ""
    """When set, this field is a secret held in the named environment
    variable: the panel reports presence or absence only and never
    edits, stores or displays the value."""


@dataclass(frozen=True)
class SettingsSchema:
    """A versioned, declarative settings description (ADR-0052)."""

    version: int = 1
    fields: tuple[SettingsField, ...] = ()


def validate_settings(
    schema: SettingsSchema, values: Mapping[str, object]
) -> tuple[dict[str, object], list[str]]:
    """Deterministic validation before any persistence (ADR-0052).

    Returns (clean values, errors). Unknown keys are surfaced as
    errors, never silently dropped; defaults fill absent keys.
    """
    clean: dict[str, object] = {}
    errors: list[str] = []
    known = {spec.key: spec for spec in schema.fields}
    for key in values:
        if key not in known:
            errors.append(f"unknown setting {key!r}")
    for spec in schema.fields:
        if spec.env:
            continue  # secrets never enter stored values
        raw = values.get(spec.key, spec.default)
        if raw is None:
            if spec.required:
                errors.append(f"{spec.key} is required")
            continue
        if spec.type == "integer":
            try:
                clean[spec.key] = int(raw)  # type: ignore[call-overload]
            except (TypeError, ValueError):
                errors.append(f"{spec.key} must be an integer")
        elif spec.type == "boolean":
            if isinstance(raw, bool):
                clean[spec.key] = raw
            elif str(raw).lower() in ("true", "1", "yes", "on"):
                clean[spec.key] = True
            elif str(raw).lower() in ("false", "0", "no", "off", ""):
                clean[spec.key] = False
            else:
                errors.append(f"{spec.key} must be a boolean")
        elif spec.type == "choice":
            if str(raw) in spec.choices:
                clean[spec.key] = str(raw)
            else:
                errors.append(f"{spec.key} must be one of: {', '.join(spec.choices)}")
        else:
            clean[spec.key] = str(raw)
    return clean, errors


def resolve_settings(
    schema: SettingsSchema, stored: Mapping[str, object]
) -> tuple[dict[str, object], dict[str, str]]:
    """Resolved values with explicit provenance (ADR-0052).

    Returns (values, provenance) where provenance maps each key to
    "default", "configured", "env-present" or "env-missing".
    """
    import os

    values: dict[str, object] = {}
    provenance: dict[str, str] = {}
    for spec in schema.fields:
        if spec.env:
            present = bool(os.environ.get(spec.env))
            provenance[spec.key] = "env-present" if present else "env-missing"
            continue
        if spec.key in stored:
            values[spec.key] = stored[spec.key]
            provenance[spec.key] = "configured"
        else:
            if spec.default is not None:
                values[spec.key] = spec.default
            provenance[spec.key] = "default"
    return values, provenance


@dataclass(frozen=True)
class HealthCheck:
    """One health verdict an extension reports about itself (ADR-0051)."""

    name: str
    ok: bool
    detail: str = ""


def run_health_check(extension: "Extension") -> tuple[HealthCheck, ...]:
    """Run an extension's declared health check, contained.

    No declared check reports nothing; a raising check becomes a single
    failed result carrying the error — never an exception (ADR-0051).
    """
    if extension.health_check is None:
        return ()
    try:
        return tuple(extension.health_check())
    except Exception as error:
        return (HealthCheck(name="health check", ok=False, detail=str(error)),)


class ExtensionError(RuntimeError):
    """A listed extension could not be loaded — loudly, never silently."""


def _from_entry_point(name: str) -> Extension | None:
    for entry in metadata.entry_points(group=ENTRY_POINT_GROUP):
        if entry.name == name:
            try:
                loaded = entry.load()
            except Exception as error:
                raise ExtensionError(f"extension {name!r} failed to load: {error}") from error
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
    except Exception as error:
        raise ExtensionError(f"extension {name!r} failed to load: {error}") from error
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
