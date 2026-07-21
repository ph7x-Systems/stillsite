"""Global admin search (#129): one box finds anything an editor edits.

The query runs at the storage layer (LIKE overrides per engine; the
portable base default for third-party backends) and the results render
server-side, grouped by kind, each hit linking straight to its editor.
Trashed entries never appear — the search finds what the lists show.
"""

from cms_core import AdminSession, User
from fastapi import APIRouter, Depends, Query, Request

from cms_admin.auth import current_session, get_db

router = APIRouter()

EDITOR_LINKS = {
    "article": lambda hit: f"/articles/{hit.id}",
    "page": lambda hit: f"/pages/{hit.id}",
    "section": lambda hit: "/pages/{}/sections/{}".format(*hit.id.split("/", 1)),
    "media": lambda hit: f"/media/{hit.id}",
}
KIND_ORDER = ("article", "page", "section", "media")


@router.get("/search")
async def search(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(current_session),
    q: str = Query(""),
) -> object:
    user, session = user_session
    needle = q.strip()
    hits = []
    if needle:
        hits = await get_db(request).run(lambda storage: storage.search_content(needle))
    groups = [
        (
            kind,
            [
                {"title": hit.title, "detail": hit.detail, "url": EDITOR_LINKS[kind](hit)}
                for hit in hits
                if hit.kind == kind
            ],
        )
        for kind in KIND_ORDER
    ]
    return request.app.state.templates.TemplateResponse(
        request,
        "search.html.j2",
        {
            "user": user,
            "csrf_token": session.csrf_token,
            "active_section": "search",
            "q": needle,
            "groups": [(kind, rows) for kind, rows in groups if rows],
            "total": len(hits),
        },
    )
