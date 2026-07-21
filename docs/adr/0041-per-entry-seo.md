# ADR-0041 — Per-entry SEO controls

- **Status:** accepted
- **Date:** 2026-07-21

## Context

SEO output (title, description, canonical, hreflang, Open Graph,
JSON-LD) is derived site-wide by the builder's head contract — one
place, never hand-assembled. Editors need per-entry control without
breaking that discipline: overrides must flow through the same
derivation, never become a second source of truth.

## Decision

- **A `Seo` submodel on the per-language content** of articles and
  pages: `seo_title`, `seo_description` (translatable overrides for
  the derived title/description), `noindex` (robots), `canonical`
  (absolute URL override) and `og_image` (a media-library asset id
  for the social card). Empty values mean "derived" — the default
  behaviour is exactly today's.
- **Per language, deliberately**: titles and descriptions are
  editorial text; canonical URLs differ per language; even `noindex`
  can legitimately differ. The fields join the content checksum, so
  editing the source's SEO marks translations outdated — the
  translation queue surfaces the work instead of shipping stale
  overrides silently.
- **Persistence** is one `seo_json` column per content table
  (articles, article translations, pages, page translations) — the
  same opaque-payload precedent as custom fields; the schema never
  grows a column per SEO knob. The portable format round-trips the
  submodel.
- **The head contract stays the single derivation point**: overrides
  enter `build_head`, which emits each tag exactly once. A `noindex`
  entry keeps its canonical and hreflang cluster (the cluster
  describes alternates, not indexability). A canonical override
  replaces the derived URL for that language only.
- **Open Graph images** resolve through the media pipeline: the
  published rendition (crop applied), with the site's absolute URL.

## Consequences

- Both bundled themes render the head from the same object — no theme
  changes are needed for correctness, only the head partials' new
  optional tags (robots, og:image).
- Validation gains advisory length/missing-field hints (warnings,
  configurable, never a gate) in a follow-up increment, alongside the
  editor surface and the automatic redirect on slug change.
- The Content API surfaces the fields additively.
