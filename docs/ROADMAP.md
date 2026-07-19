# Roadmap

The outward view: where Sardine CMS is, what ships next, and what "done"
means at each horizon. Execution detail lives in [PLAN.md](PLAN.md)
(milestones, checkboxes) — this page points at it. Live demo:
<https://sardine.ph7x.com>.

Sardine CMS is a **CMS**: the bar for "complete" is what editors already
expect from the mature CMSs they come from. The parity table below is the
honest inventory — the capability, what Sardine CMS does today, and where
the gap is scheduled. Static-first changes *how* some features work
(comments, search and scheduling need no server at request time), never
whether the editorial capability exists.

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
- **Guardrails**: 9 required CI checks (incl. axe and W3C markup), docs
  anti-drift suite, secret scanning, PR-only workflow, mypy strict.

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
| Autosave while editing | ❌ | 🔜 with the admin's JS layer (M5, after ADR-0020) |

### Content model

| Capability | Today | Gap → where |
| --- | --- | --- |
| Articles + pages with typed sections | ✅ | — |
| Categories, tags, listing pages | ✅ incl. validation rule | — |
| Custom content types | ❌ deliberate: pages-with-sections + article custom fields cover known cases | 🧭 own ADR when a real case appears (ADR-0028) |
| Custom fields | ✅ free-form fields on articles (editable, exported, themed) and sections | — |
| Navigation menus | ✅ explicit menu manager (per-language labels, ordering, external links) with automatic-menu fallback | — |
| Reusable blocks | 🟡 section kinds are the block library | 🔜 grow the kind gallery; document authoring (M6) |
| Design-aware editing | ✅ themed side-preview in the editors (ADR-0027); live refresh arrives with the autosave layer | — |
| Multilingual | ✅ **core strength**: EN source + per-language states, parity gates | — |
| Authors / bylines | ✅ editorial byline on articles, rendered by the themes | — |

### Media

| Capability | Today | Gap → where |
| --- | --- | --- |
| Library: validated uploads, translatable alt, safe delete | ✅ MIME-sniffed, dimensions parsed | — |
| Image derivatives / responsive sizes | 🟡 dimensions recorded; no derivatives | 🔜 build-time derivatives (M6) |
| Crop / focal point | ❌ | 🔜 with derivatives (M6) |
| Media search / filters | ✅ server-side search (id/path/type/alt) + quick views (images, missing alt) | — |

### Site features (static-first)

| Capability | Today | Gap → where |
| --- | --- | --- |
| SEO: canonical, hreflang, Open Graph, JSON-LD, sitemap, RSS | ✅ in every build | — |
| Search | ✅ client-side index island | — |
| Comments | ❌ | 🧭 integrations (privacy-respecting embed islands) behind a theme contract ADR (M6) |
| Redirects | ❌ | 🔜 redirect map emitted per target (SWA/nginx rules) (M6) |
| Localized 404 / error pages | ✅ | — |
| Multiple sites per install | ❌ one project = one site | out of scope before 1.0 |

### Users and access

| Capability | Today | Gap → where |
| --- | --- | --- |
| Role ladder | ✅ editor < reviewer < publisher < admin | — |
| User management UI | ✅ Users screen (admin role): create, role change, delete — self and last-admin safeguards; CLI stays the bootstrap | — |
| Admin panel in the editor's language | ✅ gettext i18n (ADR-0022): PT-PT/ES/FR/DE shipped, per-user preference + browser fallback, completeness enforced by tests | — |
| Password reset | ❌ no email subsystem | 🧭 email/notification ADR (M7) |
| Two-factor authentication | ❌ | 🔜 TOTP (M7) |
| Notifications (review requested…) | ❌ | 🧭 same email ADR (M7) |

### Platform and operations

| Capability | Today | Gap → where |
| --- | --- | --- |
| Plugin system | ✅ ADR-0028: `sardine.extensions` contract — rules, build steps, targets, backends, themes, `cms x` CLI, section-kind hints; explicit activation in `sardine.toml` | — |
| Themes + per-project overrides | ✅ entry-point discovery | — |
| **Importers** from other CMSs | ❌ | 🔜 `cms import` for the common blog-export formats — the adoption lever (M6) |
| Export / portability | ✅ JSON/Markdown is the source of truth | — |
| Content API | ❌ builds are the API | 🔜 optional JSON content export target (M6) |
| Webhooks (publish → host build) | ❌ | 🔜 on-publish webhook (M7) |
| Health check | 🟡 `cms validate` covers content | 🔜 `cms doctor` (storage, media, config) (M7) |
| Backups | ✅ export is the backup; the DB is disposable | — (document the restore path, M7) |
| Scheduled builds | ✅ recipe in ADMIN_GUIDE (CI `schedule:` + `cms export`); `publish_at`-aware by construction | — |

## Execution order (ADR-driven)

The queue evolves with the ADRs, in this order:

1. **M6 by ADR** (M5 closed): ADR-0028 extension contract (custom content types,
   fields, rules, build steps) → menu manager → image derivatives →
   redirects → importers → ADR-0027 live refresh together with the
   autosave layer.
2. **M7 by ADR**: email/notifications ADR → TOTP 2FA → webhooks →
   `cms doctor`.

## Milestones ahead

- **M5 — Editorial completeness: CLOSED.** Direct unpublish, scheduling,
  revisions with restore, trash, duplicates, per-entry and design-aware
  preview (ADR-0027), quick actions, featured flag, authorship, media
  filters, users screen, editorial notes — all shipped, all live on the
  demo. (Autosave remains queued with the ADR-0027 live-refresh work.)
- **M6 — Extensibility and adoption**: the plugin/extension ADR executed
  (custom content types, custom fields, rules, build steps), menu
  manager, image derivatives, redirects, comments-integration contract,
  JSON content target, the importers so existing sites can walk in.
  (Admin localization shipped early — ADR-0022.)
- **M7 — Operations**: email/notification subsystem (password reset,
  review notifications), TOTP 2FA, webhooks, `cms doctor`, documented
  backup/restore and scheduled-build recipes.
- **1.0** — criteria: M5–M7 shipped, admin stable, two production
  deployments beyond ph7x.com, deprecation policy on PyPI, all
  conformance suites documented as public contracts.

## Standing invariants (any horizon)

Everything lands through the same gates: English-only repo, PR + green CI,
docs move with the code (anti-drift enforced), ADRs for decisions, no
secrets/personal data, deterministic builds, WCAG 2.2 AA baseline, and the
static-first contract — the exported site never needs the admin running.
