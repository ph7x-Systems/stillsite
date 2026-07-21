"""Media assets with mandatory, translatable alt text.

Editorial rules from the brief are enforced at the model level: images must
declare their dimensions, and alt text in the source language is mandatory.
"""

from pathlib import PurePosixPath, PureWindowsPath

from pydantic import BaseModel, Field, model_validator

from cms_core.languages import TARGET_LANGUAGES, Language
from cms_core.models import SLUG_PATTERN


class MediaAsset(BaseModel):
    id: str = Field(pattern=SLUG_PATTERN)
    path: str = Field(min_length=1)
    mime_type: str = Field(min_length=1)
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    alt: dict[Language, str]
    collection: str = Field(default="", pattern=r"^([a-z0-9]+(-[a-z0-9]+)*)?$")
    """Optional grouping (#136): a slug naming the library folder the
    asset lives in; empty means uncollected."""
    content_hash: str = Field(default="", pattern=r"^([0-9a-f]{64})?$")
    """SHA-256 of the file bytes (#136): set at upload, used to refuse
    duplicate content; empty on assets recorded before it existed."""
    crop: str = Field(default="", pattern=r"^(\d+,\d+,[1-9]\d*,[1-9]\d*)?$")
    """Editorial crop (#136): ``"x,y,width,height"`` in source pixels.
    Stored as data and applied at build time — the original file is
    never rewritten; empty means the full image."""
    focal: str = Field(default="", pattern=r"^(0(\.\d+)?|1(\.0+)?),(0(\.\d+)?|1(\.0+)?)$|^$")
    """Focal point (#136): ``"x,y"`` as fractions of the (cropped)
    image, each between 0 and 1; empty means unset (center)."""

    @property
    def is_image(self) -> bool:
        return self.mime_type.startswith("image/")

    @model_validator(mode="after")
    def _enforce_editorial_rules(self) -> "MediaAsset":
        posix_path = PurePosixPath(self.path)
        windows_path = PureWindowsPath(self.path)
        if (
            posix_path.is_absolute()
            or windows_path.is_absolute()
            or windows_path.drive
            or "\\" in self.path
            or ".." in posix_path.parts
            or any(ord(char) < 0x20 or ord(char) == 0x7F for char in self.path)
        ):
            raise ValueError("media path must be relative and must not traverse upwards")
        if self.is_image and (self.width is None or self.height is None):
            raise ValueError("images must declare width and height")
        if not any(text.strip() for text in self.alt.values()):
            raise ValueError("alt text in the source language is mandatory")
        box = self.crop_box
        if box is not None and self.width is not None and self.height is not None:
            x, y, w, h = box
            if x + w > self.width or y + h > self.height:
                raise ValueError("crop must stay inside the image")
        return self

    @property
    def crop_box(self) -> tuple[int, int, int, int] | None:
        """The crop as ``(x, y, width, height)``, or None for the full
        image."""
        if not self.crop:
            return None
        x, y, w, h = (int(part) for part in self.crop.split(","))
        return (x, y, w, h)

    @property
    def focal_point(self) -> tuple[float, float] | None:
        """The focal point as ``(x, y)`` fractions, or None when unset."""
        if not self.focal:
            return None
        fx, fy = (float(part) for part in self.focal.split(","))
        return (fx, fy)

    @property
    def display_size(self) -> tuple[int | None, int | None]:
        """The size the published site shows: the crop's when one is
        set, the intrinsic size otherwise."""
        box = self.crop_box
        if box is not None:
            return (box[2], box[3])
        return (self.width, self.height)

    def missing_alt_languages(
        self, languages: tuple[Language, ...] = TARGET_LANGUAGES
    ) -> tuple[Language, ...]:
        return tuple(language for language in languages if not self.alt.get(language, "").strip())
