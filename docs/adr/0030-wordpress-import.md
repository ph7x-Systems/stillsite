# ADR-0030 — Foreign blog import: WordPress WXR is an explicit adapter

- **Status:** accepted
- **Date:** 2026-07-20

## Context

The portable JSON/Markdown pair is Sardine CMS's backup and migration
contract, but it does not help an existing blog enter the system. WordPress
WXR is the first concrete foreign format requested. Parsing it requires the
format's XML namespace identifiers to appear in source code; treating those
identifiers as forbidden hard-coded URLs would make a conforming parser
impossible.

## Decision

- Support WordPress eXtended RSS 1.2 through `cms import --format wordpress`.
- XML namespace strings are protocol identifiers, not endpoints. They may
  appear as constants only inside the foreign-format adapter and must never
  cause network access.
- Reject DTD and entity declarations before XML parsing. Import is a pure,
  deterministic conversion of supplied bytes into core models.
- Import blog posts only. Map title, slug, body, excerpt, author, date,
  workflow status, first category and tags; keep the foreign post id in an
  article custom field. Convert common HTML structure to Markdown.
- Skip pages, attachments, menu items and comments with an explicit count.
  Inventing page-section or media semantics would overstate migration
  fidelity; those need separate adapters or owner-approved mappings.
- Keep the native portable format as the default. `--replace` retains its
  existing upsert semantics for either format.

## Consequences

- A WordPress blog can enter Sardine CMS without an intermediate bespoke
  script or a runtime dependency on WordPress.
- Imported remote image references are preserved in Markdown but never
  fetched. Moving them into the media library remains an explicit later
  migration step.
- Other foreign systems get their own named adapters. Their format details
  do not leak into the portable schema or storage contract.
