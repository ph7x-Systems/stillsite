# ADR-0030 — Foreign blog imports are explicit adapters

- **Status:** accepted
- **Date:** 2026-07-20

## Context

The portable JSON/Markdown pair is Sardine CMS's backup and migration
contract, but existing sites also need a controlled path into the system.
The first concrete source is the WXR 1.2 XML export format. Parsing it
requires the format's XML namespace identifiers to appear in source code;
treating those identifiers as forbidden hard-coded URLs would make a
conforming parser impossible.

## Decision

- Support WXR 1.2 through a named `cms import --format …` adapter. The native
  portable format remains the default.
- XML namespace strings are protocol identifiers, not endpoints. They may
  appear as constants only inside the foreign-format adapter and must never
  cause network access.
- Reject DTD and entity declarations before XML parsing. Import is a pure,
  deterministic conversion of supplied bytes into core models.
- Import blog posts only. Map title, slug, body, excerpt, author, date,
  workflow status, first category and tags; keep the foreign post id in an
  article custom field. Convert common HTML structure to Markdown.
- Skip pages, attachments, navigation items and comments with an explicit
  count. Inventing page-section or media semantics would overstate migration
  fidelity; those need separate adapters or project-approved mappings.
- `--replace` retains its existing upsert semantics for every input format.

## Consequences

- A site with a supported blog export can enter Sardine CMS without an
  intermediate bespoke script or a runtime dependency on the source system.
- Imported remote image references are preserved in Markdown but never
  fetched. Moving them into the media library remains an explicit migration
  step.
- Other source systems get their own named adapters. Their details do not
  leak into the portable schema or storage contract.
