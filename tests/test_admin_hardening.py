"""Hardening (Milestone 3 phase 9; scripts per ADR-0020): headers on every
response, and every script strictly same-origin.

The admin serves its own vendored scripts (ADR-0020), so the CSP allows
exactly `script-src 'self'` — never inline, never external. The template
sources are scanned to keep it that way, and the ADMIN_GUIDE env-var table
is checked against the settings code by the docs suite.
"""

import re
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


def test_the_csp_allows_only_same_origin_scripts() -> None:
    csp = SECURITY_HEADERS["Content-Security-Policy"]
    assert "default-src 'none'" in csp
    # ADR-0020: vendored scripts only — and never inline ones.
    assert "script-src 'self';" in csp
    assert "script-src 'self' 'unsafe-inline'" not in csp
    assert "unsafe-eval" not in csp
    # ADR-0027 phase 2: autosave POSTs only to this admin origin.
    assert "connect-src 'self';" in csp
    # ADR-0023: runtime style *attributes* only (CodeMirror, Popper);
    # templates themselves stay attribute-free (test below).
    assert "style-src 'self' 'unsafe-inline'" in csp
    assert "frame-ancestors 'none'" in csp
    assert SECURITY_HEADERS["X-Frame-Options"] == "DENY"


def test_admin_templates_ship_no_inline_scripts_or_styles() -> None:
    """Script tags must load local files and carry no inline body."""
    for template in TEMPLATES.glob("*.j2"):
        text = template.read_text(encoding="utf-8")
        for tag in re.finditer(r"<script([^>]*)>(.*?)</script>", text, re.DOTALL):
            attrs, body = tag.groups()
            assert re.search(r'src="/static/', attrs), template.name
            assert body.strip() == "", template.name
        assert "style=" not in text, template.name
        assert "onclick" not in text, template.name


def test_login_page_renders_under_the_policy(tmp_path: Path) -> None:
    """The page's every asset is same-origin: what the CSP allows."""
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        page = client.get("/login").text
    assert 'href="/static/admin.css"' in page
    assert "http://" not in page.split("<body>")[0]  # no external head resources
    assert "https://" not in page.split("<body>")[0]


def test_preview_mount_allows_same_origin_framing_only(tmp_path: Path) -> None:
    """ADR-0027: the editor frames /preview/; the admin itself never frames."""
    (tmp_path / "media").mkdir()
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        admin = client.get("/login")
        anonymous = client.get("/preview/anything/", follow_redirects=False)
        csrf = admin.cookies["__Host-sardine_login_csrf"]
        client.post(
            "/login",
            data={"username": "ana", "password": PASSWORD, "login_csrf": csrf},
        )
        preview = client.get("/preview/anything/", follow_redirects=False)
        media = client.get("/media-files/private.png", follow_redirects=False)
    assert "frame-ancestors 'none'" in admin.headers["Content-Security-Policy"]
    assert admin.headers["X-Frame-Options"] == "DENY"
    assert anonymous.status_code == 303
    assert anonymous.headers["location"] == "/login"
    assert preview.status_code == 404
    assert media.status_code == 404
    assert "frame-ancestors 'self'" in preview.headers["Content-Security-Policy"]
    assert preview.headers["X-Frame-Options"] == "SAMEORIGIN"
