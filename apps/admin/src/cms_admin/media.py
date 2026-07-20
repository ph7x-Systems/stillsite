"""Media library: validated uploads, translatable alt text, safe delete.

Uploads are validated server-side from the bytes themselves — the MIME type
is sniffed from magic numbers (never trusted from the client), image
dimensions are parsed without external dependencies, and a size limit
applies. EN alt text is mandatory at the model level. Deleting checks usage
first: an asset referenced by an article cover or a section stays.
"""

import os
import struct

from cms_core import Article, Language, MediaAsset, Page, StorageBackend, User
from cms_core.accounts import AdminSession
from cms_core.languages import SOURCE_LANGUAGE, TARGET_LANGUAGES
from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import RedirectResponse
from pydantic import ValidationError

from cms_admin.articles import form_errors
from cms_admin.auth import current_session, enforce_csrf, get_db

router = APIRouter(prefix="/media")

HTTP_422 = status.HTTP_422_UNPROCESSABLE_CONTENT

EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def sniff_mime(data: bytes) -> str | None:
    """Identify the payload from magic numbers; None means unsupported."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def image_size(data: bytes, mime: str) -> tuple[int, int] | None:
    """Parse intrinsic dimensions from the bytes; None when unknown."""
    try:
        if mime == "image/png":
            width, height = struct.unpack(">II", data[16:24])
            return width, height
        if mime == "image/gif":
            width, height = struct.unpack("<HH", data[6:10])
            return width, height
        if mime == "image/jpeg":
            index = 2
            while index + 9 < len(data):
                if data[index] != 0xFF:
                    index += 1
                    continue
                marker = data[index + 1]
                if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                    height, width = struct.unpack(">HH", data[index + 5 : index + 9])
                    return width, height
                index += 2 + struct.unpack(">H", data[index + 2 : index + 4])[0]
        if mime == "image/webp":
            if data[12:16] == b"VP8X":
                width = int.from_bytes(data[24:27], "little") + 1
                height = int.from_bytes(data[27:30], "little") + 1
                return width, height
            if data[12:16] == b"VP8L":
                bits = int.from_bytes(data[21:25], "little")
                return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
            if data[12:16] == b"VP8 ":
                width, height = struct.unpack("<HH", data[26:30])
                return (width & 0x3FFF), (height & 0x3FFF)
    except (struct.error, IndexError):
        return None
    return None


def asset_references(asset_id: str, articles: list[Article], pages: list[Page]) -> list[str]:
    """Human-readable list of everything that points at the asset."""
    references: list[str] = []
    for article in articles:
        if article.cover == asset_id:
            references.append(f"article:{article.id} (cover)")
    for page in pages:
        for section in page.sections:
            contents = [section.source] + [t.content for t in section.translations.values()]
            if any(asset_id in content.media for content in contents):
                references.append(f"page:{page.id} section:{section.key}")
    return references


def _load_asset(storage: StorageBackend, asset_id: str) -> MediaAsset | None:
    return storage.load_media_asset(asset_id)


def _page(
    request: Request, template: str, context: dict[str, object], status_code: int = 200
) -> object:
    return request.app.state.templates.TemplateResponse(
        request, template, {"active_section": "media", **context}, status_code=status_code
    )


def _alt_form(asset: MediaAsset | None) -> dict[str, str]:
    alts = asset.alt if asset else {}
    return {f"alt_{language.value}": alts.get(language, "") for language in Language}


def _write_new_file(path: os.PathLike[str], data: bytes) -> None:
    """Create one upload without following or replacing an existing path."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)


@router.get("")
async def media_list(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(current_session),
    q: str = "",
    show: str = "all",
) -> object:
    """The library with server-side filters (M5): a text search over id,
    path, MIME type and alt texts, plus quick views — images only and
    assets still missing translated alt text."""
    user, session = user_session
    assets = await get_db(request).run(lambda storage: storage.load_all_media_assets())
    total = len(assets)
    needle = q.strip().lower()
    if needle:
        assets = [
            asset
            for asset in assets
            if needle in asset.id.lower()
            or needle in asset.path.lower()
            or needle in asset.mime_type.lower()
            or any(needle in alt.lower() for alt in asset.alt.values())
        ]
    if show == "images":
        assets = [asset for asset in assets if asset.is_image]
    elif show == "missing-alt":
        assets = [asset for asset in assets if asset.missing_alt_languages()]
    return _page(
        request,
        "media_list.html.j2",
        {
            "user": user,
            "csrf_token": session.csrf_token,
            "assets": assets,
            "total": total,
            "q": q,
            "show": show if show in ("all", "images", "missing-alt") else "all",
            "target_languages": TARGET_LANGUAGES,
            "source_language": SOURCE_LANGUAGE,
        },
    )


@router.get("/new")
async def media_new_form(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(current_session),
) -> object:
    user, session = user_session
    return _page(
        request,
        "media_new.html.j2",
        {
            "user": user,
            "csrf_token": session.csrf_token,
            "errors": [],
            "form": {"id": "", "alt": ""},
        },
    )


