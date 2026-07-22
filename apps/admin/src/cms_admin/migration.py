"""The Migration screen: the WXR flow's second face (ADR-0047).

No import semantics live here. Upload and inspect render the same
report the CLI prints; running consumes a short-lived in-memory stash
of the uploaded bytes and calls the same pipeline the CLI calls:
``apply_wxr_import``, ``fetch_media_for_articles`` and the shared
redirect helpers. Admin-only; runs are audited with counts, never file
contents.
"""

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from cms_core import AdminSession, Role, User, WxrMapping, import_wxr, inspect_wxr
from cms_core.migration import apply_wxr_import
from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, status

from cms_admin.audit import record as audit_record
from cms_admin.auth import current_session, enforce_csrf, get_db
from cms_admin.navigation import AdminScreen, register_screen

router = APIRouter()

register_screen(
    AdminScreen("migration", "/migration", "Migration", "bi-box-arrow-in-down", 85, Role.ADMIN)
)

STASH_TTL = timedelta(minutes=15)


@dataclass
class _Stash:
    payload: bytes
    expires: datetime


def _require_admin(user: User) -> None:
    if user.role is not Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin role required")


def _stashes(request: Request) -> dict[str, _Stash]:
    if not hasattr(request.app.state, "migration_stash"):
        request.app.state.migration_stash = {}
    stashes: dict[str, _Stash] = request.app.state.migration_stash
    return stashes


def _stash_put(request: Request, payload: bytes) -> str:
    stashes = _stashes(request)
    now = datetime.now(tz=UTC)
    for token in [token for token, stash in stashes.items() if stash.expires < now]:
        del stashes[token]
    token = secrets.token_urlsafe(16)
    stashes[token] = _Stash(payload=payload, expires=now + STASH_TTL)
    return token


def _stash_take(request: Request, token: str) -> bytes | None:
    stash = _stashes(request).pop(token, None)
    if stash is None or stash.expires < datetime.now(tz=UTC):
        return None
    return stash.payload


def _mapping_from_form(raw: str) -> dict[str, str]:
    """One rename per line, ``source = target``; blank target drops."""
    table: dict[str, str] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        source, _, target = line.partition("=")
        source, target = source.strip(), target.strip()
        if source:
            table[source] = target
    return table


@router.get("/migration")
async def migration_home(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(current_session),
) -> object:
    user, session = user_session
    _require_admin(user)
    return request.app.state.templates.TemplateResponse(
        request,
        "migration.html.j2",
        {
            "user": user,
            "csrf_token": session.csrf_token,
            "active_section": "migration",
            "stage": "upload",
        },
    )


@router.post("/migration/inspect")
async def migration_inspect(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    export: UploadFile | None = None,
) -> object:
    user, session = user_session
    _require_admin(user)
    settings = request.app.state.settings
    payload = b""
    if export is not None:
        payload = await export.read(settings.upload_max_bytes + 1)
    if not payload:
        raise HTTPException(status_code=400, detail="an export file is required")
    if len(payload) > settings.upload_max_bytes:
        raise HTTPException(status_code=413, detail="export exceeds the upload size limit")
    try:
        report = inspect_wxr(payload)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    token = _stash_put(request, payload)
    return request.app.state.templates.TemplateResponse(
        request,
        "migration.html.j2",
        {
            "user": user,
            "csrf_token": session.csrf_token,
            "active_section": "migration",
            "stage": "report",
            "report": report,
            "token": token,
        },
    )


@router.post("/migration/run")
async def migration_run(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    token: str = Form(""),
    map_authors: str = Form(""),
    map_categories: str = Form(""),
    map_tags: str = Form(""),
    update: str = Form(""),
    fetch_media: str = Form(""),
) -> object:
    user, session = user_session
    _require_admin(user)
    payload = _stash_take(request, token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="the uploaded export expired; upload it again",
        )
    mapping = WxrMapping(
        authors=_mapping_from_form(map_authors),
        categories=_mapping_from_form(map_categories),
        tags=_mapping_from_form(map_tags),
    )
    try:
        imported = import_wxr(payload, mapping=mapping)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    from cms_cli.project import load_project

    project = load_project(request.app.state.settings.project_dir)
    applied = await get_db(request).run(
        lambda storage: apply_wxr_import(storage, imported.articles, update=bool(update))
    )

    media_outcomes: list[Any] = []
    if fetch_media:
        media_outcomes = await get_db(request).run(lambda storage: _fetch_media(project, storage))

    redirect_count = _record_redirects(project, applied.landed, applied.renamed)

    await audit_record(
        request,
        user.username,
        "migrated",
        "wxr-import",
        f"{applied.new} new, {applied.updated} updated, {applied.matched} matched",
    )
    return request.app.state.templates.TemplateResponse(
        request,
        "migration.html.j2",
        {
            "user": user,
            "csrf_token": session.csrf_token,
            "active_section": "migration",
            "stage": "result",
            "applied": applied,
            "skipped": imported.skipped,
            "media_outcomes": media_outcomes,
            "redirect_count": redirect_count,
        },
    )


def _fetch_media(project: Any, storage: Any) -> list[Any]:
    from cms_core.media_fetch import default_fetcher, fetch_media_for_articles

    migrated = [
        article for article in storage.load_all_articles() if article.fields.get("wxr_post_id")
    ]
    result = fetch_media_for_articles(
        migrated,
        storage.load_all_media_assets(),
        source_language=project.site.source_language,
        fetch=default_fetcher,
    )
    media_root = project.directory / "media"
    for relative, data in sorted(result.files.items()):
        destination = media_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    for asset in result.assets:
        storage.save_media_asset(asset)
    for article in result.articles:
        storage.save_article(article)
    return list(result.outcomes)


def _record_redirects(project: Any, articles: list[Any], renamed: list[Any]) -> int:
    from cms_build.redirects import (
        merge_redirects,
        migration_redirect_changes,
        write_redirects,
    )
    from cms_cli.project import PROJECT_FILE

    config = project.site
    changes = migration_redirect_changes(config, articles, renamed)
    if not changes:
        return 0
    existing = dict(config.redirects)
    merged = merge_redirects(existing, changes)
    if merged != existing:
        write_redirects(project.directory / PROJECT_FILE, merged)
    return len(changes)


__all__ = ["router"]
