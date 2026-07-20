"""The menu manager (M6): explicit navigation from the panel."""

from datetime import UTC, datetime
from pathlib import Path

from cms_admin import AdminSettings, create_app
from cms_admin.security import hash_password
from cms_core import Role, User, create_storage
from fastapi import FastAPI
from fastapi.testclient import TestClient

PASSWORD = "correct horse battery staple"
NOW = datetime(2026, 7, 19, tzinfo=UTC)


def _app(tmp_path: Path, role: Role = Role.PUBLISHER) -> FastAPI:
    url = f"sqlite:///{tmp_path / 'content.db'}"
    with create_storage(url) as storage:
        storage.save_user(
            User(username="ana", password_hash=hash_password(PASSWORD), role=role, created_at=NOW)
        )
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


def test_menu_items_add_update_and_delete(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        csrf = _sign_in(client)
        saved = client.post(
            "/menu",
            data={
                "csrf_token": csrf,
                "id": "docs",
                "url": "/docs/",
                "position": "1",
                "label_en": "Docs",
                "label_pt-pt": "Documentação",
            },
            follow_redirects=False,
        )
        assert saved.status_code == 303
        page = client.get("/menu").text
        assert "Documentação" in page
        bad = client.post(
            "/menu", data={"csrf_token": csrf, "id": "Bad Id!", "url": "/x/", "position": "1"}
        )
        assert bad.status_code == 422
        removed = client.post(
            "/menu/docs/delete", data={"csrf_token": csrf}, follow_redirects=False
        )
        assert removed.status_code == 303
        assert "No explicit items" in client.get("/menu").text


def test_menu_writes_need_the_publisher_role(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path, role=Role.EDITOR), base_url="https://testserver") as client:
        csrf = _sign_in(client)
        assert client.get("/menu").status_code == 200  # anyone signed in can look
        denied = client.post(
            "/menu", data={"csrf_token": csrf, "id": "x", "url": "/", "position": "1"}
        )
        assert denied.status_code == 403
