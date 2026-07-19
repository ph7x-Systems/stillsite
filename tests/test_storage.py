"""Backend conformance suite (ADR-0004): every engine must pass unchanged.

The `backend` fixture (tests/conftest.py) parameterizes these tests over all
implemented engines — SQLite always, PostgreSQL when a server is available.
"""

from datetime import datetime

from cms_core import (
    AdminSession,
    ArticleContent,
    ContentStatus,
    Language,
    MediaAsset,
    PageContent,
    Role,
    Section,
    SectionContent,
    User,
    new_article,
    new_page,
)
from cms_core.storage import MIGRATIONS, StorageBackend


def test_connect_applies_all_migrations(backend: StorageBackend) -> None:
    assert backend.schema_version() == len(MIGRATIONS)
    # A second migrate call is a no-op, not an error.
    assert backend.migrate() == len(MIGRATIONS)


def test_article_round_trip(backend: StorageBackend) -> None:
    article = new_article("first-post", ArticleContent(title="First", body_markdown="Hello."))
    article.set_translation(Language.PT_PT, ArticleContent(title="Primeiro", body_markdown="Olá."))
    article.status = ContentStatus.REVIEW
    article.category = "field-notes"
    article.tags = ("craft", "maps")

    backend.save_article(article)
    assert backend.load_article("first-post") == article


def test_save_is_an_upsert(backend: StorageBackend) -> None:
    article = new_article("first-post", ArticleContent(title="First"))
    backend.save_article(article)

    article.source = ArticleContent(title="First, revised")
    article.set_translation(Language.ES, ArticleContent(title="Primero"))
    backend.save_article(article)

    loaded = backend.load_article("first-post")
    assert loaded is not None
    assert loaded.source.title == "First, revised"
    assert set(loaded.translations) == {Language.ES}


def test_delete_cascades_to_translations(backend: StorageBackend) -> None:
    article = new_article("first-post", ArticleContent(title="First"))
    article.set_translation(Language.FR, ArticleContent(title="Premier"))
    backend.save_article(article)

    assert backend.delete_article("first-post")
    assert not backend.delete_article("first-post")
    assert backend.list_article_ids() == []


def test_missing_article_loads_as_none(backend: StorageBackend) -> None:
    assert backend.load_article("nope") is None


def test_page_round_trip_preserves_section_order(backend: StorageBackend) -> None:
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


def test_page_delete_removes_page(backend: StorageBackend) -> None:
    page = new_page("home", PageContent(title="Home", slug="home"))
    hero = Section(key="hero", kind="hero", source=SectionContent(fields={"heading": "Welcome"}))
    hero.set_translation(Language.FR, SectionContent(fields={"heading": "Bienvenue"}))
    page.sections.append(hero)
    backend.save_page(page)

    assert backend.delete_page("home")
    assert backend.list_page_ids() == []
    assert backend.load_page("home") is None


def test_media_round_trip_and_delete(backend: StorageBackend) -> None:
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


def test_has_content_reflects_all_collections(backend: StorageBackend) -> None:
    assert not backend.has_content()
    backend.save_page(new_page("home", PageContent(title="Home", slug="home")))
    assert backend.has_content()
    backend.delete_page("home")
    assert not backend.has_content()


def test_load_all_collections(backend: StorageBackend) -> None:
    backend.save_article(new_article("b-post", ArticleContent(title="B")))
    backend.save_article(new_article("a-post", ArticleContent(title="A")))
    backend.save_page(new_page("home", PageContent(title="Home", slug="home")))

    assert [article.id for article in backend.load_all_articles()] == ["a-post", "b-post"]
    assert [page.id for page in backend.load_all_pages()] == ["home"]
    assert backend.load_all_media_assets() == []


def test_backend_is_a_context_manager(backend: StorageBackend) -> None:
    with backend as storage:
        storage.save_article(new_article("post", ArticleContent(title="Post")))


# Admin accounts and sessions (never part of the export)


def _user(username: str = "ana", role: Role = Role.EDITOR) -> User:
    return User(
        username=username,
        password_hash="argon2-hash-placeholder",
        role=role,
        created_at=datetime(2026, 7, 18, 12, 0, 0),
    )


def test_user_round_trip_and_upsert(backend: StorageBackend) -> None:
    backend.save_user(_user())
    assert backend.load_user("ana") == _user()
    backend.save_user(_user(role=Role.ADMIN))
    loaded = backend.load_user("ana")
    assert loaded is not None
    assert loaded.role is Role.ADMIN
    assert loaded.language is None  # unset preference follows the browser
    assert backend.list_usernames() == ["ana"]


def test_user_language_preference_round_trips(backend: StorageBackend) -> None:
    backend.save_user(_user().model_copy(update={"language": Language.PT_PT}))
    loaded = backend.load_user("ana")
    assert loaded is not None
    assert loaded.language is Language.PT_PT
    backend.save_user(_user())  # upsert back to unset
    reloaded = backend.load_user("ana")
    assert reloaded is not None
    assert reloaded.language is None


def test_user_delete_and_missing_user(backend: StorageBackend) -> None:
    backend.save_user(_user())
    assert backend.delete_user("ana")
    assert not backend.delete_user("ana")
    assert backend.load_user("ana") is None
    assert backend.list_usernames() == []


def test_users_do_not_count_as_content(backend: StorageBackend) -> None:
    backend.save_user(_user())
    assert not backend.has_content()


def test_session_round_trip_and_cascade(backend: StorageBackend) -> None:
    backend.save_user(_user())
    session = AdminSession(
        token_hash="digest-1",
        username="ana",
        csrf_token="csrf-1",
        expires_at=datetime(2026, 7, 18, 23, 59, 59),
    )
    backend.save_session(session)
    assert backend.load_session("digest-1") == session
    backend.delete_user("ana")
    assert backend.load_session("digest-1") is None


def test_expired_sessions_are_purged(backend: StorageBackend) -> None:
    backend.save_user(_user())
    stale = AdminSession(
        token_hash="digest-old",
        username="ana",
        csrf_token="csrf-old",
        expires_at=datetime(2026, 7, 18, 1, 0, 0),
    )
    fresh = AdminSession(
        token_hash="digest-new",
        username="ana",
        csrf_token="csrf-new",
        expires_at=datetime(2026, 7, 18, 23, 0, 0),
    )
    backend.save_session(stale)
    backend.save_session(fresh)
    assert backend.delete_expired_sessions(datetime(2026, 7, 18, 12, 0, 0)) == 1
    assert backend.load_session("digest-old") is None
    assert backend.load_session("digest-new") == fresh
    assert backend.delete_session("digest-new")
    assert not backend.delete_session("digest-new")
