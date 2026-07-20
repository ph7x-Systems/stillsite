"""Pages: metadata, ordered typed sections, and their translations.

Sections are free-form field maps (the theme owns the meaning of each
``kind``), so the section editor is a dynamic name/value form. For the kinds
the reference theme ships, the editor suggests the field names that kind
consumes — suggestions only, never validation: any theme can define any
kind. The side-by-side translation UX mirrors the article editor: the EN
source read-only next to the translation, one field at a time.
"""

import difflib
from datetime import UTC, datetime
from pathlib import Path

from cms_build import urls
from cms_build.themes import SECTION_KIND_GALLERY
from cms_core import (
    SOURCE_LANGUAGE,
    AdminSession,
    ContentStatus,
    Language,
    Page,
    PageContent,
    Role,
    Section,
    SectionContent,
    StorageBackend,
    TranslationState,
    User,
    new_page,
)
from cms_core.languages import TARGET_LANGUAGES
from cms_core.translatable import TranslatableModel
from cms_validation import SiteContent
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import ValidationError

from cms_admin.articles import (
    _copy_id,
    _form_error_list,
    form_errors,
    parse_publish_at,
    publish_at_form,
)
from cms_admin.auth import current_session, enforce_csrf, get_db
from cms_admin.publishing import _project, refresh_entry_preview
from cms_admin.security import admin_path
from cms_admin.workflow import (
    allowed,
    available_transitions,
    publish_blockers,
    transition_minimum,
)

router = APIRouter(prefix="/pages")

HTTP_422 = status.HTTP_422_UNPROCESSABLE_CONTENT

BLANK_FIELD_ROWS = 3


def _kind_hints(request: Request) -> dict[str, tuple[str, ...]]:
    """The bundled section-kind gallery plus any kinds the project's
    extensions advertise (ADR-0028). Hints only, never validation: any
    theme can define any kind; bundled names win on collision."""
    hints = dict(SECTION_KIND_GALLERY)
    project = _project(request)
    if project is not None:
        for extension in sorted(project.load_extensions(), key=lambda e: e.name):
            for kind, fields in extension.section_kinds.items():
                hints.setdefault(kind, tuple(fields))
    return hints


def parse_media(raw: str) -> list[str]:
    return [line.strip() for line in raw.splitlines() if line.strip()]


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
            detail="the source language is edited on the page itself",
        )
    return language


async def _load_page(request: Request, page_id: str) -> Page:
    page = await get_db(request).run(lambda storage: storage.load_page(page_id))
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown page")
    return page


def _section_or_404(page: Page, key: str) -> Section:
    section = page.section(key)
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown section")
    return section


async def _save_page(request: Request, page: Page, author: str, *, revision: bool = True) -> None:
    """Persist and append the revision snapshot (ADR-0025)."""
    page.updated_at = datetime.now(UTC)
    payload = page.model_dump_json()
    when = datetime.now(UTC)

    def run(storage: StorageBackend) -> None:
        storage.save_page(page)
        if revision:
            storage.save_revision("page", page.id, author, payload, when)

    await get_db(request).run(run)


def _page_response(
    request: Request, template: str, context: dict[str, object], status_code: int = 200
) -> object:
    return request.app.state.templates.TemplateResponse(
        request, template, {"active_section": "pages", **context}, status_code=status_code
    )


def own_states(page: Page) -> dict[Language, TranslationState]:
    """The page's own content state, without the section aggregation."""
    return {
        language: TranslatableModel.translation_state(page, language)
        for language in TARGET_LANGUAGES
    }


@router.get("")
async def pages_list(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(current_session),
) -> object:
    user, session = user_session
    everything = await get_db(request).run(lambda storage: storage.load_all_pages())
    pages = [p for p in everything if p.deleted_at is None]
    trashed_count = len(everything) - len(pages)
    row_actions_map = {page.id: available_transitions(page.status, user.role) for page in pages}
    return _page_response(
        request,
        "pages_list.html.j2",
        {
            "user": user,
            "csrf_token": session.csrf_token,
            "pages": pages,
            "trashed_count": trashed_count,
            "row_actions_map": row_actions_map,
            "target_languages": TARGET_LANGUAGES,
        },
    )


