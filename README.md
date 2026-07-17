# Ph7x.CMS.Framework

Reusable multilingual, static-first CMS framework extracted from the pH7x Systems website architecture.

> **License:** to be decided (marked as pending — see [open decisions](docs/PLAN.md#open-decisions)).

## What it is

A static-first, multilingual content and publishing engine (EN as source + PT-PT, ES, FR, DE), built on the contracts proven on the public ph7x.com site:

- structured content in JSON and Markdown articles, separated from presentation;
- strong validation before publishing (language parity, structure, editorial rules);
- deterministic build with static export ready for Azure Static Web Apps;
- multilingual SEO: canonical, hreflang, Open Graph, JSON-LD, sitemap and RSS;
- authenticated admin panel with a `draft → review → published → archived` workflow.

## Structure

```text
apps/
  admin/                        # admin panel (API + UI)
packages/
  cms-core/                     # content model, schemas, translation states
  cms-build/                    # deterministic static generator
  cms-validation/               # configurable validation rules
  cms-theme-ph7x-reference/     # reference theme (tokens, components, local fonts)
examples/
  multilingual-company-site/    # example site with fictional content in 5 languages
docs/                           # architecture, plan, ADRs
tests/                          # unit and integration tests
```

## Status

Freshly initialized repository. Private during initial development; planned to become public later — all content must be written as if public (no secrets, personal data or client content). See [docs/PLAN.md](docs/PLAN.md) for the execution plan and [docs/BRIEF.md](docs/BRIEF.md) for the full brief.

## Local development

Requirements and commands will be documented as the MVP is implemented. Target CLI:

```bash
cms validate   # validate content and language parity
cms build      # deterministic static build
cms preview    # local preview
cms export     # export static artifacts
cms seed       # seed example content
```

## Principles

1. Static-first — the public frontend is static HTML/CSS/JS.
2. Content separated from presentation — zero editorial text in templates.
3. Multilingual from the ground up, with translation states and parity validation.
4. Portability — JSON and Markdown, no database lock-in.
5. Deterministic build and mandatory validation before publishing.
6. Security, accessibility (WCAG 2.2 AA) and Azure compatibility.
