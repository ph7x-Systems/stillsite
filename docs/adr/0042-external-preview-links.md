# ADR-0042 — External preview links

- **Status:** accepted
- **Date:** 2026-07-22

## Context

Editorial approval today requires a panel account; teams expect "send
a preview link". An unauthenticated preview URL is a deliberate hole
in the authentication wall, so its shape is a security decision before
it is a feature.

## Decision

- **Signed, not merely random**: a preview link carries an HMAC-SHA256
  token binding the entry kind, the entry id and the expiry moment,
  keyed by a per-instance secret stored in the panel's database (never
  in configuration or the artifact). Verification is constant-time and
  needs no lookup for the common case; forgery requires the key.
- **Expiry is mandatory and inside the signature**: every link states
  its expiry; verification compares against the current moment — a
  tampered expiry breaks the signature. No unlimited links exist.
- **Revocation is explicit**: each link has an id recorded at creation;
  a revocation marks it and verification refuses it afterwards.
  Revocation survives restarts (stored), and revoking is available on
  the entry's management card alongside the active-links list.
- **Minimal scope**: a link renders exactly one entry, through the real
  builder and theme, with a visible draft banner in the viewer's
  language (from the language packs). It exposes no listings, no
  navigation into other unpublished content and no panel data; the
  publication state of the entry never changes.
- **Audited**: creation and revocation land in the audit trail with the
  link id — never the token.
- The leak surface is documented in SECURITY_STRATEGY: a leaked link is
  readable until expiry or revocation; the mitigations are short
  default lifetimes, one-click revocation and the audit trail.

## Consequences

- A new storage table for link records (id, entry, expiry, revoked) —
  additive migration; the signing key is created on first use.
- The preview route lives in the panel app (it has the builder, the
  storage and the audit trail) and requires no session.
- The entry editors gain a management card: create with a chosen
  lifetime, copy, revoke, active links listed with their expiry.
