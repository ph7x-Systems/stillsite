# Changelog

All notable changes to Sardine CMS. The project follows semantic versioning
from `0.1.0`; the six packages release in lockstep under one `vX.Y.Z` tag.

## Unreleased

- **The section model's growth path is decided** (ADR-0037, accepted):
  structured sections stay the contract — opaque block-markup bodies
  are rejected because multilingual parity, validation and the
  portable JSON source of truth need data, not markup blobs — and the
  three real restrictions get fixes: unbounded translatable `items`
  replace numbered fields with caps hidden in templates (`q6`,
  `row8`), section kinds will declare Markdown-capable fields, and
  pages gain a long-form `body_markdown`. The editor stays
  server-rendered; a drag-and-drop visual builder is explicitly
  deferred to its own ADR. Docs and roadmap now state the current
  limits honestly.

- **ADR-0034 closes: language packs are an ecosystem** (M8): the
  authoring guide (docs/LANGUAGE_PACK_GUIDE.md + wiki) documents the
  whole contract, ECOSYSTEM.md gains the `sardine-lang-<tag>` naming
  grant and a registry row, a data-only pack extension is proven in
  the test suite, and CI now drives a fictional RTL build through the
  axe accessibility gate on every push. The new probe immediately paid
  for itself: it caught the builder skipping pages (not articles) of a
  non-default source language — fixed, and the end-to-end test now
  covers pages too.

- **The panel's languages come from packs too** (M8, ADR-0034 admin
  phase): the four shipped gettext catalogs moved out of the admin's
  file tree into their language packs (`LanguagePack.admin_catalog`,
  with a `native_name` for selectors) — activating an extension pack
  that carries a catalog is now the whole job of adding a panel
  language, offered in the switcher by its own name and mirrored
  (`dir="rtl"`) when the pack says so. Every editor surface — lists,
  editors, dashboard matrix, media alt coverage, the publish gate and
  the validation report — now reads the project's configured source
  and target languages instead of module constants, and the media
  model requires alt text in *some* language rather than hardcoding
  which one.

- **RTL is real, permanently** (M8, ADR-0034): every physical CSS
  property in the bundled themes and the panel stylesheet became its
  flow-relative twin (`margin-inline-start`, `padding-inline`,
  `text-align: start/end`, `inset-inline-*`), so a pack-declared
  `dir="rtl"` now mirrors the layout instead of just the text. The
  theme conformance suite enforces it forever — physical properties and
  asymmetric four-value shorthands fail any theme, third-party ones
  included — and the sweep already caught one hand-audit miss. Axe
  stayed green over the example site in both color schemes.

- **The source language is configurable** (M8, ADR-0034):
  `[site] source_language` (default `en`) accepts any registered pack
  tag — the URL root, hreflang x-default, feeds, label and alt-text
  fallbacks, menu labels and the validation parity gates all follow it,
  and the source never doubles as a target. A stored translation now
  always wins over the source shortcut, so a project whose source is
  not `en` can still target `en` correctly. Existing projects change by
  nothing: the whole suite passed untouched, and a fictional pack-tag
  source builds with its language at the root and RTL from its pack.

