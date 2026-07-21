"""PostgreSQL backend (production target).

Driver: psycopg 3 — an optional dependency (`pip install cms-core[postgres]`).
Applies the same shared migration history as SQLite, tracked in a
``schema_migrations`` table. All statements are parameterized; each write is
one transaction.
"""

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any

from cms_core.accounts import AdminSession, PasswordReset, Role, User
from cms_core.languages import Language
from cms_core.media import MediaAsset
from cms_core.menus import MenuItem
from cms_core.models import Article, ArticleContent
from cms_core.pages import Page, PageContent, Section, SectionContent
from cms_core.states import ContentStatus
from cms_core.storage.base import StorageBackend
from cms_core.storage.migrations import MIGRATIONS
from cms_core.translatable import Translation

if TYPE_CHECKING:
    import psycopg


def _connect(dsn: str) -> "psycopg.Connection[Any]":
    try:
        import psycopg
    except ImportError as error:  # pragma: no cover - exercised without the extra
        raise ImportError(
            "the PostgreSQL backend needs the optional dependency: pip install 'cms-core[postgres]'"
        ) from error
    return psycopg.connect(dsn)


class PostgresBackend(StorageBackend):
    def __init__(self, dsn: str) -> None:
        self._connection = _connect(dsn)
        self.migrate()

    def schema_version(self) -> int:
        with self._connection.transaction():
            self._connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)"
            )
        row = self._connection.execute(
            "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
        ).fetchone()
        return int(row[0]) if row else 0

    def migrate(self) -> int:
        current = self.schema_version()
        for number, script in enumerate(MIGRATIONS[current:], start=current + 1):
            with self._connection.transaction():
                self._connection.execute(script)
                self._connection.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s)", (number,)
                )
        return self.schema_version()

    def close(self) -> None:
        self._connection.close()

    # Articles

    def save_article(self, article: Article) -> None:
        with self._connection.transaction():
            self._connection.execute(
                "INSERT INTO articles"
                " (id, status, created_at, updated_at, title, summary, body_markdown, slug,"
                "  category, tags_json, cover, publish_at, deleted_at, featured, author,"
                "  fields_json)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                " ON CONFLICT (id) DO UPDATE SET"
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
            self._connection.execute(
                "DELETE FROM translations WHERE article_id = %s", (article.id,)
            )
            for language, translation in sorted(
                article.translations.items(), key=lambda item: item[0].value
            ):
                self._connection.execute(
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
        row = self._connection.execute(
            "SELECT id, status, created_at, updated_at, title, summary, body_markdown, slug,"
            " category, tags_json, cover, publish_at, deleted_at, featured, author, fields_json"
            " FROM articles WHERE id = %s",
            (article_id,),
        ).fetchone()
        if row is None:
            return None
        translations: dict[Language, Translation[ArticleContent]] = {}
        for t_row in self._connection.execute(
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
            deleted_at=datetime.fromisoformat(row[12]) if row[12] else None,
            featured=bool(row[13]),
            author=row[14],
            fields=json.loads(row[15]) if row[15] else {},
        )

    def delete_article(self, article_id: str) -> bool:
        with self._connection.transaction():
            cursor = self._connection.execute("DELETE FROM articles WHERE id = %s", (article_id,))
        return cursor.rowcount > 0

    def list_article_ids(self) -> list[str]:
        rows = self._connection.execute("SELECT id FROM articles ORDER BY id").fetchall()
        return [str(row[0]) for row in rows]

    # Pages

    def save_page(self, page: Page) -> None:
        with self._connection.transaction():
            self._connection.execute(
                "INSERT INTO pages"
                " (id, status, created_at, updated_at, title, description, slug,"
                "  publish_at, deleted_at, body_markdown)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                " ON CONFLICT (id) DO UPDATE SET"
                " status = excluded.status, updated_at = excluded.updated_at,"
                " title = excluded.title, description = excluded.description,"
                " slug = excluded.slug, publish_at = excluded.publish_at,"
                " deleted_at = excluded.deleted_at,"
                " body_markdown = excluded.body_markdown",
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
                ),
            )
            self._connection.execute("DELETE FROM page_translations WHERE page_id = %s", (page.id,))
            for language, translation in sorted(
                page.translations.items(), key=lambda item: item[0].value
            ):
                self._connection.execute(
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
            self._connection.execute("DELETE FROM sections WHERE page_id = %s", (page.id,))
            for position, section in enumerate(page.sections):
                self._connection.execute(
                    "INSERT INTO sections (page_id, key, position, kind, fields_json, media_json,"
                    "  items_json)"
                    " VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (
                        page.id,
                        section.key,
                        position,
                        section.kind,
                        json.dumps(section.source.fields, sort_keys=True),
                        json.dumps(section.source.media),
                        json.dumps(section.source.items, sort_keys=True),
                    ),
                )
                for section_language, section_translation in sorted(
                    section.translations.items(), key=lambda item: item[0].value
                ):
                    self._connection.execute(
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

    def _load_sections(self, page_id: str) -> list[Section]:
        sections: list[Section] = []
        for row in self._connection.execute(
            "SELECT key, kind, fields_json, media_json, items_json FROM sections"
            " WHERE page_id = %s ORDER BY position",
            (page_id,),
        ).fetchall():
            translations: dict[Language, Translation[SectionContent]] = {}
            for t_row in self._connection.execute(
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
                    source=SectionContent(
                        fields=json.loads(row[2]),
                        media=json.loads(row[3]),
                        items=json.loads(row[4]),
                    ),
                    translations=translations,
                )
            )
        return sections

    def load_page(self, page_id: str) -> Page | None:
        row = self._connection.execute(
            "SELECT id, status, created_at, updated_at, title, description, slug, publish_at,"
            " deleted_at, body_markdown"
            " FROM pages WHERE id = %s",
            (page_id,),
        ).fetchone()
        if row is None:
            return None
        translations: dict[Language, Translation[PageContent]] = {}
        for t_row in self._connection.execute(
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
            deleted_at=datetime.fromisoformat(row[8]) if row[8] else None,
        )

    def delete_page(self, page_id: str) -> bool:
        with self._connection.transaction():
            cursor = self._connection.execute("DELETE FROM pages WHERE id = %s", (page_id,))
        return cursor.rowcount > 0

    def list_page_ids(self) -> list[str]:
        rows = self._connection.execute("SELECT id FROM pages ORDER BY id").fetchall()
        return [str(row[0]) for row in rows]

    # Media

    def save_media_asset(self, asset: MediaAsset) -> None:
        with self._connection.transaction():
            self._connection.execute(
                "INSERT INTO media_assets (id, path, mime_type, width, height)"
                " VALUES (%s, %s, %s, %s, %s)"
                " ON CONFLICT (id) DO UPDATE SET"
                " path = excluded.path, mime_type = excluded.mime_type,"
                " width = excluded.width, height = excluded.height",
                (asset.id, asset.path, asset.mime_type, asset.width, asset.height),
            )
            self._connection.execute("DELETE FROM media_alt_texts WHERE media_id = %s", (asset.id,))
            for language, alt in sorted(asset.alt.items(), key=lambda item: item[0].value):
                self._connection.execute(
                    "INSERT INTO media_alt_texts (media_id, language, alt) VALUES (%s, %s, %s)",
                    (asset.id, language.value, alt),
                )

    def load_media_asset(self, asset_id: str) -> MediaAsset | None:
        row = self._connection.execute(
            "SELECT id, path, mime_type, width, height FROM media_assets WHERE id = %s",
            (asset_id,),
        ).fetchone()
        if row is None:
            return None
        alt = {
            Language(alt_row[0]): str(alt_row[1])
            for alt_row in self._connection.execute(
                "SELECT language, alt FROM media_alt_texts WHERE media_id = %s ORDER BY language",
                (asset_id,),
            )
        }
        return MediaAsset(
            id=row[0], path=row[1], mime_type=row[2], width=row[3], height=row[4], alt=alt
        )

    def delete_media_asset(self, asset_id: str) -> bool:
        with self._connection.transaction():
            cursor = self._connection.execute("DELETE FROM media_assets WHERE id = %s", (asset_id,))
        return cursor.rowcount > 0

    def list_media_ids(self) -> list[str]:
        rows = self._connection.execute("SELECT id FROM media_assets ORDER BY id").fetchall()
        return [str(row[0]) for row in rows]

    # Menu items (M6)

    def save_menu_item(self, item: MenuItem) -> None:
        with self._connection.transaction():
            self._connection.execute(
                "INSERT INTO menu_items (id, url, position, labels_json)"
                " VALUES (%s, %s, %s, %s)"
                " ON CONFLICT (id) DO UPDATE SET url = excluded.url,"
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
        with self._connection.transaction():
            cursor = self._connection.execute("DELETE FROM menu_items WHERE id = %s", (item_id,))
        return cursor.rowcount > 0

    # Editorial notes (M5)

    def add_note(
        self, entity_type: str, entity_id: str, author: str, body: str, created_at: datetime
    ) -> int:
        with self._connection.transaction():
            row = self._connection.execute(
                "SELECT COALESCE(MAX(seq), 0) FROM notes WHERE entity_type = %s AND entity_id = %s",
                (entity_type, entity_id),
            ).fetchone()
            number = int(row[0]) + 1 if row else 1
            self._connection.execute(
                "INSERT INTO notes (entity_type, entity_id, seq, created_at, author, body)"
                " VALUES (%s, %s, %s, %s, %s, %s)",
                (entity_type, entity_id, number, created_at.isoformat(), author, body),
            )
        return number

    def list_notes(self, entity_type: str, entity_id: str) -> list[tuple[int, datetime, str, str]]:
        rows = self._connection.execute(
            "SELECT seq, created_at, author, body FROM notes"
            " WHERE entity_type = %s AND entity_id = %s ORDER BY seq DESC",
            (entity_type, entity_id),
        ).fetchall()
        return [(int(r[0]), datetime.fromisoformat(r[1]), str(r[2]), str(r[3])) for r in rows]

    def delete_note(self, entity_type: str, entity_id: str, seq: int) -> bool:
        with self._connection.transaction():
            cursor = self._connection.execute(
                "DELETE FROM notes WHERE entity_type = %s AND entity_id = %s AND seq = %s",
                (entity_type, entity_id, seq),
            )
        return cursor.rowcount > 0

    # Revisions (ADR-0025)

    def save_revision(
        self, entity_type: str, entity_id: str, author: str, payload_json: str, created_at: datetime
    ) -> int:
        with self._connection.transaction():
            row = self._connection.execute(
                "SELECT COALESCE(MAX(revision), 0) FROM revisions"
                " WHERE entity_type = %s AND entity_id = %s",
                (entity_type, entity_id),
            ).fetchone()
            number = int(row[0]) + 1 if row else 1
            self._connection.execute(
                "INSERT INTO revisions"
                " (entity_type, entity_id, revision, created_at, author, payload_json)"
                " VALUES (%s, %s, %s, %s, %s, %s)",
                (entity_type, entity_id, number, created_at.isoformat(), author, payload_json),
            )
            self._connection.execute(
                "DELETE FROM revisions WHERE entity_type = %s AND entity_id = %s"
                " AND revision <= %s",
                (entity_type, entity_id, number - self.REVISION_LIMIT),
            )
        return number

    def list_revisions(self, entity_type: str, entity_id: str) -> list[tuple[int, datetime, str]]:
        rows = self._connection.execute(
            "SELECT revision, created_at, author FROM revisions"
            " WHERE entity_type = %s AND entity_id = %s ORDER BY revision DESC",
            (entity_type, entity_id),
        ).fetchall()
        return [(int(r[0]), datetime.fromisoformat(r[1]), str(r[2])) for r in rows]

    def load_revision(self, entity_type: str, entity_id: str, revision: int) -> str | None:
        row = self._connection.execute(
            "SELECT payload_json FROM revisions"
            " WHERE entity_type = %s AND entity_id = %s AND revision = %s",
            (entity_type, entity_id, revision),
        ).fetchone()
        return str(row[0]) if row else None

    # Admin accounts

    def save_user(self, user: User) -> None:
        with self._connection.transaction():
            self._connection.execute(
                "INSERT INTO users"
                " (username, password_hash, role, created_at, language, email,"
                " totp_secret, totp_step)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                " ON CONFLICT (username) DO UPDATE SET"
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
            " FROM users WHERE username = %s",
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
        with self._connection.transaction():
            cursor = self._connection.execute("DELETE FROM users WHERE username = %s", (username,))
        return cursor.rowcount > 0

    def list_usernames(self) -> list[str]:
        rows = self._connection.execute("SELECT username FROM users ORDER BY username").fetchall()
        return [str(row[0]) for row in rows]

    # Admin sessions

    def save_session(self, session: AdminSession) -> None:
        with self._connection.transaction():
            self._connection.execute(
                "INSERT INTO admin_sessions (token_hash, username, csrf_token, expires_at)"
                " VALUES (%s, %s, %s, %s)"
                " ON CONFLICT (token_hash) DO UPDATE SET expires_at = excluded.expires_at",
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
            " FROM admin_sessions WHERE token_hash = %s",
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
        with self._connection.transaction():
            cursor = self._connection.execute(
                "DELETE FROM admin_sessions WHERE token_hash = %s", (token_hash,)
            )
        return cursor.rowcount > 0

    def delete_expired_sessions(self, now: datetime) -> int:
        with self._connection.transaction():
            cursor = self._connection.execute(
                "DELETE FROM admin_sessions WHERE expires_at <= %s", (now.isoformat(),)
            )
        return cursor.rowcount

    def delete_sessions_for(self, username: str) -> int:
        with self._connection.transaction():
            cursor = self._connection.execute(
                "DELETE FROM admin_sessions WHERE username = %s", (username,)
            )
        return cursor.rowcount

    def save_password_reset(self, reset: PasswordReset) -> None:
        with self._connection.transaction():
            self._connection.execute(
                "INSERT INTO password_resets (token_hash, username, expires_at)"
                " VALUES (%s, %s, %s)"
                " ON CONFLICT (token_hash) DO UPDATE SET"
                " username = excluded.username, expires_at = excluded.expires_at",
                (reset.token_hash, reset.username, reset.expires_at.isoformat()),
            )

    def pop_password_reset(self, token_hash: str, now: datetime) -> PasswordReset | None:
        row = self._connection.execute(
            "SELECT token_hash, username, expires_at FROM password_resets WHERE token_hash = %s",
            (token_hash,),
        ).fetchone()
        if row is None:
            return None
        with self._connection.transaction():
            self._connection.execute(
                "DELETE FROM password_resets WHERE token_hash = %s", (token_hash,)
            )
        expires_at = datetime.fromisoformat(row[2])
        if expires_at <= now:
            return None
        return PasswordReset(token_hash=row[0], username=row[1], expires_at=expires_at)

    def delete_password_resets_for(self, username: str) -> int:
        with self._connection.transaction():
            cursor = self._connection.execute(
                "DELETE FROM password_resets WHERE username = %s", (username,)
            )
        return cursor.rowcount
