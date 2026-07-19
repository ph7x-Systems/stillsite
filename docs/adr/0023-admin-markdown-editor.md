# ADR-0023 — Markdown editing gets a real editor (EasyMDE, vendored)

- **Status:** accepted
- **Date:** 2026-07-19

## Context

Article bodies are written in Markdown through a bare `<textarea>`. With
the theme's JavaScript layer in place (ADR-0020, CSP `script-src 'self'`),
the panel can offer a proper editing surface without breaking any of its
rules. The owner asked for a Markdown editor.

## Decision

- **EasyMDE 2.20.0** (MIT, the maintained fork of SimpleMDE), vendored
  verbatim with its license at `static/vendor/easymde/` — JS + CSS, no
  CDN, no build step, initialized from `static/admin.js` (no inline
  scripts).
- **Progressive enhancement**: the editor attaches only to textareas
  marked `data-markdown-editor` (the Markdown bodies — article source and
  translations). Without JavaScript the plain textarea still submits the
  same field; the server never knows the difference.
- **The builder's preview stays the truth.** EasyMDE's built-in
  preview/side-by-side/fullscreen buttons are disabled: its bundled
  renderer is not the product's CommonMark renderer (raw HTML disabled),
  and two previews that disagree are worse than one. The toolbar keeps
  formatting actions only (headings, emphasis, lists, links, quotes,
  code, guide).
- **Toolbar in the editor's language**: button titles come from the i18n
  catalogs (ADR-0022) — the template writes them into a
  `data-markdown-labels` JSON attribute, `admin.js` reads it. The msgids
  join the anti-drift inventory like every other string.

- **CSP**: CodeMirror positions and measures through element style
  attributes (as Popper already does for dropdowns), so `style-src` gains
  `'unsafe-inline'`. Scripts stay strictly `'self'`; templates still ship
  zero `style=` attributes (the hardening suite scans them) and
  autoescape keeps user content inert — the added surface is runtime
  styling by vendored code only.

## Consequences

- The a11y gate keeps running over the editor pages in both color
  schemes; EasyMDE's CodeMirror surface must stay AA-clean there.
- Summary/description textareas stay plain — they are short text, not
  Markdown.
- If a future block editor lands (M6 blocks), it supersedes this ADR
  explicitly; until then this is the writing surface.
