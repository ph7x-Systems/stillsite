# ADR-0045 — Migrated media is fetched explicitly, safely and accountably

- **Status:** accepted
- **Date:** 2026-07-22

## Context

ADR-0030 keeps remote image references in imported Markdown but never
downloads them; ADR-0043 made "moving them into the media library" an
explicit later step of the migration flow. That step needs network
access — the first in the migration path — so its safety and failure
semantics must be decided, not improvised, and the admin flow will run
the same code later.

## Decision

- **Opt-in, never implicit.** `cms import --format wxr --fetch-media`
  downloads the images the imported posts' bodies reference, stores
  them in the media library and rewrites the body references to
  `/media/…` paths. Without the flag, nothing touches the network.
- **The fetcher is injected.** The orchestration lives in
  `cms_core.media_fetch` and takes a fetch callable; the default one
  (stdlib only) enforces the transport rules. Tests inject fakes and
  stay fully offline; the admin flow reuses the same orchestration.
- **Transport rules:** `http`/`https` only; the resolved host must be
  public (loopback, private, link-local and reserved ranges are
  refused — the admin will call this code, where request forgery is a
  real attack); 25 MB size cap; timeout per request; three attempts
  with backoff before a URL is declared failed.
- **Library rules hold.** Images must carry dimensions (probed with
  the optional imaging dependency; without it the URL fails with that
  reason) and alt text — taken from the source `alt` attribute the
  Markdown kept, or the filename as a last resort. Fetched assets land
  in the `imported` collection with their content hash.
- **Idempotent by content.** A downloaded file whose hash matches an
  existing asset reuses that asset instead of duplicating it; a re-run
  finds already-rewritten bodies and has nothing left to fetch.
- **Every URL is accounted for**: fetched (new asset), reused
  (existing asset) or failed (with its reason) — printed per URL,
  never summarized away.

## Consequences

- The migration keeps the source site's images without keeping the
  source site alive, and a failed URL is visible instead of silently
  leaving a remote reference behind.
- Attachment items nothing references are inventory in the report, not
  downloads: the flow fetches what published bodies actually use.
- The admin flow inherits a network step whose abuse surface was
  bounded before any UI existed.
