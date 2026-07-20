"""Supply-chain invariants for workflows that build, release and deploy."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"


def test_every_referenced_action_is_pinned_to_a_full_commit() -> None:
    references: list[tuple[Path, str]] = []
    for workflow in sorted(WORKFLOWS.glob("*.yml")):
        for reference in re.findall(r"uses:\s*[^@\s]+@([^\s#]+)", workflow.read_text()):
            references.append((workflow, reference))
    assert references
    for workflow, reference in references:
        assert re.fullmatch(r"[0-9a-f]{40}", reference), (
            f"{workflow.name} uses mutable action reference {reference!r}"
        )


def test_deploy_secret_is_isolated_from_package_build_steps() -> None:
    workflow = (WORKFLOWS / "deploy-demo.yml").read_text()
    build, deploy = workflow.split("\n  deploy:\n", maxsplit=1)
    assert "AZURE_STATIC_WEB_APPS_API_TOKEN" not in build
    assert deploy.count("AZURE_STATIC_WEB_APPS_API_TOKEN") == 1
    assert "actions/download-artifact@" in deploy
    assert "pip install" not in deploy


def test_remote_security_tools_are_integrity_pinned() -> None:
    workflow = (WORKFLOWS / "ci.yml").read_text()
    assert "axe-core-4.12.1.tgz" in workflow
    assert "sha256sum --check --strict" in workflow
    assert "ghcr.io/trufflesecurity/trufflehog@sha256:" in workflow
    assert "trufflesecurity/trufflehog/main/scripts/install.sh" not in workflow
    assert "pip-audit --local" in workflow
    assert "bandit -q" in workflow
