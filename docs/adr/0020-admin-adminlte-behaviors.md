# ADR-0020 — The admin adopts AdminLTE's JavaScript behaviors

- **Status:** accepted
- **Date:** 2026-07-19

## Context

ADR-0013 chose a server-rendered admin with zero JavaScript, and ADR-0017
kept that stance when AdminLTE 4 became the design system: the stylesheet
was vendored, the scripts were not. That left the theme half-implemented —
no sidebar toggle (below the desktop breakpoint the sidebar degraded to an
ugly static block), no dropdowns, none of the behaviors AdminLTE's own
reference pages ship. The owner's direction is to implement the design
faithfully, behaviors included.

## Decision

- Vendor and serve, verbatim with their licenses, the exact scripts the
  AdminLTE reference pages load: `adminlte.min.js` (v4.1.0, MIT),
  `bootstrap.bundle.min.js` (5.3.8, MIT) and OverlayScrollbars (2.11.0,
  MIT, CSS + JS). No CDN — the admin still serves everything itself.
- The one inline init snippet the reference pages use (OverlayScrollbars
  on the sidebar) moves to `static/admin.js`, because inline scripts stay
  forbidden.
- CSP gains exactly `script-src 'self'` — never `'unsafe-inline'`, never
  external hosts. Everything else in the security model is unchanged
  (sessions, CSRF, headers, role gates are all server-side; JavaScript is
  presentation only, and every page still functions without it).
- The chrome uses the behaviors the theme provides: sidebar toggle
  (`data-lte-toggle="sidebar"`), the user dropdown menu, treeview when
  nested navigation appears. The no-JS static-sidebar CSS fallback is
  removed.

## Consequences

- Server-side enforcement remains the security boundary; scripts add no
  new inputs. The hardening suite now asserts `script-src 'self'` and
  that templates reference only local script files with no inline bodies.
- The a11y (axe) CI gate keeps running over the rendered pages with the
  scripts active.
- Future admin conveniences that need JavaScript (autosave, client-side
  filtering) are unblocked, each still needing its own justification.
