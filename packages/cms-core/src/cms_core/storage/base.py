"""Backend-agnostic storage interface.

Every storage engine (SQLite today; PostgreSQL and SQL Server planned)
implements this one interface, so nothing above the storage layer knows which
database is in use. The database is always a working store — the portable
source of truth is the JSON/Markdown export (:mod:`cms_core.export`).
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime
from types import TracebackType

from cms_core.accounts import AdminSession, PasswordReset, User
from cms_core.activity import ActivityRecord
from cms_core.forms import FormSubmission
from cms_core.media import MediaAsset
from cms_core.menus import MenuItem
from cms_core.models import Article
from cms_core.pages import Page
from cms_core.preview_links import PreviewLink
from cms_core.search import SearchHit


class StorageBackend(ABC):
    @abstractmethod
    def schema_version(self) -> int: ...

    @abstractmethod
    def migrate(self) -> int: ...

    @abstractmethod
    def close(self) -> None: ...

    # Articles

    @abstractmethod
    def save_article(self, article: Article) -> None: ...

    @abstractmethod
    def load_article(self, article_id: str) -> Article | None: ...

    @abstractmethod
    def delete_article(self, article_id: str) -> bool: ...

    @abstractmethod
    def list_article_ids(self) -> list[str]: ...

    @abstractmethod
    def record_activity(self, record: ActivityRecord) -> None: ...

    @abstractmethod
    def list_activity(
        self,
        limit: int = 100,
        actor: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[ActivityRecord]: ...

    @abstractmethod
    def prune_activity(self, before: datetime) -> int: ...

    @abstractmethod
    def save_form_submission(self, submission: FormSubmission) -> None: ...

    @abstractmethod
    def list_form_submissions(
        self,
        limit: int = 100,
        page_id: str | None = None,
        section_key: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[FormSubmission]: ...

    @abstractmethod
    def delete_form_submission(self, submission_id: str) -> bool: ...

    @abstractmethod
    def prune_form_submissions(self, before: datetime) -> int: ...

    @abstractmethod
    def save_preview_link(self, link: PreviewLink) -> None: ...

    @abstractmethod
    def load_preview_link(self, link_id: str) -> PreviewLink | None: ...

    @abstractmethod
    def list_preview_links(self, entry_kind: str, entry_id: str) -> list[PreviewLink]: ...

    @abstractmethod
    def revoke_preview_link(self, link_id: str) -> bool: ...

    @abstractmethod
    def get_or_create_secret(self, name: str, factory: Callable[[], str]) -> str: ...

    def search_content(self, needle: str, limit: int = 20) -> list[SearchHit]:
        """Find articles, pages, sections and media whose text contains
        ``needle`` (case-insensitive), at most ``limit`` hits per kind.
        Trashed entries never match. This portable default walks the
        loaded content; the bundled SQL engines override it with LIKE
        queries — third-party backends inherit correctness and may
        override for speed (#129)."""
        lowered = needle.lower()
        if not lowered:
            return []
        hits: list[SearchHit] = []

        def texts_match(*values: str | None) -> bool:
            return any(lowered in value.lower() for value in values if value)

        articles = 0
        for article in self.load_all_articles():
            if article.deleted_at is not None or articles >= limit:
                continue
            contents = [article.source, *(t.content for t in article.translations.values())]
            if texts_match(
                article.id,
                *(c.title for c in contents),
                *(c.summary for c in contents),
                *(c.body_markdown for c in contents),
                *(c.slug or "" for c in contents),
            ):
                hits.append(SearchHit("article", article.id, article.source.title))
                articles += 1
        pages = sections = 0
        for page in self.load_all_pages():
            if page.deleted_at is not None:
                continue
            page_contents = [page.source, *(t.content for t in page.translations.values())]
            if pages < limit and texts_match(
                page.id,
                *(c.title for c in page_contents),
                *(c.description for c in page_contents),
                *(c.body_markdown for c in page_contents),
                *(c.slug for c in page_contents),
            ):
                hits.append(SearchHit("page", page.id, page.source.title))
                pages += 1
            for section in page.sections:
                if sections >= limit:
                    break
                bodies = [section.source, *(t.content for t in section.translations.values())]
                values = [
                    value
                    for body in bodies
                    for value in (
                        *body.fields.values(),
                        *(cell for item in body.items for cell in item.values()),
                    )
                ]
                if texts_match(section.key, *values):
                    hits.append(
                        SearchHit("section", f"{page.id}/{section.key}", section.key, section.kind)
                    )
                    sections += 1
        media = 0
        for asset in self.load_all_media_assets():
            if media >= limit:
                break
            if texts_match(asset.id, asset.path, *(alt for alt in asset.alt.values())):
                hits.append(SearchHit("media", asset.id, asset.path))
                media += 1
        return hits

    def load_all_articles(self) -> list[Article]:
        articles = (self.load_article(article_id) for article_id in self.list_article_ids())
        return [article for article in articles if article is not None]

    # Pages

    @abstractmethod
    def save_page(self, page: Page) -> None: ...

    @abstractmethod
    def load_page(self, page_id: str) -> Page | None: ...

    @abstractmethod
    def delete_page(self, page_id: str) -> bool: ...

    @abstractmethod
    def list_page_ids(self) -> list[str]: ...

    def load_all_pages(self) -> list[Page]:
        pages = (self.load_page(page_id) for page_id in self.list_page_ids())
        return [page for page in pages if page is not None]

    # Media

    @abstractmethod
    def save_media_asset(self, asset: MediaAsset) -> None: ...

    @abstractmethod
    def load_media_asset(self, asset_id: str) -> MediaAsset | None: ...

    @abstractmethod
    def delete_media_asset(self, asset_id: str) -> bool: ...

    @abstractmethod
    def list_media_ids(self) -> list[str]: ...

    def load_all_media_assets(self) -> list[MediaAsset]:
        assets = (self.load_media_asset(asset_id) for asset_id in self.list_media_ids())
        return [asset for asset in assets if asset is not None]

    def has_content(self) -> bool:
        """True when any article, page or media asset exists."""
        return bool(self.list_article_ids() or self.list_page_ids() or self.list_media_ids())

    # Admin accounts (never exported — see cms_core.accounts)

    @abstractmethod
    def save_user(self, user: User) -> None: ...

    @abstractmethod
    def load_user(self, username: str) -> User | None: ...

    @abstractmethod
    def delete_user(self, username: str) -> bool: ...

    @abstractmethod
    def list_usernames(self) -> list[str]: ...

    # Admin sessions

    # Menu items (M6): explicit navigation.

    @abstractmethod
    def save_menu_item(self, item: "MenuItem") -> None: ...

    @abstractmethod
    def load_menu_items(self) -> list["MenuItem"]: ...

    @abstractmethod
    def delete_menu_item(self, item_id: str) -> bool: ...

    # Editorial notes (M5): a comment trail per entity.

    @abstractmethod
    def add_note(
        self, entity_type: str, entity_id: str, author: str, body: str, created_at: datetime
    ) -> int:
        """Append a note; returns its sequence number."""

    @abstractmethod
    def list_notes(self, entity_type: str, entity_id: str) -> list[tuple[int, datetime, str, str]]:
        """(seq, created_at, author, body), newest first."""

    @abstractmethod
    def delete_note(self, entity_type: str, entity_id: str, seq: int) -> bool: ...

    # Revisions (ADR-0025): a bounded per-entity edit history.

    REVISION_LIMIT = 20

    @abstractmethod
    def save_revision(
        self, entity_type: str, entity_id: str, author: str, payload_json: str, created_at: datetime
    ) -> int:
        """Append a revision, prune beyond REVISION_LIMIT; returns its number."""

    @abstractmethod
    def list_revisions(self, entity_type: str, entity_id: str) -> list[tuple[int, datetime, str]]:
        """(revision, created_at, author), newest first."""

    @abstractmethod
    def load_revision(self, entity_type: str, entity_id: str, revision: int) -> str | None: ...

    @abstractmethod
    def save_session(self, session: AdminSession) -> None: ...

    @abstractmethod
    def load_session(self, token_hash: str) -> AdminSession | None: ...

    @abstractmethod
    def delete_session(self, token_hash: str) -> bool: ...

    @abstractmethod
    def delete_expired_sessions(self, now: datetime) -> int: ...

    @abstractmethod
    def delete_sessions_for(self, username: str) -> int:
        """Revoke every session of the account (ADR-0032 reset contract)."""

    # Password resets (ADR-0032)

    @abstractmethod
    def save_password_reset(self, reset: PasswordReset) -> None: ...

    @abstractmethod
    def pop_password_reset(self, token_hash: str, now: datetime) -> PasswordReset | None:
        """Single use: return and delete the row; None when absent or expired."""

    @abstractmethod
    def delete_password_resets_for(self, username: str) -> int: ...

    # Context manager

    def __enter__(self) -> "StorageBackend":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
