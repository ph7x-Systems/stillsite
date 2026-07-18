# Component Inventory

Every user-facing component, where it lives, and its contract. Anti-drift:
`tests/test_docs.py` asserts that every custom element a theme ships is
documented here.

## Public site — theme chrome (server-rendered)

Rendered by theme templates from builder-provided context
([THEME_GUIDE.md](THEME_GUIDE.md) documents the contexts):

| Component | Template | Context it consumes |
| --- | --- | --- |
| Site header + navigation | `base.html.j2` | `nav.home_url`, `nav.menu` (blog + published pages, localized), `head.site_name` |
| Language switcher | `base.html.j2` | `nav.languages` (code, url, current) |
| Head contract block | `base.html.j2` | `head` (canonical, hreflang, OG, JSON-LD) |
| Page sections | `page.html.j2` | `sections` (key, kind, fields, images) |
| Article body + meta | `article.html.j2` | `article` (title, date, category, tags, body_html) |
| Listing + pagination | `listing.html.j2` | `listing` (entries, page/pages, prev/next) |
| Not-found | `not_found.html.j2` | `not_found.home_url`, localized `head.title` |
| Footer | `base.html.j2` | `footer.text`, `footer.menu` |

UI strings come from the localized label system (`cms_build.ui`,
overridable via `[site.labels]`) — components never hardcode text.

## Public site — Web Component islands (progressive enhancement)

Native custom elements shipped as ES modules in theme assets (ADR-0010);
every page is complete without them. Total JS budget ≤ 20 KB (tested).

| Element | Asset | Attributes | Behavior |
| --- | --- | --- | --- |
| `<site-search>` | `assets/search.js` | `index-url`, `label` | Filters listings from the per-language `search-index.json`; same-origin fetch only; results announced via `aria-live` |

The reference theme adds **no JavaScript**: its effects (aurora, grain,
reveal-on-scroll) are modern CSS only — gradients, an inline-SVG noise data
URI and scroll-driven animations behind `@supports`, all disabled under
`prefers-reduced-motion` (ADR-0010's CSS-over-JS rule). It also adopts the modern platform end to end: oklch color tokens with `color-mix()` states, cross-document View Transitions, a sticky glass header (`backdrop-filter`), `text-wrap: balance/pretty`, and declarative Speculation Rules prerendering (inline JSON, not JavaScript).

### Reference theme section kinds (`cms-theme-ph7x-reference`)

| Kind | Markup |
| --- | --- |
| `hero` | ph7x hero: `kicker` kick line, `lead` right-aligned lead-line, serif display `heading` + italic `accent`, base row with description + menu CTAs, optional hero image |
| `latest-articles` | Kick + serif `h2` + the language's three newest articles as `b-card`s |
| `story` | Two-column `.two` grid: sticky kick label + `h2`/`body` prose |
| _any other_ | Generic field/image rendering (graceful fallback) |

## hTWOo component set (vendored, reserved for the admin)

hTWOo Core 2.7.1 lives in `packages/cms-theme-ph7x-reference/vendor/` (MIT,
license alongside; Segoe web-font fetches stripped, reduced-motion
kill-switch appended). The public reference theme uses the ph7x design
system instead; hTWOo is the component set **decided** for the Milestone 3
admin UI ([ADR-0013](adr/0013-admin-ui-architecture.md)) — the copy moves
into the admin package when the shell lands (phase 4).

## Admin panel (Milestone 3 — in progress)

Decided in [ADR-0013](adr/0013-admin-ui-architecture.md): server-rendered
Jinja inside the FastAPI process, **hTWOo** (`n8design/htwoo`, MIT — Fluent
Design in pure HTML/CSS/JS) vendored as local assets, no CDN, islands per
ADR-0010. Mapping:

| Admin feature | hTWOo components |
| --- | --- |
| Dashboard (content/translation status) | cards, pivot, progress indicators |
| Content lists | details list/table, command bar, search box |
| Side-by-side translation editor | split panels, text fields, persona/status badges |
| Media library | file list, dialogs, upload button, image cells |
| Workflow actions (draft→review→published) | buttons, dialogs, message bars, toggles |
| Validation results | message bars, callouts |

The admin remains an application (not a theme); its component decisions do
not constrain public-site themes.
