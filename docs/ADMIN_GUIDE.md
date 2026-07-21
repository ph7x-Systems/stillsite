# Admin Guide

The Sardine CMS admin (`apps/admin`, package `cms-admin`) runs the whole
editorial cycle from the browser. One FastAPI process serves the API and the
server-rendered UI (AdminLTE 4, vendored, with same-origin behaviors —
ADR-0017/0020); it drives `cms-core`, `cms-validation` and `cms-build`
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
account always comes from the CLI. Passwords must contain between 12 and
1024 characters. Replacing an account with `cms admin create-user --force`
revokes all of its existing sessions before storing the new credentials.

## Configuration (environment only)

| Variable | Default | Meaning |
| --- | --- | --- |
| `SARDINE_STORAGE_URL` | `sqlite:///content.db` | Storage URL for `create_storage` |
| `SARDINE_ADMIN_SESSION_HOURS` | `12` | Session lifetime |
| `SARDINE_ADMIN_COOKIE_SECURE` | `1` | Set `0` only for plain-http local development |
| `SARDINE_MEDIA_DIR` | `media` | Media upload directory (the project's `media/`) |
| `SARDINE_ADMIN_UPLOAD_MAX_MB` | `10` | Upload size limit in MB |
| `SARDINE_ADMIN_UPLOAD_MAX_PIXELS` | `40000000` | Maximum image dimensions (`width × height`) |
| `SARDINE_PROJECT_DIR` | `.` | Project directory holding `sardine.toml` (panel builds) |
| `SARDINE_ADMIN_PUBLISH_GATE` | `1` | Set `0` to allow publishing despite validation errors |
| `SARDINE_MAIL_TRANSPORT` | `smtp` | Outbound email transport (ADR-0032): `smtp` is the bundled baseline; any other name resolves to an activated extension's mail transport (passwordless provider APIs) |
| `SARDINE_SMTP_URL` | unset | For the `smtp` transport: `smtp://user:pass@host:587` (STARTTLS) or `smtps://host:465`; unset keeps email off |
| `SARDINE_MAIL_FROM` | unset | The From address for panel email; required together with the SMTP URL |

### Password reset (ADR-0032)

With SMTP configured and an address on the account (Users screen or
`cms admin create-user --email`), the login page offers "Forgot your
password?". The response never reveals whether an account exists; the
mailed link is single-use, expires in 30 minutes, and its token is
stored only as a hash. Completing a reset applies the password policy
and revokes every session of the account. Without SMTP the pages do not
exist and the panel behaves exactly as before.

### Notifications (ADR-0032)

With email configured, two events notify by mail: a transition into
review mails every account of role reviewer or above that has an
address (except the actor), and publishing mails the entry's most
recent editing author. Messages are plain text in each recipient's
panel language; delivery runs off the request path and a transport
failure never becomes an editorial error.

### Two-factor authentication (ADR-0035)

Self-service TOTP (RFC 6238, the profile every authenticator app
implements — standard library only). Each user enables it from the user
menu: enter the shown key in an authenticator app and confirm with a
valid code; from then on sign-in requires the current code, every code
is single-use, and wrong codes spend the same rate-limit budget as
wrong passwords. Disabling requires a valid code. There are no backup
codes in this phase: the recovery path is
`cms admin create-user --force`, which replaces the account, clears
two-factor state and revokes every session. Password reset by email
deliberately does not clear the second factor.

The admin never reads configuration files — secrets cannot end up in a
project directory that gets committed or exported. Preview artifacts and
uploaded media are served only to an authenticated session. Responses are
non-cacheable and carry HSTS; keep secure cookies enabled behind HTTPS in
every non-local deployment. Secure deployments use `__Host-` cookies, which
cannot be scoped by a parent domain or overwritten by a sibling subdomain.

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
| published → draft | Unpublish | publisher |
| published → archived | Archive | publisher |
| archived → draft | Restore to draft | publisher |

Publishing runs the validation ruleset over the would-be state and blocks
with that entity's errors listed (the publish gate; disable only with
`SARDINE_ADMIN_PUBLISH_GATE=0`). Only `published` content reaches builds.

## Editing

