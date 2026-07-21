# Roadmap

The outward view: where Sardine CMS is, what ships next, and what "done"
means at each horizon. Execution detail lives in [PLAN.md](PLAN.md)
(milestones, checkboxes) — this page points at it. Live demo:
<https://sardine.ph7x.com>.

Sardine CMS is a **CMS**: the bar for "complete" is the capability set
editors expect from a mature publishing system. This is a benchmark, not a
clone target. The inventory below states what works now, what remains and
which milestone owns each gap. Static-first changes *how* a capability works
(comments, search and scheduling need no server at request time), never
whether editors get the capability.

Product direction has three pillars:

1. **Editorial confidence** — preview, workflow, revisions, scheduling,
   accessibility and multilingual parity are visible and enforceable.
2. **Adoption without lock-in** — themes, extensions, portable content and
   controlled import paths let a site enter, evolve and leave cleanly.
3. **Operational completeness** — authentication recovery, notifications,
   webhooks and diagnostics make the system dependable beyond development.

## Where the project stands

- **Milestones 0–3 shipped**: content core (translation states from
  checksums, four storage engines behind one factory, conformance-tested),
  validation engine with per-rule reporting, deterministic builder (SEO
  head contract, feeds, search indexes, categories/tags/pagination, media
  pipeline), theme system with overrides, deployment adapters
  (SWA/nginx/generic), the `cms` CLI, and the **full browser admin** —
  accounts/roles, dashboard, side-by-side translation editors, media
  library, editorial workflow, publishing panel, hardening (WCAG 2.2 AA
  gated in CI). UI is AdminLTE 4, vendored, implemented faithfully
  (ADR-0017).
- **v0.1.x on PyPI** — six `sardine-cms-*` packages, lockstep versions,
  trusted publishing, per-package environments.
- **Public demo live** at <https://sardine.ph7x.com> (site + read-only
  admin), auto-deployed from `main`.
- **Guardrails**: 10 CI checks (including accessibility, markup, dependency
  audit and static security analysis), docs anti-drift suite, secret
  scanning, CodeQL, PR-only workflow and mypy strict. All ten contexts are
  required by branch protection.

## Capability inventory

Legend: ✅ shipped · 🟡 partial · 🔜 scheduled (milestone in brackets) ·
🧭 needs an ADR first.

### Editorial workflow

| Capability | Today | Gap → where |
| --- | --- | --- |
| Draft / review / publish / archive, role-gated | ✅ | — |
| Markdown editor with toolbar | ✅ EasyMDE vendored, localized toolbar (ADR-0023); builder preview stays the truth | — |
| **Unpublish** (published straight back to draft) | ✅ one click, publisher role; the next build drops the entry | — |
| Scheduled publishing | ✅ `publish_at` on articles/pages (ADR-0024): the build is the clock; documented CI-cron recipe | — |
| Revisions + restore | ✅ bounded history on every save (ADR-0025), diff view, undoable restore | — |
| Trash / restore | ✅ reversible deletion (ADR-0026): trash view, exact restore, admin-only purge | — |
| Duplicate content | ✅ Duplicate as draft on articles and pages, collision-safe ids | — |
| Per-entry preview | ✅ editors link straight to the entry's URL inside `/preview/` | — |
| Quick actions from the list | ✅ per-row dropdown: workflow transitions + trash | — |
| Featured / pinned content | ✅ featured flag: leads the home highlight; listings stay recency | — |
| Editorial notes on entries | ✅ note trail per article/page (author-or-admin removal); never published | — |
| Bulk actions on content lists | ❌ one entry at a time | 🔜 multi-select workflow/trash operations (M8) |
| Admin-wide search | ❌ per-list filters only | 🔜 one search box over articles, pages, media (M8) |
| Scheduled unpublish | ❌ `publish_at` only | 🔜 `unpublish_at` mirror of the scheduling contract (M8) |
| Editorial calendar | ❌ | 🔜 month view of scheduled/published entries (M8) |
| Audit log | ❌ revisions cover content only | 🔜 who-did-what trail for accounts and workflow (M8) |
| Autosave while editing | ✅ valid article/page source edits persist on a debounce without flooding revisions | — |

### Content model