@router.get("/new")
async def page_new_form(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(current_session),
) -> object:
    user, session = user_session
    form = {"id": "", "title": "", "description": "", "slug": ""}
    return _page_response(
        request,
        "page_new.html.j2",
        {"user": user, "csrf_token": session.csrf_token, "errors": [], "form": form},
    )


@router.post("")
async def page_create(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    page_id: str = Form(alias="id"),
    title: str = Form(""),
    description: str = Form(""),
    slug: str = Form(""),
) -> object:
    user, session = user_session
    db = get_db(request)
    form = {"id": page_id, "title": title, "description": description, "slug": slug}
    try:
        page = new_page(page_id, PageContent(title=title, description=description, slug=slug))
    except ValidationError as error:
        errors = form_errors(error)
    else:
        existing = await db.run(lambda storage: storage.load_page(page_id))
        if existing is None:
            await db.run(lambda storage: storage.save_page(page))
            return RedirectResponse(
                admin_path("pages", page.id), status_code=status.HTTP_303_SEE_OTHER
            )
        errors = [f"id: a page with id {page_id!r} already exists"]
    return _page_response(
        request,
        "page_new.html.j2",
        {"user": user, "csrf_token": session.csrf_token, "errors": errors, "form": form},
        status_code=HTTP_422,
    )


def _editor_context(
    request: Request, page: Page, form: dict[str, str] | None = None, role: Role | None = None
) -> dict[str, object]:
    return {
        "page": page,
        "transitions": available_transitions(page.status, role) if role else [],
        "states": {language: page.translation_state(language) for language in TARGET_LANGUAGES},
        "own_states": own_states(page),
        "target_languages": TARGET_LANGUAGES,
        "kind_hints": sorted(_kind_hints(request)),
        "form": form
        or {
            "title": page.source.title,
            "description": page.source.description,
            "slug": page.source.slug,
            "publish_at": publish_at_form(page.publish_at),
        },
    }


@router.get("/{page_id}")
async def page_edit_form(
    request: Request,
    page_id: str,
    user_session: tuple[User, AdminSession] = Depends(current_session),
) -> object:
    user, session = user_session
    page = await _load_page(request, page_id)
    revisions = await get_db(request).run(lambda storage: storage.list_revisions("page", page_id))
    notes = await get_db(request).run(lambda storage: storage.list_notes("page", page_id))
    project = _project(request)
    preview_path = "/preview" + urls.page_path(page, SOURCE_LANGUAGE) if project else None
    preview_target = (preview_path or "").removeprefix("/preview/").rstrip("/")
    preview_ready = bool(
        preview_path
        and (Path(request.app.state.preview_dir) / preview_target / "index.html").is_file()
    )
    return _page_response(
        request,
        "page_edit.html.j2",
        {
            "user": user,
            "csrf_token": session.csrf_token,
            "errors": [],
            "revisions": revisions,
            "notes": notes,
            "note_kind": "page",
            "entity_id": page_id,
            "preview_path": preview_path,
            "preview_ready": preview_ready,
            **_editor_context(request, page, role=user.role),
        },
    )


