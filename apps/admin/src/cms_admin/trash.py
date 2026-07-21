"""The trash (ADR-0026): reversible deletion for articles and pages.

Trashing stamps ``deleted_at`` and saves through the same choke points as
every other edit, so it is recorded as a revision; restore clears the
stamp the same way. Purge is the panel's only hard delete and needs the
admin role.
"""

from datetime import UTC, datetime
from typing import Annotated

from cms_core import Article, Page, Role, StorageBackend, User
from cms_core.accounts import AdminSession
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from cms_admin.articles import _save_article
from cms_admin.audit import record as audit_record
from cms_admin.auth import current_session, enforce_csrf, get_db, require_at_least
from cms_admin.navigation import AdminScreen, register_screen
from cms_admin.pages import _save_page
from cms_admin.security import admin_path

router = APIRouter(prefix="/trash")

register_screen(AdminScreen("trash", "/trash", "Trash", "bi-trash3", 130))

_REQUIRE_ADMIN = require_at_least(Role.ADMIN)


@router.get("")
async def trash_list(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(current_session),
) -> object:
    user, session = user_session

    def load(storage: StorageBackend) -> tuple[list[Article], list[Page]]:
        articles = [a for a in storage.load_all_articles() if a.deleted_at is not None]
        pages = [p for p in storage.load_all_pages() if p.deleted_at is not None]
        return articles, pages

    articles, pages = await get_db(request).run(load)
    return request.app.state.templates.TemplateResponse(
        request,
        "trash.html.j2",
        {
            "user": user,
            "csrf_token": session.csrf_token,
            "active_section": "trash",
            "articles": articles,
            "pages": pages,
        },
    )


async def _load_entity(request: Request, kind: str, entity_id: str) -> Article | Page:
    entity: Article | Page | None
    if kind == "article":
        entity = await get_db(request).run(lambda storage: storage.load_article(entity_id))
    elif kind == "page":
        entity = await get_db(request).run(lambda storage: storage.load_page(entity_id))
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown kind")
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown entity")
    return entity


async def _save_entity(request: Request, kind: str, entity: Article | Page, author: str) -> None:
    if isinstance(entity, Article):
        await _save_article(request, entity, author)
    else:
        await _save_page(request, entity, author)


@router.post("/{kind}/{entity_id}")
async def move_to_trash(
    request: Request,
    kind: str,
    entity_id: str,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
) -> RedirectResponse:
    user, _ = user_session
    entity = await _load_entity(request, kind, entity_id)
    entity.deleted_at = datetime.now(UTC)
    await _save_entity(request, kind, entity, user.username)
    await audit_record(request, user.username, "trashed", kind, entity_id)
    return RedirectResponse("/trash", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{kind}/{entity_id}/restore")
async def restore_from_trash(
    request: Request,
    kind: str,
    entity_id: str,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
) -> RedirectResponse:
    user, _ = user_session
    entity = await _load_entity(request, kind, entity_id)
    entity.deleted_at = None
    await _save_entity(request, kind, entity, user.username)
    await audit_record(request, user.username, "restored", kind, entity_id)
    destination = admin_path(f"{kind}s", entity.id)
    return RedirectResponse(destination, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{kind}/{entity_id}/purge")
async def purge_forever(
    request: Request,
    kind: str,
    entity_id: str,
    _admin: Annotated[User, Depends(_REQUIRE_ADMIN)],
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
) -> RedirectResponse:
    """The panel's only hard delete — admin role, trash-only."""
    entity = await _load_entity(request, kind, entity_id)
    if entity.deleted_at is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="only trashed content can be purged"
        )
    if kind == "article":
        await get_db(request).run(lambda storage: storage.delete_article(entity_id))
    else:
        await get_db(request).run(lambda storage: storage.delete_page(entity_id))
    actor, _session = user_session
    await audit_record(request, actor.username, "purged", kind, entity_id)
    return RedirectResponse("/trash", status_code=status.HTTP_303_SEE_OTHER)