- **Design preview** (ADR-0027): each article and page editor frames the
  entry rendered by the real builder and the real theme (from
  `/preview/`). Valid source edits autosave after a short debounce and
  refresh a scoped entry artifact — drafts included, with no whole-site
  build. Invalid intermediate values stay in the form and pause autosave.
  Autosaves do not consume the newest-20 revision history; the explicit
  **Save** remains the revision point. Only `/preview/` allows same-origin
  framing; the admin itself can never be framed.
- **Articles**: EN source with metadata (per-language slug, category, tags,
  cover, editorial byline, Featured flag — featured articles lead the home
  highlight — and free-form custom fields carried to themes and
  extensions, ADR-0028), a Markdown editor (EasyMDE, vendored — ADR-0023) with a
  localized formatting toolbar, a preview rendered by the builder's own
  Markdown renderer (raw HTML disabled — the single source of truth for
  what publishes), and a side-by-side editor per translation. Editing the
  source marks its translations `outdated` automatically — states derive
  from content checksums, never from flags.
- **Pages**: metadata plus ordered typed sections; each section is a
  free-form field map the theme interprets, translated side by side. The
  editor suggests the fields each bundled kind consumes (the gallery in
  THEME_GUIDE.md) and merges kinds advertised by activated extensions
  (ADR-0028) — suggestions only, never validation.
- **Media**: the library filters server-side — text search over id,
  path, type and alt texts, plus quick views (images only, missing
  translated alt). Uploads validated server-side — the MIME type is sniffed from
  raster bytes (png, jpeg, gif, webp), dimensions parsed, byte and pixel
  limits enforced. Active SVG is rejected and an existing filesystem path is
  never replaced.
  EN alt text is mandatory; alt is translatable per language. Assets
  referenced by covers or sections refuse deletion.

## Publishing panel

`/publishing` shows the project (`sardine.toml`), the full validation
report, and two actions: **Preview build** (any role) into a temporary
directory served under `/preview/`, and **Build & export** (publisher and
up) which validates first, then writes the project's output directory with
the chosen target's extras (`generic`, `swa`, `nginx`). Every run is
recorded and shown on the panel and the dashboard.

## Backup, restore and foreign import

The database is disposable infrastructure; the portable pair is the source
of truth. Dump and restore it with:

```bash
cms dump -p . --out portable
cms import portable -p .
```

Importing into storage that already contains content is blocked unless
`--replace` is supplied; replacement is an upsert, not an implicit purge.

An existing blog can enter through a supported external export adapter. List
the available format selectors with:

```bash
cms import --help
```

The WXR 1.2 adapter reads the local file only, rejects DTD/entity declarations and
converts posts and common HTML structure to Sardine articles and Markdown.
It preserves status, dates, author, first category and tags. Pages,
attachments, menu items and comments are reported as skipped because their
mapping needs project-specific page-section and media decisions. Remote
image references are retained but never downloaded.

The validation report (shared with the dashboard) always shows the whole
story, not only failures: a gate callout (open/blocked) with the scope that
was validated (articles, pages, media assets, languages), one row per rule
with its outcome — every rule is listed even when it passes — and the issue
list with each subject linked to its edit screen. The five default rules:

| Rule | Checks that |
| --- | --- |
| `required-translations` | Review/published content carries every required language; incomplete translations warn in review and block once published |
| `unique-slugs` | Generated URLs never collide within a language |
| `media-references` | Sections only reference media assets that exist |
| `media-alt-coverage` | Every media asset has alt text in each required language |
| `known-categories` | Articles only use declared categories (skipped when none are declared) |

The seeded example project intentionally keeps one article in review with a
missing DE translation, so a fresh project (and the public demo) shows the
gate holding a real warning instead of an empty all-green report.

## Menu

The **Menu** screen defines explicit navigation: items with per-language
labels (source language as fallback), a numeric position and an internal
or external URL. Defined items replace the automatic menu on the next
build; re-adding an id updates it (that is also how items reorder), and
an empty list keeps the automatic menu. Writes need the publisher role.

## Editorial notes and quick actions

Each editor carries an **Editorial notes** card — a comment trail for
the team (author and moment shown; the author or an admin removes).
Notes are collaboration, not content: never published, never exported,
gone with the entity. The content lists offer a per-row **actions
dropdown** with the workflow transitions your role allows plus Move to
trash — no editor round-trip for routine moves.

