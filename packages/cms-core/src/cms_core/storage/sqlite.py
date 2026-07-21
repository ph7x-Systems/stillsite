"""SQLite backend (development default).

Schema migrations are ordered scripts applied once each, tracked via SQLite's
``user_version`` pragma.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from cms_core.accounts import AdminSession, PasswordReset, Role, User
from cms_core.activity import ActivityRecord
from cms_core.forms import FormSubmission
from cms_core.languages import Language
from cms_core.media import MediaAsset
from cms_core.menus import MenuItem
from cms_core.models import Article, ArticleContent
from cms_core.pages import Page, PageContent, Section, SectionContent
from cms_core.search import SearchHit, like_pattern
from cms_core.states import ContentStatus
from cms_core.storage.base import StorageBackend
from cms_core.storage.migrations import MIGRATIONS

__all__ = ["MIGRATIONS", "SQLiteBackend", "sqlite_path_from_location"]
from cms_core.translatable import Seo, Translation


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


def _seo_from_json(raw: object) -> Seo:
    """Parse a stored seo_json payload; anything falsy is the default."""
    if not raw:
        return Seo()
    return Seo(**json.loads(str(raw)))


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
                "  fields_json, unpublish_at, seo_json)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(id) DO UPDATE SET"
                " status = excluded.status, updated_at = excluded.updated_at,"
                " title = excluded.title, summary = excluded.summary,"
                " body_markdown = excluded.body_markdown, slug = excluded.slug,"
                " category = excluded.category, tags_json = excluded.tags_json,"
                " cover = excluded.cover, publish_at = excluded.publish_at,"
                " deleted_at = excluded.deleted_at, featured = excluded.featured,"
                " author = excluded.author, fields_json = excluded.fields_json,"
                " unpublish_at = excluded.unpublish_at, seo_json = excluded.seo_json",
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
                    article.unpublish_at.isoformat() if article.unpublish_at else None,
                    json.dumps(article.source.seo.model_dump(), sort_keys=True),
                ),
            )
            connection.execute("DELETE FROM translations WHERE article_id = ?", (article.id,))
            connection.executemany(
                "INSERT INTO translations"
                " (article_id, language, title, summary, body_markdown, slug, source_checksum,"
                "  seo_json)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        article.id,
                        language.value,
                        translation.content.title,
                        translation.content.summary,
                        translation.content.body_markdown,
                        translation.content.slug,
                        translation.source_checksum,
                        json.dumps(translation.content.seo.model_dump(), sort_keys=True),
                    )
                    for language, translation in sorted(
                        article.translations.items(), key=lambda item: item[0].value
                    )
                ],
            )

    def load_article(self, article_id: str) -> Article | None:
        row = self._connection.execute(
            "SELECT id, status, created_at, updated_at, title, summary, body_markdown, slug,"
            " category, tags_json, cover, publish_at, deleted_at, featured, author, fields_json,"
            " unpublish_at, seo_json FROM articles WHERE id = ?",
            (article_id,),
        ).fetchone()
        if row is None:
            return None
        translations: dict[Language, Translation[ArticleContent]] = {}
        for t_row in self._connection.execute(
            "SELECT language, title, summary, body_markdown, slug, source_checksum, seo_json"
            " FROM translations WHERE article_id = ? ORDER BY language",
            (article_id,),
        ):
            translations[Language(t_row[0])] = Translation[ArticleContent](
                content=ArticleContent(
                    title=t_row[1],
                    summary=t_row[2],
                    body_markdown=t_row[3],
                    slug=t_row[4],
                    seo=_seo_from_json(t_row[6]),
                ),
                source_checksum=t_row[5],
            )
        return Article(
            id=row[0],
            status=ContentStatus(row[1]),
            created_at=datetime.fromisoformat(row[2]),
            updated_at=datetime.fromisoformat(row[3]),
            source=ArticleContent(
                title=row[4],
                summary=row[5],
                body_markdown=row[6],
                slug=row[7],
                seo=_seo_from_json(row[17]),
            ),
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
                "  publish_at, deleted_at, body_markdown, unpublish_at, seo_json)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(id) DO UPDATE SET"
                " status = excluded.status, updated_at = excluded.updated_at,"
                " title = excluded.title, description = excluded.description,"
                " slug = excluded.slug, publish_at = excluded.publish_at,"
                " body_markdown = excluded.body_markdown,"
                " unpublish_at = excluded.unpublish_at,"
                " deleted_at = excluded.deleted_at, seo_json = excluded.seo_json",
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
                    page.source.body_markdown,
                    page.unpublish_at.isoformat() if page.unpublish_at else None,
                    json.dumps(page.source.seo.model_dump(), sort_keys=True),
                ),
            )
            connection.execute("DELETE FROM page_translations WHERE page_id = ?", (page.id,))
            connection.executemany(
                "INSERT INTO page_translations"
                " (page_id, language, title, description, slug, source_checksum,"
                "  body_markdown, seo_json)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        page.id,
                        language.value,
                        translation.content.title,
                        translation.content.description,
                        translation.content.slug,
                        translation.source_checksum,
                        translation.content.body_markdown,
                        json.dumps(translation.content.seo.model_dump(), sort_keys=True),
                    )
                    for language, translation in sorted(
                        page.translations.items(), key=lambda item: item[0].value
                    )
                ],
            )
            connection.execute("DELETE FROM sections WHERE page_id = ?", (page.id,))
            for position, section in enumerate(page.sections):
                connection.execute(
                    "INSERT INTO sections (page_id, key, position, kind, fields_json, media_json,"
                    "  items_json, hidden)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
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
                connection.executemany(
                    "INSERT INTO section_translations"
                    " (page_id, section_key, language, fields_json, media_json, source_checksum,"
                    "  items_json)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)",
                    [
                        (
                            page.id,
                            section.key,
                            language.value,
                            json.dumps(translation.content.fields, sort_keys=True),
                            json.dumps(translation.content.media),
                            translation.source_checksum,
                            json.dumps(translation.content.items, sort_keys=True),
                        )
                        for language, translation in sorted(
                            section.translations.items(), key=lambda item: item[0].value
                        )
                    ],
                )

    def _load_sections(self, page_id: str) -> list[Section]:
        sections: list[Section] = []
        for row in self._connection.execute(
            "SELECT key, kind, fields_json, media_json, items_json, hidden FROM sections"
            " WHERE page_id = ? ORDER BY position",
            (page_id,),
        ):
            translations: dict[Language, Translation[SectionContent]] = {}
            for t_row in self._connection.execute(
                "SELECT language, fields_json, media_json, source_checksum, items_json"
                " FROM section_translations WHERE page_id = ? AND section_key = ?"
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
        rows = self._rows(
            "SELECT DISTINCT a.id, a.title FROM articles a"
            " LEFT JOIN translations t ON t.article_id = a.id"
            " WHERE a.deleted_at IS NULL AND ("
            "  LOWER(a.id) LIKE ? ESCAPE '!' OR LOWER(a.title) LIKE ? ESCAPE '!'"
            "  OR LOWER(a.summary) LIKE ? ESCAPE '!'"
            "  OR LOWER(a.body_markdown) LIKE ? ESCAPE '!'"
            "  OR LOWER(t.title) LIKE ? ESCAPE '!' OR LOWER(t.summary) LIKE ? ESCAPE '!'"
            "  OR LOWER(t.body_markdown) LIKE ? ESCAPE '!')"
            " ORDER BY a.id",
            (pattern,) * 7,
        )
        hits.extend(SearchHit("article", row[0], row[1]) for row in rows[:limit])
        rows = self._rows(
            "SELECT DISTINCT p.id, p.title FROM pages p"
            " LEFT JOIN page_translations t ON t.page_id = p.id"
            " WHERE p.deleted_at IS NULL AND ("
            "  LOWER(p.id) LIKE ? ESCAPE '!' OR LOWER(p.title) LIKE ? ESCAPE '!'"
            "  OR LOWER(p.description) LIKE ? ESCAPE '!'"
            "  OR LOWER(p.body_markdown) LIKE ? ESCAPE '!'"
            "  OR LOWER(t.title) LIKE ? ESCAPE '!' OR LOWER(t.description) LIKE ? ESCAPE '!'"
            "  OR LOWER(t.body_markdown) LIKE ? ESCAPE '!')"
            " ORDER BY p.id",
            (pattern,) * 7,
        )
        hits.extend(SearchHit("page", row[0], row[1]) for row in rows[:limit])
        rows = self._rows(
            "SELECT DISTINCT s.page_id, s.key, s.kind FROM sections s"
            " JOIN pages p ON p.id = s.page_id AND p.deleted_at IS NULL"
            " LEFT JOIN section_translations t"
            "  ON t.page_id = s.page_id AND t.section_key = s.key"
            " WHERE LOWER(s.key) LIKE ? ESCAPE '!'"
            "  OR LOWER(s.fields_json) LIKE ? ESCAPE '!'"
            "  OR LOWER(s.items_json) LIKE ? ESCAPE '!'"
            "  OR LOWER(t.fields_json) LIKE ? ESCAPE '!'"
            "  OR LOWER(t.items_json) LIKE ? ESCAPE '!'"
            " ORDER BY s.page_id, s.key",
            (pattern,) * 5,
        )
        hits.extend(
            SearchHit("section", f"{row[0]}/{row[1]}", row[1], row[2]) for row in rows[:limit]
        )
        rows = self._rows(
            "SELECT DISTINCT m.id, m.path FROM media_assets m"
            " LEFT JOIN media_alt_texts alt ON alt.media_id = m.id"
            " WHERE LOWER(m.id) LIKE ? ESCAPE '!' OR LOWER(m.path) LIKE ? ESCAPE '!'"
            "  OR LOWER(alt.alt) LIKE ? ESCAPE '!'"
            " ORDER BY m.id",
            (pattern,) * 3,
        )
        hits.extend(SearchHit("media", row[0], row[1]) for row in rows[:limit])
        return hits

    def _rows(self, sql: str, params: tuple[str, ...]) -> list[tuple[str, ...]]:
        return list(self._connection.execute(sql, params))

    def load_page(self, page_id: str) -> Page | None:
        row = self._connection.execute(
            "SELECT id, status, created_at, updated_at, title, description, slug, publish_at,"
            " deleted_at, body_markdown, unpublish_at, seo_json"
            " FROM pages WHERE id = ?",
            (page_id,),
        ).fetchone()
        if row is None:
            return None
        translations: dict[Language, Translation[PageContent]] = {}
        for t_row in self._connection.execute(
            "SELECT language, title, description, slug, source_checksum, body_markdown, seo_json"
            " FROM page_translations WHERE page_id = ? ORDER BY language",
            (page_id,),
        ):
            translations[Language(t_row[0])] = Translation[PageContent](
                content=PageContent(
                    title=t_row[1],
                    description=t_row[2],
                    slug=t_row[3],
                    body_markdown=t_row[5],
                    seo=_seo_from_json(t_row[6]),
                ),
                source_checksum=t_row[4],
            )
        return Page(
            id=row[0],
            status=ContentStatus(row[1]),
            created_at=datetime.fromisoformat(row[2]),
            updated_at=datetime.fromisoformat(row[3]),
            source=PageContent(
                title=row[4],
                description=row[5],
                slug=row[6],
                body_markdown=row[9],
                seo=_seo_from_json(row[11]),
            ),
            translations=translations,
            sections=self._load_sections(page_id),
            publish_at=datetime.fromisoformat(row[7]) if row[7] else None,
            unpublish_at=datetime.fromisoformat(row[10]) if row[10] else None,
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
                "INSERT INTO media_assets (id, path, mime_type, width, height,"
                " collection, content_hash, crop, focal)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(id) DO UPDATE SET"
                " path = excluded.path, mime_type = excluded.mime_type,"
                " width = excluded.width, height = excluded.height,"
                " collection = excluded.collection, content_hash = excluded.content_hash,"
                " crop = excluded.crop, focal = excluded.focal",
                (
                    asset.id,
                    asset.path,
                    asset.mime_type,
                    asset.width,
                    asset.height,
                    asset.collection,
                    asset.content_hash,
                    asset.crop,
                    asset.focal,
                ),
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
            "SELECT id, path, mime_type, width, height, collection, content_hash, crop, focal"
            " FROM media_assets WHERE id = ?",
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
                "INSERT INTO users"
                " (username, password_hash, role, created_at, language, email,"
                " totp_secret, totp_step)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(username) DO UPDATE SET"
                " password_hash = excluded.password_hash, role = excluded.role,"
                " language = excluded.language, email = excluded.email,"
                " totp_secret = excluded.totp_secret, totp_step = excluded.totp_step",
                (
                    user.username,
                    user.password_hash,
                    user.role.value,
                    user.created_at.isoformat(),
                    user.language.value if user.language else None,
                    user.email,
                    user.totp_secret,
                    user.totp_step,
                ),
            )

    def load_user(self, username: str) -> User | None:
        row = self._connection.execute(
            "SELECT username, password_hash, role, created_at, language, email,"
            " totp_secret, totp_step"
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
            email=row[5],
            totp_secret=row[6],
            totp_step=row[7],
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

    def record_activity(self, record: ActivityRecord) -> None:
        with self._connection as connection:
            connection.execute(
                "INSERT INTO activity (at, actor, action, subject_kind, subject_id, detail)"
                " VALUES (?, ?, ?, ?, ?, ?)",
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
            clauses.append("actor = ?")
            params.append(actor)
        if since:
            clauses.append("at >= ?")
            params.append(since.isoformat())
        if until:
            clauses.append("at < ?")
            params.append(until.isoformat())
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._connection.execute(
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
        with self._connection as connection:
            cursor = connection.execute("DELETE FROM activity WHERE at < ?", (before.isoformat(),))
        return cursor.rowcount

    # Form submissions (ADR-0039): optional persistence, opaque values.

    def save_form_submission(self, submission: FormSubmission) -> None:
        with self._connection as connection:
            connection.execute(
                "INSERT INTO form_submissions"
                " (id, received_at, page_id, section_key, language, values_json)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    submission.id,
                    submission.received_at.isoformat(),
                    submission.page_id,
                    submission.section_key,
                    submission.language,
                    json.dumps(submission.values, ensure_ascii=False, sort_keys=True),
                ),
            )

    def list_form_submissions(
        self,
        limit: int = 100,
        page_id: str | None = None,
        section_key: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[FormSubmission]:
        clauses = []
        params: list[str] = []
        if page_id:
            clauses.append("page_id = ?")
            params.append(page_id)
        if section_key:
            clauses.append("section_key = ?")
            params.append(section_key)
        if since:
            clauses.append("received_at >= ?")
            params.append(since.isoformat())
        if until:
            clauses.append("received_at < ?")
            params.append(until.isoformat())
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._connection.execute(
            # Literal fragments only; values are bound parameters.
            "SELECT id, received_at, page_id, section_key, language, values_json"
            f" FROM form_submissions{where}"  # nosec B608
            " ORDER BY received_at DESC LIMIT ?",
            (*params, limit),
        ).fetchall()
        return [
            FormSubmission(
                id=row[0],
                received_at=datetime.fromisoformat(row[1]),
                page_id=row[2],
                section_key=row[3],
                language=row[4],
                values=json.loads(row[5]),
            )
            for row in rows
        ]

    def delete_form_submission(self, submission_id: str) -> bool:
        with self._connection as connection:
            cursor = connection.execute(
                "DELETE FROM form_submissions WHERE id = ?", (submission_id,)
            )
        return cursor.rowcount > 0

    def prune_form_submissions(self, before: datetime) -> int:
        with self._connection as connection:
            cursor = connection.execute(
                "DELETE FROM form_submissions WHERE received_at < ?", (before.isoformat(),)
            )
        return cursor.rowcount

    def delete_expired_sessions(self, now: datetime) -> int:
        with self._connection as connection:
            cursor = connection.execute(
                "DELETE FROM admin_sessions WHERE expires_at <= ?", (now.isoformat(),)
            )
        return cursor.rowcount

    def delete_sessions_for(self, username: str) -> int:
        with self._connection as connection:
            cursor = connection.execute(
                "DELETE FROM admin_sessions WHERE username = ?", (username,)
            )
        return cursor.rowcount

    def save_password_reset(self, reset: PasswordReset) -> None:
        with self._connection as connection:
            connection.execute(
                "INSERT INTO password_resets (token_hash, username, expires_at)"
                " VALUES (?, ?, ?)"
                " ON CONFLICT(token_hash) DO UPDATE SET"
                " username = excluded.username, expires_at = excluded.expires_at",
                (reset.token_hash, reset.username, reset.expires_at.isoformat()),
            )

    def pop_password_reset(self, token_hash: str, now: datetime) -> PasswordReset | None:
        row = self._connection.execute(
            "SELECT token_hash, username, expires_at FROM password_resets WHERE token_hash = ?",
            (token_hash,),
        ).fetchone()
        if row is None:
            return None
        with self._connection as connection:
            connection.execute("DELETE FROM password_resets WHERE token_hash = ?", (token_hash,))
        expires_at = datetime.fromisoformat(row[2])
        if expires_at <= now:
            return None
        return PasswordReset(token_hash=row[0], username=row[1], expires_at=expires_at)

    def delete_password_resets_for(self, username: str) -> int:
        with self._connection as connection:
            cursor = connection.execute(
                "DELETE FROM password_resets WHERE username = ?", (username,)
            )
        return cursor.rowcount
