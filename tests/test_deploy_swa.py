"""#156 slice 2: the Azure Static Web Apps provider, mock-verified.

The mock endpoint implements the transport contract (authenticated
upload, status polling) so every failure mode runs in CI: rejected
tokens, endpoint rejection, timeouts, negative health — and the rule
above all of them: a failure never touches the previously published
version, and the token never appears anywhere.
"""

import http.server
import json
import socketserver
import threading
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar

import pytest
from cms_admin import AdminSettings, create_app
from cms_admin.security import hash_password
from cms_build.deploy import SwaDeployer
from cms_core import Role, User, create_storage
from cms_core.models import ArticleContent, new_article
from fastapi import FastAPI
from fastapi.testclient import TestClient

PASSWORD = "correct horse battery staple"
NOW = datetime(2026, 7, 21, tzinfo=UTC)
TOKEN = "swa-test-token-9c1f4b"


class MockSwa(http.server.BaseHTTPRequestHandler):
    """One knob (`mode`) selects the scenario; uploads are recorded."""

    mode: ClassVar[str] = "ok"
    uploads: ClassVar[list[int]] = []
    polls: ClassVar[int] = 0

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            self.send_response(401)
            self.end_headers()
            return
        MockSwa.uploads.append(len(body))
        if MockSwa.mode == "reject-upload":
            self.send_response(500)
            self.end_headers()
            return
        self.send_response(202)
        self.send_header("Location", f"http://{self.headers['Host']}/status")
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status": "running"}')

    def do_GET(self) -> None:
        if self.path == "/site":
            healthy = MockSwa.mode != "unhealthy"
            self.send_response(200 if healthy else 503)
            self.end_headers()
            if healthy:
                self.wfile.write(b"live")
            return
        MockSwa.polls += 1
        outcome = {
            "ok": "succeeded",
            "unhealthy": "succeeded",
            "reject-status": "failed",
            "hang": "running",
        }.get(MockSwa.mode, "succeeded")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": outcome}).encode())

    def log_message(self, *args: object) -> None:  # silence
        return


