# Product History

How the product's direction evolved and why. Feature-level detail
lives in [RELEASE_NOTES.md](../RELEASE_NOTES.md); per-version changes
in [CHANGELOG.md](../CHANGELOG.md); the map as it stands in
[ROADMAP.md](ROADMAP.md).

## Origin — a framework extracted from a proven site (2026-07)

Sardine CMS began as the extraction of the architecture behind the
public ph7x.com site: structured multilingual content, strong
validation before publishing, deterministic static builds. The brief
(BRIEF.md) fixed the contracts; ADR-0001 fixed the architecture
(Python engine, FastAPI admin, monorepo, SQLite→PostgreSQL, exporter
independent of the admin).

## Scope reset — full CMS parity, static-first (M5 era)

The owner reset the ambition: not a niche generator but the capability
set editors expect from a mature publishing system — benchmarked
silently, never cloned, delivered static-first. The roadmap became a
capability inventory with explicit gaps; trunk-based development
(ADR-0033) replaced ceremony; milestones M5–M7 (editorial
completeness, extensibility, operations) closed against that bar.

## Languages become data (ADR-0034)

A standing correction with product consequences: the bundled five
languages lost every privilege. Locale sets opened to packs
(contributable, RTL/LTR, admin catalogs included), the source language
became configuration, and a spatial invariant was fixed — no admin
surface may grow horizontally with the language count. Rationale:
multilingual is the product's spine; hardcoded language assumptions
were compounding debt.

## The product review — implementation by validation (2026-07-21)

An external product assessment found the engineering base far ahead of
the product experience: planning documents trailing the code, no
operational backlog, contract-complete features presented as done, and
architecture prioritized over the editor. The correction, adopted in
full:

- **Issues before code** — nothing starts without a tracked issue
  carrying the user problem and acceptance criteria (#126–#141 created
  as the backlog).
- **Vertical slices** — model → render → admin → docs → public demo
  close together; backend never accumulates without visible UI.
- **Honest done** — usable in the admin, E2E, both themes, two
  languages, empty/error states, docs, demo; contracts alone are 🟡.
- **P0–P3 by editor pain** — usability first; custom taxonomies and
  relations demoted to P3 as platform depth, not editor pain.
- **Metrics with method** — every number declares environment,
  dataset, runs, percentile and tester; editor metrics require a real
  non-technical tester.
- **Observation-driven order** — usability sessions produce a standard
  record whose findings pick the next front, not a fixed sequence.

ADR-0037 ("sections grow up") was the review's first test: repeating
groups, Markdown fields and long-form pages closed vertically, with
the roadmap flipped only after seed, docs, demo and a behavioral
end-to-end proof.

## Human validation becomes confirmation (2026-07-21, later)

The founder revoked human validation as a development gate: the
instrumented evidence recorded on #127 sufficed to continue, sessions
remain wanted as confirmation attached to their issues, and priorities
stay revisable by real observation. The dominant recorded friction
(start / understand / complete the first site) sent onboarding (#128)
ahead of search and bulk actions.

## The operational model is explicit (2026-07-21)

Documented as product truth (#152, DEPLOYMENT.md): Sardine is where
the site is managed; external infrastructure serves it; publication is
a repeatable cycle, never an export. The provider contract was split
into five phases (generation → transport → activation → health →
rollback) with generation shipped and the rest planned as vertical
slices. Later the same day the capability was reclassified **P0**
(#156, superseding #152): one-click publication — publish, unpublish,
scheduled changes and rollback all ending on the public site — is
essential to a CMS's proposition, with the Filesystem/Nginx provider
as the reference implementation before any secondary provider.

## Documentation separated by concern (2026-07-21)

The roadmap had accumulated execution history and stopped being a map
(#155). The split: ROADMAP (product map), RELEASE_NOTES (features,
PRs, migrations), CHANGELOG (per-version changes), PRODUCT_HISTORY
(this file), DEPLOYMENT (operations), wiki by domain.
