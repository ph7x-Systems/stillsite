"""Password reset (ADR-0032): enumeration-safe, single-use, revoking.

Real flows over HTTP with a captured mailer — no SMTP server involved.
"""

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from cms_admin import AdminSettings, create_app
from cms_admin.mail import Mailer
from cms_admin.security import hash_password, token_digest
from cms_core import AdminSession, Language, PasswordReset, Role, User, create_storage
from fastapi import FastAPI
from fastapi.testclient import TestClient

PASSWORD = "correct horse battery staple"
NOW = datetime(2026, 7, 21, tzinfo=UTC)


class CapturingMailer:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str]] = []

    def send(self, to: str, subject: str, body: str) -> None:
        self.sent.append((to, subject, body))


def _app(tmp_path: Path, *, email: str | None = "ana@example.com") -> FastAPI:
    url = f"sqlite:///{tmp_path / 'content.db'}"
    with create_storage(url) as storage:
        storage.save_user(
            User(
                username="ana",
                password_hash=hash_password(PASSWORD),
                role=Role.ADMIN,
                created_at=NOW,
                language=Language.PT_PT,
                email=email,
            )
        )
    app = create_app(AdminSettings(storage_url=url, media_dir=tmp_path / "media"))
    app.state.mailer = CapturingMailer()
    return app


def _request_reset(client: TestClient, username: str) -> Any:
    page = client.get("/reset")
    csrf = client.cookies["__Host-sardine_login_csrf"]
    assert page.status_code == 200
    return client.post("/reset", data={"username": username, "login_csrf": csrf})


def _wait_for_mail(app: FastAPI, count: int = 1) -> None:
    """Delivery is fire-and-forget in a thread; give it a moment."""
    import time

    for _ in range(200):
        if len(app.state.mailer.sent) >= count:
            return
        time.sleep(0.01)
    raise AssertionError("mail never arrived")


def test_mailer_parses_smtp_urls() -> None:
    mailer = Mailer.from_settings("smtp://user:p%40ss@mail.example:2525", "cms@example.com")
    assert mailer is not None
    assert (mailer.host, mailer.port, mailer.implicit_tls) == ("mail.example", 2525, False)
    assert mailer.password == "p@ss"
    implicit = Mailer.from_settings("smtps://mail.example", "cms@example.com")
    assert implicit is not None and implicit.port == 465 and implicit.implicit_tls
    assert Mailer.from_settings(None, "cms@example.com") is None
    assert Mailer.from_settings("smtp://mail.example", None) is None
    try:
        Mailer.from_settings("https://mail.example", "cms@example.com")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_reset_is_hidden_when_email_is_off(tmp_path: Path) -> None:
    app = _app(tmp_path)
    app.state.mailer = None
    with TestClient(app, base_url="https://testserver") as client:
        assert "/reset" not in client.get("/login").text
        assert client.get("/reset").status_code == 404
        assert client.get("/reset/some-token").status_code == 404


def test_known_and_unknown_accounts_get_the_same_answer(tmp_path: Path) -> None:
    app = _app(tmp_path)
    with TestClient(app, base_url="https://testserver") as client:
        assert "/reset" in client.get("/login").text
        known = _request_reset(client, "ana")
        unknown = _request_reset(client, "nobody")
        assert known.status_code == unknown.status_code == 200
        assert known.text == unknown.text  # byte-identical: nothing to enumerate
        _wait_for_mail(app)
    assert len(app.state.mailer.sent) == 1  # only the real account got mail


