# Deployment Guide

Sardine is where the site is **managed**; the public site is **served**
elsewhere. This guide is for the person who operates a Sardine site:
how publishing works, the supported operating models, configuration,
and what to do when something fails.

Related documentation:

- [Deployment providers](DEPLOYMENT_PROVIDERS.md) — what providers
  exist and what they can do.
- [Writing a deployment provider](WRITING_A_DEPLOYMENT_PROVIDER.md) —
  the developer guide for adding a new destination.

## The model

```text
┌─────────────┐   ┌───────────────────┐   ┌───────────┐   ┌────────────────────┐   ┌────────────────┐
│ Admin panel │──▶│ Editorial storage │──▶│   Build   │──▶│ Deployment target/ │──▶│ Public hosting │
│  (editors)  │   │ (SQLite/PG/MySQL/ │   │ (reprodu- │   │ provider (extras + │   │ (SWA, Nginx,   │
│             │   │  MSSQL — working  │   │  cible)   │   │ transport)         │   │  S3, Pages, …) │
└─────────────┘   │  store, not SOT)  │   └───────────┘   └────────────────────┘   └────────────────┘
```

- Editors create, edit and manage content in the **panel**. The panel
  never needs to serve the public site — it can live on a laptop, an
  internal server or a private network.
- The **build** turns the editorial state into a reproducible static
  site: the same content always produces the same files.
- A **deployment provider** moves the built site to its destination
  and activates it. A **deployment target** shapes the artifact for
  its host (extra files such as `staticwebapp.config.json` or an Nginx
  server block).
- **Public hosting** serves the result: Azure Static Web Apps, your
  own Nginx, S3/CloudFront, GitHub Pages, Netlify, or any static host.

Publication is a **cycle, not an export**: further changes are made in
Sardine and republished to the same destination. The database is a
working store; the portable JSON/Markdown export remains the source of
truth for content itself.

## The publish flow

Every publication — a button in the panel, a workflow transition, or a
scheduled window — runs the same flow:

```text
Editor action
     ↓
   Build
     ↓
 Validation      (failures stop here — the live site is untouched)
     ↓
  Provider       (immutable release, transported to the destination)
     ↓
 Activation      (atomic — the new version goes live in one step)
     ↓
Health check     (failures roll back — the previous version returns)
     ↓
 Public site
```

A failure at any step leaves the previously published version serving,
and the panel's Public site card reports what happened with a retry
action. Every operation lands in the admin's Activity trail.

## Supported operating models

### 1. Local directory served by Nginx — automated

