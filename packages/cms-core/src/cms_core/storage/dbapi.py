"""Shared DB-API implementation for the MySQL and SQL Server backends.

The CRUD logic is identical across SQL engines; what differs is the dialect
(key column types, upsert syntax) and the connection niceties. Subclasses
provide a connection, a migration-script transform and an upsert strategy;
everything else lives here once. The shared migration history from
:mod:`cms_core.storage.migrations` applies unchanged in content — the
transform only adapts column types the engine cannot index (ANSI ``TEXT``
keys become bounded ``VARCHAR``s), tracked in a ``schema_migrations`` table
exactly like the PostgreSQL backend.
"""

import json
import re
from abc import abstractmethod
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from cms_core.accounts import AdminSession, PasswordReset, Role, User
from cms_core.activity import ActivityRecord
from cms_core.languages import Language
from cms_core.media import MediaAsset
from cms_core.menus import MenuItem
from cms_core.models import Article, ArticleContent
from cms_core.pages import Page, PageContent, Section, SectionContent
from cms_core.search import SearchHit, like_pattern
from cms_core.states import ContentStatus
from cms_core.storage.base import StorageBackend
from cms_core.storage.migrations import MIGRATIONS
from cms_core.translatable import Translation

# ANSI TEXT columns that participate in keys/references must become bounded
# VARCHARs on engines that cannot index unbounded text. Shared by both
# dialects; the value type is engine-specific.
KEY_COLUMNS = (
    "id",
    "article_id",
    "page_id",
    "section_key",
    "media_id",
    "username",
    "token_hash",
    "language",
    "key",
    "entity_type",
    "entity_id",
)


def split_statements(script: str) -> list[str]:
    """The shared migrations bundle several statements per script."""
    return [statement.strip() for statement in script.split(";") if statement.strip()]


def rewrite_key_columns(statement: str, key_type: str) -> str:
    """Turn `<key column> TEXT` into a bounded type the engine can index."""
    pattern = r"\b(" + "|".join(KEY_COLUMNS) + r")\s+TEXT\b"
    return re.sub(pattern, lambda m: f"{m.group(1)} {key_type}", statement)


