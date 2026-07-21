# ADR-0033 — Trunk-based development: one protected main, no develop branch

- **Status:** accepted
- **Date:** 2026-07-21

## Context

The repository runs on a single long-lived branch. As the project grows
the question deserves a recorded answer rather than an accident: is
`main`-only right for a product with continuous demo deployment, lockstep
PyPI releases and an ambition of long-term maintenance?

The alternatives are the classic multi-branch models: a permanent
`develop` integration branch with release branches cut from it, or
per-version maintenance branches from day one.

## Decision

**Trunk-based development, deliberately.**

- One protected `main`. Every change — feature, fix, docs — lands through
  a short-lived branch (`feat/…`, `fix/…`, `docs/…`) and a pull request
  with all ten CI contexts green. Squash is the **only** merge method
  (merge commits and rebase-merge are disabled in the repository
  settings), so `main` stays a linear sequence of reviewed, releasable
  units and every commit maps to exactly one PR.
- `main` is always releasable: the demo deploys from it on every merge,
  and releases are annotated `v*` tags cut from it (protected by a tag
  ruleset — no deletion, no moving). The six packages version in
  lockstep, so one tag describes the whole product.
- Branches delete on merge; nothing long-lived exists besides `main`.

**Why not a `develop` branch:** an integration branch buys isolation for
teams that batch features into scheduled releases. This project releases
continuously, keeps `main` releasable by CI construction, and a second
long-lived branch would only add merge ceremony, drift surface and a
place for the demo and the code to disagree.

**When maintenance branches appear:** the first time a released version
needs a patch that must not carry newer work (expected after 1.0, e.g. a
security fix for `1.0.x` while `1.1` is in flight), a `release/N.x`
branch is cut **from the tag**, receives cherry-picks only, and gets the
same protection as `main`. Until that day, no release branches exist —
they are created by need, not in advance.

## Consequences

- CONTRIBUTING documents the flow; branch protection enforces it
  (PR-only, ten required checks, strict up-to-date, no force-push).
- History stays linear and auditable: `git log main` reads as the
  changelog's skeleton.
- Nothing blocks parallel work: any number of short-lived branches can
  exist concurrently; serialization happens at the merge queue, not in
  branch topology.
