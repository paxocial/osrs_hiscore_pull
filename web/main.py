"""Web UI entrypoint for OSRS Web Lab (FastAPI + HTMX pages)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from api.main import app as api_app
from web.routes.pages import router as pages_router
from web.routes.auth import router as auth_router
from web.routes.profiles import router as profiles_router
from web.routes.clans import router as clans_router
from web.routes.snapshots_ui import router as snapshots_ui_router
from web.routes.profile_detail import router as profile_detail_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="OSRS Web Lab",
        description="HTMX-fronted shell for snapshots, clans, and analytics.",
        docs_url=None,
        redoc_url=None,
    )

    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.mount("/static", StaticFiles(directory="web/static"), name="static")

    # Sessions (signed cookie). In production, set WEB_SECRET_KEY env.
    import os

    secret = os.environ.get("WEB_SECRET_KEY", "dev-secret-change-me")
    app.add_middleware(
        SessionMiddleware,
        secret_key=secret,
        session_cookie="osrs_session",
        same_site="lax",
        https_only=False,
    )

    # Mount existing API under /api for reuse.
    app.mount("/api", api_app)

    app.include_router(pages_router)
    app.include_router(auth_router)
    app.include_router(profiles_router)
    app.include_router(clans_router)
    app.include_router(snapshots_ui_router)
    app.include_router(profile_detail_router)
    return app


app = create_app()


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("web.main:app", host="0.0.0.0", port=8001, reload=True)
