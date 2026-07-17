# ADR-0003 — Milestone 1 persistence PoC: stdlib SQLite, no ORM yet

- **Status:** accepted
- **Date:** 2026-07-17

## Context

ADR-0001 fixes SQLite for development and PostgreSQL for production, with the
JSON/Markdown export as the portable source of truth. Milestone 1 starts with
a proof of concept of the content core, which needs persistence now but must
not lock in an ORM before the model has settled.

## Decision

For the PoC, `cms-core` persists through the standard library `sqlite3`
module directly:

- migrations are ordered SQL scripts applied once each, tracked with SQLite's
  `user_version` pragma;
- the storage layer is a small set of functions (`connect`, `migrate`,
  `save_article`, `load_article`, …) over parameterized SQL;
- the database remains a working store — export (`cms_core.export`) stays the
  portable source of truth and never depends on the database schema.

Adopting an ORM/query layer (SQLAlchemy being the natural candidate, to back
PostgreSQL in production) is deferred to the moment PostgreSQL support is
implemented, and will be recorded in its own ADR.

## Consequences

- Zero extra dependencies for persistence in the PoC; the model layer
  (pydantic) stays independent of storage.
- The SQL schema is explicit and reviewable; migration history starts at
  version 1 from the first commit.
- When PostgreSQL lands, the storage functions are the single seam to
  reimplement or replace — callers depend on the function signatures, not on
  SQLite specifics.
