"""The editorial calendar (#132): the month as the panel sees time.

Published entries appear on their publication day, scheduled entries on
the day their ``publish_at`` will fire — all in UTC, exactly as the
panel schedules (ADR-0024; the screen says so). Scheduled chips drag to
another day as a progressive enhancement posting a server-validated
move; every chip links to its editor, where the date field remains the
no-JS path.
"""

import calendar as calendar_module
from datetime import UTC, datetime

from cms_core import AdminSession, Article, Page, User
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse

from cms_admin.articles import _load_article, _save_article
from cms_admin.auth import current_session, enforce_csrf, get_db
from cms_admin.navigation import AdminScreen, register_screen
from cms_admin.pages import _load_page, _save_page

router = APIRouter()

register_screen(AdminScreen("calendar", "/calendar", "Calendar", "bi-calendar3", 60))


def _month_argument(raw: str) -> tuple[int, int]:
    try:
        year, month = raw.split("-", 1)
        moment = datetime(int(year), int(month), 1, tzinfo=UTC)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="month must be YYYY-MM") from error
    return moment.year, moment.month


def _entry_day(entry: Article | Page) -> datetime:
    return entry.publish_at or entry.created_at


@router.get("/calendar")
async def calendar_view(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(current_session),
    month: str = Query(""),
) -> object:
    user, session = user_session
    now = datetime.now(tz=UTC)
    year, month_number = _month_argument(month) if month else (now.year, now.month)
    db = get_db(request)
    articles = [a for a in await db.run(lambda s: s.load_all_articles()) if a.deleted_at is None]
    pages = [p for p in await db.run(lambda s: s.load_all_pages()) if p.deleted_at is None]

    chips: dict[int, list[dict[str, object]]] = {}
    entries: list[tuple[str, Article | Page]] = [
        *(("article", article) for article in articles),
        *(("page", page) for page in pages),
    ]
    for kind, entry in entries:
        moment = _entry_day(entry)
        if entry.status.value not in ("published", "review", "draft"):
            continue
        scheduled = entry.publish_at is not None and entry.publish_at > now
        if entry.status.value != "published" and not scheduled:
            continue  # drafts/review appear only when actually scheduled
        if moment.year != year or moment.month != month_number:
            continue
        chips.setdefault(moment.day, []).append(
            {
                "kind": kind,
                "id": entry.id,
                "title": entry.source.title,
                "scheduled": scheduled,
                "time": moment.strftime("%H:%M"),
                "url": f"/{kind}s/{entry.id}",
            }
        )
    for day_chips in chips.values():
        day_chips.sort(key=lambda chip: (str(chip["time"]), str(chip["id"])))

    weeks = calendar_module.Calendar().monthdayscalendar(year, month_number)
    previous_year, previous_month = (year, month_number - 1) if month_number > 1 else (year - 1, 12)
    next_year, next_month = (year, month_number + 1) if month_number < 12 else (year + 1, 1)
    return request.app.state.templates.TemplateResponse(
        request,
        "calendar.html.j2",
        {
            "user": user,
            "csrf_token": session.csrf_token,
            "active_section": "calendar",
            "year": year,
            "month": month_number,
            "weeks": weeks,
            "chips": chips,
            "previous": f"{previous_year:04d}-{previous_month:02d}",
            "next": f"{next_year:04d}-{next_month:02d}",
            "today": now.day if (now.year, now.month) == (year, month_number) else 0,
        },
    )


@router.post("/calendar/reschedule")
async def reschedule(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    kind: str = Form(...),
    entity_id: str = Form(...),
    day: str = Form(...),
) -> RedirectResponse:
    """Move a *scheduled* entry to another day, keeping its time of day.

    Published-without-schedule entries are history, not plans — they
    refuse to move; the entry editor's date field remains the precise
    (and no-JS) path."""
    user, _ = user_session
    if kind not in ("article", "page"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown kind")
    entity: Article | Page = (
        await _load_article(request, entity_id)
        if kind == "article"
        else await _load_page(request, entity_id)
    )
    if entity.publish_at is None or entity.publish_at <= datetime.now(tz=UTC):
        raise HTTPException(status_code=400, detail="only scheduled entries move")
    try:
        target = datetime.fromisoformat(day).replace(tzinfo=UTC)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="day must be YYYY-MM-DD") from error
    entity.publish_at = entity.publish_at.replace(
        year=target.year, month=target.month, day=target.day
    )
    if kind == "article":
        await _save_article(request, entity, user.username)  # type: ignore[arg-type]
    else:
        await _save_page(request, entity, user.username)  # type: ignore[arg-type]
    from cms_admin.audit import record as audit_record

    await audit_record(request, user.username, "rescheduled", kind, entity_id, day)
    month_argument = f"{target.year:04d}-{target.month:02d}"
    return RedirectResponse(
        f"/calendar?month={month_argument}", status_code=status.HTTP_303_SEE_OTHER
    )
