"""The users screen (M5): admin-only account management with safeguards."""

from datetime import UTC, datetime
from pathlib import Path

from cms_admin import AdminSettings, create_app
from cms_admin.security import hash_password
from cms_core import Role, User, create_storage
from fastapi import FastAPI
from fastapi.testclient import TestClient

PASSWORD = "correct horse battery staple"
NOW = datetime(2026, 7, 19, tzinfo=UTC)


def _app(tmp_path: Path, role: Role = Role.ADMIN) -> FastAPI:
    url = f"sqlite:///{tmp_path / 'content.db'}"
    with create_storage(url) as storage:
        storage.save_user(
            User(
                username="root",
                password_hash=hash_password(PASSWORD),
                role=role,
                created_at=NOW,
            )
        )
    return create_app(AdminSettings(storage_url=url, media_dir=tmp_path / "media"))


def _sign_in(client: TestClient) -> str:
    form = client.get("/login")
    client.post(
        "/login",
        data={
            "username": "root",
            "password": PASSWORD,
            "login_csrf": form.cookies["sardine_login_csrf"],
        },
    )
    return client.get("/").text.split('name="csrf_token" value="')[1].split('"')[0]


def test_users_screen_needs_the_admin_role(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path, role=Role.PUBLISHER), base_url="https://testserver") as client:
        _sign_in(client)
        assert client.get("/users").status_code == 403
        page = client.get("/").text
    assert 'href="/users"' not in page  # the sidebar hides it too


def test_create_change_role_and_delete(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        csrf = _sign_in(client)
        created = client.post(
            "/users",
            data={
                "csrf_token": csrf,
                "username": "rui",
                "password": "a-long-enough-password",
                "role": "editor",
                "language": "pt-pt",
            },
            follow_redirects=False,
        )
        assert created.status_code == 303
        page = client.get("/users").text
        assert "rui" in page
        promoted = client.post(
            "/users/rui/role",
            data={"csrf_token": csrf, "role": "publisher"},
            follow_redirects=False,
        )
        assert promoted.status_code == 303
        removed = client.post(
            "/users/rui/delete", data={"csrf_token": csrf}, follow_redirects=False
        )
        assert removed.status_code == 303
        assert "rui" not in client.get("/users").text


def test_safeguards_protect_self_and_last_admin(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        csrf = _sign_in(client)
        own = client.post("/users/root/delete", data={"csrf_token": csrf})
        assert own.status_code == 422
        demote = client.post("/users/root/role", data={"csrf_token": csrf, "role": "editor"})
        assert demote.status_code == 422
        weak = client.post(
            "/users",
            data={"csrf_token": csrf, "username": "x!", "password": "short", "role": "editor"},
        )
        assert weak.status_code == 422
        assert "password" in weak.text
