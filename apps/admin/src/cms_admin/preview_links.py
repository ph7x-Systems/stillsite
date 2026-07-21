"""External preview links (ADR-0042): signed, expiring, revocable.

The token binds the entry kind, the entry id, the link id and the
expiry moment under an HMAC-SHA256 keyed by a per-instance secret that
lives in the database — never in configuration or any artifact. A
tampered expiry breaks the signature; a revoked or expired link
refuses; the entry's publication state never changes. Creation and
revocation are audited with the link id, never the token.
"""

import hashlib
import hmac
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from cms_core import AdminSession, Article, ContentStatus, Language, Page, PreviewLink, User
from cms_core.language_packs import registered_language_packs
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from cms_admin.audit import record as audit_record
from cms_admin.auth import enforce_csrf, get_db
from cms_admin.publishing import _project
from cms_admin.security import admin_path

if TYPE_CHECKING:
    from cms_validation import SiteContent

logger = logging.getLogger("cms_admin.preview_links")

router = APIRouter()

SECRET_NAME = "preview-link-signing-key"
DEFAULT_LIFETIME_DAYS = 7
MAX_LIFETIME_DAYS = 30


async def _signing_key(request: Request) -> bytes:
    value = await get_db(request).run(
        lambda storage: storage.get_or_create_secret(SECRET_NAME, lambda: secrets.token_hex(32))
    )
    return bytes.fromhex(value)


def sign_token(key: bytes, kind: str, entry_id: str, link_id: str, expires_at: datetime) -> str:
    stamp = str(int(expires_at.timestamp()))
    payload = f"{kind}:{entry_id}:{link_id}:{stamp}".encode()
    digest = hmac.new(key, payload, hashlib.sha256).hexdigest()
    return f"{link_id}.{stamp}.{digest}"


def verify_token(key: bytes, kind: str, entry_id: str, token: str, now: datetime) -> str | None:
    """The link id when the token is genuine and current, else None.
    Clock-independent by construction: callers inject ``now``."""
    try:
        link_id, stamp, digest = token.split(".")
        expires_at = datetime.fromtimestamp(int(stamp), tz=UTC)
    except ValueError:
        return None
    payload = f"{kind}:{entry_id}:{link_id}:{stamp}".encode()
    expected = hmac.new(key, payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, digest):
        return None
    if now >= expires_at:
        return None
    return link_id


def _banner_label(tag: str) -> str:
    packs = {pack.tag: pack for pack in registered_language_packs()}
    pack = packs.get(tag) or packs.get("en")
    if pack and "preview-banner" in pack.site_labels:
        return pack.site_labels["preview-banner"]
    english = packs.get("en")
    if english is None:
        return "Draft preview"
    return english.site_labels.get("preview-banner", "Draft preview")


async def _load_entry(request: Request, kind: str, entry_id: str) -> Article | Page | None:
    db = get_db(request)
    if kind == "article":
        return await db.run(lambda storage: storage.load_article(entry_id))
    if kind == "page":
        return await db.run(lambda storage: storage.load_page(entry_id))
    return None


