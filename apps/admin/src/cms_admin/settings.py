"""Admin configuration.

Environment-only by design: the admin never reads config files, so secrets
cannot end up in a project directory that gets committed or exported.
"""

import os
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

DEFAULT_STORAGE_URL = "sqlite:///content.db"
DEFAULT_SESSION_HOURS = 12
DEFAULT_UPLOAD_MAX_MB = 10
DEFAULT_UPLOAD_MAX_PIXELS = 40_000_000


@dataclass(frozen=True, slots=True)
class AdminSettings:
    storage_url: str = DEFAULT_STORAGE_URL
    session_ttl: timedelta = timedelta(hours=DEFAULT_SESSION_HOURS)
    # Secure cookies are the default; set SARDINE_ADMIN_COOKIE_SECURE=0
    # only for plain-http local development.
    cookie_secure: bool = True
    # Where uploaded media files live — the project's media/ directory, the
    # same one `cms build` collects.
    media_dir: Path = field(default_factory=lambda: Path("media"))
    upload_max_bytes: int = DEFAULT_UPLOAD_MAX_MB * 1024 * 1024
    upload_max_pixels: int = DEFAULT_UPLOAD_MAX_PIXELS
    # The project directory (sardine.toml) — publishing builds read it.
    project_dir: Path = field(default_factory=lambda: Path("."))
    # The publish gate: block the review→published transition on validation
    # errors for the entity. Set SARDINE_ADMIN_PUBLISH_GATE=0 to disable.
    publish_gate: bool = True

    def __post_init__(self) -> None:
        if self.session_ttl <= timedelta(0):
            raise ValueError("session_ttl must be positive")
        if self.upload_max_bytes <= 0:
            raise ValueError("upload_max_bytes must be positive")
        if self.upload_max_pixels <= 0:
            raise ValueError("upload_max_pixels must be positive")

    @classmethod
    def from_env(cls) -> "AdminSettings":
        return cls(
            storage_url=os.environ.get("SARDINE_STORAGE_URL", DEFAULT_STORAGE_URL),
            session_ttl=timedelta(
                hours=float(
                    os.environ.get("SARDINE_ADMIN_SESSION_HOURS", str(DEFAULT_SESSION_HOURS))
                )
            ),
            cookie_secure=os.environ.get("SARDINE_ADMIN_COOKIE_SECURE", "1") != "0",
            media_dir=Path(os.environ.get("SARDINE_MEDIA_DIR", "media")),
            upload_max_bytes=int(
                float(os.environ.get("SARDINE_ADMIN_UPLOAD_MAX_MB", str(DEFAULT_UPLOAD_MAX_MB)))
                * 1024
                * 1024
            ),
            upload_max_pixels=int(
                os.environ.get("SARDINE_ADMIN_UPLOAD_MAX_PIXELS", str(DEFAULT_UPLOAD_MAX_PIXELS))
            ),
            project_dir=Path(os.environ.get("SARDINE_PROJECT_DIR", ".")),
            publish_gate=os.environ.get("SARDINE_ADMIN_PUBLISH_GATE", "1") != "0",
        )
