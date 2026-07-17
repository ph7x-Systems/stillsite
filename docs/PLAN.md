# Execution Plan — Stillsite

Short plan by milestones, per the brief ([BRIEF.md](BRIEF.md)). Small increments, clear commits, reversible decisions recorded as ADRs.

## Milestone 0 — Foundation (current)

- [x] Repository initialized (`main`), folder structure, base docs
- [x] Repository published to GitHub (`ph7x-Systems/stillsite`, public)
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
- [x] PostgreSQL backend ([ADR-0009](adr/0009-postgres-backend.md)): psycopg 3,
      optional extra `cms-core[postgres]`, shared ANSI migration history,
      conformance suite green in CI (service container) and locally (Docker)
- [ ] SQL Server and MySQL/MariaDB backends — same mold as ADR-0009

> **PoC anchor:** Milestones 2 and 4 are executed against a concrete target —
> reproducing the ph7x.com architecture (URL tree, head contract, design
> system) with fictional content, per [POC_PLAN.md](POC_PLAN.md). The original
> site is read-only reference; its documented bugs become design guarantees.

## Milestone 2 — Validation and build

Layering and development rules for this milestone are fixed in
[ARCHITECTURE.md](ARCHITECTURE.md) / [ADR-0006](adr/0006-layered-architecture.md).

- [x] `cms-validation`: composable rule engine (enable/disable per project) with
      core rules — required translations, unique slugs per language, media
      references, alt-text coverage; publishing gated on zero errors
- [x] `cms-build` MVP: deterministic generator — pages with typed sections,
      articles with safe Markdown (raw HTML disabled), per-language listings,
      RSS, search index, sitemap, robots, canonical + full hreflang cluster,
      hash-versioned assets
- [x] `cms-build` follow-ups: categories (localized labels from config), tags,
      listing pagination, 404 page, JSON-LD (organization on home, Article on
      posts), media file pipeline (`media/` copied into the artifact)
- [x] Theme interface: rendering goes through a registered theme package
      (`register_theme`); built-in minimal `default` theme (templates +
      assets, autoescape everywhere)
- [x] Theme overrides ([ADR-0007](adr/0007-theme-overrides.md)): file shadowing
      under the project's `theme/` — any template or asset, no fork
- [x] CLI (`cms`, Typer): `seed`, `validate`, `build`, `export`, `preview`
- [x] `cms init` ([ADR-0008](adr/0008-cms-init-copier.md)): Copier-based
      scaffolding shipped inside `cms-cli`; `.copier-answers.yml` enables
      `copier update` on generated projects
- [x] Static export independent of the admin panel, ready for Azure Static Web Apps
- [x] Deployment target adapters ([ADR-0005](adr/0005-deployment-target-adapters.md)):
      `swa` (Free and Standard, same artifact), `nginx` (conf + Dockerfile),
      `generic`; custom targets pluggable via `register_target`; `iis` when
      first needed

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

## Next steps (priority order)

1. ~~Close Milestone 2 — PoC parity~~ **done** (categories/tags/pagination,
   404, JSON-LD, media pipeline, theme overrides ADR-0007, `cms init`
   ADR-0008).
2. **Close Milestone 1 — server backends**: PostgreSQL behind the ADR-0004
   interface, conformance-tested against a fresh project-prefixed Docker
   container (`ph7x-cms-postgres`); SQL Server and MySQL/MariaDB follow the
   same mold.
3. **Milestone 3 — admin panel** (FastAPI): auth/roles, translation-status
   dashboard, side-by-side per-language editor, media library, editorial
   workflow.
4. **Milestone 4 — reference theme + launch**: extract the real design system
   into `cms-theme-ph7x-reference`, polish the example, installation docs —
   then the public announcement.

Small pending items: GitHub social preview upload (owner, web UI only);
reserve the PyPI names (`stillsite`; decide `stillsite-*` vs `cms-*`
distribution naming at first release, with an ADR); rename the local working
folder to match the project name.

## Demo readiness plan (stillsite.ph7x.com)

The public demo is live and auto-deployed from `main`. "Demo = ready" means a
visitor can judge the product from it. Phases, in execution order:

1. **Infrastructure** — ✅ done: Azure SWA Free, custom domain + SSL,
   deploy-on-merge workflow building with the real CLI.
2. **PostgreSQL backend (closes Milestone 1)** — ✅ done (ADR-0009): the
   conformance suite passed unchanged against PostgreSQL 16 in CI and
   locally; required check number eight.
3. **Demo content** — ✅ done: 6 articles across 3 categories with tags, an
   about page, and a compass illustration through the media pipeline (the
   seed also writes referenced media files, so scaffolded projects build
   with no broken references); ~100 pages across the 5 languages.
4. **Client-side search** — ✅ done: the `<site-search>` Web Component island
   (ADR-0010) filters listings from the per-language `search-index.json`;
   localized labels via the new UI-label system (`[site.labels]` override);
   pages stay complete without JavaScript; theme JS budget enforced by test.
5. **Reference theme (Milestone 4)** — `cms-theme-ph7x-reference` implements
   the PoC design system (tokens, Inter/Newsreader local fonts, 820px
   breakpoint, dark editorial look, effects); the demo switches to it via
   `theme = "ph7x-reference"`. Acceptance: theme conformance tests green
   (hidden rule, no inline styles, local fonts only, reduced-motion).
6. **Ready gate** — WCAG 2.2 AA automated checks green on the built demo,
   all five languages complete, README quickstart links the demo, social
   preview uploaded. Then the Milestone 4 announcement.

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

## Design and themes

Normative design rules live in [DESIGN_RULES.md](DESIGN_RULES.md); building a
theme is documented in [THEME_GUIDE.md](THEME_GUIDE.md); the frontend
technology strategy (native platform, Web Component islands, no framework) is
[ADR-0010](adr/0010-frontend-technology-strategy.md). The outward roadmap is
[ROADMAP.md](ROADMAP.md). Community sharing — licenses, naming, registry — is
[ECOSYSTEM.md](ECOSYSTEM.md) / [ADR-0011](adr/0011-community-ecosystem-policy.md). The component inventory
(theme chrome, islands, admin candidates) is [COMPONENTS.md](COMPONENTS.md).

## Open decisions

- Admin UI: server-rendered vs. lightweight TypeScript (decide in Milestone 3,
  with an ADR). Leading candidate for the look: hTWOo (n8design/htwoo, MIT) —
  Fluent Design in pure HTML/CSS/JS, pairs naturally with a server-rendered
  FastAPI UI and adds no frontend framework; would be vendored as local assets

## Decided

- License: Apache-2.0 ([ADR-0002](adr/0002-license-apache-2.md))
- Remote repository: `ph7x-Systems/stillsite` on GitHub (public since 2026-07-17)
- Project name: **Stillsite** — coined, screened against PyPI/npm/GitHub and
  trademark databases before adoption; owned by pH7x Systems

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

**Executed 2026-07-17**: the owner opted to flip early (public repos get
unlimited GitHub Actions minutes, and the sweep found nothing to hide) after
a full audit — history squashed to a single clean release commit, all
criteria of SECURITY_STRATEGY.md §4 verified. The repo is public but
low-key; the **announcement/launch** moment stays at the end of Milestone 4
(reference theme + polished example).

## Constraints

- No changes to the current corporate site (`Ph7x.Site.Corporate` / ph7x.com)
- No secrets, personal data or client content in this repository
- Irreversible actions, public publishing, costs or credentials require confirmation
