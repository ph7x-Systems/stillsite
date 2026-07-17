"""Backend-agnostic storage interface.

Every storage engine (SQLite today; PostgreSQL and SQL Server planned)
implements this one interface, so nothing above the storage layer knows which
database is in use. The database is always a working store — the portable
source of truth is the JSON/Markdown export (:mod:`cms_core.export`).
"""

from abc import ABC, abstractmethod
from types import TracebackType

from cms_core.media import MediaAsset
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
