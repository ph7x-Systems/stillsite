# ADR-0043 — Migration is a flow: inspect first, idempotent by source id

- **Status:** accepted
- **Date:** 2026-07-22

## Context

ADR-0030 gave WXR 1.2 exports a safe, deterministic parser and a bulk
`cms import --format wxr` command. Real migrations are not one command:
operators need to see what an export contains before writing anything,
re-run imports as the source site keeps changing, and account for every
item the migration cannot carry. The importer already stores the foreign
post id in the `wxr_post_id` custom field; nothing consumed it yet.

## Decision

- **Inspection is a first-class artifact.** `inspect_wxr` produces a
  report without touching storage: importable post count, the author,
  category and tag inventories, referenced media URLs, the comment
  count, and one note per item left behind with its reason. Nothing is
  ever silently dropped — an item is either imported or listed.
- **Fidelity is a number with a definition.** Fidelity is the
  percentage of channel items the migration imports. Comments are not
  channel items; they are reported separately and do not enter the
  percentage.
- **Idempotency keys on the source id.** An import matches incoming
  posts against existing articles by the `wxr_post_id` field. A match
  never creates a duplicate — not even when the post's slug changed in
  a newer export. Matched entries are left untouched by default;
  `--update` opts into overwriting them from the source (the entity id
  is kept, so preview links, redirects and references survive).
- **`--replace` keeps its one meaning** — consent to write into a
  storage that already has content — for every input format.
- **Dry run needs no storage.** `--dry-run` parses, reports and exits;
  it works before a project even has a database.
- Author mapping, taxonomy mapping, media download and URL redirects
  are later parts of this flow and get their own decisions; the report
  already carries the inventories those parts will consume.

## Consequences

- Re-running an import against a living source site becomes safe:
  new posts arrive, known posts stay as edited locally unless the
  operator explicitly chooses source-wins.
- The report is the contract between the CLI flow and the future admin
  flow: the panel will render the same artifact, not invent its own.
- Every unsupported shape is visible with a count and a reason, so a
  migration's honesty does not depend on the operator reading source
  code.
