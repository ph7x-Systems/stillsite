"""Bulk actions (#130): the same rules as single actions, many at once."""

from datetime import UTC, datetime
from pathlib import Path

from cms_admin import AdminSettings, create_app
from cms_admin.security import hash_password
from cms_core import ContentStatus, Language, MediaAsset, Role, User, create_storage
from cms_core.models import Article, ArticleContent, new_article
from cms_core.storage import StorageBackend
from fastapi import FastAPI
from fastapi.testclient import TestClient

PASSWORD = "correct horse battery staple"
NOW = datetime(2026, 7, 21, tzinfo=UTC)


def _app(tmp_path: Path, role: Role = Role.ADMIN, publish_gate: bool = False) -> FastAPI:
    url = f"sqlite:///{tmp_path / 'content.db'}"
    with create_storage(url) as storage:
        storage.save_user(
            User(
                username="ana",
                password_hash=hash_password(PASSWORD),
                role=role,
                created_at=NOW,
            )
        )
        for index in range(3):
            article = new_article(
                f"entry-{index}",
                ArticleContent(title=f"Entry {index}", summary="S", body_markdown="B"),
                now=NOW,
            )
            storage.save_article(article)
    return create_app(
        AdminSettings(storage_url=url, media_dir=tmp_path / "media", publish_gate=publish_gate)
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


def _article(storage: "StorageBackend", article_id: str) -> "Article":
    article = storage.load_article(article_id)
    assert article is not None
    return article


def _storage(tmp_path: Path) -> "StorageBackend":
    return create_storage(f"sqlite:///{tmp_path / 'content.db'}")


def test_bulk_transition_applies_to_every_selected(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        csrf = _sign_in(client)
        listing = client.get("/articles").text
        assert 'action="/articles/bulk"' in listing
        report = client.post(
            "/articles/bulk",
            data={
                "csrf_token": csrf,
                "action": "to-review",
                "selected": ["entry-0", "entry-2"],
            },
        ).text
    assert "2" in report and "ok" in report
    with _storage(tmp_path) as storage:
        assert _article(storage, "entry-0").status is ContentStatus.REVIEW
        assert _article(storage, "entry-1").status is ContentStatus.DRAFT
        assert _article(storage, "entry-2").status is ContentStatus.REVIEW


def test_bulk_reports_per_entry_without_aborting(tmp_path: Path) -> None:
    """One refused entry never stops the rest — mixed outcomes render."""
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        csrf = _sign_in(client)
        client.post(
            "/articles/bulk",
            data={"csrf_token": csrf, "action": "to-review", "selected": ["entry-0"]},
        )
        report = client.post(
            "/articles/bulk",
            data={
                "csrf_token": csrf,
                # entry-0 is in review: publish is valid; entry-1 is draft:
                # draft -> published is not a transition.
                "action": "publish",
                "selected": ["entry-0", "entry-1"],
            },
        ).text
    assert "invalid transition" in report
    with _storage(tmp_path) as storage:
        assert _article(storage, "entry-0").status is ContentStatus.PUBLISHED
        assert _article(storage, "entry-1").status is ContentStatus.DRAFT


def test_bulk_respects_roles_and_the_publish_gate(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path, role=Role.EDITOR), base_url="https://testserver") as client:
        csrf = _sign_in(client)
        client.post(
            "/articles/bulk",
            data={"csrf_token": csrf, "action": "to-review", "selected": ["entry-0"]},
        )
        report = client.post(
            "/articles/bulk",
            data={"csrf_token": csrf, "action": "publish", "selected": ["entry-0"]},
        ).text
    assert "requires the" in report  # editors cannot publish
    with _storage(tmp_path) as storage:
        assert _article(storage, "entry-0").status is ContentStatus.REVIEW


def test_bulk_gate_blocks_with_reason(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path, publish_gate=True), base_url="https://testserver") as client:
        csrf = _sign_in(client)
        client.post(
            "/articles/bulk",
            data={"csrf_token": csrf, "action": "to-review", "selected": ["entry-0"]},
        )
        report = client.post(
            "/articles/bulk",
            data={"csrf_token": csrf, "action": "publish", "selected": ["entry-0"]},
        ).text
    assert "publish gate" in report  # no translations exist


def test_bulk_trash_and_category(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        csrf = _sign_in(client)
        client.post(
            "/articles/bulk",
            data={
                "csrf_token": csrf,
                "action": "set-category",
                "category": "field-notes",
                "selected": ["entry-0", "entry-1"],
            },
        )
        client.post(
            "/articles/bulk",
            data={"csrf_token": csrf, "action": "trash", "selected": ["entry-2"]},
        )
    with _storage(tmp_path) as storage:
        assert _article(storage, "entry-0").category == "field-notes"
        assert _article(storage, "entry-2").deleted_at is not None


def test_bulk_media_delete_refuses_referenced(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path), base_url="https://testserver") as client:
        csrf = _sign_in(client)
        with _storage(tmp_path) as storage:
            storage.save_media_asset(
                MediaAsset(
                    id="loose",
                    path="images/loose.svg",
                    mime_type="image/svg+xml",
                    width=8,
                    height=8,
                    alt={Language.EN: "Loose"},
                )
            )
            storage.save_media_asset(
                MediaAsset(
                    id="used",
                    path="images/used.svg",
                    mime_type="image/svg+xml",
                    width=8,
                    height=8,
                    alt={Language.EN: "Used"},
                )
            )
            article = _article(storage, "entry-0")
            article.cover = "used"
            storage.save_article(article)
        report = client.post(
            "/media/bulk",
            data={"csrf_token": csrf, "action": "delete", "selected": ["loose", "used"]},
        ).text
    assert "referenced by" in report
    with _storage(tmp_path) as storage:
        assert storage.load_media_asset("loose") is None
        assert storage.load_media_asset("used") is not None
