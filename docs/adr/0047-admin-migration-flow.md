# ADR-0047 — The panel's migration flow is a second face of one pipeline

- **Status:** accepted
- **Date:** 2026-07-22

## Context

The WXR migration flow matured CLI-first (ADR-0043 through ADR-0046):
inspection with a fidelity report, idempotent application by source id,
mappings, media fetch and automatic redirects. The remaining gap is the
operator who migrates from the browser. Duplicating import logic in the
panel would guarantee divergence between interfaces.

## Decision

- **No new import semantics.** The panel calls the same functions the
  CLI calls: `inspect_wxr` produces the report the screen renders,
  `WxrMapping` carries the mapping form, `apply_wxr_import` (the
  matching loop, extracted to `cms_core.migration`) writes articles,
  `fetch_media_for_articles` fetches media and
  `cms_build.redirects` records redirects. The CLI is refactored onto
  the same shared functions, so there is exactly one pipeline.
- **Two steps, one stash.** Upload and inspect first — nothing is
  written; the report and the mapping form render from the same
  artifact the CLI prints. Running consumes a server-side stash of the
  uploaded bytes referenced by a random token with a 15-minute expiry;
  an expired or unknown token asks for the upload again. The stash
  lives in process memory: the panel is a single process, and the
  upload never touches the project directory before the operator
  confirms.
- **Bounded like every upload.** The export file honors the panel's
  existing upload size limit; parsing rejects DTD/entity declarations
  exactly as the CLI does (same parser).
- **Admin-only, audited.** The screen registers in the navigation
  registry at admin role; a run lands in the audit trail with the
  counts, never the file contents.
- **Failures are contained.** Media fetch outcomes render per URL —
  fetched, reused or failed with its reason — exactly like the CLI
  output; a failed URL never fails the migration.

## Consequences

- Behavior parity between CLI and panel is structural, not aspirational:
  a fix in the pipeline fixes both faces.
- The stash choice ties the flow to a single-process panel, which is
  the deployment model the admin already documents; a multi-process
  panel would revisit only the stash, not the pipeline.
- The screen inherits localization duties: its strings join every
  bundled admin catalog under the existing anti-drift guard.
