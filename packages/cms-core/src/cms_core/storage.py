"""SQLite persistence (development backend).

The database is a working store only — the portable source of truth is always
the JSON/Markdown export (see :mod:`cms_core.export`). Schema migrations are
ordered scripts applied once each, tracked via SQLite's ``user_version``.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

from cms_core.languages import Language
from cms_core.models import Article, ArticleContent, Translation
from cms_core.states import ContentStatus

MIGRATIONS: tuple[str, ...] = (
    """
    CREATE TABLE articles (
        id TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        title TEXT NOT NULL,
        summary TEXT NOT NULL,
        body_markdown TEXT NOT NULL
    );
    CREATE TABLE translations (
        article_id TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
        language TEXT NOT NULL,
        title TEXT NOT NULL,
        summary TEXT NOT NULL,
        body_markdown TEXT NOT NULL,
        source_checksum TEXT NOT NULL,
        PRIMARY KEY (article_id, language)
    );
    """,
)


def connect(path: Path | str) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    migrate(connection)
    return connection


def schema_version(connection: sqlite3.Connection) -> int:
    row = connection.execute("PRAGMA user_version").fetchone()
    return int(row[0])


def migrate(connection: sqlite3.Connection) -> int:
    current = schema_version(connection)
    for number, script in enumerate(MIGRATIONS[current:], start=current + 1):
        connection.executescript(script)
        connection.execute(f"PRAGMA user_version = {number}")
        connection.commit()
    return schema_version(connection)


def save_article(connection: sqlite3.Connection, article: Article) -> None:
    with connection:
        connection.execute(
            "INSERT INTO articles"
            " (id, status, created_at, updated_at, title, summary, body_markdown)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET"
            " status = excluded.status, updated_at = excluded.updated_at,"
            " title = excluded.title, summary = excluded.summary,"
            " body_markdown = excluded.body_markdown",
            (
                article.id,
                article.status.value,
                article.created_at.isoformat(),
                article.updated_at.isoformat(),
                article.source.title,
                article.source.summary,
                article.source.body_markdown,
            ),
        )
        connection.execute("DELETE FROM translations WHERE article_id = ?", (article.id,))
        connection.executemany(
            "INSERT INTO translations"
            " (article_id, language, title, summary, body_markdown, source_checksum)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    article.id,
                    language.value,
                    translation.content.title,
                    translation.content.summary,
                    translation.content.body_markdown,
                    translation.source_checksum,
                )
                for language, translation in sorted(
                    article.translations.items(), key=lambda item: item[0].value
                )
            ],
        )


def load_article(connection: sqlite3.Connection, article_id: str) -> Article | None:
    row = connection.execute(
        "SELECT id, status, created_at, updated_at, title, summary, body_markdown"
        " FROM articles WHERE id = ?",
        (article_id,),
    ).fetchone()
    if row is None:
        return None
    translations: dict[Language, Translation] = {}
    for t_row in connection.execute(
        "SELECT language, title, summary, body_markdown, source_checksum"
        " FROM translations WHERE article_id = ? ORDER BY language",
        (article_id,),
    ):
        translations[Language(t_row[0])] = Translation(
            content=ArticleContent(title=t_row[1], summary=t_row[2], body_markdown=t_row[3]),
            source_checksum=t_row[4],
        )
    return Article(
        id=row[0],
        status=ContentStatus(row[1]),
        created_at=datetime.fromisoformat(row[2]),
        updated_at=datetime.fromisoformat(row[3]),
        source=ArticleContent(title=row[4], summary=row[5], body_markdown=row[6]),
        translations=translations,
    )


def delete_article(connection: sqlite3.Connection, article_id: str) -> bool:
    with connection:
        cursor = connection.execute("DELETE FROM articles WHERE id = ?", (article_id,))
    return cursor.rowcount > 0


def list_article_ids(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute("SELECT id FROM articles ORDER BY id").fetchall()
    return [str(row[0]) for row in rows]


def load_all_articles(connection: sqlite3.Connection) -> list[Article]:
    articles: list[Article] = []
    for article_id in list_article_ids(connection):
        article = load_article(connection, article_id)
        if article is not None:
            articles.append(article)
    return articles
