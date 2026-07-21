"""The Activity screen (#134): the audit trail, readable.

Admin-only: who did what, when — filtered by actor and date window,
newest first. Records survive the deletion of what they describe; the
retention policy (SARDINE_ACTIVITY_RETENTION_DAYS) prunes at startup.
"""

from datetime import UTC, datetime

from cms_core import AdminSession, Role, User
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from cms_admin.auth import current_session, get_db
from cms_admin.navigation import AdminScreen, register_screen

router = APIRouter()

register_screen(
    AdminScreen("activity", "/activity", "Activity", "bi-clock-history", 70, Role.ADMIN)
)


def _parse_day(raw: str, *, end: bool = False) -> datetime | None:
    if not raw.strip():
        return None
    try:
        moment = datetime.fromisoformat(raw.strip()).replace(tzinfo=UTC)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="dates are YYYY-MM-DD") from error
    return moment.replace(hour=23, minute=59, second=59) if end else moment


@router.get("/activity")
async def activity_view(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(current_session),
    actor: str = Query(""),
    since: str = Query(""),
    until: str = Query(""),
) -> object:
    user, session = user_session
    if user.role is not Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin role required")
    records = await get_db(request).run(
        lambda storage: storage.list_activity(
            limit=100,
            actor=actor.strip() or None,
            since=_parse_day(since),
            until=_parse_day(until, end=True),
        )
    )
    return request.app.state.templates.TemplateResponse(
        request,
        "activity.html.j2",
        {
            "user": user,
            "csrf_token": session.csrf_token,
            "active_section": "activity",
            "records": records,
            "actor": actor,
            "since": since,
            "until": until,
        },
    )
