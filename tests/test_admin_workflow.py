"""The editorial workflow and panel publishing (Milestone 3 phase 8).

Role-gated transitions over real HTTP, the publish gate blocking on the
entity's validation errors, and preview/build runs through the real
builder into real directories.
"""

from datetime import UTC, datetime
from pathlib import Path

from cms_admin import AdminSettings, create_app
from cms_admin.security import hash_password
from cms_admin.workflow import available_transitions, publish_blockers
from cms_core import (
    Article,
    ArticleContent,
    ContentStatus,
    Role,
    User,
    create_storage,
    new_article,
)
from cms_core.languages import TARGET_LANGUAGES
from cms_validation import SiteContent
from fastapi import FastAPI
from fastapi.testclient import TestClient

PASSWORD = "correct horse battery staple"
NOW = datetime(2026, 7, 18, tzinfo=UTC)


def _article(article_id: str, status: ContentStatus, *, complete: bool = False) -> Article:
    article = new_article(article_id, ArticleContent(title=article_id.title()), now=NOW)
    article.status = status
    if complete:
        for language in TARGET_LANGUAGES:
            article.set_translation(language, ArticleContent(title=f"{article_id} {language}"))
    return article


def _project_dir(tmp_path: Path) -> Path:
    (tmp_path / "sardine.toml").write_text(
        '[site]\nname = "Test Site"\nbase_url = "https://test.example"\nlanguages = []\n',
        encoding="utf-8",
    )
    return tmp_path


def _app(
    tmp_path: Path,
    *articles: Article,
    role: Role = Role.PUBLISHER,
    with_project: bool = False,
    publish_gate: bool = True,
) -> FastAPI:
    url = f"sqlite:///{tmp_path / 'content.db'}"
    with create_storage(url) as storage:
        storage.save_user(
            User(
                username="ana",
                password_hash=hash_password(PASSWORD),
                role=role,
                created_at=NOW,
            )
        )
        for article in articles:
            storage.save_article(article)
    return create_app(
        AdminSettings(
            storage_url=url,
            media_dir=tmp_path / "media",
            project_dir=_project_dir(tmp_path) if with_project else tmp_path / "nowhere",
            publish_gate=publish_gate,
        )
    )


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


def test_transitions_follow_the_role_ladder() -> None:
    draft = ContentStatus.DRAFT
    review = ContentStatus.REVIEW
    assert [t["to"] for t in available_transitions(draft, Role.EDITOR)] == ["review"]
    assert available_transitions(review, Role.EDITOR) == []
    targets = {t["to"] for t in available_transitions(review, Role.PUBLISHER)}
    assert targets == {"draft", "published"}
    published = ContentStatus.PUBLISHED
    published_targets = {t["to"] for t in available_transitions(published, Role.ADMIN)}
    assert published_targets == {"draft", "archived"}  # direct unpublish + archive
    assert available_transitions(published, Role.REVIEWER) == []


def test_publish_blockers_scope_to_the_entity() -> None:
    incomplete = _article("half-done", ContentStatus.REVIEW)
    other = _article("unrelated", ContentStatus.DRAFT)
    blockers = publish_blockers(incomplete, SiteContent(articles=[incomplete, other]))
    assert blockers
    assert all("half-done" in blocker for blocker in blockers)
    complete = _article("all-done", ContentStatus.REVIEW, complete=True)
    assert publish_blockers(complete, SiteContent(articles=[complete])) == []


def test_editor_submits_for_review_but_cannot_publish(tmp_path: Path) -> None:
    app = _app(
        tmp_path,
        _article("piece", ContentStatus.DRAFT, complete=True),
        role=Role.EDITOR,
    )
    with _client(app) as client:
        csrf = _sign_in(client)
        editor_page = client.get("/articles/piece").text
        assert "Submit for review" in editor_page
        # the editor role gets no Publish button ("Publish at" field and the
        # Publishing nav entry are not transitions)
        assert ">Publish</button>" not in editor_page
        ok = client.post(
            "/articles/piece/status",
            data={"csrf_token": csrf, "to": "review"},
            follow_redirects=False,
        )
        assert ok.status_code == 303
        forbidden = client.post(
            "/articles/piece/status", data={"csrf_token": csrf, "to": "published"}
        )
    assert forbidden.status_code == 403
    with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
        stored = storage.load_article("piece")
    assert stored is not None
    assert stored.status is ContentStatus.REVIEW


