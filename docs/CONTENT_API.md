# Content API

Sardine can publish the site's content as static, versioned JSON
alongside the HTML. There is no server component and no authentication:
the files are part of the build output and are served by whatever hosts
the site.

## Enabling it

```toml
[build]
content_api = true
```

Every build then also writes the API files under `api/v1/`.

## Endpoints

| Path | Contents |
| --- | --- |
| `/api/v1/site.json` | Site metadata: name, base URL, blog path, languages, categories |
| `/api/v1/<lang>/content.json` | All published articles and pages for one language |

## Example

```text
GET /api/v1/site.json
```

```json
{
  "version": 1,
  "name": "Aurora Cartography",
  "base_url": "https://example.com/",
  "blog_path": "blog",
  "languages": ["en", "pt-pt"],
  "categories": {"field-notes": {"en": "Field notes", "pt-pt": "Notas de campo"}}
}
```

## Response contract

Every file carries `version` — the API version it speaks.

**`site.json`** — `name`, `base_url`, `blog_path`, `languages` (codes,
source language first) and `categories` (slug → per-language labels).

**`<lang>/content.json`** — `language` plus two lists:

- **`articles`**: `id`, `slug` (per-language), `url` (site-relative,
  matches the HTML page), `title`, `summary`, `body_html` (safe rendered
  HTML), `date` (ISO 8601), `author`, `featured`, `category`
  (`{slug, label, url}` or `null`), `tags` (`[{slug, url}]`), `cover`
  (media metadata: `url`, localized `alt`, `width`, `height`, `focal`
  (`{x, y}` fractions of the image, present when an editor set one),
  `sources` (a list of `{type, srcset}` alternatives in modern formats
  such as WebP/AVIF, best first; may be empty), plus `srcset` when
  image derivatives are configured) and `fields` (the article's custom
  fields).
- **`pages`**: `id`, `slug`, `url`, `title`, `description` and
  `sections` — each with `key`, `kind`, `fields` (the language's
  resolved field map) and `images` (the same media metadata as covers).

Articles and pages additionally carry `seo` when an editor set
per-entry overrides: `seo_title`, `seo_description`, `noindex`,
`canonical`, `og_image` — absent otherwise.

## Guarantees

- **Only published content**: the API lists exactly what the built site
  publishes — no drafts, trashed entries or entries outside their
  publication window; a language file only lists entries whose
  translation is complete.
- **Stable within a version**: fields may be added within `v1`; renames
  or removals only ever happen under a new `/api/vN/` path, so a
  consumer pinned to `/api/v1/` keeps working.
- **Static and cacheable**: plain UTF-8 JSON files on the same host as
  the site — cache and CDN them like any other static asset.

Live example: <https://sardine.ph7x.com/api/v1/site.json>.
