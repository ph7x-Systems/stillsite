"""Admin configuration.

Environment-only by design: the admin never reads config files, so secrets
cannot end up in a project directory that gets committed or exported.
"""

import os
from dataclasses import dataclass
from datetime import timedelta

DEFAULT_STORAGE_URL = "sqlite:///content.db"
DEFAULT_SESSION_HOURS = 12


@dataclass(frozen=True, slots=True)
class AdminSettings:
    storage_url: str = DEFAULT_STORAGE_URL
    session_ttl: timedelta = timedelta(hours=DEFAULT_SESSION_HOURS)
    # Secure cookies are the default; set SARDINE_ADMIN_COOKIE_SECURE=0
    # only for plain-http local development.
    cookie_secure: bool = True

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
        )
