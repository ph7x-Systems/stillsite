# Writing a Deployment Provider

This is the developer guide for adding a new deployment destination to
Sardine. A provider is one factory implementing one contract — the CMS
core, the editor and the publish flow never change.

For the operator's view (configuration, operating models,
troubleshooting), see the [Deployment Guide](DEPLOYMENT.md).

## The contract

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

`contract_version` is validated at selection time — a mismatch refuses
loudly before anything runs, never mid-deployment. `capabilities`
drives the panel: rollback controls render only when the provider
declares `"rollback"`.

Two contracts cooperate: the deployment contract above (transport and
activation) and the generation contract (`Target.extra_files`, which
shapes the artifact for a host). A destination often needs both — a
target for host-specific files, a provider for delivery. See the
architecture documentation for the generation side.

## Registration

Providers register by name. The bundled ones (`filesystem`, `swa`) use
the same mechanism as yours:

```python
from cms_build.deploy import register_deploy_provider

register_deploy_provider("mine", my_factory)
```

An extension ships this without any core change: put the factory in
`Extension.deploy_providers` and activation registers it. The factory
signature is `(settings: dict[str, str], project_dir: Path) ->
DeployProvider`, where `settings` is the raw `[deploy]` table — your
provider reads its own keys.

## A complete example

An rsync-style provider that composes the bundled filesystem store —
which provides immutable releases, locking and rollback for free — and
adds one step: syncing the activated release to a remote destination.

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

## Rules a provider must keep

- The factory must read its own keys from the raw `[deploy]` table and
  raise `DeployError` with an actionable message when one is missing.
- A failed deployment must never touch the previously published
  version; `state()` must report it with `status="failed"` and a real
  `error`.
- Kept releases must survive process restarts; `rollback` must
  re-activate one without rebuilding.
- Concurrent deployments must be refused (`DeployLocked`); composing
  `FilesystemDeployer` as the local store provides this.
- Credentials must come from the environment at deploy time — never
  from configuration, and never into logs, state, errors or the audit
  trail.

The repository ships a conformance suite
(`tests/test_deploy_conformance.py`) that runs these rules against
every provider, including an extension-registered one — run it against
yours while developing.

## The local store layout

Providers that compose `FilesystemDeployer` inherit this layout under
`root`:

```text
releases/<timestamp>-<digest>/site/   immutable release artifacts
releases/<timestamp>-<digest>/release.json
current -> releases/<id>/site         atomic symlink (rename swap)
state.json                            the panel's deployment state
.deploy.lock                          concurrency lock (expires after 10 minutes)
```

`write_release()` is shared by every provider — it writes an immutable
release and refuses incomplete payloads, which is what makes
rollback-without-rebuild possible on any destination.

Ecosystem naming for published providers: `sardine-deploy-<name>`
(see [ECOSYSTEM.md](ECOSYSTEM.md)).