| Capability | Today | Gap → where |
| --- | --- | --- |
| Articles + pages with typed sections | ✅ open kinds, unlimited reorderable sections; unknown kinds render generically | — |
| Repeating groups in sections | ❌ repetition is numbered fields (`q1…q6`, `row1…row8`) with caps hidden in theme templates | 🔜 unbounded `items` per section, translatable and validated ([ADR-0037](adr/0037-sections-grow-up.md) phase 1–2) |
| Rich text inside sections | ❌ section fields are plain strings | 🔜 kinds declare Markdown fields; same safe renderer as article bodies (ADR-0037 phase 2) |
| Long-form pages | ❌ pages hold no body — all content must fit section kinds | 🔜 `PageContent.body_markdown` rendered as prose (ADR-0037 phase 1–2) |
| In-editor visual page building | ❌ form-based section editor (server-rendered) | 🧭 deferred by ADR-0037: needs a client-side island beyond ADR-0010's budget — its own ADR if forms measurably fail editors |
| Categories, tags, listing pages | ✅ incl. validation rule | — |
| Custom content types | ❌ deliberate: pages-with-sections + article custom fields cover known cases | 🧭 own ADR when a real case appears (ADR-0028) |
| Custom fields | ✅ free-form fields on articles (editable, exported, themed) and sections | — |
| Navigation menus | ✅ explicit menu manager (per-language labels, ordering, external links) with automatic-menu fallback | — |
| Reusable blocks | ✅ the section-kind gallery is a tested contract: nine bundled kinds (incl. quote, FAQ, CTA, image gallery), both themes, admin field suggestions, extension-added kinds, THEME_GUIDE authoring table | 🔜 gallery v2 adds field specs (Markdown-capable fields) — ADR-0037 phase 2 |
| Design-aware editing | ✅ themed side-preview plus debounced live refresh through the scoped real builder (ADR-0027) | — |
| Multilingual | ✅ **core strength** — the dedicated map below tells the whole story | — |
| Authors / bylines | ✅ editorial byline on articles, rendered by the themes | — |
| Custom taxonomies | ❌ category + tags | 🧭 arbitrary taxonomy definitions need an ADR (M8) |
| Content relations | ❌ | 🧭 typed entry-to-entry links (related articles) need an ADR (M8) |
| Arbitrary locale sets + language packs | ✅ [ADR-0034](adr/0034-language-packs.md) fully executed: tag-based locales, packs carrying everything (site labels, dates, admin catalogs), configurable source, RTL end to end, ecosystem guide + `sardine-lang-<tag>` naming | — |

### Multilingual — the full map

The founding principle (owner directive): **every language is a pack —
the bundled five included**. Nothing about a locale lives outside its
pack once the migration completes; "EN is the source" is a factory
default, never a law. Where the mature systems leave multilingualism to
paid add-ons, it is this product's core — the bar is to stay ahead.

| Capability | Today | Gap → where |
| --- | --- | --- |
| Translation states from checksums (missing/outdated/complete) | ✅ automatic, per language — no manual "needs update" flags, ever | — |
| Parity gates (missing translation blocks publish) | ✅ configurable rules | — |
| Per-language slugs, hreflang cluster, localized feeds + search indexes | ✅ in every build | — |
| Language packs end to end | ✅ ADR-0034: an extension pack's tag is a full content language (config, build, labels, dates, RTL `dir`) | — |
| Side-by-side translation editing | ✅ EN source next to each translation, per field | — |
| Language switcher stays on page | ✅ falls back to that language's home | — |
| Scalable coverage in lists | ✅ constant-width summary (`3/4 · 1 missing`) — lists never grow horizontally per language | — |
| Bundled five as full packs | ✅ labels, months and date patterns live in each pack; the `cms_build.ui` tables are gone — no language data outside packs (admin catalogs join in the admin phase) | — |
| Configurable source language | ✅ `[site] source_language` (default `en`): any pack tag can be the source — URL root, hreflang x-default, validation parity and label fallbacks all follow it; the source never doubles as a target | — |
| Admin panel languages from packs | ✅ catalogs live in `LanguagePack.admin_catalog` (bundled four included); the panel offers every registered pack with a catalog by its native name, mirrors RTL packs, and the editors' source/target sets come from the project | — |
| RTL end to end | ✅ `dir="rtl"` on the markup and flow-relative CSS throughout both themes and the panel chrome — conformance-tested (no physical property can return) | — |
| Translation queue | ❌ | 🔜 one screen of every entry×language pair missing or outdated — the translator's worklist (M8) |
| List filters by translation state | ❌ | 🔜 "entries missing «tag»" filters on the content lists (M8) |
| Fallback policy per language (publish partial vs block) | ❌ parity blocks today | 🧭 needs an ADR — per-language policy, never silent |
| Machine-translation assist | ❌ | 🧭 provider-neutral contract (ADR-0028 pattern), post-M8 |
| Data-only language packs | ❌ packs are Python objects today | 🔜 authorable as a pure data bundle (labels + months + `.po` + direction) — contributing a language must need zero code (ADR-0034 ecosystem phase) |

### Media

