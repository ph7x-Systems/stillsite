"""Application factory.

One FastAPI process serves the API and the server-rendered UI (ADR-0013).
Storage is opened once per process (any supported engine, via the
thread-affine ``StorageExecutor``) and closed on shutdown; handlers reach it
through ``get_db``.
"""

import asyncio
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader, select_autoescape

from cms_admin.articles import router as articles_router
from cms_admin.auth import current_session, get_db
from cms_admin.auth import router as auth_router
from cms_admin.dashboard import router as dashboard_router
from cms_admin.db import StorageExecutor
from cms_admin.i18n import i18n_context, load_catalogs
from cms_admin.mail import resolve_mailer
from cms_admin.media import router as media_router
from cms_admin.menu import router as menu_router
from cms_admin.notes import router as notes_router
from cms_admin.pages import router as pages_router
from cms_admin.publishing import router as publishing_router
from cms_admin.settings import AdminSettings
from cms_admin.trash import router as trash_router
from cms_admin.users import router as users_router


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: AdminSettings = app.state.settings
    app.state.db = StorageExecutor(settings.storage_url)
    # Autosaves and manual preview builds serialize writes into /preview/ so
    # overlapping requests cannot leave a mixed artifact behind.
    app.state.preview_lock = asyncio.Lock()
    try:
        yield
    finally:
        app.state.db.close()


# Hardening (SECURITY_STRATEGY, M3 phase 9; scripts per ADR-0020): every
# script, style, font and image comes from the app itself — vendored files,
# no CDN, and scripts are strictly 'self' (never 'unsafe-inline'). Style
# *attributes* are allowed (ADR-0023): CodeMirror's measurements and
# Popper's positioning set element styles at runtime; templates still ship
# zero style attributes (enforced by the hardening suite) and autoescape
# keeps user content inert. Nothing may frame the admin.
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'self'; "
        "connect-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "font-src 'self'; img-src 'self' data:; form-action 'self'; "
        "base-uri 'none'; frame-ancestors 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Strict-Transport-Security": "max-age=31536000",
    "Cache-Control": "no-store",
    "Pragma": "no-cache",
}


def _is_private_file_path(path: str) -> bool:
    return path == "/preview" or path.startswith(("/preview/", "/media-files/"))


def create_app(settings: AdminSettings | None = None) -> FastAPI:
    from cms_admin.auth import LoginRateLimiter

    app = FastAPI(title="Sardine CMS admin", lifespan=_lifespan, docs_url=None, redoc_url=None)

    @app.middleware("http")
    async def _security_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
        response = None
        if _is_private_file_path(request.url.path):
            try:
                await current_session(request)
            except HTTPException:
                response = RedirectResponse("/login", status_code=303)
        if response is None:
            response = await call_next(request)
        headers = dict(SECURITY_HEADERS)
        if request.url.path.startswith("/preview/"):
            # ADR-0027: the same-origin editor frames the preview; nothing
            # external ever can. Only this mount relaxes the frame policy.
            headers["Content-Security-Policy"] = headers["Content-Security-Policy"].replace(
                "frame-ancestors 'none'", "frame-ancestors 'self'"
            )
            headers["X-Frame-Options"] = "SAMEORIGIN"
        for name, value in headers.items():
            response.headers[name] = value
        return response

    resolved = settings if settings is not None else AdminSettings.from_env()
    app.state.settings = resolved
    # autoescape must be forced on: the stock select_autoescape does not
    # recognize the .html.j2 extension and would render templates unescaped.
    app.state.templates = Jinja2Templates(
        env=Environment(
            loader=FileSystemLoader(Path(__file__).parent / "templates"),
            autoescape=select_autoescape(default=True, default_for_string=True),
        ),
        # ADR-0022: gettext callables enter each render's context — never
        # the shared environment, which serves all languages at once.
        context_processors=[i18n_context],
    )
    app.state.translations = load_catalogs()
    app.state.login_limiter = LoginRateLimiter()
    # ADR-0032: outbound email is optional and transport-pluggable; a
    # broken or unknown transport fails startup, never a request.
    extension_transports: dict[str, object] = {}
    if resolved.mail_transport != "smtp":
        from cms_cli.project import load_project

        project = load_project(resolved.project_dir)
        for extension in sorted(project.load_extensions(), key=lambda e: e.name):
            extension_transports.update(extension.mail_transports)
    app.state.mailer = resolve_mailer(
        resolved.mail_transport,
        resolved.smtp_url,
        resolved.mail_from,
        extension_transports,  # type: ignore[arg-type]
    )
    # Argon2 is deliberately expensive. Bound concurrent work so a burst of
    # login attempts cannot exhaust every worker thread/CPU core.
    app.state.password_slots = asyncio.Semaphore(4)
    app.include_router(auth_router)
    app.include_router(dashboard_router)
    app.include_router(articles_router)
    app.include_router(pages_router)
    app.include_router(media_router)
    app.include_router(publishing_router)
    app.include_router(trash_router)
    app.include_router(users_router)
    app.include_router(notes_router)
    app.include_router(menu_router)
    app.state.preview_dir = tempfile.mkdtemp(prefix="sardine-preview-")
    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
    app.mount(
        "/preview",
        StaticFiles(directory=app.state.preview_dir, html=True, check_dir=False),
        name="preview",
    )
    app.mount(
        "/media-files",
        StaticFiles(directory=app.state.settings.media_dir, check_dir=False),
        name="media-files",
    )

    @app.get("/healthz")
    async def healthz(request: Request) -> dict[str, str | int]:
        version = await get_db(request).run(lambda storage: storage.schema_version())
        return {"status": "ok", "schema_version": version}

    return app
