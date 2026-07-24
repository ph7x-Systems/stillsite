"""Articles: list, create, and the side-by-side translation editor.

The EN source is edited on the article page; each translation is edited next
to a read-only view of the source it translates (the checksum model marks it
outdated automatically when the source changes afterwards). The preview uses
the builder's own Markdown renderer, so what an editor sees is exactly what
the published site will render — raw HTML stays disabled.
"""

import difflib
from datetime import UTC, datetime
from pathlib import Path

from cms_build import render_markdown, urls
from cms_core import (
    AdminSession,
    Article,
    ArticleContent,
    ContentStatus,
    Language,
    Role,
    StorageBackend,
    TranslationState,
    User,
    new_article,
)
from cms_core.translatable import Seo
from cms_validation import SiteContent
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import ValidationError

from cms_admin.audit import record as audit_record
from cms_admin.auth import current_session, enforce_csrf, get_db
from cms_admin.navigation import AdminScreen, register_screen
from cms_admin.notifications import notify_transition
from cms_admin.preview_links import links_context
from cms_admin.publishing import _project, _site_source, _site_targets, refresh_entry_preview
from cms_admin.redirects import record_slug_redirects
from cms_admin.security import admin_path
from cms_admin.webhooks import emit_transition
from cms_admin.workflow import (
    allowed,
    available_transitions,
    publish_blockers,
    transition_minimum,
)

router = APIRouter(prefix="/articles")

register_screen(AdminScreen("articles", "/articles", "Articles", "bi-journal-text", 20))

HTTP_422 = status.HTTP_422_UNPROCESSABLE_CONTENT


def _form_error_list(error: ValueError) -> list[str]:
    if isinstance(error, ValidationError):
        return form_errors(error)
    return ["publish_at: use the picker format (YYYY-MM-DDTHH:MM, UTC)"]


def form_errors(error: ValidationError) -> list[str]:
    return [
        f"{'.'.join(str(part) for part in item['loc']) or 'form'}: {item['msg']}"
        for item in error.errors()
    ]


def parse_tags(raw: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def parse_publish_at(raw: str) -> datetime | None:
    """The datetime-local input submits YYYY-MM-DDTHH:MM; naive means UTC
    (ADR-0024 — the panel schedules in UTC, as the field label says)."""
    if not raw.strip():
        return None
    moment = datetime.fromisoformat(raw.strip())
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def publish_at_form(value: datetime | None) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M") if value else ""


def content_form(content: ArticleContent | None) -> dict[str, str]:
    seo = content.seo if content else None
    return {
        "title": content.title if content else "",
        "summary": content.summary if content else "",
        "body_markdown": content.body_markdown if content else "",
        "slug": (content.slug or "") if content else "",
        "seo_title": seo.seo_title if seo else "",
        "seo_description": seo.seo_description if seo else "",
        "noindex": "1" if (seo and seo.noindex) else "",
        "canonical": seo.canonical if seo else "",
        "og_image": seo.og_image if seo else "",
    }


def _target_language(request: Request, code: str) -> Language:
    try:
        language = Language(code)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="unknown language"
        ) from None
    if language is _site_source(_project(request)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="the source language is edited on the article page",
        )
    return language


async def _save_article(
    request: Request, article: Article, author: str, *, revision: bool = True
) -> None:
    """Persist and append the revision snapshot (ADR-0025) atomically-ish:
    the snapshot records exactly what was saved."""
    payload = article.model_dump_json()
    when = datetime.now(UTC)

    def run(storage: StorageBackend) -> None:
        storage.save_article(article)
        if revision:
            storage.save_revision("article", article.id, author, payload, when)

    await get_db(request).run(run)


async def _load_article(request: Request, article_id: str) -> Article:
    article = await get_db(request).run(lambda storage: storage.load_article(article_id))
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown article")
    return article


async def _picker_context(request: Request) -> dict[str, object]:
    """Library images for the cover picker (#136), with the widest
    configured responsive width so undersized sources are flagged."""
    assets = await get_db(request).run(lambda storage: storage.load_all_media_assets())
    project = _project(request)
    widths = project.site.image_widths if project else ()
    return {
        "image_assets": [asset for asset in assets if asset.is_image],
        "picker_widest": max(widths) if widths else 0,
    }


