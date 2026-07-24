"""The translation-provider conformance suite as a public contract
(ADR-0054).

This module defines, executably, what "being a Sardine translation
provider" means. Third-party providers prove conformance by running it
against their own implementation:

    import pytest
    from cms_core.translation_conformance import conformance_checks

    @pytest.mark.parametrize(("name", "check"), conformance_checks())
    def test_conformance(name, check):
        check(MyProvider())

Every check takes a built provider; no network, no filesystem, no
Sardine project. Capability-gated checks (placeholders, Markdown,
glossary) pass trivially when the capability is not declared — a
provider is only held to what it claims.
"""

from __future__ import annotations

from collections.abc import Callable

from cms_core.translations import (
    TRANSLATION_CONTRACT_VERSION,
    TranslationCapabilities,
    TranslationFailed,
    TranslationProvider,
    TranslationRequest,
)

TRANSLATION_CONFORMANCE_VERSION = 1

UNDECLARED_LANGUAGE = "x-conformance-undeclared"
"""A target tag no real provider declares; used to probe failure
semantics for languages outside ``supported_languages``."""

PLACEHOLDER_TEXT = (
    "Dear {name}, run `cms build` before %(deadline)s — "
    "see [the guide](https://example.com/guide) and ${output_dir}."
)
_PLACEHOLDER_MARKERS = (
    "{name}",
    "%(deadline)s",
    "(https://example.com/guide)",
    "`cms build`",
    "${output_dir}",
)

MARKDOWN_TEXT = "## Tides\n\n- first\n- second\n\n**Every** reading counts.\n"
_MARKDOWN_MARKERS = ("## ", "- first", "- second", "**Every**")

GLOSSARY_TEXT = "The lighthouse keeper logs the tide before dawn."
GLOSSARY_PAIRS = (("lighthouse", "farol"), ("tide", "maré"))


def _target(provider: TranslationProvider) -> str:
    languages = provider.capabilities.supported_languages
    assert languages, "capabilities must declare at least one supported language"
    return languages[0]


def _request(provider: TranslationProvider, text: str, **overrides: object) -> TranslationRequest:
    values: dict[str, object] = {
        "source_text": text,
        "source_language": "en",
        "target_language": _target(provider),
    }
    values.update(overrides)
    return TranslationRequest(**values)  # type: ignore[arg-type]


def check_contract_version(provider: TranslationProvider) -> None:
    """The provider speaks the contract version this CMS validates."""
    assert provider.contract_version == TRANSLATION_CONTRACT_VERSION


def check_capabilities_declared(provider: TranslationProvider) -> None:
    """Capabilities are declared, never inferred: a real
    ``TranslationCapabilities`` naming at least one language."""
    capabilities = provider.capabilities
    assert isinstance(capabilities, TranslationCapabilities)
    assert capabilities.supported_languages
    assert all(isinstance(tag, str) and tag for tag in capabilities.supported_languages)


def check_batch_order_preserved(provider: TranslationProvider) -> None:
    """One suggestion per request, in request order, each echoing the
    source text it answers — batch correlation is positional."""
    texts = ("First entry.", "Second entry.", "Third entry.")
    suggestions = provider.suggest([_request(provider, text) for text in texts])
    assert len(suggestions) == len(texts)
    for text, suggestion in zip(texts, suggestions, strict=True):
        assert suggestion.source_text == text


def check_placeholders_preserved(provider: TranslationProvider) -> None:
    """A provider declaring ``preserve_placeholders`` returns template
    placeholders, code spans and link URLs intact."""
    if not provider.capabilities.preserve_placeholders:
        return
    (suggestion,) = provider.suggest([_request(provider, PLACEHOLDER_TEXT)])
    for marker in _PLACEHOLDER_MARKERS:
        assert marker in suggestion.target_text, f"placeholder {marker!r} was lost"


def check_markdown_structure_preserved(provider: TranslationProvider) -> None:
    """A provider declaring ``supports_markdown`` keeps structural
    markers — headings, list items, emphasis — in the target."""
    if not provider.capabilities.supports_markdown:
        return
    (suggestion,) = provider.suggest([_request(provider, MARKDOWN_TEXT)])
    for marker in _MARKDOWN_MARKERS:
        assert marker in suggestion.target_text, f"markdown marker {marker!r} was lost"


def check_empty_source_yields_empty_target(provider: TranslationProvider) -> None:
    """Nothing to translate is not a failure: an empty source yields an
    empty target (callers report it as a skip), never an invented text
    and never an exception."""
    (suggestion,) = provider.suggest([_request(provider, "")])
    assert suggestion.target_text == ""


def check_declared_languages_accepted(provider: TranslationProvider) -> None:
    """Every language the provider declares actually answers a simple
    request — declared capabilities are promises, not aspirations."""
    for tag in provider.capabilities.supported_languages:
        suggestions = provider.suggest(
            [_request(provider, "A short sentence.", target_language=tag)]
        )
        assert len(suggestions) == 1


def check_undeclared_language_fails_structurally(provider: TranslationProvider) -> None:
    """A target outside ``supported_languages`` fails loudly and
    classified — ``TranslationFailed`` with a coded ``ProviderError`` —
    never a silent wrong-language answer."""
    try:
        provider.suggest(
            [_request(provider, "A short sentence.", target_language=UNDECLARED_LANGUAGE)]
        )
    except TranslationFailed as failure:
        assert failure.error.code
    else:
        raise AssertionError("an undeclared target language must raise TranslationFailed")


def check_glossary_honored(provider: TranslationProvider) -> None:
    """A provider declaring ``supports_glossary`` uses the required
    target terms it is given."""
    if not provider.capabilities.supports_glossary:
        return
    (suggestion,) = provider.suggest([_request(provider, GLOSSARY_TEXT, glossary=GLOSSARY_PAIRS)])
    for _source_term, target_term in GLOSSARY_PAIRS:
        assert target_term in suggestion.target_text, f"glossary term {target_term!r} ignored"


def check_glossary_never_breaks_requests(provider: TranslationProvider) -> None:
    """The glossary field is additive: any provider — supporting it or
    not — answers a request that carries one."""
    suggestions = provider.suggest([_request(provider, GLOSSARY_TEXT, glossary=GLOSSARY_PAIRS)])
    assert len(suggestions) == 1


def conformance_checks() -> tuple[tuple[str, Callable[[TranslationProvider], None]], ...]:
    """The named checks, in a stable order, for parametrized tests."""
    return (
        ("contract-version", check_contract_version),
        ("capabilities-declared", check_capabilities_declared),
        ("batch-order-preserved", check_batch_order_preserved),
        ("placeholders-preserved", check_placeholders_preserved),
        ("markdown-structure-preserved", check_markdown_structure_preserved),
        ("empty-source-empty-target", check_empty_source_yields_empty_target),
        ("declared-languages-accepted", check_declared_languages_accepted),
        ("undeclared-language-fails-structurally", check_undeclared_language_fails_structurally),
        ("glossary-honored", check_glossary_honored),
        ("glossary-never-breaks-requests", check_glossary_never_breaks_requests),
    )
