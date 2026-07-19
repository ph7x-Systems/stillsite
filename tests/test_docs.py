"""Documentation anti-drift checks.

These tests read the docs and compare them with the code. When code and
documentation diverge, CI goes red — drift cannot land silently. Keep each
fact in one authoritative place and link to it from everywhere else.
"""

import re
from pathlib import Path

from cms_core import SOURCE_LANGUAGE, Language
from cms_core.storage import available_schemes

REPO_ROOT = Path(__file__).resolve().parent.parent
README = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
PLAN = (REPO_ROOT / "docs" / "PLAN.md").read_text(encoding="utf-8")


def test_every_adr_is_referenced_by_plan_or_another_adr() -> None:
    adr_dir = REPO_ROOT / "docs" / "adr"
    corpus = PLAN + "".join(adr.read_text(encoding="utf-8") for adr in sorted(adr_dir.glob("*.md")))
    for adr in sorted(adr_dir.glob("*.md")):
        number = adr.name.split("-")[0]  # e.g. "0002"
        assert f"ADR-{number}" in corpus, f"{adr.name} is referenced nowhere"


def test_every_adr_has_an_accepted_status_line() -> None:
    for adr in sorted((REPO_ROOT / "docs" / "adr").glob("*.md")):
        text = adr.read_text(encoding="utf-8")
        assert re.search(r"\*\*Status:\*\*", text), f"{adr.name} has no status line"


def test_readme_structure_matches_real_directories() -> None:
    """Parse the README tree block (2-space indentation) into real paths."""
    listed: list[str] = []
    stack: list[str] = []
    for line in README.splitlines():
        match = re.match(r"^( *)([a-z0-9-]+)/\s*(?:#.*)?$", line)
        if not match:
            continue
        depth = len(match.group(1)) // 2
        stack = [*stack[:depth], match.group(2)]
        listed.append("/".join(stack))
    assert listed, "README structure block not found"
    for directory in listed:
        assert (REPO_ROOT / directory).is_dir(), f"README lists missing directory {directory}/"


def test_readme_languages_match_the_language_enum() -> None:
    readme_lower = README.lower()
    for language in Language:
        assert language.value in readme_lower, f"README does not mention language {language.value}"
    assert SOURCE_LANGUAGE is Language.EN


def test_plan_mentions_every_builtin_storage_engine() -> None:
    engine_names = {
        "sqlite": r"sqlite",
        "postgresql": r"postgresql",
        "mssql": r"sql server|mssql",
        "mysql": r"mysql|mariadb",
    }
    assert set(engine_names) <= set(available_schemes())
    for scheme, pattern in engine_names.items():
        assert re.search(pattern, PLAN, re.IGNORECASE), f"PLAN does not mention the {scheme} engine"


def test_ci_workflow_covers_the_checks_the_readme_promises() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for tool in ("ruff", "mypy", "pytest"):
        assert tool in workflow, f"CI workflow no longer runs {tool}"
        assert tool in README, f"README no longer documents {tool}"


def test_readme_images_exist() -> None:
    references = re.findall(r'<img src="([^"#]+)"', README) + re.findall(
        r'srcset="([^"#]+)"', README
    )
    assert references, "README references no images"
    for reference in references:
        assert (REPO_ROOT / reference).is_file(), f"README references missing image {reference}"


def test_every_shipped_custom_element_is_documented() -> None:
    components = (REPO_ROOT / "docs" / "COMPONENTS.md").read_text(encoding="utf-8")
    assets_dir = (
        REPO_ROOT / "packages" / "cms-build" / "src" / "cms_build" / "themes" / "default" / "assets"
    )
    defined: set[str] = set()
    for script in sorted(assets_dir.glob("*.js")):
        defined.update(
            re.findall(r'customElements\.define\(\s*["\']([a-z0-9-]+)["\']', script.read_text())
        )
    assert defined, "no custom elements found in theme assets"
    for element in sorted(defined):
        assert f"`<{element}>`" in components, f"custom element <{element}> not in COMPONENTS.md"


def test_admin_guide_tracks_the_settings_and_workflow() -> None:
    """ADMIN_GUIDE.md anti-drift: env vars and transitions match the code."""
    import re as _re

    from cms_admin.workflow import LABELS, TRANSITIONS

    guide = (REPO_ROOT / "docs" / "ADMIN_GUIDE.md").read_text(encoding="utf-8")
    settings_src = (REPO_ROOT / "apps" / "admin" / "src" / "cms_admin" / "settings.py").read_text(
        encoding="utf-8"
    )
    for variable in sorted(set(_re.findall(r'"(SARDINE_[A-Z_]+)"', settings_src))):
        assert f"`{variable}`" in guide, f"{variable} missing from ADMIN_GUIDE.md"
    for pair, label in LABELS.items():
        assert label in guide, f"transition label {label!r} missing from ADMIN_GUIDE.md"
        assert TRANSITIONS[pair].value in guide
