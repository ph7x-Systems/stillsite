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
| **Unpublish** (published straight back to draft) | ❌ only publish→archive→draft, two steps | 🔜 direct transition (M5) |
| Scheduled publishing | ❌ | 🔜 `publish_at` + build-time gate; static-first = the scheduled build publishes it (M5) |
| Revisions + restore | ❌ last write wins | 🔜 revision log on save, diff view, restore (M5) |
| Trash / restore | ❌ delete is final (admin refuses only referenced media) | 🔜 soft-delete status + restore + purge (M5) |
| Duplicate content | ❌ | 🔜 "Duplicate as draft" (M5) |
| Per-entry preview | 🟡 whole-site preview at `/preview/` | 🔜 jump from editor to the entry's preview URL (M5) |
| Quick edit (slug/status from the list) | ❌ | 🔜 list-row actions (M5) |
| Featured / pinned content | ❌ | 🔜 featured flag consumed by themes (M5) |
| Editorial notes on entries | ❌ | 🔜 note trail per entry (M5) |
| Autosave while editing | ❌ | 🔜 with the admin's JS layer (M5, after ADR-0020) |

### Content model

| Capability | Today | Gap → where |
| --- | --- | --- |
| Articles + pages with typed sections | ✅ | — |
| Categories, tags, listing pages | ✅ incl. validation rule | — |
| Custom content types | ❌ | 🧭 extension ADR (M6) |
| Custom fields | 🟡 sections carry typed fields; articles have a fixed schema | 🔜 article custom fields (M6) |
| Navigation menus | 🟡 menus derive from section `menu` fields + published pages | 🔜 explicit menu manager (M6) |
| Reusable blocks | 🟡 section kinds are the block library | 🔜 grow the kind gallery; document authoring (M6) |
| Multilingual | ✅ **core strength**: EN source + per-language states, parity gates | — |
| Authors / bylines | ❌ content has no author field | 🔜 authorship fields + theme credit (M5) |

### Media

| Capability | Today | Gap → where |
| --- | --- | --- |
| Library: validated uploads, translatable alt, safe delete | ✅ MIME-sniffed, dimensions parsed | — |
| Image derivatives / responsive sizes | 🟡 dimensions recorded; no derivatives | 🔜 build-time derivatives (M6) |
| Crop / focal point | ❌ | 🔜 with derivatives (M6) |
| Media search / filters | ❌ flat list | 🔜 filters + search in the library (M5) |

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
| User management UI | 🟡 CLI only (`cms admin create-user`) | 🔜 users screen in the admin (M5) |
| Admin panel in the editor's language | ❌ the panel is EN-only | 🧭 admin-localization ADR: label catalog like the site's, per-user language preference, PT-PT/ES/FR/DE shipped (M6) |
| Password reset | ❌ no email subsystem | 🧭 email/notification ADR (M7) |
| Two-factor authentication | ❌ | 🔜 TOTP (M7) |
| Notifications (review requested…) | ❌ | 🧭 same email ADR (M7) |

### Platform and operations

| Capability | Today | Gap → where |
| --- | --- | --- |
| Plugin system | ❌ | 🧭 extension ADR: content types, rules, build steps, CLI subcommands (M6) |
| Themes + per-project overrides | ✅ entry-point discovery | — |
| **Importers** from other CMSs | ❌ | 🔜 `cms import` for the common blog-export formats — the adoption lever (M6) |
| Export / portability | ✅ JSON/Markdown is the source of truth | — |
| Content API | ❌ builds are the API | 🔜 optional JSON content export target (M6) |
| Webhooks (publish → host build) | ❌ | 🔜 on-publish webhook (M7) |
| Health check | 🟡 `cms validate` covers content | 🔜 `cms doctor` (storage, media, config) (M7) |
| Backups | ✅ export is the backup; the DB is disposable | — (document the restore path, M7) |
| Scheduled builds | ❌ | 🔜 documented cron/Actions recipe + `publish_at` awareness (M5/M7) |

## Milestones ahead

- **M5 — Editorial completeness** (next): everything an editor expects
  inside the panel — direct unpublish, scheduling, revisions with
  restore, trash, duplicates, per-entry preview, quick actions, featured
  flag, authorship, media filters, users screen, editorial notes.
  Checklist in [PLAN.md](PLAN.md).
- **M6 — Extensibility and adoption**: the plugin/extension ADR executed
  (custom content types, custom fields, rules, build steps), menu
  manager, image derivatives, redirects, comments-integration contract,
  JSON content target, the importers so existing sites can walk in — and
  the **admin panel localized** (label catalog + per-user language,
  starting with the five site languages).
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
