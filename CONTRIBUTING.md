# Contributing

## Workflow

1. Create a branch off `main` (`feature/...`, `fix/...`, `docs/...`).
   The project is deliberately trunk-based
   ([ADR-0033](docs/adr/0033-trunk-based-development.md)): one protected
   `main`, short-lived branches, squash-only merges, releases as
   protected `v*` tags. No `develop` branch exists; `release/N.x`
   maintenance branches appear only when a released version first
   needs an isolated patch.
2. Small increments, clear imperative commits (`Add page schema validation`).
3. Before opening a PR: lint, type checking and tests must pass locally.
4. `main` is fully protected, **admins included**: no direct pushes, no
   force-pushes, no deletion. Every change lands via pull request with all
   applicable CI checks green, linear history (squash or rebase merge) and resolved
   conversations. Branches are deleted on merge. The suite currently defines
   ten checks; branch protection promotes a new context only after a green
   `main` run proves its stable name.

## Project rules

- No editorial text hardcoded in templates — all content comes from the content model.
- Language parity is mandatory: EN is the source; PT-PT, ES, FR and DE are validated.
- Deterministic build: the same input produces the same output.
- No secrets, personal data or client content.
- Architecture decisions recorded in `docs/adr/`.
- WCAG 2.2 AA accessibility as the baseline for the admin panel and reference theme.
- **Docs move with the code**: any change that affects behavior, structure or
  plans updates README/PLAN/ADRs and the public wiki in the same delivery
  chain. `tests/test_docs.py`
  compares the docs against the code in CI, so drift fails the build — when
  adding a documented fact worth guarding, add its check there too. Keep each
  fact in one authoritative document and link to it instead of repeating it.
  If the wiki cannot be synchronized before the PR opens, record it explicitly
  as a blocking rollout item; do not silently omit it.

## Sharing themes, targets, backends and plugins

See [docs/ECOSYSTEM.md](docs/ECOSYSTEM.md): free (OSI) license, the
relevant conformance suite green in your CI, and a registry PR.

## Commands (target)

```bash
cms validate && pytest   # before any PR
```
