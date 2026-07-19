# sardine-cms-build

The Sardine CMS deterministic builder: same content in, byte-identical
site out. Renders pages, articles, listings and category/tag pages per
language with full multilingual SEO — canonical, hreflang cluster, Open
Graph, JSON-LD, sitemap, RSS — plus hashed asset URLs, localized UI labels,
safe CommonMark rendering (raw HTML disabled), theme discovery via entry
points (`sardine.themes`) and deployment targets (generic, Azure Static
Web Apps, nginx).

```bash
pip install sardine-cms-build
```

## Sardine CMS

A multilingual, static-first CMS framework: EN-source content with
checksum-tracked translation states (PT-PT, ES, FR, DE), validation gates
before publishing, deterministic builds with full multilingual SEO, and a
browser admin for the whole editorial cycle.

- Live demo: <https://sardine.ph7x.com> (admin demo at [/admin/](https://sardine.ph7x.com/admin/))
- Repository: <https://github.com/ph7x-Systems/sardine-cms>
- Documentation: <https://github.com/ph7x-Systems/sardine-cms/wiki>
- License: Apache-2.0
