# Sardine CMS

[![CI](https://github.com/ph7x-Systems/sardine-cms/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ph7x-Systems/sardine-cms/actions/workflows/ci.yml)
[![CodeQL](https://github.com/ph7x-Systems/sardine-cms/actions/workflows/github-code-scanning/codeql/badge.svg?branch=main)](https://github.com/ph7x-Systems/sardine-cms/actions/workflows/github-code-scanning/codeql)
[![PyPI](https://img.shields.io/pypi/v/sardine-cms-cli?label=pypi&cacheSeconds=600)](https://pypi.org/project/sardine-cms-cli/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](pyproject.toml)
[![Checked with mypy (strict)](https://img.shields.io/badge/mypy-strict-blue.svg)](pyproject.toml)
[![Code style: ruff](https://img.shields.io/badge/style-ruff-261230.svg)](pyproject.toml)

**Build multilingual, SEO-ready static websites with a browser-based CMS — and no proprietary platform lock-in.**

```bash
pip install sardine-cms-cli sardine-cms-theme-ph7x-reference
cms init my-site --theme ph7x-reference
cd my-site
cms seed
cms build
cms preview
```

Six lines, in order, nothing to edit in between. The site is at
<http://127.0.0.1:8000/>, and `cms preview` keeps running until you stop
it with Ctrl+C.

Editors work in a real browser admin; the public site ships as plain
static files to any host. Content lives in portable JSON and Markdown —
never locked in a database.

**▶ [Try the live demo](https://sardine.ph7x.com)** — a fictional
five-language site, rebuilt and deployed by Sardine on every merge —
and **[walk through its read-only admin](https://sardine.ph7x.com/admin/)**.

| The generated site | The admin |
| --- | --- |
| ![The generated site: a five-language static site with its own theme](docs/images/site-home.png) | ![The admin dashboard: workflow tiles, translation coverage, the publish gate](docs/images/admin-dashboard.png) |

## Why Sardine?

- **Translations that cannot silently rot.** Seven languages ship
  bundled; editing a source marks its translations outdated, and the
  publish gate reports every parity gap before anything goes live.
  Assisted translation plugs in as a certified provider — suggestions
  always land as drafts an editor approves, with your glossary terms
  enforced.
- **SEO generated, not hand-maintained.** Canonical, hreflang, Open
  Graph, JSON-LD, sitemap and RSS derive from the content — plus
  per-entry overrides when an editor wants control.
- **A real editorial workflow.** Draft → review → published, scheduled
  publication windows, revisions, previews through the real theme,
  signed external preview links for approval without an account.
- **Static and yours.** The public site is plain files on any host;
  the panel can live on a laptop. Same input, same bytes — builds are
  deterministic and tested to be.
- **Bring your blog with you.** WXR imports inspect before they write —
  a dry-run report with an explicit fidelity percentage and one line
  per item left behind — then migrate idempotently with media download
  and automatic redirects, from the CLI or the browser.
- **Themes and extensions are declarative artifacts.** The panel
  discovers them from packaging metadata without executing code,
  activates them try-first, and contains failures; being a theme — or a
  translation provider — is an executable specification any package can
  certify against.

| Sardine CMS | Traditional CMS |
| --- | --- |
| Static public website | Dynamic public runtime |
| Portable Markdown/JSON | Content locked in a database |
| Multilingual validation before publish | Manual language consistency |
| Deterministic builds | Runtime-dependent rendering |
| Self-hosted, Apache-2.0 | Platform dependency |

> **License:** [Apache-2.0](LICENSE).

## What it is

A static-first, multilingual content and publishing engine (configurable source language; EN, PT-PT, ES, FR, DE, IT and ID bundled as language packs — any pack can join), built on the contracts proven on the public ph7x.com site:

- structured content in JSON and Markdown articles, separated from presentation;
- strong validation before publishing (language parity, structure, editorial rules);
- deterministic build with static export ready for Azure Static Web Apps;
- multilingual SEO: canonical, hreflang, Open Graph, JSON-LD, sitemap and RSS;
- authenticated admin panel with workflow, autosave, themed preview, revisions,
  scheduling, trash, media, menus and user management;
- portable content, controlled external imports and an explicit extension
  contract for themes, storage, build steps, rules, editorial components
  and providers (deployment, forms, comments, assisted translation).

**Where things run:** Sardine is where the site is *managed* — the
panel, storage and build can live on a laptop or a private server and
never need to serve the public site. Publication ships the static
build to external hosting (Azure Static Web Apps, your own Nginx,
S3/CloudFront, GitHub Pages, Netlify, …) and is a repeatable cycle,
not a one-off export: edit in Sardine, republish to the same
destination. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Structure

```text
apps/
  admin/                        # admin panel (API + UI)
packages/
  cms-core/                     # content model, schemas, translation states
  cms-build/                    # deterministic static generator, themes, targets
  cms-validation/               # configurable validation rules
  cms-cli/                      # the cms command line
  cms-theme-ph7x-reference/     # reference theme (tokens, components, local fonts)
examples/
  multilingual-company-site/    # example site with fictional content in 5 languages
docs/                           # architecture, plan, ADRs
tests/                          # unit and integration tests
```

## Status

Developed in the open and released on PyPI (see the version badge above for
the current release). Milestones 5, 6 and 7 (editorial completeness,
extensibility, operations — email, two-factor authentication, webhooks,
diagnostics) are closed; current work makes the ecosystem certifiable:
themes, extensions and providers as versioned contracts with executable
conformance suites. The content core, validator, deterministic builder,
theme system, `cms` CLI and full browser editorial cycle are implemented
and tested — the live demo is built with them on every merge. No secrets,
personal data or client content live in this repository.

## Install

Requires Python 3.12+. The packages are on PyPI (`sardine-cms-*`,
[ADR-0014](docs/adr/0014-distribution-naming.md)):

```bash
pip install sardine-cms-cli                  # the cms command (pulls core, validation, build)
pip install sardine-cms-theme-ph7x-reference # the reference theme used by the demo
pip install sardine-cms-admin                # the browser admin (optional)
```

Database engines beyond SQLite are extras of the core package:
`pip install "sardine-cms-core[postgres]"` (psycopg 3), `[mysql]` (PyMySQL)
or `[mssql]` (pymssql).

Then start a site:

```bash
cms init my-site --name "My Site" --base-url "https://my-site.example"
cd my-site && cms seed && cms build && cms preview
```

## Local development

Requires Python 3.12+.

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --group dev            # ruff, mypy, pytest
python -m pip install -e packages/cms-core -e packages/cms-validation \
                      -e packages/cms-build -e packages/cms-cli -e apps/admin

ruff check . && ruff format --check .        # lint
mypy                                         # type checking (strict)
pytest                                       # tests
```

CI (GitHub Actions) runs the same checks plus dependency/static security
analysis, a docs link check, a full-history secret scan, accessibility and
markup checks, backend conformance and an end-to-end example build on every
push and pull request.

## Quickstart

```bash
cms seed     -p examples/multilingual-company-site   # fictional content, 5 languages
cms validate -p examples/multilingual-company-site   # rules; non-zero exit on errors
cms build    -p examples/multilingual-company-site   # deterministic _site/
cms export   -p examples/multilingual-company-site --target swa   # or nginx | generic
cms preview  -p examples/multilingual-company-site   # serve locally
```

## Docker quickstart

A `docker compose up` brings up the admin panel with a seeded example site and
an admin account — no Python environment needed:

```bash
docker compose up
```

The panel is at `http://localhost:8000`. On first run a random admin password
is generated and printed once in the container log (save it — it won't be
shown again). To set a fixed password instead, uncomment
`SARDINE_ADMIN_PASSWORD` in `docker-compose.yml`. Site content and the SQLite
database persist in named volumes (`sardine-site`, `sardine-data`).

> **Local evaluation only:** this setup runs over plain HTTP with
> `SARDINE_ADMIN_COOKIE_SECURE=0`. Do not expose it to a network without
> TLS and a secure cookie setting.

## Documentation

- [Roadmap](docs/ROADMAP.md) — capability inventory, product direction and
  acceptance criteria for what comes next.
- [Execution plan](docs/PLAN.md) — delivered milestones and current queue.
- [Architecture](docs/ARCHITECTURE.md), [design rules](docs/DESIGN_RULES.md),
  [theme guide](docs/THEME_GUIDE.md), [components](docs/COMPONENTS.md) and
  [ecosystem](docs/ECOSYSTEM.md) — contracts for contributors and extensions.
- [Contributing](CONTRIBUTING.md) — workflow, rules and how to send your
  first pull request; [language pack guide](docs/LANGUAGE_PACK_GUIDE.md)
  for adding a language.
- [Admin guide](docs/ADMIN_GUIDE.md), [testing](docs/TEST_PLAN.md),
  [security](docs/SECURITY_STRATEGY.md), [proof-of-concept](docs/POC_PLAN.md),
  [ADRs](docs/adr/) — operation, verification and
  decision history.

## Principles

1. Static-first — the public frontend is static HTML/CSS/JS.
2. Content separated from presentation — zero editorial text in templates.
3. Multilingual from the ground up, with translation states and parity validation.
4. Portability — JSON and Markdown, no database lock-in.
5. Deterministic build and mandatory validation before publishing.
6. Security, accessibility (WCAG 2.2 AA) and Azure compatibility.
