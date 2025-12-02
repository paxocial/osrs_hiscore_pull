"""UI endpoints for triggering snapshots via HTMX."""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from web.deps import require_user
from web.services.snapshot import SnapshotService

templates = Jinja2Templates(directory="web/templates")
router = APIRouter()
snapshot_service = SnapshotService()


@router.post("/snapshots/run", response_class=HTMLResponse)
async def run_snapshot(request: Request, player: str = Form(...), mode: str = Form("auto")):
    require_user(request)
    result = snapshot_service.trigger_snapshot(player, mode)
    return templates.TemplateResponse(
        "partials/snapshot_result.html",
        {"request": request, "result": result},
    )
