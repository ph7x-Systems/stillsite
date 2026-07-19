# ADR-0025 — Content revisions: a bounded history with restore

- **Status:** accepted
- **Date:** 2026-07-19

## Context

Last write wins everywhere: an editor who overwrites a body or a
translation has no way back. Editors expect revisions with restore.

## Decision

- Every successful **article or page save from the admin** appends a
  revision: the full entity snapshot (`model_dump_json` — source,
  translations, sections, metadata) with author and moment. Storage
  migration 9 creates the `revisions` table (all four engines through the
  shared migrations); the history is **bounded** at
  `StorageBackend.REVISION_LIMIT` (20) per entity — older rows are pruned
  on write, so the table cannot grow without limit.
- The editors show the history (moment, author) with a per-revision
  detail page: a unified diff of the source Markdown against the current
  state, and **Restore**. Restoring validates the snapshot back through
  the model (`model_validate_json`), keeps the entity id, bumps
  `updated_at` and saves — which itself records a new revision, so a
  restore is never destructive and is itself undoable.
- Revisions are editorial history, not backup: they live in the database,
  are **never exported** (the portable JSON stays the source of truth of
  *current* content), and vanish with `delete_article`/`delete_page`.

## Consequences

- The conformance suite covers append/list/load/prune on every engine.
- Section and translation edits are captured because they save the whole
  parent entity.
- A future diff-per-field view or a higher limit are UI/config changes,
  not schema changes.
