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
| Silent fallback to the wrong database | Factory raises on unknown/unimplemented schemes (**done**) |
| Tampered translation freshness | States derived from source checksums, not editable flags (**done**) |

### Build/export (`cms-build`, M2)

| Threat | Control |
| --- | --- |
| XSS in generated sites | Autoescaping templates (Jinja2) everywhere; editors never inject raw HTML — rich content only via reviewed shortcodes/custom blocks |
| Malicious content in Markdown | Markdown rendered with a safe renderer; raw HTML blocks disabled by default, allowlist configurable per project |
| Output outside the export directory | Export paths derived from validated slugs only; writes confined to the target directory |
| Non-reproducible builds hiding injected content | Deterministic builds (same input → same output) make any diff reviewable |

### Admin panel (`apps/admin`, M3)

Access control is **in force** since M3 phase 3 (argon2id hashes, server-side
sessions with expiry, session cookies `HttpOnly`/`Secure`/`SameSite=Strict`,
synchronizer + double-submit CSRF tokens, login rate limiting, roles enforced
server-side, first account only via `cms admin create-user`) — exercised by
`tests/test_admin_auth.py`. Media-library upload controls are also in force.

| Threat | Control |
| --- | --- |
| Unauthorized access | Explicit authentication; sessions/tokens with expiry; no default credentials; rate limiting on login |
| Privilege escalation | Role-based authorization (editor / reviewer / publisher at minimum), enforced server-side per endpoint |
| CSRF | Anti-CSRF tokens on state-changing requests (server-rendered UI) or token-based auth with same-site cookies |
| Malicious uploads | Media library validates type, size and dimensions server-side; uploads stored outside the web root; no SVG scripting (sanitize or restrict) |
| Injection via API | All input through pydantic schemas; parameterized queries via the storage interface |
| Secrets in config | Configuration via environment only; startup fails if required secrets are missing rather than using defaults |

### Storage backends (M1/M2)

| Threat | Control |
| --- | --- |
| Credential leakage in database URLs | URLs come from environment variables; never logged; example values only in `.env.example` (**policy in force**) |
| Backend impersonation via plugins | `register_backend` is an explicit, code-level API — projects audit the backends they register (**done**) |
| Server engines (PostgreSQL/SQL Server/MySQL) | TLS connections and least-privilege database users are deployment requirements |

### Supply chain & CI — implemented, evolving

| Threat | Control (status) |
| --- | --- |
| Leaked secrets in history | trufflehog scans the full git history on every push/PR (**done**) |
| Compromised dependency | Minimal dependency surface, version floors in `pyproject.toml` and dependency review; reproducible lock/update automation remains an open supply-chain improvement (**partial**) |
| CI token abuse | Workflow `permissions: contents: read`; no write tokens in CI (**done**) |
| Force-push/history rewrite on `main` | Branch protection: force-pushes and deletions blocked; nine required checks (**done**) |
| Malicious PR changing CI | Required status checks on PRs; workflow changes reviewed like code (**done**) |

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
