"""Global admin search (#129): grouped results over the real surface."""

from datetime import UTC, datetime
from pathlib import Path

from cms_admin import AdminSettings, create_app
from cms_admin.security import hash_password
from cms_core import Language, Role, User, create_storage
from cms_core.models import ArticleContent, new_article
from cms_core.pages import PageContent, Section, SectionContent, new_page
from fastapi import FastAPI
from fastapi.testclient import TestClient

PASSWORD = "correct horse battery staple"
NOW = datetime(2026, 7, 21, tzinfo=UTC)


def _app(tmp_path: Path) -> FastAPI:
    url = f"sqlite:///{tmp_path / 'content.db'}"
    with create_storage(url) as storage:
        storage.save_user(
            User(
                username="ana",
                password_hash=hash_password(PASSWORD),
                role=Role.EDITOR,
                created_at=NOW,
            )
        )
        article = new_article(
            "voyage",
            ArticleContent(title="The tin voyage", summary="S", body_markdown="B"),
            now=NOW,
        )
        article.set_translation(
            Language.PT_PT, ArticleContent(title="A viagem da lata", summary="S")
        )
        storage.save_article(article)
        page = new_page("crew", PageContent(title="Crew voyage notes", slug="crew"), now=NOW)
        page.sections.append(
            Section(
                key="faq",
                kind="faq",
                source=SectionContent(items=[{"question": "Voyage length?", "answer": "A."}]),
            )
        )
        storage.save_page(page)
    return create_app(AdminSettings(storage_url=url, media_dir=tmp_path / "media"))


def _sign_in(client: TestClient) -> None:
    form = client.get("/login")
    client.post(
        "/login",
        data={
            "username": "ana",
            "password": PASSWORD,
            "login_csrf": form.cookies["__Host-sardine_login_csrf"],
        },
    )


def test_search_requires_a_session(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        response = client.get("/search?q=voyage", follow_redirects=False)
    assert response.status_code == 303


def test_search_groups_hits_and_links_to_editors(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        _sign_in(client)
        page = client.get("/search?q=voyage").text
    assert 'href="/articles/voyage"' in page
    assert 'href="/pages/crew"' in page
    assert 'href="/pages/crew/sections/faq"' in page


def test_search_matches_translated_text(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        _sign_in(client)
        page = client.get("/search?q=viagem da lata").text
    assert 'href="/articles/voyage"' in page


def test_search_empty_state_and_navbar_box(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        _sign_in(client)
        empty = client.get("/search?q=zzz-nothing").text
        home = client.get("/").text
    assert "Nothing matched" in empty
    assert 'action="/search"' in home  # the navbar box is everywhere


def test_translation_queue_lists_pending_pairs_and_filters(tmp_path: Path) -> None:
    """#131: the queue agrees with the model — missing and outdated pairs
    listed per configured language, filterable, linking to the editors."""
    url = f"sqlite:///{tmp_path / 'content.db'}"
    with create_storage(url) as storage:
        storage.save_user(
            User(
                username="ana",
                password_hash=hash_password(PASSWORD),
                role=Role.EDITOR,
                created_at=NOW,
            )
        )
        complete = new_article(
            "done", ArticleContent(title="Done", summary="S", body_markdown="B"), now=NOW
        )
        complete.set_translation(
            Language.PT_PT, ArticleContent(title="Feito", summary="S", body_markdown="B")
        )
        storage.save_article(complete)
        outdated = new_article(
            "stale", ArticleContent(title="Stale", summary="S", body_markdown="B"), now=NOW
        )
        outdated.set_translation(
            Language.PT_PT, ArticleContent(title="Velho", summary="S", body_markdown="B")
        )
        outdated.source = ArticleContent(title="Stale but edited", summary="S", body_markdown="B")
        storage.save_article(outdated)
        page = new_page("crew-q", PageContent(title="Crew", slug="crew-q"), now=NOW)
        storage.save_page(page)
    (tmp_path / "sardine.toml").write_text(
        '[site]\nname = "Q"\nbase_url = "https://q.example"\nlanguages = ["pt-pt"]\n',
        encoding="utf-8",
    )
    app = create_app(
        AdminSettings(storage_url=url, media_dir=tmp_path / "media", project_dir=tmp_path)
    )
    with TestClient(app, base_url="https://testserver") as client:
        _sign_in(client)
        queue = client.get("/translations").text
        assert "Stale but edited" in queue and "outdated" in queue
        assert "Crew" in queue and "missing" in queue
        assert "Done" not in queue  # complete pairs never appear
        assert 'href="/articles/stale/translations/pt-pt"' in queue
        only_missing = client.get("/translations?state=missing").text
        assert "Crew" in only_missing and "Stale but edited" not in only_missing
        only_articles = client.get("/translations?kind=article").text
        assert "Crew" not in only_articles and "Stale but edited" in only_articles


def test_list_needs_filter_shows_only_incomplete(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'content.db'}"
    with create_storage(url) as storage:
        storage.save_user(
            User(
                username="ana",
                password_hash=hash_password(PASSWORD),
                role=Role.EDITOR,
                created_at=NOW,
            )
        )
        done = new_article(
            "done-f", ArticleContent(title="All done", summary="S", body_markdown="B"), now=NOW
        )
        done.set_translation(
            Language.PT_PT, ArticleContent(title="Feito", summary="S", body_markdown="B")
        )
        storage.save_article(done)
        pending = new_article(
            "pending-f",
            ArticleContent(title="Still pending", summary="S", body_markdown="B"),
            now=NOW,
        )
        storage.save_article(pending)
    (tmp_path / "sardine.toml").write_text(
        '[site]\nname = "F"\nbase_url = "https://f.example"\nlanguages = ["pt-pt"]\n',
        encoding="utf-8",
    )
    app = create_app(
        AdminSettings(storage_url=url, media_dir=tmp_path / "media", project_dir=tmp_path)
    )
    with TestClient(app, base_url="https://testserver") as client:
        _sign_in(client)
        everything = client.get("/articles").text
        assert "All done" in everything and "Still pending" in everything
        filtered = client.get("/articles?needs=pt-pt").text
    assert "Still pending" in filtered
    assert "All done" not in filtered
