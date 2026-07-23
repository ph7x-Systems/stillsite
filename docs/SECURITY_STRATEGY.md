# Security Strategy — Sardine CMS

This document is the security plan for the framework: principles, threat
model, the controls that exist today, and the controls each milestone must
deliver. The public-facing policy (how to report vulnerabilities) lives in
[SECURITY.md](../SECURITY.md); this is the engineering side of it.

## 1. Principles

1. **Static-first is the first control.** The public site is static HTML/CSS/
   JS with no runtime backend, which removes injection, session and server
   attack surface from the published product. Everything dynamic is isolated
   in the admin panel, which can live on a private network.
2. **Secure by default.** Defaults must be the safe option: publishing blocked
   on failed validation, optional storage engines fail loudly instead of
   falling back, strict schema validation on every model.
3. **Least privilege.** CI runs with read-only tokens; the admin panel (M3)
   ships with explicit authn/authz and role separation; nothing gets broader
   access "for convenience".
4. **No secrets, no personal data, ever.** The repository is written as if
   public from day one. Secrets live in environment variables; `.env` is
   gitignored; CI scans the git history on every push.
5. **Defense in depth at the model layer.** Editorial and safety rules are
   enforced where the data lives (pydantic validators), not only in UI code
   that can be bypassed.

## 2. Threat model by component

### Content core (`cms-core`) — implemented

| Threat | Control (status) |
| --- | --- |
| SQL injection through content fields | Parameterized queries only; no string-built SQL (**done**) |
| Path traversal via media paths | Model validator rejects absolute paths and `..` segments (**done**) |
| Malformed content reaching the store | Strict pydantic validation: slug patterns, required fields, typed enums (**done**) |
| Active navigation URLs | Menu/admin links allow only explicit safe schemes or site-relative paths; redirects additionally reject filesystem traversal and server-directive metacharacters (**done**) |
| Silent fallback to the wrong database | Factory raises on unknown/unimplemented schemes (**done**) |
| Tampered translation freshness | States derived from source checksums, not editable flags (**done**) |

### Build/export (`cms-build`, M2)

| Threat | Control |
| --- | --- |
| XSS in generated sites | Autoescaping templates (Jinja2) everywhere; editors never inject raw HTML — rich content only via reviewed shortcodes/custom blocks |
| Malicious content in Markdown | Markdown rendered with a safe renderer; raw HTML blocks disabled by default, allowlist configurable per project |
| Script breakout through structured metadata | JSON-LD escapes every HTML closing sequence before entering its script element; adversarial regression test in force |
| Output outside the export directory | Export paths derived from validated slugs only; writes confined to the target directory |
| Non-reproducible builds hiding injected content | Deterministic builds (same input → same output) make any diff reviewable |

### Admin panel (`apps/admin`, M3)

Access control is **in force** since M3 phase 3 (argon2id hashes, server-side
sessions with expiry, `__Host-` session cookies
`HttpOnly`/`Secure`/`SameSite=Strict`,
synchronizer + double-submit CSRF tokens, login rate limiting, roles enforced
server-side, first account only via `cms admin create-user`) — exercised by
`tests/test_admin_auth.py`. Preview artifacts and uploaded media require a
valid session; sensitive responses carry HSTS and `Cache-Control: no-store`.
Unknown accounts perform equivalent password work, Argon2 verification runs
outside the event loop with bounded concurrency, and the in-process limiter
is bounded and keyed by both client and account. Media-library upload controls
are also in force. Multi-process deployments must additionally rate-limit
`/login` at the shared ingress because process-local state is not a distributed
brute-force control.

| Threat | Control |
| --- | --- |
| Unauthorized access | Explicit authentication; sessions/tokens with expiry; no default credentials; rate limiting on login |
| Privilege escalation | Role-based authorization (editor / reviewer / publisher at minimum), enforced server-side per endpoint |
| CSRF | Anti-CSRF tokens on state-changing requests (server-rendered UI) or token-based auth with same-site cookies |
| Malicious uploads | Media library validates raster type, byte size, pixel count and dimensions server-side; active SVG is rejected; writes cannot replace existing paths |
| Injection via API | All input through pydantic schemas; parameterized queries via the storage interface |
| Secrets in config | Configuration via environment only; startup fails if required secrets are missing rather than using defaults |
| Hostile XML import | `defusedxml` rejects DTDs and entities independent of source encoding; imports perform no network access |

