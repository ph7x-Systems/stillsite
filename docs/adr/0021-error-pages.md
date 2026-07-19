# ADR-0021 — Error pages: one contract for every target

- **Status:** accepted
- **Date:** 2026-07-19

## Context

The builder emitted only `404.html`, and only the SWA target wired it. A
missing path on `cms preview` or nginx showed the server's bare error
page; 401/403/5xx had no pages anywhere. There was no written contract
saying which error pages a build produces and how each deployment target
must serve them — so every target improvised.

## Decision

**The build emits four error pages at the artifact root, and every target
serves them.** This is the contract; the conformance tests enforce it.

| File | Serves HTTP status | Title label (localized) |
| --- | --- | --- |
| `401.html` | 401 | `error-unauthorized` |
| `403.html` | 403 | `error-forbidden` |
| `404.html` | 404 | `not-found` |
| `50x.html` | 500, 502, 503, 504 | `error-server` |

- All four render through the theme's existing `not_found` template — the
  theme contract does not change; the context differs only in `head`
  (title from the label above, canonical path of the page itself).
- Titles come from the UI label system (`cms_build.ui`), overridable per
  project via `[site.labels]`, translated in all five languages; the page
  itself renders in the source language (host error handling cannot
  negotiate language).
- Error pages carry `noindex` semantics by construction (they are not in
  the sitemap and no page links to them).

Per-target wiring:

- **SWA** (`staticwebapp.config.json`): `responseOverrides` for `401`,
  `403` and `404` → the matching page with the matching status code. The
  platform owns 5xx; `50x.html` still ships (harmless, forward-portable).
- **nginx**: `error_page 401 /401.html;`, `error_page 403 /403.html;`,
  `error_page 404 /404.html;`, `error_page 500 502 503 504 /50x.html;`.
- **generic**: the artifact contains the four pages; the target's README
  note tells the operator to map them (documented, not enforceable).
- **`cms preview`**: serves `<code>.html` for 401/403/404 and `50x.html`
  for 5xx with the correct status — never the dev server's bare page.

## Consequences

- Conformance: builder tests assert the four files exist in every build;
  target tests assert each config references them; the preview handler
  has its own test.
- Themes may override the look by overriding `not_found` — one template
  covers all four pages, which keeps the theme contract stable.
- Future statuses (e.g. 429) extend the same table here first, then the
  code.
