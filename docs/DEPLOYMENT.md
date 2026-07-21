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

### 1. Local directory served by Nginx — automated (#156)

With one table in `sardine.toml`, editorial actions end on the public
site — publish and unpublish redeploy automatically, and nobody runs a
deploy by hand:

```toml
[deploy]
root = "/srv/site/www"        # required — where releases live
health_url = ""               # optional — checked after activation
keep = 5                      # kept releases (rollback candidates)
```

The layout under `root`:

```text
releases/<timestamp>-<digest>/site/   immutable release artifacts
releases/<timestamp>-<digest>/release.json
current -> releases/<id>/site         atomic symlink (rename swap)
state.json                            the panel's deployment state
```

Point Nginx at `current/` once; it is never reconfigured or restarted
by a publication:

```nginx
server {
    root /srv/site/www/current;
    # include the security headers from `cms export --target nginx`
}
```

**Filesystem permissions**: the panel process needs write access to
`root`; Nginx needs read access to `root` (the symlink target changes,
the path does not). **Health check**: after activation the provider
verifies the release marker; with `health_url` set it also fetches the
URL and rolls back automatically on failure — the previous release is
always kept. **Rollback**: the panel lists kept releases; reactivating
one is a symlink swap, no rebuild. **Scheduled changes**: a watcher
redeploys as `system` when a publication window boundary passes.
**Troubleshooting**: the panel's Public site card shows the failing
phase and an actionable error; `state.json` holds the same truth for
operators; a stale `.deploy.lock` (crashed process) expires after 10
minutes. Every operation lands in the admin's Activity trail.

### 1b. Manual local directory


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

## Azure Static Web Apps — automated (#156)

The same contract and the same panel experience as the filesystem
provider — the editor never knows which provider runs:

```toml
[deploy]
provider = "swa"
root = "/srv/site/store"      # local release store: state + rollback candidates
deploy_url = "https://…"      # the deployment endpoint for your app
health_url = "https://your-site.example/"
timeout = 300                 # seconds for upload + deployment tracking
```

**Credentials**: the deployment token is read from the
`SARDINE_SWA_DEPLOY_TOKEN` environment variable at deploy time. It is
never stored in configuration, never written to logs or the audit
trail, never returned by any page, and never part of an error
message — it travels in one request header. Rotate it by replacing
the environment variable.

**Flow**: publish/unpublish → build → validate → immutable local
release → upload (Bearer token) → deployment tracking → health check →
active. The panel shows the transient phases (queued, uploading,
waiting, verifying) and the terminal state; **a failure at any phase
leaves the previously published version serving** — the host keeps its
last successful deployment until a new one succeeds. Rollback re-sends
a kept release from the local store, no rebuild.

**Troubleshooting**: "deployment token rejected" — the token is wrong
or expired; replace the environment variable and Retry. "timed out
waiting for the deployment" — raise `timeout` or check the host's
status page. "health check failed — the previous publication remains
live" — the deployment reported success but the site did not answer;
check `health_url` and the host. Every operation is in the Activity
trail (never with credentials).

## Azure Static Web Apps — manual example

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

Two contracts cooperate, both extension-registerable with no core
changes (ADR-0028):

- **Generation** (`cms_build.targets`, ADR-0005): `Target.extra_files`
  adds host-specific files to the artifact; `register_target(name,
  factory)`.
- **Deployment** (`cms_build.deploy`, #156): a `DeployProvider` moves a
  built release to its destination and reports one truthful state.

```python
class DeployProvider(Protocol):
    contract_version: int              # must equal DEPLOY_CONTRACT_VERSION
    capabilities: frozenset[str]       # of {"rollback", "health", "remote"}

    def deploy(self, files: dict[str, bytes], digest: str, actor: str) -> DeployState: ...
    def record_failure(self, error: str, phase: str, actor: str) -> DeployState: ...
    def rollback(self, release_id: str, actor: str) -> DeployState: ...
    def state(self) -> DeployState: ...
    def releases(self) -> list[ReleaseInfo]: ...
```

Providers resolve through a registry: `[deploy] provider = "<name>"`
selects one, `create_deploy_provider(name, settings, project_dir)`
builds it, validating the contract version and the interface **at
selection time** — a misconfigured provider refuses loudly before
anything runs. The bundled providers are `filesystem` and `swa`; the
panel adapts to `capabilities` (for example, rollback controls appear
only when the provider declares `"rollback"`).

## Writing a deployment provider

A new destination (S3, SSH/rsync, any static host) is one factory —
the CMS core, the editor and the publish flow never change:

```python
from cms_build.deploy import DEPLOY_CONTRACT_VERSION, DeployError, FilesystemDeployer
from cms_core.extensions import Extension

class RsyncDeployer:
    contract_version = DEPLOY_CONTRACT_VERSION
    capabilities = frozenset({"rollback", "remote"})

    def __init__(self, root, destination):
        self._store = FilesystemDeployer(root)   # immutable releases,
        self._destination = destination          # locking and rollback for free
    # deploy() / rollback() delegate to the store, then sync the
    # activated release to the destination; state()/releases()/
    # record_failure() delegate directly.

def factory(settings: dict[str, str], project_dir):
    if not settings.get("destination"):
        raise DeployError("the rsync provider needs [deploy] destination")
    return RsyncDeployer(project_dir / settings["root"], settings["destination"])

extension = Extension(name="rsync-deploy", deploy_providers={"rsync": factory})
```

The project activates it like any extension and selects it:

```toml
extensions = ["sardine_deploy_rsync:extension"]

[deploy]
provider = "rsync"
root = "deploy"                 # the local release store
destination = "user@host:/srv/site"
```

Rules a provider must keep (`tests/test_deploy_conformance.py` runs
them against every provider, including a fictional extension-registered
one — run it against yours):

- The factory reads its own keys from the raw `[deploy]` table and
  raises `DeployError` with an actionable message when one is missing.
- A failed deployment never touches the previously published version;
  `state()` reports it with `status="failed"` and a real `error`.
- Kept releases survive process restarts; `rollback` re-activates one
  without rebuilding.
- Concurrent deployments are refused (`DeployLocked`); composing
  `FilesystemDeployer` as the local store provides this.
- Credentials come from the environment at deploy time — never from
  configuration, and never into logs, state, errors or the audit trail.

Ecosystem naming: `sardine-deploy-<name>` (ECOSYSTEM.md).
