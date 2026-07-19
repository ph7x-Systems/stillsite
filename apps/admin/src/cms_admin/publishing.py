"""Publishing: preview, build and export triggered from the panel.

Builds go through `cms-build`'s public API against the project the admin
serves (SARDINE_PROJECT_DIR points at the directory holding `sardine.toml`).
The preview lands in a temporary directory served read-only under
`/preview/`; build and export write the project's output directory exactly
like the CLI. Every run is recorded in-process and shown on the dashboard.
"""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from cms_build import build_site, create_target
from cms_cli.project import Project, load_project
from cms_core import Role, StorageBackend, User
from cms_core.accounts import AdminSession
from cms_core.languages import TARGET_LANGUAGES
from cms_validation import RuleSet, SiteContent, ValidationContext, default_ruleset
from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse

from cms_admin.auth import current_session, enforce_csrf, get_db, require_at_least

router = APIRouter(prefix="/publishing")

TARGETS = ("generic", "swa", "nginx")

_REQUIRE_EDITOR = require_at_least(Role.EDITOR)
_REQUIRE_PUBLISHER = require_at_least(Role.PUBLISHER)


def _record(request: Request, kind: str, **extra: object) -> None:
    request.app.state.last_build = {
        "kind": kind,
        "when": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        **extra,
    }


async def _site_content(request: Request) -> SiteContent:
    def load(storage: StorageBackend) -> SiteContent:
        return SiteContent(
            articles=storage.load_all_articles(),
            pages=storage.load_all_pages(),
            media=storage.load_all_media_assets(),
        )

    return await get_db(request).run(load)


def _project(request: Request) -> Project | None:
    try:
        return load_project(request.app.state.settings.project_dir)
    except FileNotFoundError:
        return None


def _write_artifact(files: dict[str, bytes], output: Path) -> int:
    for path, data in files.items():
        target = output / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return len(files)


@router.get("")
async def publishing_home(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(current_session),
) -> object:
    user, session = user_session
    project = _project(request)
    content = await _site_content(request)
    languages = project.site.languages if project else TARGET_LANGUAGES
    report = RuleSet(rules=default_ruleset()).run(
        content, ValidationContext(required_languages=languages)
    )
    return request.app.state.templates.TemplateResponse(
        request,
        "publishing.html.j2",
        {
            "active_section": "publishing",
            "user": user,
            "csrf_token": session.csrf_token,
            "project": project,
            "project_dir": str(request.app.state.settings.project_dir.resolve()),
            "report": report,
            "targets": TARGETS,
            "last_build": getattr(request.app.state, "last_build", None),
        },
    )


def _redirect() -> RedirectResponse:
    return RedirectResponse("/publishing", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/preview")
async def run_preview(
    request: Request,
    _role: Annotated[User, Depends(_REQUIRE_EDITOR)],
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
) -> object:
    project = _project(request)
    if project is None:
        _record(request, "preview", ok=False, detail="no sardine.toml in the project directory")
        return _redirect()
    content = await _site_content(request)
    artifact = await asyncio.to_thread(
        build_site, project.site, content, media_files=project.collect_media_files()
    )
    preview_dir = Path(request.app.state.preview_dir)
    pages = _write_artifact(artifact.files, preview_dir)
    _record(
        request,
        "preview",
        ok=True,
        files=pages,
        digest=artifact.digest()[:12],
        detail="served under /preview/",
    )
    return _redirect()


@router.post("/build")
async def run_build(
    request: Request,
    _role: Annotated[User, Depends(_REQUIRE_PUBLISHER)],
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    target: str = Form("generic"),
) -> object:
    project = _project(request)
    if project is None:
        _record(request, "build", ok=False, detail="no sardine.toml in the project directory")
        return _redirect()
    if target not in TARGETS:
        _record(request, "build", ok=False, detail=f"unknown target {target!r}")
        return _redirect()
    content = await _site_content(request)
    report = RuleSet(rules=default_ruleset()).run(
        content, ValidationContext(required_languages=project.site.languages)
    )
    if not report.ok:
        _record(
            request,
            "build",
            ok=False,
            detail=f"validation blocked the build: {len(report.errors)} error(s)",
        )
        return _redirect()
    artifact = await asyncio.to_thread(
        build_site, project.site, content, media_files=project.collect_media_files()
    )
    extras = create_target(target).extra_files(project.site, artifact)
    files = {**artifact.files, **dict(extras)}
    pages = _write_artifact(files, project.output)
    _record(
        request,
        f"build ({target})",
        ok=True,
        files=pages,
        digest=artifact.digest()[:12],
        detail=f"written to {project.output}",
    )
    return _redirect()
