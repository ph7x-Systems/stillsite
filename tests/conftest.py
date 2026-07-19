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


def _wipe_mysql(url: str) -> None:
    import pymysql
    from cms_core.storage.mysql import _connect_kwargs

    connection = pymysql.connect(**{**_connect_kwargs(url.partition("://")[2]), "autocommit": True})
    with connection.cursor() as cursor:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        cursor.execute("SHOW TABLES")
        for (table,) in cursor.fetchall():
            cursor.execute(f"DROP TABLE IF EXISTS `{table}`")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    connection.close()


MSSQL_DROP_ORDER = (
    "menu_items",
    "notes",
    "revisions",
    "section_translations",
    "sections",
    "page_translations",
    "translations",
    "articles",
    "pages",
    "media_alt_texts",
    "media_assets",
    "admin_sessions",
    "users",
    "schema_migrations",
)


def _wipe_mssql(url: str) -> None:
    import pymssql
    from cms_core.storage.mssql import _connect_kwargs

    kwargs = _connect_kwargs(url.partition("://")[2])
    database = kwargs.pop("database")
    with (
        pymssql.connect(**kwargs, database="master", autocommit=True) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(f"IF DB_ID('{database}') IS NULL CREATE DATABASE [{database}]")
    connection = pymssql.connect(**kwargs, database=database, autocommit=True)
    with connection.cursor() as cursor:
        for table in MSSQL_DROP_ORDER:
            cursor.execute(f"DROP TABLE IF EXISTS [{table}]")
    connection.close()


ENGINE_ENV = {
    "postgresql": ("SARDINE_POSTGRES_URL", _wipe_postgres),
    "mysql": ("SARDINE_MYSQL_URL", _wipe_mysql),
    "mssql": ("SARDINE_MSSQL_URL", _wipe_mssql),
}


@pytest.fixture(params=["sqlite", "postgresql", "mysql", "mssql"])
def backend(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[StorageBackend]:
    if request.param == "sqlite":
        storage = create_storage(f"sqlite:///{tmp_path / 'cms.sqlite3'}")
    else:
        variable, wipe = ENGINE_ENV[request.param]
        url = os.environ.get(variable)
        if not url:
            pytest.skip(f"{variable} not set")
        wipe(url)
        storage = create_storage(url)
    yield storage
    storage.close()
