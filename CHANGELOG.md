# Changelog

All notable changes to Sardine CMS. The project follows semantic versioning
from `0.1.0`; the six packages release in lockstep under one `vX.Y.Z` tag.

## Unreleased

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