def _page(
    request: Request, template: str, context: dict[str, object], status_code: int = 200
) -> object:
    return request.app.state.templates.TemplateResponse(
        request, template, {"active_section": "articles", **context}, status_code=status_code
    )


@router.get("")
async def articles_list(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(current_session),
    needs: str = Query(""),
) -> object:
    user, session = user_session
    everything = await get_db(request).run(lambda storage: storage.load_all_articles())
    articles = [a for a in everything if a.deleted_at is None]
    trashed_count = len(everything) - len(articles)
    project = _project(request)
    targets = _site_targets(project)
    # #131: "entries missing «tag»" — keep only entries whose state for
    # the picked language is not complete.
    if needs and needs in {str(target) for target in targets}:
        source = _site_source(project)
        articles = [
            article
            for article in articles
            if article.translation_state(Language(needs), source=source)
            is not TranslationState.COMPLETE
        ]
    row_actions_map = {
        article.id: available_transitions(article.status, user.role) for article in articles
    }
    return _page(
        request,
        "articles_list.html.j2",
        {
            "user": user,
            "csrf_token": session.csrf_token,
            "articles": articles,
            "trashed_count": trashed_count,
            "row_actions_map": row_actions_map,
            "target_languages": targets,
            "needs": needs,
        },
    )


@router.get("/new")
async def article_new_form(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(current_session),
) -> object:
    user, session = user_session
    form = {"id": "", "category": "", "tags": "", "cover": "", **content_form(None)}
    return _page(
        request,
        "article_new.html.j2",
        {"user": user, "csrf_token": session.csrf_token, "errors": [], "form": form}
        | await _picker_context(request),
    )


def _seo_from_form(form: dict[str, str]) -> Seo:
    """The editor's SEO card (ADR-0041); absent fields mean derived."""
    return Seo(
        seo_title=form.get("seo_title", "").strip(),
        seo_description=form.get("seo_description", "").strip(),
        noindex=bool(form.get("noindex", "").strip()),
        canonical=form.get("canonical", "").strip(),
        og_image=form.get("og_image", "").strip(),
    )


def _validated_article(base: Article, form: dict[str, str]) -> Article:
    """Rebuild the article from the form and run every model validator once."""
    payload = base.model_dump()
    payload.update(
        source=ArticleContent(
            title=form["title"],
            summary=form["summary"],
            body_markdown=form["body_markdown"],
            slug=form["slug"] or None,
            seo=_seo_from_form(form),
        ).model_dump(),
        category=form["category"] or None,
        cover=form["cover"] or None,
        tags=parse_tags(form["tags"]),
        publish_at=parse_publish_at(form.get("publish_at", "")),
        unpublish_at=parse_publish_at(form.get("unpublish_at", "")),
        author=form.get("author", "").strip() or None,
        featured=bool(form.get("featured")),
        updated_at=datetime.now(UTC),
    )
    return Article.model_validate(payload)


@router.post("")
async def article_create(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    article_id: str = Form(alias="id"),
    title: str = Form(""),
    summary: str = Form(""),
    body_markdown: str = Form(""),
    slug: str = Form(""),
    category: str = Form(""),
    tags: str = Form(""),
    cover: str = Form(""),
    cover_pick: str = Form("__keep__"),
    seo_title: str = Form(""),
    seo_description: str = Form(""),
    noindex: str = Form(""),
    canonical: str = Form(""),
    og_image: str = Form(""),
    publish_at: str = Form(""),
    unpublish_at: str = Form(""),
    author: str = Form(""),
    featured: str = Form(""),
) -> object:
    user, session = user_session
    db = get_db(request)
    if cover_pick == "__none__":
        cover = ""  # the picker's explicit clear (#136)
    elif cover_pick != "__keep__":
        cover = cover_pick  # the picker wins over the text field (#136)
    form = {
        "id": article_id,
        "title": title,
        "summary": summary,
        "body_markdown": body_markdown,
        "slug": slug,
        "category": category,
        "tags": tags,
        "cover": cover,
        "publish_at": publish_at,
        "unpublish_at": unpublish_at,
        "author": author,
        "featured": featured,
        "seo_title": seo_title,
        "seo_description": seo_description,
        "noindex": noindex,
        "canonical": canonical,
        "og_image": og_image,
    }
    try:
        base = new_article(article_id, ArticleContent(title=title or "-"))
        article = _validated_article(base, form)
    except ValueError as error:
        errors = _form_error_list(error)
    else:
        existing = await db.run(lambda storage: storage.load_article(article_id))
        if existing is None:
            await _save_article(request, article, user.username)
            return RedirectResponse(
                admin_path("articles", article.id), status_code=status.HTTP_303_SEE_OTHER
            )
        errors = [f"id: an article with id {article_id!r} already exists"]
    return _page(
        request,
        "article_new.html.j2",
        {"user": user, "csrf_token": session.csrf_token, "errors": errors, "form": form}
        | await _picker_context(request),
        status_code=HTTP_422,
    )


