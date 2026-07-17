# ADR-0006 — Layered architecture (ports & adapters) for the MVP

- **Status:** accepted
- **Date:** 2026-07-17

## Context

Milestone 2 turns the content core into a working product (validate → build →
export → CLI). Without an explicit structure, the natural failure mode is a
builder that hardcodes URLs and HTML, imports storage directly and can only
ever ship its built-in behavior — the opposite of the extensibility contracts
in the PLAN.

## Decision

Adopt a strict ports & adapters layering, documented in
[ARCHITECTURE.md](../ARCHITECTURE.md):

- **Domain** (`cms-core`): pure models and translation-state logic. No I/O,
  no clock, no configuration reads.
- **Application** (`cms-validation`, `cms-build`): the rule engine and the
  deterministic builder/exporter. Depend on domain types and on contracts —
  `Theme`, `Target`, `StorageBackend` — never on concrete adapters.
- **Adapters**: storage engines, deployment targets and themes, each behind a
  registry (`register_backend` / `register_target` / `register_theme`) so
  third parties plug in without touching the framework.
- **Interface** (`cms-cli`): thin Typer CLI that loads `stillsite.toml`,
  wires adapters by name and calls application services.

Supporting choices: Jinja2 with autoescape for all HTML (templates are theme
assets); markdown-it-py in CommonMark mode with raw HTML disabled;
`stillsite.toml` (stdlib `tomllib`) as project configuration; a minimal
built-in `default` theme inside `cms-build` (the polished reference theme
remains Milestone 4).

## Consequences

- Swapping database, deployment target or theme is configuration, not code.
- The build pipeline is testable at every seam (rules, URL strategy, head
  contract, artifacts) with plain data — no mocks of concrete engines.
- The nine development rules in ARCHITECTURE.md become review criteria; mypy
  strict and the conformance/determinism test suites enforce the mechanical
  ones in CI.
