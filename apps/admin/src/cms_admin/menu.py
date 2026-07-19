"""Menu manager (M6): explicit navigation from the panel.

Defined items replace the derived menu entirely on the next build; with
none, the derived menu (home anchors + blog + published pages) keeps
working. Upserting an existing id updates it — that is also how items
reorder.
"""

from cms_core import Language, MenuItem, Role, User
from cms_core.accounts import AdminSession
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from cms_admin.auth import current_session, enforce_csrf, get_db, require_at_least

router = APIRouter(prefix="/menu")

_REQUIRE_PUBLISHER = require_at_least(Role.PUBLISHER)

HTTP_422 = status.HTTP_422_UNPROCESSABLE_CONTENT


async def _page(request: Request, context: dict[str, object], status_code: int = 200) -> object:
    items = await get_db(request).run(lambda storage: storage.load_menu_items())
    return request.app.state.templates.TemplateResponse(
        request,
        "menu.html.j2",
        {
            "active_section": "menu",
            "items": items,
            "languages": list(Language),
            **context,
        },
        status_code=status_code,
    )


@router.get("")
async def menu_list(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(current_session),
) -> object:
    user, session = user_session
    return await _page(request, {"user": user, "csrf_token": session.csrf_token, "errors": []})


@router.post("")
async def menu_save(
    request: Request,
    _role: tuple[User, AdminSession] = Depends(_REQUIRE_PUBLISHER),
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
) -> object:
    user, session = user_session
    form = await request.form()
    labels = {
        language: str(form.get(f"label_{language.value}", "")).strip()
        for language in Language
        if str(form.get(f"label_{language.value}", "")).strip()
    }
    try:
        item = MenuItem(
            id=str(form.get("id", "")).strip(),
            url=str(form.get("url", "")).strip(),
            position=int(str(form.get("position", "0") or "0")),
            labels=labels,
        )
    except (ValueError, TypeError):
        return await _page(
            request,
            {
                "user": user,
                "csrf_token": session.csrf_token,
                "errors": ["menu: id is lowercase-with-dashes, url and position are required"],
            },
            status_code=HTTP_422,
        )
    await get_db(request).run(lambda storage: storage.save_menu_item(item))
    return RedirectResponse("/menu", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{item_id}/delete")
async def menu_delete(
    request: Request,
    item_id: str,
    _role: tuple[User, AdminSession] = Depends(_REQUIRE_PUBLISHER),
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
) -> RedirectResponse:
    deleted = await get_db(request).run(lambda storage: storage.delete_menu_item(item_id))
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown menu item")
    return RedirectResponse("/menu", status_code=status.HTTP_303_SEE_OTHER)
