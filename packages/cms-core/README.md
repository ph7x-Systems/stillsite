# sardine-cms-core

The Sardine CMS content core: articles, pages with ordered typed sections,
media with mandatory translatable alt text, and the translation-state
machinery — `missing / outdated / complete` derived from content checksums,
so editing a source automatically flags its translations.

Storage is a strict contract behind `create_storage(url)` with a shared,
versioned migration history across four engines:

```bash
pip install sardine-cms-core               # SQLite built in
pip install "sardine-cms-core[postgres]"   # PostgreSQL (psycopg 3)
pip install "sardine-cms-core[mysql]"      # MySQL / MariaDB (PyMySQL)
pip install "sardine-cms-core[mssql]"      # SQL Server (pymssql)
```

The database is never the source of truth — portable JSON/Markdown export
is. Admin accounts live in storage but are never exported.

## Sardine CMS

A multilingual, static-first CMS framework: EN-source content with
checksum-tracked translation states (PT-PT, ES, FR, DE), validation gates
before publishing, deterministic builds with full multilingual SEO, and a
browser admin for the whole editorial cycle.

- Live demo: <https://sardine.ph7x.com> (admin demo at [/admin/](https://sardine.ph7x.com/admin/))
- Repository: <https://github.com/ph7x-Systems/sardine-cms>
- Documentation: <https://github.com/ph7x-Systems/sardine-cms/wiki>
- License: Apache-2.0
