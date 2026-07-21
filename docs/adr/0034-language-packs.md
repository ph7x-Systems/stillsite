# ADR-0034 — Language packs: abstract locales, contributable, direction-aware

- **Status:** proposed
- **Date:** 2026-07-21

## Context

Multilingualism is the product's core strength, and it is modeled
correctly where it matters most: every translation structure in storage
is **row-per-language** (composite keys with a `language` value column),
so adding a language never alters a table. The hardness lives one layer
up, in code: `Language` is a closed enumeration of five tags
(`en`, `pt-pt`, `es`, `fr`, `de`), the source language is fixed to EN,
the builder's UI labels and date formats are dictionaries keyed by that
enum, and the admin's gettext catalogs are the four files shipped in the
repository. Nobody can add Arabic, Italian or Mandarin — as a project
choice or as a community contribution — without forking the core. The
owner's directive is explicit: language support must be **abstract**,
language packs must be **contributable by anyone**, and right-to-left
scripts are in scope from the start.

## Decision

**A locale is data. A language pack is a contribution. Nothing about a
language is ever schema, enumeration or hardcoded string.**

1. **Locale identity: validated tags, not an enum.** `Language` becomes
   a validated value type over lowercase BCP-47-style tags
   (`pt-pt`, `ar`, `zh-hans`…), pattern-checked, unlimited. The current
   enum members survive as constants during a deprecation window; the
   five current tags keep their exact meaning, so existing projects,
   exports and databases migrate by doing nothing.
2. **The project owns its locale set.** `[site] languages` (already in
   `sardine.toml`) becomes the open set, and `[site]
   source_language` (default `en`) makes the source configurable.
   Validation, parity gates and translation states are already
   locale-agnostic (checksum-derived) and keep working unchanged.
3. **A language pack is one bundle** with everything a locale needs:

   - `tag` — the locale identifier;
   - `direction` — `ltr` or `rtl`;
   - site UI labels (the `LABEL_KEYS` set) and date formatting
     (month names + pattern — deterministic, no OS locale calls);
   - an admin catalog (`.po` content) for the panel chrome, plural
     rules included via gettext.

   The five bundled languages become five bundled packs — the core
   dogfoods the same contract it offers.
4. **Contribution path: extensions.** `Extension.language_packs`
   registers packs by tag (ADR-0028 pattern, explicit activation). A
   community package like `sardine-lang-<tag>` ships one pack; the
   ecosystem policy (ECOSYSTEM.md) lists them like themes and backends.
5. **Direction-aware output.** The builder emits `dir` on `<html>` per
   page language; the admin sets `dir` for the panel language. Both
   bundled themes and the admin overlay migrate to CSS logical
   properties where direction matters (`margin-inline-*`,
   `padding-inline-*`, `text-align: start/end`); DESIGN_RULES gains the
   rule and the conformance suite asserts no new physical-direction
   regressions in the migrated surfaces.
6. **Fallback chain stays simple and explicit**: requested locale → its
   pack; missing pack for a configured locale is a **loud build/startup
   error** (the ADR-0029/0031/0032 pattern — configured capability never
   silently missing); untranslated content keeps the existing
   translation-state machinery (missing/outdated block publishing per
   the parity gates).

## Amendment — no privileged languages (owner directive)

The bundled five are packs like any other: their labels, month names,
date patterns and admin catalogs move INTO their packs, and the tables
in `cms_build.ui` plus the repository catalog files dissolve. "EN is
the source" becomes the factory default of `[site] source_language`,
never a rule. Admin lists obey the same principle spatially: aggregate
summaries, never horizontal growth per language.

## Design note — configurable source language (*executed as designed*)

The model layer already treats the source correctly: `source` is just
"the source content", and `translations` map target tags to content —
nothing in storage records which language the source *is*. The tag is
implicit at the boundaries, and that is where the change lives:

- `[site] source_language` (default `en`, must be a registered pack
  tag, must not appear in `languages`) joins `SiteConfig`.
- Core APIs that embed the source tag today gain an explicit
  `source: Language = SOURCE_LANGUAGE` parameter — portable
  export/import, menu label fallback — so the constant becomes a
  default, not a truth.
- The builder replaces every `is SOURCE_LANGUAGE` comparison with the
  config's source: URL tree (the source lives at the root), hreflang,
  feeds, labels' source-pack fallback, content API.
- The admin reads the project's source for the side-by-side editors
  (the left column is "the source", whatever its tag) and for
  notification/reset localization fallbacks.
- The five-language demo keeps `en` — zero behavior change for every
  existing project is the acceptance bar, proven by the suite plus new
  tests building a project whose source is a non-`en` pack tag.

## Execution (phased, each phase its own PR)

1. **Core** — *executed (phases 1a + 1b)*: `Language` is an interned,
   validated tag type with the enum's exact surface plus
   `Language.register(tag)` (1a). `LanguagePack` exists as the contract
   — tag, direction, site labels, month names, date pattern, optional
   admin catalog — with a registry, the five bundled tags registered,
   and `Extension.language_packs` wiring so an activated extension's
   pack makes its tag a full content language: configurable in
   `sardine.toml`, built, labeled, date-formatted and rendered with
   `dir="rtl"` when the pack says so (1b, tested end to end with a
   fictional RTL pack). The bundled five's labels, months and date
   patterns now live in their packs — the `cms_build.ui` tables are
   gone (no language data outside packs). Still ahead: configurable
   source language (its own slice) and admin catalogs in packs.
2. **Builder + themes**: labels/dates resolved from packs; `dir`
   attribute; logical-properties migration with conformance coverage.
3. **Admin** — *executed*: catalogs live in the packs
   (`LanguagePack.admin_catalog`, the bundled four moved into
   cms-core), the panel offers every registered pack carrying a
   catalog by its `native_name`, the chrome renders the resolved
   language's `dir`, and the editors' source/target sets come from the
   project's configuration.
4. **Ecosystem** — *executed*: LANGUAGE_PACK_GUIDE.md (THEME_GUIDE-style)
   + wiki page, `sardine-lang-<tag>` naming and a registry row in
   ECOSYSTEM.md, a data-only pack extension proven end to end in the
   test suite, and `scripts/rtl_probe.py` driving a fictional RTL
   locale through the CI accessibility gate on every push.

## Consequences

- The standing invariant added to ROADMAP.md becomes enforceable:
  languages are rows, keys and configuration — never schema columns,
  enumerations in new contracts, or hardcoded strings.
- Determinism is preserved: packs are data resolved at build/startup;
  no OS locale, no ICU calls at render time.
- The demo keeps its five languages; an RTL example locale joins the
  test suite, not the demo, until a real pack exists.
- Content in languages without a pack cannot build — deliberately: half-shipped languages produce broken chrome, and loud failure beats silent
  English fallbacks in a product whose promise is parity.
