"""Deployment target adapters."""

import json

import pytest
from cms_build import Artifact, SiteConfig, available_targets, create_target, register_target
from cms_core import Language

CONFIG = SiteConfig(name="Aurora", base_url="https://example.com", languages=(Language.PT_PT,))


def test_builtin_targets_registered() -> None:
    assert {"generic", "swa", "nginx"} <= set(available_targets())


def test_generic_target_adds_nothing() -> None:
    assert create_target("generic").extra_files(CONFIG, Artifact()) == {}


def test_swa_target_emits_config_with_security_headers() -> None:
    files = create_target("swa").extra_files(CONFIG, Artifact())
    config = json.loads(files["staticwebapp.config.json"])
    assert config["globalHeaders"]["X-Content-Type-Options"] == "nosniff"
    assert config["responseOverrides"]["404"]["rewrite"] == "/404.html"
    assert any(route["route"] == "/assets/*" for route in config["routes"])


def test_nginx_target_emits_conf_and_dockerfile() -> None:
    files = create_target("nginx").extra_files(CONFIG, Artifact())
    conf = files["nginx.conf"].decode("utf-8")
    assert "add_header X-Frame-Options" in conf
    assert "try_files" in conf
    assert files["Dockerfile"].decode("utf-8").startswith("FROM nginx:")


def test_unknown_target_fails_loudly() -> None:
    with pytest.raises(ValueError, match="generic"):
        create_target("cloudflare")


def test_custom_target_registration() -> None:
    class NullTarget:
        name = "null"

        def extra_files(self, config: SiteConfig, artifact: Artifact) -> dict[str, bytes]:
            return {"null.txt": b"ok"}

    register_target("null", NullTarget)
    assert create_target("null").extra_files(CONFIG, Artifact()) == {"null.txt": b"ok"}
