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

from cms_build import build_entry_preview, build_site, create_target, urls
from cms_cli.project import Project, load_project
from cms_core import SOURCE_LANGUAGE, Article, Language, Page, Role, StorageBackend, User
from cms_core.accounts import AdminSession
from cms_core.extensions import ExtensionError
from cms_core.languages import TARGET_LANGUAGES
from cms_validation import SiteContent
from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse

from cms_admin.auth import current_session, enforce_csrf, get_db, require_at_least
from cms_admin.validation_report import report_context, run_report

router = APIRouter(prefix="/publishing")

TARGETS = ("generic", "swa", "nginx")


def persist_target(project_file: Path, target: str) -> None:
    """Remember the chosen deployment target in ``sardine.toml``
    (format-preserving: only the ``target`` line changes)."""
    text = project_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    in_build = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("["):
            in_build = stripped == "[build]"
            continue
        if in_build and stripped.startswith("target"):
            lines[index] = f'target = "{target}"'
            break
    else:
        if "[build]" in {line.strip() for line in lines}:
            at = next(i for i, line in enumerate(lines) if line.strip() == "[build]")
            lines.insert(at + 1, f'target = "{target}"')
        else:
            lines.extend(["", "[build]", f'target = "{target}"'])
    project_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
            articles=[a for a in storage.load_all_articles() if a.deleted_at is None],
            pages=[p for p in storage.load_all_pages() if p.deleted_at is None],
            media=storage.load_all_media_assets(),
            menu=storage.load_menu_items(),
        )

    return await get_db(request).run(load)


def _project(request: Request) -> Project | None:
    try:
        return load_project(request.app.state.settings.project_dir)
    except FileNotFoundError:
        return None


def _site_source(project: Project | None) -> Language:
    """ADR-0034: the project's configured source; the constant is only
    the no-project fallback."""
    return project.site.source_language if project is not None else SOURCE_LANGUAGE


def _site_targets(project: Project | None) -> tuple[Language, ...]:
    return tuple(project.site.languages) if project is not None else TARGET_LANGUAGES


def _extension_rules(project: Project | None) -> tuple[object, ...]:
    if project is None:
        return ()
    return tuple(
        rule for extension in project.load_extensions() for rule in extension.validation_rules
    )


def _write_artifact(files: dict[str, bytes], output: Path) -> int:
    for path, data in files.items():
        target = output / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return len(files)


async def refresh_entry_preview(request: Request, entry: Article | Page) -> str | None:
    """Render one saved entry into /preview/ through the active theme.

    The lock makes overlapping debounced requests converge on the newest
    stored value. Content is loaded after acquiring it for that reason.
    """
    project = _project(request)
    if project is None:
        return None
    async with request.app.state.preview_lock:
        content = await _site_content(request)
        if isinstance(entry, Article):
            current_article = next(
                (item for item in content.articles if item.id == entry.id), entry
            )
            preview_path = "/preview" + urls.article_path(
                project.site, current_article, _site_source(project)
            )
            preview_entry: Article | Page = current_article
        else:
            current_page = next((item for item in content.pages if item.id == entry.id), entry)
            preview_path = "/preview" + urls.page_path(
                current_page, _site_source(project), source=_site_source(project)
            )
            preview_entry = current_page
        artifact = await asyncio.to_thread(
            build_entry_preview,
            project.site,
            content,
            preview_entry,
            media_files=project.collect_media_files(),
            now=datetime.now(UTC),
            comments_provider=project.resolve_comments_provider(),
        )
        _write_artifact(artifact.files, Path(request.app.state.preview_dir))
        return preview_path


@router.get("")
async def publishing_home(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(current_session),
) -> object:
    user, session = user_session
    project = _project(request)
    content = await _site_content(request)
    languages = _site_targets(project)
    return request.app.state.templates.TemplateResponse(
        request,
        "publishing.html.j2",
        {
            "active_section": "publishing",
            "user": user,
            "csrf_token": session.csrf_token,
            "project": project,
            "project_dir": str(request.app.state.settings.project_dir.resolve()),
            **report_context(
                content,
                tuple(languages),
                _extension_rules(project),
                source_language=_site_source(project),
            ),
            "targets": TARGETS,
            "current_target": project.target if project else "generic",
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
    async with request.app.state.preview_lock:
        content = await _site_content(request)
        try:
            comments_provider = project.resolve_comments_provider()
        except ExtensionError as error:
            _record(request, "preview", ok=False, detail=str(error))
            return _redirect()
        artifact = await asyncio.to_thread(
            build_site,
            project.site,
            content,
            media_files=project.collect_media_files(),
            now=datetime.now(UTC),
            comments_provider=comments_provider,
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
    target: str = Form(""),
) -> object:
    project = _project(request)
    if project is None:
        _record(request, "build", ok=False, detail="no sardine.toml in the project directory")
        return _redirect()
    target = target or project.target
    if target not in TARGETS:
        _record(request, "build", ok=False, detail=f"unknown target {target!r}")
        return _redirect()
    content = await _site_content(request)
    report = run_report(content, tuple(project.site.languages), _extension_rules(project))
    if not report.ok:
        _record(
            request,
            "build",
            ok=False,
            detail=f"validation blocked the build: {len(report.errors)} error(s)",
        )
        return _redirect()
    try:
        comments_provider = project.resolve_comments_provider()
    except ExtensionError as error:
        _record(request, "build", ok=False, detail=str(error))
        return _redirect()
    artifact = await asyncio.to_thread(
        build_site,
        project.site,
        content,
        media_files=project.collect_media_files(),
        now=datetime.now(UTC),
        comments_provider=comments_provider,
    )
    for extension in sorted(project.load_extensions(), key=lambda e: e.name):
        for step in extension.build_steps:
            step(project.site, content, artifact)
    extras = create_target(target).extra_files(project.site, artifact)
    files = {**artifact.files, **dict(extras)}
    pages = _write_artifact(files, project.output)
    if target != project.target:
        # An explicit choice is remembered — the CLI shares it.
        persist_target(project.directory / "sardine.toml", target)
    _record(
        request,
        f"build ({target})",
        target=target,
        output=str(project.output),
        ok=True,
        files=pages,
        digest=artifact.digest()[:12],
        detail=f"written to {project.output}",
    )
    return _redirect()
