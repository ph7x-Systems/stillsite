"""First-run setup (#128): from an empty instance to a working site.

The E2E drives the real HTTP surface: an instance with zero accounts
lands every visitor on /setup; submitting creates the admin, writes the
project file, optionally seeds, signs in, and shows the first-steps
checklist. A configured instance never exposes the wizard again.
"""

import tomllib
from datetime import UTC, datetime
from pathlib import Path

from cms_admin import AdminSettings, create_app
from cms_admin.security import hash_password
from cms_core import Role, User, create_storage
from fastapi import FastAPI
from fastapi.testclient import TestClient

PASSWORD = "a sardine in space wins"


def _app(tmp_path: Path) -> FastAPI:
    return create_app(
        AdminSettings(
            storage_url=f"sqlite:///{tmp_path / 'content.db'}",
            media_dir=tmp_path / "media",
            project_dir=tmp_path,
        )
    )


def _setup_payload(client: TestClient, **overrides: str) -> dict[str, str]:
    page = client.get("/setup")
    csrf = page.text.split('name="setup_csrf" value="')[1].split('"')[0]
    payload: dict[str, str] = {
        "setup_csrf": csrf,
        "username": "dona",
        "password": PASSWORD,
        "password_repeat": PASSWORD,
        "site_name": "A Loja",
        "base_url": "https://loja.example",
        "source_language": "pt-pt",
        "theme": "default",
    }
    payload.update(overrides)
    return payload


def test_an_empty_instance_lands_everyone_on_setup(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 303  # -> /login
        login = client.get("/login", follow_redirects=False)
        assert login.status_code == 303
        assert login.headers["location"] == "/setup"
        wizard = client.get("/setup")
        assert "setup_csrf" in wizard.text


def test_setup_creates_admin_project_and_signs_in(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        response = client.post("/setup", data=_setup_payload(client), follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/"
        dashboard = client.get("/").text
    # the admin account exists with the admin role — never a lesser one
    with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
        user = storage.load_user("dona")
    assert user is not None and user.role is Role.ADMIN
    # the project file carries the chosen identity
    config = tomllib.loads((tmp_path / "sardine.toml").read_text(encoding="utf-8"))
    assert config["site"]["name"] == "A Loja"
    assert config["site"]["source_language"] == "pt-pt"
    assert config["site"]["languages"] == []
    # signed in, on the dashboard, with the first-steps checklist
    assert "/pages/new" in dashboard


def test_setup_can_seed_the_example_site(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        response = client.post(
            "/setup",
            data=_setup_payload(client, seed_example="on", source_language="en"),
            follow_redirects=False,
        )
        assert response.status_code == 303
    with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
        assert storage.list_page_ids()  # the example site is there
        assert storage.list_article_ids()


def test_setup_validates_and_keeps_the_form(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        response = client.post(
            "/setup",
            data=_setup_payload(client, password_repeat="different but long enough"),
        )
        assert response.status_code == 422
        assert 'value="dona"' in response.text  # the form survives
        # nothing was created
        setup_again = client.get("/setup")
        assert setup_again.status_code == 200


def test_a_configured_instance_never_exposes_setup(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'content.db'}"
    with create_storage(url) as storage:
        storage.save_user(
            User(
                username="ana",
                password_hash=hash_password(PASSWORD),
                role=Role.ADMIN,
                created_at=datetime.now(tz=UTC),
            )
        )
    app = create_app(AdminSettings(storage_url=url, media_dir=tmp_path / "media"))
    with TestClient(app, base_url="https://testserver") as client:
        response = client.get("/setup", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/login"
        blocked = client.post(
            "/setup",
            data={"setup_csrf": "x", "username": "intruder", "password": PASSWORD},
            follow_redirects=False,
        )
        assert blocked.status_code == 303  # never processed


def test_an_existing_project_file_is_never_rewritten(tmp_path: Path) -> None:
    original = '[site]\nname = "Kept"\nbase_url = "https://kept.example"\n'
    (tmp_path / "sardine.toml").write_text(original, encoding="utf-8")
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        response = client.post("/setup", data=_setup_payload(client), follow_redirects=False)
        assert response.status_code == 303
    assert (tmp_path / "sardine.toml").read_text(encoding="utf-8") == original


def test_build_persists_the_chosen_target_and_reports_next_steps(tmp_path: Path) -> None:
    """#128 slice 2: the deployment choice is remembered in the project
    and the success feedback says where the files are and what to do."""
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        client.post(
            "/setup",
            data=_setup_payload(client, source_language="en"),
            follow_redirects=False,
        )
        csrf = client.get("/").text.split('name="csrf_token" value="')[1].split('"')[0]
        panel = client.get("/publishing").text
        assert "Where will the site live?" in panel
        response = client.post(
            "/publishing/build",
            data={"csrf_token": csrf, "target": "swa"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        after = client.get("/publishing").text
    assert "ready to go live" in after
    assert "SWA CLI" in after
    config = tomllib.loads((tmp_path / "sardine.toml").read_text(encoding="utf-8"))
    assert config["build"]["target"] == "swa"
    assert (tmp_path / "_site" / "staticwebapp.config.json").is_file()


def test_build_defaults_to_the_projects_configured_target(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        client.post(
            "/setup",
            data=_setup_payload(client, source_language="en"),
            follow_redirects=False,
        )
        existing = (tmp_path / "sardine.toml").read_text(encoding="utf-8")
        (tmp_path / "sardine.toml").write_text(
            existing + '\n[build]\ntarget = "nginx"\n', encoding="utf-8"
        )
        csrf = client.get("/").text.split('name="csrf_token" value="')[1].split('"')[0]
        response = client.post(
            "/publishing/build", data={"csrf_token": csrf}, follow_redirects=False
        )
        assert response.status_code == 303
        after = client.get("/publishing").text
    assert "nginx.conf" in after