BLANK_CUSTOM_ROWS = 2


def _custom_rows(article: Article) -> list[dict[str, str]]:
    rows = [{"name": name, "value": value} for name, value in sorted(article.fields.items())]
    rows.extend({"name": "", "value": ""} for _ in range(BLANK_CUSTOM_ROWS))
    return rows


def _editor_context(
    request: Request,
    article: Article,
    form: dict[str, str] | None = None,
    role: Role | None = None,
) -> dict[str, object]:
    project = _project(request)
    targets = _site_targets(project)
    source = _site_source(project)
    return {
        "custom_rows": _custom_rows(article),
        "article": article,
        "transitions": available_transitions(article.status, role) if role else [],
        "states": article.translation_states(targets, source=source),
        "target_languages": targets,
        "preview_html": render_markdown(article.source.body_markdown),
        "form": form
        or {
            **content_form(article.source),
            "category": article.category or "",
            "tags": ", ".join(article.tags),
            "cover": article.cover or "",
            "publish_at": publish_at_form(article.publish_at),
            "unpublish_at": publish_at_form(article.unpublish_at),
            "author": article.author or "",
            "featured": "1" if article.featured else "",
        },
    }


@router.get("/{article_id}")
async def article_edit_form(
    request: Request,
    article_id: str,
    user_session: tuple[User, AdminSession] = Depends(current_session),
) -> object:
    user, session = user_session
    article = await _load_article(request, article_id)
    revisions = await get_db(request).run(
        lambda storage: storage.list_revisions("article", article_id)
    )
    notes = await get_db(request).run(lambda storage: storage.list_notes("article", article_id))
    project = _project(request)
    preview_path = (
        "/preview" + urls.article_path(project.site, article, _site_source(project))
        if project
        else None
    )
    preview_ready = bool(
        preview_path
        and (
            Path(request.app.state.preview_dir)
            / preview_path.removeprefix("/preview/").rstrip("/")
            / "index.html"
        ).is_file()
    )
    return _page(
        request,
        "article_edit.html.j2",
        {
            "user": user,
            "csrf_token": session.csrf_token,
            "errors": [],
            "revisions": revisions,
            "notes": notes,
            "note_kind": "article",
            "entity_id": article_id,
            "preview_path": preview_path,
            "preview_ready": preview_ready,
            **_editor_context(request, article, role=user.role),
            **await _picker_context(request),
            **await links_context(request, "article", article_id),
        },
    )


