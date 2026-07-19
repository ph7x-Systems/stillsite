"""Shared fixtures: the storage conformance suite runs on every engine.

`backend` is parameterized over all implemented engines. SQLite always runs;
PostgreSQL runs when `SARDINE_POSTGRES_URL` is set (CI service container or
a local Docker instance) and is skipped otherwise — never silently faked.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from cms_core.storage import StorageBackend, create_storage


def _wipe_postgres(url: str) -> None:
    import psycopg

    with psycopg.connect(url, autocommit=True) as connection:
        connection.execute("DROP SCHEMA public CASCADE")
        connection.execute("CREATE SCHEMA public")


@pytest.fixture(params=["sqlite", "postgresql"])
def backend(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[StorageBackend]:
    if request.param == "sqlite":
        storage = create_storage(f"sqlite:///{tmp_path / 'cms.sqlite3'}")
    else:
        url = os.environ.get("SARDINE_POSTGRES_URL")
        if not url:
            pytest.skip("SARDINE_POSTGRES_URL not set")
        _wipe_postgres(url)
        storage = create_storage(url)
    yield storage
    storage.close()
