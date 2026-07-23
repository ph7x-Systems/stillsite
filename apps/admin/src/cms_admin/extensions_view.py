"""The Extensions screen (ADR-0050): packaging for discovery, runtime
for capabilities, configuration for control.

Discovery imports nothing; an active extension's capabilities come from
its loaded ``Extension`` object; activation is transactional (isolated
load, then a trial build, only then the config write); deactivation
operates directly on the configuration and never imports the extension
it removes — the recovery path works precisely when the import fails.
"""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from cms_build import build_site
from cms_core import AdminSession, Role, User
from cms_core.extensions import discovered_extensions, load_extensions, run_health_check
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from cms_admin.audit import record as audit_record
from cms_admin.auth import current_session, enforce_csrf
from cms_admin.navigation import AdminScreen, register_screen
from cms_admin.publishing import _project, _site_content

router = APIRouter()

register_screen(AdminScreen("extensions", "/extensions", "Extensions", "bi-plugin", 83, Role.ADMIN))


def _require_admin(user: User) -> None:
    if user.role is not Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin role required")


def _write_extensions(project_file: Path, names: list[str]) -> None:
    """Rewrite only the top-level ``extensions`` list; the rest of the
    file stays exactly as the owner wrote it."""
    lines = project_file.read_text(encoding="utf-8").splitlines()
    rendered = "extensions = [" + ", ".join(f'"{name}"' for name in names) + "]"
    for index, line in enumerate(lines):
        if line.strip().startswith("extensions"):
            if names:
                lines[index] = rendered
            else:
                del lines[index]
            break
    else:
        if names:
            at = next(
                (i for i, line in enumerate(lines) if line.strip().startswith("[")), len(lines)
            )
            lines.insert(at, rendered)
            lines.insert(at + 1, "")
    project_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _capabilities(extension: Any) -> list[str]:
    """What the loaded Extension object actually declares — never
    inferred, never invented (ADR-0050)."""
    labels: list[str] = []
    for mapping, label in (
        (extension.section_kinds, "section kinds"),
        (extension.targets, "deployment targets"),
        (extension.storage_backends, "storage backends"),
        (extension.themes, "themes"),
        (extension.deploy_providers, "deploy providers"),
        (extension.forms_providers, "forms providers"),
        (extension.comments_providers, "comments providers"),
        (extension.mail_transports, "mail transports"),
    ):
        if mapping:
            labels.append(f"{label}: {', '.join(sorted(mapping))}")
    if extension.validation_rules:
        labels.append(f"validation rules: {len(extension.validation_rules)}")
    if extension.language_packs:
        labels.append(f"language packs: {len(extension.language_packs)}")
    if extension.build_steps:
        labels.append(f"build steps: {len(extension.build_steps)}")
    if extension.cli is not None:
        labels.append("cli commands")
    return labels


def _render(
    request: Request,
    user: User,
    session: AdminSession,
    *,
    notice: str = "",
    error: str = "",
    health_for: str = "",
) -> object:
    project = _project(request)
    active_names = list(project.extension_names) if project is not None else []
    cards: list[dict[str, Any]] = []
    seen: set[str] = set()
    for info in discovered_extensions():
        seen.add(info.name)
        cards.append({"info": info, "active": info.name in active_names})
    for name in active_names:
        if name not in seen:
            cards.append({"info": None, "name": name, "active": True})
    for card in cards:
        if not card["active"]:
            continue
        name = card["info"].name if card["info"] else card["name"]
        try:
            (extension,) = load_extensions([name])
            card["capabilities"] = _capabilities(extension)
            card["load_error"] = ""
            card["has_health"] = extension.health_check is not None
            if name == health_for:
                card["health"] = list(run_health_check(extension))
        except Exception as failure:
            card["capabilities"] = []
            card["load_error"] = str(failure)
            card["has_health"] = False
    return request.app.state.templates.TemplateResponse(
        request,
        "extensions.html.j2",
        {
            "user": user,
            "csrf_token": session.csrf_token,
            "active_section": "extensions",
            "cards": cards,
            "has_project": project is not None,
            "notice": notice,
            "error": error,
        },
    )


@router.get("/extensions")
async def extensions_view(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(current_session),
    notice: str = "",
) -> object:
    user, session = user_session
    _require_admin(user)
    allowed = {"activated", "deactivated"}
    return _render(request, user, session, notice=notice if notice in allowed else "")


async def _trial_build(request: Request, project: Any, names: list[str]) -> None:
    """The activation trial: the would-be extension set must build the
    current content (ADR-0050 guarantee 3)."""
    from cms_build import create_theme

    extensions = load_extensions(names)
    content = await _site_content(request)
    theme = create_theme(project.site.theme, overrides=project.theme_overrides)
    section_kinds: dict[str, object] = {}
    for extension in sorted(extensions, key=lambda e: e.name):
        section_kinds.update(extension.section_kinds)
    artifact = await asyncio.to_thread(
        build_site,
        project.site,
        content,
        theme=theme,
        media_files=project.collect_media_files(),
        now=datetime.now(UTC),
        section_kinds=section_kinds,  # type: ignore[arg-type]
    )
    for extension in sorted(extensions, key=lambda e: e.name):
        for step in extension.build_steps:
            step(project.site, content, artifact)


@router.post("/extensions/health")
async def extension_health(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    name: str = Form(...),
) -> object:
    user, session = user_session
    _require_admin(user)
    project = _project(request)
    active = list(project.extension_names) if project is not None else []
    # Health runs only for active extensions; the results render in
    # place (ADR-0051) — checks may touch networks, so the operator
    # decides when they run.
    if name not in active:
        raise HTTPException(status_code=404, detail="not active")
    return _render(request, user, session, health_for=name)


@router.post("/extensions/activate")
async def extension_activate(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    name: str = Form(...),
) -> object:
    user, session = user_session
    _require_admin(user)
    project = _project(request)
    if project is None:
        raise HTTPException(status_code=400, detail="no sardine.toml in the project directory")
    name = name.strip()
    active = list(project.extension_names)
    if not name or name in active:
        return _render(request, user, session, error="already active" if name else "empty name")
    try:
        load_extensions([name])  # isolated load: this extension alone
        await _trial_build(request, project, [*active, name])
    except Exception as failure:
        return _render(request, user, session, error=str(failure)[:300])
    _write_extensions(project.directory / "sardine.toml", [*active, name])
    await audit_record(request, user.username, "activated", "extension", name)
    return RedirectResponse(
        f"/extensions?notice={quote('activated')}", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/extensions/deactivate")
async def extension_deactivate(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    name: str = Form(...),
) -> RedirectResponse:
    user, _session = user_session
    _require_admin(user)
    project = _project(request)
    if project is None:
        raise HTTPException(status_code=400, detail="no sardine.toml in the project directory")
    active = list(project.extension_names)
    if name not in active:
        raise HTTPException(status_code=404, detail="not active")
    # Recovery operates on configuration alone: the extension is never
    # imported here, so this works precisely when its import fails.
    _write_extensions(project.directory / "sardine.toml", [n for n in active if n != name])
    await audit_record(request, user.username, "deactivated", "extension", name)
    return RedirectResponse(
        f"/extensions?notice={quote('deactivated')}", status_code=status.HTTP_303_SEE_OTHER
    )


__all__ = ["router"]