@router.post("/{article_id}")
async def article_edit_save(
    request: Request,
    article_id: str,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    title: str = Form(""),
    summary: str = Form(""),
    body_markdown: str = Form(""),
    slug: str = Form(""),
    category: str = Form(""),
    tags: str = Form(""),
    cover: str = Form(""),
    cover_pick: str = Form("__keep__"),
    seo_title: str = Form(""),
    seo_description: str = Form(""),
    noindex: str = Form(""),
    canonical: str = Form(""),
    og_image: str = Form(""),
    publish_at: str = Form(""),
    unpublish_at: str = Form(""),
    author: str = Form(""),
    featured: str = Form(""),
) -> object:
    user, session = user_session
    article = await _load_article(request, article_id)
    raw = await request.form()
    names = [str(value) for value in raw.getlist("custom_name")]
    values = [str(value) for value in raw.getlist("custom_value")]
    custom_fields = {
        name.strip(): value
        for name, value in zip(names, values, strict=False)
        if name.strip() and value
    }
    if cover_pick == "__none__":
        cover = ""  # the picker's explicit clear (#136)
    elif cover_pick != "__keep__":
        cover = cover_pick  # the picker wins over the text field (#136)
    form = {
        "title": title,
        "summary": summary,
        "body_markdown": body_markdown,
        "slug": slug,
        "category": category,
        "tags": tags,
        "cover": cover,
        "publish_at": publish_at,
        "unpublish_at": unpublish_at,
        "author": author,
        "featured": featured,
        "seo_title": seo_title,
        "seo_description": seo_description,
        "noindex": noindex,
        "canonical": canonical,
        "og_image": og_image,
    }
    before = article.model_copy(deep=True)
    try:
        article = _validated_article(article, form)
        article = article.model_copy(update={"fields": custom_fields})
    except ValueError as error:
        return _page(
            request,
            "article_edit.html.j2",
            {
                "user": user,
                "csrf_token": session.csrf_token,
                "errors": _form_error_list(error),
                **_editor_context(request, article, form, role=user.role),
                **await _picker_context(request),
            },
            status_code=HTTP_422,
        )
    await _save_article(request, article, user.username)
    await record_slug_redirects(request, before, article)
    return RedirectResponse(
        admin_path("articles", article.id), status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/{article_id}/autosave")
async def article_autosave(
    request: Request,
    article_id: str,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    title: str = Form(""),
    summary: str = Form(""),
    body_markdown: str = Form(""),
    slug: str = Form(""),
    category: str = Form(""),
    tags: str = Form(""),
    cover: str = Form(""),
    cover_pick: str = Form("__keep__"),
    seo_title: str = Form(""),
    seo_description: str = Form(""),
    noindex: str = Form(""),
    canonical: str = Form(""),
    og_image: str = Form(""),
    publish_at: str = Form(""),
    unpublish_at: str = Form(""),
    author: str = Form(""),
    featured: str = Form(""),
) -> object:
    """Persist a valid debounced draft without consuming revision history."""
    user, _ = user_session
    article = await _load_article(request, article_id)
    raw = await request.form()
    names = [str(value) for value in raw.getlist("custom_name")]
    values = [str(value) for value in raw.getlist("custom_value")]
    custom_fields = {
        name.strip(): value
        for name, value in zip(names, values, strict=False)
        if name.strip() and value
    }
    if cover_pick == "__none__":
        cover = ""  # the picker's explicit clear (#136)
    elif cover_pick != "__keep__":
        cover = cover_pick  # the picker wins over the text field (#136)
    form = {
        "title": title,
        "summary": summary,
        "body_markdown": body_markdown,
        "slug": slug,
        "category": category,
        "tags": tags,
        "cover": cover,
        "publish_at": publish_at,
        "unpublish_at": unpublish_at,
        "author": author,
        "featured": featured,
        "seo_title": seo_title,
        "seo_description": seo_description,
        "noindex": noindex,
        "canonical": canonical,
        "og_image": og_image,
    }
    try:
        article = _validated_article(article, form)
        article = article.model_copy(update={"fields": custom_fields})
    except ValueError as error:
        return JSONResponse({"ok": False, "errors": _form_error_list(error)}, status_code=HTTP_422)
    await _save_article(request, article, user.username, revision=False)
    preview_path = await refresh_entry_preview(request, article)
    return {"ok": True, "preview_path": preview_path}


def _translation_context(
    article: Article, language: Language, form: dict[str, str] | None = None
) -> dict[str, object]:
    translation = article.translations.get(language)
    content = translation.content if translation else None
    return {
        "article": article,
        "language": language,
        "state": article.translation_state(language),
        "source_preview_html": render_markdown(article.source.body_markdown),
        "preview_html": render_markdown(content.body_markdown) if content else "",
        "form": form or content_form(content),
        "can_suggest": False,
    }


@router.post("/{article_id}/translations/{language_code}/suggest")
async def translation_suggest(
    request: Request,
    article_id: str,
    language_code: str,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
) -> object:
    """Generate a translation suggestion for one article (ADR-0054).

    The suggestion lands as draft content in the existing state machine;
    nothing is published. Without a provider configured, the action is
    not offered. A provider failure is contained and audited.
    """
    user, session = user_session
    language = _target_language(request, language_code)
    article = await _load_article(request, article_id)
    project = _project(request)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="project not found"
        )
    if not project.translations_provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="no translation provider configured"
        )
    project.load_extensions()
    from cms_core.translations import TranslationRequest, create_translation_provider

    try:
        provider = create_translation_provider(project.translations_provider)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    request_obj = TranslationRequest(
        source_text=article.source.body_markdown,
        source_language=str(_site_source(project)),
        target_language=language_code,
        context=article.source.title,
        glossary=(
            project.glossary_for(language_code) if provider.capabilities.supports_glossary else ()
        ),
    )
    try:
        suggestions = provider.suggest([request_obj])
    except Exception as error:
        await audit_record(
            request,
            user.username,
            "translation-provider-failed",
            "article",
            article_id,
            project.translations_provider,
        )
        return _page(
            request,
            "article_translation.html.j2",
            {
                "user": user,
                "csrf_token": session.csrf_token,
                "errors": [f"provider failed: {error}"],
                **_translation_context(article, language),
            },
            status_code=status.HTTP_502_BAD_GATEWAY,
        )
    if not suggestions or not suggestions[0].target_text:
        return _page(
            request,
            "article_translation.html.j2",
            {
                "user": user,
                "csrf_token": session.csrf_token,
                "errors": ["provider returned no suggestion"],
                **_translation_context(article, language),
            },
            status_code=status.HTTP_502_BAD_GATEWAY,
        )
    suggested = suggestions[0].target_text
    form = {
        "title": article.source.title,
        "summary": article.source.summary,
        "body_markdown": suggested,
        "slug": "",
    }
    await audit_record(
        request,
        user.username,
        "translation-suggested",
        "article",
        article_id,
        language_code,
    )
    return _page(
        request,
        "article_translation.html.j2",
        {
            "user": user,
            "csrf_token": session.csrf_token,
            "errors": [],
            **_translation_context(article, language, form),
        },
    )