def test_publish_gate_blocks_incomplete_translations(tmp_path: Path) -> None:
    app = _app(tmp_path, _article("half", ContentStatus.REVIEW))
    with _client(app) as client:
        csrf = _sign_in(client)
        blocked = client.post("/articles/half/status", data={"csrf_token": csrf, "to": "published"})
        assert blocked.status_code == 422
        assert "required-translations" in blocked.text
        # the gate is configurable: disabled, the same transition passes
    (tmp_path / "second").mkdir(exist_ok=True)
    app2 = _app(
        tmp_path / "second",
        _article("half", ContentStatus.REVIEW),
        publish_gate=False,
    )
    with _client(app2) as client:
        csrf = _sign_in(client)
        allowed_now = client.post(
            "/articles/half/status",
            data={"csrf_token": csrf, "to": "published"},
            follow_redirects=False,
        )
    assert allowed_now.status_code == 303


def test_publisher_full_cycle_publish_archive_restore(tmp_path: Path) -> None:
    app = _app(tmp_path, _article("cycle", ContentStatus.REVIEW, complete=True))
    with _client(app) as client:
        csrf = _sign_in(client)
        for target in ("published", "archived", "draft"):
            response = client.post(
                "/articles/cycle/status",
                data={"csrf_token": csrf, "to": target},
                follow_redirects=False,
            )
            assert response.status_code == 303, target
        invalid = client.post("/articles/cycle/status", data={"csrf_token": csrf, "to": "archived"})
    assert invalid.status_code == 400  # draft→archived is not a transition


def test_direct_unpublish_takes_one_click(tmp_path: Path) -> None:
    """M5: published content returns to draft directly — no archive detour."""
    app = _app(tmp_path, _article("live", ContentStatus.PUBLISHED, complete=True))
    with _client(app) as client:
        csrf = _sign_in(client)
        page = client.get("/articles/live").text
        assert "Unpublish" in page
        response = client.post(
            "/articles/live/status",
            data={"csrf_token": csrf, "to": "draft"},
            follow_redirects=False,
        )
        assert response.status_code == 303
    with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
        stored = storage.load_article("live")
    assert stored is not None
    assert stored.status is ContentStatus.DRAFT


def test_preview_builds_into_the_served_directory(tmp_path: Path) -> None:
    app = _app(
        tmp_path,
        _article("live", ContentStatus.PUBLISHED),
        with_project=True,
    )
    with _client(app) as client:
        csrf = _sign_in(client)
        run = client.post("/publishing/preview", data={"csrf_token": csrf}, follow_redirects=False)
        assert run.status_code == 303
        panel = client.get("/publishing").text
        preview = client.get("/preview/blog/")
    assert "preview" in panel
    assert "ok" in panel
    assert preview.status_code == 200
    assert "Test Site" in preview.text


def test_build_writes_the_output_with_target_extras(tmp_path: Path) -> None:
    app = _app(
        tmp_path,
        _article("live", ContentStatus.PUBLISHED),
        with_project=True,
    )
    with _client(app) as client:
        csrf = _sign_in(client)
        run = client.post(
            "/publishing/build",
            data={"csrf_token": csrf, "target": "swa"},
            follow_redirects=False,
        )
        assert run.status_code == 303
        dashboard = client.get("/").text
    assert (tmp_path / "_site" / "blog" / "index.html").is_file()
    assert (tmp_path / "_site" / "staticwebapp.config.json").is_file()
    assert "build (swa)" in dashboard  # the dashboard shows the last run


def test_build_requires_publisher_and_a_project(tmp_path: Path) -> None:
    app = _app(tmp_path, role=Role.EDITOR, with_project=True)
    with _client(app) as client:
        csrf = _sign_in(client)
        forbidden = client.post("/publishing/build", data={"csrf_token": csrf})
        assert forbidden.status_code == 403
    (tmp_path / "noproj").mkdir(exist_ok=True)
    app2 = _app(tmp_path / "noproj", role=Role.PUBLISHER)
    with _client(app2) as client:
        csrf = _sign_in(client)
        client.post("/publishing/build", data={"csrf_token": csrf})
        panel = client.get("/publishing").text
    assert "no sardine.toml" in panel


def test_publishing_report_lists_every_rule_with_outcomes(tmp_path: Path) -> None:
    """The publish gate shows what ran: all five rules, pass or fail, plus
    the scope of the content set it validated."""
    app = _app(tmp_path, _article("live", ContentStatus.PUBLISHED, complete=True))
    with _client(app) as client:
        _sign_in(client)
        panel = client.get("/publishing").text
    for rule in (
        "required-translations",
        "unique-slugs",
        "media-references",
        "media-alt-coverage",
        "known-categories",
    ):
        assert rule in panel
    assert "Publish gate open" in panel
    assert "admin-rules-table" in panel
    assert "1 article" in panel  # the validated scope is stated


def test_publishing_report_links_issues_to_their_edit_screens(tmp_path: Path) -> None:
    app = _app(tmp_path, _article("halfway", ContentStatus.REVIEW))
    with _client(app) as client:
        _sign_in(client)
        panel = client.get("/publishing").text
    assert "Publish gate open" in panel  # warnings never block
    assert "warning" in panel
    assert 'href="/articles/halfway"' in panel
