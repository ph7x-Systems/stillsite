"""Deployment target adapters."""

import json

import pytest
from cms_build import Artifact, SiteConfig, available_targets, create_target, register_target
from cms_core import Language, MenuItem

CONFIG = SiteConfig(name="Aurora", base_url="https://example.com", languages=(Language.PT_PT,))


@pytest.mark.parametrize(
    "url",
    (
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "//attacker.example/path",
        "/../outside",
        "https://safe.example/line\nbreak",
    ),
)
def test_navigation_urls_reject_active_or_ambiguous_values(url: str) -> None:
    with pytest.raises(ValueError):
        MenuItem(id="unsafe", url=url)
    with pytest.raises(ValueError):
        SiteConfig(name="Unsafe", base_url="https://example.com", admin_url=url)


@pytest.mark.parametrize(
    ("source", "destination"),
    (
        ("/../../nginx.conf", "/safe/"),
        ("/safe/;", "/safe/"),
        ("/old/", "javascript:alert(1)"),
        ("/old/", "/safe/; add_header X-Owned yes"),
        ("/old/", "https://safe.example/$request_uri"),
    ),
)
def test_redirects_reject_path_and_nginx_directive_injection(source: str, destination: str) -> None:
    with pytest.raises(ValueError):
        SiteConfig(
            name="Unsafe",
            base_url="https://example.com",
            redirects={source: destination},
        )


def test_builtin_targets_registered() -> None:
    assert {"generic", "swa", "nginx", "astro"} <= set(available_targets())


def test_generic_target_adds_nothing() -> None:
    assert create_target("generic").extra_files(CONFIG, Artifact()) == {}


def test_swa_target_emits_config_with_security_headers() -> None:
    files = create_target("swa").extra_files(CONFIG, Artifact())
    config = json.loads(files["staticwebapp.config.json"])
    assert config["globalHeaders"]["X-Content-Type-Options"] == "nosniff"
    for code, page in (("401", "/401.html"), ("403", "/403.html"), ("404", "/404.html")):
        assert config["responseOverrides"][code]["rewrite"] == page  # ADR-0021
        assert config["responseOverrides"][code]["statusCode"] == int(code)
    assert any(route["route"] == "/assets/*" for route in config["routes"])


def test_nginx_target_emits_conf_and_dockerfile() -> None:
    files = create_target("nginx").extra_files(CONFIG, Artifact())
    conf = files["nginx.conf"].decode("utf-8")
    assert "add_header X-Frame-Options" in conf
    assert "try_files" in conf
    for directive in (
        "error_page 401 /401.html;",
        "error_page 403 /403.html;",
        "error_page 404 /404.html;",
        "error_page 500 502 503 504 /50x.html;",
    ):
        assert directive in conf  # ADR-0021: the site pages, not server defaults
    assert files["Dockerfile"].decode("utf-8").startswith("FROM nginx:")


def test_unknown_target_fails_loudly() -> None:
    with pytest.raises(ValueError, match="generic"):
        create_target("cloudflare")


def test_astro_target_emits_scaffold_files() -> None:
    files = create_target("astro").extra_files(CONFIG, Artifact())
    assert "astro.config.mjs" in files
    assert "src/content/config.ts" in files
    assert "package.json" in files
    assert "tsconfig.json" in files
    assert "README.md" in files
    config = files["astro.config.mjs"].decode("utf-8")
    assert "defineConfig" in config
    content_config = files["src/content/config.ts"].decode("utf-8")
    assert "defineCollection" in content_config
    assert "articles" in content_config
    assert "pages" in content_config
    pkg = json.loads(files["package.json"])
    assert "astro" in pkg["dependencies"]
    readme = files["README.md"].decode("utf-8")
    assert "Sardine" in readme
    assert "Content API" in readme


def test_astro_readme_lists_configured_languages() -> None:
    config = SiteConfig(
        name="Multi",
        base_url="https://example.com",
        languages=(Language.PT_PT, Language("it")),
    )
    files = create_target("astro").extra_files(config, Artifact())
    readme = files["README.md"].decode("utf-8")
    assert "pt-pt" in readme
    assert "it" in readme


def test_custom_target_registration() -> None:
    class NullTarget:
        name = "null"

        def extra_files(self, config: SiteConfig, artifact: Artifact) -> dict[str, bytes]:
            return {"null.txt": b"ok"}

    register_target("null", NullTarget)
    assert create_target("null").extra_files(CONFIG, Artifact()) == {"null.txt": b"ok"}


def test_redirects_reach_both_target_configs() -> None:
    """M6: configured redirects become real 301s per target."""
    config = CONFIG.model_copy(update={"redirects": {"/old/": "/new/", "/blog-old/": "/blog/"}})
    swa = json.loads(
        create_target("swa").extra_files(config, Artifact())["staticwebapp.config.json"]
    )
    redirect_routes = [route for route in swa["routes"] if "redirect" in route]
    assert redirect_routes == [
        {"route": "/blog-old/", "redirect": "/blog/", "statusCode": 301},
        {"route": "/old/", "redirect": "/new/", "statusCode": 301},
    ]
    conf = create_target("nginx").extra_files(config, Artifact())["nginx.conf"].decode("utf-8")
    assert "location = /old/ { return 301 /new/; }" in conf
    assert "location = /blog-old/ { return 301 /blog/; }" in conf
