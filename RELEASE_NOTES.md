# Release Notes

Narrative release history: delivered features with their pull
requests, breaking changes and storage migrations. Terse per-version
changes live in [CHANGELOG.md](CHANGELOG.md); the product map in
[docs/ROADMAP.md](docs/ROADMAP.md); decision evolution in
[docs/PRODUCT_HISTORY.md](docs/PRODUCT_HISTORY.md).

## 0.6.0 — 2026-07-23

The migration release: migrate a blog into Sardine from the browser,
with nothing silently dropped. No breaking changes and no storage
migrations; internal dependency ranges move to `>=0.6.0,<0.7`.

- **The Migration screen** (#219): the whole WXR flow from the panel —
  upload an export and see the inspection report before anything is
  written (fidelity percentage, author/category/tag inventories, one
  line per left-behind item with its reason), type renames one per
  line, then run with optional source-wins updates and media download.
  Runs are idempotent, audited, bounded by the panel's upload limit,
  and the screen speaks all six panel languages. The panel and the CLI
  call the same shared pipeline — behavior parity is structural, not
  aspirational.

- **Media comes along** (#217): `--fetch-media` (and the screen's
  checkbox) downloads the images imported posts reference into the
  media library and rewrites bodies to `/media/…` paths. Explicit
  opt-in, public hosts only, size and time caps with three attempts,
  duplicate bytes reuse the existing asset, and every URL is reported
  as fetched, reused or failed with its reason.

- **Old URLs keep working** (#218): each imported post's original
  permalink path is recorded in the project's `[redirects]` table when
  it differs from the new address — deterministic, collision-free,
  idempotent across re-runs, and flattened (never chained) when an
  upstream rename lands with `--update`.

- **The panel speaks Bahasa Indonesia** (#216, contributed by
  @MasRama): the seventh bundled language, with a full admin catalog
  under the anti-drift conformance guard and the correct single-form
  plural rule.

### Contributors

Thanks to @MasRama for contributing the complete Indonesian language
pack and admin translation in #216.

## 0.5.0 — 2026-07-22

The first release with external contributions. No breaking changes and
no storage migrations; internal dependency ranges move to
`>=0.5.0,<0.6`.

- **Migration inspects before it writes** (#210, #212): `cms import
  --format wxr --dry-run` reports what an export contains before
  anything is written — importable posts, author/category/tag
  inventories, referenced media, comments, one note per left-behind
  item with its reason, and an explicit fidelity percentage; the dry
  run needs no project. Imports are idempotent by source id: a re-run
  with a newer export never duplicates a post, even after an upstream
  slug rename; matched posts stay untouched unless `--update`
  overwrites them keeping the entity id. Authors and taxonomies map at
  import (`--map-author`, `--map-category`, `--map-tag`; empty target
  drops, unmatched sources warn, `--dry-run` previews the result).
  Media fetch, redirects for changed URLs and the admin migration flow
  remain pending in #140.

- **The panel speaks Italian** (#203, #211, contributed by @MasRama):
  Italian joins the bundled language packs — site labels, month names,
  date pattern, and the full admin catalog wired through the language
  pack contract, proving packs carry a complete panel language. The
  catalog joined the anti-drift conformance test, which now keeps every
  bundled catalog complete.

- **Docker quickstart** (#206, contributed by @MasRama): `docker
  compose up` brings up the admin panel with a seeded example site and
  no Python environment. A random admin password is generated on first
  run and printed once in the container log; content and database
  persist in named volumes. Local evaluation only, as the README
  states.

- **Contributing is a documented path** (#205, #209): the guide covers
  the first-PR essentials — repository language, changelog placement
  under Unreleased, the first-contribution CI approval wait, why
  basing a branch on another open PR backfires — and changelog entries
  credit external contributors.

- **CI hardening** (#204, #208): fork pull requests run the full
  backend conformance job (the MSSQL service starts with a fallback
  throwaway password when repository secrets are absent), and a
  required Commit hygiene check rejects attribution trailers in branch
  commits.

## 0.4.0 — 2026-07-22

- **From nothing to a browsable site in one command** (#190): `cms demo`
  scaffolds a demo project, seeds the fictional five-language content,
  builds and serves it, then prints what to try next. The directory
  stays afterwards so exploring can continue.

- **The quickstart is one sequence you can run** (#199, #200): the
  README's first command was `cms demo`, which no published release
  contained, so a clean `pip install` failed on the opening instruction.
  It also told the reader to install the reference theme and then never
  used it: `cms init` hardcoded `theme = "default"`, so following the
  README produced an unstyled page. `cms init` now takes `--theme`
  (defaulting to `default`, so nothing changes for existing projects),
  and the quickstart is six lines in order with nothing to edit between
  them. Two tests keep it honest: every `cms` command inside a fenced
  README block must exist, and the documented flow must select a theme.

- **The documented restore restores** (#201): `ADMIN_GUIDE` showed
  `cms import portable -p .`, which fails whenever the target project
  already holds content, which is the normal case for a restore. The
  command now carries `--replace`.

## 0.3.0 — 2026-07-22

- **Send a preview link** (#139): editorial approval no longer needs
  an account. Each article and page editor carries an External preview
  links card — create with a chosen lifetime (up to 30 days), copy,
  revoke, active links listed. The link is HMAC-signed over the entry,
  the link id and the expiry with a per-instance key stored in the
  database, so a tampered expiry breaks the signature; revocation is
  stored and immediate; verification injects the clock and is tested
  clock-independently. The viewer sees exactly one entry through the
  real theme under a draft banner in their language (translations
  fall back to the source), publication state never changes, and
  creation/revocation land in the audit trail with the link id, never
  the token. The leak surface is documented in the security policy.

- **Links survive renames, and hints stay hints** (#138, final part):
  renaming a published entry's slug records a redirect from every old
  address automatically — per language, flattened to a single hop
  (A→B then B→C becomes A→C and B→C), never looping, and dropped the
  moment an address becomes live content again. The redirect map stays
  the same `[redirects]` table operators already edit by hand; the
  builder keeps emitting fallback pages and target rules from it, and
  each recorded redirect lands in the Activity trail. The validation
  report gains advisory search-snippet hints (title over 60
  characters, description missing or outside 50–160) — warnings only,
  never a gate, and `[validation] disabled = ["seo-hints"]` switches
  them off per project through the new rule-disabling configuration.

- **The SEO card in the editors** (#138, second part): a collapsed
  Search-and-social card on every article and page editor — SEO title
  and description with a static preview of how the result will read,
  the noindex request, the canonical URL and the social image picked
  from the media library. Ten new panel strings in the four catalogs;
  the card opens itself whenever any override is set.

- **SEO the editor controls** (#138, first part): articles and pages
  take per-language SEO overrides — title, description, `noindex`
  (emitted as `noindex, follow`), a canonical override and a
  social-card image straight from the media library, served as its
  published rendition. Everything flows through the one head
  derivation, so each tag appears exactly once and empty overrides
  keep today's output byte for byte; existing translations never flip
  to outdated just because the field arrived. The portable format and
  the Content API carry the payload additively; storage migration 25
  lands on all four engines. The editor surface, advisory length
  hints and automatic redirects on slug changes are the next part.

- **Any destination for a submission** (#137, final part): the
  provider contract, frozen only after the reference implementation
  proved the shape in production. The endpoint owns everything before
  acceptance (protocol, spam layers, validation, the visitor's
  answer); a provider owns everything after it. Extensions register
  destinations (webhooks, queues, CRMs) by name; the contract version
  is validated at selection; a provider failure is contained and
  audited, never visitor-facing. A conformance suite runs the rules
  against any provider, and the developer guide documents the
  authoring path.

- **Submissions can stay** (#137, third part): `[forms] store = true`
  persists accepted submissions — storage is a consumer of the
  accepted submission, never part of the HTTP decision, and fully
  decoupled from the notification mail: either leg failing is audited
  on its own record and never reaches the visitor. The admin-only
  Submissions screen lists them newest first with operational filters
  (which form, date window), shows the visitor's values as an opaque
  payload, and deletes definitively; `retention_days` prunes at panel
  startup. Storage migration 24 on all four engines; the endpoint
  works identically with storage off.

- **Forms submit somewhere real** (#137, second part): the official
  reference endpoint. Published forms POST to the panel's
  `/forms/submit`, which validates server-side against the form's
  declared inputs, applies layered spam protection — honeypot,
  elapsed-time check when present, per-address rate limiting, origin
  allowlist — and answers deterministically (200/422/403/429/404) with
  a localized, accessible page; success speaks the section's own
  success texts. With `[forms] notify` set, submissions arrive as
  plain-text mail through the existing transports; a delivery failure
  is audited, never shown to the visitor. The example site's About
  page now carries a five-language contact form.

- **Sites can ask something back** (#137, first part): the `form`
  section kind. Editors declare a form's inputs as section items —
  key, type (text, email, textarea, checkbox), label, required — with
  every visitor-facing word being editorial content, translated like
  any other section. Both bundled themes render it accessibly (labels,
  `aria-required`, keyboard-only, no JavaScript) with a honeypot and
  an enhancement-filled elapsed-time field; a non-empty consent label
  adds a required consent checkbox. The `<form>` appears only when the
  project configures `[forms] endpoint` — the official reference
  endpoint is the next part of this work.

- **Editors pick images, they don't type IDs** (#136): the article
  metadata card and the section editor gain a library picker —
  thumbnail tiles with each image's dimensions, radio choice for the
  cover (pick, keep current, or none) and checkboxes that append to a
  section's ordered media list. Plain HTML, no script required; the ID
  inputs remain the precise path. Images narrower than the widest
  configured responsive width carry a flag, so an editor sees at
  selection time that a source is too small for the site's layouts.

- **Swap the file, keep the asset** (#136): the asset page gains a
  replace flow. The uploaded bytes change; the ID does not — so every
  cover and section reference keeps working without re-linking. Alt
  texts, collection and focal point carry over, a crop that no longer
  fits the new image is cleared rather than shipping a broken window,
  the old file leaves the disk when the format changes, and bytes
  identical to another asset are refused with that asset's name.

- **Modern image formats without asking** (#136): builds now emit
  WebP and AVIF variants of every raster image — the base rendition
  and each configured responsive width — whenever the build
  environment can encode them, with fixed encoder parameters so the
  output stays reproducible. Both bundled themes serve them through
  `<picture>` sources (browsers pick the best format they support;
  the plain `img` remains the fallback), and the Content API carries
  the same alternatives in an additive `sources` field. One switch
  (`[build] modern_image_formats = false`) restores the previous
  behaviour; environments without the encoders simply skip the
  variants — never an error.

- **Images crop where the editor says, not where the file ends**
  (#136): an image's asset page takes an optional crop (pixels of the
  original) and focal point (fractions). The crop is data — applied
  deterministically at build, so the published rendition, its declared
  dimensions, the `srcset` chain and the Content API all speak the
  cropped size while the uploaded original stays untouched; clearing
  it restores the full image on the next publish. The focal point
  rides the image metadata into themes and the API (additive within
  `v1`). Storage migration 23 on all four engines; portable format
  round-trips both; five new panel strings in the four catalogs.

- **The media library gets folders, honesty and a memory** (#136):
  assets take an optional collection — set at upload, editable later,
  filterable in the library — and the list says how many entries use
  each asset, with the full reference list on the asset page. Every
  upload records the file's SHA-256; bytes identical to an existing
  asset are refused with the existing asset's name. Storage migration
  22 (additive) on all four engines; the portable format round-trips
  both fields; five new panel strings in the four bundled catalogs.

- **Any destination, one contract** (#156): the deployment
  provider framework. Providers register by name
  (`register_deploy_provider`), read their own keys from the raw
  `[deploy]` table, declare a contract version (validated at selection,
  never at deploy time) and a capability set the panel adapts to —
  rollback controls appear only when the provider declares them.
  Extensions ship destinations via `Extension.deploy_providers`; a
  reusable conformance suite runs the contract's rules against every
  provider, bundled or third-party — including an admin E2E that
  publishes through a fictional extension-shipped provider with zero
  core changes.

Pull requests in this cycle: source language #118 · logical CSS/RTL
#119 · panel catalogs from packs #120 · pack ecosystem #121 · ADR-0037
#122 · items model #123 (migration 18) · items rendering #124 · items
editors #125 · roadmap-as-product #142 · ADR-0037 vertical close #143
· page editor UX #144 (migration 19) · editorial-flow check #145 ·
setup wizard #146 · deployment wizard #147 · global search #148 ·
bulk actions #149 · translation queue #150 · editorial calendar #151 ·
operational-model docs #153 · scheduled unpublish #154 (migration 20) · audit trail #159 (migration 21).
Storage migrations this cycle: 18 (section items + page body), 19
(section visibility), 20 (unpublish windows) — all additive, no
breaking changes; old portable exports import unchanged.

- **Publication windows close by themselves** (#133): articles and
  pages gain `unpublish_at` — after it passes, the next build drops
  the entry, deterministically, from the same clock as `publish_at`
  (ADR-0024's symmetric end). A window that ends before it starts is
  refused at the model. The editors carry the field beside the publish
  moment; storage migration 20 lands on all four engines; the portable
  format round-trips it. Two new panel strings in the four bundled
  catalogs.

- **The operational model is written down** (#152, docs-only): Sardine
  manages the site; external infrastructure serves it — and
  publication is a repeatable cycle, never a one-off export. The new
  DEPLOYMENT.md documents every supported model (Nginx-served local
  directory with the symlink pattern, sync to static hosting, panel
  build, the demo's own privilege-separated CI/CD pipeline), Azure
  Static Web Apps and Nginx examples, rollback/credentials/partial-
  failure guidance, and the five-phase provider contract with honest
  status (generation ✅, transport/activation/health/rollback → #152).
  README separates managing from serving; ADMIN_GUIDE explains what
  "publish" means and where its state lives; the wiki gains an
  Operational Architecture page with the flow diagram. The README's
  stale "EN as source" line caught up with ADR-0034 on the way.

- **The month has a face** (#132): the Calendar screen shows published
  entries on their publication day and scheduled entries on the day
  their `publish_at` will fire — in UTC, exactly as the panel
  schedules, and the screen says so. Scheduled chips drag to another
  day (a progressive enhancement posting a server-validated move that
  keeps the time of day; published history refuses to move), and every
  chip links to its editor, where the date field stays the precise
  no-JS path. Eleven new panel strings in the four bundled catalogs.

- **The translator gets a worklist** (#131): the new Translations
  screen lists every entry-language pair that is missing or outdated —
  for the project's configured language set, pack tags included —
  filterable by language, state and content type, each row linking
  straight to the side-by-side editor; zero rows is a real
  "all caught up". The content lists gain the same power as a filter:
  "missing «tag»" keeps only entries incomplete in that language.
  States come from the model's checksums, so the queue can never
  disagree with the editors. Twelve new panel strings in the four
  bundled catalogs.

- **Bulk actions with per-entry honesty** (#130): the content lists
  select with checkboxes (plain forms, no JavaScript — the checkboxes
  attach to an external form so row actions stay valid HTML) and apply
  one action to everything selected: workflow transitions, trash,
  category assignment for articles, unreferenced-media deletion.
  Nothing is looser in bulk — every entry passes the exact
  single-action checks (its own transition validity, the actor's role,
  the publish gate with the project's language set, media reference
  protection) and the result page reports every outcome, refusals with
  their reason; one failure never aborts the rest. Twenty new panel
  strings in the four bundled catalogs.

- **One search box finds everything** (#129, ADR-0038): the navbar
  carries a search on every admin screen; results come grouped —
  articles, pages, sections and media — matched by title, text, slug,
  section fields (items included) and media alt text in every
  language, each hit linking straight to its editor; the trash never
  matches. The query is a storage-contract method with a portable
  default (third-party backends inherit correctness) and LIKE
  overrides on all four bundled engines; the 300 ms budget at 10 000
  entries is met with an order of magnitude to spare (13.6 ms SQLite,
  34.5 ms PostgreSQL, worst of five runs — `scripts/search_bench.py`
  is the reproducible method).

- **Publishing answers "where will the site live?"** (#128, second
  slice): the build form becomes a guided choice — a card per
  deployment target explaining in plain words what the build includes
  and what to do with it; the choice is remembered in `sardine.toml`
  (`[build] target`, shared with `cms export`, which now defaults to
  it), and a successful build ends with where the files are and the
  one action that puts them live. Thirteen new panel strings in all
  four bundled catalogs; end-to-end tested from the wizard through a
  real build to the persisted target and the target's extra files.

- **The browser sets up the site** (#128, first slice): an instance
  with zero accounts lands every visitor on `/setup` — first admin
  account (always `admin`; an instance can never be left without one),
  site identity (name, address, main language and targets from the
  registered packs, theme — written to `sardine.toml` only when the
  project has none; an existing file is never touched) and optional
  example content — then signs the new admin in and opens the
  dashboard's first-steps checklist. The wizard disappears permanently
  once any account exists. This answers the strongest friction class
  recorded on #127: starting, understanding and completing the first
  site. The deployment wizard is the issue's next slice.

- **The editorial-flow check joins the repository and CI** (#127):
  `scripts/editor_flow_check.py` is self-contained and reproducible by
  anyone — it creates a fresh monolingual project and admin account in
  a temporary directory, serves the real admin, drives the complete
  landing-page scenario through the real UI with headless Chromium
  (block gallery, fields, the Markdown widget's editing surface, three
  FAQ items, workflow to published) and asserts every block — Markdown
  rendered — in the final built HTML. CI runs it on every push.
  Evidence lives in the repository, never in session state; the script
  is the mechanical proof that no step blocks — the 15-minute
  usability metric still requires a real non-technical tester.

- **The page editor speaks editor, not framework** (#127): sections
  add from a visual block gallery (a card per kind with a plain-words
  description; extension kinds included), keys derive from the kind —
  editors never invent slugs — and rows duplicate, hide/show, delete
  **with undo** and reorder by drag-and-drop (progressive: the up/down
  buttons remain the keyboard and no-JS path). Hidden sections keep
  their content and translations but leave every build and never block
  parity (model + migration 19 on all four engines + portable format).
  The per-section language columns became the constant-width coverage
  cell — the last admin table that grew with the language count. All
  new panel strings ship in the four bundled catalogs.

- **ADR-0037 closes vertically** (#126): the seed and public demo now
  exercise `items` (FAQ, expertise and story stat pairs — zero numbered
  fields left in seed data, and the story kind's stat pairs joined the
  items contract), THEME_GUIDE documents gallery v2 as the authoring
  contract, ADMIN_GUIDE describes the three-part section editor, and a
  behavioral end-to-end test drives the whole editorial flow over the
  admin's real HTTP surface: open the page, edit items past the retired
  cap, save, translate the second language side by side, publish
  through the gate, and read the **eighth FAQ item** in the final built
  HTML of both bundled themes. Only with all of that true do the
  roadmap rows flip to ✅ — the first feature shipped under the
  product-review definition of done.

- **The roadmap became a product plan** (2026-07-21 product review):
  the stale execution queue is gone — the queue now lives in the issue
  tracker (#126–#141), one issue per capability with user problem,
  scope and acceptance criteria, prioritized P0 (non-technical editor
  usability) → P3 (scale). The definition of done is explicit — admin
  flow, E2E, both themes, two languages, empty/error states, docs,
  public demo — and "contract shipped" without a usable bundled
  implementation is now marked 🟡, never ✅ (comments included).
  Product metrics (first site < 10 minutes, landing page < 15 minutes,
  search < 300 ms on 10k entries) are recorded as pre-1.0 targets.

- **The editors caught up with the model** (M8, ADR-0037 phase 3): the
  section editor grows a per-column items table (blank rows add, a
  cleared row removes — the same server-rendered pattern the fields
  table uses, no new JavaScript), a kind's declared Markdown fields
  get the same editor widget as article bodies, pages and their
  translations gain the long-form body field, and the side-by-side
  translation editors mirror items row-aligned beside the source. The
  editors' hardcoded "(EN)" labels became source-neutral — the panel
  stopped assuming the source language it no longer fixes. Panel
  strings ship in all four bundled catalogs.

- **Sections render without caps, fields speak Markdown, pages render
  as documents** (M8, ADR-0037 phase 2): the section-kind gallery
  becomes spec-based (`SectionKindSpec`: fields, Markdown-capable
  fields, item columns — extension kinds keep working as bare tuples),
  both bundled themes render the unbounded `items` group (`q6`/`row8`
  template caps are gone; legacy numbered fields map into items at
  render time so nothing existing breaks), declared Markdown fields
  and the page body render through the same safe renderer as article
  bodies (raw HTML off), and the theme conformance suite pins all of
  it — a 10-item FAQ, seven-question legacy content, script stripping
  and page prose must render in every theme, third-party ones
  included.

- **Sections can repeat and pages can be documents** (M8, ADR-0037
  phase 1): `SectionContent.items` — an ordered, unbounded repeating
  group — and `PageContent.body_markdown` join the model, the
  checksums (edits flip translations to outdated exactly like any
  content change; empty values keep the legacy checksum so nothing
  existing flips), storage migration 18 on all four engines, and the
  portable export/import format. Rendering and editing arrive with the
  ADR's next phases; existing content changes by nothing.

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
