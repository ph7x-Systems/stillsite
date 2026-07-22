# Roadmap

The product map: what Sardine CMS is for, which capabilities exist,
and what comes next. This page carries **no execution history** — that
lives in [RELEASE_NOTES.md](../RELEASE_NOTES.md) (features, PRs,
migrations), [CHANGELOG.md](../CHANGELOG.md) (per-version changes),
[PRODUCT_HISTORY.md](PRODUCT_HISTORY.md) (how decisions evolved) and
the [issue tracker](https://github.com/ph7x-Systems/sardine-cms/issues)
(the live queue). Execution detail per milestone: [PLAN.md](PLAN.md).
Operations: [DEPLOYMENT.md](DEPLOYMENT.md). Live demo:
<https://sardine.ph7x.com>.

## Vision

A static-first, multilingual CMS with the capability set editors expect
from a mature publishing system — a benchmark, never a clone. Three
pillars:

1. **Editorial confidence** — preview, workflow, revisions, scheduling,
   accessibility and multilingual parity, visible and enforceable.
2. **Adoption without lock-in** — themes, extensions, portable content
   and controlled import paths: a site enters, evolves and leaves
   cleanly.
3. **Operational completeness** — recovery, notifications, webhooks and
   diagnostics beyond development.

Static-first changes *how* a capability works (comments, search and
scheduling need no server at request time), never *whether* editors get
it.

## Milestones

| Milestone | Scope | State |
| --- | --- | --- |
| M0–M3 | Repo, content core, validation, builder, themes, targets, CLI, full browser admin | ✅ closed |
| M4 | Reference theme and example site | ✅ closed |
| M5 | Editorial completeness (scheduling, revisions, trash, preview, notes…) | ✅ closed |
| M6 | Extensibility and adoption (extension contract, portable round-trip, content API…) | ✅ closed |
| M7 | Operations (email, 2FA, webhooks, doctor) | ✅ closed |
| M8 | Reorganized into P0/P1 issues [#126](https://github.com/ph7x-Systems/sardine-cms/issues/126)–[#139](https://github.com/ph7x-Systems/sardine-cms/issues/139) | 🟡 engineering shipped (0.3.0); #127 and #128 stay open for human validation |
| M9 | Reorganized into P2/P3 issues [#140](https://github.com/ph7x-Systems/sardine-cms/issues/140)–[#141](https://github.com/ph7x-Systems/sardine-cms/issues/141) + platform depth | 🟡 in execution (#140 underway) |
| 1.0 | M5–M7 shipped, admin stable, two production deployments beyond ph7x.com, deprecation policy, conformance suites documented as public contracts | 🔜 |

## Capability inventory

Legend: ✅ shipped · 🟡 partial · 🔜 scheduled · 🧭 needs an ADR first.
References point at the ADR, issue or document that owns the detail.

### Editorial workflow

| Capability | State | Reference |
| --- | --- | --- |
| Draft / review / publish / archive, role-gated | ✅ | ADMIN_GUIDE.md |
| Markdown editor with toolbar | ✅ | ADR-0023 |
| Unpublish (one click) | ✅ | ADMIN_GUIDE.md |
| Scheduled publishing | ✅ | ADR-0024 |
| Scheduled unpublish | ✅ | #133 |
| Revisions + restore | ✅ | ADR-0025 |
| Trash / restore | ✅ | ADR-0026 |
| Duplicate content | ✅ | ADMIN_GUIDE.md |
| Per-entry + design-aware preview, autosave, live refresh | ✅ | ADR-0027 |
| Quick actions, featured, editorial notes | ✅ | ADMIN_GUIDE.md |
| Bulk actions on content lists | ✅ | #130 |
| Admin-wide search | ✅ | #129, ADR-0038 |
| Editorial calendar | ✅ | #132 |
| Automated deployment: publish, unpublish, rollback from the admin (P0) | ✅ one versioned provider contract with a registry, capability-aware panel and conformance suite; filesystem/Nginx and Azure Static Web Apps references bundled; extensions add destinations with zero core changes | #156, DEPLOYMENT.md |
| Audit log | ✅ | #134, ADMIN_GUIDE.md |
| Needs-attention dashboard | ✅ | #135, ADMIN_GUIDE.md |

### Content model

| Capability | State | Reference |
| --- | --- | --- |
| Articles + pages with typed sections (open kinds, unlimited, reorderable) | ✅ | THEME_GUIDE.md |
| Repeating groups, Markdown fields, long-form pages | ✅ | ADR-0037 |
| Page editor UX: block gallery, duplicate, hide, undo, drag reorder | ✅ engineering | #127 (open for human validation) |
| Categories, tags, listing pages | ✅ | — |
| Custom fields | ✅ | — |
| Navigation menus | ✅ | — |
| Reusable blocks (section-kind gallery v2) | ✅ | ADR-0037, THEME_GUIDE.md |
| Authors / bylines | ✅ | — |
| In-editor visual page building | 🧭 deferred by ADR-0037 | — |
| Custom content types | 🧭 when a real case appears | ADR-0028 |
| Custom taxonomies, content relations | 🔜 P3 | PRODUCT_HISTORY.md |

### Multilingual

| Capability | State | Reference |
| --- | --- | --- |
| Translation states from checksums; parity gates | ✅ | Content-Model (wiki) |
| Per-language slugs, hreflang, localized feeds + search | ✅ | — |
| Language packs end to end (bundled six included) | ✅ | ADR-0034 |
| Configurable source language | ✅ | ADR-0034 |
| Admin panel languages from packs; RTL end to end | ✅ | ADR-0034 |
| Side-by-side translation editing | ✅ | ADMIN_GUIDE.md |
| Translation queue + list filters | ✅ | #131 |
| Scalable coverage in lists (never a column per language) | ✅ | ADR-0034 |
| Fallback policy per language | 🧭 | — |
| Machine-translation assist | 🧭 | — |
| Data-only language packs | ✅ | LANGUAGE_PACK_GUIDE.md |

### Media

| Capability | State | Reference |
| --- | --- | --- |
| Library: validated uploads, translatable alt, safe delete, search/filters | ✅ | ADMIN_GUIDE.md |
| Image derivatives / responsive sizes | ✅ | ADR-0029 |
| Crop / focal point, WebP/AVIF, organization, picker, replace | ✅ | #136 |

### Site features (static-first)

| Capability | State | Reference |
| --- | --- | --- |
| SEO: canonical, hreflang, Open Graph, JSON-LD, sitemap, RSS | ✅ | — |
| Public search (pre-built indexes) | ✅ | — |
| Comments | 🟡 contract + consent-first island; official provider pending | ADR-0031 |
| Redirects, localized error pages | ✅ | — |
| Forms | ✅ end to end: section kind, official endpoint, storage, provider contract | #137, ADR-0039, ADR-0040 |
| Per-entry SEO controls | ✅ with advisory hints and slug-change redirects | #138, ADR-0041 |
| External review links | ✅ signed, expiring, revocable | #139, ADR-0042 |
| Embeds, analytics | 🧭 | — |
| Multiple sites per install | 🔜 P3 | — |

### Users and access

| Capability | State | Reference |
| --- | --- | --- |
| Role ladder, user management UI | ✅ | ADMIN_GUIDE.md |
| Panel in the editor's language | ✅ | ADR-0022, ADR-0034 |
| Password reset, notifications | ✅ | ADR-0032 |
| Two-factor authentication (per-role enforcement) | ✅ | ADR-0035 |
| Browser onboarding (setup + deployment wizards) | ✅ engineering | #128 (open for human validation) |
| SSO / OIDC | 🧭 post-1.0 | — |

### Platform and operations

| Capability | State | Reference |
| --- | --- | --- |
| Plugin system (explicit activation) | ✅ | ADR-0028 |
| Themes + per-project overrides | ✅ | THEME_GUIDE.md |
| Import / export / portability | ✅ | Content-Model (wiki) |
| Content API (versioned JSON) | ✅ | CONTENT_API.md |
| Webhooks (on publish) | ✅ | ADR-0036 |
| Health check (`cms doctor`) | ✅ | — |
| Theme/extension experience without editing files | 🟡 shipped: Themes screen (discover installed themes, try-first activation, failure containment), manifest-backed cards with screenshots and compatibility · pending: extension activation and health, official theme set | #141, ADR-0048, ADR-0049 |
| WXR migration flow | ✅ end to end: inspection with fidelity report, idempotent re-import by source id, `--update` keeping entity ids, mappings, media fetch with rewrite, automatic redirects, and the panel Migration screen on the same shared pipeline | #140, ADR-0043–0047 |
| Backups, scheduled builds | 🧭 | — |
| Incremental builds, ecosystem catalog | 🔜 P3 | — |

## Priorities

The live queue is the [issue tracker](https://github.com/ph7x-Systems/sardine-cms/issues),
prioritized P0 (usable by a non-technical editor) → P3 (scale), with
observation-driven reordering — see
[PRODUCT_HISTORY.md](PRODUCT_HISTORY.md) for how and why.

## Definition of done

A capability is ✅ only when all hold: usable in the admin; E2E tested;
works in both bundled themes; works in at least two languages; has
empty and error states; documented (repo + wiki); demonstrated on the
public demo. A contract without a bundled usable implementation is 🟡,
never ✅. ADRs are reserved for decisions that change public contracts,
storage, security or extensibility.

## Product metrics (targets)

| Metric | Target |
| --- | --- |
| First site published (seed path, browser) | < 10 minutes |
| First page created | without touching the CLI |
| Landing page built by a non-technical editor | < 15 minutes |
| Preview refresh | < 2 seconds |
| Admin search on 10 000 entries | < 300 ms |
| WXR migration of a reference export | explicit fidelity % reported |

Each metric, when measured, must declare its method — environment,
dataset, runs, percentile, tester (editor metrics require a real
non-technical tester) — and record the result in
[RELEASE_NOTES.md](../RELEASE_NOTES.md). A number without its method
does not count.

## Standing invariants (any horizon)

Language sets are data, never structure: anything per-language is
modeled as rows, keys or configuration — never schema columns, fixed
enumerations or hardcoded strings — so adding a language (packs, RTL
included) never alters a table or a code path.

Everything lands through the same gates: English-only repo, PR + green
CI, repository docs and wiki move with the code, ADRs for decisions,
no secrets or personal data, deterministic builds, WCAG 2.2 AA
baseline, and the static-first contract — the exported site never
needs the admin running.
