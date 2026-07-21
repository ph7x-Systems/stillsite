# ADR-0039 — Forms: a section kind and an official reference endpoint

- **Status:** accepted
- **Date:** 2026-07-21

## Context

An institutional site without a working contact form is not
functionally complete. Sardine builds static sites, so a form needs
two halves: markup the build emits, and an endpoint that receives the
submission. A contract without a bundled implementation is not a
feature — the reference endpoint ships first; a provider contract for
third parties is frozen only after the reference proves the shape.

## Functional model

- **A form is a section** of kind `form`. Its flat fields describe the
  form (`heading`, `intro` (markdown), `submit_label`,
  `success_heading`, `success_text`, `consent_label`); its repeating
  items (ADR-0037) declare the inputs — columns `key`, `type`,
  `label`, `required`. No new content model, storage or migration is
  needed to author a form.
- **Field types v1**: `text`, `email`, `textarea`, `checkbox`. New
  types are additive; unknown types render as `text` so an older theme
  never breaks on newer content.
- **Labels are editorial data** entered per language like every other
  section content — themes hardcode no visitor-facing text. The only
  theme-owned strings come from language packs' site labels.
- A consent checkbox is always rendered and always required when
  `consent_label` is non-empty.

## The submission path

- The build wires each form to `[forms] endpoint` (project
  configuration). Without an endpoint the section renders its content
  but no `<form>` — a form that cannot submit anywhere is not shown as
  if it could.
- **The reference endpoint lives in the admin application** (POST
  `/forms/submit`), because that is where the existing mail transports
  (ADR-0032) and storage already live. Operators who keep the panel
  private can point `[forms] endpoint` at any compatible service.
- The no-JS path is primary: the endpoint answers with a minimal,
  localized, accessible HTML page (success or error, with a link back
  to the referring page). Progressive enhancement may later submit
  in-page; it never becomes a requirement.
- **Responses are deterministic and correctly coded**: the same
  submission state always produces the same HTTP status (success 200,
  validation failure 422, spam/origin rejection 403, rate limit 429,
  unknown form 404) and a stable error structure — per-field failures
  identified by field key, so any client (the HTML page today, an
  enhanced one tomorrow) can rely on the shape.

## Security

- **Server-side validation is mandatory**: the endpoint validates the
  submission against the declared field set of the addressed form
  (page, section key), required flags included — never against
  whatever arrives.
- **Origin allowlist**: cross-origin by design (static site → panel
  origin), so the endpoint checks `Origin`/`Referer` against the
  site's configured `base_url` instead of cookie-based CSRF (there is
  no visitor session to protect).
- **Honeypot**: a visually hidden field that must arrive empty.
- **Time trap**: a hidden elapsed-time field filled by progressive
  enhancement; when present it must exceed a minimum. Its absence is
  never an error (the no-JS path stays first-class).
- **Rate limiting** per client address at the endpoint.
- **Sanitization**: values are treated as plain text everywhere
  (length-capped, control characters stripped); mail bodies and stored
  values never carry markup.
- Submissions are not replay-protected v1 (idempotent notification;
  rate limiting bounds abuse) — revisit if storage-backed workflows
  appear.

## Accessibility (WCAG 2.2 AA)

Every input has a `<label for>`; required fields declare
`aria-required`; the endpoint's error page lists the failures as links
in a landmarked summary; keyboard-only operation; no JavaScript
required anywhere on the path.

## Storage

Optional (`[forms] store = true`): submissions persist through the
storage contract (its own migration) before any mail is attempted.
Delivery and storage are decoupled — a mail failure never loses a
stored submission, and a storage failure still attempts notification;
each failure is reported independently in the endpoint's operator log
and audit trail.

## Extensibility

Deferred deliberately. The provider contract (what a submission is,
what a provider returns, how errors surface) is frozen in a follow-up
decision only after the reference endpoint has run in production —
freezing an immature interface is how contracts rot.

## Consequences

- Both bundled themes must render the `form` kind (accessible markup,
  honeypot, time-trap field, success/error states) — theme parity is
  part of done.
- The admin gains a public, unauthenticated endpoint: it must be
  rate-limited, origin-checked and auditable from the first release.
- The example site and live demo gain a contact form wired to a dry
  endpoint, so the full path is demonstrable without operating a
  mailbox.
