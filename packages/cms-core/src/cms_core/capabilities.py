"""Optional-capability flags: a frozen entitlement set, empty by default.

Infrastructure only. Nothing in the panel, the builder, the API or the
demo reads a capability today; the set exists so future optional
integrations can gate themselves without new plumbing. Everything is
off unless the operator explicitly enables it, and enabling something
that nothing implements does nothing.
"""

import os
from typing import Protocol, runtime_checkable

ENV_VAR = "SARDINE_CAPABILITIES"


def resolve_capabilities(raw: str | None = None) -> frozenset[str]:
    """The enabled capability names — from the explicit argument or the
    environment; absent/empty means none, which is the default."""
    value = os.environ.get(ENV_VAR, "") if raw is None else raw
    return frozenset(name.strip() for name in value.split(",") if name.strip())


def capability_enabled(name: str, enabled: frozenset[str] | None = None) -> bool:
    active = resolve_capabilities() if enabled is None else enabled
    return name in active


@runtime_checkable
class LicenseProvider(Protocol):
    """Verify an operator-supplied key into a capability set.

    A contract with no bundled implementation and no call sites in any
    user flow: registering one (via an extension) changes nothing until
    a future feature explicitly consumes a capability. Verification
    must be local — this interface never implies a network call.
    """

    def verify(self, key: str) -> frozenset[str]: ...
