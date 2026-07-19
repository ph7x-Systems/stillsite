"""Admin articles: list, create, edit, and the side-by-side translation editor.

Exercises the real flows over HTTP — no mocked internals: forms POST and
redirect, validation errors re-render the submitted values, the checksum
model drives the state indicators, and the preview is the builder's own
renderer with raw HTML disabled.
"""

from datetime import UTC, datetime
from pathlib import Path

from cms_admin import AdminSettings, create_app
from cms_admin.articles import parse_tags
from cms_admin.security import hash_password
from cms_core import (
    Article,
    ArticleContent,
    ContentStatus,
    Language,
    Role,
    User,
    create_storage,
    new_article,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient

PASSWORD = "correct horse battery staple"
NOW = datetime(2026, 7, 18, tzinfo=UTC)


def _article(article_id: str, *translated: Language) -> Article:
    article = new_article(article_id, ArticleContent(title=article_id.title()), now=NOW)
    for language in translated:
        article.set_translation(language, ArticleContent(title=f"{article_id} ({language})"))
    return article


def _app(tmp_path: Path, *articles: Article) -> FastAPI:
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
        for article in articles:
            storage.save_article(article)
    return create_app(AdminSettings(storage_url=url))


def _client(app: FastAPI) -> TestClient:
    return TestClient(app, base_url="https://testserver")


def _sign_in(client: TestClient) -> str:
    form = client.get("/login")
    client.post(
        "/login",
        data={
            "username": "ana",
            "password": PASSWORD,
            "login_csrf": form.cookies["sardine_login_csrf"],
        },
    )
    dashboard: str = client.get("/").text
    return dashboard.split('name="csrf_token" value="')[1].split('"')[0]


def test_parse_tags_splits_and_strips() -> None:
    assert parse_tags(" alpha, beta ,,gamma ") == ("alpha", "beta", "gamma")
    assert parse_tags("") == ()


def test_articles_require_a_session(tmp_path: Path) -> None:
    with _client(_app(tmp_path)) as client:
        response = client.get("/articles", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_list_shows_articles_with_translation_states(tmp_path: Path) -> None:
    app = _app(tmp_path, _article("first-post", Language.PT_PT))
    with _client(app) as client:
        _sign_in(client)
        page = client.get("/articles").text
    assert "first-post" in page
    assert "admin-state-complete" in page  # PT-PT
    assert "admin-state-missing" in page  # the other languages
    assert "/articles/first-post/translations/pt-pt" in page


def test_list_empty_state(tmp_path: Path) -> None:
    with _client(_app(tmp_path)) as client:
        _sign_in(client)
        page = client.get("/articles").text
    assert "No articles yet" in page


def test_create_redirects_to_the_editor_and_persists(tmp_path: Path) -> None:
    with _client(_app(tmp_path)) as client:
        csrf = _sign_in(client)
        response = client.post(
            "/articles",
            data={
                "csrf_token": csrf,
                "id": "hello-world",
                "title": "Hello world",
                "summary": "The first one.",
                "body_markdown": "# Hi",
                "slug": "hello",
                "category": "news",
                "tags": "intro, meta",
                "cover": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/articles/hello-world"
        editor = client.get("/articles/hello-world").text
    assert "Hello world" in editor
    assert "<h1>Hi</h1>" in editor  # builder-rendered preview
    assert 'value="intro, meta"' in editor


def test_create_with_invalid_id_rerenders_the_form(tmp_path: Path) -> None:
    with _client(_app(tmp_path)) as client:
        csrf = _sign_in(client)
        response = client.post(
            "/articles",
            data={"csrf_token": csrf, "id": "Bad Id!", "title": "Kept title"},
        )
    assert response.status_code == 422
    assert "The form was not saved" in response.text
    assert 'value="Kept title"' in response.text


def test_create_refuses_a_duplicate_id(tmp_path: Path) -> None:
    app = _app(tmp_path, _article("taken"))
    with _client(app) as client:
        csrf = _sign_in(client)
        response = client.post(
            "/articles", data={"csrf_token": csrf, "id": "taken", "title": "Again"}
        )
    assert response.status_code == 422
    assert "already exists" in response.text


def test_editing_the_source_marks_translations_outdated(tmp_path: Path) -> None:
    app = _app(tmp_path, _article("first-post", Language.PT_PT))
    with _client(app) as client:
        csrf = _sign_in(client)
        response = client.post(
            "/articles/first-post",
            data={"csrf_token": csrf, "title": "Edited source", "tags": ""},
            follow_redirects=False,
        )
        assert response.status_code == 303
        editor = client.get("/articles/first-post").text
    assert "admin-state-outdated" in editor


def test_edit_validation_error_keeps_the_submitted_values(tmp_path: Path) -> None:
    app = _app(tmp_path, _article("first-post"))
    with _client(app) as client:
        csrf = _sign_in(client)
        response = client.post(
            "/articles/first-post",
            data={"csrf_token": csrf, "title": "", "summary": "kept summary"},
        )
    assert response.status_code == 422
    assert "kept summary" in response.text
    # nothing was saved
    with _client(app) as client:
        _sign_in(client)
        assert "First-Post" in client.get("/articles/first-post").text


def test_saving_a_translation_completes_it_with_its_own_slug(tmp_path: Path) -> None:
    app = _app(tmp_path, _article("first-post"))
    with _client(app) as client:
        csrf = _sign_in(client)
        response = client.post(
            "/articles/first-post/translations/pt-pt",
            data={
                "csrf_token": csrf,
                "title": "Primeiro artigo",
                "summary": "",
                "body_markdown": "Corpo.",
                "slug": "primeiro-artigo",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        page = client.get("/articles/first-post/translations/pt-pt").text
    assert "admin-state-complete" in page
    assert 'value="primeiro-artigo"' in page
    with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
        stored = storage.load_article("first-post")
    assert stored is not None
    assert stored.translations[Language.PT_PT].content.slug == "primeiro-artigo"


def test_translation_editor_shows_the_source_side_by_side(tmp_path: Path) -> None:
    article = _article("first-post")
    article.source = ArticleContent(title="Source title", body_markdown="## Section")
    app = _app(tmp_path, article)
    with _client(app) as client:
        _sign_in(client)
        page = client.get("/articles/first-post/translations/es").text
    assert "Source title" in page
    assert "<h2>Section</h2>" in page  # rendered source preview
    assert "admin-state-missing" in page


def test_unknown_language_and_source_language_are_404(tmp_path: Path) -> None:
    app = _app(tmp_path, _article("first-post"))
    with _client(app) as client:
        _sign_in(client)
        assert client.get("/articles/first-post/translations/xx").status_code == 404
        assert client.get("/articles/first-post/translations/en").status_code == 404
        assert client.get("/articles/missing").status_code == 404


def test_stored_content_never_renders_as_raw_html(tmp_path: Path) -> None:
    """Both the preview (builder renderer, html off) and every templated value
    (autoescape forced on for .html.j2) must escape user-controlled content."""
    article = _article("first-post")
    article.source = ArticleContent(
        title="<img src=x onerror=alert(1)>", body_markdown='<script>alert("x")</script>'
    )
    app = _app(tmp_path, article)
    with _client(app) as client:
        _sign_in(client)
        page = client.get("/articles/first-post").text
        listing = client.get("/articles").text
    assert "<script>alert" not in page
    assert "&lt;script&gt;" in page
    assert "<img src=x" not in page
    assert "<img src=x" not in listing


def test_article_posts_require_the_csrf_token(tmp_path: Path) -> None:
    app = _app(tmp_path, _article("first-post"))
    with _client(app) as client:
        _sign_in(client)
        response = client.post("/articles/first-post", data={"title": "No token"})
    assert response.status_code == 403


def test_status_is_displayed_but_not_editable_here(tmp_path: Path) -> None:
    article = _article("first-post")
    article.status = ContentStatus.REVIEW
    app = _app(tmp_path, article)
    with _client(app) as client:
        csrf = _sign_in(client)
        page = client.get("/articles/first-post").text
        assert "review" in page
        client.post(
            "/articles/first-post",
            data={"csrf_token": csrf, "title": "Edited", "tags": ""},
        )
    with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
        stored = storage.load_article("first-post")
    assert stored is not None
    assert stored.status is ContentStatus.REVIEW  # workflow transitions arrive in phase 8


def test_markdown_bodies_carry_the_editor_marker(tmp_path: Path) -> None:
    """ADR-0023: the Markdown textarea is enhanced by the vendored editor;
    plain textareas (summary) are not. Toolbar labels ship localized."""
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        _sign_in(client)
        page = client.get("/articles/new").text
    assert 'name="body_markdown"' in page
    assert "data-markdown-editor" in page
    assert "data-markdown-labels" in page
    assert page.count("data-markdown-editor") == 1  # summary stays plain
