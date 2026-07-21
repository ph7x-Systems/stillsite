# Deployment Providers

A deployment provider is the component that moves a built site to its
destination and activates it. The editor and the publish flow never
know which provider runs — `[deploy] provider = "<name>"` in
`sardine.toml` selects one, and everything else stays the same:
immutable releases, atomic activation, health checks, rollback, one
truthful deployment state in the panel.

## Bundled providers

| Provider | Destination | Capabilities |
| --- | --- | --- |
| `filesystem` (default) | A local directory served by your web server (the Nginx pattern) | rollback, health |
| `swa` | Azure Static Web Apps, over its deployment endpoint | rollback, health, remote |

Configuration for both is in the
[Deployment Guide](DEPLOYMENT.md#configuration-reference).

## Capabilities

Every provider declares what it can do, and the panel adapts:

- **rollback** — kept releases can be re-activated without rebuilding;
  the panel shows rollback controls only when the provider declares it.
- **health** — the provider verifies the destination serves the new
  version after activation, and rolls back automatically on failure.
- **remote** — activation happens on a remote host over the network.

## Selection and validation

The configured provider is resolved when it is needed, and validated
before anything runs: an unknown name, an incompatible contract
version or an incomplete configuration refuses loudly with a message
naming the problem — never mid-deployment.

## Third-party providers

Extensions can register additional destinations (S3, SSH/rsync, GitHub
Pages, any static host). Installing one is activating the extension
and selecting its provider name in `[deploy]`; the ecosystem naming
for such packages is `sardine-deploy-<name>` (see
[ECOSYSTEM.md](ECOSYSTEM.md)).

To build one, see
[Writing a deployment provider](WRITING_A_DEPLOYMENT_PROVIDER.md).
