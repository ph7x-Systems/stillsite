# Content API — the headless JSON output

Opt-in (M6): `content_api = true` under `[build]` makes every build also
emit versioned JSON under `api/v1/`, next to the HTML. It is a build
output like any other — static files, served by the same host, no server
component — and it follows exactly the publication rules of the HTML
pages: published, out of the trash, past their `publish_at` moment, and
translation-complete per language. The tests in
[`tests/test_content_api.py`](../tests/test_content_api.py) are the
public contract.

## Files

| Path | Contents |
| --- | --- |
| `api/v1/site.json` | `version`, `name`, `base_url`, `blog_path`, `languages` (codes, source first), `categories` (slug → per-language labels) |
| `api/v1/<lang>/content.json` | `version`, `language`, `articles`, `pages` — one file per configured language |

## Article entries

`id`, `slug` (per-language), `url` (site-relative, matches the HTML
page), `title`, `summary`, `body_html` (the same safe rendered Markdown
the theme receives), `date` (ISO), `author`, `featured`,
`category` (`{slug, label, url}` or null), `tags` (`[{slug, url}]`),
`cover` (media metadata: `url`, localized `alt`, `width`, `height`, plus
`srcset` when `[build] image_widths` is configured — ADR-0029), and
`fields` (the article's custom fields).

## Page entries

`id`, `slug`, `url`, `title`, `description` and `sections` — each with
`key`, `kind`, `fields` (the language's resolved field map) and `images`
(same media metadata as covers).

## Guarantees

- **Deterministic**: same content, same configuration, same `now` →
  byte-identical JSON (keys sorted, UTF-8, no timestamps of the build
  itself).
- **Versioned**: the envelope carries `version`; additive fields may
  join within a version, renames or removals move to a new `api/vN/`
  path.
- **Same gates as HTML**: nothing appears in the API that the built site
  does not publish — drafts, trashed and future-scheduled entries stay
  out, and a language file only lists entries whose translation is
  complete.

Live example: <https://sardine.ph7x.com/api/v1/site.json>.
