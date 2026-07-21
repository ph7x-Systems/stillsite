# Deployment and Operations

Sardine is where the site is **managed**; the public site is **served**
elsewhere. This page documents that operational model and every
supported way of getting a build onto public infrastructure.

## The model

```text
┌─────────────┐   ┌───────────────────┐   ┌───────────┐   ┌────────────────────┐   ┌────────────────┐
│ Admin panel │──▶│ Editorial storage │──▶│   Build   │──▶│ Deployment target/ │──▶│ Public hosting │
│  (editors)  │   │ (SQLite/PG/MySQL/ │   │ (determi- │   │ provider (extras + │   │ (SWA, Nginx,   │
│             │   │  MSSQL — working  │   │  nistic)  │   │ transport)         │   │  S3, Pages, …) │
└─────────────┘   │  store, not SOT)  │   └───────────┘   └────────────────────┘   └────────────────┘
```

- Editors create, edit and manage content in the **panel**. The panel
  never needs to serve the public site — it can live on a laptop, an
  internal server or a private network.
- The **build** turns the editorial state into a deterministic static
  artifact (same content + same clock → same bytes).
- A **deployment target** shapes the artifact for its host (extra
  files: `staticwebapp.config.json`, an nginx server block, …) and —
  as [#156](https://github.com/ph7x-Systems/sardine-cms/issues/156)
  lands — transports it there from the panel.
- **Public hosting** serves the result: Azure Static Web Apps, your
  own Nginx, S3/CloudFront, GitHub Pages, Netlify, or any static host.

Publication is a **cycle, not an export**: further changes are made in
Sardine and republished to the same destination. The database is a
working store; the portable JSON/Markdown export remains the source of
truth for content itself.

## Supported operating models

### 1. Local directory served by Nginx

The panel and Nginx share a machine (or a volume). Build & export with
the `nginx` target writes the site plus a ready server block into the
project's output directory:

```nginx
# /etc/nginx/conf.d/site.conf — include the generated block
include /srv/site/_site/nginx.conf;
```

Point the generated block's root at the output directory and reload.
Republishing overwrites the output atomically per file; for strict
atomicity, publish to a versioned directory and switch a symlink (the
pattern #152 automates):

```sh
cms export -p /srv/site --target nginx
ln -sfn /srv/site/_site /srv/site/current   # nginx root: /srv/site/current
nginx -s reload
```

### 2. Upload / sync to static hosting

Build with the matching target, then sync the output directory with
the host's own tool (`swa deploy`, `aws s3 sync`, `netlify deploy`,
`gh-pages`). The artifact is self-contained — sync means copying the
directory.

### 3. Remote provider from the panel

The Publishing panel's Build & export runs validation, builds, applies
the chosen target's extras and writes the output directory, recording
the outcome (time, file count, digest, target). Transport to the
remote host is today the step your pipeline or tooling performs; #152
brings it into the panel with status, failure preservation and
rollback.

### 4. CI/CD pipeline (the live demo's own pattern)

The reference implementation deploys <https://sardine.ph7x.com> on
every merge and is honest about privilege separation:

1. A build job with **no deployment secret** installs the packages,
   seeds/loads storage, validates and exports the SWA artifact.
2. The artifact is uploaded with short retention.
3. A separate job in a **protected environment** downloads the
   finished artifact and deploys it — no project code runs where the
   Azure token lives.

The same pattern works with real content: point the workflow at your
storage URL instead of seeding.

## Azure Static Web Apps example

The `swa` target emits `staticwebapp.config.json` with security
headers, cache rules and the 404 rewrite — Free and Standard tiers
take the same artifact.

```sh
cms export -p . --target swa
npx @azure/static-web-apps-cli deploy ./_site --deployment-token "$SWA_TOKEN"
```

In CI, keep the token in a protected environment and deploy the
prebuilt artifact only (see model 4).

## Rollback, credentials, permissions, partial failure

- **Rollback today**: static artifacts are cheap — keep the previous
  output directory (or rely on the host's deployment history: SWA and
  Netlify retain previous deployments; for Nginx use the versioned
  directory + symlink pattern above). Content itself is versioned by
  revisions in the panel and by the portable export in your VCS.
- **Credentials** belong to the transport layer: CI secrets or the
  host's own CLI login. Nothing in the artifact or the panel contains
  credentials, and Build & export runs without any.
- **Permissions**: Build & export requires the publisher role and
  validation passing; preview requires any role (ADR-0027).
- **Partial failure**: a build either completes or records a failure —
  the output directory is written only from a finished artifact. For
  the network leg, prefer transports that activate atomically (SWA,
  Netlify) or the symlink pattern; #156's contract makes
  keep-previous-on-failure and rollback panel-level guarantees.

## The deployment provider contract

Today's contract (`cms_build.targets`, ADR-0005) covers **generation**:

```python
class Target(Protocol):
    name: str
    def extra_files(self, config: SiteConfig, artifact: Artifact) -> Mapping[str, bytes]: ...
```

Extensions register new destinations with `register_target(name,
factory)` (ADR-0028) — no core changes; `sardine-target-<name>` is the
ecosystem naming (ECOSYSTEM.md).

The full provider model separates five phases — the vocabulary #152's
implementation follows, so a provider for any host slots in without
touching the core:

| Phase | Meaning | Status |
| --- | --- | --- |
| Generation | build + target extras | ✅ shipped (`extra_files`) |
| Transport | move the artifact to the host | 🔜 #156 (today: your pipeline/CLI) |
| Activation | the new version goes live atomically | 🔜 #156 (host-native or symlink) |
| Health check | the destination serves the new version | 🔜 #156 |
| Rollback | return to the last valid version | 🔜 #156 |
