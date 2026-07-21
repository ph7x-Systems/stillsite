"""TOTP two-factor authentication (ADR-0035): RFC 6238, standard library.

HMAC-SHA1, 30-second steps, 6 digits — the profile every authenticator
app implements. Codes are single-use: the caller persists the accepted
timestep and refuses anything at or below it.
"""

import base64
import hashlib
import hmac
import secrets
import struct
from datetime import datetime

STEP_SECONDS = 30
DIGITS = 6
WINDOW = 1
"""Accepted clock drift, in steps, on each side of now."""


def generate_secret() -> str:
    """A fresh 160-bit secret, base32 without padding (RFC 4648)."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def provisioning_uri(secret: str, username: str, issuer: str = "Sardine CMS") -> str:
    from urllib.parse import quote

    label = f"{quote(issuer)}:{quote(username)}"
    return f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer)}"


def _decode(secret: str) -> bytes:
    padded = secret + "=" * (-len(secret) % 8)
    return base64.b32decode(padded.upper())


def code_for_step(secret: str, timestep: int) -> str:
    mac = hmac.new(_decode(secret), struct.pack(">Q", timestep), hashlib.sha1).digest()
    offset = mac[-1] & 0x0F
    value = (int.from_bytes(mac[offset : offset + 4], "big") & 0x7FFFFFFF) % 10**DIGITS
    return f"{value:0{DIGITS}d}"


def current_step(now: datetime) -> int:
    return int(now.timestamp()) // STEP_SECONDS


def verify(secret: str, code: str, now: datetime, last_step: int | None) -> int | None:
    """The accepted timestep, or None. Constant-time per candidate;
    anything at or below ``last_step`` is a replay and is refused."""
    center = current_step(now)
    for step in range(center - WINDOW, center + WINDOW + 1):
        if last_step is not None and step <= last_step:
            continue
        if hmac.compare_digest(code_for_step(secret, step), code):
            return step
    return None
