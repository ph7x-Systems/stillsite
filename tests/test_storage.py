"""SQLite round-trip and migration behavior."""

from pathlib import Path

from cms_core import ArticleContent, ContentStatus, Language, new_article
from cms_core.storage import (
    MIGRATIONS,
    connect,
    delete_article,
    list_article_ids,
    load_article,
    migrate,
    save_article,
    schema_version,
)


def test_connect_applies_all_migrations(tmp_path: Path) -> None:
    connection = connect(tmp_path / "cms.sqlite3")
    assert schema_version(connection) == len(MIGRATIONS)
    # A second migrate call is a no-op, not an error.
    assert migrate(connection) == len(MIGRATIONS)


def test_article_round_trip(tmp_path: Path) -> None:
    connection = connect(tmp_path / "cms.sqlite3")
    article = new_article("first-post", ArticleContent(title="First", body_markdown="Hello."))
    article.set_translation(Language.PT_PT, ArticleContent(title="Primeiro", body_markdown="Olá."))
    article.status = ContentStatus.REVIEW

    save_article(connection, article)
    loaded = load_article(connection, "first-post")

    assert loaded == article


def test_save_is_an_upsert(tmp_path: Path) -> None:
    connection = connect(tmp_path / "cms.sqlite3")
    article = new_article("first-post", ArticleContent(title="First"))
    save_article(connection, article)

    article.source = ArticleContent(title="First, revised")
    article.set_translation(Language.ES, ArticleContent(title="Primero"))
    save_article(connection, article)

    loaded = load_article(connection, "first-post")
    assert loaded is not None
    assert loaded.source.title == "First, revised"
    assert set(loaded.translations) == {Language.ES}


def test_delete_cascades_to_translations(tmp_path: Path) -> None:
    connection = connect(tmp_path / "cms.sqlite3")
    article = new_article("first-post", ArticleContent(title="First"))
    article.set_translation(Language.FR, ArticleContent(title="Premier"))
    save_article(connection, article)

    assert delete_article(connection, "first-post")
    assert not delete_article(connection, "first-post")
    assert list_article_ids(connection) == []
    remaining = connection.execute("SELECT COUNT(*) FROM translations").fetchone()[0]
    assert remaining == 0


def test_missing_article_loads_as_none(tmp_path: Path) -> None:
    connection = connect(tmp_path / "cms.sqlite3")
    assert load_article(connection, "nope") is None
