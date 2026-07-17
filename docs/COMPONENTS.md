# Component Inventory

Every user-facing component, where it lives, and its contract. Anti-drift:
`tests/test_docs.py` asserts that every custom element a theme ships is
documented here.

## Public site — theme chrome (server-rendered)

Rendered by theme templates from builder-provided context
([THEME_GUIDE.md](THEME_GUIDE.md) documents the contexts):

| Component | Template | Context it consumes |
| --- | --- | --- |
| Site header + navigation | `base.html.j2` | `nav.home_url`, `head.site_name` |
| Language switcher | `base.html.j2` | `nav.languages` (code, url, current) |
| Head contract block | `base.html.j2` | `head` (canonical, hreflang, OG, JSON-LD) |
| Page sections | `page.html.j2` | `sections` (key, kind, fields, images) |
| Article body + meta | `article.html.j2` | `article` (title, date, category, tags, body_html) |
| Listing + pagination | `listing.html.j2` | `listing` (entries, page/pages, prev/next) |
| Not-found | `not_found.html.j2` | `not_found.home_url`, localized `head.title` |
| Footer | `base.html.j2` | `footer.text` |

UI strings come from the localized label system (`cms_build.ui`,
overridable via `[site.labels]`) — components never hardcode text.

## Public site — Web Component islands (progressive enhancement)

Native custom elements shipped as ES modules in theme assets (ADR-0010);
every page is complete without them. Total JS budget ≤ 20 KB (tested).

| Element | Asset | Attributes | Behavior |
| --- | --- | --- | --- |
| `<site-search>` | `assets/search.js` | `index-url`, `label` | Filters listings from the per-language `search-index.json`; same-origin fetch only; results announced via `aria-live` |

Planned islands (reference theme, Milestone 4): background network effect,
reveal-on-scroll, mobile menu toggle — each its own single-source module,
honoring `prefers-reduced-motion`.

## Admin panel (Milestone 3 — planned)

Leading candidate for the component set: **hTWOo** (`n8design/htwoo`, MIT —
Fluent Design in pure HTML/CSS/JS; see PLAN "Open decisions"; final call in
the M3 ADR). Vendored as local assets, no CDN. Intended mapping:

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
