"""Explicit navigation menus (M6).

A menu item carries per-language labels and a URL (internal path or
external). When a project defines menu items, the builder renders exactly
them; when none exist, the menu derives from content as before (home
section anchors + blog + published pages) — nothing breaks by upgrading.
"""

from pydantic import BaseModel, ConfigDict, Field

from cms_core.languages import SOURCE_LANGUAGE, Language

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class MenuItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=SLUG_PATTERN)
    url: str = Field(min_length=1)
    position: int = 0
    labels: dict[Language, str] = Field(default_factory=dict)
    """Label per language; the source language is the fallback."""

    def label(self, language: Language) -> str:
        return self.labels.get(language) or self.labels.get(SOURCE_LANGUAGE) or self.id
