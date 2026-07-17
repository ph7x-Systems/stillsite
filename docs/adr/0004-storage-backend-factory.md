# ADR-0004 — Storage backend factory (SQLite, PostgreSQL, SQL Server, MySQL/MariaDB)

- **Status:** accepted (amends ADR-0003)
- **Date:** 2026-07-17

## Context

ADR-0001 fixed SQLite for development and PostgreSQL for production. The
owner additionally requires the persistence layer to support multiple
engines — SQLite, SQL Server, PostgreSQL and MySQL/MariaDB — behind one
abstraction, decided at configuration time, and open to third-party engines
per the extensibility contracts in the PLAN.

## Decision

- One abstract interface, `cms_core.storage.StorageBackend`, defines the
  entire persistence contract (articles, pages, media, migrations). Nothing
  above the storage layer knows which engine is in use.
- A URL-scheme factory, `create_storage(url)`, resolves the backend:
  `sqlite:///…` (implemented, development default — a bare file path also
  works), `postgresql://…`, `mssql://…` and `mysql://…` (registered, planned;
  they fail loudly with `NotImplementedError` until implemented). Aliases:
  `postgres`, `sqlserver`, `mariadb` (MariaDB is protocol-compatible with
  MySQL, so one backend serves both).
- `register_backend(scheme, factory)` lets projects and plugins add custom
  engines without touching the framework.
- Each backend owns its SQL dialect and migration scripts; there is no shared
  ORM for now (ADR-0003 still applies to the SQLite implementation). Whether
  the server backends share a SQLAlchemy layer is decided when the first one
  is implemented, in its own ADR.

## Consequences

- Callers write `create_storage(settings.database_url)` once; switching
  engines is a configuration change, not a code change.
- Requesting a planned engine gives an explicit error instead of silent
  SQLite fallback.
- The interface is the compatibility contract for the future PostgreSQL,
  SQL Server and MySQL backends — the existing test suite runs against any
  backend by swapping the URL, which becomes the conformance suite.