### Storage backends (M1/M2)

| Threat | Control |
| --- | --- |
| Credential leakage in database URLs | URLs come from environment variables; never logged; example values only in `.env.example` (**policy in force**) |
| Backend impersonation via plugins | `register_backend` is an explicit, code-level API — projects audit the backends they register (**done**) |
| Server engines (PostgreSQL/SQL Server/MySQL) | TLS connections and least-privilege database users are deployment requirements |

### Supply chain & CI — implemented, evolving

| Threat | Control (status) |
| --- | --- |
| Leaked secrets in history | A digest-pinned trufflehog image scans full history on every push/PR; platform scanning adds push protection, validity checks, non-provider patterns and assisted detection (**done**) |
| Compromised dependency | `pip-audit` and Bandit gate every PR; workflow actions are SHA-pinned and updated by Dependabot; reproducible Python lock files remain an open improvement (**partial**) |
| CI token abuse | Workflow `permissions: contents: read`; no write tokens in CI (**done**) |
| Deploy-secret exfiltration | Untrusted package execution is confined to an artifact-build job; only pinned download/deploy actions run in the environment that receives the Azure token (**done**) |
| Remote artifact substitution | The downloaded axe bundle is version-pinned and SHA-256 verified before extraction; release/deploy actions are pinned to full commits (**done**) |
| Vulnerable code patterns | Bandit gates Python changes; CodeQL scans Actions, Python and bundled JavaScript on its managed schedule (**done**) |
| Force-push/history rewrite on `main` | Branch protection blocks force-pushes/deletions and requires all ten CI checks, including `Security audit` (**done**) |
| Malicious PR changing CI | Required status checks on PRs; workflow changes reviewed like code (**done**) |

## Secrets policy (consolidated)

One rule, enforced at every layer: **secrets exist only in environment
variables at the moment of use.** They are never written to
`sardine.toml`, never stored in the database (the single exception is
the panel's own per-instance signing key for preview links, which is
generated, random and never user-provided), never logged, never
recorded in the audit trail, never included in exports, build
artifacts or the demo snapshot, and never echoed back by any interface.
`.env` is gitignored; `.env.example` carries placeholders only. CI
scans full history for secrets on every push, and fork pull requests
receive no repository secrets at all — their service containers run on
throwaway values.

## Architecture security model — themes, extensions and providers (0.7.x)

The 0.7 line consolidated a model worth stating as policy
(ADR-0048–0051):

- **Discovery never executes code.** Themes and extensions are listed
  from packaging metadata (`importlib.metadata`); screenshots are
  files found through the distribution's file list. The first
  third-party code execution is the trial build the operator
  explicitly requests.
- **Compatibility is the package's own declared dependency range**,
  evaluated against the installed version — the same range the
  installer enforces, so the panel can never contradict reality.
- **Activation is transactional.** An isolated load and a full trial
  build must succeed before configuration changes; a failure shows its
  error and the configuration stays untouched.
- **Failures are contained and recovery needs no imports.** Any
  extension load failure is a typed error; a broken active extension
  renders its error instead of taking the panel down, and
  deactivation rewrites configuration without importing the extension
  — the recovery path works precisely when the import fails. Health
  checks (when declared) run contained, on demand, and never gate.
- **The panel never installs packages.** Package installation is
  arbitrary code execution and belongs to the operator's environment.
- **Provider contracts keep credentials out of the core.** Comments,
  mail, deployment and forms providers — and future contracts — follow
  one policy: the core ships the contract and at most a reference
  implementation; credentials are read from the environment at use
  time; provider failures are contained and audited, never
  visitor-facing; capabilities are declared, not inferred; conformance
  suites are public contracts.
- **Migration transport is bounded.** The media fetcher accepts
  http(s) to public addresses only (loopback, private, link-local and
  reserved ranges refused), enforces size and time caps with limited
  retries, and accounts for every URL. Panel uploads honor the size
  limit, are parsed by the same DTD/entity-rejecting parser as the
  CLI, and live in a short-TTL in-memory stash until confirmed.

