"""Package versions never drift: __version__ derives from installed metadata,
and the pyproject versions stay in lockstep across the monorepo."""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECTS = [
    *sorted(ROOT.glob("packages/*/pyproject.toml")),
    ROOT / "apps" / "admin" / "pyproject.toml",
]


def _version(path: Path) -> str:
    with path.open("rb") as handle:
        return str(tomllib.load(handle)["project"]["version"])


def test_all_distributions_share_one_version() -> None:
    versions = {path.parent.name: _version(path) for path in PYPROJECTS}
    assert len(set(versions.values())) == 1, versions


def test_dunder_version_matches_the_installed_distribution() -> None:
    import cms_build
    import cms_cli
    import cms_core
    import cms_theme_ph7x_reference
    import cms_validation

    lockstep = _version(PYPROJECTS[0])
    for module in (cms_core, cms_validation, cms_build, cms_cli, cms_theme_ph7x_reference):
        assert module.__version__ == lockstep
