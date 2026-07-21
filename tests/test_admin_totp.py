"""Two-factor authentication (ADR-0035): enrolment, sign-in, replay."""

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cms_admin import AdminSettings, create_app
from cms_admin.security import hash_password
from cms_admin.totp import code_for_step, current_step, generate_secret
from cms_core import Role, User, create_storage
from fastapi import FastAPI
from fastapi.testclient import TestClient

PASSWORD = "correct horse battery staple"
NOW = datetime(2026, 7, 21, tzinfo=UTC)


def _app(tmp_path: Path, *, totp_secret: str | None = None) -> FastAPI:
    url = f"sqlite:///{tmp_path / 'content.db'}"
    with create_storage(url) as storage:
        storage.save_user(
            User(
                username="ana",
                password_hash=hash_password(PASSWORD),
                role=Role.ADMIN,
                created_at=NOW,
                totp_secret=totp_secret,
            )
        )
    return create_app(AdminSettings(storage_url=url, media_dir=tmp_path / "media"))


def _login(client: TestClient, *, totp: str | None = None) -> Any:
    client.get("/login")
    csrf = client.cookies["__Host-sardine_login_csrf"]
    data = {"username": "ana", "password": PASSWORD, "login_csrf": csrf}
    if totp is not None:
        data["totp"] = totp
    return client.post("/login", data=data, follow_redirects=False)


def _now_code(secret: str) -> str:
    return code_for_step(secret, current_step(datetime.now(UTC)))


def test_account_without_totp_signs_in_exactly_as_before(tmp_path: Path) -> None:
    app = _app(tmp_path)
    with TestClient(app, base_url="https://testserver") as client:
        assert _login(client).status_code == 303


def test_valid_password_alone_never_opens_a_totp_account(tmp_path: Path) -> None:
    secret = generate_secret()
    app = _app(tmp_path, totp_secret=secret)
    with TestClient(app, base_url="https://testserver") as client:
        missing = _login(client)
        assert missing.status_code == 401
        assert 'name="totp"' in missing.text  # the code field appears
        wrong = _login(client, totp="000000")
        assert wrong.status_code == 401
        good = _login(client, totp=_now_code(secret))
        assert good.status_code == 303


def test_a_code_is_single_use(tmp_path: Path) -> None:
    secret = generate_secret()
    app = _app(tmp_path, totp_secret=secret)
    code = _now_code(secret)
    with TestClient(app, base_url="https://testserver") as client:
        assert _login(client, totp=code).status_code == 303
    with TestClient(app, base_url="https://testserver") as client:
        replay = _login(client, totp=code)
        assert replay.status_code == 401  # accepted step persisted; replay refused


def test_enrolment_requires_a_valid_confirmation_code(tmp_path: Path) -> None:
    app = _app(tmp_path)
    with TestClient(app, base_url="https://testserver") as client:
        _login(client)
        page = client.get("/profile/2fa").text
        assert "otpauth://" in page
        secret = re.search(r"<code>([A-Z2-7]{32})</code>", page).group(1)  # type: ignore[union-attr]
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)  # type: ignore[union-attr]
        refused = client.post(
            "/profile/2fa/enable",
            data={"csrf_token": csrf, "secret": secret, "code": "000000"},
        )
        assert refused.status_code == 422
        accepted = client.post(
            "/profile/2fa/enable",
            data={"csrf_token": csrf, "secret": secret, "code": _now_code(secret)},
            follow_redirects=False,
        )
        assert accepted.status_code == 303
        assert "enabled" in client.get("/profile/2fa").text

    with create_storage(app.state.settings.storage_url) as storage:
        user = storage.load_user("ana")
    assert user is not None and user.totp_secret == secret


