# Changelog

All notable changes to Sardine CMS. The project follows semantic versioning
from `0.1.0`; the six packages release in lockstep under one `vX.Y.Z` tag.

## Unreleased

- **Featured and authorship** (M5, migration 11): articles gain a
  Featured flag — featured entries lead the home highlight while
  listings and feeds keep pure recency — and an editorial byline the
  themes render (site name when empty). The demo snapshot captures the
  Users page (its sidebar link 404ed), and a new anti-recurrence test
  asserts every sidebar entry exists in the snapshot. ADR-0027
  (proposed) records the direction for design-aware editing.

- **Media library filters** (M5): server-side search over id, path, MIME
  type and alt texts, plus quick views (images only, missing translated
  alt) with a shown-of-total counter — a plain GET form, no JavaScript
  required.

- **Users screen** (M5): admins manage accounts from the panel — create
  (with role and panel language), change roles, delete — with the
  safeguards that matter: you cannot delete yourself, and the last admin
  can neither be deleted nor demoted. The CLI remains the bootstrap for
  the first account.

- **Duplicate as draft and per-entry preview** (M5): one click copies an
  article or page — content, metadata and sections intact, fresh
  collision-safe id, workflow reset to draft, no schedule, no trash
  flag; and the editors link straight to the entry's own URL inside
  `/preview/`. The demo snapshot now captures the Trash page (it 404ed
  on the live demo).

- **Trash** (M5, ADR-0026): deleting becomes reversible — Move to trash
  hides an article or page from builds, validation, export and every
  list; the Trash page restores it exactly as it was, and Delete forever
  (admin role, trash-only) is the panel's single permanent removal.
  Storage migration 10 on all four engines.

- **Revisions with restore** (M5, ADR-0025): every article and page save
  from the panel keeps a snapshot (bounded at the newest 20 per entity,
  storage migration 9 on all four engines). The editors list the
  history; each revision shows a unified diff against the current
  content and restores with one click — the restore itself becomes a
  new revision, so it is always undoable.

- **Scheduled publishing** (M5, ADR-0024): articles and pages gain an
  optional `publish_at` (UTC) — published content with a future moment
  stays out of every build until a build runs after it; the build is the
  clock and stays deterministic for the same content and clock. Editors
  set it with a native date-time field (localized); storage migration 8
  covers all four engines; the portable export carries the field; the
  scheduled-builds CI recipe is documented in the admin guide.

- **Responsive lists**: the per-language columns collapse into one
  compact Translations cell of state-colored badges (linked to the
  translation editors; state also in the title and hidden text, never
  color alone), and every admin table sits in Bootstrap's
  `table-responsive` wrapper — no more horizontal page scroll on
  narrow screens.

- **Direct unpublish** (M5): published content goes straight back to
  draft with one click (publisher role and up) — no more
  archive-then-restore detour. The next build drops the entry from the
  site, as always.

- **Markdown editor for article bodies** (ADR-0023): EasyMDE (MIT,
  vendored, no CDN) with a Bootstrap-Icons toolbar in the editor's
  language, attached progressively — without JavaScript the plain
  textarea still works. The builder's server-rendered preview remains
  the single truth (EasyMDE's own preview is disabled). CSP note: style
  attributes are now allowed for vendored runtime code (CodeMirror,
  Popper); scripts stay strictly same-origin.

- **The admin panel speaks the editor's language** (ADR-0022): real
  gettext i18n — PT-PT, ES, FR and DE catalogs shipped, resolution by
  stored per-user preference (new language selector in the user menu,
  `cms admin create-user --language`) then `Accept-Language`, then EN.
  Storage migration 7 adds the preference column on all four engines. An
  anti-drift test keeps every catalog complete.

- The sidebar brand and the user avatar are now plain `<img>` elements
  styled entirely by AdminLTE's own rules (the invented sizing CSS is
  gone); the admin panel's localization strategy joins the M6 roadmap.

