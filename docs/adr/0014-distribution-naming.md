# ADR-0014 — Distribution naming: `sardine-cms-*` on PyPI

- **Status:** accepted
- **Date:** 2026-07-19

## Context

The release plan reserved this decision for the first PyPI release: publish
the packages as generic `cms-*` names or under a product prefix. Two things
happened since the plan was written: the product was renamed to Sardine CMS
(ADR-0016), and the ecosystem policy (ECOSYSTEM.md) already prescribes
`sardine-*` prefixes for community themes, targets, backends and plugins.

## Decision

- **Distribution names:** `sardine-cms-core`, `sardine-cms-validation`,
  `sardine-cms-build`, `sardine-cms-cli`, `sardine-cms-admin`,
  `sardine-cms-theme-ph7x-reference`.
- **Import names are unchanged** (`cms_core`, `cms_validation`, `cms_build`,
  `cms_cli`, `cms_admin`, `cms_theme_ph7x_reference`), as is the `cms`
  command. Distribution and import names serve different masters: the
  first must be globally unique and say whose it is; the second should be
  short at every call site.
- Internal dependencies reference the new distribution names.
- **Versioning:** semantic versioning from `0.1.0`, in lockstep across the
  six packages (one repo, one release train, one tag `vX.Y.Z`); each
  version is single-sourced in its package's `pyproject.toml`. The
  changelog is hand-written in `CHANGELOG.md`.
- **Publishing:** GitHub Actions on version tags via PyPI **trusted
  publishing** (OIDC) — no long-lived tokens anywhere.

Rationale for the prefix: generic `cms-*` names are squat-prone,
collision-prone and say nothing about origin; `sardine-cms-*` groups the
project on PyPI, matches the repository name and the ecosystem policy, and
leaves `sardine-<kind>-<name>` open for the community exactly as
ECOSYSTEM.md documents.

## Consequences

- Before the first release the owner must create the six **pending
  publishers** on PyPI (trusted publishing: repository
  `ph7x-Systems/sardine-cms`, workflow `release.yml`, environment `pypi`) —
  a web-UI step only the PyPI account holder can do.
- Editable installs from source are unaffected; only the names on PyPI and
  in inter-package dependency declarations change.
