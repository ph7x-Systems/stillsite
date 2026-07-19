# ADR-0024 — Scheduled publishing: the build is the clock

- **Status:** accepted
- **Date:** 2026-07-19

## Context

Editors expect to schedule content. A static-first CMS has no server at
request time, so "going live at 09:00" cannot be a runtime decision — it
must be a build-time one. The builder's core invariant (deterministic:
same input, byte-identical output, no wall-clock reads inside the build)
must survive.

## Decision

- Articles and pages gain an optional **`publish_at`** timestamp (UTC,
  storage migration 8 on all four engines, exported in the portable
  JSON).
- **The build is the clock**: `build_site(...)` takes an explicit
  `now` — content that is `published` but has `publish_at > now` stays
  out of the artifact entirely (pages, listings, feeds, sitemap, search
  indexes). The first build after the moment publishes it. Determinism
  holds: same content + same `now` = byte-identical output.
- The CLI and the admin pass `now = datetime.now(UTC)` at the boundary
  (command start / request time); tests pass fixed values.
- The workflow is unchanged: scheduling composes with `published` status
  — an entry is live when it is published **and** its moment has come.
  `publish_at` empty means "immediately once published".
- **Scheduled builds are the operator's cron**: the documented recipe is
  a scheduled CI job (e.g. GitHub Actions `schedule:`) running
  `cms export` + deploy, at whatever cadence the editorial calendar
  needs.

## Consequences

- Validation and translation gates apply to scheduled content exactly as
  to any published content — scheduling never bypasses the publish gate.
- The admin editors expose the field (native `datetime-local` input, no
  JS required); lists showing a "scheduled" hint arrive with the M5
  quick-actions work.
- A future on-publish webhook (M7) can trigger the build at the exact
  moment instead of a cadence.
