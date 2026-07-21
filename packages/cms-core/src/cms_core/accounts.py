"""Admin accounts and sessions (Milestone 3).

Accounts are an operational concern of the admin panel: they live in the
storage database (shared migration history) but are **never** part of the
JSON/Markdown export — the portable source of truth stays content-only.
The domain layer only defines the shapes; hashing and session issuance are
the admin application's job.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from cms_core.languages import Language

USERNAME_PATTERN = r"^[a-z0-9][a-z0-9._-]{0,63}$"


class Role(StrEnum):
    """Least-privilege ladder; each step includes the previous one's intent.

    editor: create and edit drafts · reviewer: move drafts through review ·
    publisher: publish and archive · admin: manage accounts and settings.
    """

    EDITOR = "editor"
    REVIEWER = "reviewer"
    PUBLISHER = "publisher"
    ADMIN = "admin"


class User(BaseModel):
    model_config = ConfigDict(frozen=True)

    username: str = Field(pattern=USERNAME_PATTERN)
    password_hash: str = Field(min_length=1)
    role: Role
    created_at: datetime
    language: Language | None = None
    """Preferred admin-panel language; None follows the browser."""
    email: str | None = None
    """Optional address for password reset and notifications (ADR-0032);
    never exported, lives only in the project database."""
    totp_secret: str | None = None
    """Base32 TOTP secret (ADR-0035); set = two-factor enabled."""
    totp_step: int | None = None
    """Last accepted TOTP timestep — makes every code single-use."""


class AdminSession(BaseModel):
    """A server-side session row. Only the token's hash is stored."""

    model_config = ConfigDict(frozen=True)

    token_hash: str = Field(min_length=1)
    username: str = Field(pattern=USERNAME_PATTERN)
    csrf_token: str = Field(min_length=1)
    expires_at: datetime


class PasswordReset(BaseModel):
    """A pending password-reset request (ADR-0032). Only the token's
    hash is stored; the row is single-use and expires."""

    model_config = ConfigDict(frozen=True)

    token_hash: str = Field(min_length=1)
    username: str = Field(pattern=USERNAME_PATTERN)
    expires_at: datetime
