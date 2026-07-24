# Design Rules

The rules every theme — the built-in one, the reference theme, and any
third-party theme — must satisfy. They come from a decade of lessons on the
production site this framework was extracted from (docs/POC_PLAN.md records
their origin); the mechanical ones are enforced by the theme conformance
suite (TEST_PLAN.md §1.5), not by review alone.

## 1. Tokens, not values

- All colors, spacing, type scale and breakpoints live in **CSS custom
  properties** (design tokens) in the theme's base stylesheet. Components
  consume tokens; they never hardcode values.
- A project rebrands by overriding the token file (`theme/assets/…`,
  ADR-0007) — never by editing templates.

## 2. The non-negotiables (conformance-tested)

| Rule | Why |
| --- | --- |
| `[hidden]{display:none!important}` is the **first rule** of the base stylesheet | The browser's `[hidden]` rule has zero specificity; any `display:` utility silently defeats it. This killed a privacy notice and a consent-gated form once. |
| **Zero inline styles** | CSP-compatible output; styling stays overridable by token/asset shadowing. |
| **Local assets only** — fonts, scripts, styles ship in the theme; no CDNs | Privacy (no third-party requests), determinism, offline builds. |
| **Images always carry `width` and `height`** | No layout shift; the builder provides dimensions from the media model. |
| **No horizontal scroll at any width** | Checked at 360/820/1280px. |
| `prefers-reduced-motion` honored — effects opt out cleanly | Accessibility; effects are decoration, never information. |
| **Single-source assets** — a behavior/effect lives in exactly one file, referenced everywhere | Copy-pasting a script into two shells once produced three divergent sites. |
| **Flow-relative CSS only** — logical properties (`margin-inline-start`, `padding-inline`, `text-align: start/end`, `inset-inline-*`), never `-left`/`-right` or asymmetric four-value shorthands | Any language pack may declare `rtl` (ADR-0034); a physical property silently breaks every RTL site. The one exception: overriding a vendored bundle's physical property, which must name what upstream names. |

## 3. Layout and type

- Main breakpoint at **820px**; progressive `max-width` steps below it.
- One content measure (`--maxw`) shared by header, main and footer.
- Typography pairs a sans for UI (reference theme: Inter) with a serif for
  editorial voice (Newsreader), subset to latin + latin-ext, `woff2`,
  preloaded, local.

## 4. Semantics and accessibility

- Semantic landmarks (`header/nav/main/footer`), one `h1` per page, skip
  clutter. WCAG **2.2 AA** is the baseline; automated axe checks join CI with
  the reference theme (TEST_PLAN §2).
- Language switcher marks the active language (`aria-current`); every page
  declares `lang`.
- Interactive states (focus, hover) visible; contrast from tokens that pass
  AA in both light and dark schemes.

## 5. Modern web platform, no frameworks

Themes target the **web platform as it is today** — and stay static-first:

- **Progressive enhancement**: every page is complete HTML without
  JavaScript; scripts only enhance (search filtering, effects, menus).
- **Web Components (native custom elements)** are the unit of interactivity —
  small self-registering islands (`<site-search>`, `<site-nav>`) shipped as
  **ES modules** from the theme's assets. No framework runtime, no build
  step, no hydration: the HTML is already there.
- **Modern CSS over JS**: container queries, `:has()`, nesting and custom
  properties before reaching for script; view transitions welcome where they
  degrade gracefully.
- Budget: a theme's total JS stays small (the reference target is under
  20 KB, uncompressed, all-in) — if a feature needs more, it belongs in the
  admin, not the public site.

## 6. What themes never do

- Assemble `<head>` content, feeds or indexes — the builder generates them
  (head contract, JSON-LD, RSS, search index); templates only render what
  they receive.
- Embed editorial text — every user-facing string comes from the content
  model or site config.
- Reference assets by literal URL — always through `asset_urls` (hash-versioned
  by the builder; cache busting is automatic).

## Language scale: disclosure, never unbounded repetition

Language sets are data and unbounded (ADR-0034). Every surface —
lists, forms, editors, switchers — must therefore scale by
*disclosure*: aggregate first, then search, filter or expand into the
language being edited. No screen renders an unbounded run of
per-language controls; content lists keep constant-width aggregate
coverage, and editing surfaces open one language at a time past a
small threshold. A 30-language fixture in the test suite enforces
this for every future screen (#241).
