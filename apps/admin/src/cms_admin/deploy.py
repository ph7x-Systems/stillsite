"""Panel deployment (#156, slice 1): publish ends on the public site.

With ``[deploy] root`` configured, every workflow transition into or
out of ``published`` runs the full flow — build, validate, immutable
release, atomic activation, health check — through the filesystem
provider, under one lock. Failures preserve the healthy version and
surface an actionable error with retry; rollback reactivates a kept
release without rebuilding. Everything lands in the audit trail.
"""

import asyncio
import contextlib
import logging
from datetime import UTC, datetime
from typing import Annotated

from cms_build import build_site
from cms_build.deploy import (
    DeployError,
    DeployLocked,
    DeployProvider,
    DeployState,
    create_deploy_provider,
)
from cms_cli.project import Project
from cms_core import AdminSession, Article, Page, StorageBackend, User
from fastapi import APIRouter, Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from cms_admin.audit import record as audit_record
from cms_admin.auth import enforce_csrf
from cms_admin.publishing import (
    _REQUIRE_PUBLISHER,
    _extension_rules,
    _project,
    _site_content,
    _site_source,
    _site_targets,
)
from cms_admin.validation_report import run_report

logger = logging.getLogger("cms_admin.deploy")

router = APIRouter()


def build_deployer(project: "Project | None") -> "DeployProvider | None":
    """The configured provider, resolved through the registry — the
    editor never knows which (#156). Extensions register additional
    destinations on activation; the contract version is validated at
    selection, never at deploy time."""
    if project is None or not project.deploy_settings.get("root"):
        return None
    with contextlib.suppress(Exception):
        project.load_extensions()  # extension providers register here
    try:
        return create_deploy_provider(
            project.deploy_provider, project.deploy_settings, project.directory
        )
    except DeployError:
        logger.exception("deploy provider misconfigured")
        return None


def deployer_for(
    request: Request,
) -> tuple["DeployProvider | None", "Project | None"]:
    project = _project(request)
    return build_deployer(project), project


async def run_deploy(request: Request, actor: str) -> DeployState | None:
    """Build → validate → release → activate → health. None when the
    project has no deploy configuration (nothing changes anywhere)."""
    deployer, project = deployer_for(request)
    if deployer is None:
        return None
    content = await _site_content(request)
    report = run_report(
        content,
        tuple(_site_targets(project)),
        _extension_rules(project),
        source_language=_site_source(project),
    )
    if not report.ok:
        # Persisted, not just returned: the panel's deploy card must show
        # this failure after the redirect, with the healthy release intact.
        state = deployer.record_failure(
            f"validation blocked the release: {len(report.errors)} error(s)",
            phase="building",
            actor=actor,
        )
        await audit_record(request, actor, "deploy-failed", "site", "filesystem", state.error)
        return state
    assert project is not None  # deployer_for returned a deployer
    artifact = await asyncio.to_thread(
        build_site,
        project.site,
        content,
        media_files=project.collect_media_files(),
        now=datetime.now(tz=UTC),
    )
    digest = artifact.digest()
    active = next((r for r in deployer.releases() if r.active), None)
    if deployer.state().status == "active" and active is not None and active.digest == digest:
        return deployer.state()  # unchanged site — the live release already serves this
    try:
        state = await asyncio.to_thread(deployer.deploy, dict(artifact.files), digest, actor)
    except DeployLocked:
        # Never fail the editorial action that triggered us: the running
        # deployment will finish and write its own state.
        await audit_record(request, actor, "deploy-skipped", "site", "lock", "already running")
        return deployer.state()
    action = {"active": "deployed", "rolled-back": "deploy-rolled-back"}.get(
        state.status, "deploy-failed"
    )
    await audit_record(
        request, actor, action, "site", state.release_id or "filesystem", state.error
    )
    return state


