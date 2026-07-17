# ADR-0007 — Per-project theme overrides via file shadowing

- **Status:** accepted
- **Date:** 2026-07-17

## Context

The extensibility contracts require that a project can change any template,
partial or design token without forking its theme. The override mechanism had
been left open when the theme interface landed (ADR-0006).

## Decision

File shadowing over the theme's own files, rooted at the project's `theme/`
directory:

- `theme/templates/<name>.html.j2` takes precedence over the theme's template
  of the same name (Jinja `ChoiceLoader`: project first, theme second). An
  override can still `{% extends %}` theme templates.
- `theme/assets/<name>` replaces or adds to the theme's assets; hashed asset
  URLs update automatically, so an overridden stylesheet busts caches by
  construction. Design-token overrides are asset overrides (tokens live in
  CSS custom properties).
- Theme factories receive the overrides directory: `create_theme(name,
  overrides)`; the CLI passes `<project>/theme` when it exists. Themes that
  ignore overrides simply don't support them.

## Consequences

- Zero configuration: dropping a file in `theme/` is the whole API.
- Overrides survive theme upgrades (no fork to rebase); a project's diff
  against the stock theme is exactly the contents of its `theme/` directory.
- The same mechanism will serve the Milestone 4 reference theme unchanged.
