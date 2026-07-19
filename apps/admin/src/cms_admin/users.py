"""Users screen (M5): manage accounts from the panel, admin role only.

The CLI (`cms admin create-user`) stays the bootstrap path — the first
account always comes from there. Safeguards: you cannot delete yourself,
and the last admin can neither be deleted nor demoted.
"""

import re
from datetime import UTC, datetime
from typing import Annotated

from cms_core import Language, Role, StorageBackend, User
from cms_core.accounts import USERNAME_PATTERN, AdminSession
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from cms_admin.auth import ROLE_ORDER, current_session, enforce_csrf, get_db, require_at_least
from cms_admin.security import hash_password

router = APIRouter(prefix="/users")

_REQUIRE_ADMIN = require_at_least(Role.ADMIN)

HTTP_422 = status.HTTP_422_UNPROCESSABLE_CONTENT


def _load_users(storage: StorageBackend) -> list[User]:
    users = [storage.load_user(name) for name in storage.list_usernames()]
    return [user for user in users if user is not None]


def _admin_count(users: list[User]) -> int:
    return sum(1 for user in users if user.role is Role.ADMIN)


async def _page(request: Request, context: dict[str, object], status_code: int = 200) -> object:
    users = await get_db(request).run(_load_users)
    return request.app.state.templates.TemplateResponse(
        request,
        "users.html.j2",
        {
            "active_section": "users",
            "users": users,
            "roles": [role.value for role in ROLE_ORDER],
            "languages": [language.value for language in Language],
            **context,
        },
        status_code=status_code,
    )


@router.get("")
async def users_list(
    request: Request,
    _admin: Annotated[User, Depends(_REQUIRE_ADMIN)],
    user_session: tuple[User, AdminSession] = Depends(current_session),
) -> object:
    user, session = user_session
    return await _page(request, {"user": user, "csrf_token": session.csrf_token, "errors": []})


@router.post("")
async def user_create(
    request: Request,
    _admin: Annotated[User, Depends(_REQUIRE_ADMIN)],
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    username: str = Form(""),
    password: str = Form(""),
    role: str = Form("editor"),
    language: str = Form(""),
) -> object:
    user, session = user_session
    errors: list[str] = []
    name = username.strip().lower()
    if not re.fullmatch(USERNAME_PATTERN, name):
        errors.append("username: lowercase letters, digits and dashes only")
    if len(password) < 12:
        errors.append("password: at least 12 characters")
    try:
        account_role = Role(role)
    except ValueError:
        errors.append("role: unknown role")
        account_role = Role.EDITOR
    preference: Language | None = None
    if language:
        try:
            preference = Language(language)
        except ValueError:
            errors.append("language: unknown language")
    db = get_db(request)
    if not errors and await db.run(lambda storage: storage.load_user(name)) is not None:
        errors.append("username: already taken")
    if errors:
        return await _page(
            request,
            {"user": user, "csrf_token": session.csrf_token, "errors": errors},
            status_code=HTTP_422,
        )
    account = User(
        username=name,
        password_hash=hash_password(password),
        role=account_role,
        created_at=datetime.now(UTC),
        language=preference,
    )
    await db.run(lambda storage: storage.save_user(account))
    return RedirectResponse("/users", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{username}/role")
async def user_role(
    request: Request,
    username: str,
    _admin: Annotated[User, Depends(_REQUIRE_ADMIN)],
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    role: str = Form(...),
) -> object:
    user, session = user_session
    db = get_db(request)
    account = await db.run(lambda storage: storage.load_user(username))
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown user")
    try:
        new_role = Role(role)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="unknown role"
        ) from error
    users = await db.run(_load_users)
    if account.role is Role.ADMIN and new_role is not Role.ADMIN and _admin_count(users) <= 1:
        return await _page(
            request,
            {
                "user": user,
                "csrf_token": session.csrf_token,
                "errors": ["role: the last admin cannot be demoted"],
            },
            status_code=HTTP_422,
        )
    updated = account.model_copy(update={"role": new_role})
    await db.run(lambda storage: storage.save_user(updated))
    return RedirectResponse("/users", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{username}/delete")
async def user_delete(
    request: Request,
    username: str,
    _admin: Annotated[User, Depends(_REQUIRE_ADMIN)],
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
) -> object:
    user, session = user_session
    db = get_db(request)
    account = await db.run(lambda storage: storage.load_user(username))
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown user")
    errors: list[str] = []
    if account.username == user.username:
        errors.append("delete: you cannot delete your own account")
    users = await db.run(_load_users)
    if account.role is Role.ADMIN and _admin_count(users) <= 1:
        errors.append("delete: the last admin cannot be deleted")
    if errors:
        return await _page(
            request,
            {"user": user, "csrf_token": session.csrf_token, "errors": errors},
            status_code=HTTP_422,
        )
    await db.run(lambda storage: storage.delete_user(username))
    return RedirectResponse("/users", status_code=status.HTTP_303_SEE_OTHER)
