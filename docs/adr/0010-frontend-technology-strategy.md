# ADR-0010 — Frontend technology strategy: native platform, Web Component islands

- **Status:** accepted
- **Date:** 2026-07-17

## Context

Themes need a position on frontend technology before the reference theme is
built. The options were analyzed against the framework's non-negotiables:
static-first output, determinism, longevity (sites live for years untouched),
zero third-party requests, WCAG 2.2 AA, and a build pipeline that stays
Python-only (no Node toolchain — already decided when Yeoman was rejected,
ADR-0008).

## Analysis

| Option | Verdict | Why |
| --- | --- | --- |
| **React/Vue/Svelte SPA or meta-framework (Next/Nuxt)** | Rejected | Adds a Node build pipeline and a runtime the content doesn't need; hydration cost; framework churn conflicts with sites that must live untouched for years. |
| **Astro-style islands with a JS bundler** | Rejected | The right architecture, the wrong dependency: we already generate the HTML; adopting a second static generator for its island tooling duplicates the core product. |
| **HTMX / server-driven interactivity** | Rejected for the public site | Requires a server at runtime — breaks static-first. (May suit the M3 admin UI; decided there.) |
| **jQuery-era script soup** | Rejected | Unstructured, untestable, the drift bug class the site's history warns about. |
| **Native Web Components as progressive-enhancement islands** | **Adopted** | Zero dependencies, no build step, ES modules straight from theme assets; components are self-contained (custom elements + optional shadow DOM), testable, and the platform guarantees decade-scale stability. |

CSS: the platform now covers what frameworks once did — custom properties
(tokens), nesting, container queries, `:has()`, `prefers-*` media features,
view transitions. Baseline: features widely available in evergreen browsers;
anything newer must degrade gracefully.

JavaScript: ES modules only, total theme budget ≤ 20 KB uncompressed;
every page complete without JS (progressive enhancement). Client-side search
consumes the built `search-index.json` (the pre-generated-index side of the
PLAN's open decision — closed by this ADR).

## Decision

Themes build on the **native web platform**: semantic HTML from Jinja
templates, token-driven modern CSS, and interactivity delivered exclusively
as **native Web Component islands** shipped from theme assets as ES modules.
No frontend framework, no Node build step, no external requests.
DESIGN_RULES.md §5 carries the normative rules; the theme conformance suite
enforces the mechanical ones.

## Consequences

- The whole stack stays installable with `pip` alone; themes are data
  (templates + assets), not applications.
- Interactive features are additive and isolated — removing a script never
  breaks a page.
- The static search strategy is settled: pre-generated per-language index +
  a `<site-search>` island (demo readiness phase 4).
- The M3 admin UI decision (server-rendered vs. TypeScript) remains open and
  is unaffected: the admin is an application, not a theme.
