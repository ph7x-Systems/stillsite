# Changelog

Per-version changes in Added / Changed / Fixed / Removed form. The
project follows semantic versioning from `0.1.0`; the six packages
release in lockstep under one `vX.Y.Z` tag. Narrative release notes —
features with their PRs, breaking changes and migrations — live in
[RELEASE_NOTES.md](RELEASE_NOTES.md).

## Unreleased

### Added

- In-editor media picker: covers and section media are chosen from a
  visual library grid (thumbnails, dimensions, undersized-image flag)
  with no script required; the ID inputs remain the precise path
  (#136).

- Media replace-file flow: swap the file behind an asset while the ID
  and every reference stay valid; alt texts, collection and focal
  carry over, an out-of-bounds crop is cleared, and duplicate bytes
  are refused naming their owner (#136).

- Modern image formats by default: every raster image ships WebP/AVIF
  variants (of the base size and of each configured responsive width)
  whenever the environment can encode them; both bundled themes render
  them as picture sources and the Content API lists them in a new
  additive `sources` field. `[build] modern_image_formats = false`
  turns it off (#136).

- Media crop and focal point: an optional crop stored as data and
  applied at build — the published image, its dimensions and every
  derivative descend from the cropped area while the original stays
  untouched — and a focal point carried in image metadata (themes and
  the Content API) (#136; migration 23).

- Media collections, usage counts and duplicate prevention: assets
  carry an optional collection (filterable in the library) and the
  SHA-256 of their bytes — identical uploads are refused naming the
  existing asset; the list shows how many entries use each asset
  (#136; migration 22).

- Deployment provider framework: a versioned `DeployProvider` contract
  with a registry (`register_deploy_provider`), per-provider settings
  from the raw `[deploy]` table, capability declaration the panel
  adapts to, selection-time validation, a conformance suite any
  provider can run, and extension registration
  (`Extension.deploy_providers`) — a third destination needs zero core
  changes (#156).

- Azure Static Web Apps deployment provider behind the same contract:
  authenticated upload of immutable releases, deployment tracking with
  transient panel phases, health verification, rollback by re-sending
  a kept release — with the token read from the environment at deploy
  time and never stored, logged, audited or echoed (#156).

- Automated deployment, filesystem/Nginx reference provider: publish
  and unpublish end on the public site through immutable releases,
  atomic symlink activation, health checks with automatic rollback,
  panel-side manual rollback without rebuild, concurrency locking, a
  scheduled-window watcher and full audit-trail coverage (#156).

- Needs-attention dashboard: review queue, pending translations,
  scheduled changes within 7 days and stale drafts — each card linking
  to its work, with a real all-clear state (#135).

- Audit trail: append-only activity records for sign-ins, transitions,
  trash/purge, media, user/role/2FA changes and builds, with an
  admin-only Activity screen and startup retention pruning (#134;
  migration 21).

- Configurable source language (`[site] source_language`, ADR-0034).
- Language packs carry everything: site labels, dates, admin catalogs,
  `native_name`; data-only packs; authoring guide and `sardine-lang-<tag>`
  naming; CI drives an RTL build through the accessibility gate.
- Repeating `items` in sections, kind-declared Markdown fields and
  long-form page bodies (`body_markdown`) — model, storage, both
  themes, editors, portable format (ADR-0037; migrations 18–19).
- Page editor UX: block gallery with auto-derived keys, duplicate,
  hide/show, delete with undo, drag reorder (#127).
- Browser onboarding: first-run setup wizard and guided deployment
  choice with persisted target and go-live feedback (#128).
- Global admin search over articles, pages, sections and media in
  every language (#129, ADR-0038).
- Bulk actions with per-entry rules and outcome report (#130).
- Translation queue and "missing «tag»" list filters (#131).
- Editorial calendar with drag-to-reschedule (#132).
- Scheduled unpublish: `unpublish_at` publication windows (#133;
  migration 20).
- Editorial-flow check (`scripts/editor_flow_check.py`) in CI.
- Operational model documentation (DEPLOYMENT.md, #152).
- Internal dependency bounds (`>=0.2.0,<0.3`) and OIDC-first/token-
  fallback publishing.

### Changed

- Deployment documentation split by audience: a short Deployment Guide
  for operators (operating models, configuration reference, complete
  examples, one consolidated troubleshooting table), a Deployment
  Providers overview, and a Writing a Deployment Provider developer
  guide (contract, registration, example, conformance rules, store
  layout). Public pages no longer reference issues or decision
  records.

- The Content API documentation is written for the API consumer:
  endpoints, response contract, guarantees and a short example;
  verification detail moved to the test plan (#165).

- Flow-relative CSS only in themes and panel (RTL end to end),
  conformance-enforced.
- Media alt text requires *some* language, not a hardcoded one.
- Content lists show constant-width translation coverage, never a
  column per language.
- The roadmap became a product plan with an issue-tracked queue and an
  explicit definition of done; documentation split by concern (#155).
- The comments capability is recorded as partial (contract without an
  official provider).

### Fixed

- The builder no longer skips pages of a non-default source language.
- The publishing flow's editor check types through the Markdown
  widget's real surface (silent-loss case caught by the in-repo check).

## 0.2.0 — 2026-07-21

Editorial completeness (M5), extensibility and adoption (M6) and
operations (M7) in one release — see
[RELEASE_NOTES.md](RELEASE_NOTES.md) for the full account.

### Added

- Scheduling, revisions with restore, trash, duplicates, previews with
  autosave and live refresh, quick actions, featured, authorship,
  editorial notes, users screen (M5).
- Extension contract (ADR-0028), menu manager, image derivatives,
  redirects, portable round-trip, external blog import, section-kind
  gallery, comments contract (ADR-0031), versioned JSON content API
  (M6).
- Pluggable email with enumeration-safe password reset and editorial
  notifications (ADR-0032), TOTP two-factor with per-role enforcement
  (ADR-0035), signed on-publish webhooks (ADR-0036), `cms doctor`
  (M7).
- Admin panel localization (ADR-0022); storage migrations up to 17.

## 0.1.x — 2026-07

First public releases: content core with checksum translation states,
four storage engines behind one conformance-tested contract,
validation engine, deterministic builder with SEO head contract,
themes with overrides, deployment targets, the `cms` CLI and the full
browser admin (WCAG 2.2 AA gated in CI).
