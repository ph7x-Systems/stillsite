"""The translation provider contract: suggestions under editorial
sovereignty (ADR-0054).

A provider produces suggestions, never modifies published content,
never publishes, and is contained when it fails. The fictional provider
in this file registers through an extension and receives translation
requests — a new provider with zero changes to the editorial flow.
"""

from collections.abc import Sequence
from pathlib import Path

import pytest
from cms_core.extensions import Extension
from cms_core.translations import (
    TRANSLATION_CONTRACT_VERSION,
    ProviderError,
    TranslationCapabilities,
    TranslationFailed,
    TranslationProvider,
    TranslationRequest,
    TranslationSuggestion,
    available_translation_providers,
    create_translation_provider,
    register_translation_provider,
)

RECEIVED: list[TranslationRequest] = []


class EchoProvider:
    """A fictional provider: it echoes the source text with a language
    tag prefix, so tests can assert the round-trip without a network."""

    contract_version = TRANSLATION_CONTRACT_VERSION

    @property
    def capabilities(self) -> TranslationCapabilities:
        return TranslationCapabilities(
            supported_languages=("pt-pt", "es", "fr", "de"),
            supports_markdown=True,
            supports_glossary=True,
            preserve_placeholders=True,
        )

    def suggest(self, requests: Sequence[TranslationRequest]) -> tuple[TranslationSuggestion, ...]:
        RECEIVED.extend(requests)
        suggestions: list[TranslationSuggestion] = []
        for req in requests:
            if req.target_language not in self.capabilities.supported_languages:
                raise TranslationFailed(
                    ProviderError(
                        code="unsupported-language",
                        retryable=False,
                        message=f"{req.target_language!r} is not a supported target",
                    )
                )
            if not req.source_text:
                suggestions.append(TranslationSuggestion(target_text="", source_text=""))
                continue
            text = req.source_text
            for source_term, target_term in req.glossary:
                text = text.replace(source_term, target_term)
            suggestions.append(
                TranslationSuggestion(
                    target_text=f"[{req.target_language}] {text}",
                    source_text=req.source_text,
                )
            )
        return tuple(suggestions)


class ExplodingProvider:
    contract_version = TRANSLATION_CONTRACT_VERSION

    @property
    def capabilities(self) -> TranslationCapabilities:
        return TranslationCapabilities()

    def suggest(self, requests: Sequence[TranslationRequest]) -> tuple[TranslationSuggestion, ...]:
        raise RuntimeError("the service is gone")


class EmptyProvider:
    """A provider that returns no suggestion for any request."""

    contract_version = TRANSLATION_CONTRACT_VERSION

    @property
    def capabilities(self) -> TranslationCapabilities:
        return TranslationCapabilities()

    def suggest(self, requests: Sequence[TranslationRequest]) -> tuple[TranslationSuggestion, ...]:
        return tuple(TranslationSuggestion(target_text="") for _ in requests)


class PlainEchoProvider(EchoProvider):
    """Echo without glossary support — proves callers gate the glossary
    on the declared capability."""

    @property
    def capabilities(self) -> TranslationCapabilities:
        return TranslationCapabilities(
            supported_languages=("pt-pt", "es", "fr", "de"),
            supports_markdown=True,
            supports_glossary=False,
            preserve_placeholders=True,
        )


def _echo_factory() -> EchoProvider:
    return EchoProvider()


def _plain_echo_factory() -> PlainEchoProvider:
    return PlainEchoProvider()


def _exploding_factory() -> ExplodingProvider:
    return ExplodingProvider()


def _empty_factory() -> EmptyProvider:
    return EmptyProvider()


extension = Extension(
    name="echo-translations",
    translation_providers={"echo": _echo_factory, "echo-plain": _plain_echo_factory},
)


def test_the_contract_version_is_one() -> None:
    assert TRANSLATION_CONTRACT_VERSION == 1


def test_provider_error_is_structured() -> None:
    error = ProviderError(code="rate-limited", retryable=True, message="slow down")
    assert error.code == "rate-limited"
    assert error.retryable is True
    assert error.message == "slow down"


def test_capabilities_declare_what_the_provider_supports() -> None:
    caps = TranslationCapabilities(
        supported_languages=("pt-pt", "es"),
        supports_markdown=True,
        supports_glossary=False,
        max_batch_size=100,
        max_characters=5000,
        preserve_placeholders=True,
    )
    assert caps.supported_languages == ("pt-pt", "es")
    assert caps.max_batch_size == 100
    assert caps.preserve_placeholders is True


def test_a_provider_receives_requests_and_returns_suggestions() -> None:
    register_translation_provider("echo", _echo_factory)
    RECEIVED.clear()
    provider = create_translation_provider("echo")
    requests = [
        TranslationRequest(
            source_text="Hello world",
            source_language="en",
            target_language="pt-pt",
            context="greeting",
        ),
        TranslationRequest(
            source_text="Goodbye",
            source_language="en",
            target_language="pt-pt",
        ),
    ]
    suggestions = provider.suggest(requests)
    assert len(suggestions) == 2
    assert suggestions[0].target_text == "[pt-pt] Hello world"
    assert suggestions[0].source_text == "Hello world"
    assert suggestions[1].target_text == "[pt-pt] Goodbye"
    assert len(RECEIVED) == 2
    assert RECEIVED[0].context == "greeting"


def test_selection_validates_the_contract() -> None:
    with pytest.raises(ValueError, match="unknown translation provider 'nowhere'"):
        create_translation_provider("nowhere")

    class Ancient:
        contract_version = 0

        @property
        def capabilities(self) -> TranslationCapabilities:
            return TranslationCapabilities()

        def suggest(
            self, requests: Sequence[TranslationRequest]
        ) -> tuple[TranslationSuggestion, ...]:
            return ()

    register_translation_provider("contract-ancient", lambda: Ancient())
    with pytest.raises(ValueError, match="contract version 0"):
        create_translation_provider("contract-ancient")

    class Hollow:
        contract_version = TRANSLATION_CONTRACT_VERSION

    register_translation_provider("contract-hollow", lambda: Hollow())
    with pytest.raises(ValueError, match="does not implement the translation contract"):
        create_translation_provider("contract-hollow")

    register_translation_provider("echo", _echo_factory)  # idempotent by identity
    with pytest.raises(ValueError, match="already registered differently"):
        register_translation_provider("echo", lambda: EchoProvider())
    provider = create_translation_provider("echo")
    assert isinstance(provider, TranslationProvider)
    assert "echo" in available_translation_providers()


def test_an_empty_suggestion_is_not_a_failure() -> None:
    register_translation_provider("empty", _empty_factory)
    provider = create_translation_provider("empty")
    requests = [TranslationRequest(source_text="Hello", source_language="en", target_language="fr")]
    suggestions = provider.suggest(requests)
    assert len(suggestions) == 1
    assert suggestions[0].target_text == ""


def test_extension_activation_registers_the_provider(tmp_path: Path) -> None:
    """The dotted-path activation used by real projects registers the
    provider exactly like forms providers — zero core changes."""
    from cms_cli.project import load_project

    (tmp_path / "sardine.toml").write_text(
        'extensions = ["test_translation_provider_contract:extension"]\n'
        '[site]\nname = "S"\nbase_url = "https://s.example"\nlanguages = []\n',
        encoding="utf-8",
    )
    project = load_project(tmp_path)
    project.load_extensions()
    assert "echo" in available_translation_providers()
