# ADR-0037 — Sections grow up: repeating groups, rich text and long-form pages

- **Status:** accepted
- **Date:** 2026-07-21

## Context

Pages are ordered lists of typed sections (ADR-0021 lineage): any kind
string, unlimited sections per page, reorderable, extensions add kinds
(ADR-0028), unknown kinds render generically. That part is open and
stays.

Three things are hammered, and the hammering lives where nobody can
see it:

1. **Repetition is numbered field names with invisible caps.** An FAQ
   is `q1/a1 … q6/a6`; an expertise list is `row1* … row8*`. The caps
   are `range()` calls inside theme templates — not in the model, not
   in validation, not in the editor. The seventh question silently
   never renders.
2. **Section fields are flat plain strings.** No Markdown anywhere
   inside a section: a CTA body cannot hold a link, a story cannot
   hold emphasis. The only rich text in the system is the article
   body.
3. **Pages have no long-form body.** `PageContent` is title,
   description and slug; every paragraph of page content must fit a
   pre-shaped kind. A page cannot simply be a document.

The mature-CMS benchmark solves editor expressiveness with a freeform
block editor whose blocks serialize into the post body as annotated
markup. That model is rejected here — not skipped, rejected: opaque
block soup in a body field defeats everything this framework is built
on. Translation states hang off structured content checksums; parity
validation needs to see fields; deterministic builds and the portable
JSON source of truth need data, not markup blobs. A multilingual site
with block-soup bodies cannot answer "which parts of this page are
untranslated?" — ours can, and must keep being able to.

## Decision

Structured sections remain the contract. They become expressive enough
that the structure stops being a cage:

1. **Repeating groups.** `SectionContent` gains
   `items: list[dict[str, str]]` — one ordered, unbounded repeating
   group per section. FAQ items are `{"question": …, "answer": …}`,
   expertise rows `{"no": …, "title": …, "detail": …}`. Items are
   content: they travel with translations, count into the checksum,
   and parity validation sees them. The numbered-field convention and
   its template caps are retired (storage migration + import mapping
   keep old content working, mapped into items).
2. **Markdown fields.** The section-kind gallery contract grows field
   *specs*: a kind declares which of its fields are Markdown, and
   those render through the same safe renderer as article bodies (raw
   HTML off). Extension kinds declare their own. Plain-string fields
   stay plain.
3. **Long-form pages.** `PageContent` gains `body_markdown` — rendered
   as prose between the page header and the sections. A page can be a
   document, a zone composition, or both. Translation state covers it
   like any content field.
4. **The editor keeps up, server-rendered.** Item rows get add/remove
   controls in the section editor; Markdown-declared fields get the
   same editor widget as article bodies; the existing per-entry live
   preview covers sections already. A drag-and-drop visual builder is
   **deferred, not decided**: it would require a client-side island
   beyond ADR-0010's budget, so it gets its own ADR with its own
   justification if the forms ever measurably fail editors.
5. **Zones are the theme's choice, never the engine's.** The engine
   renders any kind, any order, any count, unknown kinds included —
   documented as a standing guarantee. A theme that implements three
   kinds restricts *that theme*, not the site: switching themes never
   loses content.

## Consequences

- The template caps (`q6`, `row8`) disappear; theme conformance gains
  a check that bundled kinds render unbounded items.
- Storage schema version bumps (items column on sections); export
  format carries `items`; the WXR import maps repeated structures
  into items where recognizable.
- The editor grows item controls but stays form-based and
  server-rendered — no new dependencies.
- Docs must stop presenting numbered fields as the contract
  (THEME_GUIDE gallery table, wiki Themes page).

## Execution (phased, each phase its own PR)

1. **Model + storage**: `SectionContent.items`, `PageContent.
   body_markdown`, checksum coverage, storage migration on all four
   engines, export/import round-trip.
2. **Builder + themes + validation**: field specs in the gallery
   contract, Markdown field rendering, items rendering in both bundled
   themes (caps removed), parity validation over items, conformance
   test for unbounded items.
3. **Admin**: item add/remove rows in the section editor, Markdown
   widgets for declared fields, translation editors mirror items.
4. **Docs**: THEME_GUIDE gallery v2, ADMIN_GUIDE, wiki Content-Model /
   Themes / Admin-Panel, seed content exercising items.
