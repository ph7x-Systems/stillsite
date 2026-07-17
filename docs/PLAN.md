# Execution Plan — Ph7x.CMS.Framework

Short plan by milestones, per the brief ([BRIEF.md](BRIEF.md)). Small increments, clear commits, reversible decisions recorded as ADRs.

## Milestone 0 — Foundation (current)

- [x] Repository initialized (`main`), folder structure, base docs
- [x] Repository published to GitHub (`ph7x-Systems/Ph7x.CMS.Framework`, private)
- [x] License: Apache-2.0 (`LICENSE`, `NOTICE`, ADR-0002)
- [x] Python toolchain: `pyproject.toml`, lint (ruff), type checking (mypy), pytest
- [x] GitHub Actions CI: lint, types, tests, docs link check, secret scan
      (content validation and example build jobs arrive with Milestone 2)
- [x] ADR-0001: base architecture (Python core + FastAPI admin)
- [x] Branch protection on `main`: force-pushes and deletions blocked; all six
      CI checks required (strict, up-to-date branches) for pull requests

## Milestone 1 — Content core

- [x] PoC — `cms-core` article schema with languages and per-language translations
      (pydantic; pages, sections and media schemas still pending)
- [x] Translation model: EN as source; `missing / outdated / complete` states
      derived from source checksums (outdated detection is automatic)
- [x] PoC persistence: SQLite via stdlib `sqlite3`, no ORM yet ([ADR-0003](adr/0003-sqlite-poc-persistence.md))
- [x] Storage backend factory ([ADR-0004](adr/0004-storage-backend-factory.md)):
      one `StorageBackend` interface + URL-scheme factory (`create_storage`);
      SQLite implemented; PostgreSQL, SQL Server and MySQL/MariaDB registered
      as planned engines; custom backends pluggable via `register_backend`
- [x] Versioned migrations (ordered scripts tracked via `user_version`)
- [x] Deterministic JSON/Markdown export as the portable source of truth
- [x] Pages composed of typed sections (`kind` maps to a theme template per the
      extensibility contracts); page state aggregates its sections (worst wins)
- [x] Media assets: mandatory EN alt text, translatable alt, image dimensions
      required, safe relative paths
- [ ] Server backends: PostgreSQL (prod target), SQL Server, MySQL/MariaDB —
      implement behind the ADR-0004 interface; shared-layer decision (e.g.
      SQLAlchemy) gets its own ADR; test via project-prefixed Docker containers

> **PoC anchor:** Milestones 2 and 4 are executed against a concrete target —
> reproducing the ph7x.com architecture (URL tree, head contract, design
> system) with fictional content, per [POC_PLAN.md](POC_PLAN.md). The original
> site is read-only reference; its documented bugs become design guarantees.

## Milestone 2 — Validation and build

- [ ] `cms-validation`: language parity, structure, editorial rules, configurable per project
- [ ] `cms-build`: deterministic generator — pages, listings, categories, tags, static search, RSS, sitemap, canonical, hreflang
- [ ] Theme interface: HTML rendering goes through a theme package (templates +
      design tokens + static assets); any template/partial/token overridable per
      project without forking the theme (design to be recorded in an ADR)
- [ ] CLI (`cms`): `validate`, `build`, `preview`, `export`, `seed` — Typer-based
- [ ] `cms init`: interactive scaffolding of new projects from Copier templates
      (kept in-stack instead of a Node-based generator; templates derive from
      `examples/multilingual-company-site`; record Copier decision as an ADR)
- [ ] Static export independent of the admin panel, ready for Azure Static Web Apps
- [ ] Deployment target adapters ([ADR-0005](adr/0005-deployment-target-adapters.md)):
      one deterministic artifact + per-target config via `cms export --target`
      — `swa` (Azure SWA Free and Standard, same artifact), `nginx` (on-prem/
      container), `generic`; `iis` when first needed; custom targets pluggable
      via `register_target`

## Milestone 3 — Admin panel

- [ ] Authenticated FastAPI API (explicit auth/authz, least privilege)
- [ ] Dashboard: content status, missing translations, validations, last build
- [ ] Page/section management and Markdown articles (per-language slug, SEO, cover image, tags)
- [ ] Side-by-side editor per language with translation indicators
- [ ] Media library (mandatory alt text, dimensions, type/size validation)
- [ ] Preview and `draft → review → published → archived` workflow

## Milestone 4 — Reference theme and example

- [ ] `cms-theme-ph7x-reference`: tokens, local fonts (Inter, Newsreader), inline SVG, 820px breakpoint, zero inline styles, `[hidden]{display:none!important}`
- [ ] `examples/multilingual-company-site` with fictional content in 5 languages
- [ ] Documentation: installation, architecture, content model, theme extension, deployment

## Extensibility contracts (cross-milestone)

Everything user-facing must be extensible without forking the framework:

- **Themes/designs**: a theme is an installable package (templates, design
  tokens, static assets). Projects pick a theme and may override any template,
  partial or token locally; the reference theme is just the default.
- **HTML output**: all HTML is produced by theme templates — no markup
  hardcoded in `cms-build`. Markdown rendering supports custom blocks/
  shortcodes so editors can embed rich HTML components without raw HTML.
- **Extensions/plugins**: registration points for custom content types,
  validation rules (`cms-validation` is configurable per project), build
  steps and CLI subcommands. Mechanism (entry points vs. explicit registry)
  decided in an ADR when the first extension lands.

## Open decisions

- Admin UI: server-rendered vs. lightweight TypeScript (decide in Milestone 3, with an ADR)
- Static search strategy (pre-generated index vs. lunr-like)

## Decided

- License: Apache-2.0 ([ADR-0002](adr/0002-license-apache-2.md))
- Remote repository: `ph7x-Systems/Ph7x.CMS.Framework` on GitHub (private; public later)

## Testing

Every documented guarantee has a test that fails when it stops being true —
layers, CI mapping and policies in [TEST_PLAN.md](TEST_PLAN.md). The storage
and theme conformance suites are public contracts for third-party backends
and themes.

## Security

Security is part of each milestone's definition of done — threat model,
controls in force and per-milestone gates are documented in
[SECURITY_STRATEGY.md](SECURITY_STRATEGY.md).

## Going public — when and how

The repository flips to public when it demonstrates a working product, not
promises — and only with zero documentation drift. Criteria (all objective):

1. **Milestone 2 complete**: `cms validate|build|export` work end-to-end and
   CI builds the example site on every push (the proof is executable).
2. **All CI gates green** on the flip commit, including the docs anti-drift
   suite and the head-contract/parity checks — this is what "no drift" means
   here: it is enforced by tests, not by a final proofread.
3. **Go-public checklist executed** (SECURITY_STRATEGY.md §4: history clean of
   personal emails, secret scan green over full history, no policy-ignored
   files tracked, dependencies reviewed, monitored security contact).
4. README reflects reality for a first-time visitor (install, quickstart,
   what works today vs. roadmap) — guarded by the anti-drift tests.

Recommended timing: **flip at the end of Milestone 2** (framework usable,
example site building in CI), and treat the end of Milestone 4 (reference
theme + polished example) as the **announcement/launch** moment. Between the
two, the repo is public but low-key. The flip itself happens via a PR that
records the executed checklist.

## Constraints

- No changes to the current corporate site (`Ph7x.Site.Corporate` / ph7x.com)
- No secrets, personal data or client content in this repository
- Irreversible actions, public publishing, costs or credentials require confirmation
