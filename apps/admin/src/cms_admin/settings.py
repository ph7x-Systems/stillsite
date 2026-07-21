"""Admin configuration.

Environment-only by design: the admin never reads config files, so secrets
cannot end up in a project directory that gets committed or exported.
"""

import os
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

from cms_core.accounts import Role

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
    # Outbound email (ADR-0032): a named transport. "smtp" is the bundled
    # baseline (needs smtp_url + mail_from); any other name resolves to an
    # activated extension's mail transport. Unconfigured = email off.
    mail_transport: str = "smtp"
    smtp_url: str | None = None
    mail_from: str | None = None
    # ADR-0035 amendment: minimum role at/above which two-factor is
    # mandatory (forced enrolment). None = optional for everyone.
    require_2fa_role: "Role | None" = None

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
            mail_transport=os.environ.get("SARDINE_MAIL_TRANSPORT", "smtp"),
            smtp_url=os.environ.get("SARDINE_SMTP_URL"),
            mail_from=os.environ.get("SARDINE_MAIL_FROM"),
            require_2fa_role=_parse_2fa_role(os.environ.get("SARDINE_ADMIN_REQUIRE_2FA")),
        )


def _parse_2fa_role(value: str | None) -> Role | None:
    """Unknown values fail startup loudly — a security policy must never
    silently become a no-op (ADR-0035 amendment)."""
    if not value:
        return None
    try:
        return Role(value)
    except ValueError as error:
        raise ValueError(
            "SARDINE_ADMIN_REQUIRE_2FA must be one of "
            f"editor|reviewer|publisher|admin, got {value!r}"
        ) from error
