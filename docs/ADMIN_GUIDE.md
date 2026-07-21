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
| `SARDINE_ADMIN_REQUIRE_2FA` | unset | Minimum role at/above which two-factor is mandatory (`editor`\|`reviewer`\|`publisher`\|`admin`); unset keeps it optional |
| `SARDINE_WEBHOOK_URL` | unset | ADR-0036 on-publish webhook receiver (HTTPS; plain HTTP only for loopback) |
| `SARDINE_WEBHOOK_SECRET` | unset | Shared secret signing every webhook body; required with the URL |

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
wrong passwords. Disabling requires a valid code. With `SARDINE_ADMIN_REQUIRE_2FA` set, covered accounts without
two-factor sign in but are corralled to the enrolment page until they
confirm a code, and disabling is refused while the policy applies.
There are no backup
codes in this phase: the recovery path is
`cms admin create-user --force`, which replaces the account, clears
two-factor state and revokes every session. Password reset by email
deliberately does not clear the second factor.

### On-publish webhooks (ADR-0036)

With the URL and secret set, transitions that change the public site —
into `published` and out of it — POST a minimal signed JSON doorbell
(`{"event", "entity": {"kind", "id"}, "occurred_at"}`) to the receiver.
Verify `X-Sardine-Signature` (`sha256=<hex>`, HMAC-SHA256 of the exact
body with the shared secret), answer 2xx quickly and rebuild
asynchronously. Delivery retries three times with backoff off the
request path; after that the failure is recorded and the event is
dropped — the scheduled-build recipe remains the safety net.

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
- **Page building (#127)**: sections add from a visual **block
  gallery** — one card per kind (bundled and extension-contributed)
  with a description; keys derive from the kind automatically (a
  custom-kind form stays behind "advanced"). Rows **duplicate**
  (content, translations and visibility copied), **hide/show** (hidden
  sections keep everything but leave every build and never block
  translation parity), **delete with undo** (the flash restores the
  section, translations included), and reorder by **drag-and-drop** —
  a progressive enhancement; the up/down buttons remain the keyboard
  and no-JS path. Sections whose kind the theme does not implement are
  badged as rendering generically.
- **Pages**: metadata, an optional long-form Markdown body (rendered
  between the header and the sections — a page can be a document, a
  zone composition, or both), plus ordered typed sections translated
  side by side. A section editor has three parts (ADR-0037): the flat
  name/value fields the theme interprets (suggestions from the kind's
  spec — the gallery in THEME_GUIDE.md — merged with kinds advertised
  by activated extensions, ADR-0028; suggestions only, never
  validation), the kind's declared **Markdown fields** with the same
  editor widget as article bodies, and the unbounded **items table**
  (one column per item column; blank trailing rows add an item, fully
  clearing a row removes it). The translation editor mirrors all three
  with the source read-only beside each input.
- **Media**: the library filters server-side — text search over id,
  path, type and alt texts, plus quick views (images only, missing
  translated alt). Uploads validated server-side — the MIME type is sniffed from
  raster bytes (png, jpeg, gif, webp), dimensions parsed, byte and pixel
  limits enforced. Active SVG is rejected and an existing filesystem path is
  never replaced.
  Alt text in at least one language is mandatory (the source's, in
  practice — validation checks the configured source); alt is
  translatable per language. Assets
  referenced by covers or sections refuse deletion.
- **Collections**: an optional lowercase-with-dashes folder name set at
  upload or edited later on the asset page; the library filter narrows
  to one collection, and collection names in the list link to their
  filtered view. Every asset also shows how many entries use it — a
  count in the list, the full reference list on the asset page.
- **Duplicate prevention**: each upload records the file's SHA-256;
  uploading bytes identical to an existing asset is refused with a
  message naming the asset that already holds them.
- **Picking images in the editors**: the article metadata card and the
  section editor offer a library picker — thumbnails with dimensions,
  chosen by radio (cover: pick, keep, or none) or checkbox (section
  media: append to the ordered list). No script is required; the ID
  text inputs remain the precise path. Images narrower than the widest
  configured responsive width are flagged so editors see when a source
  is too small for the site's layouts.
- **Replace file**: the asset page swaps the file behind an asset
  while the ID — and therefore every reference from covers and
  sections — stays valid. Alt texts, collection and focal point carry
  over; a crop that no longer fits the new image is cleared; the old
  file leaves the disk when the format changes. Bytes identical to
  another asset are refused, naming it.
- **Crop and focal point**: on an image's asset page, an optional crop
  (`x,y,width,height` in pixels of the original) and focal point
  (`x,y` fractions, 0–1). The crop is stored as data and applied when
  the site is built — the published image, its dimensions and every
  responsive derivative descend from the cropped area, while the
  uploaded original stays untouched; clearing the crop restores the
  full image on the next publish. The focal point travels with the
  image's metadata (themes and the Content API receive it) so the
  important part stays in view wherever the image is trimmed to fit.

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

## First-run setup (#128)

An instance with no accounts sets itself up in the browser: every
request lands on `/setup` — one page, three sections. **Your account**
creates the first admin (always the `admin` role; the instance can
never be left without one). **Your site** writes `sardine.toml` when
the project has none — name, address, main language and optional
target languages chosen from the registered language packs, theme; an
existing project file is never rewritten and its settings show as
kept. **Example content** optionally seeds the demo site. Submitting
signs the new admin straight in; a fresh site's dashboard opens with a
first-steps checklist (create a page → preview → publish). The wizard
disappears permanently the moment any account exists. `cms admin
create-user` remains the scripted path.

## Publishing and deployment (#128)

The Publishing panel's build form asks one plain question — *where
will the site live?* — with a card per deployment target (any static
host, Azure Static Web Apps, your own nginx server), each explaining
what the build includes. The choice is remembered in `sardine.toml`
(`[build] target`), and `cms export` without `--target` uses it too. A
successful build answers *what now*: where the files are and the one
action that puts them live for the chosen target.

## Forms

A page section of kind **form** turns into a working visitor form.
Editors declare the inputs as the section's items (`key`, `type` —
`text`, `email`, `textarea`, `checkbox` — `label`, `required`) and the
form's texts as its fields; every visitor-facing word is editorial
content, translated like any other section.