With one table in `sardine.toml`, editorial actions end on the public
site — publish and unpublish redeploy automatically, and nobody runs a
deploy by hand. Point Nginx at the `current/` directory once; it is
never reconfigured or restarted by a publication. See the
[complete example](#example-filesystem--nginx) below.

### 2. Azure Static Web Apps — automated

The same panel experience with a remote destination: the release is
uploaded to the SWA deployment endpoint, tracked to completion and
health-checked. The deployment token lives only in an environment
variable. See the [complete example](#example-azure-static-web-apps)
below.

### 3. Manual export and sync

Build with the matching target (`cms export -p . --target swa|nginx|generic|astro`),
then copy the output directory with the host's own tool (`swa deploy`,
`aws s3 sync`, `netlify deploy`, `gh-pages`). The artifact is
self-contained — sync means copying the directory.

### 4. CI/CD pipeline (the live demo's own pattern)

The reference implementation deploys <https://sardine.ph7x.com> on
every merge and keeps privileges separated:

1. A build job with **no deployment secret** installs the packages,
   loads storage, validates and exports the artifact.
2. The artifact is uploaded with short retention.
3. A separate job in a **protected environment** downloads the
   finished artifact and deploys it — no project code runs where the
   deployment token lives.

The same pattern works with real content: point the workflow at your
storage URL instead of seeding.

## Configuration reference

All deployment configuration lives in the `[deploy]` table of
`sardine.toml`. The `provider` key selects who delivers the site;
every other key belongs to the selected provider.

### Filesystem (default)

| Key | Required | Meaning |
| --- | --- | --- |
| `root` | yes | Where releases live; the web server serves `<root>/current` |
| `health_url` | no | Fetched after activation; a failure rolls back automatically |
| `keep` | no (5) | How many releases to keep as rollback candidates |

### Azure Static Web Apps

| Key | Required | Meaning |
| --- | --- | --- |
| `provider` | yes | `"swa"` |
| `root` | yes | Local release store (deployment state and rollback candidates) |
| `deploy_url` | yes | The deployment endpoint for your app |
| `health_url` | no | Fetched after the deployment reports success |
| `timeout` | no (300) | Seconds allowed for upload and deployment tracking |

The deployment token is read from the `SARDINE_SWA_DEPLOY_TOKEN`
environment variable at deploy time. It is never stored in
configuration, never written to logs or the audit trail, never
returned by any page, and never part of an error message. Rotate it by
replacing the environment variable.

### Other providers

Extensions can add destinations; each documents its own keys. See
[Deployment providers](DEPLOYMENT_PROVIDERS.md).

## Example: filesystem + Nginx

`sardine.toml`:

```toml
[deploy]
root = "/srv/site/www"
health_url = "https://example.com/"
keep = 5
```

Nginx, configured once:

```nginx
server {
    root /srv/site/www/current;
    # include the security headers from `cms export --target nginx`
}
```

Permissions: the panel process writes to `root`; Nginx reads it (the
symlink target changes, the path does not).

**Publish**: publishing or unpublishing any entry redeploys the site;
the panel's Public site card also has a "Publish site now" button for
a forced fresh release.

**Rollback**: the Public site card lists kept releases; rolling back
reactivates one atomically, with no rebuild.

## Example: Azure Static Web Apps

`sardine.toml`:

```toml
[deploy]
provider = "swa"
root = "/srv/site/store"
deploy_url = "https://…"
health_url = "https://your-site.example/"
timeout = 300
```

Environment, where the panel runs:

```sh
export SARDINE_SWA_DEPLOY_TOKEN="…"   # from your SWA deployment settings
```

**Publish**: the same actions as the filesystem provider; the panel
shows the transient phases (queued, uploading, waiting, verifying) and
the terminal state.

**Retry**: after a failure, fix the cause (see below) and use the
panel's "Retry deployment" button — the previously published version
keeps serving until a new deployment succeeds.

## Rollback

Every automated provider keeps recent releases (`keep`). The panel
lists them; rolling back re-activates a kept release without
rebuilding — locally as a symlink swap, remotely by re-sending the
kept files. Content itself is versioned independently: revisions in
the panel, and the portable export in your VCS.

## Troubleshooting

| Problem | What it means | What to do |
| --- | --- | --- |
| "health check failed — the previous publication remains live" | The new version was delivered but the site did not answer at `health_url` | Check `health_url` and the host; the previous version keeps serving; fix and retry |
| "timed out waiting for the deployment" | The host did not finish within `timeout` | Raise `timeout` or check the host's status page; retry |
| "deployment token rejected" | The token is wrong or expired | Replace the `SARDINE_SWA_DEPLOY_TOKEN` environment variable and retry |
| "a deployment is already running" | Two deployments overlapped; they are serialized | Wait — the running deployment writes its own state; the panel refreshes |
| Stale lock after a crash | A crashed process left a lock behind | The lock expires by itself after 10 minutes; the next deploy proceeds |
| Permission denied under `root` | The panel process cannot write the release | Give the panel user write access to `root`; the web server only needs read |
| Disk full under `root` | Releases accumulate bytes | Lower `keep`; each release is a full copy of the site |
| Validation blocked the release | Content rules failed before anything was deployed | The panel's validation report lists every finding; the live site is untouched |

Every failure is also recorded in the panel's Public site card (with
the failing phase) and in the Activity trail — never with credentials.
