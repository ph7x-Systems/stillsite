"""SQLite backend (development default).

Schema migrations are ordered scripts applied once each, tracked via SQLite's
``user_version`` pragma.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from cms_core.accounts import AdminSession, Role, User
from cms_core.languages import Language
from cms_core.media import MediaAsset
from cms_core.menus import MenuItem
from cms_core.models import Article, ArticleContent
from cms_core.pages import Page, PageContent, Section, SectionContent
from cms_core.states import ContentStatus
from cms_core.storage.base import StorageBackend
from cms_core.storage.migrations import MIGRATIONS

__all__ = ["MIGRATIONS", "SQLiteBackend", "sqlite_path_from_location"]
from cms_core.translatable import Translation


def sqlite_path_from_location(location: str) -> str:
    """Translate the URL location part into a filesystem path.

    ``sqlite:///relative.db`` -> ``relative.db``;
    ``sqlite:////abs/path.db`` -> ``/abs/path.db``;
    ``:memory:`` (with or without a leading slash) is passed through.
    """
    path = location.removeprefix("/")
    if path == ":memory:":
        return path
    if location.startswith("//"):
        return location[1:]
    return path


class SQLiteBackend(StorageBackend):
    def __init__(self, path: Path | str) -> None:
        self._connection = sqlite3.connect(path)
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA busy_timeout = 5000")
        # WAL survives crashes without blocking readers; NORMAL sync is the
        # recommended pairing (durable at the application level, fast).
        # In-memory databases report "memory" and are unaffected.
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute("PRAGMA synchronous = NORMAL")
        self.migrate()

    def schema_version(self) -> int:
        row = self._connection.execute("PRAGMA user_version").fetchone()
        return int(row[0])

    def migrate(self) -> int:
        current = self.schema_version()
        for number, script in enumerate(MIGRATIONS[current:], start=current + 1):
            self._connection.executescript(script)
            self._connection.execute(f"PRAGMA user_version = {number}")
            self._connection.commit()
        return self.schema_version()

    def close(self) -> None:
        self._connection.close()

    # Articles

    def save_article(self, article: Article) -> None:
        with self._connection as connection:
            connection.execute(
                "INSERT INTO articles"
                " (id, status, created_at, updated_at, title, summary, body_markdown, slug,"
                "  category, tags_json, cover, publish_at, deleted_at, featured, author,"
                "  fields_json)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(id) DO UPDATE SET"
                " status = excluded.status, updated_at = excluded.updated_at,"
                " title = excluded.title, summary = excluded.summary,"
                " body_markdown = excluded.body_markdown, slug = excluded.slug,"
                " category = excluded.category, tags_json = excluded.tags_json,"
                " cover = excluded.cover, publish_at = excluded.publish_at,"
                " deleted_at = excluded.deleted_at, featured = excluded.featured,"
                " author = excluded.author, fields_json = excluded.fields_json",
                (
                    article.id,
                    article.status.value,
                    article.created_at.isoformat(),
                    article.updated_at.isoformat(),
                    article.source.title,
                    article.source.summary,
                    article.source.body_markdown,
                    article.source.slug,
                    article.category,
                    json.dumps(list(article.tags)),
                    article.cover,
                    article.publish_at.isoformat() if article.publish_at else None,
                    article.deleted_at.isoformat() if article.deleted_at else None,
                    1 if article.featured else 0,
                    article.author,
                    json.dumps(article.fields, sort_keys=True),
                ),
            )
            connection.execute("DELETE FROM translations WHERE article_id = ?", (article.id,))
            connection.executemany(
                "INSERT INTO translations"
                " (article_id, language, title, summary, body_markdown, slug, source_checksum)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        article.id,
                        language.value,
                        translation.content.title,
                        translation.content.summary,
                        translation.content.body_markdown,
                        translation.content.slug,
                        translation.source_checksum,
                    )
                    for language, translation in sorted(
                        article.translations.items(), key=lambda item: item[0].value
                    )
                ],
            )

    def load_article(self, article_id: str) -> Article | None:
        row = self._connection.execute(
            "SELECT id, status, created_at, updated_at, title, summary, body_markdown, slug,"
            " category, tags_json, cover, publish_at, deleted_at, featured, author, fields_json"
            " FROM articles WHERE id = ?",
            (article_id,),
        ).fetchone()
        if row is None:
            return None
        translations: dict[Language, Translation[ArticleContent]] = {}
        for t_row in self._connection.execute(
            "SELECT language, title, summary, body_markdown, slug, source_checksum"
            " FROM translations WHERE article_id = ? ORDER BY language",
            (article_id,),
        ):
            translations[Language(t_row[0])] = Translation[ArticleContent](
                content=ArticleContent(
                    title=t_row[1], summary=t_row[2], body_markdown=t_row[3], slug=t_row[4]
                ),
                source_checksum=t_row[5],
            )
        return Article(
            id=row[0],
            status=ContentStatus(row[1]),
            created_at=datetime.fromisoformat(row[2]),
            updated_at=datetime.fromisoformat(row[3]),
            source=ArticleContent(title=row[4], summary=row[5], body_markdown=row[6], slug=row[7]),
            translations=translations,
            category=row[8],
            tags=tuple(json.loads(row[9])),
            cover=row[10],
            publish_at=datetime.fromisoformat(row[11]) if row[11] else None,
            deleted_at=datetime.fromisoformat(row[12]) if row[12] else None,
            featured=bool(row[13]),
            author=row[14],
            fields=json.loads(row[15]) if row[15] else {},
        )

    def delete_article(self, article_id: str) -> bool:
        with self._connection as connection:
            cursor = connection.execute("DELETE FROM articles WHERE id = ?", (article_id,))
        return cursor.rowcount > 0

    def list_article_ids(self) -> list[str]:
        rows = self._connection.execute("SELECT id FROM articles ORDER BY id").fetchall()
        return [str(row[0]) for row in rows]

    # Pages

    def save_page(self, page: Page) -> None:
        with self._connection as connection:
            connection.execute(
                "INSERT INTO pages"
                " (id, status, created_at, updated_at, title, description, slug,"
                "  publish_at, deleted_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(id) DO UPDATE SET"
                " status = excluded.status, updated_at = excluded.updated_at,"
                " title = excluded.title, description = excluded.description,"
                " slug = excluded.slug, publish_at = excluded.publish_at,"
                " deleted_at = excluded.deleted_at",
                (
                    page.id,
                    page.status.value,
                    page.created_at.isoformat(),
                    page.updated_at.isoformat(),
                    page.source.title,
                    page.source.description,
                    page.source.slug,
                    page.publish_at.isoformat() if page.publish_at else None,
                    page.deleted_at.isoformat() if page.deleted_at else None,
                ),
            )
            connection.execute("DELETE FROM page_translations WHERE page_id = ?", (page.id,))
            connection.executemany(
                "INSERT INTO page_translations"
                " (page_id, language, title, description, slug, source_checksum)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        page.id,
                        language.value,
                        translation.content.title,
                        translation.content.description,
                        translation.content.slug,
                        translation.source_checksum,
                    )
                    for language, translation in sorted(
                        page.translations.items(), key=lambda item: item[0].value
                    )
                ],
            )
            connection.execute("DELETE FROM sections WHERE page_id = ?", (page.id,))
            for position, section in enumerate(page.sections):
                connection.execute(
                    "INSERT INTO sections (page_id, key, position, kind, fields_json, media_json)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        page.id,
                        section.key,
                        position,
                        section.kind,
                        json.dumps(section.source.fields, sort_keys=True),
                        json.dumps(section.source.media),
                    ),
                )
                connection.executemany(
                    "INSERT INTO section_translations"
                    " (page_id, section_key, language, fields_json, media_json, source_checksum)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    [
                        (
                            page.id,
                            section.key,
                            language.value,
                            json.dumps(translation.content.fields, sort_keys=True),
                            json.dumps(translation.content.media),
                            translation.source_checksum,
                        )
                        for language, translation in sorted(
                            section.translations.items(), key=lambda item: item[0].value
                        )
                    ],
                )

    def _load_sections(self, page_id: str) -> list[Section]:
        sections: list[Section] = []
        for row in self._connection.execute(
            "SELECT key, kind, fields_json, media_json FROM sections"
            " WHERE page_id = ? ORDER BY position",
            (page_id,),
        ):
            translations: dict[Language, Translation[SectionContent]] = {}
            for t_row in self._connection.execute(
                "SELECT language, fields_json, media_json, source_checksum"
                " FROM section_translations WHERE page_id = ? AND section_key = ?"
                " ORDER BY language",
                (page_id, row[0]),
            ):
                translations[Language(t_row[0])] = Translation[SectionContent](
                    content=SectionContent(fields=json.loads(t_row[1]), media=json.loads(t_row[2])),
                    source_checksum=t_row[3],
                )
            sections.append(
                Section(
                    key=row[0],
                    kind=row[1],
                    source=SectionContent(fields=json.loads(row[2]), media=json.loads(row[3])),
                    translations=translations,
                )
            )
        return sections

    def load_page(self, page_id: str) -> Page | None:
        row = self._connection.execute(
            "SELECT id, status, created_at, updated_at, title, description, slug, publish_at,"
            " deleted_at"
            " FROM pages WHERE id = ?",
            (page_id,),
        ).fetchone()
        if row is None:
            return None
        translations: dict[Language, Translation[PageContent]] = {}
        for t_row in self._connection.execute(
            "SELECT language, title, description, slug, source_checksum"
            " FROM page_translations WHERE page_id = ? ORDER BY language",
            (page_id,),
        ):
            translations[Language(t_row[0])] = Translation[PageContent](
                content=PageContent(title=t_row[1], description=t_row[2], slug=t_row[3]),
                source_checksum=t_row[4],
            )
        return Page(
            id=row[0],
            status=ContentStatus(row[1]),
            created_at=datetime.fromisoformat(row[2]),
            updated_at=datetime.fromisoformat(row[3]),
            source=PageContent(title=row[4], description=row[5], slug=row[6]),
            translations=translations,
            sections=self._load_sections(page_id),
            publish_at=datetime.fromisoformat(row[7]) if row[7] else None,
            deleted_at=datetime.fromisoformat(row[8]) if row[8] else None,
        )

    def delete_page(self, page_id: str) -> bool:
        with self._connection as connection:
            cursor = connection.execute("DELETE FROM pages WHERE id = ?", (page_id,))
        return cursor.rowcount > 0

    def list_page_ids(self) -> list[str]:
        rows = self._connection.execute("SELECT id FROM pages ORDER BY id").fetchall()
        return [str(row[0]) for row in rows]

    # Media

    def save_media_asset(self, asset: MediaAsset) -> None:
        with self._connection as connection:
            connection.execute(
                "INSERT INTO media_assets (id, path, mime_type, width, height)"
                " VALUES (?, ?, ?, ?, ?)"
                " ON CONFLICT(id) DO UPDATE SET"
                " path = excluded.path, mime_type = excluded.mime_type,"
                " width = excluded.width, height = excluded.height",
                (asset.id, asset.path, asset.mime_type, asset.width, asset.height),
            )
            connection.execute("DELETE FROM media_alt_texts WHERE media_id = ?", (asset.id,))
            connection.executemany(
                "INSERT INTO media_alt_texts (media_id, language, alt) VALUES (?, ?, ?)",
                [
                    (asset.id, language.value, alt)
                    for language, alt in sorted(asset.alt.items(), key=lambda item: item[0].value)
                ],
            )

    def load_media_asset(self, asset_id: str) -> MediaAsset | None:
        row = self._connection.execute(
            "SELECT id, path, mime_type, width, height FROM media_assets WHERE id = ?",
            (asset_id,),
        ).fetchone()
        if row is None:
            return None
        alt = {
            Language(alt_row[0]): str(alt_row[1])
            for alt_row in self._connection.execute(
                "SELECT language, alt FROM media_alt_texts WHERE media_id = ? ORDER BY language",
                (asset_id,),
            )
        }
        return MediaAsset(
            id=row[0], path=row[1], mime_type=row[2], width=row[3], height=row[4], alt=alt
        )

    def delete_media_asset(self, asset_id: str) -> bool:
        with self._connection as connection:
            cursor = connection.execute("DELETE FROM media_assets WHERE id = ?", (asset_id,))
        return cursor.rowcount > 0

    def list_media_ids(self) -> list[str]:
        rows = self._connection.execute("SELECT id FROM media_assets ORDER BY id").fetchall()
        return [str(row[0]) for row in rows]

    # Menu items (M6)

    def save_menu_item(self, item: MenuItem) -> None:
        with self._connection as connection:
            connection.execute(
                "INSERT INTO menu_items (id, url, position, labels_json)"
                " VALUES (?, ?, ?, ?)"
                " ON CONFLICT(id) DO UPDATE SET url = excluded.url,"
                " position = excluded.position, labels_json = excluded.labels_json",
                (
                    item.id,
                    item.url,
                    item.position,
                    json.dumps({k.value: v for k, v in item.labels.items()}, sort_keys=True),
                ),
            )

    def load_menu_items(self) -> list[MenuItem]:
        rows = self._connection.execute(
            "SELECT id, url, position, labels_json FROM menu_items ORDER BY position, id"
        ).fetchall()
        return [
            MenuItem(
                id=row[0],
                url=row[1],
                position=int(row[2]),
                labels={Language(k): v for k, v in json.loads(row[3]).items()},
            )
            for row in rows
        ]

    def delete_menu_item(self, item_id: str) -> bool:
        with self._connection as connection:
            cursor = connection.execute("DELETE FROM menu_items WHERE id = ?", (item_id,))
        return cursor.rowcount > 0

    # Editorial notes (M5)

    def add_note(
        self, entity_type: str, entity_id: str, author: str, body: str, created_at: datetime
    ) -> int:
        with self._connection as connection:
            row = connection.execute(
                "SELECT COALESCE(MAX(seq), 0) FROM notes WHERE entity_type = ? AND entity_id = ?",
                (entity_type, entity_id),
            ).fetchone()
            number = int(row[0]) + 1
            connection.execute(
                "INSERT INTO notes (entity_type, entity_id, seq, created_at, author, body)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (entity_type, entity_id, number, created_at.isoformat(), author, body),
            )
        return number

    def list_notes(self, entity_type: str, entity_id: str) -> list[tuple[int, datetime, str, str]]:
        rows = self._connection.execute(
            "SELECT seq, created_at, author, body FROM notes"
            " WHERE entity_type = ? AND entity_id = ? ORDER BY seq DESC",
            (entity_type, entity_id),
        ).fetchall()
        return [(int(r[0]), datetime.fromisoformat(r[1]), str(r[2]), str(r[3])) for r in rows]

    def delete_note(self, entity_type: str, entity_id: str, seq: int) -> bool:
        with self._connection as connection:
            cursor = connection.execute(
                "DELETE FROM notes WHERE entity_type = ? AND entity_id = ? AND seq = ?",
                (entity_type, entity_id, seq),
            )
        return cursor.rowcount > 0

    # Revisions (ADR-0025)

    def save_revision(
        self, entity_type: str, entity_id: str, author: str, payload_json: str, created_at: datetime
    ) -> int:
        with self._connection as connection:
            row = connection.execute(
                "SELECT COALESCE(MAX(revision), 0) FROM revisions"
                " WHERE entity_type = ? AND entity_id = ?",
                (entity_type, entity_id),
            ).fetchone()
            number = int(row[0]) + 1
            connection.execute(
                "INSERT INTO revisions"
                " (entity_type, entity_id, revision, created_at, author, payload_json)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (entity_type, entity_id, number, created_at.isoformat(), author, payload_json),
            )
            connection.execute(
                "DELETE FROM revisions WHERE entity_type = ? AND entity_id = ? AND revision <= ?",
                (entity_type, entity_id, number - self.REVISION_LIMIT),
            )
        return number

    def list_revisions(self, entity_type: str, entity_id: str) -> list[tuple[int, datetime, str]]:
        rows = self._connection.execute(
            "SELECT revision, created_at, author FROM revisions"
            " WHERE entity_type = ? AND entity_id = ? ORDER BY revision DESC",
            (entity_type, entity_id),
        ).fetchall()
        return [(int(r[0]), datetime.fromisoformat(r[1]), str(r[2])) for r in rows]

    def load_revision(self, entity_type: str, entity_id: str, revision: int) -> str | None:
        row = self._connection.execute(
            "SELECT payload_json FROM revisions"
            " WHERE entity_type = ? AND entity_id = ? AND revision = ?",
            (entity_type, entity_id, revision),
        ).fetchone()
        return str(row[0]) if row else None

    # Admin accounts

    def save_user(self, user: User) -> None:
        with self._connection as connection:
            connection.execute(
                "INSERT INTO users (username, password_hash, role, created_at, language)"
                " VALUES (?, ?, ?, ?, ?)"
                " ON CONFLICT(username) DO UPDATE SET"
                " password_hash = excluded.password_hash, role = excluded.role,"
                " language = excluded.language",
                (
                    user.username,
                    user.password_hash,
                    user.role.value,
                    user.created_at.isoformat(),
                    user.language.value if user.language else None,
                ),
            )

    def load_user(self, username: str) -> User | None:
        row = self._connection.execute(
            "SELECT username, password_hash, role, created_at, language"
            " FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if row is None:
            return None
        return User(
            username=row[0],
            password_hash=row[1],
            role=Role(row[2]),
            created_at=datetime.fromisoformat(row[3]),
            language=Language(row[4]) if row[4] else None,
        )

    def delete_user(self, username: str) -> bool:
        with self._connection as connection:
            cursor = connection.execute("DELETE FROM users WHERE username = ?", (username,))
        return cursor.rowcount > 0

    def list_usernames(self) -> list[str]:
        rows = self._connection.execute("SELECT username FROM users ORDER BY username").fetchall()
        return [str(row[0]) for row in rows]

    # Admin sessions

    def save_session(self, session: AdminSession) -> None:
        with self._connection as connection:
            connection.execute(
                "INSERT INTO admin_sessions (token_hash, username, csrf_token, expires_at)"
                " VALUES (?, ?, ?, ?)"
                " ON CONFLICT(token_hash) DO UPDATE SET expires_at = excluded.expires_at",
                (
                    session.token_hash,
                    session.username,
                    session.csrf_token,
                    session.expires_at.isoformat(),
                ),
            )

    def load_session(self, token_hash: str) -> AdminSession | None:
        row = self._connection.execute(
            "SELECT token_hash, username, csrf_token, expires_at"
            " FROM admin_sessions WHERE token_hash = ?",
            (token_hash,),
        ).fetchone()
        if row is None:
            return None
        return AdminSession(
            token_hash=row[0],
            username=row[1],
            csrf_token=row[2],
            expires_at=datetime.fromisoformat(row[3]),
        )

    def delete_session(self, token_hash: str) -> bool:
        with self._connection as connection:
            cursor = connection.execute(
                "DELETE FROM admin_sessions WHERE token_hash = ?", (token_hash,)
            )
        return cursor.rowcount > 0

    def delete_expired_sessions(self, now: datetime) -> int:
        with self._connection as connection:
            cursor = connection.execute(
                "DELETE FROM admin_sessions WHERE expires_at <= ?", (now.isoformat(),)
            )
        return cursor.rowcount
