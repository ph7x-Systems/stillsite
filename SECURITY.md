# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 0.7.x | Yes — fixes land here |
| < 0.7 | No — upgrade; releases are lockstep and migrations are additive |

The six packages release together; a security fix produces a new
lockstep release rather than patches to older lines.

## Reporting a vulnerability

Use **GitHub private vulnerability reporting**: *Security → Report a
vulnerability* on this repository. Do not open public issues or pull
requests containing exploitation details.

What to expect:

- **Acknowledgement within 72 hours**, triage within 7 days.
- Coordinated disclosure: we agree a timeline with you, land the fix,
  release it, and only then publish an advisory describing impact
  without an exploitation recipe. Reporter credit is offered, never
  required.
- A credential that ever appears in a commit is treated as compromised:
  rotation first, history cleanup second.

## Scope

In scope: the six published packages, the admin panel, the build and
export pipeline, the migration flow, and the workflows in this
repository.

Out of scope:

- Vulnerabilities in third-party themes, extensions or providers not
  maintained in this repository (report to their maintainers; we will
  help coordinate if the contract itself enables the issue).
- The demo site's content and availability.
- Deployment misconfiguration in user infrastructure (for example a
  panel exposed without TLS despite the documented requirement).
- Denial of service through volume alone against self-hosted panels.

## Standing principles

- **Secrets via environment only** — never in `sardine.toml`, the
  database, audit records, logs, exports or build artifacts.
- **No default credentials** anywhere; first accounts come from the
  CLI.
- **Static public frontend** — the published site has no runtime
  backend surface.
- **Nothing activates by installation** — themes and extensions are
  listed without executing their code and run only after explicit
  activation.
- **CI gates**: secret scanning over full history, dependency audit,
  static analysis, CodeQL, and a commit-hygiene check on every PR.

## Engineering strategy

The full plan — threat model per component, controls in force and the
architecture security model — lives in
[docs/SECURITY_STRATEGY.md](docs/SECURITY_STRATEGY.md).
