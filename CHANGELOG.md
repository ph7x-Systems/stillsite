# Changelog

All notable changes to Sardine CMS. The project follows semantic versioning
from `0.1.0`; the six packages release in lockstep under one `vX.Y.Z` tag.

## Unreleased — 0.1.0

The first release: a multilingual, static-first CMS framework.

- **Content core** (`sardine-cms-core`): articles, pages with ordered typed
  sections, media with mandatory translatable alt text; translation states
  (`missing / outdated / complete`) derived from content checksums; the
  `draft → review → published → archived` workflow; storage contract with
  SQLite and PostgreSQL backends behind `create_storage(url)`, shared
  versioned migrations, admin accounts (argon2id) that are never exported.
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
