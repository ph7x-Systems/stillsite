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
            "login_csrf": form.cookies["__Host-sardine_login_csrf"],
        },
    )
    dashboard: str = client.get("/").text
    return dashboard.split('name="csrf_token" value="')[1].split('"')[0]


def _client(app: FastAPI) -> TestClient:
    return TestClient(app, base_url="https://testserver")


def test_sniffing_reads_magic_numbers_not_names() -> None:
    assert sniff_mime(_png()) == "image/png"
    assert sniff_mime(b"GIF89a" + b"\x00" * 10) == "image/gif"
    assert sniff_mime(b'<svg xmlns="http://www.w3.org/2000/svg"></svg>') is None
    assert sniff_mime(b"#!/bin/sh\nrm -rf /") is None
    assert sniff_mime(b"MZ\x90\x00") is None


def test_image_size_parses_png_and_gif() -> None:
    assert image_size(_png(7, 5), "image/png") == (7, 5)
    gif = b"GIF89a" + struct.pack("<HH", 12, 34) + b"\x00" * 10
    assert image_size(gif, "image/gif") == (12, 34)


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
    assert "3×2" in editor  # noqa: RUF001
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


def test_upload_rejects_active_svg_and_excessive_dimensions(tmp_path: Path) -> None:
    app = _app(tmp_path)
    oversized = bytearray(_png())
    oversized[16:24] = struct.pack(">II", 100_000, 100_000)
    with _client(app) as client:
        csrf = _sign_in(client)
        svg = client.post(
            "/media",
            data={"csrf_token": csrf, "id": "active", "alt": "active"},
            files={"upload": ("active.svg", b"<svg><script>alert(1)</script></svg>")},
        )
        huge = client.post(
            "/media",
            data={"csrf_token": csrf, "id": "huge-pixels", "alt": "huge"},
            files={"upload": ("huge.png", bytes(oversized))},
        )
    assert svg.status_code == 422
    assert "unsupported type" in svg.text
    assert huge.status_code == 422
    assert "pixel limit" in huge.text


def test_upload_never_replaces_an_existing_file(tmp_path: Path) -> None:
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    existing = media_dir / "collision.png"
    existing.write_bytes(b"owner-data")
    app = _app(tmp_path)
    with _client(app) as client:
        csrf = _sign_in(client)
        response = client.post(
            "/media",
            data={"csrf_token": csrf, "id": "collision", "alt": "collision"},
            files={"upload": ("collision.png", _png())},
        )
    assert response.status_code == 422
    assert "already exists" in response.text
    assert existing.read_bytes() == b"owner-data"


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


def test_media_filters_search_and_views(tmp_path: Path) -> None:
    """M5: the library filters server-side — text search and quick views."""
    app = _app(tmp_path)
    with TestClient(app, base_url="https://testserver") as client:
        _sign_in(client)
        csrf = client.get("/").text.split('name="csrf_token" value="')[1].split('"')[0]
        for asset_id, alt, size in (
            ("tin-rocket", "A tin rocket", 4),
            ("sea-chart", "A sea chart", 6),  # distinct bytes: identical content is refused
        ):
            client.post(
                "/media",
                data={"csrf_token": csrf, "id": asset_id, "alt": alt},
                files={"upload": (f"{asset_id}.png", _png(size, size))},
            )
        everything = client.get("/media").text
        assert "tin-rocket" in everything and "sea-chart" in everything
        searched = client.get("/media", params={"q": "rocket"}).text
        assert "tin-rocket" in searched
        assert 'href="/media/sea-chart"' not in searched
        assert "1" in searched  # shown-of-total counter
        missing = client.get("/media", params={"show": "missing-alt"}).text
        assert "tin-rocket" in missing  # translations still missing
        none = client.get("/media", params={"q": "nothing-here"}).text
        assert "Nothing matches the filter." in none


def test_duplicate_content_is_refused_naming_the_existing_asset(tmp_path: Path) -> None:
    app = _app(tmp_path)
    with _client(app) as client:
        csrf = _sign_in(client)
        first = client.post(
            "/media",
            data={"csrf_token": csrf, "id": "original", "alt": "The tin"},
            files={"upload": ("a.png", _png(3, 2), "image/png")},
            follow_redirects=False,
        )
        assert first.status_code == 303
        again = client.post(
            "/media",
            data={"csrf_token": csrf, "id": "copycat", "alt": "The tin again"},
            files={"upload": ("b.png", _png(3, 2), "image/png")},
            follow_redirects=False,
        )
    assert again.status_code == 422
    assert "identical content already exists" in again.text
    assert "original" in again.text  # the message names where the bytes live
    with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
        assert storage.load_media_asset("copycat") is None


