# ADR-0022 — The admin panel speaks the editor's language (gettext i18n)

- **Status:** accepted
- **Date:** 2026-07-19

## Context

The admin chrome was EN-only, with literals hardcoded across the Jinja
templates and route messages. A multilingual CMS whose own panel cannot
speak the editor's language undercuts its core promise, and hardcoded
strings cannot be translated, audited or kept complete. The roadmap
scheduled admin localization for M6; the owner pulled it forward and asked
for real i18n, not string swapping.

## Decision

- **Mechanism: GNU gettext via Babel** (a dependency of
  `sardine-cms-admin` only). Industry-standard pipeline — extract,
  translate, compile — with plural support. Templates call `_(...)`
  directly; the callables are injected per render context.
- **Catalogs are text, in git**: `messages.po` per language under
  `apps/admin/src/cms_admin/locale/<locale>/LC_MESSAGES/`, for `pt_PT`,
  `es`, `fr`, `de`. English is the source language: msgids are the real
  English strings. No binary `.mo` files in the repository — the app
  compiles every catalog to in-memory translations at startup
  (`babel.messages.mofile.write_mo` into a buffer), deterministic and
  build-step-free.
- **Resolution order, per request**: signed-in user's stored preference →
  the request's `Accept-Language` → English. The login page (no user yet)
  resolves from `Accept-Language`.
- **Per-user preference**: a nullable `language` column on the users
  table (storage migration 7, all four engines through the shared
  migrations and dialect transforms). The navbar user menu gains a
  language selector posting to `/profile/language` (CSRF like every
  form); `cms admin create-user` accepts `--language`.
- **Translations are passed per render context**, never installed
  globally on the shared Jinja environment — one process serves users in
  different languages concurrently.
- **Scope**: panel chrome, forms, messages, workflow transition labels
  and validation-rule descriptions as displayed by the admin. The
  engines' own strings (`cms-validation` descriptions, `cms-core` labels)
  stay English — they are API surface; the admin wraps them with its own
  msgids at the display boundary. Editorial content is never touched.
- **Completeness is enforced, not hoped for**: an anti-drift test parses
  the catalogs and fails if any extracted msgid is missing or untranslated
  in any shipped language — the same philosophy as the docs anti-drift
  suite.

## Consequences

- Adding a language = adding one `.po` file and listing it once; the
  anti-drift test then enforces its completeness.
- The five site languages and the admin languages are the same set today
  but decoupled by design (the admin list lives in `cms_admin.i18n`).
- Babel joins the admin's dependencies; the other five packages gain
  nothing.
