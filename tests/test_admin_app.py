"""Admin application skeleton: factory, settings, storage wiring."""

from pathlib import Path

import pytest
from cms_admin import AdminSettings, create_app
from cms_admin.settings import DEFAULT_STORAGE_URL
from cms_core.storage import MIGRATIONS
from fastapi.testclient import TestClient


def _settings(tmp_path: Path) -> AdminSettings:
    return AdminSettings(storage_url=f"sqlite:///{tmp_path / 'content.db'}")


def test_health_reports_the_migrated_schema_version(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "schema_version": len(MIGRATIONS)}


def test_storage_opens_on_startup_and_closes_on_shutdown(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    with TestClient(app):
        assert not app.state.db.closed
    assert app.state.db.closed


def test_settings_come_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STILLSITE_STORAGE_URL", raising=False)
    assert AdminSettings.from_env().storage_url == DEFAULT_STORAGE_URL
    monkeypatch.setenv("STILLSITE_STORAGE_URL", "sqlite:///elsewhere.db")
    assert AdminSettings.from_env().storage_url == "sqlite:///elsewhere.db"


def test_api_docs_pages_are_disabled(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/redoc").status_code == 404
