# ADR-0016 — The product is renamed to Sardine CMS

- **Status:** accepted
- **Date:** 2026-07-18

## Context

The project launched as Stillsite. Meanwhile the demo — a fictional space
programme run by a sardine — became the product's actual voice: the tin
rocket is the favicon, the sardine is the star of every screenshot, and the
name people remember. The owner decided the product follows the brand:
**Sardine CMS**.

## Decision

- Product name: **Sardine CMS**. Repository: `ph7x-Systems/sardine-cms`
  (GitHub redirects the old URLs).
- Project file: `sardine.toml`. Pre-rename projects keep working — the CLI
  falls back to `stillsite.toml` when `sardine.toml` is absent.
- Environment variables: `SARDINE_*` (`SARDINE_STORAGE_URL`,
  `SARDINE_ADMIN_SESSION_HOURS`, `SARDINE_ADMIN_COOKIE_SECURE`,
  `SARDINE_POSTGRES_URL`).
- Theme entry-point group: `sardine.themes`.
- Session cookies: `sardine_session`, `sardine_login_csrf`.
- Python package names (`cms-core`, `cms-validation`, `cms-build`,
  `cms-cli`, `cms-admin`) and import names are unchanged; distribution
  naming on PyPI remains an ADR-0014 decision at first release, now with
  `sardine-cms-*` as the leading candidate.
- Historical documents (ADRs 0001–0015, BRIEF) keep the name they were
  written with; everything current-facing says Sardine CMS.
- The demo domain (`stillsite.ph7x.com`) keeps working; a rename of the
  domain is a separate owner-level DNS decision.

## Consequences

- Existing deployments only need the new env var names when they upgrade;
  the config-file fallback removes any migration urgency.
- The name screening done for "Stillsite" does not transfer: before the
  first PyPI release the `sardine-cms` names must be screened and reserved
  (folded into the ADR-0014 checklist).
