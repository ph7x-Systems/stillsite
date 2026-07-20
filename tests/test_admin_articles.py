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
            "login_csrf": form.cookies["__Host-sardine_login_csrf"],
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


def _form_payload() -> dict[str, str]:
    return {
        "title": "Piece",
        "summary": "",
        "body_markdown": "Body.",
        "slug": "",
        "category": "",
        "tags": "",
        "cover": "",
    }


def test_publish_at_is_set_and_cleared_from_the_editor(tmp_path: Path) -> None:
    """ADR-0024: the scheduling moment round-trips through the form."""
    with _client(_app(tmp_path, _article("piece"))) as client:
        csrf = _sign_in(client)
        page = client.get("/articles/piece").text
        assert 'name="publish_at"' in page
        saved = client.post(
            "/articles/piece",
            data={**_form_payload(), "csrf_token": csrf, "publish_at": "2027-06-01T09:00"},
            follow_redirects=False,
        )
        assert saved.status_code == 303
        edited = client.get("/articles/piece").text
        assert 'value="2027-06-01T09:00"' in edited
        cleared = client.post(
            "/articles/piece",
            data={**_form_payload(), "csrf_token": csrf, "publish_at": ""},
            follow_redirects=False,
        )
        assert cleared.status_code == 303
        bad = client.post(
            "/articles/piece",
            data={**_form_payload(), "csrf_token": csrf, "publish_at": "not-a-moment"},
        )
        assert bad.status_code == 422
        assert "publish_at" in bad.text


def test_revisions_record_diff_and_restore(tmp_path: Path) -> None:
    """ADR-0025: every save snapshots; restore brings the old body back and
    is itself recorded as a new revision."""
    with _client(_app(tmp_path, _article("piece"))) as client:
        csrf = _sign_in(client)
        client.post(
            "/articles/piece",
            data={**_form_payload(), "csrf_token": csrf, "body_markdown": "First body."},
        )
        client.post(
            "/articles/piece",
            data={**_form_payload(), "csrf_token": csrf, "body_markdown": "Second body."},
        )
        editor = client.get("/articles/piece").text
        assert "Revisions" in editor
        assert 'href="/articles/piece/revisions/1"' in editor
        detail = client.get("/articles/piece/revisions/1").text
        assert "First body." in detail  # the diff shows the old line
        restored = client.post(
            "/articles/piece/revisions/1/restore",
            data={"csrf_token": csrf},
            follow_redirects=False,
        )
        assert restored.status_code == 303
        after = client.get("/articles/piece").text
        assert "First body." in after
        assert 'href="/articles/piece/revisions/3"' in after  # the restore itself


def test_trash_restore_and_purge_flow(tmp_path: Path) -> None:
    """ADR-0026: trash hides everywhere, restore is exact, purge is the
    only hard delete and needs the admin role."""
    with _client(_app(tmp_path, _article("bin-me"))) as client:
        csrf = _sign_in(client)
        trashed = client.post(
            "/trash/article/bin-me", data={"csrf_token": csrf}, follow_redirects=False
        )
        assert trashed.status_code == 303
        listing = client.get("/articles").text
        assert 'href="/articles/bin-me"' not in listing  # hidden from the list
        trash_page = client.get("/trash").text
        assert "bin-me" in trash_page
        restored = client.post(
            "/trash/article/bin-me/restore", data={"csrf_token": csrf}, follow_redirects=False
        )
        assert restored.status_code == 303
        assert 'href="/articles/bin-me"' in client.get("/articles").text
        client.post("/trash/article/bin-me", data={"csrf_token": csrf})
        forbidden = client.post(
            "/trash/article/bin-me/purge", data={"csrf_token": csrf}, follow_redirects=False
        )
        assert forbidden.status_code == 403  # purge is admin-only; editors cannot
        assert "bin-me" in client.get("/trash").text  # still safely in the trash


def test_purge_needs_the_admin_role_and_is_final(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'content.db'}"
    with create_storage(url) as storage:
        storage.save_user(
            User(
                username="root",
                password_hash=hash_password(PASSWORD),
                role=Role.ADMIN,
                created_at=NOW,
            )
        )
        storage.save_article(_article("bin-me"))
    app = create_app(AdminSettings(storage_url=url, media_dir=tmp_path / "media"))
    with _client(app) as client:
        form = client.get("/login")
        client.post(
            "/login",
            data={
                "username": "root",
                "password": PASSWORD,
                "login_csrf": form.cookies["__Host-sardine_login_csrf"],
            },
        )
        csrf = client.get("/").text.split('name="csrf_token" value="')[1].split('"')[0]
        client.post("/trash/article/bin-me", data={"csrf_token": csrf})
        purged = client.post(
            "/trash/article/bin-me/purge", data={"csrf_token": csrf}, follow_redirects=False
        )
        assert purged.status_code == 303
        assert client.get("/articles/bin-me").status_code == 404
        assert "bin-me" not in client.get("/trash").text


def test_duplicate_as_draft_resets_state_and_resolves_id(tmp_path: Path) -> None:
    """M5: a copy keeps content, drops schedule/trash, and never collides."""
    article = _article("origin")
    article.status = ContentStatus.PUBLISHED
    with _client(_app(tmp_path, article)) as client:
        csrf = _sign_in(client)
        first = client.post(
            "/articles/origin/duplicate", data={"csrf_token": csrf}, follow_redirects=False
        )
        assert first.headers["location"] == "/articles/origin-copy"
        second = client.post(
            "/articles/origin/duplicate", data={"csrf_token": csrf}, follow_redirects=False
        )
        assert second.headers["location"] == "/articles/origin-copy-2"
        editor = client.get("/articles/origin-copy").text
        assert "draft" in editor  # the copy starts over in the workflow


def test_notes_add_and_delete_with_authorship_gate(tmp_path: Path) -> None:
    """M5: the note trail — anyone writes, only the author or an admin
    removes; notes never publish."""
    with _client(_app(tmp_path, _article("piece"))) as client:
        csrf = _sign_in(client)
        added = client.post(
            "/notes/article/piece",
            data={"csrf_token": csrf, "body": "Needs a better title."},
            follow_redirects=False,
        )
        assert added.status_code == 303
        editor = client.get("/articles/piece").text
        assert "Needs a better title." in editor
        removed = client.post(
            "/notes/article/piece/1/delete", data={"csrf_token": csrf}, follow_redirects=False
        )
        assert removed.status_code == 303  # author removes their own
        assert "Needs a better title." not in client.get("/articles/piece").text


def test_list_quick_actions_transition_without_the_editor(tmp_path: Path) -> None:
    """M5: workflow moves straight from the list row."""
    with _client(_app(tmp_path, _article("piece"))) as client:
        csrf = _sign_in(client)
        listing = client.get("/articles").text
        assert "bi-three-dots" in listing
        assert "Submit for review" in listing
        moved = client.post(
            "/articles/piece/status",
            data={"csrf_token": csrf, "to": "review"},
            follow_redirects=False,
        )
        assert moved.status_code == 303
        assert "review" in client.get("/articles").text
