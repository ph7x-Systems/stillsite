"""Admin configuration.

Environment-only by design: the admin never reads config files, so secrets
cannot end up in a project directory that gets committed or exported.
"""

import os
from dataclasses import dataclass

DEFAULT_STORAGE_URL = "sqlite:///content.db"


@dataclass(frozen=True, slots=True)
class AdminSettings:
    storage_url: str = DEFAULT_STORAGE_URL

    @classmethod
    def from_env(cls) -> "AdminSettings":
        return cls(storage_url=os.environ.get("STILLSITE_STORAGE_URL", DEFAULT_STORAGE_URL))
