"""Project configuration: `stillsite.toml` loading and content access."""

import tomllib
from dataclasses import dataclass
from pathlib import Path

from cms_build import SiteConfig
from cms_core import Language
from cms_core.storage import StorageBackend, create_storage
from cms_validation import SiteContent

PROJECT_FILE = "stillsite.toml"


@dataclass(frozen=True, slots=True)
class Project:
    directory: Path
    site: SiteConfig
    storage_url: str
    output: Path

    def open_storage(self) -> StorageBackend:
        return create_storage(self.storage_url)

    def load_content(self) -> SiteContent:
        with self.open_storage() as storage:
            return SiteContent(
                articles=storage.load_all_articles(),
                pages=storage.load_all_pages(),
                media=storage.load_all_media_assets(),
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
    return Project(directory=directory, site=site, storage_url=storage_url, output=output)