- **No language data outside packs** (M8, ADR-0034): the bundled five
  languages' UI labels, month names and date patterns moved into their
  `LanguagePack`s and the hardcoded tables in `cms_build.ui` are gone —
  label and date resolution is now one uniform path (project override →
  the language's pack → the source pack → the key), identical output
  proven by the full suite. Contributing a language and shipping the
  bundled ones now use exactly the same mechanism.

- **Lists stop growing with languages**: the per-language badge strip in
  the content lists becomes a constant-width coverage summary
  (`3/4 · 1 missing`) linking to the editor — with unbounded language
  packs (ADR-0034), no admin surface may grow horizontally per
  language. The roadmap gains the full multilingual map: what already
  leads (checksum states, parity gates, packs end to end) and what
  ships next (bundled five as full packs, configurable source language,
  admin catalogs from packs, full RTL, translation queue, state
  filters).

- **Language packs work end to end** (M8, ADR-0034 phase 1b): a
  `LanguagePack` bundles a locale's identity, text direction, site
  labels, month names and date pattern; extensions contribute packs via
  `Extension.language_packs`, and an activated pack's tag becomes a
  full content language — configurable in `sardine.toml`, built,
  labeled, date-formatted and rendered with `dir="rtl"` on `<html>`
  when the pack says so, in both bundled themes. A configured tag
  without its pack still fails loudly. The five bundled languages are
  now packs too (direction; their labels and date tables migrate in the
  next phase).

- **The locale set opens** (M8, ADR-0034 phase 1a): `Language` is no
  longer a closed five-member enum but an interned, validated tag type
  with the exact same surface — identity comparisons, `.value`, class
  iteration and `ValueError` on unknown tags all behave as before, and
  the entire test suite passed without touching a single call site.
  `Language.register(tag)` is the new entry point language packs will
  use; until a pack registers a tag, behavior is unchanged.

- **Internal dependencies are bounded to the release series**
  (`>=0.2.0,<0.3`): a half-published release can no longer hand new
  installs a mix of package versions — the resolver now refuses instead
  of breaking at import time.
- **Publishing gains a fallback**: OIDC trusted publishing stays the
  primary path; when it fails, the job retries with the repository's
  API-token secret so a PyPI publisher mismatch can never stall a
  release again (the v0.2.0 lesson).

## 0.2.0 — 2026-07-21

Three milestones in one release: editorial completeness (M5),
extensibility and adoption (M6) and operations (M7) — the capability
inventory in docs/ROADMAP.md tells the full story.

- **`cms doctor` closes M7**: one read-only command diagnoses the
  machinery around the content — configuration (theme, extensions,
  comments provider, Pillow when image widths are configured), storage
  connectivity and schema level, content counts, referenced media files
  on disk, Python and lockstep package versions. Exit 1 on any failure;
  content-level problems remain `cms validate`'s job.

- **On-publish webhooks** (M7, ADR-0036): with `SARDINE_WEBHOOK_URL` +
  `SARDINE_WEBHOOK_SECRET` set, transitions that change the public site
  (into and out of `published`) POST a minimal signed JSON doorbell —
  HMAC-SHA256 over the exact body in `X-Sardine-Signature` — to the
  receiver, retried three times with backoff off the request path.
  HTTPS enforced (loopback exempt for development); a URL without a
  secret fails startup; unset means nothing changes anywhere.

- **Two-factor enforcement by role** (ADR-0035 amendment):
  `SARDINE_ADMIN_REQUIRE_2FA` names the minimum role at/above which
  two-factor is mandatory. Covered accounts without it still sign in
  but every route corrals them to the enrolment page until a code
  confirms; disabling is refused while the policy applies; unknown
  values fail startup loudly.

- **Two-factor authentication** (M7, ADR-0035): self-service TOTP —
  RFC 6238 with the standard library only, enrolment confirmed by a
  valid code, single-use codes (replay refused), wrong codes spending
  the same login rate budget, disable gated by a current code. Storage
  migration 17 on all four engines; panel strings in the four
  languages. Recovery is `cms admin create-user --force`; password
  reset deliberately does not clear the second factor.

- **Editorial notifications** (M7, ADR-0032 phase 2 — the ADR is now
  accepted): a transition into review mails every reviewer-and-above
  account with an address (except the actor), and publishing mails the
  entry's most recent editing author. Plain-text messages in each
  recipient's panel language, delivered fire-and-forget through the
  pluggable transport; failures are recorded, never editorial errors;
  without a configured transport nothing changes at all.

- **Password reset, with a pluggable mail contract** (M7, ADR-0032
  phase 1): accounts gain an optional email address (Users screen,
  `cms admin create-user --email`; migration 15) and the login page —
  when email is configured — offers an enumeration-safe reset: identical
  response for any username, hashed single-use tokens expiring in 30
  minutes (migration 16), the password policy enforced and **every
  session of the account revoked** on completion. Messages are plain
  text in the recipient's panel language. Delivery goes through a named
  transport: `smtp` (standard library, STARTTLS/TLS) ships as the
  baseline, and `Extension.mail_transports` lets extensions register
  passwordless provider-API transports (ADR-0028 pattern) selected via
  `SARDINE_MAIL_TRANSPORT`. Unconfigured email keeps the panel exactly
  as before. Language stays abstract throughout — and the roadmap now
  pins it as a standing invariant: languages are rows, keys and
  configuration, never schema columns or fixed enumerations; the
  language-pack ADR (arbitrary locales, contributable packs, RTL/LTR)
  opens Milestone 8.

- **The scope is written down**: the roadmap now carries the full
  capability map toward a complete static-first CMS — new scheduled rows
  (bulk actions, admin-wide search, scheduled unpublish, editorial
  calendar, audit log, WebP/AVIF derivatives, media organization,
  per-entry SEO controls) and ADR-first items (custom taxonomies,
  content relations, crop/focal point, embeds, forms, analytics,
  external review links, arbitrary locales, SSO) organized into
  Milestones 8 and 9 with plans in PLAN.md. ADR-0033 records the
  branching strategy: trunk-based, one protected main, squash-only,
  protected release tags — maintenance branches cut from tags only when
  first needed.

- **The content API closes M6**: `content_api = true` under `[build]`
  makes every build also emit versioned JSON under `api/v1/` —
  `site.json` plus one `content.json` per language with articles
  (slugs, rendered bodies, categories, tags, cover metadata incl.
  `srcset`, custom fields) and pages with their typed sections. Exactly
  the HTML build's publication, scheduling, trash and language-parity
  gates; deterministic; the contract tests are public
  ([CONTENT_API.md](docs/CONTENT_API.md)). Enabled on the live demo.

- **Comments, as a contract** (M6, ADR-0031): a `[comments]` table in
  `sardine.toml` selects a provider an activated extension registers
  (`Extension.comments_providers`) — the core ships no provider and no
  third-party endpoint. Every article gains a localized "Join the
  discussion" link (the page stays complete without JavaScript) wrapped
  in a `<site-comments>` island whose script ships same-origin from the
  artifact; nothing may reach the provider before an explicit reader
  action. A configured provider no activated extension offers fails the
  build loudly; without the table, builds are byte-identical to before.
  Conformance-tested in both bundled themes; the fictional example
  passes the accessibility gate.

- **Reference theme stylesheets cleaned to contract**: the four CSS files
  inherited from the original site import now speak English only (repo
  language rule), lose every rule for components this theme never renders
  (consent banner, client carousel, case studies, certifications, process
  rail, canvas backdrop, contact form) and keep the load-bearing comments
  as documentation. Also adds the missing `-webkit-backdrop-filter`
  fallback. No visual change — the removed selectors matched no element
  any template emits.

- **The section-kind gallery becomes a contract** (M6): reusable blocks
  now have one source of truth — `SECTION_KIND_GALLERY` maps each bundled
  kind to the fields it consumes, and four new kinds join the nine-strong
  gallery: pull **quote**, **faq** (native `<details>`, no JavaScript),
  **cta** (per-language target URL) and image **gallery** (`srcset`-aware
  grid). Both bundled themes render every kind; unknown kinds keep falling
  back to the generic renderer (conformance-tested). The section editor's
  suggestions come from the same gallery and now merge kinds advertised by
  activated extensions (ADR-0028). The seeded demo shows a FAQ on the home
  page and a crew quote on the About page in all five languages; the Theme
  Guide gains the authoring table. Also repairs broken selector lines in
  the reference theme's stylesheet that were silently disabling its
  large-button styles.

- **System security hardening**: hostile XML now goes through `defusedxml`;
  preview/media files require authentication; uploads are bounded before
  allocation, reject active SVG and excessive pixel counts, and never replace
  an existing path. Login CSRF comparisons are constant-time, password work
  is equalized for unknown users, and username rotation cannot evade the
  bounded client limiter. CLI credential replacement enforces the password
  policy and revokes every existing session.
- **Supply-chain hardening**: workflow actions are pinned to full commits,
  downloaded axe assets are checksum-verified, secret scanning uses a pinned
  container digest, and Azure deployment consumes an isolated build artifact.
  A required `pip-audit` + Bandit security gate now runs on every PR. Managed
  CodeQL and enhanced secret scanning are enabled, and dynamic admin redirect
  paths encode every route segment.

- **Live themed refresh + autosave** (M6, ADR-0027 phase 2): valid
  article/page source edits persist after a short debounce and refresh a
  scoped entry artifact through the real builder and theme, drafts included.
  Invalid intermediate forms pause without overwriting content; autosaves do
  not consume the bounded revision history, while explicit Save still does.
  Requests are serialized, CSRF-protected and announced through an accessible
  localized status line.

- **External blog import** (M6, ADR-0030): the WXR 1.2 adapter converts
  foreign posts into Sardine articles — common HTML becomes Markdown;
  workflow status, dates,
  author, category and tags are retained. The adapter is deterministic,
  performs no network access and rejects DTD/entity declarations. Foreign
  pages, attachments, menu items and comments are counted and skipped
  instead of receiving invented mappings.

- **Portable round-trip** (M6): the portable format is now complete
  (slugs, category, tags, cover, trash flag included) and gains its
  commands — `cms dump` writes `content.json` + the Markdown tree,
  `cms import` reads it back losslessly into any project (byte-verified
  round-trip test). This is the backup, the restore path and the
  instance-migration story in one pair.

- **Redirects** (M6): a `[redirects]` map in `sardine.toml` becomes
  real 301s on the SWA and nginx targets, and the builder ships
  meta-refresh fallback pages (canonical set, noindex) so redirects
  work on any static host.

- **Image derivatives** (M6, ADR-0029): opt-in responsive sizes at
  build time — `[build] image_widths = [480, 960]` plus the
  `sardine-cms-build[images]` extra (Pillow). Derivatives keep the
  source format, never upscale, and stay deterministic; the builder's
  image contexts gain `srcset` and both bundled themes render it.
  Configured widths without Pillow fail the build loudly.

- **Menu manager** (M6, migration 14): explicit navigation from the
  panel — per-language labels with source-language fallback, numeric
  ordering, internal or external URLs. Defined items replace the
  automatic menu on the next build; an empty list keeps the automatic
  one (home anchors + blog + published pages). Carried in the portable
  export.

- **The extension contract** (ADR-0028): packages plug in through one
  `sardine.extensions` entry point (or a dotted path) — validation
  rules, deterministic build steps, deployment targets, storage
  backends, themes, a `cms x <name>` CLI mount and section-kind hints.
  Activation is explicit in `sardine.toml`; nothing activates just by
  being installed. Articles gain free-form custom fields (migration 13)
  — editable in the panel, exported portably, exposed to themes.

- **M5 closes: editorial notes and list quick actions.** Every article
  and page carries a team-only note trail (never published, never
  exported; the author or an admin removes) — storage migration 12 on
  all four engines. The content lists gain a per-row actions dropdown:
  workflow transitions and trash without opening the editor.

- **Design-aware editing** (ADR-0027, owner-approved): the article and
  page editors gain a Design preview — the entry rendered by the real
  builder and the real theme, framed from `/preview/` and refreshed on
  every save. Only the `/preview/` mount allows same-origin framing;
  the admin document itself remains unframeable.

- **Featured and authorship** (M5, migration 11): articles gain a
  Featured flag — featured entries lead the home highlight while
  listings and feeds keep pure recency — and an editorial byline the
  themes render (site name when empty). The demo snapshot captures the
  Users page (its sidebar link 404ed), and a new anti-recurrence test
  asserts every sidebar entry exists in the snapshot. ADR-0027
  records the direction for design-aware editing.

- **Media library filters** (M5): server-side search over id, path, MIME
  type and alt texts, plus quick views (images only, missing translated
  alt) with a shown-of-total counter — a plain GET form, no JavaScript
  required.

- **Users screen** (M5): admins manage accounts from the panel — create
  (with role and panel language), change roles, delete — with the
  safeguards that matter: you cannot delete yourself, and the last admin
  can neither be deleted nor demoted. The CLI remains the bootstrap for
  the first account.

- **Duplicate as draft and per-entry preview** (M5): one click copies an
  article or page — content, metadata and sections intact, fresh
  collision-safe id, workflow reset to draft, no schedule, no trash
  flag; and the editors link straight to the entry's own URL inside
  `/preview/`. The demo snapshot now captures the Trash page (it 404ed
  on the live demo).

- **Trash** (M5, ADR-0026): deleting becomes reversible — Move to trash
  hides an article or page from builds, validation, export and every
  list; the Trash page restores it exactly as it was, and Delete forever
  (admin role, trash-only) is the panel's single permanent removal.
  Storage migration 10 on all four engines.

- **Revisions with restore** (M5, ADR-0025): every article and page save
  from the panel keeps a snapshot (bounded at the newest 20 per entity,
  storage migration 9 on all four engines). The editors list the
  history; each revision shows a unified diff against the current
  content and restores with one click — the restore itself becomes a
  new revision, so it is always undoable.

- **Scheduled publishing** (M5, ADR-0024): articles and pages gain an
  optional `publish_at` (UTC) — published content with a future moment
  stays out of every build until a build runs after it; the build is the
  clock and stays deterministic for the same content and clock. Editors
  set it with a native date-time field (localized); storage migration 8
  covers all four engines; the portable export carries the field; the
  scheduled-builds CI recipe is documented in the admin guide.

- **Responsive lists**: the per-language columns collapse into one
  compact Translations cell of state-colored badges (linked to the
  translation editors; state also in the title and hidden text, never
  color alone), and every admin table sits in Bootstrap's
  `table-responsive` wrapper — no more horizontal page scroll on
  narrow screens.

- **Direct unpublish** (M5): published content goes straight back to
  draft with one click (publisher role and up) — no more
  archive-then-restore detour. The next build drops the entry from the
  site, as always.

- **Markdown editor for article bodies** (ADR-0023): EasyMDE (MIT,
  vendored, no CDN) with a Bootstrap-Icons toolbar in the editor's
  language, attached progressively — without JavaScript the plain
  textarea still works. The builder's server-rendered preview remains
  the single truth (EasyMDE's own preview is disabled). CSP note: style
  attributes are now allowed for vendored runtime code (CodeMirror,
  Popper); scripts stay strictly same-origin.

- **The admin panel speaks the editor's language** (ADR-0022): real
  gettext i18n — PT-PT, ES, FR and DE catalogs shipped, resolution by
  stored per-user preference (new language selector in the user menu,
  `cms admin create-user --language`) then `Accept-Language`, then EN.
  Storage migration 7 adds the preference column on all four engines. An
  anti-drift test keeps every catalog complete.

- The sidebar brand and the user avatar are now plain `<img>` elements
  styled entirely by AdminLTE's own rules (the invented sizing CSS is
  gone); the admin panel's localization strategy joins the M6 roadmap.

- **Admin chrome 1:1 with the AdminLTE reference pages**: theme-init
  before first paint (external file — the CSP still allows no inline
  scripts), the reference's stylesheet order, fullscreen toggle, the
  light/dark/auto color-mode switcher, and the canonical user menu
  (user-header/user-footer). The axe CI gate now audits the admin in
  **both color schemes**; the demo snapshot's Preview link points at the
  public site (the snapshot cannot serve /preview/).

- **Error pages for every host** (ADR-0021): each build now ships
  `401.html`, `403.html`, `404.html` and `50x.html` (localized titles via
  the label system, rendered through the theme's `not_found` template).
  The SWA config overrides 401/403/404, the nginx config maps all four
  groups including 500/502/503/504, and `cms preview` serves the site's
  own pages with the right status instead of the dev server's bare error
  page.

- **The admin ships the theme's behaviors** (ADR-0020): AdminLTE's own
  scripts, the Bootstrap bundle and OverlayScrollbars are vendored and
  served same-origin — working sidebar toggle (mobile included), user
  dropdown menu, automatic light/dark mode. CSP allows exactly
  `script-src 'self'`: no inline scripts, no CDN. The ugly no-JS static
  sidebar fallback is gone.

- **Admin design is now genuinely AdminLTE**: the panel renders exactly as
  the AdminLTE 4 reference pages do — Source Sans 3 (the font the theme
  itself asks for; OFL, local files) instead of the previous brand fonts,
  vendored Bootstrap Icons (MIT) across the sidebar, navbar and stat
  boxes, content headers with breadcrumbs, the canonical footer, and
  small-boxes with icons and footer links. `admin.css` no longer restyles
  the theme; it only adds the font-face, accessibility fixes and the
  no-JavaScript fallbacks.

- **Validation report** across the panel and CLI: `Report` now carries one
  `RuleResult` per rule that ran (passing rules included, each with a
  human description). The admin dashboard and publishing pages share a
  full report — gate callout with the validated scope, a per-rule outcome
  table, and issues linked to their edit screens; `cms validate` prints
  the per-rule outcomes too.
- The seeded example keeps one article in review with a missing DE
  translation, so fresh projects and the demo show the publish gate
  holding a real warning.
- Package `__version__` attributes now derive from the installed
  distribution metadata (they were stuck at `0.1.0`); a test keeps all six
  pyproject versions in lockstep.

## 0.1.1 — 2026-07-19

Documentation release: every package ships a proper PyPI description —
what it does, how to install it (including the database extras), and links
to the live demo, repository and documentation. No code changes.

## 0.1.0 — 2026-07-19

The first release: a multilingual, static-first CMS framework.

- **Content core** (`sardine-cms-core`): articles, pages with ordered typed
  sections, media with mandatory translatable alt text; translation states
  (`missing / outdated / complete`) derived from content checksums; the
  `draft → review → published → archived` workflow; storage contract with
  SQLite, PostgreSQL, MySQL/MariaDB and SQL Server backends behind
  `create_storage(url)`, shared versioned migrations, admin accounts (argon2id) that are never exported.
- **Validation** (`sardine-cms-validation`): composable rule engine —
  required translations, unique slugs per language, media references,
  alt-text coverage, known categories. Errors block publishing.
- **Builder** (`sardine-cms-build`): deterministic static builds (same input,
  byte-identical output), full multilingual SEO (canonical, hreflang, Open
  Graph, JSON-LD, sitemap, RSS), localized UI labels, theme discovery via
  entry points (`sardine.themes`), deployment targets (generic, Azure Static
  Web Apps, nginx), safe CommonMark rendering with raw HTML disabled.
- **CLI** (`sardine-cms-cli`): `cms init | seed | validate | build | export |
  preview | admin create-user` over a `sardine.toml` project file.
- **Admin** (`sardine-cms-admin`): the full editorial cycle in the browser —
  side-by-side translation editors, media library with sniffed-bytes upload
  validation, role-gated workflow with a publish gate, panel builds/exports
  with a served preview; server-rendered, zero JavaScript, CSP with no
  script source, WCAG 2.2 AA gated in CI; styled natively with the ph7x
  design system.
- **Reference theme** (`sardine-cms-theme-ph7x-reference`): the ph7x
  editorial dark design as a standalone theme package with local fonts and
  CSS-only motion.
