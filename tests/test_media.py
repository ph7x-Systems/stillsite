"""Editorial rules enforced by the media asset model."""

import pytest
from cms_core import Language, MediaAsset
from pydantic import ValidationError


def make_image(**overrides: object) -> MediaAsset:
    data: dict[str, object] = {
        "id": "hero-image",
        "path": "images/hero.webp",
        "mime_type": "image/webp",
        "width": 1600,
        "height": 900,
        "alt": {Language.EN: "A sunrise over the office"},
    }
    data.update(overrides)
    return MediaAsset.model_validate(data)


def test_valid_image_asset() -> None:
    asset = make_image()
    assert asset.is_image
    assert asset.missing_alt_languages() == (
        Language.PT_PT,
        Language.ES,
        Language.FR,
        Language.DE,
    )


def test_images_require_dimensions() -> None:
    with pytest.raises(ValueError, match="width and height"):
        make_image(width=None)


def test_non_images_do_not_require_dimensions() -> None:
    asset = make_image(mime_type="application/pdf", width=None, height=None)
    assert not asset.is_image


def test_alt_text_in_some_language_is_mandatory() -> None:
    """ADR-0034: the source is configurable, so the model requires alt
    text in at least one language — which one is the validation
    context's business, not the model's."""
    with pytest.raises(ValueError, match="alt text"):
        make_image(alt={Language.EN: "   "})
    assert make_image(alt={Language.PT_PT: "Um nascer do sol"}).alt[Language.PT_PT]


def test_media_path_must_be_relative_and_safe() -> None:
    with pytest.raises(ValueError, match="relative"):
        make_image(path="/etc/passwd")
    with pytest.raises(ValueError, match="relative"):
        make_image(path="images/../../secret.png")
    with pytest.raises(ValueError, match="relative"):
        make_image(path=r"images\..\secret.png")
    with pytest.raises(ValueError, match="relative"):
        make_image(path=r"C:\Windows\system.ini")
    with pytest.raises(ValueError, match="relative"):
        make_image(path="images/control\n.png")


def test_translated_alt_counts_only_when_non_blank() -> None:
    asset = make_image(
        alt={Language.EN: "A sunrise", Language.PT_PT: "Um nascer do sol", Language.ES: "  "}
    )
    assert Language.PT_PT not in asset.missing_alt_languages()
    assert Language.ES in asset.missing_alt_languages()


def test_collection_is_a_slug_or_empty() -> None:
    ok = MediaAsset(
        id="pic",
        path="pic.png",
        mime_type="image/png",
        width=1,
        height=1,
        alt={Language.EN: "A pic"},
        collection="press-kit",
    )
    assert ok.collection == "press-kit"
    with pytest.raises(ValidationError):
        MediaAsset(
            id="pic",
            path="pic.png",
            mime_type="image/png",
            width=1,
            height=1,
            alt={Language.EN: "A pic"},
            collection="Press Kit",
        )


def test_content_hash_is_sha256_hex_or_empty() -> None:
    ok = MediaAsset(
        id="pic",
        path="pic.png",
        mime_type="image/png",
        width=1,
        height=1,
        alt={Language.EN: "A pic"},
        content_hash="0" * 64,
    )
    assert ok.content_hash == "0" * 64
    with pytest.raises(ValidationError):
        MediaAsset(
            id="pic",
            path="pic.png",
            mime_type="image/png",
            width=1,
            height=1,
            alt={Language.EN: "A pic"},
            content_hash="not-a-hash",
        )


def test_crop_must_stay_inside_the_image() -> None:
    ok = MediaAsset(
        id="pic",
        path="pic.png",
        mime_type="image/png",
        width=100,
        height=80,
        alt={Language.EN: "A pic"},
        crop="10,10,50,40",
        focal="0.5,0.25",
    )
    assert ok.crop_box == (10, 10, 50, 40)
    assert ok.focal_point == (0.5, 0.25)
    assert ok.display_size == (50, 40)
    with pytest.raises(ValidationError):
        MediaAsset(
            id="pic",
            path="pic.png",
            mime_type="image/png",
            width=100,
            height=80,
            alt={Language.EN: "A pic"},
            crop="60,10,50,40",  # 60+50 > 100
        )
    with pytest.raises(ValidationError):
        MediaAsset(
            id="pic",
            path="pic.png",
            mime_type="image/png",
            width=100,
            height=80,
            alt={Language.EN: "A pic"},
            focal="1.5,0.5",  # outside 0..1
        )
