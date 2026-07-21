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
| Articles + pages with typed sections | ✅ | — |
| Categories, tags, listing pages | ✅ incl. validation rule | — |
| Custom content types | ❌ deliberate: pages-with-sections + article custom fields cover known cases | 🧭 own ADR when a real case appears (ADR-0028) |
| Custom fields | ✅ free-form fields on articles (editable, exported, themed) and sections | — |
| Navigation menus | ✅ explicit menu manager (per-language labels, ordering, external links) with automatic-menu fallback | — |
| Reusable blocks | ✅ the section-kind gallery is a tested contract: nine bundled kinds (incl. quote, FAQ, CTA, image gallery), both themes, admin field suggestions, extension-added kinds, THEME_GUIDE authoring table | — |
| Design-aware editing | ✅ themed side-preview plus debounced live refresh through the scoped real builder (ADR-0027) | — |
| Multilingual | ✅ **core strength**: EN source + per-language states, parity gates | — |
| Authors / bylines | ✅ editorial byline on articles, rendered by the themes | — |
| Custom taxonomies | ❌ category + tags | 🧭 arbitrary taxonomy definitions need an ADR (M8) |
| Content relations | ❌ | 🧭 typed entry-to-entry links (related articles) need an ADR (M8) |
| Arbitrary locale sets + language packs | ❌ the five supported languages are fixed | 🧭 **top of M8**: one ADR for configurable locales, contributable language packs (site labels + admin catalogs) and RTL/LTR text direction |

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
| Comments | ✅ contract shipped ([ADR-0031](adr/0031-comments-integration.md)): `[comments]` + extension-registered providers, consent-first island, no-JS link, byte-identical builds without it | Real provider packages live outside the core |
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
| Two-factor authentication | ❌ | 🔜 TOTP (M7) |
| Notifications (review requested…) | ❌ | 🔜 ADR-0032 phase 2: review-requested + published, fire-and-forget (M7, next) |

### Platform and operations

| Capability | Today | Gap → where |
| --- | --- | --- |
| Plugin system | ✅ ADR-0028: `sardine.extensions` contract — rules, build steps, targets, backends, themes, `cms x` CLI, section-kind hints; explicit activation in `sardine.toml` | — |
| Themes + per-project overrides | ✅ entry-point discovery | — |
| Import / restore | ✅ portable JSON/Markdown round-trip plus an offline WXR 1.2 blog adapter ([ADR-0030](adr/0030-foreign-blog-import.md)) | More foreign formats only when a concrete migration requires one |
| Export / portability | ✅ JSON/Markdown is the source of truth | — |
| Content API | ✅ opt-in `api/v1/` JSON in every build ([CONTENT_API.md](CONTENT_API.md)): versioned, deterministic, same publication/language gates as the HTML | — |
| Webhooks (publish → host build) | ❌ | 🔜 on-publish webhook (M7) |
| Health check | 🟡 `cms validate` covers content | 🔜 `cms doctor` (storage, media, config) (M7) |
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

Current queue:

1. **M7 operations** — implement ADR-0032 (email + notifications) →
   TOTP 2FA → on-publish webhooks → `cms doctor`.

## Definition of done for the current queue

| Item | Done means |
| --- | --- |
| M7 operations | Recovery and notifications have an explicit delivery contract; 2FA is role-safe; webhooks are signed/retryable; `cms doctor` reports storage, media, configuration and environment health. |

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
- **M7 — Operations** (current): email/notification subsystem per
  ADR-0032 (password reset, review notifications), TOTP 2FA, on-publish
  webhooks and `cms doctor`.
- **M8 — Editorial power and content depth**: bulk actions, admin-wide
  search, scheduled unpublish, editorial calendar, audit log, custom
  taxonomies (ADR), content relations (ADR), crop/focal point (ADR),
  WebP/AVIF derivatives, media organization, embeds contract (ADR),
  forms contract (ADR), per-entry SEO controls.
- **M9 — Platform, measurement and ecosystem**: privacy-first analytics
  contract (ADR), external review links (ADR), incremental builds,
  ecosystem catalog.
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