Configuration in `sardine.toml`:

```toml
[forms]
endpoint = "https://panel.example.com/forms/submit"  # where forms submit
notify = "owner@example.com"                          # notification address
store = true                                          # optional: keep submissions
retention_days = 90                                   # optional: prune at startup
```

The published form submits to the panel's endpoint, which validates
server-side against the declared inputs (the HTML's hints are a
convenience, never the source of truth), applies layered spam
protection (honeypot, elapsed-time check when present, per-address
rate limiting, origin allowlist against the site's `base_url`) and
answers with a localized, accessible page — success shows the
section's own success texts. With `notify` set and the panel's mail
transport configured, each submission is delivered as a plain-text
message; a delivery failure is recorded in the Activity trail and
never shown to the visitor as an error. Without `endpoint`, published
pages render the form's content but no form.

With `store = true`, accepted submissions also persist — storage is a
consumer of the accepted submission, decoupled from the mail leg: a
storage failure is audited and never affects the visitor's answer or
the notification, and the endpoint works identically with storage off.
The admin-only **Submissions** screen lists them newest first,
filtered by form (`page/section`) and date window; the visitor's
values display as an opaque payload; deletion is definitive; and
`retention_days` prunes older submissions at panel startup (0 keeps
everything until deleted).

With `[deploy]` configured (DEPLOYMENT.md), the flow goes further —
**editorial actions end on the public site**: publishing or
unpublishing content rebuilds, validates, writes an immutable release,
activates it atomically and health-checks it, automatically; the
Public site card shows the state (active / failed / rolled back), the
actionable error and its phase, a Publish/Retry button, and the kept
releases with one-click rollback that needs no rebuild. A failure
never touches the healthy version. Without `[deploy]`:
"Publish" here means: validate, build deterministically, apply the
destination's extras and write the output directory — the public site
itself is served by external infrastructure (DEPLOYMENT.md documents
every model). The **Last run** card is the publication's state: kind,
time, file count, digest, and the failure detail when something
refused — validation errors block the build before anything is
written, so a failed publish never leaves a half-updated output. The
editorial flow ends here and starts again here: further changes
republish to the same destination
([#156](https://github.com/ph7x-Systems/sardine-cms/issues/156) brings
the transport leg, status, failure preservation and rollback fully
into the panel).

## Needs attention (#135)

The dashboard opens with work, not totals: entries in review (with
"waiting for your decision" for roles that can publish), translation
pairs pending in the configured languages, scheduled changes firing in
the next 7 days (publish and unpublish windows both), and drafts
untouched for 30 days. Every card links to where the work gets done;
when nothing waits, the panel says so plainly.

## Activity (#134)

**Activity** (admin role only) is the audit trail, readable: who did
what, when — sign-ins (successes and failures), workflow transitions,
trash/restore/purge, media uploads and deletions, user and role
changes, two-factor changes, reschedules and site builds. Filter by
actor and date window; newest first, 100 at a time. Records are
append-only, survive the deletion of what they describe, and never
block the action they record. Retention:
`SARDINE_ACTIVITY_RETENTION_DAYS` (default 365; `0` keeps everything),
pruned at startup.

## Scheduled unpublish (#133)

Entries carry an optional **Unpublish at (UTC)** next to the publish
moment: after it passes, the next build drops the entry — the
symmetric end of ADR-0024's window, from the same deterministic clock.
A window that ends before it starts is refused at the model. Campaign
pages and legal notices get an end date without anyone remembering to
unpublish them.

## Calendar (#132)

**Calendar** shows the month as the panel sees time: published entries
on their publication day, scheduled entries on the day their
`publish_at` will fire — in UTC, exactly as the panel schedules
(ADR-0024; the screen says so). Scheduled chips drag to another day
(keeping their time of day; the server refuses to move published
history), and every chip links to its editor, where the date field
remains the precise no-JS path.

## Translations (#131)

**Translations** in the sidebar is the translator's worklist: every
entry-language pair that is missing or outdated for the project's
configured language set (pack tags included), filterable by language,
state and content type, each row linking straight to the side-by-side
editor. Zero rows is a real statement — everything is caught up.
States come from the model's checksums, so the queue can never
disagree with the editors. The content lists carry the same power as a
filter: "missing «tag»" keeps only entries whose state for that
language is not complete.

## Bulk actions (#130)

The content lists select with checkboxes (plain forms — no JavaScript
required) and apply one action to everything selected: workflow
transitions, move to trash, and — for articles — category assignment;
the media list bulk-deletes unreferenced assets. Nothing is looser in
bulk: every entry passes the exact single-action checks (transition
validity from its own status, the actor's role, the publish gate with
the project's language set, reference protection for media), and the
result page reports every outcome per entry — refusals with their
reason, and one failure never aborts the rest.

## Search (#129)

The navbar carries a search box on every screen; `/search` finds
anything an editor can edit — articles, pages, sections and media — by
title, text, slug, section fields (items included) and media alt text,
**in every language**. Results come grouped by kind, each hit linking
straight to its editor. Trashed entries never appear. The query runs
at the storage layer (ADR-0038): measured worst case 13.6 ms on SQLite
and 34.5 ms on PostgreSQL at 10 000 entries (`scripts/search_bench.py`
reproduces the measurement).

## Panel language (i18n)

The panel speaks the editor's language (ADR-0022 + ADR-0034).
Resolution order per request: the signed-in user's stored preference
(the **Language** selector in the navbar user menu) → the browser's
`Accept-Language` → English. `cms admin create-user --language pt-pt`
seeds the preference. Catalogs are gettext `.po` text carried by
language packs (`LanguagePack.admin_catalog`; EN msgids are the source
text and need no catalog), compiled in memory at startup — no binary
files, no build step. The bundled four ship inside cms-core's packs;
an extension pack that carries a catalog makes its language a panel
language the moment the pack is activated — the selector lists every
registered pack with a catalog under the pack's own `native_name`, and
the panel chrome renders `dir="rtl"` when the pack says so. An
anti-drift test fails if any msgid is missing or untranslated in any
bundled catalog. The editors' source and target language sets come
from the project's `sardine.toml` (`source_language`, `languages`).
Editorial content is never touched by panel i18n.

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
