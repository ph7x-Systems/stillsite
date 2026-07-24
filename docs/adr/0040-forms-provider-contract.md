# ADR-0040 — The forms provider contract

- **Status:** accepted
- **Date:** 2026-07-21

## Context

The forms feature shipped implementation-first: the section kind, the
official endpoint (validation, layered spam protection, deterministic
responses), contained mail notification and optional storage — all in
production. The contract for third-party providers was deliberately
deferred until the reference implementation proved the shape. This
decision freezes it.

## Evolvability verification

Freezing an interface is only safe when the system around it can grow
without breaking it. Four questions, answered by the shipped design:

1. **New anti-spam mechanisms without touching providers?** Yes. Spam
   protection runs in the endpoint pipeline *before* acceptance;
   providers only ever receive accepted submissions. A new layer is an
   endpoint change, invisible to every provider.
2. **New notification destinations without breaking the contract?**
   Yes. A destination *is* a provider. The reference provider (mail +
   optional storage) is one implementation of the same contract a
   webhook or queue provider would implement; destinations can also be
   composed by an extension provider delegating to the reference one.
3. **New field types with compatibility?** Yes. Validation happens in
   the endpoint against the form's declared items; the provider
   receives the accepted values as an opaque mapping. A new field type
   changes validation, never the provider interface.
4. **Is the lifecycle decoupled?** Yes: validate → accept → hand to
   the provider. The provider owns everything after acceptance
   (deliver, store, forward); the endpoint owns everything before it
   (protocol, spam, validation, the visitor's answer).

## Decision

- **The contract** lives in `cms_core.forms` (pure, no I/O in the
  interface):

  ```python
  class FormsProvider(Protocol):
      contract_version: int  # must equal FORMS_CONTRACT_VERSION

      def handle(self, submission: FormSubmission, form: FormContext) -> None: ...
  ```

  `FormSubmission` is the accepted submission (operational fields plus
  the opaque values); `FormContext` carries what the form declared
  (heading, notify address, whether to store) so providers need no
  configuration lookups of their own.
- **Registry**: `register_forms_provider(name, factory)` /
  `create_forms_provider(name, ...)` with contract-version and
  interface validation at selection time — the same discipline as the
  deployment registry. `[forms] provider` selects; the default is
  `reference`.
- **The reference provider** implements the contract: persist when
  storage is on (first), then notify by mail — each leg contained and
  audited independently.
- **Containment is the endpoint's job**: whatever a provider raises is
  logged and audited, never visitor-facing. A provider cannot break
  the deterministic response contract.
- **Extensions** register providers via `Extension.forms_providers`;
  ecosystem naming is `sardine-forms-<name>`.

## Rules a provider must keep

- It only ever sees accepted submissions and must treat the values as
  plain text.
- It must not answer the visitor — its outcome never changes the HTTP
  response.
- Failures must raise (the endpoint contains and audits them) rather
  than being swallowed silently.
- Credentials come from the environment, never from configuration, and
  never enter logs or the audit trail.

A conformance suite runs these rules against every provider, including
an extension-registered one, and third-party authors run it against
theirs.

## Consequences

- The endpoint's pipeline stays fixed; growth happens in providers.
- The reference behaviour is unchanged — it becomes the bundled
  provider rather than inline code.
- The contract version starts at 1; additive evolution within it,
  breaking changes only with a new version validated at selection.
