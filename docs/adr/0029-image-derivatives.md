# ADR-0029 — Image derivatives: responsive sizes at build time

- **Status:** accepted
- **Date:** 2026-07-19

## Context

The media pipeline copies images verbatim; every visitor downloads the
original. Responsive sites ship width-appropriate variants via
`srcset` — a build-time job in a static-first CMS.

## Decision

- **Opt-in per project**: `[build] image_widths = [480, 960]` in
  `sardine.toml`. Empty (the default) changes nothing — no new
  dependency, byte-identical artifacts as before.
- **Pillow behind an extra** (`sardine-cms-build[images]`): when widths
  are configured and Pillow is missing, the build fails loudly with the
  install hint — never a silent quality downgrade.
- **Derivatives keep the original format** (png/jpeg/webp; svg and gif
  pass through untouched) and land next to the original as
  `media/<stem>@<width><suffix>`. Only widths smaller than the original
  are generated; the original remains the `src` and the largest
  candidate.
- **Determinism holds**: fixed resampling (LANCZOS), fixed encoder
  parameters, no timestamps — same input, same widths, same bytes.
- **Themes get `srcset` for free**: the builder's image contexts gain a
  `srcset` string when variants exist; both bundled themes render it
  with `sizes="100vw"` as the safe default. Themes that ignore `srcset`
  keep working.

## Consequences

- The artifact grows by the configured variants; hashes stay
  content-derived.
- Crop/focal-point control is a separate, later decision — derivatives
  only scale.
