# ADR-0052 — Extension settings: declared schema, explicit provenance, secrets never touched

- **Status:** accepted
- **Date:** 2026-07-23

## Context

Extensions can declare capabilities and health, but configuration
still means documentation and hand-edited files. The panel needs a
settings surface — without breaking the two rules everything else
obeys: nothing is inferred from code, and secrets exist only in the
environment.

## Decision

- **The schema is declared data.** The `Extension` contract gains
  `settings_schema`: a versioned, declarative description —
  `SettingsSchema(version, fields)` where each
  `SettingsField(key, type, label, default, required, env)` is plain
  data. Types are a small closed set (string, integer, boolean,
  choice). Defaults live in the schema, never in imperative code.
- **Values live in the project file; secrets never do.** Non-secret
  values persist under `[extension_settings.<name>]` in
  `sardine.toml`, written surgically like every other panel edit. A
  field with `env` set names a required environment variable: the
  panel never edits, stores or displays its value — it reports only
  presence or absence. The secrets policy in SECURITY_STRATEGY applies
  verbatim.
- **Provenance is explicit.** Every rendered value states where it
  came from: schema default, operator-configured, or environment
  (present/absent). The panel shows it; nothing is silently merged.
- **Validation is deterministic and precedes persistence.** Submitted
  values validate against the schema (type, choices, required) before
  anything is written; a validation failure renders in place with the
  config untouched — the activation pattern, applied to settings.
- **Schema versions may migrate, optionally.** An extension may
  declare `migrate(old_version, values) -> values`; stored values
  carry the schema version they were written under, and migration
  runs contained at read time. No migration declared → unknown keys
  are surfaced, never silently dropped.
- **Extensions read their settings at load time.** The resolved,
  validated values (defaults + operator values, with env presence
  flags) are handed to the extension through one optional
  `configure(values)` callable — contained like every extension call.
- **Doctor reports the whole picture** per extension: schema valid,
  stored values valid, each required environment variable present or
  missing, migration state.

## Consequences

- An operator configures extensions where they manage everything else,
  with the same failure semantics: invalid input never reaches disk,
  a broken extension never takes the screen down.
- Secrets remain impossible to leak through this surface by
  construction — the panel has nothing to show.
- The consent architecture (#232) and translation providers (#228)
  inherit a finished settings mechanism instead of inventing their
  own.
