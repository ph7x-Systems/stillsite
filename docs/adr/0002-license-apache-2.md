# ADR-0002 — License: Apache License 2.0

- **Status:** accepted
- **Date:** 2026-07-17

## Context

The repository is private today but will become public. The framework is meant
to be reused by third parties (companies building multilingual static sites),
while pH7x Systems keeps using it commercially in its own products. The license
had been left as an open decision in the README and PLAN.

Options considered:

- **MIT** — maximally simple and permissive, but grants no explicit patent
  license and has no built-in trademark protection.
- **Apache-2.0** — permissive like MIT, adds an explicit patent grant
  (Section 3), explicit trademark carve-out (Section 6), and a contribution
  inbound=outbound rule (Section 5) that removes the need for a CLA.
- **AGPL-3.0** — strong copyleft; would deter adoption by the companies this
  framework targets and complicate pH7x Systems' own commercial use.

## Decision

Use the **Apache License 2.0** with a `NOTICE` file crediting pH7x Systems.

## Consequences

- Third parties can adopt, embed and extend the framework commercially, which
  maximizes adoption once public.
- Contributors automatically license their contributions under the same terms
  (no separate CLA needed).
- The pH7x Systems name and branding remain protected (trademark carve-out); the
  reference theme ships design tokens only, so publishing it does not license
  the brand identity.
- `LICENSE` and `NOTICE` live at the repository root; the README license
  placeholder is replaced.
