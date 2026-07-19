"""Admin media library: validated uploads, alt editing, safe delete.

The MIME type comes from the bytes (magic numbers), never the client;
dimensions are parsed without external dependencies; EN alt is mandatory;
referenced assets refuse to die.
"""

import struct
import zlib
from datetime import UTC, datetime
from pathlib import Path

from cms_admin import AdminSettings, create_app
from cms_admin.media import image_size, sniff_mime
from cms_admin.security import hash_password
from cms_core import (
    ArticleContent,
    Language,
    MediaAsset,
    Role,
    User,
    create_storage,
    new_article,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient

PASSWORD = "correct horse battery staple"
NOW = datetime(2026, 7, 18, tzinfo=UTC)


def _png(width: int = 3, height: int = 2) -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload))
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = zlib.compress(b"\x00" + b"\x00" * (3 * width) * height)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", raw) + chunk(b"IEND", b"")


def _app(tmp_path: Path, *assets: MediaAsset, with_cover: bool = False) -> FastAPI:
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
        for asset in assets:
            storage.save_media_asset(asset)
        if with_cover:
            article = new_article("cover-user", ArticleContent(title="Covered"), now=NOW)
            article.cover = assets[0].id
            storage.save_article(article)
    return create_app(AdminSettings(storage_url=url, media_dir=tmp_path / "media"))


def _asset(asset_id: str = "tin-photo") -> MediaAsset:
    return MediaAsset(
        id=asset_id,
        path=f"{asset_id}.png",
        mime_type="image/png",
        width=3,
        height=2,
        alt={Language.EN: "A tin, heroic"},
    )


def _sign_in(client: TestClient) -> str:
    form = client.get("/login")
    client.post(
        "/login",
        data={
            "username": "ana",
            "password": PASSWORD,
            "login_csrf": form.cookies["sardine_login_csrf"],
        },
    )
    dashboard: str = client.get("/").text
    return dashboard.split('name="csrf_token" value="')[1].split('"')[0]


def _client(app: FastAPI) -> TestClient:
    return TestClient(app, base_url="https://testserver")


def test_sniffing_reads_magic_numbers_not_names() -> None:
    assert sniff_mime(_png()) == "image/png"
    assert sniff_mime(b"GIF89a" + b"\x00" * 10) == "image/gif"
    assert sniff_mime(b'<svg xmlns="http://www.w3.org/2000/svg"></svg>') == "image/svg+xml"
    assert sniff_mime(b"#!/bin/sh\nrm -rf /") is None
    assert sniff_mime(b"MZ\x90\x00") is None


def test_image_size_parses_png_gif_svg() -> None:
    assert image_size(_png(7, 5), "image/png") == (7, 5)
    gif = b"GIF89a" + struct.pack("<HH", 12, 34) + b"\x00" * 10
    assert image_size(gif, "image/gif") == (12, 34)
    svg = b'<svg xmlns="x" width="640" height="480"></svg>'
    assert image_size(svg, "image/svg+xml") == (640, 480)


def test_upload_persists_the_asset_and_the_file(tmp_path: Path) -> None:
    app = _app(tmp_path)
    with _client(app) as client:
        csrf = _sign_in(client)
        response = client.post(
            "/media",
            data={"csrf_token": csrf, "id": "hero-shot", "alt": "The tin at dawn"},
            files={"upload": ("anything.bin", _png(3, 2), "application/octet-stream")},
            follow_redirects=False,
        )
        assert response.status_code == 303, response.text
        editor = client.get("/media/hero-shot").text
        served = client.get("/media-files/hero-shot.png")
    assert "The tin at dawn" in editor
    assert "3×2" in editor  # noqa: RUF001 — the editor renders width×height
    assert served.status_code == 200
    assert (tmp_path / "media" / "hero-shot.png").is_file()
    with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
        stored = storage.load_media_asset("hero-shot")
    assert stored is not None
    assert stored.mime_type == "image/png"  # sniffed, despite the .bin name
    assert (stored.width, stored.height) == (3, 2)


def test_upload_rejects_unsupported_bytes_and_missing_alt(tmp_path: Path) -> None:
    app = _app(tmp_path)
    with _client(app) as client:
        csrf = _sign_in(client)
        bad = client.post(
            "/media",
            data={"csrf_token": csrf, "id": "nasty", "alt": "x"},
            files={"upload": ("virus.png", b"#!/bin/sh\necho boo", "image/png")},
        )
        assert bad.status_code == 422
        assert "unsupported type" in bad.text
        no_alt = client.post(
            "/media",
            data={"csrf_token": csrf, "id": "quiet", "alt": "  "},
            files={"upload": ("ok.png", _png(), "image/png")},
        )
    assert no_alt.status_code == 422
    assert "alt" in no_alt.text
    assert not (tmp_path / "media" / "nasty.png").exists()


def test_upload_enforces_the_size_limit(tmp_path: Path) -> None:
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
    app = create_app(
        AdminSettings(storage_url=url, media_dir=tmp_path / "media", upload_max_bytes=64)
    )
    with _client(app) as client:
        csrf = _sign_in(client)
        response = client.post(
            "/media",
            data={"csrf_token": csrf, "id": "huge", "alt": "big"},
            files={"upload": ("big.png", _png(40, 40), "image/png")},
        )
    assert response.status_code == 422
    assert "limit" in response.text


def test_alt_translations_save_and_report_completeness(tmp_path: Path) -> None:
    app = _app(tmp_path, _asset())
    with _client(app) as client:
        csrf = _sign_in(client)
        listing = client.get("/media").text
        assert "admin-state-missing" in listing  # no translated alt yet
        response = client.post(
            "/media/tin-photo",
            data={
                "csrf_token": csrf,
                "alt_en": "A tin, heroic",
                "alt_pt-pt": "Uma lata, heroica",
                "alt_es": "Una lata, heroica",
                "alt_fr": "Une boîte, héroïque",
                "alt_de": "Eine Dose, heldenhaft",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        listing = client.get("/media").text
    assert "admin-state-complete" in listing
    with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
        stored = storage.load_media_asset("tin-photo")
    assert stored is not None
    assert stored.missing_alt_languages() == ()


def test_clearing_the_en_alt_is_refused(tmp_path: Path) -> None:
    app = _app(tmp_path, _asset())
    with _client(app) as client:
        csrf = _sign_in(client)
        response = client.post("/media/tin-photo", data={"csrf_token": csrf, "alt_en": "   "})
    assert response.status_code == 422
    assert "mandatory" in response.text


def test_referenced_assets_refuse_deletion(tmp_path: Path) -> None:
    app = _app(tmp_path, _asset(), with_cover=True)
    with _client(app) as client:
        csrf = _sign_in(client)
        editor = client.get("/media/tin-photo").text
        assert "cover-user" in editor  # the reference is listed
        refused = client.post("/media/tin-photo/delete", data={"csrf_token": csrf})
        assert refused.status_code == 422
        assert "in use" in refused.text
    with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
        assert storage.load_media_asset("tin-photo") is not None


def test_unreferenced_assets_delete_with_their_file(tmp_path: Path) -> None:
    app = _app(tmp_path, _asset())
    (tmp_path / "media").mkdir()
    (tmp_path / "media" / "tin-photo.png").write_bytes(_png())
    with _client(app) as client:
        csrf = _sign_in(client)
        response = client.post(
            "/media/tin-photo/delete", data={"csrf_token": csrf}, follow_redirects=False
        )
        assert response.status_code == 303
    assert not (tmp_path / "media" / "tin-photo.png").exists()
    with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
        assert storage.load_media_asset("tin-photo") is None
