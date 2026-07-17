# ADR-0005 — Deployment target adapters (Azure SWA Free/Standard, on-prem)

- **Status:** accepted
- **Date:** 2026-07-17

## Context

The framework must deploy to at least: Azure Static Web Apps **Free**, Azure
Static Web Apps **Standard**, and **on-premises** infrastructure. The
temptation is to maintain per-target builds ("editions"); that would fork the
output and break the deterministic-build contract.

## Decision

One artifact, many adapters:

- `cms build` always produces the **same target-agnostic static artifact**
  (deterministic: same input → same output). No target-specific markup ever
  enters the build.
- `cms export --target <name>` copies that artifact and adds the **adapter
  layer** — the target's configuration files only:

| Target | Adapter emits |
| --- | --- |
| `swa` (Azure Static Web Apps, Free and Standard) | `staticwebapp.config.json`: per-language 404s, redirects, caching and security headers, MIME types |
| `nginx` (on-prem/container) | `nginx.conf` (headers, redirects, cache rules) + `Dockerfile` (nginx serving the artifact) + compose example |
| `iis` (on-prem Windows) | `web.config` equivalent (planned when first needed) |
| `generic` | artifact as-is — serves from any static file server |

- SWA **Free vs Standard is not a build difference**: the artifact and the
  adapter are identical. The tiers differ only in platform features (SLA,
  number of staging environments, custom authentication, private endpoints,
  bring-your-own-functions). The docs carry a comparison matrix; projects
  choose the tier by requirements, not by rebuilding.
- Adapters are **pluggable** like storage backends: `register_target(name,
  adapter)`, mirroring ADR-0004, per the extensibility contracts. Custom
  targets (S3+CloudFront, Cloudflare Pages, …) plug in without touching the
  framework.
- The on-prem **admin panel** (dynamic, Milestone 3) ships separately as a
  compose profile: admin API + database + static server for the artifact.
  The public site never depends on the admin being reachable.

## Consequences

- One build pipeline to test; targets differ by reviewable config files.
- Adding a target is additive — no risk to existing deployments.
- The example site can CI-verify every adapter's output on each push.
- Free→Standard upgrades (or SWA→on-prem migrations) are re-deployments of
  the same artifact, never content migrations.