| Capability | Today | Gap → where |
| --- | --- | --- |
| Library: validated uploads, translatable alt, safe delete | ✅ MIME-sniffed, dimensions parsed | — |
| Image derivatives / responsive sizes | ✅ opt-in build-time derivatives (ADR-0029): `[build] image_widths`, deterministic, `srcset` in both themes | — |
| Crop / focal point | ❌ | 🧭 ADR scheduled with the M8 media work |
| Modern format derivatives (WebP/AVIF) | ❌ derivatives keep the source format | 🔜 opt-in format conversion beside `image_widths` (M8) |
| Media organization | ❌ flat library with filters | 🔜 folders or collections once libraries grow (M8) |
| Media search / filters | ✅ server-side search (id/path/type/alt) + quick views (images, missing alt) | — |

### Site features (static-first)

| Capability | Today | Gap → where |
| --- | --- | --- |
| SEO: canonical, hreflang, Open Graph, JSON-LD, sitemap, RSS | ✅ in every build | — |
| Search | ✅ client-side index island | — |
| Comments | 🟡 contract + fictional test provider only ([ADR-0031](adr/0031-comments-integration.md)): `[comments]`, consent-first island, no-JS link | An **official usable provider** is the done bar — contract alone is not a feature |
| Redirects | ✅ `[redirects]` map: real 301s on SWA/nginx + meta-refresh fallback pages for any host | — |
| Localized 404 / error pages | ✅ | — |
| Embeds (video, social, maps) | ❌ safe Markdown only | 🧭 static-safe embed contract — consent-first islands like comments (M8) |
| Forms (contact, signup) | ❌ | 🧭 provider contract like ADR-0031's: static page, consent-first submission (M8) |
| Per-entry SEO controls | 🟡 summary drives description | 🔜 per-entry noindex + meta overrides (M8) |
| Analytics | ❌ | 🧭 privacy-first measurement contract, provider-neutral (M9) |
| External review links | ❌ preview requires an account | 🧭 shareable expiring preview links need an ADR (M9) |
| Multiple sites per install | ❌ one project = one site | out of scope before 1.0 |

### Users and access

| Capability | Today | Gap → where |
| --- | --- | --- |
| Role ladder | ✅ editor < reviewer < publisher < admin | — |
| User management UI | ✅ Users screen (admin role): create, role change, delete — self and last-admin safeguards; CLI stays the bootstrap | — |
| Admin panel in the editor's language | ✅ gettext i18n (ADR-0022): PT-PT/ES/FR/DE shipped, per-user preference + browser fallback, completeness enforced by tests | — |
| Password reset | ✅ ADR-0032: enumeration-safe request, hashed single-use 30-min tokens, session revocation; pluggable mail transports (`smtp` baseline, extensions for passwordless APIs) | — |
| Two-factor authentication | ✅ TOTP ([ADR-0035](adr/0035-totp.md)): confirmed enrolment, single-use codes, shared login rate budget, per-role enforcement (`SARDINE_ADMIN_REQUIRE_2FA`, forced enrolment) | — |
| Notifications (review requested…) | ✅ ADR-0032: review-requested (reviewers and above) + published (last editing author), localized, fire-and-forget off the request path | — |

### Platform and operations

| Capability | Today | Gap → where |
| --- | --- | --- |
| Plugin system | ✅ ADR-0028: `sardine.extensions` contract — rules, build steps, targets, backends, themes, `cms x` CLI, section-kind hints; explicit activation in `sardine.toml` | — |
| Themes + per-project overrides | ✅ entry-point discovery | — |
| Import / restore | ✅ portable JSON/Markdown round-trip plus an offline WXR 1.2 blog adapter ([ADR-0030](adr/0030-foreign-blog-import.md)) | More foreign formats only when a concrete migration requires one |
| Export / portability | ✅ JSON/Markdown is the source of truth | — |
| Content API | ✅ opt-in `api/v1/` JSON in every build ([CONTENT_API.md](CONTENT_API.md)): versioned, deterministic, same publication/language gates as the HTML | — |
| Webhooks (publish → host build) | ✅ [ADR-0036](adr/0036-on-publish-webhooks.md): signed doorbell on publish/unpublish, bounded retries, HTTPS-only, optional | — |
| Health check | ✅ `cms doctor`: configuration, theme, extensions, comments, storage schema, media files, environment — read-only, exit 1 on failure; `cms validate` keeps the content side | — |
| Backups | ✅ `cms dump` writes the portable pair, `cms import` restores it — the DB stays disposable | — |
| Scheduled builds | ✅ recipe in ADMIN_GUIDE (CI `schedule:` + `cms export`); `publish_at`-aware by construction | — |
| Incremental builds | ❌ full rebuild every time (fast today) | 🔜 content-hash build cache when site size demands it (M9) |
| Ecosystem catalog | 🟡 ECOSYSTEM.md policy exists | 🔜 published index of themes/extensions once third-party packages exist (M9) |
| SSO / OIDC sign-in | ❌ local accounts only | 🧭 identity-provider ADR (post-1.0) |

## Execution order

Completed M6 foundation:

