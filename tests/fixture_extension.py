"""A fixture extension for the Extensions screen tests."""

from cms_core.extensions import Extension, HealthCheck


def _health() -> list[HealthCheck]:
    return [
        HealthCheck(name="storage reachable", ok=True, detail="fixture store answers"),
        HealthCheck(name="webhook endpoint", ok=False, detail="connection refused"),
    ]


extension = Extension(
    name="fixture",
    section_kinds={"fixture-hero": ("title", "body")},
    health_check=_health,
)


def _broken_health() -> list[HealthCheck]:
    raise RuntimeError("health probe exploded")


noisy = Extension(name="noisy", health_check=_broken_health)
