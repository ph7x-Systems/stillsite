"""Backend-agnostic storage interface.

Every storage engine (SQLite today; PostgreSQL and SQL Server planned)
implements this one interface, so nothing above the storage layer knows which
database is in use. The database is always a working store — the portable
source of truth is the JSON/Markdown export (:mod:`cms_core.export`).
"""

from abc import ABC, abstractmethod
from datetime import datetime
from types import TracebackType

from cms_core.accounts import AdminSession, User
from cms_core.media import MediaAsset
from cms_core.menus import MenuItem
from cms_core.models import Article
from cms_core.pages import Page


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
