# Theme Authoring Guide

How to build a Stillsite theme — from override to installable package. The
contracts referenced here are code (`cms_build.themes.Theme`), guarded by
tests; this guide shows the path. Read [DESIGN_RULES.md](DESIGN_RULES.md)
first: conformance is what makes a theme a theme. The shipped components and
islands are inventoried in [COMPONENTS.md](COMPONENTS.md).

## Level 0 — override the current theme (no code)

Any project can reshape its theme without forking it (ADR-0007). Files under
the project's `theme/` directory shadow the theme's own:

```text
my-site/
  stillsite.toml
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

A project selects it with `theme = "midnight"` in `stillsite.toml`. The
built-in [`DefaultTheme`](../packages/cms-build/src/cms_build/themes/default/__init__.py)
is the working reference implementation — start by copying its shape.

## Template kinds and their contexts

The builder calls `render(kind, context)` with these kinds. Every context
contains `head`, `nav`, `footer` and `asset_urls`; each kind adds its own:

| Kind | Extra context |
| --- | --- |
| `page` | `page` (title, description), `sections` (key, kind, fields, images) |
| `article` | `article` (title, summary, date_iso, category, tags, body_html) |
| `listing` | `listing` (title, entries, page, pages, previous_url, next_url) |
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

## Conformance checklist (what CI will assert)

- [ ] `[hidden]{display:none!important}` first in the base stylesheet
- [ ] Zero inline styles; all assets referenced through `asset_urls`
- [ ] Local fonts/scripts only; no external requests
- [ ] Images rendered with `width`/`height`
- [ ] No horizontal scroll at 360/820/1280px; `prefers-reduced-motion` honored
- [ ] Autoescape on; `body_html` is the only safe-injected value
- [ ] Renders all four kinds; unknown section kinds degrade gracefully

Run the output-integrity suite against a build with your theme
(`tests/test_output_integrity.py` shows how): every local reference in your
HTML/CSS must resolve inside the artifact.
