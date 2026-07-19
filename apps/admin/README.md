# cms-admin

The Sardine CMS admin panel: an authenticated FastAPI application serving both
the admin API and the server-rendered UI (ADR-0013). It drives `cms-core`,
`cms-validation` and `cms-build` through their public APIs — storage comes
from `create_storage(url)`, so every supported engine works unchanged.

```bash
pip install -e apps/admin
SARDINE_STORAGE_URL="sqlite:///content.db" uvicorn --factory cms_admin.app:create_app
```

There are no default credentials — create the first account with the CLI,
then sign in at `/login`:

```bash
cms admin create-user editor-in-chief -p my-project --role admin
```

The UI speaks the ph7x design system natively (ADR-0015): the same tokens
and local Inter/Newsreader font subsets as the reference theme, one
self-served stylesheet, no component library, no CDN. The dashboard shows
content by workflow status, the translation coverage matrix and a live
validation report. Articles and pages are edited in the browser: EN source
plus a side-by-side editor per translation, with state indicators from the
checksum model and a preview rendered by the builder's own Markdown
renderer (raw HTML disabled).

Configuration is environment-only (no config files with secrets):

| Variable                        | Meaning                                     | Default                |
| ------------------------------- | ------------------------------------------- | ---------------------- |
| `SARDINE_STORAGE_URL`         | Storage URL for `create_storage`            | `sqlite:///content.db` |
| `SARDINE_ADMIN_SESSION_HOURS` | Session lifetime in hours                   | `12`                   |
| `SARDINE_ADMIN_COOKIE_SECURE` | Set `0` only for plain-http local dev       | `1`                    |

Milestone 3 status and the phased plan live in
[docs/PLAN.md](../../docs/PLAN.md).
