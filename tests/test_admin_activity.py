"""The audit trail (#134): every listed action produces one record."""

from datetime import UTC, datetime
from pathlib import Path

from cms_admin import AdminSettings, create_app
from cms_admin.security import hash_password
from cms_core import Role, User, create_storage
from cms_core.models import ArticleContent, new_article
from fastapi import FastAPI
from fastapi.testclient import TestClient

PASSWORD = "correct horse battery staple"
NOW = datetime(2026, 7, 21, tzinfo=UTC)


def _app(tmp_path: Path, role: Role = Role.ADMIN) -> FastAPI:
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
        article = new_article(
            "traced", ArticleContent(title="Traced", summary="S", body_markdown="B"), now=NOW
        )
        storage.save_article(article)
    return create_app(AdminSettings(storage_url=url, media_dir=tmp_path / "media"))


def _sign_in(client: TestClient, username: str = "ana") -> str:
    form = client.get("/login")
    client.post(
        "/login",
        data={
            "username": username,
            "password": PASSWORD,
            "login_csrf": form.cookies["__Host-sardine_login_csrf"],
        },
    )
    return client.get("/").text.split('name="csrf_token" value="')[1].split('"')[0]


def _actions(tmp_path: Path) -> list[tuple[str, str, str]]:
    with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
        return [
            (record.actor, record.action, record.subject_id) for record in storage.list_activity()
        ]


def test_sign_in_transition_and_trash_each_produce_one_record(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        csrf = _sign_in(client)
        client.post(
            "/articles/traced/status",
            data={"csrf_token": csrf, "to": "review"},
            follow_redirects=False,
        )
        client.post("/trash/article/traced", data={"csrf_token": csrf}, follow_redirects=False)
    actions = _actions(tmp_path)
    assert actions.count(("ana", "signed-in", "ana")) == 1
    assert actions.count(("ana", "review", "traced")) == 1
    assert actions.count(("ana", "trashed", "traced")) == 1


def test_failed_sign_in_is_recorded(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        form = client.get("/login")
        client.post(
            "/login",
            data={
                "username": "ana",
                "password": "wrong password entirely",
                "login_csrf": form.cookies["__Host-sardine_login_csrf"],
            },
        )
    assert ("ana", "sign-in-failed", "ana") in _actions(tmp_path)


def test_records_survive_purge_of_their_subject(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        csrf = _sign_in(client)
        client.post("/trash/article/traced", data={"csrf_token": csrf}, follow_redirects=False)
        client.post(
            "/trash/article/traced/purge", data={"csrf_token": csrf}, follow_redirects=False
        )
    actions = _actions(tmp_path)
    assert ("ana", "purged", "traced") in actions
    assert ("ana", "trashed", "traced") in actions  # history intact after hard delete


def test_activity_screen_is_admin_only_and_filters(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        csrf = _sign_in(client)
        client.post(
            "/articles/traced/status",
            data={"csrf_token": csrf, "to": "review"},
            follow_redirects=False,
        )
        screen = client.get("/activity").text
        assert "signed-in" in screen and "review" in screen
        filtered = client.get("/activity?actor=nobody").text
        assert "No activity in this window" in filtered
    with TestClient(_app(tmp_path, role=Role.EDITOR), base_url="https://testserver") as client:
        _sign_in(client)
        assert client.get("/activity").status_code == 403
        assert "/activity" not in client.get("/").text  # link hidden below admin


def test_dashboard_needs_attention_cards_and_empty_state(tmp_path: Path) -> None:
    """#135: the dashboard reports work, not totals — with a real empty
    state when nothing waits."""
    from datetime import timedelta

    from cms_core import ContentStatus

    url = f"sqlite:///{tmp_path / 'attention.db'}"
    with create_storage(url) as storage:
        storage.save_user(
            User(
                username="ana",
                password_hash=hash_password(PASSWORD),
                role=Role.ADMIN,
                created_at=NOW,
            )
        )
    app = create_app(AdminSettings(storage_url=url, media_dir=tmp_path / "m1"))
    with TestClient(app, base_url="https://testserver") as client:
        _sign_in(client)
        empty = client.get("/").text
    assert "Nothing is waiting for you" in empty

    with create_storage(url) as storage:
        reviewing = new_article(
            "pitch", ArticleContent(title="Pitch", summary="S", body_markdown="B"), now=NOW
        )
        reviewing.status = ContentStatus.REVIEW
        storage.save_article(reviewing)
        scheduled = new_article(
            "soon", ArticleContent(title="Soon", summary="S", body_markdown="B"), now=NOW
        )
        scheduled.status = ContentStatus.PUBLISHED
        scheduled.publish_at = datetime.now(tz=UTC) + timedelta(days=2)
        storage.save_article(scheduled)
        stale = new_article(
            "dusty", ArticleContent(title="Dusty", summary="S", body_markdown="B"), now=NOW
        )
        stale.updated_at = datetime.now(tz=UTC) - timedelta(days=45)
        storage.save_article(stale)
    app = create_app(AdminSettings(storage_url=url, media_dir=tmp_path / "m2"))
    with TestClient(app, base_url="https://testserver") as client:
        _sign_in(client)
        dashboard = client.get("/").text
    assert "in review" in dashboard and "waiting for your decision" in dashboard
    assert "scheduled change(s) in the next 7 days" in dashboard
    assert "untouched for 30 days" in dashboard
    assert 'href="/translations"' in dashboard  # missing translations card links
