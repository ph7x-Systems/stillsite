# ADR-0001: Base architecture

- **Status:** accepted
- **Date:** 2026-07-17

## Context

The brief requires a static-first, multilingual CMS framework (EN + PT-PT, ES, FR, DE) with deterministic builds, strong validation and export to Azure Static Web Apps. The proven existing base (the ph7x.com site) uses a Python static generator with `content.json`, per-language Markdown articles and pytest-based validation.

## Decision

1. **Python for the content engine, validation and build** (`cms-core`, `cms-validation`, `cms-build`) — continuity with the contracts proven on the current site.
2. **FastAPI for the admin panel API** (`apps/admin`) — lightweight, typed, testable; the UI starts server-rendered and only evolves to TypeScript if it brings clear value (with its own ADR at that point).
3. **Monorepo with separate packages** following the brief's structure — separates core, theme, example and publishing adapters.
4. **SQLite in dev, PostgreSQL in production**, with versioned schemas and migrations; the portable source of truth is always the JSON/Markdown export, never the database.
5. **Exporter independent of the admin panel** — static artifacts do not depend on the admin running.

## Consequences

- Direct reuse of the validation/parity patterns already proven.
- Avoids distributed architecture and unnecessary dependencies at the start.
- The admin UI choice is explicitly deferred (reversible decision, tracked in PLAN.md).
