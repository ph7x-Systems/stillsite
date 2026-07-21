"""External preview links (ADR-0042): signed, expiring, revocable —
and nothing more than one entry's rendering."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from cms_admin import AdminSettings, create_app
from cms_admin.preview_links import sign_token, verify_token
from cms_admin.security import hash_password
from cms_core import (
    ArticleContent,
    Role,
    User,
    create_storage,
    new_article,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient

PASSWORD = "correct horse battery staple"
NOW = datetime(2026, 7, 22, tzinfo=UTC)


def test_tokens_verify_clock_independently() -> None:
    """Signature and expiry are pure functions of the injected clock."""
    key = b"k" * 32
    expiry = datetime(2026, 8, 1, tzinfo=UTC)
    token = sign_token(key, "article", "launch", "lnk1", expiry)
    before = datetime(2026, 7, 31, tzinfo=UTC)
    after = datetime(2026, 8, 2, tzinfo=UTC)
    assert verify_token(key, "article", "launch", token, before) == "lnk1"
    assert verify_token(key, "article", "launch", token, after) is None  # expired
    assert verify_token(key, "article", "other", token, before) is None  # wrong entry
    assert verify_token(b"x" * 32, "article", "launch", token, before) is None  # wrong key
    forged = token[:-1] + ("0" if token[-1] != "0" else "1")
    assert verify_token(key, "article", "launch", forged, before) is None  # tampered
    stamped = token.split(".")
    tampered_expiry = f"{stamped[0]}.9999999999.{stamped[2]}"
    assert verify_token(key, "article", "launch", tampered_expiry, after) is None


def _app(tmp_path: Path) -> FastAPI:
    (tmp_path / "sardine.toml").write_text(
        '[site]\nname = "S"\nbase_url = "https://s.example"\nlanguages = ["pt-pt"]\n',
        encoding="utf-8",
    )
    url = f"sqlite:///{tmp_path / 'content.db'}"
    with create_storage(url) as storage:
        storage.save_user(
            User(
                username="ana",
                password_hash=hash_password(PASSWORD),
                role=Role.EDITOR,
                created_at=NOW,
            )
        )
        draft = new_article(
            "launch", ArticleContent(title="Launch note", summary="S", body_markdown="B"), now=NOW
        )
        from cms_core import Language

        draft.set_translation(
            Language.PT_PT,
            ArticleContent(title="Nota de lancamento", summary="R", body_markdown="C"),
        )
        storage.save_article(draft)
        other = new_article("secret", ArticleContent(title="Sibling secret"), now=NOW)
        storage.save_article(other)
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


def test_the_full_life_of_a_preview_link(tmp_path: Path) -> None:
    """Create in the editor, visit without a session, revoke, refused —
    with the publication state untouched throughout."""
    app = _app(tmp_path)
    with TestClient(app, base_url="https://testserver") as client:
        csrf = _sign_in(client)
        response = client.post(
            "/articles/launch/preview-links",
            data={"csrf_token": csrf, "days": "7"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        editor = client.get("/articles/launch").text
        assert "/shared/article/launch/" in editor
        share_url = next(
            v.split('"')[0]
            for v in editor.split('value="')[1:]
            if v.startswith("/shared/article/launch/")
        )

        # an anonymous browser (no session cookies, same running app)
        anonymous = TestClient(app, base_url="https://testserver")
        page = anonymous.get(share_url)
        assert page.status_code == 200
        assert "Launch note" in page.text
        assert "sardine-preview-banner" in page.text
        assert "Draft preview" in page.text
        localized = anonymous.get(share_url, params={"lang": "pt-pt"})
        assert "rascunho" in localized.text  # banner speaks the viewer's language
        # minimal scope: a token for one entry opens nothing else
        crossed = anonymous.get(share_url.replace("/launch/", "/secret/"))
        assert crossed.status_code == 404

        # publication state never changed
        with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
            stored = storage.load_article("launch")
            assert stored is not None and stored.status.value == "draft"
            link_id = storage.list_preview_links("article", "launch")[0].id

        # revoke: the same link refuses afterwards
        response = client.post(
            f"/preview-links/{link_id}/revoke",
            data={"csrf_token": csrf},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert TestClient(app, base_url="https://testserver").get(share_url).status_code == 404

        # audit carries the link id, never the token
        with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
            records = storage.list_activity(limit=10)
        actions = {record.action for record in records}
        assert "preview-link-created" in actions and "preview-link-revoked" in actions
        assert not any(share_url.rsplit("/", 1)[-1] in record.detail for record in records)


def test_expired_links_refuse(tmp_path: Path) -> None:
    from cms_core import PreviewLink

    app = _app(tmp_path)
    url = f"sqlite:///{tmp_path / 'content.db'}"
    with TestClient(app, base_url="https://testserver") as client:
        _sign_in(client)
        with create_storage(url) as storage:
            expired = PreviewLink(
                id="expiredlink00000",
                entry_kind="article",
                entry_id="launch",
                created_at=datetime.now(tz=UTC) - timedelta(days=10),
                expires_at=datetime.now(tz=UTC) - timedelta(days=3),
            )
            storage.save_preview_link(expired)
            key = bytes.fromhex(
                storage.get_or_create_secret("preview-link-signing-key", lambda: "00" * 32)
            )
        token = sign_token(key, "article", "launch", "expiredlink00000", expired.expires_at)
        assert client.get(f"/shared/article/launch/{token}").status_code == 404
