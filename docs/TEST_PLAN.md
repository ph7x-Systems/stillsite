# Test Plan — Stillsite

What gets tested, at which layer, with which gate. Rule of thumb: **every
guarantee the docs promise has a test that fails when it stops being true.**
Current state: 53 tests, mypy strict, ruff — all required in CI on every
push/PR (branch protection enforces the six checks).

## 1. Layers

### 1.1 Unit — models and rules (`cms-core`) — in force

- Translation states: missing/outdated/complete derived from checksums;
  source edits downgrade translations; source language always complete.
- Publishing gate: all-required-languages logic, configurable subsets.
- Aggregation: page state = worst of own + sections.
- Editorial rules at model level: slug patterns, mandatory EN alt text,
  image dimensions, safe media paths (traversal rejected).
- Checksums: field-order insensitivity, media-list sensitivity.

### 1.2 Storage conformance suite — in force, grows per backend

The suite in `tests/test_storage.py` **is the contract** (ADR-0004): every
backend must pass it unchanged. Covers migrations (idempotent, versioned),
round-trips preserving equality, upserts, cascade deletes, ordering, None on
missing. When PostgreSQL/SQL Server/MySQL land, the same tests run against a
project-prefixed Docker container per engine (created, never destroying
existing containers); the only difference per engine is the connection URL.
Factory tests: scheme registry, aliases, bare paths, loud failure of planned
engines, custom registration.

### 1.3 Validation (`cms-validation`, M2)

- Each rule tested in isolation: language parity, slug uniqueness per
  language, structure, editorial rules, head-contract completeness.
- Configurability: per-project rule sets, severity levels, rule
  enable/disable — tested as configuration matrices.
- Property: a content set that validates must build; one that doesn't must
  block publishing.

### 1.4 Build and export (`cms-build`, M2) — PoC acceptance

- **Determinism**: two builds of the same input are byte-identical (hash the
  whole output tree).
- **Structural parity** with the PoC reference (docs/POC_PLAN.md): expected
  URL-tree shape (localized slugs, pagination, categories, per-language RSS
  and search index, sitemap, legal pages, 404).
- **Head-contract checker**: every generated page has title, description,
  canonical, complete hreflang cluster (+x-default), OG set with image
  dimensions, correct JSON-LD type. Runs over the built example on every CI
  push — this is also the anti-drift guard for SEO.
- Output confinement: no file written outside the export dir; asset URLs
  carry content hashes; search index/RSS regenerated every build.
- Adapter tests (ADR-0005): `swa` emits the exact config policy (headers,
  overrides, redirects from the content model); `nginx` emits the equivalent;
  redirect targets cross-checked against generated URLs.

### 1.5 Theme conformance (M4)

Applies to the reference theme and any third-party theme:
- `[hidden]{display:none!important}` present in the base layer.
- Zero inline styles; images with dimensions; no horizontal scroll at any
  breakpoint (checked at 360/820/1280px in a headless browser).
- Local fonts only — build fails on external font/CDN references.
- `prefers-reduced-motion` honored; WCAG 2.2 AA via automated axe checks in
  CI (manual audit before go-public).
- No duplicated asset content across bundles (kills the copy-paste drift bug
  class).

### 1.6 Admin panel (`apps/admin`, M3)

- AuthN/AuthZ: every endpoint denies anonymous by default; role matrix tested
  endpoint-by-endpoint (editor/reviewer/publisher); privilege escalation
  attempts fail.
- CSRF protection on state-changing routes; session/token expiry.
- Upload validation: type, size, dimensions, SVG scripting rejected.
- Workflow: draft→review→published→archived transitions, invalid transitions
  rejected; publishing blocked while validation fails.
- API contract tests against the storage interface (backend-agnostic).

### 1.7 Docs anti-drift — in force

`tests/test_docs.py`: ADRs referenced + status lines, README structure vs
real directories, languages vs enum, storage engines vs PLAN, CI workflow vs
README promises. Grows one check per new guarded fact.

### 1.8 CLI (`cms`, M2)

- Each subcommand smoke-tested end-to-end on the example project
  (validate/build/preview/export/seed, init via Copier template).
- Exit codes: non-zero on validation failure (CI-friendly); machine-readable
  output where promised.

## 2. CI mapping

| Gate | Where | Status |
| --- | --- | --- |
| ruff lint + format | job `Lint (ruff)` | in force |
| mypy strict | job `Types (mypy)` | in force |
| Unit/storage/docs tests, py3.12+3.13 | jobs `Tests (pytest, …)` | in force |
| Internal docs links | job `Docs internal links` (lychee) | in force |
| Secret scan (full history) | job `Secret scan` (trufflehog) | in force |
| Example build (seed→validate→build→export via the CLI) | job `Example build` | in force |
| Head contract + determinism + URL tree | `tests/test_builder.py`, `tests/test_cli.py` | in force |
| Full PoC structural parity (categories, pagination, JSON-LD) | extend at M2 follow-ups | planned |
| Backend conformance (Docker engines) | new job/matrix at M1-completion | planned |
| Accessibility (axe) + no-scroll checks | new job at M4 | planned |
| Coverage floor (fail under threshold) | add with M2, target ≥90% on packages | planned |

## 3. Policies

- A bug fix lands **with the regression test** that would have caught it.
- Tests are deterministic: no network, no wall-clock dependence (fixed
  timestamps in fixtures), temp dirs per test.
- The storage conformance and theme conformance suites are public contracts:
  third-party backends/themes run them as-is.
- Per-milestone security gates (SECURITY_STRATEGY.md §6) are implemented as
  tests in these layers, not as checklists.
