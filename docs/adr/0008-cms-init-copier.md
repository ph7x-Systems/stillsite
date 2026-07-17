# ADR-0008 — `cms init` scaffolds projects with Copier

- **Status:** accepted
- **Date:** 2026-07-17

## Context

New projects need a scaffold (`stillsite.toml`, media/theme directories,
gitignore). A Node-based generator (Yeoman) was considered and rejected: it
would add a second toolchain to a Python framework. The candidates in-stack
were Cookiecutter and Copier.

## Decision

`cms init <dir>` runs **Copier** (as a library) over a template shipped
inside `cms-cli` (`templates/init`). Copier over Cookiecutter for one
decisive capability: **`copier update`** re-applies template evolutions to
already-generated projects, and the generated `.copier-answers.yml` records
the answers that make that possible. Generation is non-interactive by
default (`--name`, `--base-url`, `--languages` flags with sensible
defaults), which keeps it scriptable and CI-testable.

## Consequences

- One command from nothing to a building project: `cms init x && cms seed
  -p x && cms build -p x`.
- Projects can pick up future template improvements without regenerating.
- `copier` becomes a `cms-cli` dependency only — the core packages stay
  dependency-minimal.
