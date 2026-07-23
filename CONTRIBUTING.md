# Contributing

## Language

Everything that enters git is English: code, comments, docstrings,
tests, commit messages, pull request titles and bodies, issues and
docs. Other languages appear only as product data — language packs,
seed content and translation fixtures.

## Workflow

0. Before every commit run the local gate — after **any** edit, however
   small (a one-line fix after a green run invalidates the run):

   ```bash
   ./scripts/gate.sh          # lint, format, types, full test suite
   FAST=1 ./scripts/gate.sh   # docs-only changes
   ```

1. Create a branch off `main` (`feature/...`, `fix/...`, `docs/...`).
   The project is deliberately trunk-based
   ([ADR-0033](docs/adr/0033-trunk-based-development.md)): one protected
   `main`, short-lived branches, squash-only merges, releases as
   protected `v*` tags. No `develop` branch exists; `release/N.x`
   maintenance branches appear only when a released version first
   needs an isolated patch.
2. Small increments, clear imperative commits (`Add page schema validation`).
   Authorship lives in git metadata: commit messages carry no
   tool-generated attribution (`Generated with/by`, or co-authors at
   automation addresses) — CI enforces this. Human co-authorship
   trailers are welcome when work is genuinely joint.
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

## Your first pull request

- Fork, then branch from an up-to-date `main`. Never base your branch
  on another open pull request — the moment that one squash-merges,
  yours inherits its whole diff as conflicts.
- One topic per pull request; small ones review and merge fast.
- Changelog entries go under `## Unreleased` in CHANGELOG.md. Released
  sections never change.
- CI on a first contribution starts only after a maintainer approves
  the run — that click is manual, so a short wait is normal.
- Keep "Allow edits by maintainers" enabled: it lets a maintainer
  resolve a conflict or apply a small fixup without a round trip.
- Adding a language is a great first contribution:
  [docs/LANGUAGE_PACK_GUIDE.md](docs/LANGUAGE_PACK_GUIDE.md) is the
  whole path, and the project's first external pull request was
  exactly this.

## Panel screens: identifiers and redirects

Three CodeQL rounds distilled one rule for every admin screen:

- Never build a success redirect from user-received parameters.
- Resolve any incoming identifier against a source of truth first — an
  allowlist, a registry, or the loaded object — and from that point on
  work exclusively with the canonical value it returned: storage keys,
  audit records, URLs and redirects all take the canonical value, never
  the raw input.
- In failure flows, render the same page again with validation
  messages instead of redirecting with unvalidated input.

Beyond satisfying static analysis, canonical resolution removes alias,
casing and encoding ambiguity and keeps storage, audit and UI
consistent by construction.

## Contributor credit

External contributions are credited through their pull requests: the
squash commit keeps the contributor as its author, and the merge
message describes the work without appropriating it. Substantial
contributions are also acknowledged in the relevant release notes'
Contributors section and in their changelog entry. Shared authorship
may be recorded with Co-authored-by trailers when contributors jointly
author the same change — maintainer review, integration adjustments or
final fixes do not add the maintainer as co-author.

## Sharing themes, targets, backends and plugins

See [docs/ECOSYSTEM.md](docs/ECOSYSTEM.md): free (OSI) license, the
relevant conformance suite green in your CI, and a registry PR.

## Commands (target)

```bash
cms validate && pytest   # before any PR
```
