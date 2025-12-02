"""Page routes for the Web UI shell."""

from __future__ import annotations

from pathlib import Path

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from web.deps import get_current_user

templates = Jinja2Templates(directory="web/templates")
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "title": "OSRS Web Lab",
            "user": user,
        },
    )


@router.get("/status", response_class=HTMLResponse)
async def status(request: Request):
    # Health check via mounted API
    api_status = "unknown"
    db_present = Path("data/analytics.db").exists()
    health_url = str(request.base_url) + "api/health"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(health_url)
            if resp.status_code == 200:
                api_status = "healthy"
            else:
                api_status = f"error ({resp.status_code})"
    except Exception:
        api_status = "unreachable"

    status_text = f"API {api_status}" if api_status != "healthy" else "API healthy"

    return templates.TemplateResponse(
        "partials/status.html",
        {
            "request": request,
            "status_text": status_text,
            "db_present": db_present,
            "api_status": api_status,
        },
    )
