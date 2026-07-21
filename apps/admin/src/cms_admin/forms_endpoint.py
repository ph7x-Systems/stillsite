"""The official forms endpoint: where published forms submit.

Static sites cannot receive a POST, so the panel does — this is the
reference implementation the decision record promises. Server-side
validation against the addressed form's declared fields is the only
source of truth; the anti-spam protections are layered (honeypot,
elapsed-time check when present, per-address rate limiting, origin
allowlist); responses are deterministic (the same state always maps
to the same HTTP status) and localized from the language packs; the
notification mail is contained — a delivery failure is reported and
audited, never a crash.
"""

import asyncio
import logging
import time
from html import escape
from urllib.parse import urlsplit

from cms_core.language_packs import registered_language_packs
from fastapi import APIRouter, Request, status
from fastapi.responses import HTMLResponse

from cms_admin.audit import record as audit_record
from cms_admin.publishing import _project

logger = logging.getLogger("cms_admin.forms")

router = APIRouter()

RATE_LIMIT_WINDOW_SECONDS = 60.0
RATE_LIMIT_MAX_SUBMISSIONS = 5
MIN_ELAPSED_SECONDS = 3.0
VALUE_MAX_CHARS = 10_000


def _label(tag: str, key: str, **kwargs: str) -> str:
    """A pack site label, EN fallback — the endpoint hardcodes no
    visitor-facing text."""
    packs = {pack.tag: pack for pack in registered_language_packs()}
    pack = packs.get(tag) or packs.get("en")
    text = (pack.site_labels.get(key) if pack else None) or (
        packs["en"].site_labels.get(key, key) if "en" in packs else key
    )
    return text.format(**kwargs) if kwargs else text


def _response(
    title: str, body_html: str, back_url: str, back_label: str, status_code: int, lang: str
) -> HTMLResponse:
    """A minimal, accessible, self-contained page — the no-JS path."""
    page = (
        "<!DOCTYPE html>\n"
        f'<html lang="{escape(lang)}">\n<head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(title)}</title></head>\n"
        f"<body><main><h1>{escape(title)}</h1>{body_html}"
        f'<p><a href="{escape(back_url, quote=True)}">{escape(back_label)}</a></p>'
        "</main></body></html>\n"
    )
    return HTMLResponse(page, status_code=status_code)


def _clean(value: str) -> str:
    """Plain text only: control characters stripped, length capped."""
    text = "".join(ch for ch in value if ch >= " " or ch in "\n\t")
    return text[:VALUE_MAX_CHARS].strip()


def _origin_allowed(request: Request, base_url: str) -> bool:
    """The published site is the only expected sender (ADR: origin
    allowlist instead of visitor-session CSRF). Absent headers pass —
    strict same-origin browsers and non-browser clients send none, and
    the layered protections still apply."""
    allowed = urlsplit(base_url)
    for header in ("origin", "referer"):
        value = request.headers.get(header)
        if not value:
            continue
        got = urlsplit(value)
        if (got.scheme, got.netloc) != (allowed.scheme, allowed.netloc):
            return False
    return True


def _rate_limited(request: Request) -> bool:
    client = request.client.host if request.client else "unknown"
    now = time.monotonic()
    buckets: dict[str, list[float]] = request.app.state.__dict__.setdefault(
        "forms_rate_buckets", {}
    )
    bucket = [t for t in buckets.get(client, []) if now - t < RATE_LIMIT_WINDOW_SECONDS]
    if len(bucket) >= RATE_LIMIT_MAX_SUBMISSIONS:
        buckets[client] = bucket
        return True
    bucket.append(now)
    buckets[client] = bucket
    return False


@router.post("/forms/submit")
async def submit(request: Request) -> HTMLResponse:
    form = await request.form()
    lang = _clean(str(form.get("form_language", "en"))) or "en"
    project = _project(request)
    back_url = str(project.site.base_url) if project else "/"
    back = _label(lang, "form-back")

    def refuse(status_code: int, key: str) -> HTMLResponse:
        return _response(_label(lang, key), "", back_url, back, status_code, lang)

    if project is None:
        return refuse(status.HTTP_404_NOT_FOUND, "form-error")
    if _rate_limited(request):
        return refuse(status.HTTP_429_TOO_MANY_REQUESTS, "form-rate-limited")
    if not _origin_allowed(request, str(project.site.base_url)):
        return refuse(status.HTTP_403_FORBIDDEN, "form-error")
    if _clean(str(form.get("website", ""))):  # honeypot: must arrive empty
        return refuse(status.HTTP_403_FORBIDDEN, "form-error")
    elapsed_raw = _clean(str(form.get("form_elapsed", "")))
    if elapsed_raw:
        try:
            if float(elapsed_raw) < MIN_ELAPSED_SECONDS:
                return refuse(status.HTTP_403_FORBIDDEN, "form-error")
        except ValueError:
            return refuse(status.HTTP_403_FORBIDDEN, "form-error")

    # Resolve the addressed form — validation runs against the declared
    # field set, never against whatever arrives.
    page_id = _clean(str(form.get("form_page", "")))
    section_key = _clean(str(form.get("form_section", "")))
    db = request.app.state.db
    page = await db.run(lambda storage: storage.load_page(page_id)) if page_id else None
    section = next(
        (s for s in (page.sections if page else []) if s.key == section_key and s.kind == "form"),
        None,
    )
    if page is None or page.deleted_at is not None or section is None:
        return refuse(status.HTTP_404_NOT_FOUND, "form-error")

    declared = [dict(item) for item in section.source.items]
    errors: list[str] = []
    values: dict[str, str] = {}
    for field in declared:
        key = str(field.get("key", "")).strip()
        if not key:
            continue
        label = str(field.get("label", key))
        value = _clean(str(form.get(f"field_{key}", "")))
        required = bool(str(field.get("required", "")).strip())
        if required and not value:
            errors.append(_label(lang, "form-field-required", label=label))
        elif value and str(field.get("type", "")) == "email" and ("@" not in value or " " in value):
            errors.append(_label(lang, "form-field-email", label=label))
        values[key] = value
    consent_label = section.source.fields.get("consent_label", "")
    if consent_label and not _clean(str(form.get("consent", ""))):
        errors.append(_label(lang, "form-field-required", label=consent_label))
    if errors:
        listing = "".join(f"<li>{escape(error)}</li>" for error in errors)
        return _response(
            _label(lang, "form-error"),
            f'<ul aria-label="{escape(_label(lang, "form-error"), quote=True)}">{listing}</ul>',
            back_url,
            back,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            lang,
        )

    # Notification: contained — a mail failure is reported, never a crash.
    delivered = False
    if project.forms_notify:
        try:
            mailer = request.app.state.mailer
            if mailer is not None:
                body = "\n".join(f"{key}: {value}" for key, value in values.items() if value)
                subject = f"[{project.site.name}] {section.source.fields.get('heading', 'Form')}"
                await asyncio.to_thread(
                    mailer.send, project.forms_notify, subject, f"{page_id}/{section_key}\n\n{body}"
                )
                delivered = True
        except Exception:
            logger.exception("form notification failed")
    await audit_record(
        request,
        "visitor",
        "form-received" if delivered or not project.forms_notify else "form-mail-failed",
        "form",
        f"{page_id}/{section_key}",
        "",
    )

    heading = section.source.fields.get("success_heading", "") or _label(lang, "form-received")
    text = section.source.fields.get("success_text", "") or _label(lang, "form-thanks")
    return _response(heading, f"<p>{escape(text)}</p>", back_url, back, status.HTTP_200_OK, lang)
