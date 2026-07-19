# ADR-0017 — Admin UI: AdminLTE (Bootstrap 5), vendored, CSS-only

- **Status:** accepted (supersedes the visual-layer decision of ADR-0015)
- **Date:** 2026-07-19

## Context

The owner wants the back office on **AdminLTE** (adminlte.io) — the widely
known open-source Bootstrap admin dashboard template — as the default look.
ADR-0015's native ph7x styling gave the admin a distinctive editorial skin,
but a conventional dashboard language is instantly familiar to every admin
user and ships a complete, battle-tested component vocabulary.

## Decision

- **AdminLTE v4.1.0** (MIT, ColorlibHQ) is vendored verbatim at
  `apps/admin/src/cms_admin/static/vendor/adminlte/` — `adminlte.min.css`
  (which bundles Bootstrap 5) plus its license file, served by the admin
  itself. No CDN, no npm toolchain, no modifications to the vendored file;
  the copyright banner and `ADMINLTE-LICENSE.txt` ship with it, satisfying
  the MIT terms.
- **CSS only — the admin still ships zero JavaScript.** No collapsible
  widgets, dropdowns or JS-driven components are used; below the desktop
  breakpoint the sidebar renders statically (overlay rule) instead of
  behind a JS toggle. The CSP with no script source (phase 9) is unchanged.
- `static/admin.css` becomes a small overlay: the local Inter/Newsreader
  subsets (OFL), the tin-rocket brand in the sidebar, state helpers, the
  no-JS fallbacks, and AA fixes (Bootstrap's code pink darkened).
- Templates use the AdminLTE/Bootstrap idiom (app-wrapper, dark sidebar,
  small-box stat cards, cards, striped tables, badges, form-controls) while
  keeping the semantic `admin-*` classes the test-suite and future tooling
  rely on.
- The axe gate (WCAG 2.2 AA) continues to run over the admin pages in CI.

## Consequences

- The admin looks like the dashboards people already know; the public site
  keeps the ph7x editorial identity — two surfaces, two languages, on
  purpose.
- Dependency surface: one vendored MIT stylesheet (~300 KB minified);
  updates are a file swap plus the visual gates.
- If richer interactivity is ever wanted (collapsible sidebar on mobile,
  dropdowns), Bootstrap's JS would need its own ADR revisiting the
  zero-JavaScript CSP stance.
