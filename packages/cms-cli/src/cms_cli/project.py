"""Project configuration: `sardine.toml` loading and content access."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from cms_build import CommentsSettings, SiteConfig, register_target, register_theme
from cms_build.deploy import register_deploy_provider
from cms_core import Language
from cms_core.extensions import CommentsProvider, Extension, ExtensionError, load_extensions
from cms_core.language_packs import register_language_pack
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
    target: str = "generic"
    """The project's deployment target (``[build] target``): the admin's
    publish flow and ``cms export`` default to it (#128)."""
    deploy_root: Path | None = None
    """``[deploy] root``: when set, the filesystem provider (#156)
    publishes releases there and the panel's publish flow deploys
    automatically — no CLI, no manual copying."""
    deploy_health_url: str = ""
    deploy_keep: int = 5
    deploy_provider: str = "filesystem"
    """``[deploy] provider``: ``filesystem`` (default) or ``swa``."""
    deploy_url: str = ""
    """``[deploy] deploy_url``: the remote endpoint (swa provider)."""
    deploy_timeout: int = 300
    deploy_settings: dict[str, str] = field(default_factory=dict)
    """The raw ``[deploy]`` table — providers read their own keys."""

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
            for pack in extension.language_packs:
                register_language_pack(pack)  # type: ignore[arg-type]
            for name, factory in extension.deploy_providers.items():
                register_deploy_provider(name, factory)
        return extensions

    def resolve_comments_provider(self) -> CommentsProvider | None:
        """The provider ``[comments]`` names, from an activated extension
        (ADR-0031). None without the table; loud when the name resolves to
        nothing — a configured integration must never vanish silently."""
        settings = self.site.comments
        if settings is None:
            return None
        for extension in sorted(self.load_extensions(), key=lambda e: e.name):
            provider = extension.comments_providers.get(settings.provider)
            if provider is not None:
                return provider
        raise ExtensionError(
            f"comments provider {settings.provider!r} is not offered by any activated extension"
        )

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

    # ADR-0034: extension language packs must register before the site's
    # language list is parsed, or a pack-provided tag would be refused.
    # A broken extension is tolerated HERE only — the commands' own
    # load_extensions() call reports it loudly (doctor shows the FAIL).
    extension_names = tuple(data.get("extensions", []))
    try:
        for extension in load_extensions(extension_names):
            for pack in extension.language_packs:
                register_language_pack(pack)  # type: ignore[arg-type]
    except ExtensionError:
        pass

    site_data = data.get("site", {})
    site = SiteConfig(
        name=site_data["name"],
        base_url=site_data["base_url"],
        source_language=Language(site_data.get("source_language", "en")),
        languages=tuple(Language(code) for code in site_data.get("languages", [])),
        blog_path=site_data.get("blog_path", "blog"),
        theme=site_data.get("theme", "default"),
        page_size=site_data.get("page_size", 10),
        categories=site_data.get("categories", {}),
        labels=site_data.get("labels", {}),
        organization=site_data.get("organization"),
        footer_text=site_data.get("footer_text"),
        admin_url=site_data.get("admin_url"),
        redirects=data.get("redirects", {}),
        comments=CommentsSettings(**data["comments"]) if data.get("comments") else None,
    )

    storage_url = data.get("storage", {}).get("url", "sqlite:///content.sqlite3")
    if storage_url.startswith("sqlite:///"):
        # Relative SQLite paths are relative to the project directory.
        raw_path = Path(storage_url.removeprefix("sqlite:///").lstrip("/"))
        resolved = raw_path if raw_path.is_absolute() else directory / raw_path
        storage_url = f"sqlite:///{resolved}"

    deploy_data = data.get("deploy", {})
    build_data = data.get("build", {})
    build_updates: dict[str, object] = {}
    if build_data.get("image_widths"):
        build_updates["image_widths"] = tuple(int(w) for w in build_data["image_widths"])
    if build_data.get("content_api"):
        build_updates["content_api"] = bool(build_data["content_api"])
    site = site.model_copy(update=build_updates) if build_updates else site
    output = directory / build_data.get("output", "_site")
    return Project(
        directory=directory,
        site=site,
        storage_url=storage_url,
        output=output,
        extension_names=extension_names,
        target=str(build_data.get("target", "generic")),
        deploy_root=(
            (directory / raw_root if not Path(raw_root).is_absolute() else Path(raw_root))
            if (raw_root := str(deploy_data.get("root", "")))
            else None
        ),
        deploy_health_url=str(deploy_data.get("health_url", "")),
        deploy_keep=int(deploy_data.get("keep", 5)),
        deploy_provider=str(deploy_data.get("provider", "filesystem")),
        deploy_url=str(deploy_data.get("deploy_url", "")),
        deploy_timeout=int(deploy_data.get("timeout", 300)),
        deploy_settings={str(k): str(v) for k, v in deploy_data.items()},
    )