@router.post("/{kind}s/{entry_id}/preview-links")
async def create_link(
    request: Request,
    kind: str,
    entry_id: str,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    days: int = Form(DEFAULT_LIFETIME_DAYS),
) -> RedirectResponse:
    user, _ = user_session
    if kind not in ("article", "page"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown kind")
    entry = await _load_entry(request, kind, entry_id)
    if entry is None or entry.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown entry")
    lifetime = min(max(int(days), 1), MAX_LIFETIME_DAYS)
    now = datetime.now(tz=UTC)
    link = PreviewLink(
        id=uuid.uuid4().hex[:16],
        entry_kind=kind,
        entry_id=entry_id,
        created_at=now,
        expires_at=now + timedelta(days=lifetime),
    )
    await get_db(request).run(lambda storage: storage.save_preview_link(link))
    await audit_record(request, user.username, "preview-link-created", kind, entry_id, link.id)
    return RedirectResponse(admin_path(f"{kind}s", entry_id), status_code=status.HTTP_303_SEE_OTHER)


@router.post("/preview-links/{link_id}/revoke")
async def revoke_link(
    request: Request,
    link_id: str,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
) -> RedirectResponse:
    user, _ = user_session
    db = get_db(request)
    link = await db.run(lambda storage: storage.load_preview_link(link_id))
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown link")
    await db.run(lambda storage: storage.revoke_preview_link(link_id))
    await audit_record(
        request, user.username, "preview-link-revoked", link.entry_kind, link.entry_id, link.id
    )
    return RedirectResponse(
        admin_path(f"{link.entry_kind}s", link.entry_id), status_code=status.HTTP_303_SEE_OTHER
    )


async def links_context(request: Request, kind: str, entry_id: str) -> dict[str, object]:
    """Active links for the entry's management card, tokens included —
    computed, never stored."""
    db = get_db(request)
    links = await db.run(lambda storage: storage.list_preview_links(kind, entry_id))
    key = await _signing_key(request)
    now = datetime.now(tz=UTC)
    active = [
        {
            "id": link.id,
            "expires_at": link.expires_at,
            "url": f"/shared/{kind}/{entry_id}/"
            + sign_token(key, kind, entry_id, link.id, link.expires_at),
        }
        for link in links
        if not link.revoked and link.expires_at > now
    ]
    return {"preview_links": active, "preview_kind": kind, "preview_entry_id": entry_id}


@router.get("/shared/{kind}/{entry_id}/{token}")
async def shared_preview(
    request: Request,
    kind: str,
    entry_id: str,
    token: str,
    lang: str = "",
) -> HTMLResponse:
    """The unauthenticated preview (ADR-0042): one entry, the real
    theme, a visible draft banner — nothing else."""
    if kind not in ("article", "page"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown kind")
    key = await _signing_key(request)
    now = datetime.now(tz=UTC)
    link_id = verify_token(key, kind, entry_id, token, now)
    if link_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown link")
    link = await get_db(request).run(lambda storage: storage.load_preview_link(link_id))
    if link is None or link.revoked or link.entry_kind != kind or link.entry_id != entry_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown link")
    entry = await _load_entry(request, kind, entry_id)
    if entry is None or entry.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown entry")
    project = _project(request)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no project")
    language = project.site.source_language
    if lang:
        try:
            candidate = Language(lang)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="unknown language"
            ) from None
        if candidate in (project.site.source_language, *project.site.languages):
            language = candidate

    import asyncio

    from cms_build import build_site, urls

    preview = entry.model_copy(deep=True)
    preview.status = ContentStatus.PUBLISHED  # render only; never persisted
    content = await _shared_content(request, preview, kind)
    # A one-entry site build: every complete language renders, and the
    # content set contains nothing but this entry and the media.
    artifact = await asyncio.to_thread(
        build_site,
        project.site,
        content,
        media_files=project.collect_media_files(),
        now=now,
    )
    if isinstance(preview, Article):
        path = urls.article_path(project.site, preview, language)
    else:
        path = urls.page_path(preview, language, source=project.site.source_language)
    page_file = urls.output_file(path)
    if page_file not in artifact.files:
        # The entry has no rendering in that language yet — fall back to
        # the source language rather than failing a valid link.
        language = project.site.source_language
        if isinstance(preview, Article):
            path = urls.article_path(project.site, preview, language)
        else:
            path = urls.page_path(preview, language, source=project.site.source_language)
        page_file = urls.output_file(path)
        if page_file not in artifact.files:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not renderable")
    html = artifact.files[page_file].decode("utf-8")
    style = (
        "<style>.sardine-preview-banner{position:sticky;top:0;z-index:99;"
        "background:#7a1f1f;color:#fff;padding:.6em 1em;text-align:center;"
        "font-family:system-ui,sans-serif}</style>"
    )
    label = _banner_label(language.value)
    banner = f'<div class="sardine-preview-banner" role="status">{label}</div>'
    html = html.replace("</head>", style + "</head>", 1)
    html = html.replace("<body>", "<body>" + banner, 1)
    return HTMLResponse(html)


async def _shared_content(request: Request, entry: Article | Page, kind: str) -> "SiteContent":
    from cms_validation import SiteContent

    db = get_db(request)
    media = await db.run(lambda storage: storage.load_all_media_assets())
    if isinstance(entry, Article):
        return SiteContent(articles=[entry], media=media)
    return SiteContent(pages=[entry], media=media)