def test_collection_persists_filters_and_edits(tmp_path: Path) -> None:
    app = _app(tmp_path)
    with _client(app) as client:
        csrf = _sign_in(client)
        client.post(
            "/media",
            data={"csrf_token": csrf, "id": "press-logo", "alt": "Logo", "collection": "press"},
            files={"upload": ("a.png", _png(3, 2), "image/png")},
            follow_redirects=False,
        )
        client.post(
            "/media",
            data={"csrf_token": csrf, "id": "loose-shot", "alt": "Loose"},
            files={"upload": ("b.png", _png(5, 4), "image/png")},
            follow_redirects=False,
        )
        filtered = client.get("/media", params={"collection": "press"}).text
        assert "press-logo" in filtered
        assert "loose-shot" not in filtered
        # the collection is editable from the asset page
        response = client.post(
            "/media/loose-shot",
            data={"csrf_token": csrf, "alt_en": "Loose", "collection": "press"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        filtered = client.get("/media", params={"collection": "press"}).text
        assert "loose-shot" in filtered
        # a bad slug is refused with the model's message
        bad = client.post(
            "/media/loose-shot",
            data={"csrf_token": csrf, "alt_en": "Loose", "collection": "Not A Slug"},
        )
    assert bad.status_code == 422
    with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
        stored = storage.load_media_asset("loose-shot")
    assert stored is not None
    assert stored.collection == "press"


def test_the_list_shows_usage_counts(tmp_path: Path) -> None:
    app = _app(tmp_path, _asset(), with_cover=True)
    with _client(app) as client:
        _sign_in(client)
        listing = client.get("/media").text
    assert "unused" not in listing.split("tin-photo")[0]  # header intact
    assert '<span class="badge text-bg-secondary">1</span>' in listing


def test_crop_and_focal_edit_and_validate(tmp_path: Path) -> None:
    app = _app(tmp_path, _asset())
    with _client(app) as client:
        csrf = _sign_in(client)
        response = client.post(
            "/media/tin-photo",
            data={
                "csrf_token": csrf,
                "alt_en": "A tin, heroic",
                "crop": "0,0,2,1",
                "focal": "0.5,0.5",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        bad = client.post(
            "/media/tin-photo",
            data={"csrf_token": csrf, "alt_en": "A tin, heroic", "crop": "9,9,9,9"},
        )
    assert bad.status_code == 422  # outside the 3-by-2 image
    with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
        stored = storage.load_media_asset("tin-photo")
    assert stored is not None
    assert stored.crop == "0,0,2,1"
    assert stored.focal == "0.5,0.5"


def _gif(width: int = 5, height: int = 4) -> bytes:
    return (
        b"GIF89a"
        + struct.pack("<HH", width, height)
        + b"\xf0\x00\x00"
        + b"\x00\x00\x00\xff\xff\xff"
        + b"\x2c\x00\x00\x00\x00"
        + struct.pack("<HH", width, height)
        + b"\x00\x02\x02\x44\x01\x00\x3b"
    )


def test_replace_keeps_the_id_and_every_reference(tmp_path: Path) -> None:
    """#136: the file changes, the asset does not — references, alt
    texts, collection and focal survive; a crop that no longer fits is
    cleared; the old file leaves the disk when the format changes."""
    asset = _asset().model_copy(
        update={"collection": "press", "focal": "0.5,0.5", "crop": "0,0,3,2"}
    )
    app = _app(tmp_path, asset, with_cover=True)
    (tmp_path / "media").mkdir(exist_ok=True)
    (tmp_path / "media" / "tin-photo.png").write_bytes(_png(3, 2))
    with _client(app) as client:
        csrf = _sign_in(client)
        response = client.post(
            "/media/tin-photo/replace",
            data={"csrf_token": csrf},
            files={"upload": ("new.gif", _gif(2, 1), "image/gif")},
            follow_redirects=False,
        )
        assert response.status_code == 303, response.text
        editor = client.get("/media/tin-photo").text
    assert "image/gif" in editor
    with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
        stored = storage.load_media_asset("tin-photo")
        articles = storage.load_all_articles()
    assert stored is not None
    assert stored.path == "tin-photo.gif"
    assert (stored.width, stored.height) == (2, 1)
    assert stored.collection == "press"  # carried over
    assert stored.focal == "0.5,0.5"  # carried over
    assert stored.crop == ""  # a 3x2 crop cannot describe a 2x1 image
    assert stored.alt  # alt texts carried over
    assert any(a.cover == "tin-photo" for a in articles)  # reference intact
    assert (tmp_path / "media" / "tin-photo.gif").is_file()
    assert not (tmp_path / "media" / "tin-photo.png").exists()


def test_replace_refuses_bytes_owned_by_another_asset(tmp_path: Path) -> None:
    app = _app(tmp_path, _asset("first"), _asset("second"))
    with _client(app) as client:
        csrf = _sign_in(client)
        # give "second" real content first
        client.post(
            "/media/second/replace",
            data={"csrf_token": csrf},
            files={"upload": ("s.png", _png(6, 6), "image/png")},
            follow_redirects=False,
        )
        clash = client.post(
            "/media/first/replace",
            data={"csrf_token": csrf},
            files={"upload": ("f.png", _png(6, 6), "image/png")},
        )
    assert clash.status_code == 422
    assert "identical content already exists" in clash.text


def test_replace_rejects_unsupported_bytes(tmp_path: Path) -> None:
    app = _app(tmp_path, _asset())
    with _client(app) as client:
        csrf = _sign_in(client)
        bad = client.post(
            "/media/tin-photo/replace",
            data={"csrf_token": csrf},
            files={"upload": ("evil.png", b"MZ\x90\x00not-an-image", "image/png")},
        )
    assert bad.status_code == 422
    assert "unsupported type" in bad.text