## Supply chain (releases)

Publishing uses **PyPI trusted publishing** (OIDC) with one GitHub
environment per package, so no long-lived PyPI credentials exist;
artifacts build in CI from the tagged commit. Every release is
verified post-publication from the published artifacts themselves:
lockstep versions and bounds, license/notice payloads present, and a
clean install from the index. Third-party license texts are retained
in-tree and in the wheels, aggregated in THIRD_PARTY_NOTICES.md.

## 3. Data protection

- The framework stores editorial content only. Deployments that add user
  accounts (admin panel) hold names/emails of staff: keep them in the
  database, never in exported artifacts, and document retention on deletion.
- The generated public site contains no tracking by default; anything added
  by a project is that project's responsibility.
- The example site ships fictional content only.

## 4. Go-public record

- [x] `git log` audited for project-owned author addresses; no
      personal emails anywhere in history
- [x] Secret scan green over the full history at the flip commit
- [x] No files excluded by policy tracked (local tooling context, `.env`)
- [x] Dependencies reviewed; no known-vulnerable versions at the flip
- [x] SECURITY.md reporting channel set to a monitored address
- [x] License headers/NOTICE consistent (Apache-2.0)

Executed before the repository became public on 2026-07-17. These controls
remain standing CI and review requirements; the checklist is not a future
launch gate.

## 5. Incident response

1. A credential that ever appears in a commit is **compromised**: rotate it
   first, clean history second.
2. Vulnerabilities reported per SECURITY.md are triaged privately; fixes land
   before disclosure details.
3. After the repo is public, security fixes get their own releases and a
   changelog entry describing impact without an exploitation recipe.

## 6. Milestone gates

Security work is part of each milestone's definition of done:

- **Every milestone:** identify new trust boundaries; add hostile-input or
  abuse-path regressions; run dependency/static analysis; update repository
  documentation and the public wiki in the same delivery chain.

- **M2 (build/CLI):** autoescaping verified by tests; safe Markdown rendering;
  dependency review and version floors; export path confinement tests.
- **M3 (admin):** authn/authz test suite; CSRF protection; upload validation
  tests; failed-login rate limiting; security section in the admin docs —
  **all in force**, plus security headers on every admin response (CSP with
  no script source at all, frame denial) and the axe gate over the admin
  pages in CI. See [ADMIN_GUIDE.md](ADMIN_GUIDE.md).
- **M4 (theme/example):** CSP-compatible reference theme (no inline styles —
  already a theme rule); accessibility (WCAG 2.2 AA) checks in CI.
- **Go-public:** the checklist in section 4 was executed before visibility
  changed and remains the audit record.

## Deployment credentials (#156)

Deployment providers authenticate with secrets that never enter the
repository, the artifact, the interface or the logs. The standing
rules for the automated providers: encrypted at rest, least-privilege
tokens, configurable timeouts, concurrent-deployment protection, every
operation audited, and no editor-supplied command execution under any
circumstance. The demo pipeline already models the separation: the job
holding the deployment token never executes project code.

## Audit trail (#134)

Every security-relevant panel operation appends one activity record —
sign-ins and failures, workflow transitions, trash and purge, media,
user/role/2FA changes, builds. Records are append-only, survive the
deletion of their subject, never block the action they observe, and
are readable only by admins; retention is configurable and pruned at
startup. This is the auditing layer the automated-deployment work
(#156) plugs into.


## External preview links

Preview links are a deliberate, bounded hole in the authentication
wall. The token is HMAC-SHA256-signed over the entry, the link id and
the expiry, keyed by a per-instance secret stored in the database —
never in configuration or any artifact; a tampered expiry breaks the
signature. Every link expires (30-day maximum), revocation is stored
and immediate, and verification is constant-time. A link renders one
entry only, never listings or other unpublished content, and never
changes publication state. The residual risk is a leaked link being
readable until expiry or revocation; mitigations are short default
lifetimes, one-click revocation on the entry's card and the audit
trail recording every creation and revocation (link id only, never
the token).
