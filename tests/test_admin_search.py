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