- **Admin chrome 1:1 with the AdminLTE reference pages**: theme-init
  before first paint (external file — the CSP still allows no inline
  scripts), the reference's stylesheet order, fullscreen toggle, the
  light/dark/auto color-mode switcher, and the canonical user menu
  (user-header/user-footer). The axe CI gate now audits the admin in
  **both color schemes**; the demo snapshot's Preview link points at the
  public site (the snapshot cannot serve /preview/).

- **Error pages for every host** (ADR-0021): each build now ships
  `401.html`, `403.html`, `404.html` and `50x.html` (localized titles via
  the label system, rendered through the theme's `not_found` template).
  The SWA config overrides 401/403/404, the nginx config maps all four
  groups including 500/502/503/504, and `cms preview` serves the site's
  own pages with the right status instead of the dev server's bare error
  page.

- **The admin ships the theme's behaviors** (ADR-0020): AdminLTE's own
  scripts, the Bootstrap bundle and OverlayScrollbars are vendored and
  served same-origin — working sidebar toggle (mobile included), user
  dropdown menu, automatic light/dark mode. CSP allows exactly
  `script-src 'self'`: no inline scripts, no CDN. The ugly no-JS static
  sidebar fallback is gone.

- **Admin design is now genuinely AdminLTE**: the panel renders exactly as
  the AdminLTE 4 reference pages do — Source Sans 3 (the font the theme
  itself asks for; OFL, local files) instead of the previous brand fonts,
  vendored Bootstrap Icons (MIT) across the sidebar, navbar and stat
  boxes, content headers with breadcrumbs, the canonical footer, and
  small-boxes with icons and footer links. `admin.css` no longer restyles
  the theme; it only adds the font-face, accessibility fixes and the
  no-JavaScript fallbacks.

- **Validation report** across the panel and CLI: `Report` now carries one
  `RuleResult` per rule that ran (passing rules included, each with a
  human description). The admin dashboard and publishing pages share a
  full report — gate callout with the validated scope, a per-rule outcome
  table, and issues linked to their edit screens; `cms validate` prints
  the per-rule outcomes too.
- The seeded example keeps one article in review with a missing DE
  translation, so fresh projects and the demo show the publish gate
  holding a real warning.
- Package `__version__` attributes now derive from the installed
  distribution metadata (they were stuck at `0.1.0`); a test keeps all six
  pyproject versions in lockstep.

## 0.1.1 — 2026-07-19

Documentation release: every package ships a proper PyPI description —
what it does, how to install it (including the database extras), and links
to the live demo, repository and documentation. No code changes.

## 0.1.0 — 2026-07-19

The first release: a multilingual, static-first CMS framework.

- **Content core** (`sardine-cms-core`): articles, pages with ordered typed
  sections, media with mandatory translatable alt text; translation states
  (`missing / outdated / complete`) derived from content checksums; the
  `draft → review → published → archived` workflow; storage contract with
  SQLite, PostgreSQL, MySQL/MariaDB and SQL Server backends behind
  `create_storage(url)`, shared versioned migrations, admin accounts (argon2id) that are never exported.
- **Validation** (`sardine-cms-validation`): composable rule engine —
  required translations, unique slugs per language, media references,
  alt-text coverage, known categories. Errors block publishing.
- **Builder** (`sardine-cms-build`): deterministic static builds (same input,
  byte-identical output), full multilingual SEO (canonical, hreflang, Open
  Graph, JSON-LD, sitemap, RSS), localized UI labels, theme discovery via
  entry points (`sardine.themes`), deployment targets (generic, Azure Static
  Web Apps, nginx), safe CommonMark rendering with raw HTML disabled.
- **CLI** (`sardine-cms-cli`): `cms init | seed | validate | build | export |
  preview | admin create-user` over a `sardine.toml` project file.
- **Admin** (`sardine-cms-admin`): the full editorial cycle in the browser —
  side-by-side translation editors, media library with sniffed-bytes upload
  validation, role-gated workflow with a publish gate, panel builds/exports
  with a served preview; server-rendered, zero JavaScript, CSP with no
  script source, WCAG 2.2 AA gated in CI; styled natively with the ph7x
  design system.
- **Reference theme** (`sardine-cms-theme-ph7x-reference`): the ph7x
  editorial dark design as a standalone theme package with local fonts and
  CSS-only motion.
