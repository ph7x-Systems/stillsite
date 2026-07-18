# cms-admin

The Stillsite admin panel: an authenticated FastAPI application serving both
the admin API and the server-rendered UI (ADR-0013). It drives `cms-core`,
`cms-validation` and `cms-build` through their public APIs — storage comes
from `create_storage(url)`, so every supported engine works unchanged.

```bash
pip install -e apps/admin
STILLSITE_STORAGE_URL="sqlite:///content.db" uvicorn --factory cms_admin.app:create_app
```

Configuration is environment-only (no config files with secrets):

| Variable                | Meaning                              | Default                |
| ----------------------- | ------------------------------------ | ---------------------- |
| `STILLSITE_STORAGE_URL` | Storage URL for `create_storage`     | `sqlite:///content.db` |

Milestone 3 status and the phased plan live in
[docs/PLAN.md](../../docs/PLAN.md).