@router.post("/publishing/deploy")
async def deploy_now(
    request: Request,
    _publisher: Annotated[User, Depends(_REQUIRE_PUBLISHER)],
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
) -> RedirectResponse:
    user, _ = user_session
    state = await run_deploy(request, user.username)
    if state is None:
        raise HTTPException(status_code=404, detail="no [deploy] configuration")
    return RedirectResponse("/publishing", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/publishing/rollback")
async def rollback_now(
    request: Request,
    _publisher: Annotated[User, Depends(_REQUIRE_PUBLISHER)],
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    release_id: str = Form(...),
) -> RedirectResponse:
    user, _ = user_session
    deployer, _project_obj = deployer_for(request)
    if deployer is None:
        raise HTTPException(status_code=404, detail="no [deploy] configuration")
    if "rollback" not in deployer.capabilities:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="the configured provider does not support rollback",
        )
    try:
        state = await asyncio.to_thread(deployer.rollback, release_id, user.username)
    except DeployLocked:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="a deployment is already running"
        ) from None
    action = "rolled-back" if state.status == "active" else "deploy-failed"
    await audit_record(request, user.username, action, "site", release_id, state.error)
    return RedirectResponse("/publishing", status_code=status.HTTP_303_SEE_OTHER)


async def scheduled_boundary_crossed(app: FastAPI, since: datetime, now: datetime) -> bool:
    def _check(storage: StorageBackend) -> bool:
        entries: list[Article | Page] = [
            *storage.load_all_articles(),
            *storage.load_all_pages(),
        ]
        for entry in entries:
            if entry.deleted_at is not None:
                continue
            for moment in (entry.publish_at, entry.unpublish_at):
                if moment is not None and since < moment <= now:
                    return True
        return False

    crossed: bool = await app.state.db.run(_check)
    return crossed


async def run_scheduled_deploys(app: FastAPI) -> None:
    """The scheduled flow (#156): when a publication window boundary
    passes, the configured provider redeploys as ``system`` — the
    editor set the moment; nobody runs a deploy by hand. One check per
    interval; the provider lock serializes with manual deploys."""
    from cms_cli.project import load_project

    interval = 60.0
    app.state.last_window_check = datetime.now(tz=UTC)
    while True:
        await asyncio.sleep(interval)
        try:
            project = load_project(app.state.settings.project_dir)
        except FileNotFoundError:
            continue
        if project.deploy_root is None:
            continue
        now = datetime.now(tz=UTC)
        since = app.state.last_window_check
        app.state.last_window_check = now
        try:
            if await scheduled_boundary_crossed(app, since, now):
                await run_deploy_for_app(app, "system")
        except Exception:  # pragma: no cover - the watcher never dies
            import logging

            logging.getLogger("cms_admin.deploy").exception("scheduled deploy failed")


async def run_deploy_for_app(app: FastAPI, actor: str) -> DeployState | None:
    """The request-free flow the watcher uses: same build, validation,
    provider and audit as the panel button."""
    from cms_cli.project import load_project
    from cms_core.activity import ActivityRecord
    from cms_validation import SiteContent

    try:
        project = load_project(app.state.settings.project_dir)
    except FileNotFoundError:
        return None
    if project.deploy_root is None:
        return None
    deployer = build_deployer(project)
    if deployer is None:
        return None

    def _load(storage: StorageBackend) -> SiteContent:
        return SiteContent(
            articles=[a for a in storage.load_all_articles() if a.deleted_at is None],
            pages=[p for p in storage.load_all_pages() if p.deleted_at is None],
            media=storage.load_all_media_assets(),
        )

    content = await app.state.db.run(_load)
    report = run_report(
        content,
        tuple(project.site.languages),
        source_language=project.site.source_language,
    )
    if not report.ok:
        state = deployer.record_failure(
            f"validation blocked the release: {len(report.errors)} error(s)",
            phase="building",
            actor=actor,
        )
    else:
        artifact = await asyncio.to_thread(
            build_site,
            project.site,
            content,
            media_files=project.collect_media_files(),
            now=datetime.now(tz=UTC),
        )
        try:
            state = await asyncio.to_thread(
                deployer.deploy, dict(artifact.files), artifact.digest(), actor
            )
        except DeployLocked:
            return deployer.state()
    action = {"active": "deployed", "rolled-back": "deploy-rolled-back"}.get(
        state.status, "deploy-failed"
    )
    entry = ActivityRecord(
        at=datetime.now(tz=UTC),
        actor=actor,
        action=action,
        subject_kind="site",
        subject_id=state.release_id or "filesystem",
        detail=state.error,
    )
    with contextlib.suppress(Exception):  # pragma: no cover - trail never blocks
        await app.state.db.run(lambda storage: storage.record_activity(entry))
    return state
