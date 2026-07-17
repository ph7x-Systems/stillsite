"""Storage factory: URL scheme -> backend.

``create_storage("sqlite:///content.sqlite3")`` returns a ready (migrated)
backend. Third parties can plug their own engines with
:func:`register_backend`, per the extensibility contracts in docs/PLAN.md.

Built-in schemes:

- ``sqlite`` — implemented (development default; a bare file path also works)
- ``postgresql`` (alias ``postgres``) — planned
- ``mssql`` (alias ``sqlserver``) — planned
- ``mysql`` (alias ``mariadb``; MariaDB is protocol-compatible) — planned
"""

from collections.abc import Callable

from cms_core.storage.base import StorageBackend
from cms_core.storage.sqlite import SQLiteBackend, sqlite_path_from_location

BackendFactory = Callable[[str], StorageBackend]

_REGISTRY: dict[str, BackendFactory] = {}
_ALIASES: dict[str, str] = {
    "postgres": "postgresql",
    "sqlserver": "mssql",
    "mariadb": "mysql",
}


def register_backend(scheme: str, factory: BackendFactory) -> None:
    _REGISTRY[scheme] = factory


def available_schemes() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


def create_storage(url: str) -> StorageBackend:
    scheme, separator, location = url.partition("://")
    if not separator:
        # Bare path: normalize to the URL location form ("/relative" or "//abs").
        scheme, location = "sqlite", f"/{url}"
    scheme = _ALIASES.get(scheme, scheme)
    factory = _REGISTRY.get(scheme)
    if factory is None:
        known = ", ".join(available_schemes())
        raise ValueError(f"unknown storage scheme {scheme!r} (known schemes: {known})")
    return factory(location)


def _planned(engine: str) -> BackendFactory:
    def factory(location: str) -> StorageBackend:
        raise NotImplementedError(
            f"the {engine} backend is planned but not implemented yet (see docs/PLAN.md);"
            " use sqlite for now or register a custom backend"
        )

    return factory


def _sqlite_factory(location: str) -> StorageBackend:
    return SQLiteBackend(sqlite_path_from_location(location))


register_backend("sqlite", _sqlite_factory)
register_backend("postgresql", _planned("PostgreSQL"))
register_backend("mssql", _planned("SQL Server"))
register_backend("mysql", _planned("MySQL/MariaDB"))
