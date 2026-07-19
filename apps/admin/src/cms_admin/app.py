"""Application factory.

One FastAPI process serves the API and the server-rendered UI (ADR-0013).
Storage is opened once per process (any supported engine, via the
thread-affine ``StorageExecutor``) and closed on shutdown; handlers reach it
through ``get_db``.
"""

import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader, select_autoescape

from cms_admin.articles import router as articles_router
from cms_admin.auth import get_db
from cms_admin.auth import router as auth_router
from cms_admin.dashboard import router as dashboard_router
from cms_admin.db import StorageExecutor
from cms_admin.media import router as media_router
from cms_admin.pages import router as pages_router
from cms_admin.publishing import router as publishing_router
from cms_admin.settings import AdminSettings


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: AdminSettings = app.state.settings
    app.state.db = StorageExecutor(settings.storage_url)
    try:
        yield
    finally:
        app.state.db.close()


# Hardening (SECURITY_STRATEGY, M3 phase 9): the admin ships zero JavaScript,
# so the CSP allows no script source at all; styles, fonts and images come
# only from the app itself; nothing may frame it.
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'none'; style-src 'self'; font-src 'self'; "
        "img-src 'self' data:; form-action 'self'; base-uri 'none'; "
        "frame-ancestors 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


def create_app(settings: AdminSettings | None = None) -> FastAPI:
    from cms_admin.auth import LoginRateLimiter

    app = FastAPI(title="Sardine CMS admin", lifespan=_lifespan, docs_url=None, redoc_url=None)

    @app.middleware("http")
    async def _security_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response

    app.state.settings = settings if settings is not None else AdminSettings.from_env()
    # autoescape must be forced on: the stock select_autoescape does not
    # recognize the .html.j2 extension and would render templates unescaped.
    app.state.templates = Jinja2Templates(
        env=Environment(
            loader=FileSystemLoader(Path(__file__).parent / "templates"),
            autoescape=select_autoescape(default=True, default_for_string=True),
        )
    )
    app.state.login_limiter = LoginRateLimiter()
    app.include_router(auth_router)
    app.include_router(dashboard_router)
    app.include_router(articles_router)
    app.include_router(pages_router)
    app.include_router(media_router)
    app.include_router(publishing_router)
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
