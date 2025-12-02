"""Profile detail page for individual RSNs with timeline, skills, and activities."""

from __future__ import annotations

import json
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from web.deps import get_current_user
from web.services.profile_data import ProfileDataService

templates = Jinja2Templates(directory="web/templates")
router = APIRouter()
profile_data = ProfileDataService()


@router.get("/profiles/{rsn}", response_class=HTMLResponse)
async def profile_detail(request: Request, rsn: str):
    user = get_current_user(request)
    data = profile_data.get_profile(rsn)

    return templates.TemplateResponse(
        "profile_detail.html",
        {
            "request": request,
            "user": user,
            "rsn": rsn,
            "latest": data["latest"],
            "snapshots": data["timeline"],
            "total_snapshots": data["total"],
        },
    )


@router.get("/profiles/{rsn}/timeline", response_class=HTMLResponse)
async def profile_timeline(request: Request, rsn: str, page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=50)):
    start = (page - 1) * page_size
    data = profile_data.get_profile(rsn, limit=page_size, offset=start)
    snapshots = data["timeline"]
    return templates.TemplateResponse(
        "partials/timeline.html",
        {
            "request": request,
            "rsn": rsn,
            "snapshots": snapshots,
            "total": data["total"],
            "page": page,
            "page_size": page_size,
        },
    )


def _safe_read(path: Path) -> str:
    if not path.exists():
        return "Not found."
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        return f"Error reading file: {exc}"


@router.get("/profiles/{rsn}/report", response_class=HTMLResponse)
async def profile_report(request: Request, rsn: str, snapshot_id: str, copy: int = 0):
    safe_rsn = rsn.replace(" ", "_")
    report_path = Path(f"reports/{safe_rsn}/{snapshot_id}.md")
    content = _safe_read(report_path)
    if copy:
        return PlainTextResponse(content)
    return HTMLResponse(f"<pre class='report-view'>{content}</pre>")


@router.get("/profiles/{rsn}/json", response_class=HTMLResponse)
async def profile_json(request: Request, rsn: str, snapshot_id: str, copy: int = 0):
    payload = profile_data.get_snapshot_payload(snapshot_id)
    if not payload:
        content = "JSON not found."
    else:
        content = json.dumps(payload, indent=2)
    if copy:
        return PlainTextResponse(content)
    return HTMLResponse(f"<pre class='report-view'>{content}</pre>")
