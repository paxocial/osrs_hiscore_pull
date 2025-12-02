"""UI endpoints for triggering snapshots via HTMX."""

from __future__ import annotations

from fastapi import APIRouter, Form, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from web.deps import require_user, get_current_user
from web.services.snapshot import SnapshotService
from web.services.jobs import JobService

templates = Jinja2Templates(directory="web/templates")
router = APIRouter()
jobs = JobService()


@router.post("/snapshots/run", response_class=HTMLResponse)
async def run_snapshot(request: Request, player: str = Form(...), mode: str = Form("auto")):
    user = require_user(request)
    job_id = jobs.create_job("snapshot", {"player": player, "mode": mode, "user_id": user["id"], "target_type": "account"})
    return templates.TemplateResponse(
        "partials/snapshot_result.html",
        {"request": request, "job_id": job_id, "player": player},
    )


@router.get("/snapshots/run/status", response_class=HTMLResponse)
async def snapshot_status(request: Request, job_id: str = Query(...), player: str = Query(...)):
    require_user(request)
    job = jobs.get_job(job_id)
    return templates.TemplateResponse(
        "partials/snapshot_result.html",
        {"request": request, "job": job, "job_id": job_id, "player": player},
    )
