# ADR-0013 — Admin UI: server-rendered FastAPI + Jinja with hTWOo

- **Status:** accepted; the hTWOo component-library choice is superseded by
  [ADR-0015](0015-admin-ph7x-design.md) (the admin uses the ph7x design
  system natively). Everything else here stands.
- **Date:** 2026-07-18

## Context

Milestone 3 builds the admin panel — the application that makes Stillsite a
full CMS: the entire editorial cycle runs in the browser. ADR-0001 fixed
FastAPI for the admin API and left the UI approach open (server-rendered vs.
lightweight TypeScript, to be decided here). ADR-0010 fixed the frontend
strategy for the *public* output: native web platform, no frameworks,
Web-Component islands for the few interactive parts. The admin is a different
surface — authenticated, stateful, form-heavy — but the same forces apply:
no build step, no framework churn, a small dependency surface that one
person can audit.

## Decision

- **Server-rendered UI in the same FastAPI application.** Pages are Jinja
  templates rendered by the API process; forms POST back and redirect
  (POST/redirect/GET). One process, one deployment unit, no separate SPA,
  no client-side router, no API/UI version skew.
- **hTWOo is the component library** (`n8design/htwoo`, MIT — Fluent Design
  in pure HTML/CSS/JS), vendored as local static assets served by the admin
  itself: no CDN, no Node toolchain, no fonts phoning home (Segoe sources
  stripped, system font stack). The COMPONENTS.md table maps admin surfaces
  to hTWOo components.
- **Web-Component islands where interactivity demands it** — the ADR-0010
  rule applies to the admin too: server-rendered HTML is the baseline, and
  small ES-module islands (no build step) add behavior only where forms
  cannot express it (e.g. the side-by-side editor's scroll sync, upload
  progress). Every admin page must remain functional without JavaScript
  except where the enhancement is the feature.
- **No TypeScript, no bundler.** If a concrete need appears that plain ES
  modules cannot serve, that change gets its own ADR — the burden of proof
  is on the tooling.
- **Session-cookie authentication, not bearer tokens.** A server-rendered
  UI pairs with `HttpOnly` + `Secure` + `SameSite=Strict` session cookies
  and anti-CSRF tokens on state-changing requests (SECURITY_STRATEGY, admin
  panel section). Token-based API auth can be added later for headless
  clients without changing this decision.
- **The admin is Interface-layer** (ADR-0006): it drives `cms-core`,
  `cms-validation` and `cms-build` through their public APIs — storage via
  `create_storage(url)` so every supported engine works unchanged — and
  never reaches into their internals or the database directly.

## Consequences

- One Python process serves API and UI; deployment is `uvicorn` behind any
  reverse proxy, with no frontend pipeline to maintain.
- Accessibility gates (WCAG 2.2 AA, axe) run over rendered pages the same
  way they run over the public site — one methodology, one script.
- The hTWOo copy vendored for evaluation inside the reference theme's
  `vendor/` directory moves to the admin package when the shell lands
  (phase 4); themes never depend on it.
- Interactive richness is bounded by what islands can express; that is the
  accepted trade-off, consistent with ADR-0010.