class DbApiBackend(StorageBackend):
    """Everything above the driver: CRUD, migrations, version tracking."""

    def __init__(self) -> None:
        self._connection = self._connect()
        self.migrate()

    # --- engine-specific surface -------------------------------------------------

    @abstractmethod
    def _connect(self) -> Any: ...

    @abstractmethod
    def _migration_statements(self, script: str) -> list[str]:
        """Dialect-adapted statements for one shared migration script."""

    @abstractmethod
    def _upsert(self, table: str, keys: dict[str, Any], values: dict[str, Any]) -> None:
        """Insert or update one row, without touching other tables' rows."""

    # --- plumbing ----------------------------------------------------------------

    def _execute(self, sql: str, params: Sequence[Any] = ()) -> Any:
        cursor = self._connection.cursor()
        cursor.execute(sql, tuple(params))
        return cursor

    @contextmanager
    def _tx(self) -> Iterator[None]:
        try:
            yield
        except Exception:
            self._connection.rollback()
            raise
        self._connection.commit()

    def _fetchone(self, sql: str, params: Sequence[Any] = ()) -> Any:
        return self._execute(sql, params).fetchone()

    def _fetchall(self, sql: str, params: Sequence[Any] = ()) -> list[Any]:
        return list(self._execute(sql, params).fetchall())

    # --- migrations --------------------------------------------------------------

    def _ensure_migrations_table(self) -> None:
        self._execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)")

    def schema_version(self) -> int:
        with self._tx():
            self._ensure_migrations_table()
        row = self._fetchone("SELECT COALESCE(MAX(version), 0) FROM schema_migrations")
        return int(row[0]) if row else 0

    def migrate(self) -> int:
        current = self.schema_version()
        for number, script in enumerate(MIGRATIONS[current:], start=current + 1):
            with self._tx():
                for statement in self._migration_statements(script):
                    self._execute(statement)
                self._execute("INSERT INTO schema_migrations (version) VALUES (%s)", (number,))
        return self.schema_version()

    def close(self) -> None:
        if getattr(self, "_closed", False):
            return
        self._connection.close()
        self._closed = True

    # --- articles ----------------------------------------------------------------

    def save_article(self, article: Article) -> None:
        with self._tx():
            self._upsert(
                "articles",
                {"id": article.id},
                {
                    "status": article.status.value,
                    "created_at": article.created_at.isoformat(),
                    "updated_at": article.updated_at.isoformat(),
                    "title": article.source.title,
                    "summary": article.source.summary,
                    "body_markdown": article.source.body_markdown,
                    "slug": article.source.slug,
                    "category": article.category,
                    "tags_json": json.dumps(list(article.tags)),
                    "cover": article.cover,
                    "publish_at": article.publish_at.isoformat() if article.publish_at else None,
                    "deleted_at": article.deleted_at.isoformat() if article.deleted_at else None,
                    "featured": 1 if article.featured else 0,
                    "author": article.author,
                    "fields_json": json.dumps(article.fields, sort_keys=True),
                    "unpublish_at": (
                        article.unpublish_at.isoformat() if article.unpublish_at else None
                    ),
                },
            )
            self._execute("DELETE FROM translations WHERE article_id = %s", (article.id,))
            for language, translation in sorted(
                article.translations.items(), key=lambda item: item[0].value
            ):
                self._execute(
                    "INSERT INTO translations"
                    " (article_id, language, title, summary, body_markdown, slug,"
                    "  source_checksum)"
                    " VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (
                        article.id,
                        language.value,
                        translation.content.title,
                        translation.content.summary,
                        translation.content.body_markdown,
                        translation.content.slug,
                        translation.source_checksum,
                    ),
                )

    def load_article(self, article_id: str) -> Article | None:
        row = self._fetchone(
            "SELECT id, status, created_at, updated_at, title, summary, body_markdown, slug,"
            " category, tags_json, cover, publish_at, deleted_at, featured, author, fields_json,"
            " unpublish_at FROM articles WHERE id = %s",
            (article_id,),
        )
        if row is None:
            return None
        translations: dict[Language, Translation[ArticleContent]] = {}
        for t_row in self._fetchall(
            "SELECT language, title, summary, body_markdown, slug, source_checksum"
            " FROM translations WHERE article_id = %s ORDER BY language",
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
            unpublish_at=datetime.fromisoformat(row[16]) if row[16] else None,
            deleted_at=datetime.fromisoformat(row[12]) if row[12] else None,
            featured=bool(row[13]),
            author=row[14],
            fields=json.loads(row[15]) if row[15] else {},
        )

    def delete_article(self, article_id: str) -> bool:
        with self._tx():
            cursor = self._execute("DELETE FROM articles WHERE id = %s", (article_id,))
            count = int(cursor.rowcount)
        return count > 0

    def list_article_ids(self) -> list[str]:
        return [str(row[0]) for row in self._fetchall("SELECT id FROM articles ORDER BY id")]

    # --- pages -------------------------------------------------------------------

    def save_page(self, page: Page) -> None:
        with self._tx():
            self._upsert(
                "pages",
                {"id": page.id},
                {
                    "status": page.status.value,
                    "created_at": page.created_at.isoformat(),
                    "updated_at": page.updated_at.isoformat(),
                    "title": page.source.title,
                    "description": page.source.description,
                    "slug": page.source.slug,
                    "body_markdown": page.source.body_markdown,
                    "unpublish_at": (page.unpublish_at.isoformat() if page.unpublish_at else None),
                    "publish_at": page.publish_at.isoformat() if page.publish_at else None,
                    "deleted_at": page.deleted_at.isoformat() if page.deleted_at else None,
                },
            )
            self._execute("DELETE FROM page_translations WHERE page_id = %s", (page.id,))
            for language, translation in sorted(
                page.translations.items(), key=lambda item: item[0].value
            ):
                self._execute(
                    "INSERT INTO page_translations"
                    " (page_id, language, title, description, slug, source_checksum,"
                    "  body_markdown)"
                    " VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (
                        page.id,
                        language.value,
                        translation.content.title,
                        translation.content.description,
                        translation.content.slug,
                        translation.source_checksum,
                        translation.content.body_markdown,
                    ),
                )
            self._execute("DELETE FROM section_translations WHERE page_id = %s", (page.id,))
            self._execute("DELETE FROM sections WHERE page_id = %s", (page.id,))
            for position, section in enumerate(page.sections):
                self._execute(
                    "INSERT INTO sections"
                    " (page_id, " + self._quoted_key_column() + ", position, kind,"
                    "  fields_json, media_json, items_json, hidden)"
                    " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        page.id,
                        section.key,
                        position,
                        section.kind,
                        json.dumps(section.source.fields, sort_keys=True),
                        json.dumps(section.source.media),
                        json.dumps(section.source.items, sort_keys=True),
                        1 if section.hidden else 0,
                    ),
                )
                for section_language, section_translation in sorted(
                    section.translations.items(), key=lambda item: item[0].value
                ):
                    self._execute(
                        "INSERT INTO section_translations"
                        " (page_id, section_key, language, fields_json, media_json,"
                        "  source_checksum, items_json)"
                        " VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (
                            page.id,
                            section.key,
                            section_language.value,
                            json.dumps(section_translation.content.fields, sort_keys=True),
                            json.dumps(section_translation.content.media),
                            section_translation.source_checksum,
                            json.dumps(section_translation.content.items, sort_keys=True),
                        ),
                    )

    def _quoted_key_column(self) -> str:
        """`key` is reserved on MySQL; engines quote it their own way."""
        return "key"

    def _load_sections(self, page_id: str) -> list[Section]:
        sections: list[Section] = []
        for row in self._fetchall(
            "SELECT " + self._quoted_key_column() + ", kind, fields_json, media_json,"
            " items_json, hidden FROM sections WHERE page_id = %s ORDER BY position",
            (page_id,),
        ):
            translations: dict[Language, Translation[SectionContent]] = {}
            for t_row in self._fetchall(
                "SELECT language, fields_json, media_json, source_checksum, items_json"
                " FROM section_translations WHERE page_id = %s AND section_key = %s"
                " ORDER BY language",
                (page_id, row[0]),
            ):
                translations[Language(t_row[0])] = Translation[SectionContent](
                    content=SectionContent(
                        fields=json.loads(t_row[1]),
                        media=json.loads(t_row[2]),
                        items=json.loads(t_row[4]),
                    ),
                    source_checksum=t_row[3],
                )
            sections.append(
                Section(
                    key=row[0],
                    kind=row[1],
                    hidden=bool(row[5]),
                    source=SectionContent(
                        fields=json.loads(row[2]),
                        media=json.loads(row[3]),
                        items=json.loads(row[4]),
                    ),
                    translations=translations,
                )
            )
        return sections

    def search_content(self, needle: str, limit: int = 20) -> list[SearchHit]:
        """LIKE-based override of the portable default (#129): four
        queries instead of loading every entry; case folded on both
        sides, user input made literal via ESCAPE '!'."""
        if not needle:
            return []
        pattern = like_pattern(needle)
        hits: list[SearchHit] = []
        rows = self._search_rows(
            "SELECT DISTINCT a.id, a.title FROM articles a"
            " LEFT JOIN translations t ON t.article_id = a.id"
            " WHERE a.deleted_at IS NULL AND ("
            "  LOWER(a.id) LIKE %s ESCAPE '!' OR LOWER(a.title) LIKE %s ESCAPE '!'"
            "  OR LOWER(a.summary) LIKE %s ESCAPE '!'"
            "  OR LOWER(a.body_markdown) LIKE %s ESCAPE '!'"
            "  OR LOWER(t.title) LIKE %s ESCAPE '!' OR LOWER(t.summary) LIKE %s ESCAPE '!'"
            "  OR LOWER(t.body_markdown) LIKE %s ESCAPE '!')"
            " ORDER BY a.id",
            (pattern,) * 7,
        )
        hits.extend(SearchHit("article", row[0], row[1]) for row in rows[:limit])
        rows = self._search_rows(
            "SELECT DISTINCT p.id, p.title FROM pages p"
            " LEFT JOIN page_translations t ON t.page_id = p.id"
            " WHERE p.deleted_at IS NULL AND ("
            "  LOWER(p.id) LIKE %s ESCAPE '!' OR LOWER(p.title) LIKE %s ESCAPE '!'"
            "  OR LOWER(p.description) LIKE %s ESCAPE '!'"
            "  OR LOWER(p.body_markdown) LIKE %s ESCAPE '!'"
            "  OR LOWER(t.title) LIKE %s ESCAPE '!' OR LOWER(t.description) LIKE %s ESCAPE '!'"
            "  OR LOWER(t.body_markdown) LIKE %s ESCAPE '!')"
            " ORDER BY p.id",
            (pattern,) * 7,
        )
        hits.extend(SearchHit("page", row[0], row[1]) for row in rows[:limit])
        key = self._quoted_key_column()
        section_sql = (
            f"SELECT DISTINCT s.page_id, s.{key}, s.kind FROM sections s"
            " JOIN pages p ON p.id = s.page_id AND p.deleted_at IS NULL"
            " LEFT JOIN section_translations t"
            f"  ON t.page_id = s.page_id AND t.section_key = s.{key}"
            f" WHERE LOWER(s.{key}) LIKE %s ESCAPE '!'"
            "  OR LOWER(s.fields_json) LIKE %s ESCAPE '!'"
            "  OR LOWER(s.items_json) LIKE %s ESCAPE '!'"
            "  OR LOWER(t.fields_json) LIKE %s ESCAPE '!'"
            "  OR LOWER(t.items_json) LIKE %s ESCAPE '!'"
            f" ORDER BY s.page_id, s.{key}"
        )
        rows = self._search_rows(section_sql, (pattern,) * 5)
        hits.extend(
            SearchHit("section", f"{row[0]}/{row[1]}", row[1], row[2]) for row in rows[:limit]
        )
        rows = self._search_rows(
            "SELECT DISTINCT m.id, m.path FROM media_assets m"
            " LEFT JOIN media_alt_texts alt ON alt.media_id = m.id"
            " WHERE LOWER(m.id) LIKE %s ESCAPE '!' OR LOWER(m.path) LIKE %s ESCAPE '!'"
            "  OR LOWER(alt.alt) LIKE %s ESCAPE '!'"
            " ORDER BY m.id",
            (pattern,) * 3,
        )
        hits.extend(SearchHit("media", row[0], row[1]) for row in rows[:limit])
        return hits

    def _search_rows(self, sql: str, params: tuple[str, ...]) -> list[tuple[str, ...]]:
        return [tuple(row) for row in self._fetchall(sql, params)]

    def load_page(self, page_id: str) -> Page | None:
        row = self._fetchone(
            "SELECT id, status, created_at, updated_at, title, description, slug, publish_at,"
            " deleted_at, body_markdown, unpublish_at FROM pages WHERE id = %s",
            (page_id,),
        )
        if row is None:
            return None
        translations: dict[Language, Translation[PageContent]] = {}
        for t_row in self._fetchall(
            "SELECT language, title, description, slug, source_checksum, body_markdown"
            " FROM page_translations WHERE page_id = %s ORDER BY language",
            (page_id,),
        ):
            translations[Language(t_row[0])] = Translation[PageContent](
                content=PageContent(
                    title=t_row[1], description=t_row[2], slug=t_row[3], body_markdown=t_row[5]
                ),
                source_checksum=t_row[4],
            )
        return Page(
            id=row[0],
            status=ContentStatus(row[1]),
            created_at=datetime.fromisoformat(row[2]),
            updated_at=datetime.fromisoformat(row[3]),
            source=PageContent(title=row[4], description=row[5], slug=row[6], body_markdown=row[9]),
            translations=translations,
            sections=self._load_sections(row[0]),
            publish_at=datetime.fromisoformat(row[7]) if row[7] else None,
            unpublish_at=datetime.fromisoformat(row[10]) if row[10] else None,
            deleted_at=datetime.fromisoformat(row[8]) if row[8] else None,
        )

    def delete_page(self, page_id: str) -> bool:
        with self._tx():
            self._execute("DELETE FROM section_translations WHERE page_id = %s", (page_id,))
            self._execute("DELETE FROM sections WHERE page_id = %s", (page_id,))
            self._execute("DELETE FROM page_translations WHERE page_id = %s", (page_id,))
            cursor = self._execute("DELETE FROM pages WHERE id = %s", (page_id,))
            count = int(cursor.rowcount)
        return count > 0

    def list_page_ids(self) -> list[str]:
        return [str(row[0]) for row in self._fetchall("SELECT id FROM pages ORDER BY id")]

    # --- media -------------------------------------------------------------------

    def save_media_asset(self, asset: MediaAsset) -> None:
        with self._tx():
            self._upsert(
                "media_assets",
                {"id": asset.id},
                {
                    "path": asset.path,
                    "mime_type": asset.mime_type,
                    "width": asset.width,
                    "height": asset.height,
                    "collection": asset.collection,
                    "content_hash": asset.content_hash,
                    "crop": asset.crop,
                    "focal": asset.focal,
                },
            )
            self._execute("DELETE FROM media_alt_texts WHERE media_id = %s", (asset.id,))
            for language, alt in sorted(asset.alt.items(), key=lambda item: item[0].value):
                self._execute(
                    "INSERT INTO media_alt_texts (media_id, language, alt) VALUES (%s, %s, %s)",
                    (asset.id, language.value, alt),
                )

    def load_media_asset(self, asset_id: str) -> MediaAsset | None:
        row = self._fetchone(
            "SELECT id, path, mime_type, width, height, collection, content_hash, crop, focal"
            " FROM media_assets WHERE id = %s",
            (asset_id,),
        )
        if row is None:
            return None
        alt = {
            Language(alt_row[0]): str(alt_row[1])
            for alt_row in self._fetchall(
                "SELECT language, alt FROM media_alt_texts WHERE media_id = %s ORDER BY language",
                (asset_id,),
            )
        }
        return MediaAsset(
            id=row[0],
            path=row[1],
            mime_type=row[2],
            width=row[3],
            height=row[4],
            alt=alt,
            collection=str(row[5] or ""),
            content_hash=str(row[6] or ""),
            crop=str(row[7] or ""),
            focal=str(row[8] or ""),
        )

    def delete_media_asset(self, asset_id: str) -> bool:
        with self._tx():
            cursor = self._execute("DELETE FROM media_assets WHERE id = %s", (asset_id,))
            count = int(cursor.rowcount)
        return count > 0

    def list_media_ids(self) -> list[str]:
        return [str(row[0]) for row in self._fetchall("SELECT id FROM media_assets ORDER BY id")]

    # --- admin accounts ----------------------------------------------------------

    # Menu items (M6)

    def save_menu_item(self, item: MenuItem) -> None:
        with self._tx():
            self._upsert(
                "menu_items",
                {"id": item.id},
                {
                    "url": item.url,
                    "position": item.position,
                    "labels_json": json.dumps(
                        {k.value: v for k, v in item.labels.items()}, sort_keys=True
                    ),
                },
            )

    def load_menu_items(self) -> list[MenuItem]:
        rows = self._fetchall(
            "SELECT id, url, position, labels_json FROM menu_items ORDER BY position, id", ()
        )
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
        with self._tx():
            cursor = self._execute("DELETE FROM menu_items WHERE id = %s", (item_id,))
            count = int(cursor.rowcount)
        return count > 0

    # Editorial notes (M5)

    def add_note(
        self, entity_type: str, entity_id: str, author: str, body: str, created_at: datetime
    ) -> int:
        with self._tx():
            row = self._fetchone(
                "SELECT COALESCE(MAX(seq), 0) FROM notes WHERE entity_type = %s AND entity_id = %s",
                (entity_type, entity_id),
            )
            number = int(row[0]) + 1 if row else 1
            self._execute(
                "INSERT INTO notes (entity_type, entity_id, seq, created_at, author, body)"
                " VALUES (%s, %s, %s, %s, %s, %s)",
                (entity_type, entity_id, number, created_at.isoformat(), author, body),
            )
        return number

    def list_notes(self, entity_type: str, entity_id: str) -> list[tuple[int, datetime, str, str]]:
        rows = self._fetchall(
            "SELECT seq, created_at, author, body FROM notes"
            " WHERE entity_type = %s AND entity_id = %s ORDER BY seq DESC",
            (entity_type, entity_id),
        )
        return [(int(r[0]), datetime.fromisoformat(r[1]), str(r[2]), str(r[3])) for r in rows]

    def delete_note(self, entity_type: str, entity_id: str, seq: int) -> bool:
        with self._tx():
            cursor = self._execute(
                "DELETE FROM notes WHERE entity_type = %s AND entity_id = %s AND seq = %s",
                (entity_type, entity_id, seq),
            )
            count = int(cursor.rowcount)
        return count > 0

    # Revisions (ADR-0025)

    def save_revision(
        self, entity_type: str, entity_id: str, author: str, payload_json: str, created_at: datetime
    ) -> int:
        with self._tx():
            row = self._fetchone(
                "SELECT COALESCE(MAX(revision), 0) FROM revisions"
                " WHERE entity_type = %s AND entity_id = %s",
                (entity_type, entity_id),
            )
            number = int(row[0]) + 1 if row else 1
            self._execute(
                "INSERT INTO revisions"
                " (entity_type, entity_id, revision, created_at, author, payload_json)"
                " VALUES (%s, %s, %s, %s, %s, %s)",
                (entity_type, entity_id, number, created_at.isoformat(), author, payload_json),
            )
            self._execute(
                "DELETE FROM revisions WHERE entity_type = %s AND entity_id = %s"
                " AND revision <= %s",
                (entity_type, entity_id, number - self.REVISION_LIMIT),
            )
        return number

    def list_revisions(self, entity_type: str, entity_id: str) -> list[tuple[int, datetime, str]]:
        rows = self._fetchall(
            "SELECT revision, created_at, author FROM revisions"
            " WHERE entity_type = %s AND entity_id = %s ORDER BY revision DESC",
            (entity_type, entity_id),
        )
        return [(int(r[0]), datetime.fromisoformat(r[1]), str(r[2])) for r in rows]

    def load_revision(self, entity_type: str, entity_id: str, revision: int) -> str | None:
        row = self._fetchone(
            "SELECT payload_json FROM revisions"
            " WHERE entity_type = %s AND entity_id = %s AND revision = %s",
            (entity_type, entity_id, revision),
        )
        return str(row[0]) if row else None

    def save_user(self, user: User) -> None:
        with self._tx():
            self._upsert(
                "users",
                {"username": user.username},
                {
                    "password_hash": user.password_hash,
                    "role": user.role.value,
                    "created_at": user.created_at.isoformat(),
                    "language": user.language.value if user.language else None,
                    "email": user.email,
                    "totp_secret": user.totp_secret,
                    "totp_step": user.totp_step,
                },
            )

    def load_user(self, username: str) -> User | None:
        row = self._fetchone(
            "SELECT username, password_hash, role, created_at, language, email,"
            " totp_secret, totp_step"
            " FROM users WHERE username = %s",
            (username,),
        )
        if row is None:
            return None
        return User(
            username=row[0],
            password_hash=row[1],
            role=Role(row[2]),
            created_at=datetime.fromisoformat(row[3]),
            language=Language(row[4]) if row[4] else None,
            email=row[5],
            totp_secret=row[6],
            totp_step=int(row[7]) if row[7] is not None else None,
        )

    def delete_user(self, username: str) -> bool:
        with self._tx():
            self._execute("DELETE FROM admin_sessions WHERE username = %s", (username,))
            self._execute("DELETE FROM password_resets WHERE username = %s", (username,))
            cursor = self._execute("DELETE FROM users WHERE username = %s", (username,))
            count = int(cursor.rowcount)
        return count > 0

    def list_usernames(self) -> list[str]:
        return [
            str(row[0]) for row in self._fetchall("SELECT username FROM users ORDER BY username")
        ]

    # --- admin sessions ----------------------------------------------------------

    def save_session(self, session: AdminSession) -> None:
        with self._tx():
            self._upsert(
                "admin_sessions",
                {"token_hash": session.token_hash},
                {
                    "username": session.username,
                    "csrf_token": session.csrf_token,
                    "expires_at": session.expires_at.isoformat(),
                },
            )

    def load_session(self, token_hash: str) -> AdminSession | None:
        row = self._fetchone(
            "SELECT token_hash, username, csrf_token, expires_at"
            " FROM admin_sessions WHERE token_hash = %s",
            (token_hash,),
        )
        if row is None:
            return None
        return AdminSession(
            token_hash=row[0],
            username=row[1],
            csrf_token=row[2],
            expires_at=datetime.fromisoformat(row[3]),
        )

    def delete_session(self, token_hash: str) -> bool:
        with self._tx():
            cursor = self._execute(
                "DELETE FROM admin_sessions WHERE token_hash = %s", (token_hash,)
            )
            count = int(cursor.rowcount)
        return count > 0

    def record_activity(self, record: ActivityRecord) -> None:
        with self._tx():
            self._execute(
                "INSERT INTO activity (at, actor, action, subject_kind, subject_id, detail)"
                " VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    record.at.isoformat(),
                    record.actor,
                    record.action,
                    record.subject_kind,
                    record.subject_id,
                    record.detail,
                ),
            )

    def list_activity(
        self,
        limit: int = 100,
        actor: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[ActivityRecord]:
        clauses = []
        params: list[str] = []
        if actor:
            clauses.append("actor = %s")
            params.append(actor)
        if since:
            clauses.append("at >= %s")
            params.append(since.isoformat())
        if until:
            clauses.append("at < %s")
            params.append(until.isoformat())
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._fetchall(
            # The concatenated fragments are all literals above; every
            # value is bound. nosec B608: no user data reaches the SQL text.
            "SELECT at, actor, action, subject_kind, subject_id, detail FROM activity"  # nosec B608
            + where
            + " ORDER BY at DESC",
            tuple(params),
        )
        records = [
            ActivityRecord(
                at=datetime.fromisoformat(row[0]),
                actor=row[1],
                action=row[2],
                subject_kind=row[3],
                subject_id=row[4],
                detail=row[5],
            )
            for row in rows
        ]
        return records[:limit]

    def prune_activity(self, before: datetime) -> int:
        with self._tx():
            cursor = self._execute("DELETE FROM activity WHERE at < %s", (before.isoformat(),))
            count = int(cursor.rowcount)
        return count

    def delete_expired_sessions(self, now: datetime) -> int:
        with self._tx():
            cursor = self._execute(
                "DELETE FROM admin_sessions WHERE expires_at <= %s", (now.isoformat(),)
            )
            count = int(cursor.rowcount)
        return count

    def delete_sessions_for(self, username: str) -> int:
        with self._tx():
            cursor = self._execute("DELETE FROM admin_sessions WHERE username = %s", (username,))
            count = int(cursor.rowcount)
        return count

    def save_password_reset(self, reset: PasswordReset) -> None:
        with self._tx():
            self._upsert(
                "password_resets",
                {"token_hash": reset.token_hash},
                {"username": reset.username, "expires_at": reset.expires_at.isoformat()},
            )

    def pop_password_reset(self, token_hash: str, now: datetime) -> PasswordReset | None:
        row = self._fetchone(
            "SELECT token_hash, username, expires_at FROM password_resets WHERE token_hash = %s",
            (token_hash,),
        )
        if row is None:
            return None
        with self._tx():
            self._execute("DELETE FROM password_resets WHERE token_hash = %s", (token_hash,))
        expires_at = datetime.fromisoformat(row[2])
        if expires_at <= now:
            return None
        return PasswordReset(token_hash=str(row[0]), username=str(row[1]), expires_at=expires_at)

    def delete_password_resets_for(self, username: str) -> int:
        with self._tx():
            cursor = self._execute("DELETE FROM password_resets WHERE username = %s", (username,))
            count = int(cursor.rowcount)
        return count
