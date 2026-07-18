"""Application factory.

One FastAPI process serves the API and the server-rendered UI (ADR-0013).
Storage is opened once per process (any supported engine, via the
thread-affine ``StorageExecutor``) and closed on shutdown; handlers reach it
through ``get_db``.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from cms_admin.db import StorageExecutor
from cms_admin.settings import AdminSettings


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: AdminSettings = app.state.settings
    app.state.db = StorageExecutor(settings.storage_url)
    try:
        yield
    finally:
        app.state.db.close()


def get_db(request: Request) -> StorageExecutor:
    db: StorageExecutor = request.app.state.db
    return db


def create_app(settings: AdminSettings | None = None) -> FastAPI:
    app = FastAPI(title="Stillsite admin", lifespan=_lifespan, docs_url=None, redoc_url=None)
    app.state.settings = settings if settings is not None else AdminSettings.from_env()

    @app.get("/healthz")
    async def healthz(request: Request) -> dict[str, str | int]:
        version = await get_db(request).run(lambda storage: storage.schema_version())
        return {"status": "ok", "schema_version": version}

    return app
