# Contributing

## Workflow

1. Create a branch off `main` (`feature/...`, `fix/...`, `docs/...`).
2. Small increments, clear imperative commits (`Add page schema validation`).
3. Before opening a PR: lint, type checking and tests must pass locally.
4. `main` is protected — merge only via pull request with green CI.

## Project rules

- No editorial text hardcoded in templates — all content comes from the content model.
- Language parity is mandatory: EN is the source; PT-PT, ES, FR and DE are validated.
- Deterministic build: the same input produces the same output.
- No secrets, personal data or client content.
- Architecture decisions recorded in `docs/adr/`.
- WCAG 2.2 AA accessibility as the baseline for the admin panel and reference theme.

## Commands (target)

```bash
cms validate && pytest   # before any PR
```
