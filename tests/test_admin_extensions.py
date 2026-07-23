"""The Extensions screen (ADR-0050): discovery, transactional
activation, capabilities after load, recovery without imports."""

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


def _app(tmp_path: Path, toml: str = PROJECT_TOML) -> FastAPI:
    url = f"sqlite:///{tmp_path / 'content.db'}"
    (tmp_path / "sardine.toml").write_text(toml, encoding="utf-8")
    with create_storage(url) as storage:
        storage.save_user(
            User(
                username="ana",
                password_hash=hash_password(PASSWORD),
                role=Role.ADMIN,
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


def test_activation_is_transactional_and_capabilities_come_from_the_load(
    tmp_path: Path,
) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        csrf = _sign_in(client)

        page = client.get("/extensions")
        assert page.status_code == 200
        assert "No extensions are installed or active." in page.text

        done = client.post(
            "/extensions/activate",
            data={"csrf_token": csrf, "name": "fixture_extension:extension"},
            follow_redirects=True,
        )
        assert done.status_code == 200
        assert "Extension activated" in done.text
        config = (tmp_path / "sardine.toml").read_text(encoding="utf-8")
        assert 'extensions = ["fixture_extension:extension"]' in config

        # Capabilities render only from the loaded Extension object.
        page = client.get("/extensions")
        assert "section kinds: fixture-hero" in page.text

        # A broken extension never reaches the configuration.
        failed = client.post(
            "/extensions/activate",
            data={"csrf_token": csrf, "name": "fixture_broken_extension:extension"},
            follow_redirects=True,
        )
        assert "Activation failed and the configuration was left untouched" in failed.text
        assert "fixture_broken_extension" not in (tmp_path / "sardine.toml").read_text(
            encoding="utf-8"
        )


def test_a_broken_active_extension_is_contained_and_deactivates_without_import(
    tmp_path: Path,
) -> None:
    toml = 'extensions = ["fixture_broken_extension:extension"]\n' + PROJECT_TOML
    with TestClient(_app(tmp_path, toml=toml), base_url="https://testserver") as client:
        csrf = _sign_in(client)

        # The panel stays up; the card shows the failure.
        page = client.get("/extensions")
        assert page.status_code == 200
        assert "This extension fails to load" in page.text
        assert "deliberately broken" in page.text

        # Recovery operates on configuration alone — no import happens.
        done = client.post(
            "/extensions/deactivate",
            data={"csrf_token": csrf, "name": "fixture_broken_extension:extension"},
            follow_redirects=True,
        )
        assert done.status_code == 200
        assert "Extension deactivated" in done.text
        assert "fixture_broken_extension" not in (tmp_path / "sardine.toml").read_text(
            encoding="utf-8"
        )


def test_health_runs_on_demand_and_contains_raising_checks(tmp_path: Path) -> None:
    toml = (
        'extensions = ["fixture_extension:extension", "fixture_extension:noisy"]\n' + PROJECT_TOML
    )
    with TestClient(_app(tmp_path, toml=toml), base_url="https://testserver") as client:
        csrf = _sign_in(client)

        # Health never runs unrequested.
        page = client.get("/extensions")
        assert "storage reachable" not in page.text
        assert "Check health" in page.text

        checked = client.post(
            "/extensions/health",
            data={"csrf_token": csrf, "name": "fixture_extension:extension"},
        )
        assert checked.status_code == 200
        assert "storage reachable" in checked.text
        assert "fixture store answers" in checked.text
        assert "connection refused" in checked.text  # a failed check, shown

        # A raising health check is a failed check, never a crash (ADR-0051).
        contained = client.post(
            "/extensions/health",
            data={"csrf_token": csrf, "name": "fixture_extension:noisy"},
        )
        assert contained.status_code == 200
        assert "health probe exploded" in contained.text


def test_settings_validate_before_persisting_and_show_provenance(tmp_path: Path) -> None:
    toml = 'extensions = ["fixture_extension:extension"]\n' + PROJECT_TOML
    with TestClient(_app(tmp_path, toml=toml), base_url="https://testserver") as client:
        csrf = _sign_in(client)

        page = client.get("/extensions/settings/fixture_extension:extension")
        assert page.status_code == 200
        assert "Source: schema default" in page.text
        assert "Environment variable FIXTURE_API_KEY is missing" in page.text
        after_key = page.text.split("FIXTURE_API_KEY")[1][:200]
        assert "value=" not in after_key  # presence only, never the value

        # Invalid input: nothing persists.
        bad = client.post(
            "/extensions/settings/fixture_extension:extension",
            data={"csrf_token": csrf, "region": "mars", "retries": "many"},
        )
        assert bad.status_code == 200
        assert "Nothing was saved" in bad.text
        assert "extension_settings" not in (tmp_path / "sardine.toml").read_text(encoding="utf-8")

        # Valid input persists surgically with the schema version.
        ok = client.post(
            "/extensions/settings/fixture_extension:extension",
            data={"csrf_token": csrf, "region": "us", "retries": "5"},
            follow_redirects=True,
        )
        assert ok.status_code == 200
        assert "Settings saved" in ok.text
        config = (tmp_path / "sardine.toml").read_text(encoding="utf-8")
        assert "[extension_settings.fixture_extension:extension]" in config.replace('"', "")
        assert "schema_version = 2" in config
        assert 'region = "us"' in config
        assert "retries = 5" in config
        assert (
            "Source: configured for this project"
            in client.get("/extensions/settings/fixture_extension:extension").text
        )


def test_settings_migrate_and_reach_configure_at_load(tmp_path: Path) -> None:
    import fixture_extension

    fixture_extension.received.clear()
    toml = (
        'extensions = ["fixture_extension:extension"]\n'
        + PROJECT_TOML
        + '\n[extension_settings."fixture_extension:extension"]\n'
        + "schema_version = 1\n"
        + 'zone = "us"\n'
    )
    with TestClient(_app(tmp_path, toml=toml), base_url="https://testserver") as client:
        _sign_in(client)
        client.get("/extensions")  # loads the extension, applying settings
    assert fixture_extension.received, "configure() was never called"
    resolved = fixture_extension.received[-1]
    # v1 "zone" migrated to v2 "region"; defaults filled the rest.
    assert resolved["region"] == "us"
    assert resolved["retries"] == 3
