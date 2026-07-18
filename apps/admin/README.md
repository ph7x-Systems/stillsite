# cms-admin

The Stillsite admin panel: an authenticated FastAPI application serving both
the admin API and the server-rendered UI (ADR-0013). It drives `cms-core`,
`cms-validation` and `cms-build` through their public APIs — storage comes
from `create_storage(url)`, so every supported engine works unchanged.

```bash
pip install -e apps/admin
STILLSITE_STORAGE_URL="sqlite:///content.db" uvicorn --factory cms_admin.app:create_app
```

There are no default credentials — create the first account with the CLI,
then sign in at `/login`:

```bash
cms admin create-user editor-in-chief -p my-project --role admin
```

The UI is built from vendored hTWOo components served by the admin itself
under `/static/vendor/` (no CDN); the dashboard shows content by workflow
status, the translation coverage matrix and a live validation report.

Configuration is environment-only (no config files with secrets):

| Variable                        | Meaning                                     | Default                |
| ------------------------------- | ------------------------------------------- | ---------------------- |
| `STILLSITE_STORAGE_URL`         | Storage URL for `create_storage`            | `sqlite:///content.db` |
| `STILLSITE_ADMIN_SESSION_HOURS` | Session lifetime in hours                   | `12`                   |
| `STILLSITE_ADMIN_COOKIE_SECURE` | Set `0` only for plain-http local dev       | `1`                    |

Milestone 3 status and the phased plan live in
[docs/PLAN.md](../../docs/PLAN.md).
