"""The translation queue (#131): the translator's worklist.

One screen lists every entry-language pair that is missing or
outdated — for the project's configured language set, pack tags
included — filterable by language, state and content type, each row
linking straight to the side-by-side editor. Zero rows is a real
statement: everything is caught up. States come from the model's
checksums, never from flags, so the queue can never disagree with the
editors.
"""

from cms_core import AdminSession, Article, Page, TranslationState, User
from fastapi import APIRouter, Depends, Query, Request

from cms_admin.auth import current_session, get_db
from cms_admin.navigation import AdminScreen, register_screen
from cms_admin.publishing import _project, _site_source, _site_targets

router = APIRouter()

register_screen(AdminScreen("translations", "/translations", "Translations", "bi-translate", 50))

QUEUE_STATES = (TranslationState.MISSING, TranslationState.OUTDATED)


@router.get("/translations")
async def translation_queue(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(current_session),
    language: str = Query(""),
    state: str = Query(""),
    kind: str = Query(""),
) -> object:
    user, session = user_session
    project = _project(request)
    targets = _site_targets(project)
    source = _site_source(project)
    db = get_db(request)
    articles = [a for a in await db.run(lambda s: s.load_all_articles()) if a.deleted_at is None]
    pages = [p for p in await db.run(lambda s: s.load_all_pages()) if p.deleted_at is None]

    rows: list[dict[str, str]] = []
    entries: list[tuple[str, Article | Page]] = [
        *(("article", article) for article in articles),
        *(("page", page) for page in pages),
    ]
    for entry_kind, entry in entries:
        for target in targets:
            entry_state = entry.translation_state(target, source=source)
            if entry_state not in QUEUE_STATES:
                continue
            rows.append(
                {
                    "kind": entry_kind,
                    "id": entry.id,
                    "title": entry.source.title,
                    "language": str(target),
                    "state": entry_state.value,
                    "url": f"/{entry_kind}s/{entry.id}/translations/{target}",
                }
            )

    filtered = [
        row
        for row in rows
        if (not language or row["language"] == language)
        and (not state or row["state"] == state)
        and (not kind or row["kind"] == kind)
    ]
    filtered.sort(key=lambda row: (row["language"], row["kind"], row["id"]))
    return request.app.state.templates.TemplateResponse(
        request,
        "translations_queue.html.j2",
        {
            "user": user,
            "csrf_token": session.csrf_token,
            "active_section": "translations",
            "rows": filtered,
            "total_pending": len(rows),
            "targets": [str(target) for target in targets],
            "language": language,
            "state": state,
            "kind": kind,
        },
    )
