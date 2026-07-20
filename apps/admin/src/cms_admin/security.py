"""Password hashing and token primitives.

Argon2id for passwords (the argon2-cffi defaults track the RFC 9106
recommendations). Session tokens are 256-bit random values; only their
SHA-256 digest is stored, so a database leak does not leak usable tokens.
"""

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()
_dummy_password_hash = _hasher.hash(secrets.token_urlsafe(32))
MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 1024


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError):
        return False


def dummy_password_hash() -> str:
    """A valid process-local hash used to equalize unknown-user login work."""
    return _dummy_password_hash


def password_needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return False


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
