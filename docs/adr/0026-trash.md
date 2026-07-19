# ADR-0026 — Trash: deletion becomes reversible

- **Status:** accepted
- **Date:** 2026-07-19

## Context

The admin offered no way to delete articles or pages at all — because a
hard delete was the only primitive and hard deletes are unforgivable in
an editorial tool. Editors expect a trash: remove now, restore later,
purge deliberately.

## Decision

- Articles and pages gain a nullable **`deleted_at`** timestamp
  (storage migration 10, all four engines). Trashed means
  `deleted_at IS NOT NULL`; the storage API's hard `delete_*` stays, now
  reserved for the explicit purge.
- **Trashed content is invisible everywhere that matters**: excluded
  from builds (whatever its status), from validation, from the portable
  export, from the admin lists and dashboards. It exists only in the
  Trash view.
- **Admin flow**: every editor can *Move to trash* from the editor
  screens; the **Trash** page lists trashed articles and pages with
  *Restore* (any role) and *Delete forever* (admin role — the only hard
  delete in the panel). Trashing and restoring are recorded as
  revisions like any other save (ADR-0025), and media references from
  trashed content no longer block media deletion only after the purge.
- No auto-purge: nothing expires silently. Retention policies can come
  later as configuration, not behavior changes.

## Consequences

- `Project.load_content` (CLI and panel builds) filters trashed entries,
  so every consumer — builder, validator, exporter — sees the same
  world.
- The conformance suite covers the flag round-trip on every engine; the
  admin suite drives trash → restore → purge end to end.