@router.post("/{page_id}")
async def page_edit_save(
    request: Request,
    page_id: str,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    title: str = Form(""),
    description: str = Form(""),
    slug: str = Form(""),
    publish_at: str = Form(""),
) -> object:
    user, session = user_session
    page = await _load_page(request, page_id)
    form = {"title": title, "description": description, "slug": slug, "publish_at": publish_at}
    try:
        page.publish_at = parse_publish_at(publish_at)
        page.source = PageContent(title=title, description=description, slug=slug)
    except ValueError as error:
        return _page_response(
            request,
            "page_edit.html.j2",
            {
                "user": user,
                "csrf_token": session.csrf_token,
                "errors": _form_error_list(error),
                **_editor_context(request, page, form),
            },
            status_code=HTTP_422,
        )
    await _save_page(request, page, user.username)
    return RedirectResponse(admin_path("pages", page.id), status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{page_id}/autosave")
async def page_autosave(
    request: Request,
    page_id: str,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    title: str = Form(""),
    description: str = Form(""),
    slug: str = Form(""),
    publish_at: str = Form(""),
) -> object:
    """Persist valid page metadata and refresh its scoped themed preview."""
    user, _ = user_session
    page = await _load_page(request, page_id)
    try:
        page.publish_at = parse_publish_at(publish_at)
        page.source = PageContent(title=title, description=description, slug=slug)
    except ValueError as error:
        return JSONResponse({"ok": False, "errors": _form_error_list(error)}, status_code=HTTP_422)
    await _save_page(request, page, user.username, revision=False)
    preview_path = await refresh_entry_preview(request, page)
    return {"ok": True, "preview_path": preview_path}


@router.post("/{page_id}/sections")
async def section_add(
    request: Request,
    page_id: str,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    key: str = Form(""),
    kind: str = Form(""),
) -> object:
    user, session = user_session
    page = await _load_page(request, page_id)
    errors: list[str] = []
    if page.section(key) is not None:
        errors = [f"key: a section with key {key!r} already exists on this page"]
    else:
        try:
            page.sections.append(Section(key=key, kind=kind, source=SectionContent()))
        except ValidationError as error:
            errors = form_errors(error)
    if errors:
        return _page_response(
            request,
            "page_edit.html.j2",
            {
                "user": user,
                "csrf_token": session.csrf_token,
                "errors": errors,
                **_editor_context(request, page),
            },
            status_code=HTTP_422,
        )
    await _save_page(request, page, user.username)
    return RedirectResponse(
        admin_path("pages", page.id, "sections", key),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/{page_id}/sections/{key}/move")
async def section_move(
    request: Request,
    page_id: str,
    key: str,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    direction: str = Form(...),
) -> object:
    user, _ = user_session
    page = await _load_page(request, page_id)
    _section_or_404(page, key)
    index = next(i for i, section in enumerate(page.sections) if section.key == key)
    swap = index - 1 if direction == "up" else index + 1
    if 0 <= swap < len(page.sections):
        page.sections[index], page.sections[swap] = page.sections[swap], page.sections[index]
        await _save_page(request, page, user.username)
    return RedirectResponse(admin_path("pages", page.id), status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{page_id}/sections/{key}/delete")
async def section_delete(
    request: Request,
    page_id: str,
    key: str,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
) -> object:
    user, _ = user_session
    page = await _load_page(request, page_id)
    _section_or_404(page, key)
    page.sections = [section for section in page.sections if section.key != key]
    await _save_page(request, page, user.username)
    return RedirectResponse(admin_path("pages", page.id), status_code=status.HTTP_303_SEE_OTHER)


def _field_rows(section: Section, hints: dict[str, tuple[str, ...]]) -> list[dict[str, str]]:
    rows = [{"name": name, "value": value} for name, value in sorted(section.source.fields.items())]
    for hint in hints.get(section.kind, ()):
        if hint not in section.source.fields:
            rows.append({"name": hint, "value": ""})
    rows.extend({"name": "", "value": ""} for _ in range(BLANK_FIELD_ROWS))
    return rows


def _section_context(request: Request, page: Page, section: Section) -> dict[str, object]:
    return {
        "page": page,
        "section": section,
        "rows": _field_rows(section, _kind_hints(request)),
        "media_text": "\n".join(section.source.media),
        "states": {language: section.translation_state(language) for language in TARGET_LANGUAGES},
        "target_languages": TARGET_LANGUAGES,
    }


@router.get("/{page_id}/sections/{key}")
async def section_edit_form(
    request: Request,
    page_id: str,
    key: str,
    user_session: tuple[User, AdminSession] = Depends(current_session),
) -> object:
    user, session = user_session
    page = await _load_page(request, page_id)
    section = _section_or_404(page, key)
    return _page_response(
        request,
        "section_edit.html.j2",
        {
            "user": user,
            "csrf_token": session.csrf_token,
            "errors": [],
            **_section_context(request, page, section),
        },
    )


@router.post("/{page_id}/sections/{key}")
async def section_edit_save(
    request: Request,
    page_id: str,
    key: str,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
) -> object:
    user, _ = user_session
    page = await _load_page(request, page_id)
    section = _section_or_404(page, key)
    form = await request.form()
    names = [str(value) for value in form.getlist("field_name")]
    values = [str(value) for value in form.getlist("field_value")]
    fields = {
        name.strip(): value
        for name, value in zip(names, values, strict=False)
        if name.strip() and value
    }
    section.source = SectionContent(fields=fields, media=parse_media(str(form.get("media", ""))))
    await _save_page(request, page, user.username)
    return RedirectResponse(
        admin_path("pages", page.id, "sections", key),
        status_code=status.HTTP_303_SEE_OTHER,
    )


def _page_translation_context(
    page: Page, language: Language, form: dict[str, str] | None = None
) -> dict[str, object]:
    translation = page.translations.get(language)
    content = translation.content if translation else None
    return {
        "page": page,
        "language": language,
        "state": TranslatableModel.translation_state(page, language),
        "form": form
        or {
            "title": content.title if content else "",
            "description": content.description if content else "",
            "slug": content.slug if content else "",
        },
    }


@router.get("/{page_id}/translations/{language_code}")
async def page_translation_form(
    request: Request,
    page_id: str,
    language_code: str,
    user_session: tuple[User, AdminSession] = Depends(current_session),
) -> object:
    user, session = user_session
    language = _target_language(language_code)
    page = await _load_page(request, page_id)
    return _page_response(
        request,
        "page_translation.html.j2",
        {
            "user": user,
            "csrf_token": session.csrf_token,
            "errors": [],
            **_page_translation_context(page, language),
        },
    )


@router.post("/{page_id}/translations/{language_code}")
async def page_translation_save(
    request: Request,
    page_id: str,
    language_code: str,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    title: str = Form(""),
    description: str = Form(""),
    slug: str = Form(""),
) -> object:
    user, session = user_session
    language = _target_language(language_code)
    page = await _load_page(request, page_id)
    form = {"title": title, "description": description, "slug": slug}
    try:
        content = PageContent(title=title, description=description, slug=slug)
    except ValidationError as error:
        return _page_response(
            request,
            "page_translation.html.j2",
            {
                "user": user,
                "csrf_token": session.csrf_token,
                "errors": form_errors(error),
                **_page_translation_context(page, language, form),
            },
            status_code=HTTP_422,
        )
    page.set_translation(language, content)
    await _save_page(request, page, user.username)
    return RedirectResponse(
        admin_path("pages", page.id, "translations", language.value),
        status_code=status.HTTP_303_SEE_OTHER,
    )


def _section_translation_context(
    page: Page, section: Section, language: Language, form: dict[str, str] | None = None
) -> dict[str, object]:
    translation = section.translations.get(language)
    content = translation.content if translation else None
    translated = content.fields if content else {}
    return {
        "page": page,
        "section": section,
        "language": language,
        "state": section.translation_state(language),
        "source_fields": sorted(section.source.fields.items()),
        "form": form or {name: translated.get(name, "") for name in section.source.fields},
        "media_text": "\n".join(content.media if content else section.source.media),
    }


@router.get("/{page_id}/sections/{key}/translations/{language_code}")
async def section_translation_form(
    request: Request,
    page_id: str,
    key: str,
    language_code: str,
    user_session: tuple[User, AdminSession] = Depends(current_session),
) -> object:
    user, session = user_session
    language = _target_language(language_code)
    page = await _load_page(request, page_id)
    section = _section_or_404(page, key)
    return _page_response(
        request,
        "section_translation.html.j2",
        {
            "user": user,
            "csrf_token": session.csrf_token,
            "errors": [],
            **_section_translation_context(page, section, language),
        },
    )


@router.post("/{page_id}/sections/{key}/translations/{language_code}")
async def section_translation_save(
    request: Request,
    page_id: str,
    key: str,
    language_code: str,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
) -> object:
    user, _ = user_session
    language = _target_language(language_code)
    page = await _load_page(request, page_id)
    section = _section_or_404(page, key)
    form = await request.form()
    fields = {
        name: str(form.get(f"field__{name}", "")).strip()
        for name in section.source.fields
        if str(form.get(f"field__{name}", "")).strip()
    }
    content = SectionContent(fields=fields, media=parse_media(str(form.get("media", ""))))
    section.set_translation(language, content)
    await _save_page(request, page, user.username)
    return RedirectResponse(
        admin_path("pages", page.id, "sections", key, "translations", language.value),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/{page_id}/status")
async def page_status(
    request: Request,
    page_id: str,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    to: str = Form(...),
) -> object:
    user, session = user_session
    page = await _load_page(request, page_id)
    try:
        target = ContentStatus(to)
    except ValueError:
        raise HTTPException(status_code=400, detail="unknown status") from None
    minimum = transition_minimum(page.status, target)
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
        blockers = publish_blockers(page, content)
        if blockers:
            return _page_response(
                request,
                "page_edit.html.j2",
                {
                    "user": user,
                    "csrf_token": session.csrf_token,
                    "errors": blockers,
                    **_editor_context(request, page, role=user.role),
                },
                status_code=HTTP_422,
            )
    page.status = target
    await _save_page(request, page, user.username)
    return RedirectResponse(admin_path("pages", page.id), status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{page_id}/revisions/{revision}")
async def page_revision_detail(
    request: Request,
    page_id: str,
    revision: int,
    user_session: tuple[User, AdminSession] = Depends(current_session),
) -> object:
    user, session = user_session
    page = await _load_page(request, page_id)
    payload = await get_db(request).run(
        lambda storage: storage.load_revision("page", page_id, revision)
    )
    if payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown revision")
    snapshot = Page.model_validate_json(payload)
    diff = "\n".join(
        difflib.unified_diff(
            snapshot.source.description.splitlines(),
            page.source.description.splitlines(),
            fromfile=f"revision {revision}",
            tofile="current",
            lineterm="",
        )
    )
    return _page_response(
        request,
        "revision_detail.html.j2",
        {
            "user": user,
            "csrf_token": session.csrf_token,
            "active_section": "pages",
            "entity_id": page.id,
            "back_url": f"/pages/{page.id}",
            "restore_url": f"/pages/{page.id}/revisions/{revision}/restore",
            "snapshot_title": snapshot.source.title,
            "revision": revision,
            "diff": diff,
        },
    )


@router.post("/{page_id}/revisions/{revision}/restore")
async def page_revision_restore(
    request: Request,
    page_id: str,
    revision: int,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
) -> RedirectResponse:
    user, _ = user_session
    await _load_page(request, page_id)
    payload = await get_db(request).run(
        lambda storage: storage.load_revision("page", page_id, revision)
    )
    if payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown revision")
    restored = Page.model_validate_json(payload)
    restored = restored.model_copy(update={"id": page_id})
    await _save_page(request, restored, user.username)
    return RedirectResponse(admin_path("pages", restored.id), status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{page_id}/duplicate")
async def page_duplicate(
    request: Request,
    page_id: str,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
) -> RedirectResponse:
    """Duplicate as draft (M5): content, metadata and sections copied,
    fresh identity, no schedule, no trash flag."""
    user, _ = user_session
    page = await _load_page(request, page_id)
    taken = set(await get_db(request).run(lambda storage: storage.list_page_ids()))
    now = datetime.now(UTC)
    copy = page.model_copy(
        update={
            "id": _copy_id(page_id, taken),
            "status": ContentStatus.DRAFT,
            "publish_at": None,
            "deleted_at": None,
            "created_at": now,
            "updated_at": now,
        }
    )
    await _save_page(request, copy, user.username)
    return RedirectResponse(admin_path("pages", copy.id), status_code=status.HTTP_303_SEE_OTHER)
