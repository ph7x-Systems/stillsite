# ADR-0027 — Design-aware editing: see the real theme while you edit

- **Status:** accepted
- **Date:** 2026-07-19

## Context

Editing happens in the panel; the design lives in the theme. Today the
bridge is the preview build (whole site, plus per-entry jump links) —
correct but coarse: the editor saves, rebuilds the preview, then looks.
The owner wants a deliberate decision on how editing and *seeing the
design* converge, before any implementation.

## Options considered

1. **WYSIWYG inside the panel** (edit on top of the rendered theme):
   rejected. It couples the admin to every theme's markup, breaks the
   theme contract (themes are packages, ADR-0012), and static-first
   guarantees would have to be faked in the browser.
2. **Design-aware side preview**: the editor pane keeps the form; beside
   it, an iframe renders the entry through the *real* builder and the
   *real* theme (the same `/preview/` pipeline, scoped to one entry),
   refreshed on save. No theme coupling — the theme renders itself.
3. **Live-preview islands**: option 2 plus a small JS layer that
   re-renders the iframe on a debounce while typing (server round-trip
   to a render endpoint, same renderer). More moving parts; needs its
   own security look (a render endpoint that accepts unsaved content).

## Decision

Owner-confirmed 2026-07-19. Adopt **option 2 now, option 3 later**: a split editor view — form on
the left, the themed entry in an iframe on the right, rendered by the
existing preview pipeline on every save. It reuses what exists (builder,
theme discovery, `/preview/` mount), keeps themes fully sovereign over
markup, and works with the CSP unchanged (`frame-ancestors` stays
`'none'` for the admin itself; the iframe is same-origin `/preview/`).
Option 3 becomes attractive once the autosave layer (M5, after
ADR-0020) exists — the same debounce that autosaves can refresh the
render.

## Consequences

- The editors gain a **Design preview** card: the entry framed from
  `/preview/` when a preview build exists, a pointer to the Publishing
  panel otherwise.
- **CSP nuance**: the admin document keeps `frame-ancestors 'none'`;
  responses under `/preview/` alone move to `frame-ancestors 'self'`
  (with `X-Frame-Options SAMEORIGIN`) so the same-origin editor can
  frame them — nothing external ever can.
- Live refresh (option 3) lands together with the autosave layer.
- The theme contract gains nothing to implement — that is the point.
