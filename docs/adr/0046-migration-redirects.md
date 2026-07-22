# ADR-0046 — Migration keeps source URLs alive, with three guarantees

- **Status:** accepted
- **Date:** 2026-07-22

## Context

A migrated site changes its address structure: the source site's
permalinks (dated paths, custom prefixes) become this site's
`/blog/<slug>/` addresses. Every inbound link, bookmark and search
result still points at the old paths. The project already has one
redirect mechanism — the `[redirects]` table the builder consumes and
the panel's slug-change flow writes — and the migration must feed it,
not invent a second one.

## Decision

- **Redirects record automatically at import.** Each imported post
  keeps its source permalink path (from the export's `link` element);
  when that path differs from the post's address on this site, the
  import records `source path → new address` in the project's
  `[redirects]` table. No flag: keeping URLs alive is what a migration
  is for, and the same-address case records nothing.
- **One mechanism.** The merge and the config writing move to
  `cms_build.redirects` (`merge_redirects`, `write_redirects`), shared
  by the panel's slug-change flow and the importer. Chains flatten,
  self-redirects never survive, and an address that becomes live again
  drops its stale redirect.
- **Three guarantees, held by construction:**
  - *Deterministic* — articles are processed in sorted order and the
    table is written sorted; the same export against the same project
    always produces the same map.
  - *Collision-free* — an address that is a live destination never
    remains a redirect source; a source path equal to its own target
    records nothing.
  - *Idempotent* — a re-run merges the same changes into the same map
    and leaves the file untouched when nothing changed.

## Consequences

- A migrated site answers its old URLs from the first build after the
  import, through the same fallback pages and target rules operators
  already know.
- An upstream slug change followed by `--update` flattens the chain:
  both the original permalink and the intermediate address point at
  the newest one.
- The admin migration flow inherits the same behaviour by calling the
  same code.
