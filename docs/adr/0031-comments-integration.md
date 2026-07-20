# ADR-0031 — Comments: a provider-neutral, consent-first embed contract

- **Status:** accepted
- **Date:** 2026-07-20

## Context

Editors coming from mature publishing systems expect readers to be able
to comment on articles. Sardine CMS builds static sites: there is no
server at request time to store or render a discussion, and the roadmap
(ROADMAP.md, Site features) schedules comments as an integration behind
a theme-contract ADR — not as a bundled subsystem. Whatever we adopt
must survive three constraints that are already contracts elsewhere:

1. **Static-first** (BRIEF): every page is complete without JavaScript
   and without the admin running.
2. **Privacy**: the bundled themes make no external requests
   (conformance-tested). A comments provider is by definition a third
   party — it must never piggyback on a page load.
3. **Determinism**: the same content and configuration produce
   byte-identical builds, provider reachable or not.

## Decision

**The core ships a contract, not a provider.**

- **Configuration**: an optional `[comments]` table in `sardine.toml`:

  ```toml
  [comments]
  provider = "example-provider"     # an extension-registered name
  url = "https://discuss.example"   # provider-specific target, validated https
  ```

  No `[comments]` table → nothing changes anywhere. The bundled build
  stays byte-identical to today's output.

- **Providers are extensions** (ADR-0028): a package registers a comments
  provider under its extension; the provider contributes (a) the island
  asset (vendored JavaScript, served same-origin from the artifact — no
  CDN) and (b) a per-entry thread URL strategy. The core never contains
  provider names or provider endpoints.

- **The theme contract is one context key**: article contexts gain an
  optional `comments` object — `{label, thread_url, island_html}` — only
  when a provider is configured. Themes render it in one place; ignoring
  it keeps working (same pattern as `srcset`, ADR-0029).

- **Consent-first, click-to-load**: the rendered block is a plain link to
  `thread_url` ("Join the discussion") plus a `<site-comments>` island.
  On page load the island makes **zero** requests. Only an explicit
  reader action (activating the block) lets the island load the
  provider's vendored script and reach the provider — the informed-consent
  moment is the click, and the no-JS reader still has the working link.
  No cookies, no storage, no fetches before that action.

- **Accessibility**: the placeholder is a real `<a>` with a localized
  label from the label system (`[site.labels]` overridable); the
  activated state announces itself (`aria-live="polite"`); the block
  passes the same axe gate as every page.

- **Determinism**: the build embeds only the provider name, the thread
  URL and the island asset — all derived from configuration and the
  extension package, never from network calls at build time.

## Consequences

- The theme conformance suite gains a case: with a fake provider
  configured, pages render the link + island and still make no external
  requests at load; without one, output is byte-identical to a build
  before this ADR.
- The first real provider integration lives outside this repository (or
  as a fictional example extension in tests) — the core's surface is the
  contract above and nothing else.
- Validation: a configured provider whose extension is not activated is
  a build error (loud, like Pillow-less image widths in ADR-0029).
