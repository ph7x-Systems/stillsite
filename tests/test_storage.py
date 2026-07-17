"""Backend round-trips and migration behavior (SQLite backend via the factory)."""

from pathlib import Path

from cms_core import (
    ArticleContent,
    ContentStatus,
    Language,
    MediaAsset,
    PageContent,
    Section,
    SectionContent,
    new_article,
    new_page,
)
from cms_core.storage import MIGRATIONS, StorageBackend, create_storage


def open_backend(tmp_path: Path) -> StorageBackend:
    return create_storage(f"sqlite:///{tmp_path / 'cms.sqlite3'}")


def test_connect_applies_all_migrations(tmp_path: Path) -> None:
    backend = open_backend(tmp_path)
    assert backend.schema_version() == len(MIGRATIONS)
    # A second migrate call is a no-op, not an error.
    assert backend.migrate() == len(MIGRATIONS)


def test_article_round_trip(tmp_path: Path) -> None:
    backend = open_backend(tmp_path)
    article = new_article("first-post", ArticleContent(title="First", body_markdown="Hello."))
    article.set_translation(Language.PT_PT, ArticleContent(title="Primeiro", body_markdown="Olá."))
    article.status = ContentStatus.REVIEW

    backend.save_article(article)
    assert backend.load_article("first-post") == article


def test_save_is_an_upsert(tmp_path: Path) -> None:
    backend = open_backend(tmp_path)
    article = new_article("first-post", ArticleContent(title="First"))
    backend.save_article(article)

    article.source = ArticleContent(title="First, revised")
    article.set_translation(Language.ES, ArticleContent(title="Primero"))
    backend.save_article(article)

    loaded = backend.load_article("first-post")
    assert loaded is not None
    assert loaded.source.title == "First, revised"
    assert set(loaded.translations) == {Language.ES}


def test_delete_cascades_to_translations(tmp_path: Path) -> None:
    backend = open_backend(tmp_path)
    article = new_article("first-post", ArticleContent(title="First"))
    article.set_translation(Language.FR, ArticleContent(title="Premier"))
    backend.save_article(article)

    assert backend.delete_article("first-post")
    assert not backend.delete_article("first-post")
    assert backend.list_article_ids() == []


def test_missing_article_loads_as_none(tmp_path: Path) -> None:
    backend = open_backend(tmp_path)
    assert backend.load_article("nope") is None


def test_page_round_trip_preserves_section_order(tmp_path: Path) -> None:
    backend = open_backend(tmp_path)
    page = new_page("home", PageContent(title="Home", slug="home"))
    for key in ("hero", "features", "contact"):
        page.sections.append(
            Section(key=key, kind=key, source=SectionContent(fields={"heading": key.title()}))
        )
    page.sections[0].set_translation(
        Language.PT_PT, SectionContent(fields={"heading": "Bem-vindo"})
    )
    page.set_translation(Language.PT_PT, PageContent(title="Início", slug="inicio"))
    backend.save_page(page)

    loaded = backend.load_page("home")
    assert loaded is not None
    assert loaded == page
    assert [section.key for section in loaded.sections] == ["hero", "features", "contact"]


def test_page_delete_removes_page(tmp_path: Path) -> None:
    backend = open_backend(tmp_path)
    page = new_page("home", PageContent(title="Home", slug="home"))
    hero = Section(key="hero", kind="hero", source=SectionContent(fields={"heading": "Welcome"}))
    hero.set_translation(Language.FR, SectionContent(fields={"heading": "Bienvenue"}))
    page.sections.append(hero)
    backend.save_page(page)

    assert backend.delete_page("home")
    assert backend.list_page_ids() == []
    reloaded = backend.load_page("home")
    assert reloaded is None


def test_media_round_trip_and_delete(tmp_path: Path) -> None:
    backend = open_backend(tmp_path)
    asset = MediaAsset(
        id="logo",
        path="images/logo.svg",
        mime_type="image/svg+xml",
        width=64,
        height=64,
        alt={Language.EN: "Company logo", Language.PT_PT: "Logótipo da empresa"},
    )
    backend.save_media_asset(asset)
    assert backend.load_media_asset("logo") == asset
    assert backend.list_media_ids() == ["logo"]

    assert backend.delete_media_asset("logo")
    assert backend.load_media_asset("logo") is None


def test_load_all_collections(tmp_path: Path) -> None:
    backend = open_backend(tmp_path)
    backend.save_article(new_article("b-post", ArticleContent(title="B")))
    backend.save_article(new_article("a-post", ArticleContent(title="A")))
    backend.save_page(new_page("home", PageContent(title="Home", slug="home")))

    assert [article.id for article in backend.load_all_articles()] == ["a-post", "b-post"]
    assert [page.id for page in backend.load_all_pages()] == ["home"]
    assert backend.load_all_media_assets() == []


def test_backend_is_a_context_manager(tmp_path: Path) -> None:
    with open_backend(tmp_path) as backend:
        backend.save_article(new_article("post", ArticleContent(title="Post")))