def test_disable_requires_a_valid_current_code(tmp_path: Path) -> None:
    secret = generate_secret()
    app = _app(tmp_path, totp_secret=secret)
    with TestClient(app, base_url="https://testserver") as client:
        _login(client, totp=_now_code(secret))
        page = client.get("/profile/2fa").text
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)  # type: ignore[union-attr]
        refused = client.post("/profile/2fa/disable", data={"csrf_token": csrf, "code": "000000"})
        assert refused.status_code == 422
        # the sign-in consumed the current step; the next step disables
        next_code = code_for_step(secret, current_step(datetime.now(UTC)) + 1)
        done = client.post(
            "/profile/2fa/disable",
            data={"csrf_token": csrf, "code": next_code},
            follow_redirects=False,
        )
        assert done.status_code == 303

    with create_storage(app.state.settings.storage_url) as storage:
        user = storage.load_user("ana")
    assert user is not None and user.totp_secret is None and user.totp_step is None


def test_wrong_codes_spend_the_login_budget(tmp_path: Path) -> None:
    secret = generate_secret()
    app = _app(tmp_path, totp_secret=secret)
    with TestClient(app, base_url="https://testserver") as client:
        statuses = []
        for _ in range(12):
            answer = _login(client, totp="000000")
            statuses.append(answer.status_code)
            if answer.status_code == 429:
                break
    assert 429 in statuses


def _policy_app(tmp_path: Path, role: Role, *, totp_secret: str | None = None) -> FastAPI:
    url = f"sqlite:///{tmp_path / 'content.db'}"
    with create_storage(url) as storage:
        storage.save_user(
            User(
                username="ana",
                password_hash=hash_password(PASSWORD),
                role=role,
                created_at=NOW,
                totp_secret=totp_secret,
            )
        )
    return create_app(
        AdminSettings(storage_url=url, media_dir=tmp_path / "media", require_2fa_role=Role.ADMIN)
    )


def test_policy_corrals_a_covered_account_until_enrolment(tmp_path: Path) -> None:
    app = _policy_app(tmp_path, Role.ADMIN)
    with TestClient(app, base_url="https://testserver") as client:
        assert _login(client).status_code == 303  # credentials still work
        corral = client.get("/", follow_redirects=False)
        assert corral.status_code == 303
        assert corral.headers["location"] == "/profile/2fa"
        articles = client.get("/articles", follow_redirects=False)
        assert articles.headers["location"] == "/profile/2fa"
        page = client.get("/profile/2fa")
        assert page.status_code == 200
        assert "required for your role" in page.text
        secret = re.search(r"<code>([A-Z2-7]{32})</code>", page.text).group(1)  # type: ignore[union-attr]
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)  # type: ignore[union-attr]
        done = client.post(
            "/profile/2fa/enable",
            data={"csrf_token": csrf, "secret": secret, "code": _now_code(secret)},
            follow_redirects=False,
        )
        assert done.status_code == 303
        assert client.get("/", follow_redirects=False).status_code == 200  # free again


def test_policy_leaves_lower_roles_alone(tmp_path: Path) -> None:
    app = _policy_app(tmp_path, Role.EDITOR)
    with TestClient(app, base_url="https://testserver") as client:
        _login(client)
        assert client.get("/", follow_redirects=False).status_code == 200


def test_disable_is_refused_while_the_policy_covers_the_account(tmp_path: Path) -> None:
    secret = generate_secret()
    app = _policy_app(tmp_path, Role.ADMIN, totp_secret=secret)
    with TestClient(app, base_url="https://testserver") as client:
        _login(client, totp=_now_code(secret))
        page = client.get("/profile/2fa").text
        assert "cannot be disabled" in page
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)  # type: ignore[union-attr]
        next_code = code_for_step(secret, current_step(datetime.now(UTC)) + 1)
        refused = client.post("/profile/2fa/disable", data={"csrf_token": csrf, "code": next_code})
        assert refused.status_code == 403


def test_unknown_policy_value_fails_startup() -> None:
    import os

    from cms_admin.settings import AdminSettings as Settings

    os.environ["SARDINE_ADMIN_REQUIRE_2FA"] = "supervisor"
    try:
        Settings.from_env()
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert "supervisor" in str(error)
    finally:
        del os.environ["SARDINE_ADMIN_REQUIRE_2FA"]
