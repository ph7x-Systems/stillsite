# Language Pack Guide

How to give Sardine CMS a language it does not ship — as a package
anyone can install. A language pack is data, not code (ADR-0034):
every locale, script and text direction travels through the same
contract the five bundled languages use. There are no privileged
languages.

## The contract

A pack is one `LanguagePack` object contributed through an extension
(ADR-0028):

```python
from cms_core import Extension, LanguagePack

extension = Extension(
    name="lang-mir",
    language_packs=(
        LanguagePack(
            tag="mir",  # BCP-47-shaped, lowercase
            direction="rtl",  # "ltr" or "rtl"
            native_name="Mirrorish",  # the language's name in itself
            site_labels={...},  # UI label key -> text
            month_names=(...),  # exactly 12, for date formatting
            date_pattern="{day} {month} {year}",
            admin_catalog=CATALOG,  # optional: gettext .po bytes
        ),
    ),
)
```

| Field | Meaning |
| --- | --- |
| `tag` | The language tag (`[a-z]{2,3}(-[a-z0-9]{2,8})*`). Activating the pack registers it: the tag becomes usable in `[site] source_language` and `[site] languages`. |
| `direction` | Text direction. `rtl` puts `dir="rtl"` on `<html>` for the language's pages **and** the admin panel; both bundled themes are flow-relative CSS throughout (conformance-tested), so the layout mirrors, not just the text. |
| `native_name` | Shown in language selectors — the panel's switcher lists the pack by this name. |
| `site_labels` | The public-site UI strings (`blog`, `search`, `min-read`, error titles…). `cms_build.ui.LABEL_KEYS` is the authoritative key list. Missing keys fall back to the project's source pack, then to the key itself — a partial pack degrades loudly-visibly, never crashes. |
| `month_names` | Twelve month names; empty falls back to the source pack's. |
| `date_pattern` | Deterministic `{day}/{month}/{year}` pattern (e.g. `"{day} de {month} de {year}"` for pt-pt). |
| `admin_catalog` | Optional gettext `.po` content (bytes, UTF-8, English msgids). When present, the pack's language is also a **panel** language: offered in the switcher, compiled in memory at startup. Without it the panel stays English for this language — content in the language still works fully. |

A data-only package — an extension whose *only* contribution is
`language_packs` — is a first-class ecosystem shape; the test suite
proves it end to end (`test_a_data_only_pack_extension_is_a_valid_extension`).

## Activation

The user adds your package and one line:

```toml
extensions = ["sardine_lang_mir"]

[site]
source_language = "mir"   # or a target in `languages`
languages = ["en"]
```

That is the whole integration. The tag builds at the URL root when it
is the source, under `/mir/` when a target; labels, dates, feeds,
hreflang and validation parity all follow the pack. A configured tag
whose pack is not activated fails loudly at load time.

## Registration semantics

- `register_language_pack` is idempotent by value and **loud on
  conflict**: two different packs claiming one tag raise immediately.
- Packs register before the site's language list parses, so a
  pack-provided tag is valid in `sardine.toml` from the first read.

## Writing the admin catalog

Msgids are the panel's English source strings. The anti-drift pattern
in `tests/test_admin_i18n.py` shows how the repository keeps its own
catalogs complete; for a pack, completeness is your call — untranslated
msgids fall back to English string by string. Start from the bundled
catalogs in `packages/cms-core/src/cms_core/locale/` as a reference.

## RTL

Declare `direction="rtl"` and everything else is already done: the
markup carries `dir`, both bundled themes and the panel are logical-CSS
only (the theme conformance suite bans physical properties, third-party
themes included), and CI drives an RTL build through the axe
accessibility gate on every push (`scripts/rtl_probe.py`).

## Naming and listing

Package-name pattern (nominative-use grant, ADR-0011):
`sardine-lang-<tag>` — e.g. `sardine-lang-mir`. Tag the repository with
the GitHub topics `sardine-cms` and `sardine-lang`, then open a pull
request adding a row to the registry in
[ECOSYSTEM.md](ECOSYSTEM.md) — requirements there apply (OSI license,
tests, no trademark misuse).

## Testing your pack

Copy the repository's pattern (`tests/test_extensions.py`):

1. Write a `sardine.toml` activating your extension with your tag in
   `languages` (and once as `source_language`).
2. Build with `cms build` or `build_site` and assert your labels,
   month names and `dir` appear in the output.
3. If you ship an `admin_catalog`, start the admin against the project
   and assert your language shows in the switcher and translates a
   known string.
