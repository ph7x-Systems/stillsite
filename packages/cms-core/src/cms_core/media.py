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
        return self

    def missing_alt_languages(
        self, languages: tuple[Language, ...] = TARGET_LANGUAGES
    ) -> tuple[Language, ...]:
        return tuple(language for language in languages if not self.alt.get(language, "").strip())
