# Roadmap

The outward view: where Stillsite is, what ships next, and what "done" means
at each horizon. Execution detail lives in [PLAN.md](PLAN.md) (milestones,
checkboxes) — this page never duplicates it, it points at it. Live demo:
<https://stillsite.ph7x.com>.

## Where the project stands

- **Foundation, content core, build pipeline: shipped.** Milestones 0–2 are
  closed: translation model with checksum-derived states, multi-engine
  storage (SQLite + PostgreSQL behind one factory, conformance-tested),
  validation engine, deterministic builder (head contract, feeds, search
  indexes, categories/tags/pagination, media pipeline), theme system with
  per-project overrides, deployment adapters (SWA/nginx/generic), and the
  `cms` CLI (init/seed/validate/build/export/preview).
- **Public demo live** and auto-deployed from `main` on Azure Static Web
  Apps (Free), custom domain + SSL.
- **Engineering guardrails in force**: 8 required CI checks, docs anti-drift
  suite, output-integrity suite, secret scanning + push protection, PR-only
  workflow, mypy strict.

## Near term — "demo = ready" (PLAN: Demo readiness plan)

1. ✅ Infrastructure · 2. ✅ PostgreSQL · 3. ✅ Demo content
4. **Client-side search** — `<site-search>` Web Component island over the
   per-language `search-index.json` (ADR-0010).
5. **Reference theme** (`cms-theme-ph7x-reference`, Milestone 4) — the PoC
   design system: tokens, Inter/Newsreader local fonts, 820px breakpoint,
   dark editorial look, effects as islands; demo switches to it.
6. **Ready gate** — automated WCAG 2.2 AA checks in CI, five complete
   languages, README quickstart against the live demo, social preview. Then
   the public announcement.

## Mid term

- **Admin panel (Milestone 3)** — FastAPI, explicit auth/roles, translation
  dashboard, side-by-side editor, media library, editorial workflow. UI
  approach decided by ADR at kickoff (server-rendered vs. light TypeScript).
- **First release on PyPI** — distribution naming decided by ADR
  (`stillsite-*` vs `cms-*`), semantic versioning from `0.1.0`, changelog,
  release workflow with trusted publishing.
- **SQL Server and MySQL/MariaDB backends** — same mold as ADR-0009
  (shared migrations, engine-specific version tracking, conformance suite).
- **`iis` deployment adapter** when the first on-prem Windows deployment
  needs it (ADR-0005).

## Long term

- **Extension ecosystem** — the plugin registration ADR (content types,
  validation rules, build steps, CLI subcommands), plus a documented gallery
  of themes/targets/backends passing the public conformance suites.
- **Dogfooding** — the project's documentation site built with Stillsite
  itself, deployed like the demo.
- **1.0** — criteria: admin panel stable, two production deployments beyond
  ph7x.com, PyPI packages with a deprecation policy, all conformance suites
  documented as public contracts.

## Standing invariants (any horizon)

Everything lands through the same gates: English-only repo, PR + green CI,
docs move with the code (anti-drift enforced), ADRs for decisions, no
secrets/personal data, deterministic builds, WCAG 2.2 AA baseline.
