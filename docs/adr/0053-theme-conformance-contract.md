# ADR-0053 — The theme conformance suite is a public, versioned contract

- **Status:** accepted
- **Date:** 2026-07-23

## Context

A theme conformance suite existed as repository tests: real checks,
but reachable only by copying test files that import private fixtures.
The theme experience (ADR-0048/0049) made themes first-class artifacts;
what "being a Sardine theme" means deserved the same treatment the
storage, deployment and forms contracts already have — an executable
specification anyone can import.

## Decision

- **The suite is a public module**: `cms_build.theme_conformance`,
  carrying `CONFORMANCE_VERSION`, self-contained fictional sample
  content, and `conformance_checks()` — every check named, each a
  callable taking a `Theme`. A third-party theme proves conformance by
  parametrizing its own tests over the checks; no repository files to
  copy, no private fixtures.
- **The contract is what the checks enforce**, fifteen today: the
  `[hidden]` rule first; no external requests from assets; no inline
  styles in rendered pages; images with dimensions; reduced-motion
  honored; the JavaScript budget; fonts and local references that
  resolve; every gallery kind rendering every advertised field;
  unknown kinds degrading generically; flow-relative CSS only;
  unbounded item repetition; legacy numbered fields; safe Markdown
  rendering; page bodies as prose.
- **Certification is proven, not claimed.** The repository runs the
  full contract against every bundled theme in CI; both current themes
  pass unchanged — the suite ships already validated by real
  consumers.
- **The version moves with the contract.** Adding or strengthening a
  check bumps `CONFORMANCE_VERSION` and lands in the changelog like
  any public contract change; ecosystem listings state the version a
  theme was certified against.

## Consequences

- "A starter theme is accepted when it passes the conformance suite in
  full" becomes an objective acceptance rule — community themes get a
  machine-checkable bar instead of subjective review.
- The theme/extension experience epic can close on a complete
  platform: discovery, cards, activation, health, settings and an
  executable definition of the artifact itself.
- Repo-specific checks (the admin stylesheet, the comments contract)
  stay repository tests: the public contract carries only what applies
  to every theme everywhere.
