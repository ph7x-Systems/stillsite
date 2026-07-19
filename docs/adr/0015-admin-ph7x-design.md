# ADR-0015 — Admin UI design: the ph7x design system natively, hTWOo removed

- **Status:** superseded by [ADR-0017](0017-admin-adminlte.md) — the admin now
  uses vendored AdminLTE; this ADR's removal of hTWOo stands
- **Date:** 2026-07-18

## Context

ADR-0013 chose server-rendered FastAPI + Jinja for the admin — that stands —
and hTWOo as the component library. In practice hTWOo underdelivered: its
components assume host-provided Fluent theme variables and Fluent-style
markup scaffolding, and the resulting panel looked unstyled and unfinished
rather than professional. Meanwhile the repository already owns a complete,
proven design system: the ph7x editorial dark design the reference theme
ships (tokens, Inter/Newsreader font subsets, button and badge idioms).

## Decision

- **The admin adopts the ph7x design system natively.** `static/admin.css`
  defines the same tokens (`--bg #080809`, `--navy #0e1626`, `--panel`,
  `--head`, `--ink`, `--muted`, `--accent #d8cfc0`, …), uses the same local
  font subsets (Inter for interface, Newsreader for display; OFL license
  shipped alongside) and mirrors the site's button (`.btn`/`.btn-p`) and
  kick-line idioms.
- **hTWOo is removed entirely** — the vendored copy, every `hoo-*` class,
  and its documentation references. No component library replaces it: the
  admin is plain semantic HTML styled by one stylesheet, consistent with
  the no-framework stance of ADR-0010/0013.
- Muted text uses `#8b909c` (one shade above the site's `--muted`) so every
  pairing on the dark surfaces passes WCAG AA.

## Consequences

- One visual language across the whole product: the public reference theme
  and the admin read as the same family.
- The admin remains an application, not a theme; sites theming the public
  output do not affect the admin's look.
- The dependency surface shrinks: no third-party CSS to track or license.
- ADR-0013's remaining decisions (server-rendered Jinja, islands where
  needed, session cookies, interface-layer boundaries) are unchanged.