`extension contract → menu manager → image derivatives → redirects →
portable round-trip → external blog adapter → live refresh + autosave →
reusable-block gallery → comments contract (ADR-0031) → JSON content
target`

The execution queue lives in the
[issue tracker](https://github.com/ph7x-Systems/sardine-cms/issues) now —
one issue per capability, each carrying the user problem, scope,
dependencies and acceptance criteria. **No implementation starts without
its issue.** The 2026-07-21 product review reset the direction: the
engineering base (multilingual core, four storage engines, deterministic
builds, admin, workflows, extensions, operations) outgrew the product
experience, so the queue is now organized by what an *editor* can do,
not by which contract exists.

## Priorities (P0 → P3)

- **P0 — usable by a non-technical editor** (#126–#135): close ADR-0037
  vertically, page-editor UX (block gallery, duplicate, drag reorder,
  hide, delete with undo), browser onboarding wizard, global admin
  search, bulk actions, translation queue + filters, editorial
  calendar, scheduled unpublish, audit log, needs-attention dashboard.
- **P1 — gaps that block real sites** (#136–#139): media maturity
  (collections, crop, focal point, WebP/AVIF, replace, picker), an
  **official forms provider** — a contract alone is not a feature —
  per-entry SEO controls, signed external preview links.
- **P2 — ecosystem experience** (#140–#141): WXR migration as a real
  admin flow, theme/extension install-activate-inspect without editing
  files, three official themes.
- **P3 — scale and platform**: incremental builds, multisite, SSO/OIDC,
  custom taxonomies, content relations, analytics — only when real
  sites surface real problems.

## Definition of done (every feature)

A capability is ✅ only when **all** hold: usable in the admin; E2E
tested; works in both bundled themes; works in at least two languages;
has empty and error states; documented (repo + wiki); demonstrated on
the public demo. "Contract shipped" without a bundled usable
implementation is 🟡, never ✅. ADRs are reserved for decisions that
change public contracts, storage, security or extensibility — UX
details do not need one.

## Product metrics (targets, measured before 1.0)

| Metric | Target |
| --- | --- |
| First site published (seed path, browser) | < 10 minutes |
| First page created | without touching the CLI |
| Landing page built by a non-technical editor | < 15 minutes |
| Preview refresh | < 2 seconds |
| Admin search on 10 000 entries | < 300 ms |
| WXR migration of a reference export | explicit fidelity % reported |

## Milestones ahead

- **M5 — Editorial completeness: CLOSED.** Direct unpublish, scheduling,
  revisions with restore, trash, duplicates, per-entry and design-aware
  preview (ADR-0027), quick actions, featured flag, authorship, media
  filters, users screen, editorial notes — all shipped, all live on the
  demo. Autosave and live themed refresh shipped immediately after closure
  as ADR-0027 phase 2.
- **M6 — Extensibility and adoption: CLOSED.** The extension contract
  executed (ADR-0028), menu manager, image derivatives, redirects,
  portable round-trip and external blog import, live refresh/autosave,
  reusable-block gallery, comments contract (ADR-0031) and the JSON
  content target — all shipped. (Admin localization shipped early —
  ADR-0022.)
- **M7 — Operations: CLOSED.** Pluggable email transports with
  enumeration-safe password reset and editorial notifications
  (ADR-0032), TOTP two-factor with per-role enforcement (ADR-0035),
  signed on-publish webhooks (ADR-0036) and `cms doctor` — all shipped.
- **M8 → reorganized into P0/P1 issues** (#126–#139): editorial
  usability first — see Priorities above. Custom taxonomies and content
  relations moved to P3: they are platform depth, not editor pain.
- **M9 → reorganized into P2/P3**: ecosystem experience (#140–#141),
  then incremental builds, analytics, external review links, catalog.
- **1.0** — criteria: M5–M7 shipped, admin stable, two production
  deployments beyond ph7x.com, deprecation policy on PyPI, all
  conformance suites documented as public contracts. M8/M9 continue
  past 1.0 unless adoption pulls items forward.
- **Post-1.0 architectural horizon**: SSO/OIDC — it changes core
  contracts and waits for its own ADR. (Arbitrary locales moved up: the
  language-pack ADR opens M8.)

The bar stays what it has been since M5: the capability set editors
expect from the mature publishing systems they come from, delivered
static-first — the same benchmark, never a clone.

## Standing invariants (any horizon)

Language sets are data, never structure: anything per-language is
modeled as rows, keys or configuration — never as schema columns, fixed
enumerations in new contracts, or hardcoded strings — so that adding a
language (packs, RTL scripts included) never alters a table or a code
path.

Everything lands through the same gates: English-only repo, PR + green CI,
repository docs and public wiki move with the code (anti-drift enforced for
the repository set), ADRs for decisions, no secrets/personal data,
deterministic builds, WCAG 2.2 AA baseline, and the static-first contract —
the exported site never needs the admin running.
