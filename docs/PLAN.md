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

- [ ] `cms-core`: versioned schemas (pages, sections, articles, media, languages)
- [ ] Translation model: EN as source; `missing / outdated / complete` states
- [ ] Persistence: SQLite (dev) / PostgreSQL (prod) + JSON/Markdown export as the portable source
- [ ] Versioned migrations

## Milestone 2 — Validation and build

- [ ] `cms-validation`: language parity, structure, editorial rules, configurable per project
- [ ] `cms-build`: deterministic generator — pages, listings, categories, tags, static search, RSS, sitemap, canonical, hreflang
- [ ] CLI (`cms`): `validate`, `build`, `preview`, `export`, `seed` — Typer-based
- [ ] Static export independent of the admin panel, ready for Azure Static Web Apps

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

## Open decisions

- Admin UI: server-rendered vs. lightweight TypeScript (decide in Milestone 3, with an ADR)
- Static search strategy (pre-generated index vs. lunr-like)

## Decided

- License: Apache-2.0 ([ADR-0002](adr/0002-license-apache-2.md))
- Remote repository: `ph7x-Systems/Ph7x.CMS.Framework` on GitHub (private; public later)

## Constraints

- No changes to the current corporate site (`Ph7x.Site.Corporate` / ph7x.com)
- No secrets, personal data or client content in this repository
- Irreversible actions, public publishing, costs or credentials require confirmation
