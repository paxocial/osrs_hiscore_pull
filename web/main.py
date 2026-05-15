"""Web UI entrypoint for OSRS Web Lab (FastAPI + HTMX pages)."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import PlainTextResponse
from starlette.middleware.sessions import SessionMiddleware

from api.main import app as api_app
from web.routes.pages import router as pages_router
from web.routes.auth import router as auth_router
from web.routes.profiles import router as profiles_router
from web.routes.clans import router as clans_router
from web.routes.snapshots_ui import router as snapshots_ui_router
from web.routes.profile_detail import router as profile_detail_router
from web.routes.jobs import router as jobs_router
from web.routes.webhooks import router as webhooks_router
from web.routes.admin import router as admin_router
from web.routes.compare import router as compare_router
from web.services.job_worker import JobWorker
from database.connection import DatabaseConnection
from web.services.scheduler import Scheduler
from config.settings import AppConfig
from web.middleware.security_headers import SecurityHeadersMiddleware
from web.middleware.session_timeout import SessionTimeoutMiddleware


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _is_allowed_public_api_path(path: str) -> bool:
    return (
        path == "/api/v1/ledger/osrs"
        or path.startswith("/api/v1/ledger/osrs/")
        or path == "/api/api/v1/ledger/osrs"
        or path.startswith("/api/api/v1/ledger/osrs/")
    )


def _is_blocked_public_path(path: str) -> bool:
    blocked_prefixes = (
        "/admin",
        "/jobs",
        "/webhooks",
        "/operator",
        "/ops",
        "/runtime",
        "/council",
        "/.council",
        "/.codex",
        "/.claude",
        "/.mcp",
    )
    if path.startswith("/api"):
        return not _is_allowed_public_api_path(path)
    return any(path == prefix or path.startswith(prefix + "/") for prefix in blocked_prefixes)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Catherby",
        description="OSRS Account Tracker & Tools - Track your RuneScape progress",
        docs_url=None,
        redoc_url=None,
    )

    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.mount("/static", StaticFiles(directory="web/static"), name="static")

    # Load config for middleware settings
    config = AppConfig()

    # MIDDLEWARE ORDER MATTERS!
    # In Starlette, middleware added LAST runs FIRST.
    # So we add in reverse order of desired execution:
    # 1. GZipMiddleware (already added above) - runs last (compression)
    # 2. SecurityHeadersMiddleware - runs 3rd (add headers)
    # 3. SessionTimeoutMiddleware - runs 2nd (needs session)
    # 4. SessionMiddleware - runs 1st (provides session)

    # Security headers for all responses (doesn't need session)
    app.add_middleware(SecurityHeadersMiddleware)

    # Session activity timeout - needs session, so add BEFORE SessionMiddleware
    app.add_middleware(SessionTimeoutMiddleware)

    # Sessions (signed cookie) - must be added LAST so it runs FIRST
    app.add_middleware(
        SessionMiddleware,
        secret_key=config.security.secret_key,
        session_cookie="osrs_session",
        same_site=config.security.same_site,
        https_only=config.security.https_only,
        max_age=config.security.session_max_age,
    )

    public_host_mode = _env_flag("CATHERBY_PUBLIC_HOST_MODE", default=False)
    if public_host_mode:
        @app.middleware("http")
        async def public_surface_guard(request, call_next):
            if _is_blocked_public_path(request.url.path):
                return PlainTextResponse("Not Found", status_code=404)
            return await call_next(request)

    # Mount existing API under /api for reuse.
    app.mount("/api", api_app)

    app.include_router(pages_router)
    app.include_router(auth_router)
    app.include_router(profiles_router)
    app.include_router(clans_router)
    app.include_router(snapshots_ui_router)
    app.include_router(profile_detail_router)
    app.include_router(jobs_router)
    app.include_router(webhooks_router)
    app.include_router(compare_router)
    app.include_router(admin_router)  # Admin routes (protected by @require_admin)

    # Ensure DB initialized and jobs table present before starting worker
    db = DatabaseConnection(reuse_connection=False, check_same_thread=False)
    db.initialize_database()
    worker = JobWorker(job_service=None, ingest_service=None, config_path="config/project.json")
    worker.start()
    app.state.job_worker = worker
    scheduler = Scheduler(db=db)
    scheduler.start()
    app.state.scheduler = scheduler

    return app


app = create_app()


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("web.main:app", host="0.0.0.0", port=8001, reload=True)
