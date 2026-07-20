# ADR-0032 — Email and notifications: SMTP-only, optional, enumeration-safe

- **Status:** proposed
- **Date:** 2026-07-20

## Context

Two M7 capabilities need outbound email: password reset (today a lost
password requires CLI access to the server) and editorial notifications
(a reviewer should not have to poll the panel to learn that something
awaits review). The admin is the project's only server component; the
exported site must stay static and untouched by any of this. Constraints
already in force: settings come from the environment only (no secrets in
files), accounts are never exported, personal data stays in the
project's database (SECURITY_STRATEGY), and every admin string is
localized (ADR-0022).

## Decision

**Transport: SMTP, nothing else.**

- Delivery uses the standard library (`smtplib`, `email.message`) over
  STARTTLS or implicit TLS. No provider SDKs, no HTTP APIs, no new
  dependencies: SMTP is the one contract every provider offers, and it
  keeps provider names out of the repository.
- Configuration is environment-only:
  `SARDINE_SMTP_URL` (`smtp://user:password@host:587` — STARTTLS — or
  `smtps://…:465`) and `SARDINE_MAIL_FROM`. Unset means **email is off
  and everything degrades gracefully**: no reset link on the login page,
  no notifications, the panel fully functional — exactly today's
  behavior. Misconfigured SMTP never blocks an editorial action.

**Addresses: a new optional `email` column on users** (storage migration,
all four engines, shared dialect transforms). The Users screen and
`cms admin create-user` gain the optional field. Accounts remain
unexported; addresses live only in the project database.

**Password reset, enumeration-safe:**

- The login page links to a request form. The response is always the
  same ("if that account has an address, a message was sent") with
  equalized work, and the form shares the login rate limiter — no user
  enumeration, no timing oracle.
- Tokens are single-use, 256-bit random, stored **hashed** (like session
  tokens), expire in 30 minutes, and are stored in a new
  `password_resets` table (own migration). A completed reset applies the
  password policy and revokes every session of the account — the same
  contract as `cms admin create-user --force`.
- Messages are plain text, localized to the user's panel language
  (ADR-0022 catalogs), and contain exactly one absolute link built from
  the admin's own request origin. No tracking, no HTML.

**Notifications, minimal and explicit:**

- Two events only, for now: **review requested** (a transition into
  `review` mails every user of role reviewer or above that has an
  address, except the actor) and **published** (mails the entry's last
  editing author, if not the actor).
- Delivery is fire-and-forget off the request path (a worker thread);
  failures are recorded on the publishing panel's activity record and
  never surface as editorial errors, never retry storms.
- Every message states why it was sent; there is no digest, no
  scheduling, no per-event preference matrix yet — a preferences ADR can
  supersede this when reality demands one.

## Consequences

- Two storage migrations (users.email; password_resets), covered by the
  conformance suite on SQLite, PostgreSQL, MySQL/MariaDB and SQL Server.
- The hardening suite grows: reset responses indistinguishable for
  known/unknown accounts, hashed tokens at rest, expiry and single-use
  enforced, sessions revoked on reset, no email content in logs.
- New admin msgids join the i18n catalogs and the anti-drift inventory
  (PT-PT, ES, FR, DE).
- The demo ships with SMTP unset: the public snapshot must not change.
- TOTP 2FA (next M7 item) stays out of scope here — it deliberately
  does not depend on email.
