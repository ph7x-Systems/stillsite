# Execution Plan — Sardine CMS

Short plan by milestones, per the brief ([BRIEF.md](BRIEF.md)). Small increments, clear commits, reversible decisions recorded as ADRs.

## Milestone 0 — Foundation (current)

- [x] Repository initialized (`main`), folder structure, base docs
- [x] Repository published to GitHub (`ph7x-Systems/sardine-cms`, public)
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

## Milestone 3 — Admin panel (detailed plan)

**This is what makes Sardine CMS a CMS** — not a static site generator with
extras: an editor runs the whole editorial cycle (create → translate →
review → publish → deployed artifact) from the browser, with no JSON files,
no CLI and no code. The admin is an Interface-layer application
([ADR-0006](adr/0006-layered-architecture.md)): it drives `cms-core`,
`cms-validation` and `cms-build` through their public APIs and never
bypasses them. Security gates per [SECURITY_STRATEGY.md](SECURITY_STRATEGY.md)
(admin panel section). Phases in execution order; each lands as its own PR
with tests:

1. [x] **ADR-0013 — admin UI architecture**
       ([ADR-0013](adr/0013-admin-ui-architecture.md)): FastAPI +
       server-rendered Jinja, with Web-Component islands where interactivity
       demands it (ADR-0010 applies to the admin too); TypeScript only if a
       concrete need appears, with its own ADR. The original hTWOo component
       choice was later superseded by
       [ADR-0015](adr/0015-admin-ph7x-design.md).
