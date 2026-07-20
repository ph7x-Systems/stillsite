"""Editorial notes (M5): a comment trail on articles and pages.

Notes are collaboration, not content: they never publish, never export,
and vanish with the entity. Anyone signed in can write; a note's author
or an admin can remove it.
"""

from datetime import UTC, datetime

from cms_core import Role, User
from cms_core.accounts import AdminSession
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from cms_admin.auth import enforce_csrf, get_db
from cms_admin.security import admin_path

router = APIRouter(prefix="/notes")

_KINDS = {"article": "articles", "page": "pages"}


def _back_url(kind: str, entity_id: str) -> str:
    try:
        return admin_path(_KINDS[kind], entity_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown kind") from None


@router.post("/{kind}/{entity_id}")
async def note_add(
    request: Request,
    kind: str,
    entity_id: str,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    body: str = Form(""),
) -> RedirectResponse:
    user, _ = user_session
    destination = _back_url(kind, entity_id)
    text = body.strip()
    if text:
        await get_db(request).run(
            lambda storage: storage.add_note(
                kind, entity_id, user.username, text, datetime.now(UTC)
            )
        )
    return RedirectResponse(destination, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{kind}/{entity_id}/{seq}/delete")
async def note_delete(
    request: Request,
    kind: str,
    entity_id: str,
    seq: int,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
) -> RedirectResponse:
    user, _ = user_session
    destination = _back_url(kind, entity_id)
    notes = await get_db(request).run(lambda storage: storage.list_notes(kind, entity_id))
    match = next((note for note in notes if note[0] == seq), None)
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown note")
    if match[2] != user.username and user.role is not Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="only the author or an admin"
        )
    await get_db(request).run(lambda storage: storage.delete_note(kind, entity_id, seq))
    return RedirectResponse(destination, status_code=status.HTTP_303_SEE_OTHER)
