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
    SOURCE_LANGUAGE,
    AdminSession,
    Article,
    ArticleContent,
    ContentStatus,
    Language,
    Role,
    StorageBackend,
    User,
    new_article,
)
from cms_core.languages import TARGET_LANGUAGES
from cms_validation import SiteContent
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import ValidationError

from cms_admin.auth import current_session, enforce_csrf, get_db
from cms_admin.publishing import _project
from cms_admin.workflow import (
    allowed,
    available_transitions,
    publish_blockers,
    transition_minimum,
)

router = APIRouter(prefix="/articles")

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
    if content is None:
        return {"title": "", "summary": "", "body_markdown": "", "slug": ""}
    return {
        "title": content.title,
        "summary": content.summary,
        "body_markdown": content.body_markdown,
        "slug": content.slug or "",
    }


def _target_language(code: str) -> Language:
    try:
        language = Language(code)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="unknown language"
        ) from None
    if language is SOURCE_LANGUAGE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="the source language is edited on the article page",
        )
    return language


async def _save_article(request: Request, article: Article, author: str) -> None:
    """Persist and append the revision snapshot (ADR-0025) atomically-ish:
    the snapshot records exactly what was saved."""
    payload = article.model_dump_json()
    when = datetime.now(UTC)

    def run(storage: StorageBackend) -> None:
        storage.save_article(article)
        storage.save_revision("article", article.id, author, payload, when)

    await get_db(request).run(run)


async def _load_article(request: Request, article_id: str) -> Article:
    article = await get_db(request).run(lambda storage: storage.load_article(article_id))
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown article")
    return article


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
) -> object:
    user, session = user_session
    everything = await get_db(request).run(lambda storage: storage.load_all_articles())
    articles = [a for a in everything if a.deleted_at is None]
    trashed_count = len(everything) - len(articles)
    return _page(
        request,
        "articles_list.html.j2",
        {
            "user": user,
            "csrf_token": session.csrf_token,
            "articles": articles,
            "trashed_count": trashed_count,
            "target_languages": TARGET_LANGUAGES,
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
        {"user": user, "csrf_token": session.csrf_token, "errors": [], "form": form},
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
        ).model_dump(),
        category=form["category"] or None,
        cover=form["cover"] or None,
        tags=parse_tags(form["tags"]),
        publish_at=parse_publish_at(form.get("publish_at", "")),
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
    publish_at: str = Form(""),
    author: str = Form(""),
    featured: str = Form(""),
) -> object:
    user, session = user_session
    db = get_db(request)
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
        "author": author,
        "featured": featured,
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
                f"/articles/{article.id}", status_code=status.HTTP_303_SEE_OTHER
            )
        errors = [f"id: an article with id {article_id!r} already exists"]
    return _page(
        request,
        "article_new.html.j2",
        {"user": user, "csrf_token": session.csrf_token, "errors": errors, "form": form},
        status_code=HTTP_422,
    )


def _editor_context(
    article: Article, form: dict[str, str] | None = None, role: Role | None = None
) -> dict[str, object]:
    return {
        "article": article,
        "transitions": available_transitions(article.status, role) if role else [],
        "states": article.translation_states(),
        "target_languages": TARGET_LANGUAGES,
        "preview_html": render_markdown(article.source.body_markdown),
        "form": form
        or {
            **content_form(article.source),
            "category": article.category or "",
            "tags": ", ".join(article.tags),
            "cover": article.cover or "",
            "publish_at": publish_at_form(article.publish_at),
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
    project = _project(request)
    preview_path = (
        "/preview" + urls.article_path(project.site, article, SOURCE_LANGUAGE) if project else None
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
            "preview_path": preview_path,
            "preview_ready": preview_ready,
            **_editor_context(article, role=user.role),
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
    publish_at: str = Form(""),
    author: str = Form(""),
    featured: str = Form(""),
) -> object:
    user, session = user_session
    article = await _load_article(request, article_id)
    form = {
        "title": title,
        "summary": summary,
        "body_markdown": body_markdown,
        "slug": slug,
        "category": category,
        "tags": tags,
        "cover": cover,
        "publish_at": publish_at,
        "author": author,
        "featured": featured,
    }
    try:
        article = _validated_article(article, form)
    except ValueError as error:
        return _page(
            request,
            "article_edit.html.j2",
            {
                "user": user,
                "csrf_token": session.csrf_token,
                "errors": _form_error_list(error),
                **_editor_context(article, form, role=user.role),
            },
            status_code=HTTP_422,
        )
    await _save_article(request, article, user.username)
    return RedirectResponse(f"/articles/{article.id}", status_code=status.HTTP_303_SEE_OTHER)


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
    }


@router.get("/{article_id}/translations/{language_code}")
async def translation_form(
    request: Request,
    article_id: str,
    language_code: str,
    user_session: tuple[User, AdminSession] = Depends(current_session),
) -> object:
    user, session = user_session
    language = _target_language(language_code)
    article = await _load_article(request, article_id)
    return _page(
        request,
        "article_translation.html.j2",
        {
            "user": user,
            "csrf_token": session.csrf_token,
            "errors": [],
            **_translation_context(article, language),
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
    language = _target_language(language_code)
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
        f"/articles/{article.id}/translations/{language.value}",
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
        blockers = publish_blockers(article, content)
        if blockers:
            return _page(
                request,
                "article_edit.html.j2",
                {
                    "user": user,
                    "csrf_token": session.csrf_token,
                    "errors": blockers,
                    **_editor_context(article, role=user.role),
                },
                status_code=HTTP_422,
            )
    article.status = target
    article.updated_at = datetime.now(UTC)
    await _save_article(request, article, user.username)
    return RedirectResponse(f"/articles/{article.id}", status_code=status.HTTP_303_SEE_OTHER)


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
    return RedirectResponse(f"/articles/{article_id}", status_code=status.HTTP_303_SEE_OTHER)


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
    return RedirectResponse(f"/articles/{copy.id}", status_code=status.HTTP_303_SEE_OTHER)
