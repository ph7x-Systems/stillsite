# ADR-0049 — The theme manifest is the package's own metadata

- **Status:** accepted
- **Date:** 2026-07-23

## Context

The Themes screen (ADR-0048) lists what the environment can activate
without loading code. Its cards need more than a name: description,
author, license, homepage, a screenshot and whether the theme is
compatible with this installation. Inventing a manifest format would
mean a second source of truth that drifts from the package.

## Decision

- **No new format.** Everything the panel presents comes from the
  distribution's own metadata, read through `importlib.metadata`
  without importing theme code: name and version from the
  distribution, description from `Summary`, author from
  `Author`/`Author-email`, license from the license expression, the
  homepage from `Project-URL`. A theme's packaging *is* its manifest.
- **Compatibility is the dependency it already declares.** A theme
  package depends on `sardine-cms-build` with a version range; the
  panel evaluates that range against the installed version and shows
  the verdict. Nothing new to declare, nothing that can contradict
  reality: the same range pip enforces is the one the panel shows.
- **The screenshot is a file convention.** A distribution may ship a
  file named `theme-screenshot.png` (or `.jpg`/`.webp`); the panel
  finds it through the distribution's file list — still without any
  import — and serves it to signed-in admins from its own route.
  Absence is fine: the card renders without an image.
- **Bundled themes get literals.** The built-in default theme has no
  distribution; its card fields are hardcoded next to its
  registration.
- Declared capabilities stay with the extension contract work; themes
  need none today and the field is not invented ahead of a use.

## Consequences

- The panel keeps treating themes as declarative artifacts: at no
  point between listing, card rendering and the activation click does
  third-party code run — the first execution remains the trial build
  the operator asked for.
- Theme authors improve their cards by improving their packaging —
  the same fields PyPI shows — plus one optional image file.
- A stale compatibility range shows up honestly as "incompatible
  here", because it is the same range the installer would refuse.
