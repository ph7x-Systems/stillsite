# ADR-0054 — Translation providers: suggestions under editorial sovereignty

- **Status:** accepted
- **Date:** 2026-07-24

## Context

Translation states (`missing`/`outdated`) show the work, but filling them
is entirely manual. Teams want assisted translation without coupling the
CMS, or their content, to any vendor. The existing provider pattern
(ADR-0040 for forms, ADR-0028 for extensions) is the natural shape: a
contract in the core, providers as extensions, selection by
configuration, no provider bundled.

## Evolvability verification

1. **New languages without touching providers?** Yes. A language is
   project configuration; a provider receives the target tag as data.
2. **New content types with compatibility?** Yes. The contract speaks
   `TranslationRequest` (source text + languages + context hint); the
   caller builds requests from whatever content type it serves. A new
   type changes the caller, never the provider interface.
3. **New providers without breaking the contract?** Yes. A provider is
   an extension registered by name; `[translations] provider` selects.
   Adding a destination never touches the core, the editor or the flow.
4. **Is the lifecycle decoupled?** Yes: the caller collects → requests →
   receives suggestions → the editor decides. The provider owns
   translation; the caller owns persistence and editorial state.

## Decision

- **The contract** lives in `cms_core.translations` (pure, no I/O in the
  interface):

  ```python
  class TranslationProvider(Protocol):
      contract_version: int

      @property
      def capabilities(self) -> TranslationCapabilities: ...

      def suggest(self, requests: Sequence[TranslationRequest]) -> tuple[TranslationSuggestion, ...]: ...
  ```

  `TranslationRequest` carries source text (Markdown, plain text or a
  structured field value, never rendered HTML), source and target
  language tags, and an optional human context hint. `TranslationSuggestion`
  carries the translated text and echoes the source for batch correlation.
- **Declared capabilities, not inferred**: `TranslationCapabilities`
  states `supported_languages`, `supports_markdown`, `supports_glossary`,
  `max_batch_size`, `max_characters`, `preserve_placeholders`. The core
  never classifies anything automatically.
- **Registry**: `register_translation_provider(name, factory)` /
  `create_translation_provider(name)` with contract-version and interface
  validation at selection time — the same discipline as the forms
  registry. `[translations] provider` selects; without one configured,
  the feature is invisible.
- **Structured failure**: `ProviderError(code, retryable, message)`
  covers rate-limited, quota-exceeded and temporarily-unavailable as
  first-class states. A failing provider never affects build, panel or
  publishing; whatever `suggest` raises is contained and audited by the
  caller.
- **Suggestions land as draft**: the caller writes a suggestion into the
  existing state machine via `set_translation`, which records the source
  checksum. The editor reviews, edits or discards; nothing is published
  by the provider. Checksums work unchanged.
- **Two faces, one pipeline**: `cms translate --language <tag> --missing`
  (batch, per-entry report, failures listed) and a Suggest-translation
  action in the side-by-side editor, visible only when a provider is
  configured.
- **Secrets via environment only** — never in TOML, database, audit
  records or exports. Audit records carry provider name, language,
  duration, outcome and actor — never prompts, tokens or keys.
- **Extensions** register providers via `Extension.translation_providers`;
  ecosystem naming is `sardine-translate-<name>`.

## Rules a provider must keep

- It only ever sees source text (Markdown, plain text, structured
  fields), never rendered HTML.
- It must preserve template placeholders and structural markers intact.
- It must not publish or change editorial states; suggestions are draft.
- Failures must raise (the caller contains and audits them) rather than
  being swallowed silently.
- Credentials come from the environment, never from configuration, and
  never enter logs or the audit trail.

A conformance suite runs these rules against every provider, including
an extension-registered one, and third-party authors run it against
theirs.

## Consequences

- The editorial flow stays fixed; growth happens in providers.
- The reference behaviour is unchanged — without a provider, the feature
  is invisible.
- The contract version starts at 1; additive evolution within it,
  breaking changes only with a new version validated at selection.
- The consent architecture (#232) and other future provider-style
  features inherit a finished translation contract instead of inventing
  their own.
