# Ecosystem — sharing themes, targets, backends and plugins

Sardine CMS is free software (Apache-2.0) and its extension seams are public
contracts. This page is the community handbook: how to build something
shareable, license it, name it, and get it listed. Policy rationale lives in
[ADR-0011](adr/0011-community-ecosystem-policy.md).

## What can be shared

| Kind | Contract | Conformance gate |
| --- | --- | --- |
| Theme | `Theme` protocol + `register_theme` ([THEME_GUIDE.md](THEME_GUIDE.md)) | Theme checklist (THEME_GUIDE) + output-integrity suite |
| Deployment target | `Target` protocol + `register_target` (ADR-0005) | Adapter tests over a built artifact |
| Storage backend | `StorageBackend` + `register_backend` (ADR-0004) | The storage conformance suite, unchanged |
| Validation rules / plugins | `Rule` protocol + `RuleSet` | Rule unit tests; plugin mechanism ADR pending |

## Licensing

- Your package, your copyright, your license — as long as it is an
  **OSI-approved free license**. Recommended: **MIT** or **Apache-2.0**
  (both compose cleanly with the framework).
- Non-free or source-available licenses (BUSL, SUL, …) are your right to
  choose, but such packages are **not listed** in the registry.
- You keep full commercial freedom: building and selling sites, support or
  hosting with Sardine CMS is exactly what the Apache-2.0 core is for.

## Naming

Expressly permitted package-name patterns (limited nominative trademark
grant — see ADR-0011):

```text
sardine-theme-<name>        sardine-target-<name>
sardine-backend-<engine>    sardine-plugin-<name>
```

Not permitted: the Sardine CMS logos, "official" claims, or names implying
pH7x Systems authorship. Official packages live in the `ph7x-Systems`
GitHub organization.

## Getting listed

Open a pull request adding one row to the registry below. Requirements
(objective, reviewed like code):

1. OSI-approved license, stated in the repo.
2. The relevant conformance gate green in **your** CI (link the run).
3. README with a quickstart a stranger can follow.

Delisting follows the same path: a PR with evidence of the failing gate.
Tag your repo with the GitHub topics `sardine-cms` and the kind
(`sardine-theme`, …) for discovery.

## Registry

| Package | Kind | License | Maintainer | Conformance |
| --- | --- | --- | --- | --- |
| _(empty — be the first: open a PR)_ | | | | |

Extensions plug in through the `sardine.extensions` contract
(ADR-0028): explicit activation in `sardine.toml`, contributions through
the public registries, conformance suites as the license to publish.
