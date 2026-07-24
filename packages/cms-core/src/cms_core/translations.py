"""Translation providers (ADR-0054): suggestions under editorial sovereignty.

A provider produces suggestions; it never modifies published content,
never publishes, and never changes editorial states without explicit
user action. The editorial decision always belongs to the user.

The contract follows the established provider pattern (ADR-0040):
contract version validated at selection time, registered via
``Extension.translation_providers``, selected by ``[translations] provider``.
Without a provider configured, the feature is invisible.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

TRANSLATION_CONTRACT_VERSION = 1
"""The provider contract's version: validated at selection time, never
mid-translation."""


@dataclass(frozen=True, slots=True)
class ProviderError:
    """A structured failure a provider reports (ADR-0054).

    Rate-limited, quota-exceeded and temporarily-unavailable are
    first-class states; a failing provider never affects build, panel
    or publishing.
    """

    code: str
    retryable: bool
    message: str


@dataclass(frozen=True, slots=True)
class TranslationCapabilities:
    """Declared capabilities, not inferred (ADR-0054).

    Providers state what they support; the core never classifies
    anything automatically.
    """

    supported_languages: tuple[str, ...] = ()
    supports_markdown: bool = True
    supports_glossary: bool = False
    max_batch_size: int = 0
    """Zero means no declared limit."""
    max_characters: int = 0
    """Zero means no declared limit."""
    preserve_placeholders: bool = True


@dataclass(frozen=True, slots=True)
class TranslationRequest:
    """One source text the provider translates into a target language.

    The source is Markdown, plain text or a structured field value,
    never rendered HTML. Template placeholders and structural markers
    must survive the round-trip intact.
    """

    source_text: str
    source_language: str
    target_language: str
    context: str = ""
    """A human hint (heading, field label) the provider may use for
    disambiguation; never required and never contains HTML."""


@dataclass(frozen=True, slots=True)
class TranslationSuggestion:
    """One provider suggestion landing as draft content (ADR-0054).

    Suggestions enter the existing state machine: source change →
    outdated → suggest → draft → editor review → complete. The
    checksum model is unchanged.
    """

    target_text: str
    source_text: str = ""
    """The text that was translated, echoed for batch correlation."""


@runtime_checkable
class TranslationProvider(Protocol):
    """Suggestions under editorial sovereignty (ADR-0054).

    Whatever ``suggest`` raises is contained and audited by the caller,
    never build- or panel-facing. A provider cannot break the editorial
    flow.
    """

    contract_version: int

    @property
    def capabilities(self) -> TranslationCapabilities: ...

    def suggest(
        self, requests: Sequence[TranslationRequest]
    ) -> tuple[TranslationSuggestion, ...]: ...

    """Return one suggestion per request, in order. A provider that
    cannot handle a request may return an empty ``target_text`` for
    that position; a structural failure raises and is contained."""


_PROVIDERS: dict[str, object] = {}


def register_translation_provider(name: str, factory: object) -> None:
    """Register a factory ``() -> TranslationProvider``. Idempotent by
    identity; loud on conflict."""
    existing = _PROVIDERS.get(name)
    if existing is not None and existing is not factory:
        raise ValueError(f"translation provider {name!r} is already registered differently")
    _PROVIDERS[name] = factory


def available_translation_providers() -> tuple[str, ...]:
    return tuple(sorted(_PROVIDERS))


def create_translation_provider(name: str) -> TranslationProvider:
    """Resolve and build the configured provider, validating the
    contract before anything runs."""
    factory = _PROVIDERS.get(name)
    if factory is None:
        known = ", ".join(available_translation_providers()) or "none"
        raise ValueError(f"unknown translation provider {name!r} (registered: {known})")
    provider = factory()  # type: ignore[operator]
    version = getattr(provider, "contract_version", None)
    if version != TRANSLATION_CONTRACT_VERSION:
        raise ValueError(
            f"provider {name!r} implements contract version {version!r}; "
            f"this CMS speaks version {TRANSLATION_CONTRACT_VERSION}"
        )
    if not isinstance(provider, TranslationProvider):
        raise ValueError(f"provider {name!r} does not implement the translation contract")
    return provider
