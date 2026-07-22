"""The Migration screen: the panel face of the WXR pipeline (ADR-0047)."""

from datetime import UTC, datetime
from pathlib import Path

from cms_admin import AdminSettings, create_app
from cms_admin.security import hash_password
from cms_core import Role, User, create_storage
from fastapi import FastAPI
from fastapi.testclient import TestClient

PASSWORD = "correct horse battery staple"
NOW = datetime(2026, 7, 22, tzinfo=UTC)

WXR = """<?xml version="1.0"?>
<rss xmlns:content="http://purl.org/rss/1.0/modules/content/"
     xmlns:dc="http://purl.org/dc/elements/1.1/"
     xmlns:wp="http://wordpress.org/export/1.2/">
  <channel>
  <item>
    <title>Panel launch</title>
    <link>https://old-site.test/2025/06/panel-launch/</link>
    <dc:creator><![CDATA[Old Desk]]></dc:creator>
    <content:encoded><![CDATA[<p>Body.</p>]]></content:encoded>
    <wp:post_id>21</wp:post_id><wp:post_name>panel-launch</wp:post_name>
    <wp:status>draft</wp:status><wp:post_type>post</wp:post_type>
  </item>
  <item>
    <title>Old page</title>
    <wp:post_id>22</wp:post_id><wp:post_type>page</wp:post_type>
  </item>
  </channel>
</rss>"""

PROJECT_TOML = """
[site]
name = "Aurora Cartography"
base_url = "https://example.com"
languages = ["pt-pt", "es", "fr", "de"]

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


def _inspect(client: TestClient, csrf: str) -> str:
    page = client.post(
        "/migration/inspect",
        data={"csrf_token": csrf},
        files={"export": ("blog.xml", WXR.encode(), "text/xml")},
    )
    assert page.status_code == 200, page.text
    return page.text.split('name="token" value="')[1].split('"')[0]


def test_migration_flow_inspects_runs_and_stays_idempotent(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        _run_flow(client, tmp_path)


def _run_flow(client: TestClient, tmp_path: Path) -> None:
    csrf = _sign_in(client)

    home = client.get("/migration")
    assert home.status_code == 200
    assert "Inspect the export" in home.text

    page = client.post(
        "/migration/inspect",
        data={"csrf_token": csrf},
        files={"export": ("blog.xml", WXR.encode(), "text/xml")},
    )
    assert page.status_code == 200
    assert "1 importable post(s) of 2 item(s)" in page.text
    assert "Old Desk" in page.text
    assert "pages are not migrated" in page.text  # nothing silently dropped
    token = page.text.split('name="token" value="')[1].split('"')[0]

    result = client.post(
        "/migration/run",
        data={
            "csrf_token": csrf,
            "token": token,
            "map_authors": "Old Desk = Newsroom",
        },
    )
    assert result.status_code == 200, result.text
    assert "1 new article(s) imported" in result.text
    assert "1 redirect(s) recorded" in result.text
    with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
        article = storage.load_article("panel-launch")
    assert article is not None
    assert article.author == "Newsroom"  # the mapping form reached the pipeline
    config = (tmp_path / "sardine.toml").read_text(encoding="utf-8")
    assert '"/2025/06/panel-launch/" = "/blog/panel-launch/"' in config

    # A second full pass never duplicates and leaves the config untouched.
    token = _inspect(client, csrf)
    rerun = client.post("/migration/run", data={"csrf_token": csrf, "token": token})
    assert rerun.status_code == 200
    assert "0 new article(s) imported" in rerun.text
    assert "1 already migrated, left untouched" in rerun.text
    assert (tmp_path / "sardine.toml").read_text(encoding="utf-8") == config

    # A consumed or expired token asks for the upload again.
    stale = client.post("/migration/run", data={"csrf_token": csrf, "token": token})
    assert stale.status_code == 410


def test_migration_screen_is_admin_only(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path, role=Role.PUBLISHER), base_url="https://testserver") as client:
        _sign_in(client)
        assert client.get("/migration").status_code == 403


def test_migration_rejects_a_malformed_export(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        csrf = _sign_in(client)
        bad = client.post(
            "/migration/inspect",
            data={"csrf_token": csrf},
            files={"export": ("blog.xml", b"<!DOCTYPE rss><rss/>", "text/xml")},
        )
        assert bad.status_code == 400
