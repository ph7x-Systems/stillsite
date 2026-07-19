"""Project configuration: `sardine.toml` loading and content access."""

import tomllib
from dataclasses import dataclass
from pathlib import Path

from cms_build import SiteConfig, register_target, register_theme
from cms_core import Language
from cms_core.extensions import Extension, load_extensions
from cms_core.storage import StorageBackend, create_storage, register_backend
from cms_validation import SiteContent

PROJECT_FILE = "sardine.toml"
LEGACY_PROJECT_FILE = "stillsite.toml"
"""Pre-rename projects keep working: read the old file when the new one
is absent (the product was renamed from Stillsite to Sardine CMS)."""


@dataclass(frozen=True, slots=True)
class Project:
    directory: Path
    site: SiteConfig
    storage_url: str
    output: Path
    extension_names: tuple[str, ...] = ()

    def load_extensions(self) -> list[Extension]:
        """The extensions this project explicitly trusts (ADR-0028); their
        targets, backends and themes register on load."""
        extensions = load_extensions(self.extension_names)
        for extension in extensions:
            for name, factory in extension.storage_backends.items():
                register_backend(name, factory)  # type: ignore[arg-type]
            for name, factory in extension.targets.items():
                register_target(name, factory)  # type: ignore[arg-type]
            for name, factory in extension.themes.items():
                register_theme(name, factory)  # type: ignore[arg-type]
        return extensions

    def open_storage(self) -> StorageBackend:
        return create_storage(self.storage_url)

    def load_content(self) -> SiteContent:
        """The current editorial world: trashed entries (ADR-0026) are
        invisible to every consumer — builder, validator, exporter."""
        with self.open_storage() as storage:
            return SiteContent(
                articles=[a for a in storage.load_all_articles() if a.deleted_at is None],
                pages=[p for p in storage.load_all_pages() if p.deleted_at is None],
                media=storage.load_all_media_assets(),
                menu=storage.load_menu_items(),
            )

    @property
    def theme_overrides(self) -> Path | None:
        overrides = self.directory / "theme"
        return overrides if overrides.is_dir() else None

    def collect_media_files(self) -> dict[str, bytes]:
        media_dir = self.directory / "media"
        if not media_dir.is_dir():
            return {}
        return {
            path.relative_to(media_dir).as_posix(): path.read_bytes()
            for path in sorted(media_dir.rglob("*"))
            if path.is_file() and not path.name.startswith(".")
        }


def load_project(directory: Path) -> Project:
    config_path = directory / PROJECT_FILE
    if not config_path.is_file():
        legacy = directory / LEGACY_PROJECT_FILE
        if legacy.is_file():
            config_path = legacy
        else:
            raise FileNotFoundError(f"{PROJECT_FILE} not found in {directory}")
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))

    site_data = data.get("site", {})
    site = SiteConfig(
        name=site_data["name"],
        base_url=site_data["base_url"],
        languages=tuple(Language(code) for code in site_data.get("languages", [])),
        blog_path=site_data.get("blog_path", "blog"),
        theme=site_data.get("theme", "default"),
        page_size=site_data.get("page_size", 10),
        categories=site_data.get("categories", {}),
        labels=site_data.get("labels", {}),
        organization=site_data.get("organization"),
        footer_text=site_data.get("footer_text"),
        admin_url=site_data.get("admin_url"),
    )

    storage_url = data.get("storage", {}).get("url", "sqlite:///content.sqlite3")
    if storage_url.startswith("sqlite:///"):
        # Relative SQLite paths are relative to the project directory.
        raw_path = Path(storage_url.removeprefix("sqlite:///").lstrip("/"))
        resolved = raw_path if raw_path.is_absolute() else directory / raw_path
        storage_url = f"sqlite:///{resolved}"

    output = directory / data.get("build", {}).get("output", "_site")
    return Project(
        directory=directory,
        site=site,
        storage_url=storage_url,
        output=output,
        extension_names=tuple(data.get("extensions", [])),
    )
