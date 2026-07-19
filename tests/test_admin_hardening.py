"""Hardening (Milestone 3 phase 9): headers on every response, no scripts.

The admin ships zero JavaScript, so the CSP allows no script source at all;
the template sources are scanned to keep it that way, and the ADMIN_GUIDE
env-var table is checked against the settings code by the docs suite.
"""

from datetime import UTC, datetime
from pathlib import Path

from cms_admin import AdminSettings, create_app
from cms_admin.app import SECURITY_HEADERS
from cms_admin.security import hash_password
from cms_core import Role, User, create_storage
from fastapi import FastAPI
from fastapi.testclient import TestClient

PASSWORD = "correct horse battery staple"
NOW = datetime(2026, 7, 18, tzinfo=UTC)

TEMPLATES = Path("apps/admin/src/cms_admin/templates")


def _app(tmp_path: Path) -> FastAPI:
    url = f"sqlite:///{tmp_path / 'content.db'}"
    with create_storage(url) as storage:
        storage.save_user(
            User(
                username="ana",
                password_hash=hash_password(PASSWORD),
                role=Role.ADMIN,
                created_at=NOW,
            )
        )
    return create_app(AdminSettings(storage_url=url, media_dir=tmp_path / "media"))


def test_every_response_carries_the_security_headers(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        for path in ("/login", "/", "/static/admin.css", "/definitely-missing"):
            response = client.get(path, follow_redirects=False)
            for name, value in SECURITY_HEADERS.items():
                assert response.headers.get(name) == value, (path, name)


def test_the_csp_allows_no_scripts_anywhere() -> None:
    csp = SECURITY_HEADERS["Content-Security-Policy"]
    assert "default-src 'none'" in csp
    assert "script-src" not in csp  # no script source, not even 'self'
    assert "unsafe-inline" not in csp
    assert "frame-ancestors 'none'" in csp
    assert SECURITY_HEADERS["X-Frame-Options"] == "DENY"


def test_admin_templates_ship_no_scripts_and_no_inline_styles() -> None:
    for template in TEMPLATES.glob("*.j2"):
        text = template.read_text(encoding="utf-8")
        assert "<script" not in text, template.name
        assert "style=" not in text, template.name
        assert "onclick" not in text, template.name


def test_login_page_renders_under_the_policy(tmp_path: Path) -> None:
    """The page's every asset is same-origin: what the CSP allows."""
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        page = client.get("/login").text
    assert 'href="/static/admin.css"' in page
    assert "http://" not in page.split("<body>")[0]  # no external head resources
    assert "https://" not in page.split("<body>")[0]
