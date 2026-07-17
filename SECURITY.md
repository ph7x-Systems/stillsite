# Security Policy

## Reporting vulnerabilities

Report vulnerabilities privately to the `ph7x-Systems` organization maintainers. Do not open public issues with exploitation details.

## Principles applied in this project

- **No secrets in the repository** — sensitive configuration via environment variables (`.env`, never committed; see `.env.example`).
- **Explicit authentication and authorization** in the admin panel, with least privilege.
- **Validated uploads** — type, size and dimensions checked in the media library.
- **Static public frontend** — no exposed dynamic surface; dynamic features isolated in the API.
- **CI checks for absence of secrets** before every merge.

## Scope

This repository contains no real credentials or infrastructure. Any credential found in the history must be treated as compromised and reported.