@router.post("")
async def media_upload(
    request: Request,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
    asset_id: str = Form(alias="id"),
    alt: str = Form(""),
    upload: UploadFile | None = None,
) -> object:
    user, session = user_session
    settings = request.app.state.settings
    db = get_db(request)
    form = {"id": asset_id, "alt": alt}
    errors: list[str] = []
    data = b""
    if upload is not None:
        try:
            data = await upload.read(settings.upload_max_bytes + 1)
        finally:
            await upload.close()
    mime = sniff_mime(data) if data and len(data) <= settings.upload_max_bytes else None
    if not data:
        errors.append("file: choose a file to upload")
    elif len(data) > settings.upload_max_bytes:
        limit_mb = settings.upload_max_bytes // (1024 * 1024)
        errors.append(f"file: larger than the {limit_mb} MB limit")
    elif mime is None:
        errors.append("file: unsupported type — png, jpeg, gif or webp")
    asset: MediaAsset | None = None
    if not errors and mime is not None:
        size = image_size(data, mime)
        if size is None:
            errors.append("file: could not read the image dimensions")
        elif size[0] * size[1] > settings.upload_max_pixels:
            errors.append("file: image dimensions exceed the pixel limit")
        else:
            try:
                asset = MediaAsset(
                    id=asset_id,
                    path=f"{asset_id}{EXTENSIONS[mime]}",
                    mime_type=mime,
                    width=size[0],
                    height=size[1],
                    alt={SOURCE_LANGUAGE: alt},
                )
            except ValidationError as error:
                errors.extend(form_errors(error))
    if asset is not None and not errors:
        existing = await db.run(lambda storage: _load_asset(storage, asset_id))
        if existing is not None:
            errors = [f"id: a media asset with id {asset_id!r} already exists"]
    if asset is None or errors:
        return _page(
            request,
            "media_new.html.j2",
            {"user": user, "csrf_token": session.csrf_token, "errors": errors, "form": form},
            status_code=HTTP_422,
        )
    settings.media_dir.mkdir(parents=True, exist_ok=True)
    file_path = settings.media_dir / asset.path
    try:
        _write_new_file(file_path, data)
    except FileExistsError:
        return _page(
            request,
            "media_new.html.j2",
            {
                "user": user,
                "csrf_token": session.csrf_token,
                "errors": ["file: a file already exists at the generated path"],
                "form": form,
            },
            status_code=HTTP_422,
        )
    try:
        await db.run(lambda storage: storage.save_media_asset(asset))
    except BaseException:
        file_path.unlink(missing_ok=True)
        raise
    return RedirectResponse(f"/media/{asset.id}", status_code=status.HTTP_303_SEE_OTHER)


async def _asset_context(request: Request, asset_id: str) -> dict[str, object]:
    db = get_db(request)
    asset = await db.run(lambda storage: _load_asset(storage, asset_id))
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown media asset")
    articles = await db.run(lambda storage: storage.load_all_articles())
    pages = await db.run(lambda storage: storage.load_all_pages())
    return {
        "asset": asset,
        "references": asset_references(asset.id, articles, pages),
        "target_languages": TARGET_LANGUAGES,
        "form": _alt_form(asset),
    }


@router.get("/{asset_id}")
async def media_edit_form(
    request: Request,
    asset_id: str,
    user_session: tuple[User, AdminSession] = Depends(current_session),
) -> object:
    user, session = user_session
    context = await _asset_context(request, asset_id)
    return _page(
        request,
        "media_edit.html.j2",
        {"user": user, "csrf_token": session.csrf_token, "errors": [], **context},
    )


@router.post("/{asset_id}")
async def media_alt_save(
    request: Request,
    asset_id: str,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
) -> object:
    user, session = user_session
    db = get_db(request)
    asset = await db.run(lambda storage: _load_asset(storage, asset_id))
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown media asset")
    form = await request.form()
    alts = {
        language: str(form.get(f"alt_{language.value}", "")).strip()
        for language in Language
        if str(form.get(f"alt_{language.value}", "")).strip()
    }
    try:
        updated = asset.model_copy(update={"alt": alts})
        MediaAsset.model_validate(updated.model_dump())
    except ValidationError as error:
        context = await _asset_context(request, asset_id)
        context["form"] = {f"alt_{lang.value}": alts.get(lang, "") for lang in Language}
        return _page(
            request,
            "media_edit.html.j2",
            {
                "user": user,
                "csrf_token": session.csrf_token,
                "errors": form_errors(error),
                **context,
            },
            status_code=HTTP_422,
        )
    await db.run(lambda storage: storage.save_media_asset(updated))
    return RedirectResponse(f"/media/{asset_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{asset_id}/delete")
async def media_delete(
    request: Request,
    asset_id: str,
    user_session: tuple[User, AdminSession] = Depends(enforce_csrf),
) -> object:
    user, session = user_session
    db = get_db(request)
    asset = await db.run(lambda storage: _load_asset(storage, asset_id))
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown media asset")
    articles = await db.run(lambda storage: storage.load_all_articles())
    pages = await db.run(lambda storage: storage.load_all_pages())
    references = asset_references(asset_id, articles, pages)
    if references:
        context = await _asset_context(request, asset_id)
        return _page(
            request,
            "media_edit.html.j2",
            {
                "user": user,
                "csrf_token": session.csrf_token,
                "errors": [f"in use: referenced by {', '.join(references)}"],
                **context,
            },
            status_code=HTTP_422,
        )
    await db.run(lambda storage: storage.delete_media_asset(asset_id))
    file_path = request.app.state.settings.media_dir / asset.path
    if file_path.is_file():
        file_path.unlink()
    return RedirectResponse("/media", status_code=status.HTTP_303_SEE_OTHER)
