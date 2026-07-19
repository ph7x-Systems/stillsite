# Admin Guide

The Sardine CMS admin (`apps/admin`, package `cms-admin`) runs the whole
editorial cycle from the browser. One FastAPI process serves the API and the
server-rendered UI (AdminLTE 4, vendored, CSS-only — ADR-0017); it drives `cms-core`, `cms-validation` and `cms-build`
through their public APIs and never bypasses them (ADR-0013, ADR-0015).
Facts in this guide are checked against the code by the anti-drift suite
(`tests/test_docs.py`).

## Quickstart

```bash
pip install -e apps/admin
cms admin create-user editor-in-chief --role admin   # prompts for a password
SARDINE_STORAGE_URL="sqlite:///content.sqlite3" \
SARDINE_ADMIN_COOKIE_SECURE=0 \
  uvicorn --factory cms_admin.app:create_app
```

Sign in at `/login`. **There are no default credentials** — the first
account always comes from the CLI.

## Configuration (environment only)

| Variable | Default | Meaning |
| --- | --- | --- |
| `SARDINE_STORAGE_URL` | `sqlite:///content.db` | Storage URL for `create_storage` |
| `SARDINE_ADMIN_SESSION_HOURS` | `12` | Session lifetime |
| `SARDINE_ADMIN_COOKIE_SECURE` | `1` | Set `0` only for plain-http local development |
| `SARDINE_MEDIA_DIR` | `media` | Media upload directory (the project's `media/`) |
| `SARDINE_ADMIN_UPLOAD_MAX_MB` | `10` | Upload size limit in MB |
| `SARDINE_PROJECT_DIR` | `.` | Project directory holding `sardine.toml` (panel builds) |
| `SARDINE_ADMIN_PUBLISH_GATE` | `1` | Set `0` to allow publishing despite validation errors |

The admin never reads configuration files — secrets cannot end up in a
project directory that gets committed or exported.

## Roles

The least-privilege ladder: `editor < reviewer < publisher < admin`.
Everyone signed in can edit content and media; the ladder gates workflow
transitions and panel builds.

## The editorial workflow

Content moves through `draft → review → published → archived`:

| Transition | Button | Minimum role |
| --- | --- | --- |
| draft → review | Submit for review | editor |
| review → draft | Send back to draft | reviewer |
| review → published | Publish | publisher |
| published → archived | Archive | publisher |
| archived → draft | Restore to draft | publisher |

Publishing runs the validation ruleset over the would-be state and blocks
with that entity's errors listed (the publish gate; disable only with
`SARDINE_ADMIN_PUBLISH_GATE=0`). Only `published` content reaches builds.

## Editing

- **Articles**: EN source with metadata (per-language slug, category, tags,
  cover), a preview rendered by the builder's own Markdown renderer (raw
  HTML disabled), and a side-by-side editor per translation. Editing the
  source marks its translations `outdated` automatically — states derive
  from content checksums, never from flags.
- **Pages**: metadata plus ordered typed sections; each section is a
  free-form field map the theme interprets, translated side by side.
- **Media**: uploads validated server-side — the MIME type is sniffed from
  the bytes (png, jpeg, gif, webp, svg), dimensions parsed, size limited.
  EN alt text is mandatory; alt is translatable per language. Assets
  referenced by covers or sections refuse deletion.

## Publishing panel

`/publishing` shows the project (`sardine.toml`), the live validation
report, and two actions: **Preview build** (any role) into a temporary
directory served under `/preview/`, and **Build & export** (publisher and
up) which validates first, then writes the project's output directory with
the chosen target's extras (`generic`, `swa`, `nginx`). Every run is
recorded and shown on the panel and the dashboard.

## Security model

- Argon2id password hashes; server-side sessions storing only the token
  digest; cookies `HttpOnly` + `Secure` + `SameSite=Strict`.
- Synchronizer CSRF tokens on every authenticated state-changing request,
  plus a double-submit token on the login form; failed-login rate limiting.
- Security headers on every response, including a Content-Security-Policy
  with no script sources at all (the admin ships zero JavaScript) and
  frame denial.
- Accounts live in the storage database via the shared migrations and are
  **never exported**.
- The axe accessibility gate (WCAG 2.2 AA) runs over the admin pages in CI,
  the same methodology as the public site.

## The demo snapshot

`python -m cms_admin.demo_export` captures the real admin as inert static
HTML for the public demo (`/admin/` on the demo site): links prefixed, CSRF
stripped, forms neutralized, a read-only banner injected. Nothing a visitor
does can save anything — there is no server behind it.
