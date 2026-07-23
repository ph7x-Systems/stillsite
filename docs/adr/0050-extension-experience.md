# ADR-0050 — Extensions: packaging for discovery, runtime for capabilities, configuration for control

- **Status:** accepted
- **Date:** 2026-07-23

## Context

Extensions have a contract (ADR-0028: one `Extension` object per
package through the `sardine.extensions` entry-point group, activated
by the project's `extensions = […]` list) but no experience: activating
one means editing TOML, and a broken extension fails loudly with no
administrative way back. The theme experience (ADR-0048/0049) proved a
shape worth keeping — this record adapts it where extensions genuinely
differ.

## Decision

Five guarantees:

1. **Discovery is declarative and import-free.** The Extensions screen
   enumerates the `sardine.extensions` entry-point group and renders
   each card from the distribution's own metadata — name, version,
   author, description, license, homepage — exactly as themes do.
   Nothing is imported to produce the list.
2. **Compatibility derives from `Requires-Dist`.** The package's
   declared `sardine-cms-core` range, evaluated against the installed
   version — the same range the installer enforces. Incompatible
   extensions show the verdict and cannot be activated.
3. **Activation is transactional with prior validation.** Activate
   loads the one extension in isolation, then runs a trial build with
   the would-be extension list; only success writes the updated
   `extensions = […]` list — a surgical rewrite. Failure shows its
   error and the configuration stays untouched.
4. **Capabilities exist only after a successful load.** An active
   extension's card lists what its `Extension` object actually
   declares — section kinds, validation rules, providers, packs,
   screens. Capabilities are never inferred statically and never
   invented for inactive extensions.
5. **Failures are isolated, visible and reversible — and recovery
   never needs the broken code.** An active extension that fails to
   load renders its card with the error instead of taking the panel
   down. Deactivation operates directly on the configuration list; it
   must never import the extension it removes, so the recovery path is
   available precisely when the import fails.

## Consequences

- The lifecycle has three clean layers: packaging answers "what is
  installed", the runtime answers "what does it contribute", and the
  configuration answers "what does this project trust".
- "Fail early" keeps its meaning and gains an ending: fail early, show
  the cause, and keep a one-click administrative way back.
- The build/CLI path keeps its loud-failure semantics untouched — the
  containment lives in the panel's screens, not in the contract.