2. [x] **Application skeleton**: `apps/admin` as an installable package
       (`cms-admin`, src layout like the rest), app factory, settings from
       environment only (no config files with secrets), health endpoint
       reporting the migrated schema version, storage through
       `create_storage(url)` so any supported engine works unchanged;
       test scaffold and CI wiring (admin joins every job's PACKAGES).
3. [x] **Accounts and access control**: users with argon2id password
       hashes; the role ladder `editor / reviewer / publisher / admin`
       enforced server-side (`require_at_least`); server-side sessions
       (only the token digest stored) with expiry, cookies HttpOnly +
       Secure + SameSite=Strict; synchronizer CSRF tokens on authenticated
       state-changing requests plus a double-submit token on the login
       form; failed-login rate limiting; **no default credentials** — the
       first account is created with `cms admin create-user`. Accounts
       live in the storage database via shared migration 6 but are
       **never exported**; the conformance suite covers them on every
       engine.
4. [x] **Admin shell + dashboard**: the chrome (top bar, navigation, tables
       per the COMPONENTS.md mapping — restyled natively with the ph7x
       design system per ADR-0015); dashboard shows content by
       status, the translation coverage matrix (missing/outdated/complete
       per language), current validation results and the last build/export.
5. [x] **Articles**: list/create/edit with the side-by-side editor (EN
       source next to each translation), translation-state indicators from
       the checksum model, safe Markdown preview (same renderer as the
       builder), per-language slugs, SEO fields, category, tags, cover.
6. [x] **Pages and sections**: page metadata plus ordered typed sections
       with kind-aware field forms; same side-by-side translation UX.
7. [x] **Media library**: uploads validated server-side (MIME sniffing,
       size limits, image dimensions), mandatory EN alt text, translatable
       alt, usage references checked before delete.
8. [x] **Workflow and publishing**: `draft → review → published → archived`
       transitions gated by role; the publish gate runs `cms-validation`
       and blocks on errors (configurable); preview builds through
       `cms-build` into a temporary directory; build/export can be
       triggered from the panel with visible results.
9. [x] **Hardening + accessibility gate**: security headers (CSP with no
       inline script, frame denial), the SECURITY_STRATEGY M3 test suites
       (authn/authz, CSRF, upload validation, failed-login rate limiting),
       axe over the admin pages (WCAG 2.2 AA, same gate as the public
       site), admin guide in `docs/` covered by the anti-drift suite.

**Definition of done**: the full editorial cycle works from the browser
against any supported storage engine, with every security and accessibility
gate green in CI.

## Release plan — first PyPI release (after Milestone 3 kickoff)

- [x] **ADR-0014 — distribution naming**: `sardine-cms-*` for all six
      packages, import names unchanged
      ([ADR-0014](adr/0014-distribution-naming.md)). Reserving the names on
      PyPI (pending publishers) is an owner web-UI step before the first
      tag.
- [x] **Trusted publishing**: `release.yml` publishes all six packages on
      `v*` tags via PyPI OIDC (no long-lived tokens), with a tag-vs-version
      consistency check; semantic versioning from `0.1.0` in lockstep;
      hand-written `CHANGELOG.md`; one single-sourced version per package.
- [x] **Remaining backends**: MySQL/MariaDB
      ([ADR-0018](adr/0018-mysql-backend.md), PyMySQL) and SQL Server
      ([ADR-0019](adr/0019-mssql-backend.md), pymssql) — optional extras,
      the shared migrations with mechanical dialect adaptations, one shared
      DB-API implementation, and the conformance suite green in CI against
      real service containers. Every engine promised by ADR-0004 is now
      implemented.

## Milestone 4 — Reference theme and example (detailed plan)

Executed against DESIGN_RULES.md; every mechanical rule lands as a test in
the theme conformance suite.

- [x] **Theme discovery by entry points (ADR-0012)** — `sardine.themes`
      entry-point group; `create_theme` loads lazily on a registry miss, so
      installed theme packages need zero configuration; same policy will
      serve targets/backends/plugins later
- [x] **Package scaffold** `cms-theme-ph7x-reference` (src layout, templates
      and assets as package data, Apache-2.0, entry point registered)
- [x] **Shared Jinja base** in `cms-build` (`JinjaTheme`) so the reference
      theme layers over the default's templates instead of copying them; the
      head contract moves to a shared `_head.html.j2` partial (one source)
- [x] **Design tokens + base layer** — dark editorial look: full token set
      (`--bg --ink --muted --head --accent --navy --green --panel --line
      --line-2 --faint --maxw --sans --serif`), `[hidden]` first rule, 820px
      main breakpoint, zero inline styles
- [x] **Section kinds**: `hero` (aurora/grain backdrop), `story`,
      `features`, generic fallback — same context contract as the default
- [x] **Local fonts**: Inter (sans) + Newsreader (serif/italic), latin
      subsets, woff2, preloaded, OFL license files shipped alongside
- [x] **Effects without JS**: grain/aurora and reveals via modern CSS
      (gradients, scroll-driven animations behind `@supports`), honoring
      `prefers-reduced-motion` — ADR-0010's CSS-over-JS rule; JS budget
      unchanged (search island only)
- [x] **Theme conformance suite** (`tests/test_theme_conformance.py`)
      running the DESIGN_RULES mechanical checks over every shipped theme
- [x] **Demo switch**: example project sets `theme = "ph7x-reference"`;
      CI/deploy install the theme package; COMPONENTS.md updated
- [ ] Documentation pass: installation, architecture, content model, theme
      extension, deployment (pre-announcement)

## Milestone 5 — Editorial completeness (CLOSED)

Everything an editor expects from a mature CMS, inside the panel. The
outward framing lives in [ROADMAP.md](ROADMAP.md); each item ships with
tests, docs and wiki updates, per the standing gates.

- [x] **Direct unpublish**: `published → draft` transition (publisher
      role), one click
- [x] **Scheduled publishing** (ADR-0024): `publish_at` on articles and
      pages; the build excludes future content, the next build after the
      moment publishes it; CI-cron recipe in ADMIN_GUIDE
- [x] **Revisions** (ADR-0025): snapshot on every save (migration 9,
      bounded at 20), diff view, undoable restore
- [x] **Trash** (ADR-0026): reversible deletion with exact restore and
      admin-only purge (migration 10)
- [x] **Duplicate as draft** from the editor (collision-safe ids)
- [x] **Per-entry preview**: the editor links straight to the entry's URL
      inside `/preview/`
- [x] **Quick list actions**: per-row dropdown with the workflow
      transitions and trash (slug stays in the editor — it is a
      deliberate, careful change)
- [x] **Featured flag** on articles (migration 11): leads the home
      highlight, listings stay recency
- [x] **Authorship**: editorial byline on articles, rendered by themes
- [x] **Media library filters**: server-side search over id/path/type/alt
      plus quick views (images only, missing translated alt)
- [x] **Users screen** in the admin (list, create, role change, delete
      with self/last-admin safeguards) — CLI stays for bootstrap
- [x] **Editorial notes**: comment trail per entry (migration 12),
      author-or-admin removal, never published

## Milestone 6 — Extensibility and adoption

- [x] Extension contract (ADR-0028): `sardine.extensions` entry-point
      group + dotted paths, explicit activation, validation rules, build
      steps, targets/backends/themes, `cms x` CLI, section-kind hints;
      free-form custom fields on articles (migration 13)
- [x] **Design-aware editing** (ADR-0027, accepted): themed side-preview
      in the editors via the real preview pipeline; live refresh arrives
      with the autosave layer
- [x] Explicit menu manager (migration 14): per-language labels,
      ordering, external links; defined items replace the derived menu,
      empty list falls back to it
- [ ] Build-time image derivatives (responsive sizes; crop/focal point)
- [ ] Redirect map emitted per target (SWA rules, nginx rewrites)
- [ ] Comments-integration contract for static sites (embed islands,
      privacy-respecting)
- [ ] JSON content export target (headless consumption)
- [ ] Importers for common blog-export formats (`cms import`)
- [x] **Admin panel localization** — shipped early (ADR-0022): gettext
      catalogs (EN msgids; PT-PT/ES/FR/DE), per-user preference +
      `Accept-Language` fallback, anti-drift completeness test

## Milestone 7 — Operations

- [ ] Email/notification subsystem ADR (password reset, review-requested
      notifications)
- [ ] TOTP two-factor authentication
- [ ] On-publish webhook (trigger the host's build)
- [ ] `cms doctor`: storage, media, config, environment diagnostics
- [ ] Documented backup/restore and scheduled-build recipes

## Next steps (priority order)

1. ~~Close Milestone 2 — PoC parity~~ **done** (categories/tags/pagination,
   404, JSON-LD, media pipeline, theme overrides ADR-0007, `cms init`
   ADR-0008).
2. ~~Close Milestone 1 — PostgreSQL~~ **done** (ADR-0009; SQL Server and
   MySQL/MariaDB remain, same mold).
3. ~~Reference theme~~ **done** (production stylesheets vendored; demo on
   sardine.ph7x.com).
4. ~~Demo ready gate~~ **done** (axe/WCAG + W3C Nu job required in CI, README
   links the live demo; owner still owes the social preview upload and the
   announcement moment).
5. ~~Milestone 3 — admin panel~~ **done** (accounts/roles, editors, media
   library, workflow, publishing, hardening; AdminLTE with its behaviors,
   ADR-0017/0020).
6. ~~First PyPI release~~ **done** (v0.1.x, `sardine-cms-*`, trusted
   publishing, per-package environments; all four storage backends
   shipped, ADR-0018/0019).
7. **Milestone 5 — editorial completeness (next)**: the checklist above,
   starting with direct unpublish, scheduling and revisions.
8. **Milestones 6–7**: extensibility/adoption, then operations — see the
   checklists above and [ROADMAP.md](ROADMAP.md).

Small pending items: GitHub social preview upload (owner, web UI only);
reserve the PyPI names (`sardine-cms`; decide `sardine-cms-*` vs `cms-*`
distribution naming at first release, with an ADR); rename the local working
folder to match the project name.

## Demo readiness plan (sardine.ph7x.com)

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
5. **Reference theme (Milestone 4)** — ✅ done: the reference theme ships the
   production ph7x stylesheets and fonts verbatim with templates on the
   exact site classes; anchor menu, cover thumbnails, localized dates and
   editorial blog labels close the visual drifts; conformance suite green.
6. **Ready gate** — ✅ axe gate in force (zero serious/critical across 7
   pages; contrast fixes applied), five languages complete, README links
   the live demo and the documentation set. Remaining (owner): social
   preview upload, then the announcement.

## Design overhaul plan (component system, not a monolith)

**Historical.** This plan predates the verbatim-CSS decision (the demo now
ships the real ph7x stylesheets) and the admin's hTWOo experiment, which
ended with hTWOo removed everywhere
([ADR-0015](adr/0015-admin-ph7x-design.md)). Kept for the record:

1. **Vendor hTWOo Core** as local assets (npm tarball → dist CSS, no Node in
   the build, no CDN): new base layer available to official themes.
2. **Componentized theme assets**: `assets/components/*.css` per component
   (tokens, header, hero, entries, search, footer); the theme concatenates
   them deterministically into the single hash-versioned stylesheet —
   authoring is componentized, delivery stays one request.
3. **Map chrome onto hTWOo components**: navigation/command-bar, buttons,
   cards for entry lists, search box; editorial voice (Newsreader display,
   aurora) stays ours via tokens on top.
4. **Visual QA gate**: every design PR ships with before/after screenshots
   generated from the built example (headless browser job — planned CI
   addition with the axe job), so "looks wrong" is caught before deploy.
5. **Demo switch + conformance**: the suite runs over the new composition
   unchanged (local assets only, hidden-first, budgets).

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

**Positioning (definitive).** Sardine CMS is a framework, not a site: the
design belongs to whoever uses it. Themes are installable
packages (ADR-0012) or per-project overrides (ADR-0007); anyone can take an
existing site's stylesheets and wrap them as a theme. The **ph7x design
system is only the reference theme** (`cms-theme-ph7x-reference`, vendoring
the production stylesheets), and **Sardine Aerospace is only dummy example
content** for demos — neither constrains what users build.

Normative design rules live in [DESIGN_RULES.md](DESIGN_RULES.md); building a
theme is documented in [THEME_GUIDE.md](THEME_GUIDE.md); the frontend
technology strategy (native platform, Web Component islands, no framework) is
[ADR-0010](adr/0010-frontend-technology-strategy.md). The outward roadmap is
[ROADMAP.md](ROADMAP.md). Community sharing — licenses, naming, registry — is
[ECOSYSTEM.md](ECOSYSTEM.md) / [ADR-0011](adr/0011-community-ecosystem-policy.md). The component inventory
(theme chrome, islands, admin candidates) is [COMPONENTS.md](COMPONENTS.md).

## Open decisions

- PyPI distribution naming, `sardine-cms-*` vs `cms-*` (ADR-0014 at first
  release — see the release plan above)

## Decided

- Admin UI: server-rendered FastAPI + Jinja, islands per ADR-0010,
  session-cookie auth ([ADR-0013](adr/0013-admin-ui-architecture.md));
  styled natively with the ph7x design system — no component library
  ([ADR-0015](adr/0015-admin-ph7x-design.md))
- License: Apache-2.0 ([ADR-0002](adr/0002-license-apache-2.md))
- Remote repository: `ph7x-Systems/sardine-cms` on GitHub (public since 2026-07-17)
- Project name: **Sardine CMS** — coined, screened against PyPI/npm/GitHub and
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
