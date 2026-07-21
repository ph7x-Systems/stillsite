"""Capability flags: dark by default, everywhere.

These tests encode the rules, not just the parsing: the default is
empty, nothing user-visible consumes a capability, and the demo
pipeline never enables one.
"""

import pathlib

from cms_core.capabilities import LicenseProvider, capability_enabled, resolve_capabilities


def test_default_is_empty() -> None:
    assert resolve_capabilities("") == frozenset()
    assert not capability_enabled("anything", frozenset())


def test_explicit_parsing_is_exact() -> None:
    enabled = resolve_capabilities(" alpha, beta ,,")
    assert enabled == frozenset({"alpha", "beta"})
    assert capability_enabled("alpha", enabled)
    assert not capability_enabled("gamma", enabled)


def test_license_provider_is_a_contract_only() -> None:
    class Verifier:
        def verify(self, key: str) -> frozenset[str]:
            return frozenset({"example"})

    assert isinstance(Verifier(), LicenseProvider)


def test_nothing_user_visible_reads_capabilities() -> None:
    """No panel route, template, builder path or demo file consumes the
    flag surface — the infrastructure ships dark."""
    root = pathlib.Path(__file__).resolve().parent.parent
    surfaces = [
        *(root / "apps" / "admin" / "src").rglob("*.py"),
        *(root / "apps" / "admin" / "src").rglob("*.j2"),
        *(root / "packages" / "cms-build" / "src").rglob("*.py"),
        *(root / "packages" / "cms-cli" / "src").rglob("*.py"),
        root / ".github" / "workflows" / "ci.yml",
        root / ".github" / "workflows" / "deploy-demo.yml",
    ]
    for path in surfaces:
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert "capability_enabled" not in text, path
        assert "SARDINE_CAPABILITIES" not in text, path
