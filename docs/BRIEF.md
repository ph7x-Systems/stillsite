# Brief — pH7x CMS Framework

Create a new product and its GitHub repository (private for now; may become public later):

- Organization: `ph7x-Systems`
- Repository: `Ph7x.CMS.Framework`
- Default branch: `main`
- Description: `Reusable multilingual, static-first CMS framework extracted from the pH7x Systems website architecture.`

Do not change or publish anything in the existing corporate repository or website. The new repository must be born separate and free of secrets, personal data, client content or generated files from the current site.

## Goal

Build a reusable, static-first, multilingual CMS framework based on the contracts already proven on the public site `https://ph7x.com` and the skeleton of the `Ph7x.Site.Corporate` project.

The result is not a visual clone of the site. It is a content and publishing engine that enables building other sites with the same rigor: structured content, five languages, templates, Markdown blog, strong validation, preview and static export ready for Azure Static Web Apps.

## Existing source of truth

The current project uses:

- a static generator in Python;
- `content.json` for all visible text on the homepage and institutional pages;
- HTML templates with content keys;
- Markdown articles organized per article and language;
- five languages: EN as the base, PT-PT, ES, FR and DE;
- separate builds for site, blog and contact;
- validation that fails on language parity loss, hardcoded text, improper fallback, invalid structure or broken editorial rules;
- `pytest` tests before publishing;
- static output for Azure Static Web Apps;
- multilingual SEO: canonical, hreflang, Open Graph, JSON-LD, sitemap and RSS;
- local assets, no third-party visual dependencies;
- stable design tokens and components;
- forms and dynamic features isolated in an API, without turning the whole site into a dynamic application.

## Mandatory principles

1. Static-first: the public frontend must remain static HTML/CSS/JS — fast, accessible and easy to host.
2. Content separated from presentation: no editorial text hardcoded in templates.
3. Multilingual from the ground up: EN, PT-PT, ES, FR and DE, with translation state and parity validation.
4. Portability: content exportable as JSON and Markdown; no lock-in to a proprietary database.
5. Deterministic build: the same input must produce the same output.
6. Validation before publishing: never allow an invalid build to be promoted.
7. Security: no secrets in the repository, explicit authentication and authorization in the admin panel, validated uploads, least privilege.
8. Accessibility: WCAG 2.2 AA as the baseline for the admin panel and the reference theme.
9. Azure compatibility: simple local development and publishing prepared for Azure Static Web Apps.
10. Reuse: clearly separate core, theme, example content and publishing adapters.

## Functional MVP

Create a first usable version with:

- authenticated admin panel;
- dashboard with content status, missing translations, validations and last build;
- management of pages and structured sections;
- management of Markdown articles with title, per-language slug, summary, body, date, time, category, tags, cover image, state and SEO;
- side-by-side editor per language, with EN as the source and an incomplete/outdated translation indicator;
- media library with mandatory alt text, dimensions and type/size validation;
- preview before publishing;
- `draft -> review -> published -> archived` workflow;
- per-project configurable validation;
- generation of pages, listings, categories, tags, static search, RSS, sitemap, canonical and hreflang;
- full export to a static folder;
- reference theme inspired by the ph7x.com visual system, but with fictional content and without copying personal or client data;
- CLI for `validate`, `build`, `preview`, `export` and `seed`;
- unit and integration tests for the critical contracts;
- documentation for installation, architecture, content model, theme extension and deployment.

## Expected architecture

Choose the simplest solution that preserves these contracts. Keep Python in the content/build engine, because it is the proven existing base. You may use FastAPI for the API/admin and a lightweight TypeScript UI if it brings clear value, but avoid a distributed architecture or unnecessary dependencies.

Desired structure, adjustable if you justify a better alternative:

```text
apps/
  admin/
packages/
  cms-core/
  cms-build/
  cms-validation/
  cms-theme-ph7x-reference/
examples/
  multilingual-company-site/
docs/
tests/
```

Support SQLite in development and PostgreSQL in production, without making the database the only portable source. Define versioned schemas and migrations. The exporter must produce static artifacts independent of the admin panel.

## Reference theme visual rules

- tokens, never scattered colors/fonts;
- local fonts;
- inline SVG for icons;
- zero inline styles;
- reusable components;
- main breakpoint at 820 px;
- images always with dimensions;
- no horizontal scroll;
- `[hidden]{display:none!important}`;
- editorial dark theme with Inter, Newsreader and a neutral palette similar to the public site, without copying brand or sensitive content into the example.

## Quality and CI

Configure GitHub Actions for:

- lint and formatting;
- type checking;
- tests;
- content validation;
- static build of the example;
- link checking, accessibility and absence of secrets;
- preview artifact per pull request, when possible;
- documented `main` branch protection.

Include `.env.example`, a to-be-decided license clearly marked in the README, `SECURITY.md`, `CONTRIBUTING.md`, an initial ADR and a short list of still-open decisions. Do not invent credentials or real infrastructure.

## Acceptance criteria for the first delivery

- the private repository exists and is initialized;
- local installation is documented and repeatable;
- a user can create a page and an article in five languages;
- missing translations block publishing according to configuration;
- preview works;
- `validate` and tests pass;
- `build` generates a navigable static site with multilingual SEO, RSS and sitemap;
- the example can be served locally and prepared for Azure Static Web Apps;
- no changes were made to the current corporate site;
- the README includes architecture, commands, roadmap and real limitations.

## Execution approach

Start by creating the private repository and a short plan in `docs/PLAN.md`. Then implement the MVP in small increments with clear commits. Do not stop for cosmetic preferences; make reversible decisions and record them. For any irreversible action, public publishing, cost, credential or change to the current site, ask for confirmation.

At the end, deliver:

1. repository URL;
2. architecture summary;
3. exact commands to run locally;
4. test and validation results;
5. what is done, what is left for the next milestone and known risks.
