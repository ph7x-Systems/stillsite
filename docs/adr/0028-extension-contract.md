# ADR-0028 — The extension contract: how Sardine CMS grows without forks

- **Status:** proposed
- **Date:** 2026-07-19

## Context

Every extension point so far is a registry: storage engines
(`register_backend`), themes (`register_theme` + the `sardine.themes`
entry-point group), deployment targets (`register_target`), validation
rules (`RuleSet(rules=[...])`). What is missing is the umbrella
contract — how a third-party package plugs new capability into all of
it at once, discoverably, without patching the framework.

## Proposed decision

- **One entry-point group, `sardine.extensions`.** An extension is a
  package exposing a single `Extension` object with optional
  contributions, each reusing the registries that already exist:
  - `validation_rules: list[Rule]` — appended to the project ruleset
    (enable/disable per project stays in `sardine.toml`).
  - `build_steps: list[BuildStep]` — post-artifact hooks
    (`(config, content, artifact) -> None`) that may add or transform
    files; deterministic, ordered by name.
  - `targets`, `storage_backends`, `themes` — registered on load through
    the existing factories.
  - `cli: typer.Typer | None` — mounted as `cms x <name> ...`.
  - `section_kinds: dict[str, FieldHints]` — advertised to the admin's
    section editor hints.
- **Custom article fields** (the model half of extensibility): articles
  gain a `fields: dict[str, str]` free-form map (like sections already
  have), editable in the admin, exported portably, exposed to themes —
  extensions and projects agree on keys, the framework only carries
  them. No dynamic content *types* yet: pages-with-sections plus
  article custom fields cover the known cases without schema magic;
  full custom types would need their own ADR once a real case appears.
- **Loading is explicit**: `sardine.toml` lists `extensions = ["pkg"]`.
  Nothing auto-activates just by being installed — a project states
  what it trusts.
- **Conformance is the license to publish**: the public suites (storage,
  theme, target) stay the contract an extension must pass; the ECOSYSTEM
  policy (ADR-0011) governs listing.

## Consequences

- The extension surface is the sum of surfaces that already exist —
  no new framework concepts, only one discovery-and-activation story.
- The admin, builder and CLI each read from the registries they already
  use; the diff is wiring, not architecture.
- Menu manager, image derivatives and redirects (M6) each land as
  core features, not extensions — they are part of the product's own
  promise.
