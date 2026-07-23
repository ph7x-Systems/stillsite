"""The Themes screen: discover, try, activate — never install (ADR-0048)."""

from datetime import UTC, datetime
from pathlib import Path

from cms_admin import AdminSettings, create_app
from cms_admin.security import hash_password
from cms_core import Role, User, create_storage
from fastapi import FastAPI
from fastapi.testclient import TestClient

PASSWORD = "correct horse battery staple"
NOW = datetime(2026, 7, 23, tzinfo=UTC)

PROJECT_TOML = """
[site]
name = "Aurora Cartography"
base_url = "https://example.com"
languages = ["pt-pt", "es", "fr", "de"]
theme = "default"

[storage]
url = "sqlite:///content.db"

[build]
output = "_site"
"""


def _app(tmp_path: Path, role: Role = Role.ADMIN) -> FastAPI:
    url = f"sqlite:///{tmp_path / 'content.db'}"
    (tmp_path / "sardine.toml").write_text(PROJECT_TOML, encoding="utf-8")
    with create_storage(url) as storage:
        storage.save_user(
            User(
                username="ana",
                password_hash=hash_password(PASSWORD),
                role=role,
                created_at=NOW,
            )
        )
    return create_app(
        AdminSettings(storage_url=url, media_dir=tmp_path / "media", project_dir=tmp_path)
    )


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


def test_themes_list_and_try_first_activation(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        csrf = _sign_in(client)

        page = client.get("/themes")
        assert page.status_code == 200
        assert "ph7x-reference" in page.text  # discovered from the entry point
        assert "Built-in" in page.text  # the default theme's package column

        done = client.post(
            "/themes/activate",
            data={"csrf_token": csrf, "name": "ph7x-reference"},
            follow_redirects=True,
        )
        assert done.status_code == 200
        assert "Activated ph7x-reference" in done.text
        config = (tmp_path / "sardine.toml").read_text(encoding="utf-8")
        assert 'theme = "ph7x-reference"' in config
        assert 'theme = "default"' not in config
        # Only the theme line moved; the rest of the file is untouched.
        assert 'name = "Aurora Cartography"' in config

        # The active badge follows the activation.
        page = client.get("/themes")
        assert "Active" in page.text


def test_activation_of_an_unknown_theme_leaves_config_untouched(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        csrf = _sign_in(client)
        failed = client.post(
            "/themes/activate",
            data={"csrf_token": csrf, "name": "no-such-theme"},
            follow_redirects=True,
        )
        assert failed.status_code == 200
        assert "Activation failed and the configuration was left untouched" in failed.text
        assert 'theme = "default"' in (tmp_path / "sardine.toml").read_text(encoding="utf-8")


def test_themes_screen_is_admin_only(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path, role=Role.PUBLISHER), base_url="https://testserver") as client:
        _sign_in(client)
        assert client.get("/themes").status_code == 403


def test_theme_cards_render_from_the_manifest(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        _sign_in(client)
        page = client.get("/themes")
        # Every card field comes from packaging metadata (ADR-0049).
        assert "dark editorial design system" in page.text
        assert "By pH7x Systems" in page.text
        assert "License: Apache-2.0" in page.text
        assert "Compatible with this installation" in page.text

        shot = client.get("/themes/screenshot/ph7x-reference.png")
        assert shot.status_code == 200
        assert shot.headers["content-type"] == "image/png"
        assert client.get("/themes/screenshot/default.png").status_code == 404
        assert client.get("/themes/screenshot/ph7x-reference.webp").status_code == 404
        assert client.get("/themes/screenshot/no-such.png").status_code == 404