@router.get("/{article_id}/translations/{language_code}")
async def translation_form(
    request: Request,
    article_id: str,
    language_code: str,
    user_session: tuple[User, AdminSession] = Depends(current_session),
) -> object:
    user, session = user_session
    language = _target_language(request, language_code)
    article = await _load_article(request, article_id)
    context = _translation_context(article, language)
    project = _project(request)
    if project is not None and project.translations_provider:
        context["can_suggest"] = True
    return _page(
        request,
        "article_translation.html.j2",
        {
            "user": user,
            "csrf_token": session.csrf_token,
            "errors": [],
            **context,
        },
    )


@router.post("/{article_id}/translations/{language_code}")
async def translation_save(
    request: Request,
    article_id: str,
    language_code: str,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    title: str = Form(""),
    summary: str = Form(""),
    body_markdown: str = Form(""),
    slug: str = Form(""),
) -> object:
    user, session = user_session
    language = _target_language(request, language_code)
    article = await _load_article(request, article_id)
    form = {"title": title, "summary": summary, "body_markdown": body_markdown, "slug": slug}
    try:
        content = ArticleContent(
            title=title, summary=summary, body_markdown=body_markdown, slug=slug or None
        )
    except ValidationError as error:
        return _page(
            request,
            "article_translation.html.j2",
            {
                "user": user,
                "csrf_token": session.csrf_token,
                "errors": form_errors(error),
                **_translation_context(article, language, form),
            },
            status_code=HTTP_422,
        )
    article.set_translation(language, content)
    article.updated_at = datetime.now(UTC)
    await _save_article(request, article, user.username)
    return RedirectResponse(
        admin_path("articles", article.id, "translations", language.value),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/{article_id}/status")
async def article_status(
    request: Request,
    article_id: str,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    to: str = Form(...),
) -> object:
    user, session = user_session
    article = await _load_article(request, article_id)
    try:
        target = ContentStatus(to)
    except ValueError:
        raise HTTPException(status_code=400, detail="unknown status") from None
    minimum = transition_minimum(article.status, target)
    if minimum is None:
        raise HTTPException(status_code=400, detail="invalid transition")
    if not allowed(user.role, minimum):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"requires the {minimum.value} role",
        )
    if target is ContentStatus.PUBLISHED and request.app.state.settings.publish_gate:
        db = get_db(request)
        all_articles = await db.run(lambda storage: storage.load_all_articles())
        all_pages = await db.run(lambda storage: storage.load_all_pages())
        content = SiteContent(
            articles=[a for a in all_articles if a.deleted_at is None],
            pages=[entry for entry in all_pages if entry.deleted_at is None],
            media=await db.run(lambda storage: storage.load_all_media_assets()),
        )
        gate_project = _project(request)
        blockers = publish_blockers(
            article,
            content,
            required_languages=_site_targets(gate_project),
            source=_site_source(gate_project),
        )
        if blockers:
            return _page(
                request,
                "article_edit.html.j2",
                {
                    "user": user,
                    "csrf_token": session.csrf_token,
                    "errors": blockers,
                    **_editor_context(request, article, role=user.role),
                },
                status_code=HTTP_422,
            )
    previous = article.status
    article.status = target
    article.updated_at = datetime.now(UTC)
    await _save_article(request, article, user.username)
    emit_transition(request, kind="article", entity_id=article.id, before=previous, after=target)
    await audit_record(
        request, user.username, target.value, "article", article.id, f"from {previous.value}"
    )
    if ContentStatus.PUBLISHED in (previous, target):
        # #156: publish and unpublish end on the public site — the
        # configured provider redeploys automatically (no-op without one).
        from cms_admin.deploy import run_deploy

        await run_deploy(request, user.username)
    await notify_transition(
        request,
        section="articles",
        entity_id=article.id,
        title=article.source.title,
        target=target,
        actor=user.username,
    )
    return RedirectResponse(
        admin_path("articles", article.id), status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/{article_id}/revisions/{revision}")
async def article_revision_detail(
    request: Request,
    article_id: str,
    revision: int,
    user_session: tuple[User, AdminSession] = Depends(current_session),
) -> object:
    user, session = user_session
    article = await _load_article(request, article_id)
    payload = await get_db(request).run(
        lambda storage: storage.load_revision("article", article_id, revision)
    )
    if payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown revision")
    snapshot = Article.model_validate_json(payload)
    diff = "\n".join(
        difflib.unified_diff(
            snapshot.source.body_markdown.splitlines(),
            article.source.body_markdown.splitlines(),
            fromfile=f"revision {revision}",
            tofile="current",
            lineterm="",
        )
    )
    return _page(
        request,
        "revision_detail.html.j2",
        {
            "user": user,
            "csrf_token": session.csrf_token,
            "active_section": "articles",
            "entity_id": article.id,
            "back_url": f"/articles/{article.id}",
            "restore_url": f"/articles/{article.id}/revisions/{revision}/restore",
            "snapshot_title": snapshot.source.title,
            "revision": revision,
            "diff": diff,
        },
    )


@router.post("/{article_id}/revisions/{revision}/restore")
async def article_revision_restore(
    request: Request,
    article_id: str,
    revision: int,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
) -> RedirectResponse:
    """Restore = validate the snapshot back through the model and save,
    which records a new revision — a restore is itself undoable."""
    user, _ = user_session
    await _load_article(request, article_id)  # 404 before touching history
    payload = await get_db(request).run(
        lambda storage: storage.load_revision("article", article_id, revision)
    )
    if payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown revision")
    restored = Article.model_validate_json(payload)
    restored = restored.model_copy(update={"id": article_id, "updated_at": datetime.now(UTC)})
    await _save_article(request, restored, user.username)
    return RedirectResponse(
        admin_path("articles", restored.id), status_code=status.HTTP_303_SEE_OTHER
    )


def _copy_id(base_id: str, taken: set[str]) -> str:
    candidate = f"{base_id}-copy"
    counter = 2
    while candidate in taken:
        candidate = f"{base_id}-copy-{counter}"
        counter += 1
    return candidate


@router.post("/{article_id}/duplicate")
async def article_duplicate(
    request: Request,
    article_id: str,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
) -> RedirectResponse:
    """Duplicate as draft (M5): same content and metadata, fresh identity,
    no schedule, no trash flag — ready to edit."""
    user, _ = user_session
    article = await _load_article(request, article_id)
    taken = set(await get_db(request).run(lambda storage: storage.list_article_ids()))
    now = datetime.now(UTC)
    copy = article.model_copy(
        update={
            "id": _copy_id(article_id, taken),
            "status": ContentStatus.DRAFT,
            "publish_at": None,
            "deleted_at": None,
            "created_at": now,
            "updated_at": now,
        }
    )
    await _save_article(request, copy, user.username)
    return RedirectResponse(admin_path("articles", copy.id), status_code=status.HTTP_303_SEE_OTHER)
