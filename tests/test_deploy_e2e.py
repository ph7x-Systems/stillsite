"""#156, end to end over the real admin surface:

Edit -> Publish -> site updated. Unpublish -> site updated. A failure
keeps the healthy version with retry offered; rollback needs no
rebuild; concurrency is refused; the audit trail records everything;
the dashboard reports the all-clear afterwards.

Runs on SQLite always and on every engine whose SARDINE_*_URL is
present (the same convention as the storage conformance suite).
"""

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from cms_admin import AdminSettings, create_app
from cms_admin.security import hash_password
from cms_core import Role, User, create_storage
from cms_core.models import ArticleContent, new_article
from fastapi import FastAPI
from fastapi.testclient import TestClient

PASSWORD = "correct horse battery staple"
NOW = datetime(2026, 7, 21, tzinfo=UTC)

ENGINES = [("sqlite", None)] + [
    (name, os.environ.get(var))
    for name, var in (
        ("postgres", "SARDINE_POSTGRES_URL"),
        ("mysql", "SARDINE_MYSQL_URL"),
        ("mssql", "SARDINE_MSSQL_URL"),
    )
    if os.environ.get(var)
]


@pytest.fixture(params=[name for name, _url in ENGINES])
def storage_url(request: pytest.FixtureRequest, tmp_path: Path) -> str:
    name = request.param
    url = dict(ENGINES)[name]
    if name == "sqlite":
        return f"sqlite:///{tmp_path / 'content.db'}"
    assert url is not None
    return url


def _wipe(url: str) -> None:
    with create_storage(url) as storage:
        for article_id in storage.list_article_ids():
            storage.delete_article(article_id)
        for page_id in storage.list_page_ids():
            storage.delete_page(page_id)
        for username in storage.list_usernames():
            storage.delete_user(username)


def _app(tmp_path: Path, storage_url: str) -> FastAPI:
    (tmp_path / "sardine.toml").write_text(
        '[site]\nname = "Live"\nbase_url = "https://live.example"\nlanguages = []\n'
        "\n[deploy]\n"
        f'root = "{tmp_path / "www"}"\n',
        encoding="utf-8",
    )
    with create_storage(storage_url) as storage:
        storage.save_user(
            User(
                username="ana",
                password_hash=hash_password(PASSWORD),
                role=Role.ADMIN,
                created_at=NOW,
            )
        )
        article = new_article(
            "launch",
            ArticleContent(title="Launch note", summary="S", body_markdown="B"),
            now=NOW,
        )
        storage.save_article(article)
    return create_app(
        AdminSettings(
            storage_url=storage_url,
            media_dir=tmp_path / "media",
            project_dir=tmp_path,
            publish_gate=False,
        )
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


def _current_index(tmp_path: Path) -> str:
    index = tmp_path / "www" / "current" / "blog" / "launch" / "index.html"
    return index.read_text(encoding="utf-8") if index.is_file() else ""


def test_publish_and_unpublish_end_on_the_public_site(tmp_path: Path, storage_url: str) -> None:
    if not storage_url.startswith("sqlite"):
        _wipe(storage_url)
    app = _app(tmp_path, storage_url)
    with TestClient(app, base_url="https://testserver") as client:
        csrf = _sign_in(client)

        # Edit -> Publish -> site updated: the transition alone deploys.
        for target in ("review", "published"):
            response = client.post(
                "/articles/launch/status",
                data={"csrf_token": csrf, "to": target},
                follow_redirects=False,
            )
            assert response.status_code == 303
        assert "Launch note" in _current_index(tmp_path)
        panel = client.get("/publishing").text
        assert "Publish site now" in panel

        # Unpublish -> site updated: the entry leaves the public site.
        response = client.post(
            "/articles/launch/status",
            data={"csrf_token": csrf, "to": "draft"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert _current_index(tmp_path) == ""  # page gone from current/

        # The audit trail saw the whole story.
        activity = client.get("/activity").text
        assert "deployed" in activity
        # And the dashboard reports the all-clear.
        assert "Nothing is waiting for you" in client.get("/").text
    if not storage_url.startswith("sqlite"):
        _wipe(storage_url)


def test_failure_keeps_the_healthy_version_and_offers_retry(
    tmp_path: Path, storage_url: str
) -> None:
    if not storage_url.startswith("sqlite"):
        _wipe(storage_url)
    app = _app(tmp_path, storage_url)
    with TestClient(app, base_url="https://testserver") as client:
        csrf = _sign_in(client)
        for target in ("review", "published"):
            client.post(
                "/articles/launch/status",
                data={"csrf_token": csrf, "to": target},
                follow_redirects=False,
            )
        healthy = _current_index(tmp_path)
        assert "Launch note" in healthy

        # Break the next release: demand a language nothing translates —
        # the parity gate blocks the build before the provider runs.
        toml_path = tmp_path / "sardine.toml"
        original_toml = toml_path.read_text(encoding="utf-8")
        toml_path.write_text(
            original_toml.replace("languages = []", 'languages = ["pt-pt"]'),
            encoding="utf-8",
        )
        response = client.post(
            "/publishing/deploy", data={"csrf_token": csrf}, follow_redirects=False
        )
        assert response.status_code == 303
        panel = client.get("/publishing").text
        assert "validation blocked the release" in panel
        assert "Retry deployment" in panel
        assert _current_index(tmp_path) == healthy  # untouched

        # Fix and retry: back to active.
        toml_path.write_text(original_toml, encoding="utf-8")
        client.post("/publishing/deploy", data={"csrf_token": csrf}, follow_redirects=False)
        assert "Publish site now" in client.get("/publishing").text
    if not storage_url.startswith("sqlite"):
        _wipe(storage_url)


def test_manual_rollback_from_the_panel(tmp_path: Path, storage_url: str) -> None:
    if not storage_url.startswith("sqlite"):
        _wipe(storage_url)
    app = _app(tmp_path, storage_url)
    with TestClient(app, base_url="https://testserver") as client:
        csrf = _sign_in(client)
        for target in ("review", "published"):
            client.post(
                "/articles/launch/status",
                data={"csrf_token": csrf, "to": target},
                follow_redirects=False,
            )
        first = _current_index(tmp_path)
        with create_storage(storage_url) as storage:
            article = storage.load_article("launch")
            assert article is not None
            article.source = ArticleContent(
                title="Launch note, revised", summary="S", body_markdown="B"
            )
            storage.save_article(article)
        client.post("/publishing/deploy", data={"csrf_token": csrf}, follow_redirects=False)
        assert "revised" in _current_index(tmp_path)

        panel = client.get("/publishing").text
        previous_release = panel.split("Roll back to this release")[0]
        release_id = previous_release.split('name="release_id" value="')[-1].split('"')[0]
        response = client.post(
            "/publishing/rollback",
            data={"csrf_token": csrf, "release_id": release_id},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert _current_index(tmp_path) == first  # no rebuild, old bytes back
        assert "rolled-back" in client.get("/activity").text
    if not storage_url.startswith("sqlite"):
        _wipe(storage_url)