def test_reset_round_trip_changes_password_and_revokes_sessions(tmp_path: Path) -> None:
    app = _app(tmp_path)
    with TestClient(app, base_url="https://testserver") as client:
        _request_reset(client, "ana")
        _wait_for_mail(app)
        to, subject, body = app.state.mailer.sent[0]
        assert to == "ana@example.com"
        assert "Sardine CMS" in subject
        # the user's stored language drives the message (PT-PT)
        assert "palavra-passe" in body
        match = re.search(r"https://testserver(/reset/[A-Za-z0-9_-]+)", body)
        assert match, body
        link = match.group(1)

        # a live session that must die with the reset
        storage_url = app.state.settings.storage_url
        with create_storage(storage_url) as storage:
            storage.save_session(
                AdminSession(
                    token_hash="old-session",
                    username="ana",
                    csrf_token="csrf",
                    expires_at=NOW + timedelta(days=1),
                )
            )

        form = client.get(link)
        assert form.status_code == 200
        csrf = client.cookies["__Host-sardine_login_csrf"]
        short = client.post(
            link,
            data={"password": "short", "password_repeat": "short", "login_csrf": csrf},
        )
        assert short.status_code == 422
        done = client.post(
            link,
            data={
                "password": "a-brand-new-password",
                "password_repeat": "a-brand-new-password",
                "login_csrf": csrf,
            },
        )
        assert done.status_code == 200

        # the token is single-use
        again = client.post(
            link,
            data={
                "password": "another-new-password",
                "password_repeat": "another-new-password",
                "login_csrf": client.cookies["__Host-sardine_login_csrf"],
            },
        )
        assert again.status_code == 422
        assert "no longer valid" in again.text

    from cms_admin.security import verify_password

    with create_storage(storage_url) as storage:
        user = storage.load_user("ana")
        assert user is not None
        assert verify_password(user.password_hash, "a-brand-new-password")
        assert storage.load_session("old-session") is None  # revoked


def test_expired_tokens_are_refused(tmp_path: Path) -> None:
    app = _app(tmp_path)
    with TestClient(app, base_url="https://testserver") as client:
        storage_url = app.state.settings.storage_url
        with create_storage(storage_url) as storage:
            storage.save_password_reset(
                PasswordReset(
                    token_hash=token_digest("stale-token"),
                    username="ana",
                    expires_at=datetime.now(UTC) - timedelta(minutes=1),
                )
            )
        client.get("/reset/stale-token")
        csrf = client.cookies["__Host-sardine_login_csrf"]
        refused = client.post(
            "/reset/stale-token",
            data={
                "password": "a-brand-new-password",
                "password_repeat": "a-brand-new-password",
                "login_csrf": csrf,
            },
        )
    assert refused.status_code == 422
    assert "no longer valid" in refused.text


def test_reset_requests_share_the_login_budget(tmp_path: Path) -> None:
    app = _app(tmp_path)
    with TestClient(app, base_url="https://testserver") as client:
        responses = []
        for _ in range(12):
            page = client.get("/reset")
            if page.status_code == 429:
                responses.append(429)
                break
            csrf = client.cookies["__Host-sardine_login_csrf"]
            answer = client.post("/reset", data={"username": "nobody", "login_csrf": csrf})
            responses.append(answer.status_code)
    assert 429 in responses  # the shared limiter eventually closes the door


def test_extension_mail_transport_carries_the_reset(tmp_path: Path) -> None:
    """ADR-0032: transports are pluggable — a non-smtp name resolves to an
    activated extension's sender (where passwordless provider APIs live)."""
    import test_extensions

    (tmp_path / "sardine.toml").write_text(
        'extensions = ["test_extensions:extension"]\n'
        '[site]\nname = "T"\nbase_url = "https://t.example"\nlanguages = []\n',
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
                email="ana@example.com",
            )
        )
    test_extensions.CAUGHT_MAIL.clear()
    app = create_app(
        AdminSettings(
            storage_url=url,
            media_dir=tmp_path / "media",
            project_dir=tmp_path,
            mail_transport="fishmail",
        )
    )
    with TestClient(app, base_url="https://testserver") as client:
        _request_reset(client, "ana")
        import time

        for _ in range(200):
            if test_extensions.CAUGHT_MAIL:
                break
            time.sleep(0.01)
    assert test_extensions.CAUGHT_MAIL and test_extensions.CAUGHT_MAIL[0][0] == "ana@example.com"


def test_unknown_mail_transport_fails_startup(tmp_path: Path) -> None:
    (tmp_path / "sardine.toml").write_text(
        '[site]\nname = "T"\nbase_url = "https://t.example"\nlanguages = []\n',
        encoding="utf-8",
    )
    try:
        create_app(
            AdminSettings(
                storage_url=f"sqlite:///{tmp_path / 'content.db'}",
                media_dir=tmp_path / "media",
                project_dir=tmp_path,
                mail_transport="ghost",
            )
        )
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert "ghost" in str(error)
