"""Deployment target adapters (ADR-0005).

One deterministic artifact for every target; an adapter only contributes the
target's configuration files. Targets register by name, mirroring the storage
factory, so custom targets plug in without touching the framework.
"""

import json
from collections.abc import Callable, Mapping
from typing import Protocol, runtime_checkable

from cms_build.builder import Artifact
from cms_build.config import SiteConfig

_SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


@runtime_checkable
class Target(Protocol):
    name: str

    def extra_files(self, config: SiteConfig, artifact: Artifact) -> Mapping[str, bytes]: ...


TargetFactory = Callable[[], Target]

_REGISTRY: dict[str, TargetFactory] = {}


def register_target(name: str, factory: TargetFactory) -> None:
    _REGISTRY[name] = factory


def available_targets() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


def create_target(name: str) -> Target:
    factory = _REGISTRY.get(name)
    if factory is None:
        known = ", ".join(available_targets())
        raise ValueError(f"unknown deployment target {name!r} (known targets: {known})")
    return factory()


class GenericTarget:
    """Any static file server — the artifact as-is."""

    name = "generic"

    def extra_files(self, config: SiteConfig, artifact: Artifact) -> Mapping[str, bytes]:
        return {}


class SwaTarget:
    """Azure Static Web Apps (Free and Standard: same artifact, same config)."""

    name = "swa"

    def extra_files(self, config: SiteConfig, artifact: Artifact) -> Mapping[str, bytes]:
        swa_config = {
            "globalHeaders": {
                "cache-control": "no-cache, must-revalidate",
                **_SECURITY_HEADERS,
            },
            # ADR-0021: the platform owns 5xx; 401/403/404 use the site's pages.
            "responseOverrides": {
                "401": {"rewrite": "/401.html", "statusCode": 401},
                "403": {"rewrite": "/403.html", "statusCode": 403},
                "404": {"rewrite": "/404.html", "statusCode": 404},
            },
            "routes": [
                {
                    "route": "/assets/*",
                    "headers": {"cache-control": "public, max-age=86400, must-revalidate"},
                },
                {"route": "/sitemap.xml", "headers": {"cache-control": "public, max-age=86400"}},
                {"route": "/robots.txt", "headers": {"cache-control": "public, max-age=86400"}},
            ],
            "mimeTypes": {".json": "application/json", ".xml": "application/xml"},
        }
        payload = json.dumps(swa_config, indent=2, sort_keys=True) + "\n"
        return {"staticwebapp.config.json": payload.encode("utf-8")}


class NginxTarget:
    """On-prem/container: nginx configuration plus a ready-to-build image."""

    name = "nginx"

    def extra_files(self, config: SiteConfig, artifact: Artifact) -> Mapping[str, bytes]:
        header_lines = "\n".join(
            f'    add_header {name} "{value}" always;'
            for name, value in sorted(_SECURITY_HEADERS.items())
        )
        nginx_conf = (
            "server {\n"
            "    listen 8080;\n"
            "    root /usr/share/nginx/html;\n"
            "    index index.html;\n"
            f"{header_lines}\n"
            "    location /assets/ {\n"
            '        add_header cache-control "public, max-age=86400, must-revalidate";\n'
            "    }\n"
            "    error_page 401 /401.html;\n"
            "    error_page 403 /403.html;\n"
            "    error_page 404 /404.html;\n"
            "    error_page 500 502 503 504 /50x.html;\n"
            "    location / {\n"
            "        try_files $uri $uri/ =404;\n"
            "    }\n"
            "}\n"
        )
        dockerfile = (
            "FROM nginx:1.27-alpine\n"
            "COPY nginx.conf /etc/nginx/conf.d/default.conf\n"
            "COPY . /usr/share/nginx/html\n"
        )
        return {
            "nginx.conf": nginx_conf.encode("utf-8"),
            "Dockerfile": dockerfile.encode("utf-8"),
        }


register_target("generic", GenericTarget)
register_target("swa", SwaTarget)
register_target("nginx", NginxTarget)
