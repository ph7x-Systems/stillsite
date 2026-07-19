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

## Admin panel (Milestone 3 — in progress)

Server-rendered Jinja inside the FastAPI process
([ADR-0013](adr/0013-admin-ui-architecture.md)), built on **AdminLTE 4**
(MIT, vendored verbatim with its license at `static/vendor/adminlte/`,
Bootstrap 5 bundled — [ADR-0017](adr/0017-admin-adminlte.md)), behaviors
included ([ADR-0020](adr/0020-admin-adminlte-behaviors.md)): the theme's
own scripts (adminlte.min.js, Bootstrap bundle, OverlayScrollbars) ship
vendored and same-origin — sidebar toggle, user dropdown, treeview all
work as the theme intends, with a CSP of exactly `script-src 'self'` (no
inline, no CDN). The design is AdminLTE's, implemented as its reference
pages do:
**Source Sans 3** (the font AdminLTE's own `--bs-font-sans-serif` asks
for; OFL, local variable-font files at `static/vendor/source-sans/`) and
**Bootstrap Icons** (MIT, vendored at `static/vendor/bootstrap-icons/`)
for nav/navbar/small-box icons — `static/admin.css` never restyles the
theme, it only adds the font-face, accessibility fixes and no-JS
fallbacks. Chrome per the reference: navbar with icon links and the user
menu, dark sidebar (`sidebar-brand` + `sidebar-menu` with `nav-icon bi`),
content header with `breadcrumb`, `app-footer` with copyright. Surfaces:

| Admin surface | AdminLTE/Bootstrap building blocks |
| --- | --- |
| Shell chrome (all authenticated pages) | app-header navbar, dark app-sidebar with the tin-rocket brand, skip link |
| Dashboard | small-box stat tiles per status, cards, striped coverage table + progress |
| Content lists | cards with striped/hover tables in Bootstrap `table-responsive` wrappers; one compact **Translations** cell of per-language badges (state in color + title + hidden text, linked to the translation editors) |
| Side-by-side editors | Bootstrap grid (`row`/`col`, `admin-sbs`), cards, Markdown preview panel |
| Forms | `form-control`/`form-label` (+ mono textarea), form-text hints, alert block |
| Markdown editor (article bodies) | EasyMDE (MIT, vendored at `static/vendor/easymde/` — ADR-0023), Bootstrap Icons toolbar, localized titles, no built-in preview (the builder's preview is the truth) |
| Workflow (status transitions) | role-filtered button group (`admin-workflow`), per-status badge colors |
| Publishing panel | gate `callout` (success/danger), rules + issues tables in cards, target select, buttons |
| Editorial notes (editors) | comment trail card with inline add form, author-or-admin removal |
| List quick actions | per-row Bootstrap dropdown (bi-three-dots): workflow transitions + trash |
| Trash | sidebar entry, per-kind tables with Restore / admin-only Delete forever |
| Design preview (editors) | card with a same-origin iframe onto `/preview/<entry>`, pointer to Publishing when no build exists |
| Revisions (editors) | history card + detail page with unified diff in `admin-preview`, restore button |
| Menu manager | items table + add/update card (per-language labels), publisher-gated writes |
| Users screen (admin) | accounts table with inline role select, new-account card |
| Language selector (user menu) | `form-select` in the AdminLTE `user-body`, POST + CSRF like every form |
| Validation report (shared partial) | `callout callout-success/-danger` verdict, `.table` per-rule outcomes with `text-bg-*` badges, issue subjects linked to edit screens |

The admin remains an application (not a theme); sites theming the public
output do not affect the admin's look.
