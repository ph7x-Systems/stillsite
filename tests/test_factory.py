"""Storage factory: scheme registry, aliases and planned backends."""

from pathlib import Path

import pytest
from cms_core import ArticleContent, new_article
from cms_core.storage import SQLiteBackend, available_schemes, create_storage, register_backend
from cms_core.storage.sqlite import sqlite_path_from_location


def test_bare_path_defaults_to_sqlite(tmp_path: Path) -> None:
    backend = create_storage(str(tmp_path / "cms.sqlite3"))
    assert isinstance(backend, SQLiteBackend)


def test_sqlite_url_creates_working_backend(tmp_path: Path) -> None:
    backend = create_storage(f"sqlite:///{tmp_path / 'cms.sqlite3'}")
    backend.save_article(new_article("post", ArticleContent(title="Post")))
    assert backend.list_article_ids() == ["post"]


def test_sqlite_location_parsing() -> None:
    assert sqlite_path_from_location("/relative.db") == "relative.db"
    assert sqlite_path_from_location("//abs/path.db") == "/abs/path.db"
    assert sqlite_path_from_location(":memory:") == ":memory:"
    assert sqlite_path_from_location("/:memory:") == ":memory:"


def test_all_planned_backends_are_registered() -> None:
    assert set(available_schemes()) >= {"sqlite", "postgresql", "mssql", "mysql"}


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://cms:secret@localhost/cms",
        "postgres://cms:secret@localhost/cms",
        "mssql://cms:secret@localhost/cms",
        "sqlserver://cms:secret@localhost/cms",
        "mysql://cms:secret@localhost/cms",
        "mariadb://cms:secret@localhost/cms",
    ],
)
def test_planned_backends_fail_loudly(url: str) -> None:
    with pytest.raises(NotImplementedError, match="planned"):
        create_storage(url)


def test_unknown_scheme_lists_known_ones() -> None:
    with pytest.raises(ValueError, match="sqlite"):
        create_storage("oracle://localhost/cms")


def test_custom_backend_registration(tmp_path: Path) -> None:
    seen: list[str] = []

    def factory(location: str) -> SQLiteBackend:
        seen.append(location)
        return SQLiteBackend(tmp_path / "custom.sqlite3")

    register_backend("custom", factory)
    backend = create_storage("custom://anything")
    assert isinstance(backend, SQLiteBackend)
    assert seen == ["anything"]
