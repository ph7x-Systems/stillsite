# Theme Authoring Guide

How to build a Sardine CMS theme — from override to installable package. The
contracts referenced here are code (`cms_build.themes.Theme`), guarded by
tests; this guide shows the path. Read [DESIGN_RULES.md](DESIGN_RULES.md)
first: conformance is what makes a theme a theme. The shipped components and
islands are inventoried in [COMPONENTS.md](COMPONENTS.md).

## Level 0 — override the current theme (no code)

Any project can reshape its theme without forking it (ADR-0007). Files under
the project's `theme/` directory shadow the theme's own:

```text
my-site/
  sardine.toml
  theme/
    templates/article.html.j2    # replaces the theme's article template
    assets/site.css              # replaces the stylesheet (tokens included)
```

Overridden templates can still `{% extends "base.html.j2" %}`. Overridden
assets are re-hashed automatically — cache busting needs no action.

## Level 1 — a theme package

A theme is any object satisfying the `Theme` protocol, registered by name:

```python
from collections.abc import Mapping
from pathlib import Path

from cms_build import register_theme


class MidnightTheme:
    name = "midnight"

    def __init__(self, overrides: Path | None = None) -> None:
        ...  # set up Jinja environment (autoescape on!), honor overrides

    def render(self, kind: str, context: Mapping[str, object]) -> str:
        ...  # kind is one of the template kinds below

    def assets(self) -> Mapping[str, bytes]:
        ...  # e.g. {"assets/site.css": b"...", "assets/search.js": b"..."}


register_theme("midnight", MidnightTheme)
```

A project selects it with `theme = "midnight"` in `sardine.toml`. The
built-in [`DefaultTheme`](../packages/cms-build/src/cms_build/themes/default/__init__.py)
is the working reference implementation — start by copying its shape.

## Template kinds and their contexts

The builder calls `render(kind, context)` with these kinds. Every context
contains `head`, `nav`, `footer` and `asset_urls`; each kind adds its own:

| Kind | Extra context |
| --- | --- |
| `page` | `page` (title, description), `sections` (key, kind, fields, data, images), `latest` (recent articles, for `latest-articles` sections) |
| `article` | `article` (title, summary, body_html, date_iso, date_human, minutes, min_read_label, back_url, back_label, category, tags, author, featured, fields); optional top-level `comments` (ADR-0031) |
| `listing` | `listing` (title, eyebrow, sub, entries, filters, page, pages, previous_url, next_url, search_index_url, search_label, view_cards_label, view_list_label) |
| `not_found` | `not_found` (home_url) |

Contracts to respect:

- **`head` is rendered, never assembled** — canonical, hreflang cluster,
  Open Graph and JSON-LD arrive ready; output them (see the default theme's
  `base.html.j2`).
- **`asset_urls`** maps every asset path to its hash-versioned URL — the only
  way to reference theme assets.
- **`sections`**: a page is a list of typed sections; `section.kind` picks
  your markup. Unknown kinds should render generically, not crash.
- `article.body_html` is pre-rendered safe Markdown — inject it unescaped
  exactly once (`{{ article.body_html }}` with the builder's safe wrapper).

## The section-kind gallery

`SECTION_KIND_GALLERY` in `cms_build.themes` is the authoring contract for
reusable blocks: kind → the field names it consumes. Both bundled themes
implement every kind, the admin's section editor suggests exactly these
fields, and the conformance suite proves each advertised field reaches the
rendered page. A section's context offers the same fields twice: `fields`
(sorted name/value pairs, for generic rendering) and `data` (a mapping, for
kind-specific markup), plus `images` resolved from the section's media list.

| Kind | Fields | Notes |
| --- | --- | --- |
| `hero` | `kicker`, `lead`, `heading`, `accent` | opening statement; `accent` is the emphasized tail of the heading |
| `story` | `kicker`, `heading`, `body` | narrative block; also renders `meta1k`/`meta1v` … `meta6k`/`meta6v` stat pairs and the section's images |
| `expertise` | `kicker`, `heading`, `row1no`, `row1t`, `row1d` | numbered capability rows, repeat up to `row8*` — the numbered convention and its cap retire with [ADR-0037](adr/0037-sections-grow-up.md) `items` |
| `latest-articles` | `kicker`, `heading` | the builder injects the recent-articles list as `latest` |
| `quote` | `quote`, `attribution`, `role` | a pull quote needs no heading — the quote is the content |
| `faq` | `kicker`, `heading`, `q1`, `a1` … | question/answer pairs, repeat up to `q6`/`a6`; rendered as native `<details>` (no JS) — the numbered convention and its cap retire with ADR-0037 `items` |
| `cta` | `kicker`, `heading`, `body`, `button`, `url` | the button renders only when `button` **and** `url` are both set; `url` is per-language content, so each translation can point at its own path |
| `gallery` | `kicker`, `heading` | renders the section's media list as an image grid (`srcset`-aware) |
| `contact` | `kicker`, `heading`, `accent`, `button` | closing call to action; the button links to the last menu entry |

Rules for theme authors:

- Implement the kinds you care about; **everything else must fall through
  to a generic renderer** (fields as labeled values, images below) — the
  conformance suite's unknown-kind test enforces this shape.
- Extensions advertise additional kinds via `Extension.section_kinds`
  (ADR-0028); the admin merges them into its suggestions. The bundled
  names win on collision, so pick distinct kind names.
- Field suggestions are hints, never validation: editors can add any
  field to any section, and your templates should ignore what they do
  not know.

## Interactivity: Web Component islands

Ship interactive behavior as native custom elements in your assets (ES
modules, no framework). Example: a search island consuming the per-language
`search-index.json` the builder already emits:

```html
<site-search index-url="/blog/search-index.json"></site-search>
<script type="module" src="{{ asset_urls['assets/search.js'] }}"></script>
```

The page must remain complete without it (progressive enhancement — see
DESIGN_RULES §5).

## Conformance checklist

Mechanically asserted by `tests/test_theme_conformance.py`:

- [ ] `[hidden]{display:none!important}` first in the base stylesheet
- [ ] Zero inline styles; all assets referenced through `asset_urls`
- [ ] Local fonts/scripts only; no external requests
- [ ] Images rendered with `width`/`height`
- [ ] `prefers-reduced-motion` honored wherever animations exist
- [ ] JavaScript budget respected (≤ 20 KB)
- [ ] Renders all four kinds; every gallery kind's fields reach the page;
      unknown section kinds degrade gracefully

Authoring requirements the accessibility gate and review enforce:

- [ ] No horizontal scroll at 360/820/1280px
- [ ] Autoescape on; `body_html` is the only safe-injected value

Run the output-integrity suite against a build with your theme
(`tests/test_output_integrity.py` shows how): every local reference in your
HTML/CSS must resolve inside the artifact.

Image contexts (`image`, `entry.thumb`) carry an optional `srcset`
string when the project configures `[build] image_widths` (ADR-0029) —
render it with an appropriate `sizes` attribute; ignoring it keeps
working.

Article contexts carry an optional top-level `comments` object
(ADR-0031) when the project configures a `[comments]` provider:
`{label, thread_url, island_url}`. Render it as a plain localized link
to `thread_url` (the no-JS surface) wrapped in a `<site-comments>`
element, plus a module script for the same-origin `island_url` — the
island must contact nothing before an explicit reader action. Ignoring
the key keeps working, like `srcset`.
