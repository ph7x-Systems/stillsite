"""Bulk actions (#130): the same rules as single actions, many at once.

One POST applies a workflow transition, a trash/restore move or a
category assignment to every selected entry. Nothing is looser in
bulk: each entry passes the exact per-entry checks — transition
validity from its own status, the actor's role, the publish gate with
the project's language set — and the report lists every outcome, the
refused ones with their reason. A failure never aborts the rest.
"""

import re
from datetime import UTC, datetime

from cms_cli.project import Project
from cms_core import AdminSession, Article, ContentStatus, Page, User
from cms_validation import SiteContent
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError

from cms_admin.articles import _load_article, _save_article
from cms_admin.auth import enforce_csrf, get_db
from cms_admin.i18n import translate
from cms_admin.notifications import notify_transition
from cms_admin.pages import _load_page, _save_page
from cms_admin.publishing import _project, _site_source, _site_targets
from cms_admin.webhooks import emit_transition
from cms_admin.workflow import allowed, publish_blockers, transition_minimum

router = APIRouter()

WORKFLOW_ACTIONS = {
    "to-draft": ContentStatus.DRAFT,
    "to-review": ContentStatus.REVIEW,
    "publish": ContentStatus.PUBLISHED,
    "archive": ContentStatus.ARCHIVED,
}
CATEGORY_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


async def _gate_content(request: Request) -> SiteContent:
    db = get_db(request)
    return SiteContent(
        articles=[a for a in await db.run(lambda s: s.load_all_articles()) if a.deleted_at is None],
        pages=[p for p in await db.run(lambda s: s.load_all_pages()) if p.deleted_at is None],
        media=await db.run(lambda s: s.load_all_media_assets()),
    )


@router.post("/{kind}/bulk")
async def bulk_apply(
    request: Request,
    kind: str,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
) -> object:
    user, session = user_session
    if kind not in ("articles", "pages", "media"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown kind")
    form = await request.form()
    action = str(form.get("action", ""))
    category = str(form.get("category", "")).strip()
    selected = [str(value) for value in form.getlist("selected")]
    if kind == "media":
        known_actions: tuple[str, ...] = ("delete",)
    else:
        known_actions = (*WORKFLOW_ACTIONS, "trash", "restore") + (
            ("set-category",) if kind == "articles" else ()
        )
    if action not in known_actions:
        raise HTTPException(status_code=400, detail="unknown action")
    if not selected:
        return _report(request, user, session, kind, action, [])

    gate = None
    if action == "publish" and request.app.state.settings.publish_gate:
        gate = await _gate_content(request)
    project = _project(request)
    outcomes: list[tuple[str, str]] = []
    for entity_id in selected:
        try:
            outcome = await _apply_one(
                request, user, kind, entity_id, action, category, gate, project
            )
        except HTTPException:
            outcome = translate(request, "not found")
        outcomes.append((entity_id, outcome))
    return _report(request, user, session, kind, action, outcomes)


async def _apply_one(
    request: Request,
    user: User,
    kind: str,
    entity_id: str,
    action: str,
    category: str,
    gate: SiteContent | None,
    project: "Project | None",
) -> str:
    if kind == "media":
        return await _delete_media(request, entity_id)
    entity: Article | Page
    if kind == "articles":
        entity = await _load_article(request, entity_id)
    else:
        entity = await _load_page(request, entity_id)

    if action == "trash":
        entity.deleted_at = datetime.now(UTC)
        await _save(request, kind, entity, user.username)
        return "ok"
    if action == "restore":
        entity.deleted_at = None
        await _save(request, kind, entity, user.username)
        return "ok"
    if action == "set-category":
        if not CATEGORY_PATTERN.match(category):
            return translate(request, "category: lowercase-with-dashes")
        try:
            updated = entity.model_copy(update={"category": category})
        except ValidationError:
            return translate(request, "category: lowercase-with-dashes")
        await _save(request, kind, updated, user.username)
        return "ok"

    target = WORKFLOW_ACTIONS[action]
    minimum = transition_minimum(entity.status, target)
    if minimum is None:
        return translate(request, "invalid transition from %(status)s") % {
            "status": entity.status.value
        }
    if not allowed(user.role, minimum):
        return translate(request, "requires the %(role)s role") % {"role": minimum.value}
    if gate is not None and target is ContentStatus.PUBLISHED:
        blockers = publish_blockers(
            entity,
            gate,
            required_languages=_site_targets(project),
            source=_site_source(project),
        )
        if blockers:
            return translate(request, "publish gate: %(count)s validation error(s)") % {
                "count": len(blockers)
            }
    previous = entity.status
    entity.status = target
    entity.updated_at = datetime.now(UTC)
    await _save(request, kind, entity, user.username)
    emit_transition(
        request, kind=kind.rstrip("s"), entity_id=entity.id, before=previous, after=target
    )
    title = entity.source.title
    await notify_transition(
        request,
        section=kind,
        entity_id=entity.id,
        title=title,
        target=target,
        actor=user.username,
    )
    return "ok"


async def _save(request: Request, kind: str, entity: Article | Page, author: str) -> None:
    if isinstance(entity, Article):
        await _save_article(request, entity, author)
    else:
        await _save_page(request, entity, author)


async def _delete_media(request: Request, asset_id: str) -> str:
    from cms_admin.media import asset_references

    db = get_db(request)
    asset = await db.run(lambda storage: storage.load_media_asset(asset_id))
    if asset is None:
        return translate(request, "not found")
    articles = await db.run(lambda storage: storage.load_all_articles())
    pages = await db.run(lambda storage: storage.load_all_pages())
    references = asset_references(asset_id, articles, pages)
    if references:
        return translate(request, "referenced by %(count)s entr(ies)") % {"count": len(references)}
    await db.run(lambda storage: storage.delete_media_asset(asset_id))
    return "ok"


def _report(
    request: Request,
    user: User,
    session: AdminSession,
    kind: str,
    action: str,
    outcomes: list[tuple[str, str]],
) -> object:
    applied = sum(1 for _id, outcome in outcomes if outcome == "ok")
    return request.app.state.templates.TemplateResponse(
        request,
        "bulk_report.html.j2",
        {
            "user": user,
            "active_section": kind,
            "csrf_token": session.csrf_token,
            "kind": kind,
            "action": action,
            "outcomes": outcomes,
            "applied": applied,
            "back_url": f"/{kind}",
        },
    )
