"""Multi-backend persistence behind one interface.

Backends register per URL scheme (``create_storage("sqlite:///content.db")``).
SQLite ships built in; PostgreSQL, SQL Server and MySQL/MariaDB are planned
and third parties can register custom engines via :func:`register_backend`.
"""

from cms_core.storage.base import StorageBackend
from cms_core.storage.factory import (
    available_schemes,
    create_storage,
    register_backend,
)
from cms_core.storage.sqlite import MIGRATIONS, SQLiteBackend

__all__ = [
    "MIGRATIONS",
    "SQLiteBackend",
    "StorageBackend",
    "available_schemes",
    "create_storage",
    "register_backend",
]