## Duplicating and previewing an entry

**Duplicate as draft** copies an article or page — content, metadata,
translations and sections intact — under a fresh collision-safe id
(`-copy`, `-copy-2`, …), with the workflow reset to draft and no
schedule or trash flag. **View in preview** on each editor jumps
straight to that entry's URL inside `/preview/` (run a preview build
from the Publishing panel first).

## Trash

Deletion is reversible (ADR-0026): **Move to trash** on any article or
page hides it from every build, validation run, export and list — it
lives only in the **Trash** page, from where any role can **Restore** it
exactly as it was. **Delete forever** (admin role only) is the panel's
single permanent removal, and only works from the trash. Trashing and
restoring are recorded as revisions; nothing expires automatically.

## Revisions

Every article or page save from the panel keeps a snapshot (ADR-0025):
the **Revisions** card on each editor lists the newest 20 with moment and
author; each revision opens a detail page showing a unified diff of the
source text against the current content, with **Restore**. Restoring
validates the snapshot back through the model and saves — which records a
new revision, so a restore is always undoable. Revisions are editorial
history, not backup: they are never exported and are removed with the
entity.

## Scheduled publishing

Articles and pages carry an optional **Publish at (UTC)** moment
(ADR-0024). Scheduling composes with the workflow: an entry is live when
it is `published` **and** its moment has passed — a future `publish_at`
keeps it out of every build (pages, listings, feeds, sitemap, search)
until a build runs after that moment. **The build is the clock**: on a
static host nothing changes until something builds, so schedule builds at
the cadence the editorial calendar needs, e.g. a scheduled CI job:

```yaml
on:
  schedule:
    - cron: "0 * * * *"   # hourly: scheduled content goes live within the hour
jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install sardine-cms-cli sardine-cms-theme-ph7x-reference
      - run: cms export -p . --target swa
      # deploy the output directory with your host's action
```

Validation and the publish gate apply to scheduled content exactly as to
anything published — scheduling never bypasses them.

## Users

Admins manage accounts at **Users**: create (username, password ≥ 12
characters, role, panel language), change roles inline, delete. Two
safeguards are enforced server-side: you cannot delete your own account,
and the last admin can neither be deleted nor demoted. The first account
still comes from `cms admin create-user` — there are never default
credentials.

## Panel language (i18n)

The panel speaks the editor's language (ADR-0022). Resolution order per
request: the signed-in user's stored preference (the **Language** selector
in the navbar user menu) → the browser's `Accept-Language` → English.
`cms admin create-user --language pt-pt` seeds the preference. Catalogs
are gettext `.po` files under `cms_admin/locale/` (EN msgids; PT-PT, ES,
FR and DE shipped), compiled in memory at startup — no binary files, no
build step. Adding a language = one new `.po` plus one entry in
`cms_admin.i18n.LOCALES`; an anti-drift test fails if any msgid is
missing or untranslated in any shipped catalog. Editorial content is
never touched by panel i18n.

## Security model

- Argon2id password hashes; server-side sessions storing only the token
  digest; cookies `HttpOnly` + `Secure` + `SameSite=Strict`.
- Synchronizer CSRF tokens on every authenticated state-changing request,
  plus a double-submit token on the login form; failed-login rate limiting is
  keyed by both client and account. Password verification has bounded
  concurrency and unknown accounts receive equivalent Argon2 work. For more
  than one admin process, also rate-limit `/login` at the shared ingress.
- Security headers on every response, including a Content-Security-Policy
  allowing only same-origin scripts — the vendored AdminLTE behaviors, no
  inline scripts, no CDN (ADR-0020) — and frame denial.
- Accounts live in the storage database via the shared migrations and are
  **never exported**.
- The axe accessibility gate (WCAG 2.2 AA) runs over the admin pages in CI,
  the same methodology as the public site.

## The demo snapshot

`python -m cms_admin.demo_export` captures the real admin as inert static
HTML for the public demo (`/admin/` on the demo site): links prefixed, CSRF
stripped, forms neutralized, a read-only banner injected. Nothing a visitor
does can save anything — there is no server behind it.
