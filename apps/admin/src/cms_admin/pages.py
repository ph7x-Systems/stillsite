"""Pages: metadata, ordered typed sections, and their translations.

Sections are free-form field maps (the theme owns the meaning of each
``kind``), so the section editor is a dynamic name/value form. For the kinds
the reference theme ships, the editor suggests the field names that kind
consumes — suggestions only, never validation: any theme can define any
kind. The side-by-side translation UX mirrors the article editor: the EN
source read-only next to the translation, one field at a time.
"""

from datetime import UTC, datetime

from cms_core import (
    AdminSession,
    Language,
    Page,
    PageContent,
    Section,
    SectionContent,
    TranslationState,
    User,
    new_page,
)
from cms_core.languages import SOURCE_LANGUAGE, TARGET_LANGUAGES
from cms_core.translatable import TranslatableModel
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import ValidationError

from cms_admin.articles import form_errors
from cms_admin.auth import current_session, enforce_csrf, get_db

router = APIRouter(prefix="/pages")

HTTP_422 = status.HTTP_422_UNPROCESSABLE_CONTENT

# Field names the reference theme's section kinds consume — shown as empty
# suggested rows in the editor. Hints only; themes own the real contract.
KIND_FIELD_HINTS: dict[str, tuple[str, ...]] = {
    "hero": ("kicker", "lead", "heading", "accent"),
    "latest-articles": ("kicker", "heading"),
    "story": ("kicker", "heading", "body"),
    "expertise": ("kicker", "heading", "row1no", "row1t", "row1d"),
    "contact": ("kicker", "heading", "accent", "button"),
}

BLANK_FIELD_ROWS = 3


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


async def _save_page(request: Request, page: Page) -> None:
    page.updated_at = datetime.now(UTC)
    await get_db(request).run(lambda storage: storage.save_page(page))


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
    pages = await get_db(request).run(lambda storage: storage.load_all_pages())
    return _page_response(
        request,
        "pages_list.html.j2",
        {
            "user": user,
            "csrf_token": session.csrf_token,
            "pages": pages,
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
            return RedirectResponse(f"/pages/{page.id}", status_code=status.HTTP_303_SEE_OTHER)
        errors = [f"id: a page with id {page_id!r} already exists"]
    return _page_response(
        request,
        "page_new.html.j2",
        {"user": user, "csrf_token": session.csrf_token, "errors": errors, "form": form},
        status_code=HTTP_422,
    )


def _editor_context(page: Page, form: dict[str, str] | None = None) -> dict[str, object]:
    return {
        "page": page,
        "states": {language: page.translation_state(language) for language in TARGET_LANGUAGES},
        "own_states": own_states(page),
        "target_languages": TARGET_LANGUAGES,
        "kind_hints": sorted(KIND_FIELD_HINTS),
        "form": form
        or {
            "title": page.source.title,
            "description": page.source.description,
            "slug": page.source.slug,
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
    return _page_response(
        request,
        "page_edit.html.j2",
        {"user": user, "csrf_token": session.csrf_token, "errors": [], **_editor_context(page)},
    )


@router.post("/{page_id}")
async def page_edit_save(
    request: Request,
    page_id: str,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    title: str = Form(""),
    description: str = Form(""),
    slug: str = Form(""),
) -> object:
    user, session = user_session
    page = await _load_page(request, page_id)
    form = {"title": title, "description": description, "slug": slug}
    try:
        page.source = PageContent(title=title, description=description, slug=slug)
    except ValidationError as error:
        return _page_response(
            request,
            "page_edit.html.j2",
            {
                "user": user,
                "csrf_token": session.csrf_token,
                "errors": form_errors(error),
                **_editor_context(page, form),
            },
            status_code=HTTP_422,
        )
    await _save_page(request, page)
    return RedirectResponse(f"/pages/{page.id}", status_code=status.HTTP_303_SEE_OTHER)


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
                **_editor_context(page),
            },
            status_code=HTTP_422,
        )
    await _save_page(request, page)
    return RedirectResponse(
        f"/pages/{page.id}/sections/{key}", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/{page_id}/sections/{key}/move")
async def section_move(
    request: Request,
    page_id: str,
    key: str,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    direction: str = Form(...),
) -> object:
    page = await _load_page(request, page_id)
    _section_or_404(page, key)
    index = next(i for i, section in enumerate(page.sections) if section.key == key)
    swap = index - 1 if direction == "up" else index + 1
    if 0 <= swap < len(page.sections):
        page.sections[index], page.sections[swap] = page.sections[swap], page.sections[index]
        await _save_page(request, page)
    return RedirectResponse(f"/pages/{page.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{page_id}/sections/{key}/delete")
async def section_delete(
    request: Request,
    page_id: str,
    key: str,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
) -> object:
    page = await _load_page(request, page_id)
    _section_or_404(page, key)
    page.sections = [section for section in page.sections if section.key != key]
    await _save_page(request, page)
    return RedirectResponse(f"/pages/{page.id}", status_code=status.HTTP_303_SEE_OTHER)


def _field_rows(section: Section) -> list[dict[str, str]]:
    rows = [{"name": name, "value": value} for name, value in sorted(section.source.fields.items())]
    for hint in KIND_FIELD_HINTS.get(section.kind, ()):
        if hint not in section.source.fields:
            rows.append({"name": hint, "value": ""})
    rows.extend({"name": "", "value": ""} for _ in range(BLANK_FIELD_ROWS))
    return rows


def _section_context(page: Page, section: Section) -> dict[str, object]:
    return {
        "page": page,
        "section": section,
        "rows": _field_rows(section),
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
            **_section_context(page, section),
        },
    )


@router.post("/{page_id}/sections/{key}")
async def section_edit_save(
    request: Request,
    page_id: str,
    key: str,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
) -> object:
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
    await _save_page(request, page)
    return RedirectResponse(
        f"/pages/{page.id}/sections/{key}", status_code=status.HTTP_303_SEE_OTHER
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
    await _save_page(request, page)
    return RedirectResponse(
        f"/pages/{page.id}/translations/{language.value}",
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
    await _save_page(request, page)
    return RedirectResponse(
        f"/pages/{page.id}/sections/{key}/translations/{language.value}",
        status_code=status.HTTP_303_SEE_OTHER,
    )
