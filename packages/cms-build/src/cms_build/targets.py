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
                *[
                    {"route": source, "redirect": destination, "statusCode": 301}
                    for source, destination in sorted(config.redirects.items())
                ],
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
            + "".join(
                f"    location = {source} {{ return 301 {destination}; }}\n"
                for source, destination in sorted(config.redirects.items())
            )
            + "    error_page 401 /401.html;\n"
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


class AstroTarget:
    """Astro: a project scaffold that consumes Sardine's Content API JSON
    through Content Collections, for teams that already deploy Astro."""

    name = "astro"

    def extra_files(self, config: SiteConfig, artifact: Artifact) -> Mapping[str, bytes]:
        languages = [lang.value for lang in config.all_languages]
        return {
            "astro.config.mjs": _astro_config().encode("utf-8"),
            "src/content/config.ts": _astro_content_config().encode("utf-8"),
            "package.json": _astro_package_json().encode("utf-8"),
            "tsconfig.json": _astro_tsconfig().encode("utf-8"),
            "README.md": _astro_readme(languages).encode("utf-8"),
        }


def _astro_config() -> str:
    return (
        "import { defineConfig } from 'astro/config';\n"
        "\n"
        "export default defineConfig({\n"
        "  output: 'static',\n"
        "});\n"
    )


def _astro_content_config() -> str:
    return (
        "import { defineCollection, z } from 'astro:content';\n"
        "\n"
        "// Schemas match Sardine's Content API (api/v1/{lang}/content.json).\n"
        "// Enable [build] content_api = true in sardine.toml to emit the JSON.\n"
        "\n"
        "const articles = defineCollection({\n"
        "  type: 'data',\n"
        "  schema: z.object({\n"
        "    id: z.string(),\n"
        "    slug: z.string().nullable(),\n"
        "    url: z.string(),\n"
        "    title: z.string(),\n"
        "    summary: z.string(),\n"
        "    body_html: z.string(),\n"
        "    date: z.string(),\n"
        "    author: z.string().nullable(),\n"
        "    featured: z.boolean().optional(),\n"
        "    category: z.object({\n"
        "      slug: z.string(),\n"
        "      label: z.string(),\n"
        "      url: z.string(),\n"
        "    }).nullable(),\n"
        "    tags: z.array(z.object({\n"
        "      slug: z.string(),\n"
        "      url: z.string(),\n"
        "    })).optional(),\n"
        "    cover: z.object({\n"
        "      url: z.string(),\n"
        "      alt: z.string(),\n"
        "      width: z.number(),\n"
        "      height: z.number(),\n"
        "      sources: z.array(z.object({\n"
        "        type: z.string(),\n"
        "        srcset: z.string(),\n"
        "      })),\n"
        "      focal: z.object({ x: z.number(), y: z.number() }).optional(),\n"
        "      srcset: z.string().optional(),\n"
        "    }).nullable(),\n"
        "    fields: z.record(z.string()).nullable(),\n"
        "  }),\n"
        "});\n"
        "\n"
        "const pages = defineCollection({\n"
        "  type: 'data',\n"
        "  schema: z.object({\n"
        "    id: z.string(),\n"
        "    slug: z.string().nullable(),\n"
        "    url: z.string(),\n"
        "    title: z.string(),\n"
        "    description: z.string(),\n"
        "    body_markdown: z.string(),\n"
        "    sections: z.array(z.object({\n"
        "      key: z.string(),\n"
        "      kind: z.string(),\n"
        "      fields: z.record(z.string()),\n"
        "      items: z.array(z.record(z.unknown())),\n"
        "      images: z.array(z.object({\n"
        "        url: z.string(),\n"
        "        alt: z.string(),\n"
        "        width: z.number(),\n"
        "        height: z.number(),\n"
        "        sources: z.array(z.object({\n"
        "          type: z.string(),\n"
        "          srcset: z.string(),\n"
        "        })),\n"
        "        focal: z.object({ x: z.number(), y: z.number() }).optional(),\n"
        "        srcset: z.string().optional(),\n"
        "      })),\n"
        "    })),\n"
        "  }),\n"
        "});\n"
        "\n"
        "export const collections = { articles, pages };\n"
    )


def _astro_package_json() -> str:
    return (
        "{\n"
        '  "name": "sardine-astro",\n'
        '  "type": "module",\n'
        '  "version": "0.0.1",\n'
        '  "private": true,\n'
        '  "scripts": {\n'
        '    "dev": "astro dev",\n'
        '    "build": "astro build",\n'
        '    "preview": "astro preview"\n'
        "  },\n"
        '  "dependencies": {\n'
        '    "astro": "^4.16.0"\n'
        "  }\n"
        "}\n"
    )


def _astro_tsconfig() -> str:
    return '{\n  "extends": "astro/tsconfigs/strict"\n}\n'


def _astro_readme(languages: list[str]) -> str:
    lang_list = ", ".join(languages)
    return (
        "# Sardine CMS + Astro\n"
        "\n"
        "This directory contains a Sardine CMS build with an Astro project\n"
        "scaffold. The static HTML site is ready to serve as-is; the scaffold\n"
        "lets you consume the same content through Astro if you prefer its\n"
        "component model.\n"
        "\n"
        "## Prerequisites\n"
        "\n"
        "- Node.js 18 or later\n"
        "- Sardine's Content API enabled (`content_api = true` in `[build]`)\n"
        "\n"
        "## Quick start\n"
        "\n"
        "```sh\n"
        "npm install\n"
        "npm run dev\n"
        "```\n"
        "\n"
        "The dev server starts at http://localhost:4321.\n"
        "\n"
        "## How it works\n"
        "\n"
        "Sardine's Content API emits versioned JSON at\n"
        "`api/v1/{lang}/content.json` with the same publication, scheduling\n"
        f"and language rules as the HTML build. Configured languages: {lang_list}.\n"
        "The content collections in `src/content/config.ts` define Zod schemas\n"
        "matching that JSON, so you can query articles and pages type-safely in\n"
        "your Astro components.\n"
        "\n"
        "## File layout\n"
        "\n"
        "- `astro.config.mjs` — Astro configuration\n"
        "- `src/content/config.ts` — content collection schemas\n"
        "- `package.json` — dependencies and scripts\n"
        "- `tsconfig.json` — TypeScript configuration (extends Astro's strict preset)\n"
        "- `api/v1/` — Sardine's Content API JSON (generated by the build)\n"
    )


register_target("generic", GenericTarget)
register_target("swa", SwaTarget)
register_target("nginx", NginxTarget)
register_target("astro", AstroTarget)
