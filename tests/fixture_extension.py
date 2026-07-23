"""A fixture extension for the Extensions screen tests."""

from collections.abc import Mapping

from cms_core.extensions import Extension, HealthCheck, SettingsField, SettingsSchema

received: list[dict[str, object]] = []
"""configure() captures resolved values here for assertions."""


def _health() -> list[HealthCheck]:
    return [
        HealthCheck(name="storage reachable", ok=True, detail="fixture store answers"),
        HealthCheck(name="webhook endpoint", ok=False, detail="connection refused"),
    ]


SCHEMA = SettingsSchema(
    version=2,
    fields=(
        SettingsField(
            key="region", type="choice", label="Region", choices=("eu", "us"), default="eu"
        ),
        SettingsField(key="retries", type="integer", label="Retries", default=3),
        SettingsField(key="verbose", type="boolean", label="Verbose", default=False),
        SettingsField(key="api_key", label="API key", env="FIXTURE_API_KEY"),
    ),
)


def _migrate(old_version: int, values: Mapping[str, object]) -> Mapping[str, object]:
    # v1 stored "zone"; v2 calls it "region".
    migrated = dict(values)
    if old_version == 1 and "zone" in migrated:
        migrated["region"] = migrated.pop("zone")
    return migrated


def _configure(values: Mapping[str, object]) -> None:
    received.append(dict(values))


extension = Extension(
    name="fixture",
    section_kinds={"fixture-hero": ("title", "body")},
    health_check=_health,
    settings_schema=SCHEMA,
    configure=_configure,
    migrate_settings=_migrate,
)


def _broken_health() -> list[HealthCheck]:
    raise RuntimeError("health probe exploded")


noisy = Extension(name="noisy", health_check=_broken_health)
