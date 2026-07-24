# Writing a Translation Provider

This is the developer guide for assisted translation with your own
engine — a machine-translation API, a translation memory, an LLM,
anything. A provider is one factory implementing one contract; the
editors, the state machine and the publish flow never change.

For the operator's view (configuration, the Suggest action, the
glossary), see the Translations section of
[ADMIN_GUIDE.md](ADMIN_GUIDE.md).

## The lifecycle

The caller owns everything editorial: it collects entries that are
missing or outdated, builds requests, and writes accepted suggestions
as **draft** translations through the existing checksum model. A
provider owns exactly one thing — turning source text into suggested
target text:

```text
collect → provider.suggest(requests) → draft → editor decides
```

A provider never publishes, never changes editorial states, and never
sees rendered HTML. New content types change the caller, never the
provider interface.

## The contract

```python
from cms_core.translations import (
    TRANSLATION_CONTRACT_VERSION,
    TranslationCapabilities,
    TranslationRequest,
    TranslationSuggestion,
)


class MyProvider:
    contract_version = TRANSLATION_CONTRACT_VERSION

    @property
    def capabilities(self) -> TranslationCapabilities:
        return TranslationCapabilities(
            supported_languages=("pt-pt", "es", "fr", "de"),
            supports_markdown=True,
            supports_glossary=True,
            preserve_placeholders=True,
        )

    def suggest(self, requests: list[TranslationRequest]) -> tuple[TranslationSuggestion, ...]: ...
```

- Each `TranslationRequest` carries `source_text` (Markdown, plain text
  or a structured field value), the language pair, an optional human
  `context` hint, and — when the target language has one configured and
  you declare `supports_glossary` — a `glossary` of
  `(source term, required target term)` pairs you must honor.
- Return **one suggestion per request, in request order**, echoing each
  request's `source_text` for batch correlation. An empty source yields
  an empty target; an empty target is a valid "no suggestion" answer,
  never an error.
- Capabilities are promises: every language you declare must answer,
  and a target you never declared must fail structurally (below).
- `contract_version` is validated at selection time; a mismatch refuses
  loudly before anything runs.

## Failure semantics

Raise `TranslationFailed` carrying a `ProviderError` so callers can
show the failure classified and honor `retryable`:

```python
from cms_core.translations import ProviderError, TranslationFailed

raise TranslationFailed(ProviderError(code="rate-limited", retryable=True, message="slow down"))
```

Any other exception is contained and audited too — `TranslationFailed`
just keeps the code and retryability visible to the operator. Never
swallow a failure silently, and never return a wrong-language answer
instead of raising.

## Registration

```python
from cms_core.extensions import Extension


def factory() -> MyProvider:
    return MyProvider()


extension = Extension(name="my-translations", translation_providers={"mine": factory})
```

The project activates the extension and selects the provider:

```toml
extensions = ["sardine_translate_mine:extension"]

[translations]
provider = "mine"

[translations.glossary.pt-pt]
lighthouse = "farol"
```

Without `[translations] provider`, the feature is invisible — no
Suggest action, no `cms translate`.

## Proving conformance

The conformance suite is a public, versioned contract
(`cms_core.translation_conformance`, `TRANSLATION_CONFORMANCE_VERSION`).
Certifying your provider is four lines in your own test suite:

```python
import pytest
from cms_core.translation_conformance import conformance_checks


@pytest.mark.parametrize(("name", "check"), conformance_checks())
def test_conformance(name, check):
    check(MyProvider())
```

The checks need no network, no filesystem and no Sardine project.
Capability-gated checks (placeholders, Markdown, glossary) hold you
only to what your capabilities declare.

## Rules a provider must keep

- It only ever sees source text (Markdown, plain text, structured
  fields), never rendered HTML.
- It must preserve template placeholders and structural markers intact.
- It must not publish or change editorial states; suggestions are draft.
- Failures must raise — classified via `TranslationFailed` — rather
  than being swallowed silently.
- Credentials come from the environment, never from configuration, and
  never enter logs or the audit trail.

Ecosystem naming for published providers: `sardine-translate-<name>`
(see [ECOSYSTEM.md](ECOSYSTEM.md)).
