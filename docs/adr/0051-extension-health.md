# ADR-0051 — Extension health is declared, contained and visible in both faces

- **Status:** accepted
- **Date:** 2026-07-23

## Context

The Extensions screen (ADR-0050) shows whether an extension loads and
what it declares — but "loads" is not "works". A deploy provider whose
credentials expired, a forms destination whose endpoint moved or a
translation service that lost connectivity all load perfectly and fail
at the worst moment. `cms doctor` covers the machinery around content;
extensions need the same idea, from the extension's own point of view.

## Decision

- **Health is declared, never inferred.** The `Extension` contract
  gains one optional field, `health_check`: a callable returning a
  sequence of `HealthCheck(name, ok, detail)` results. An extension
  without one reports nothing — absence is not a failure, exactly like
  every other optional contribution (ADR-0028).
- **Checks are contained like everything else.** The panel and the CLI
  run a health check inside the same containment the load path uses: a
  raising check renders as a failed check with its error, never as a
  crash. Checks are synchronous and expected to be fast; a slow or
  network-bound check is the extension author's trade-off to document.
- **Two faces, one contract.** The Extensions screen shows each active
  extension's health results on its card, on demand (a Check health
  action — health calls may touch networks, so the operator decides
  when). `cms doctor` runs the same checks in its report, one line per
  check, FAIL when `ok` is false. No new mechanism: doctor's existing
  verdict semantics apply.
- **Health never gates.** A failing health check blocks nothing — not
  builds, not publishing, not activation. It informs the operator; the
  recovery lever remains deactivation, which keeps working without
  imports (ADR-0050 guarantee 5).

## Consequences

- Extension authors get a first-class place to say "here is how to
  tell my integration is alive", and operators get it surfaced where
  they already look.
- The conformance expectations for providers can require a meaningful
  `health_check`, turning "my extension works" into something a
  machine can ask.
- The translation-provider contract (#228) inherits this surface
  as-is: a provider's connectivity and quota state are health checks,
  not new UI.
