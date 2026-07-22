"""The Themes screen: discover, try, activate — never install (ADR-0048).

The list enumerates every theme the environment can activate without
loading any of them. Activation is try-first, write-second: the theme
must resolve and a trial build of the current content must succeed
before ``theme = "…"`` is written into ``[site]``; a failing theme
shows its error and the config stays untouched.
"""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

from cms_build import build_site, create_theme
from cms_build.themes import discovered_themes
from cms_core import AdminSession, Role, User
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import FileResponse, RedirectResponse

from cms_admin.audit import record as audit_record
from cms_admin.auth import current_session, enforce_csrf
from cms_admin.navigation import AdminScreen, register_screen
from cms_admin.publishing import _project, _site_content

router = APIRouter()

register_screen(AdminScreen("themes", "/themes", "Themes", "bi-palette", 82, Role.ADMIN))


def _require_admin(user: User) -> None:
    if user.role is not Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin role required")


def _write_site_theme(project_file: Path, name: str) -> None:
    """Rewrite only the ``theme`` key of ``[site]``; everything else
    stays exactly as the owner wrote it."""
    lines = project_file.read_text(encoding="utf-8").splitlines()
    in_site = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("["):
            in_site = stripped == "[site]"
            continue
        if in_site and stripped.startswith("theme"):
            lines[index] = f'theme = "{name}"'
            break
    else:
        at = next(i for i, line in enumerate(lines) if line.strip() == "[site]")
        lines.insert(at + 1, f'theme = "{name}"')
    project_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _render(
    request: Request,
    user: User,
    session: AdminSession,
    *,
    activated: str = "",
    error: str = "",
) -> object:
    project = _project(request)
    active = project.site.theme if project is not None else None
    active_error = ""
    if project is not None:
        try:
            create_theme(active or "default", overrides=project.theme_overrides)
        except Exception as failure:
            active_error = str(failure)
    return request.app.state.templates.TemplateResponse(
        request,
        "themes.html.j2",
        {
            "user": user,
            "csrf_token": session.csrf_token,
            "active_section": "themes",
            "themes": discovered_themes(),
            "active": active,
            "active_error": active_error,
            "has_project": project is not None,
            "activated": activated,
            "error": error,
        },
    )


@router.get("/themes")
async def themes_view(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(current_session),
    activated: str = "",
) -> object:
    user, session = user_session
    _require_admin(user)
    # `activated` reflects only an allowlisted theme name, never raw input.
    known = {info.name for info in discovered_themes()}
    return _render(request, user, session, activated=activated if activated in known else "")


@router.get("/themes/screenshot/{name}")
async def theme_screenshot(
    name: str,
    user_session: tuple[User, AdminSession] = Depends(current_session),
) -> FileResponse:
    user, _session = user_session
    _require_admin(user)
    info = next((t for t in discovered_themes() if t.name == name), None)
    if info is None or info.screenshot is None:
        raise HTTPException(status_code=404, detail="no screenshot")
    media_types = {".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp"}
    media_type = media_types.get(info.screenshot.suffix.lower())
    if media_type is None:
        raise HTTPException(status_code=404, detail="no screenshot")
    return FileResponse(info.screenshot, media_type=media_type)


@router.post("/themes/activate")
async def theme_activate(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    name: str = Form(...),
) -> object:
    user, session = user_session
    _require_admin(user)
    project = _project(request)
    if project is None:
        raise HTTPException(status_code=400, detail="no sardine.toml in the project directory")

    def _failed(message: str) -> object:
        # Failures render in place: no user-influenced value enters a redirect.
        return _render(request, user, session, error=message[:300])

    # The redirect target uses the allowlisted name from discovery, never raw input.
    safe_name = next((info.name for info in discovered_themes() if info.name == name), None)
    if safe_name is None:
        return _failed(f"unknown theme {name[:60]!r}")

    try:
        theme = create_theme(safe_name, overrides=project.theme_overrides)
    except Exception as failure:
        return _failed(str(failure))

    content = await _site_content(request)
    trial_config = project.site.model_copy(update={"theme": safe_name})
    try:
        await asyncio.to_thread(
            build_site,
            trial_config,
            content,
            theme=theme,
            media_files=project.collect_media_files(),
            now=datetime.now(UTC),
        )
    except Exception as failure:
        return _failed(str(failure))

    _write_site_theme(project.directory / "sardine.toml", safe_name)
    await audit_record(request, user.username, "activated", "theme", safe_name)
    return RedirectResponse(
        f"/themes?activated={quote(safe_name)}", status_code=status.HTTP_303_SEE_OTHER
    )


__all__ = ["router"]
