"""The editorial calendar (#132): the month as the panel sees time."""

from datetime import UTC, datetime
from pathlib import Path

from cms_admin import AdminSettings, create_app
from cms_admin.security import hash_password
from cms_core import ContentStatus, Role, User, create_storage
from cms_core.models import Article, ArticleContent, new_article
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
        published = new_article(
            "launched",
            ArticleContent(title="Launched note", summary="S", body_markdown="B"),
            now=datetime(2030, 3, 5, 9, 30, tzinfo=UTC),
        )
        published.status = ContentStatus.PUBLISHED
        storage.save_article(published)
        scheduled = new_article(
            "upcoming",
            ArticleContent(title="Upcoming note", summary="S", body_markdown="B"),
            now=NOW,
        )
        scheduled.status = ContentStatus.PUBLISHED
        scheduled.publish_at = datetime(2030, 3, 18, 14, 45, tzinfo=UTC)
        storage.save_article(scheduled)
        draft = new_article(
            "invisible",
            ArticleContent(title="Unscheduled draft", summary="S", body_markdown="B"),
            now=datetime(2030, 3, 9, tzinfo=UTC),
        )
        storage.save_article(draft)
    return create_app(AdminSettings(storage_url=url, media_dir=tmp_path / "media"))


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
    return client.get("/").text.split('name="csrf_token" value="')[1].split('"')[0]


def test_month_view_places_entries_on_their_utc_days(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        _sign_in(client)
        month = client.get("/calendar?month=2030-03").text
    assert "Launched note" in month  # published on its creation day
    assert "Upcoming note" in month and "scheduled" in month
    assert "Unscheduled draft" not in month  # drafts appear only when scheduled
    assert 'data-calendar-day="2030-03-05"' in month
    assert "2030-02" in month and "2030-04" in month  # month navigation


def test_reschedule_moves_the_day_and_keeps_the_time(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        csrf = _sign_in(client)
        response = client.post(
            "/calendar/reschedule",
            data={
                "csrf_token": csrf,
                "kind": "article",
                "entity_id": "upcoming",
                "day": "2030-03-25",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
    with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
        moved = storage.load_article("upcoming")
    assert isinstance(moved, Article)
    assert moved.publish_at == datetime(2030, 3, 25, 14, 45, tzinfo=UTC)


def test_reschedule_refuses_history_and_bad_input(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        csrf = _sign_in(client)
        history = client.post(
            "/calendar/reschedule",
            data={
                "csrf_token": csrf,
                "kind": "article",
                "entity_id": "launched",
                "day": "2030-03-25",
            },
        )
        assert history.status_code == 400  # published history never moves
        bad_month = client.get("/calendar?month=not-a-month")
        assert bad_month.status_code == 400
