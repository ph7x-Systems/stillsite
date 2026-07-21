"""Build-time image derivatives (ADR-0029).

Opt-in per project (``[build] image_widths``). Pillow lives behind the
``sardine-cms-build[images]`` extra; configured widths without Pillow
fail the build loudly. Derivatives keep the source format, use fixed
resampling and encoder parameters, and are therefore deterministic.
"""

from io import BytesIO
from pathlib import PurePosixPath

RESIZABLE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def derivative_path(path: str, width: int) -> str:
    pure = PurePosixPath(path)
    return str(pure.with_name(f"{pure.stem}@{width}{pure.suffix}"))


def apply_crops(media_files: dict[str, bytes], crops: dict[str, tuple[int, int, int, int]]) -> None:
    """Apply editorial crops in place (#136): the published pipeline —
    base rendition and every derivative — descends from the cropped
    bytes. The stored original is untouched; a cleared crop restores
    the full image on the next build. Fixed encoder parameters keep the
    output deterministic."""
    if not crops:
        return
    try:
        from PIL import Image
    except ImportError as error:  # pragma: no cover - exercised via message test
        raise RuntimeError(
            "a media crop is set but Pillow is not installed — install sardine-cms-build[images]"
        ) from error
    for path in sorted(crops):
        if path not in media_files:
            continue
        if PurePosixPath(path).suffix.lower() not in RESIZABLE_SUFFIXES:
            continue
        x, y, width, height = crops[path]
        with Image.open(BytesIO(media_files[path])) as image:
            box = (x, y, min(x + width, image.width), min(y + height, image.height))
            cropped = image.crop(box)
            buffer = BytesIO()
            cropped.save(buffer, format=image.format)
        media_files[path] = buffer.getvalue()


def generate_derivatives(
    media_files: dict[str, bytes], widths: tuple[int, ...]
) -> dict[str, dict[int, str]]:
    """Extend ``media_files`` in place with resized variants; returns
    ``{original_path: {width: derivative_path}}`` for the builder's
    srcset assembly."""
    if not widths:
        return {}
    try:
        from PIL import Image
    except ImportError as error:  # pragma: no cover - exercised via message test
        raise RuntimeError(
            "image_widths is configured but Pillow is not installed — "
            "install sardine-cms-build[images]"
        ) from error
    variants: dict[str, dict[int, str]] = {}
    for path in sorted(media_files):
        suffix = PurePosixPath(path).suffix.lower()
        if suffix not in RESIZABLE_SUFFIXES:
            continue
        with Image.open(BytesIO(media_files[path])) as image:
            original_width = image.width
            image_format = image.format
            for width in sorted(widths):
                if width >= original_width:
                    continue
                ratio = width / original_width
                resized = image.resize(
                    (width, max(1, round(image.height * ratio))), Image.Resampling.LANCZOS
                )
                buffer = BytesIO()
                resized.save(buffer, format=image_format)
                target = derivative_path(path, width)
                media_files[target] = buffer.getvalue()
                variants.setdefault(path, {})[width] = target
    return variants
