"""Authentication and access control (SECURITY_STRATEGY M3 gates).

Covers the authn/authz suite, CSRF protection and failed-login rate
limiting over the real login flow — no mocked internals.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cms_admin import AdminSettings, create_app
from cms_admin.security import hash_password, token_digest
from cms_core import Role, User
from cms_core.storage import create_storage
from fastapi import FastAPI
from fastapi.testclient import TestClient

PASSWORD = "correct horse battery staple"


def _app(tmp_path: Path, **users: Role) -> FastAPI:
    url = f"sqlite:///{tmp_path / 'content.db'}"
    with create_storage(url) as storage:
        for username, role in users.items():
            storage.save_user(
                User(
                    username=username,
                    password_hash=hash_password(PASSWORD),
                    role=role,
                    created_at=datetime.now(UTC),
                )
            )
    return create_app(AdminSettings(storage_url=url))


def _client(app: FastAPI) -> TestClient:
    # https base URL so the client sends Secure cookies.
    return TestClient(app, base_url="https://testserver")


def _login(client: TestClient, username: str = "ana", password: str = PASSWORD) -> object:
    form = client.get("/login")
    csrf = form.cookies[  # the double-submit value equals the cookie by construction
        "sardine_login_csrf"
    ]
    return client.post(
        "/login",
        data={"username": username, "password": password, "login_csrf": csrf},
        follow_redirects=False,
    )


def test_anonymous_requests_are_redirected_to_login(tmp_path: Path) -> None:
    with _client(_app(tmp_path)) as client:
        response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_login_sets_a_session_and_opens_the_dashboard(tmp_path: Path) -> None:
    with _client(_app(tmp_path, ana=Role.EDITOR)) as client:
        response = _login(client)
        assert response.status_code == 303  # type: ignore[attr-defined]
        cookie = response.headers["set-cookie"]  # type: ignore[attr-defined]
        assert "HttpOnly" in cookie and "SameSite=strict" in cookie.lower().replace(
            "samesite=strict", "SameSite=strict"
        )
        dashboard = client.get("/")
        assert dashboard.status_code == 200
        assert "ana" in dashboard.text


def test_wrong_password_fails_and_rate_limits_after_five_attempts(tmp_path: Path) -> None:
    with _client(_app(tmp_path, ana=Role.EDITOR)) as client:
        for _ in range(5):
            response = _login(client, password="wrong")
            assert response.status_code == 401  # type: ignore[attr-defined]
        blocked = _login(client, password="wrong")
        assert blocked.status_code == 429  # type: ignore[attr-defined]
        # The right password is also blocked while the window lasts.
        assert _login(client).status_code == 429  # type: ignore[attr-defined]


def test_login_without_matching_csrf_cookie_is_rejected(tmp_path: Path) -> None:
    with _client(_app(tmp_path, ana=Role.EDITOR)) as client:
        client.get("/login")
        response = client.post(
            "/login",
            data={"username": "ana", "password": PASSWORD, "login_csrf": "forged"},
            follow_redirects=False,
        )
    assert response.status_code == 403


def test_logout_requires_the_session_csrf_token(tmp_path: Path) -> None:
    with _client(_app(tmp_path, ana=Role.EDITOR)) as client:
        _login(client)
        forged = client.post("/logout", data={"csrf_token": "forged"}, follow_redirects=False)
        assert forged.status_code == 403
        csrf = client.get("/").text.split('name="csrf_token" value="')[1].split('"')[0]
        response = client.post("/logout", data={"csrf_token": csrf}, follow_redirects=False)
        assert response.status_code == 303
        assert client.get("/", follow_redirects=False).status_code == 303


def test_expired_sessions_are_rejected(tmp_path: Path) -> None:
    app = _app(tmp_path, ana=Role.EDITOR)
    with _client(app) as client:
        _login(client)
        token = client.cookies["sardine_session"]
        settings: AdminSettings = app.state.settings
        with create_storage(settings.storage_url) as storage:
            session = storage.load_session(token_digest(token))
            assert session is not None
            storage.save_session(
                session.model_copy(update={"expires_at": datetime.now(UTC) - timedelta(hours=1)})
            )
        assert client.get("/", follow_redirects=False).status_code == 303


def test_roles_form_a_least_privilege_ladder(tmp_path: Path) -> None:
    from cms_admin.auth import ROLE_ORDER

    assert ROLE_ORDER == (Role.EDITOR, Role.REVIEWER, Role.PUBLISHER, Role.ADMIN)


@pytest.mark.parametrize(
    ("role", "expected"), [(Role.EDITOR, 403), (Role.PUBLISHER, 200), (Role.ADMIN, 200)]
)
def test_role_enforcement_on_a_protected_route(tmp_path: Path, role: Role, expected: int) -> None:
    from cms_admin.auth import require_at_least
    from fastapi import Depends

    app = _app(tmp_path, ana=role)

    @app.get("/publish-probe")
    async def probe(
        user: User = Depends(require_at_least(Role.PUBLISHER)),  # noqa: B008
    ) -> dict[str, str]:
        return {"user": user.username}

    with _client(app) as client:
        _login(client)
        assert client.get("/publish-probe").status_code == expected
