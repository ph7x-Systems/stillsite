# sardine-cms-admin

The Sardine CMS admin panel: an authenticated FastAPI application serving both
the admin API and the server-rendered UI (ADR-0013). It drives `cms-core`,
`cms-validation` and `cms-build` through their public APIs — storage comes
from `create_storage(url)`, so every supported engine works unchanged.

```bash
pip install sardine-cms-admin
SARDINE_STORAGE_URL="sqlite:///content.db" uvicorn --factory cms_admin.app:create_app
```

There are no default credentials — create the first account with the CLI,
then sign in at `/login`:

```bash
cms admin create-user editor-in-chief -p my-project --role admin
```

The UI is built on AdminLTE 4 (MIT, vendored verbatim with its license —
ADR-0017), used CSS-only and implemented as its reference pages do:
Source Sans 3 (OFL) and Bootstrap Icons (MIT) ship as local files, the
admin serves everything itself with zero JavaScript and no CDN, and the
only overlay is accessibility fixes and no-JS fallbacks. The dashboard shows
content by workflow status, the translation coverage matrix and a live
validation report. Articles and pages are edited in the browser: EN source
plus a side-by-side editor per translation, with state indicators from the
checksum model and a preview rendered by the builder's own Markdown
renderer (raw HTML disabled). The media library uploads with server-side
validation (MIME sniffed from bytes, size limit, parsed image dimensions),
manages mandatory EN + translatable alt text, and refuses to delete assets
that articles or sections still reference. The workflow moves content through
draft → review → published → archived with each transition owned by a rung
of the role ladder; publishing runs the validation gate. The Publishing
panel previews into `/preview/` and builds/exports the project output with
target extras, with every run recorded on the dashboard.

Configuration is environment-only (no config files with secrets):

| Variable                        | Meaning                                     | Default                |
| ------------------------------- | ------------------------------------------- | ---------------------- |
| `SARDINE_STORAGE_URL`         | Storage URL for `create_storage`            | `sqlite:///content.db` |
| `SARDINE_ADMIN_SESSION_HOURS` | Session lifetime in hours                   | `12`                   |
| `SARDINE_ADMIN_COOKIE_SECURE` | Set `0` only for plain-http local dev       | `1`                    |
| `SARDINE_MEDIA_DIR`             | Media upload directory (the project's)      | `media`                |
| `SARDINE_ADMIN_UPLOAD_MAX_MB`   | Upload size limit in MB                     | `10`                   |
| `SARDINE_PROJECT_DIR`           | Project directory (`sardine.toml`)          | `.`                    |
| `SARDINE_ADMIN_PUBLISH_GATE`    | Set `0` to publish despite validation errors | `1`                   |

The full admin guide — configuration, roles, workflow, publishing,
security model — is [docs/ADMIN_GUIDE.md](https://github.com/ph7x-Systems/sardine-cms/blob/main/docs/ADMIN_GUIDE.md)
(anti-drift-checked). Milestone 3 status and the phased plan live in
[docs/PLAN.md](https://github.com/ph7x-Systems/sardine-cms/blob/main/docs/PLAN.md).

## Sardine CMS

- Live demo: <https://sardine.ph7x.com> (admin demo at [/admin/](https://sardine.ph7x.com/admin/))
- Repository: <https://github.com/ph7x-Systems/sardine-cms>
- Documentation: <https://github.com/ph7x-Systems/sardine-cms/wiki>
- License: Apache-2.0
