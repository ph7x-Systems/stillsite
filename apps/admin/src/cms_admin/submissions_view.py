"""The Submissions screen: stored form submissions, readable.

Admin-only. The operational fields filter (which form, date window);
the visitor's values display as an opaque payload — the screen never
depends on user-defined field keys. Deletion is definitive; the
retention policy (``[forms] retention_days``) prunes at startup.
"""

from datetime import UTC, datetime, timedelta

from cms_core import AdminSession, Role, User
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse

from cms_admin.audit import record as audit_record
from cms_admin.auth import current_session, enforce_csrf, get_db

router = APIRouter()


def _parse_day(raw: str, *, end: bool = False) -> datetime | None:
    if not raw.strip():
        return None
    try:
        moment = datetime.fromisoformat(raw.strip()).replace(tzinfo=UTC)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="dates are YYYY-MM-DD") from error
    return moment.replace(hour=23, minute=59, second=59) if end else moment


def _require_admin(user: User) -> None:
    if user.role is not Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin role required")


@router.get("/submissions")
async def submissions_view(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(current_session),
    form_id: str = Query(""),
    since: str = Query(""),
    until: str = Query(""),
) -> object:
    user, session = user_session
    _require_admin(user)
    page_id, _, section_key = form_id.partition("/")
    submissions = await get_db(request).run(
        lambda storage: storage.list_form_submissions(
            limit=100,
            page_id=page_id.strip() or None,
            section_key=section_key.strip() or None,
            since=_parse_day(since),
            until=_parse_day(until, end=True),
        )
    )
    return request.app.state.templates.TemplateResponse(
        request,
        "submissions.html.j2",
        {
            "user": user,
            "csrf_token": session.csrf_token,
            "active_section": "submissions",
            "submissions": submissions,
            "form_id": form_id,
            "since": since,
            "until": until,
        },
    )


@router.post("/submissions/{submission_id}/delete")
async def submission_delete(
    request: Request,
    submission_id: str,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
) -> RedirectResponse:
    user, _ = user_session
    _require_admin(user)
    removed = await get_db(request).run(
        lambda storage: storage.delete_form_submission(submission_id)
    )
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown submission")
    await audit_record(request, user.username, "deleted", "submission", submission_id)
    return RedirectResponse("/submissions", status_code=status.HTTP_303_SEE_OTHER)


async def apply_forms_retention(app: object) -> None:
    """Prune stored submissions per the project's retention setting."""
    from cms_cli.project import load_project

    try:
        project = load_project(app.state.settings.project_dir)  # type: ignore[attr-defined]
    except FileNotFoundError:
        return
    days = project.forms_retention_days
    if days <= 0:
        return
    cutoff = datetime.now(tz=UTC) - timedelta(days=days)
    try:
        await app.state.db.run(  # type: ignore[attr-defined]
            lambda storage: storage.prune_form_submissions(cutoff)
        )
    except Exception:  # pragma: no cover
        import logging

        logging.getLogger("cms_admin.forms").exception("submission pruning failed")


__all__ = ["apply_forms_retention", "router"]