@pytest.fixture
def mock_swa() -> "Iterator[str]":
    server = socketserver.TCPServer(("127.0.0.1", 0), MockSwa)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    MockSwa.mode = "ok"
    MockSwa.uploads = []
    MockSwa.polls = 0
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def _app(tmp_path: Path, endpoint: str, timeout: int = 30) -> FastAPI:
    (tmp_path / "sardine.toml").write_text(
        '[site]\nname = "Live"\nbase_url = "https://live.example"\nlanguages = []\n'
        "\n[deploy]\n"
        'provider = "swa"\n'
        f'root = "{tmp_path / "store"}"\n'
        f'deploy_url = "{endpoint}/deploy"\n'
        f'health_url = "{endpoint}/site"\n'
        f"timeout = {timeout}\n",
        encoding="utf-8",
    )
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
        article = new_article(
            "launch",
            ArticleContent(title="Launch note", summary="S", body_markdown="B"),
            now=NOW,
        )
        storage.save_article(article)
    return create_app(
        AdminSettings(
            storage_url=url,
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


def _publish(client: TestClient, csrf: str) -> None:
    for target in ("review", "published"):
        client.post(
            "/articles/launch/status",
            data={"csrf_token": csrf, "to": target},
            follow_redirects=False,
        )


def test_publish_uploads_and_activates(
    tmp_path: Path, mock_swa: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SARDINE_SWA_DEPLOY_TOKEN", TOKEN)
    with TestClient(_app(tmp_path, mock_swa), base_url="https://testserver") as client:
        csrf = _sign_in(client)
        _publish(client, csrf)
        panel = client.get("/publishing").text
        activity = client.get("/activity").text
        assert MockSwa.uploads, "the release never reached the endpoint"
        assert "Publish site now" in panel  # active state
        assert "deployed" in activity
        # the token never leaks: panel, audit, provider state
        state = (tmp_path / "store" / "state.json").read_text(encoding="utf-8")
        for surface in (panel, activity, state):
            assert TOKEN not in surface

        # unpublish uploads again (the site without the entry)
        upload_count = len(MockSwa.uploads)
        response = client.post(
            "/articles/launch/status",
            data={"csrf_token": csrf, "to": "draft"},
            follow_redirects=False,
        )
        assert response.status_code == 303
    assert len(MockSwa.uploads) > upload_count


def test_rejected_token_fails_without_touching_the_site(
    tmp_path: Path, mock_swa: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SARDINE_SWA_DEPLOY_TOKEN", "the-wrong-token")
    with TestClient(_app(tmp_path, mock_swa), base_url="https://testserver") as client:
        csrf = _sign_in(client)
        _publish(client, csrf)
        panel = client.get("/publishing").text
    assert "deployment token rejected" in panel
    assert "Retry deployment" in panel
    assert "the-wrong-token" not in panel


def test_missing_token_is_actionable(
    tmp_path: Path, mock_swa: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SARDINE_SWA_DEPLOY_TOKEN", raising=False)
    with TestClient(_app(tmp_path, mock_swa), base_url="https://testserver") as client:
        csrf = _sign_in(client)
        _publish(client, csrf)
        panel = client.get("/publishing").text
    assert "SARDINE_SWA_DEPLOY_TOKEN" in panel  # the fix is named, no secret shown


def test_endpoint_rejection_and_retry(
    tmp_path: Path, mock_swa: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SARDINE_SWA_DEPLOY_TOKEN", TOKEN)
    MockSwa.mode = "reject-status"
    with TestClient(_app(tmp_path, mock_swa), base_url="https://testserver") as client:
        csrf = _sign_in(client)
        _publish(client, csrf)
        panel = client.get("/publishing").text
        assert "rejected the deployment" in panel and "Retry deployment" in panel
        # fix the endpoint and retry from the panel button
        MockSwa.mode = "ok"
        client.post("/publishing/deploy", data={"csrf_token": csrf}, follow_redirects=False)
        panel = client.get("/publishing").text
    assert "Publish site now" in panel  # active again


def test_timeout_fails_cleanly(
    tmp_path: Path, mock_swa: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SARDINE_SWA_DEPLOY_TOKEN", TOKEN)
    monkeypatch.setattr("cms_build.deploy.POLL_INTERVAL_SECONDS", 0.05)
    MockSwa.mode = "hang"
    with TestClient(_app(tmp_path, mock_swa, timeout=5), base_url="https://testserver") as client:
        csrf = _sign_in(client)
        _publish(client, csrf)
        panel = client.get("/publishing").text
    assert "timed out" in panel and "Retry deployment" in panel


def test_negative_health_reports_previous_still_live(
    tmp_path: Path, mock_swa: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SARDINE_SWA_DEPLOY_TOKEN", TOKEN)
    MockSwa.mode = "unhealthy"
    with TestClient(_app(tmp_path, mock_swa), base_url="https://testserver") as client:
        csrf = _sign_in(client)
        _publish(client, csrf)
        panel = client.get("/publishing").text
    assert "previous publication remains live" in panel


def test_concurrent_deploys_are_serialized(tmp_path: Path, mock_swa: str) -> None:
    deployer = SwaDeployer(tmp_path / "store", deploy_url=f"{mock_swa}/deploy")
    deployer._store._acquire_lock()
    try:
        from cms_build.deploy import DeployLocked

        with pytest.raises(DeployLocked):
            deployer.deploy({"sitemap.xml": b"<urlset/>"}, digest="d" * 16, actor="ana")
    finally:
        deployer._store._release_lock()


def test_rollback_reuploads_a_kept_release(
    tmp_path: Path, mock_swa: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SARDINE_SWA_DEPLOY_TOKEN", TOKEN)
    deployer = SwaDeployer(
        tmp_path / "store", deploy_url=f"{mock_swa}/deploy", health_url=f"{mock_swa}/site"
    )
    first = deployer.deploy(
        {"sitemap.xml": b"<urlset/>", "index.html": b"v1"}, digest="a" * 16, actor="ana"
    )
    deployer.deploy(
        {"sitemap.xml": b"<urlset/>", "index.html": b"v2"}, digest="b" * 16, actor="ana"
    )
    uploads_before = len(MockSwa.uploads)
    state = deployer.rollback(first.release_id, actor="maria")
    assert state.status == "active" and state.release_id == first.release_id
    assert len(MockSwa.uploads) == uploads_before + 1  # re-sent, not rebuilt
