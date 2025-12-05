"""Profile detail page for individual RSNs with timeline, skills, and activities."""

from __future__ import annotations

import json
from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import httpx
from datetime import datetime

from web.deps import require_user
from web.services.profile_data import ProfileDataService
from web.services.detect_mode import detect_mode
from web.services.accounts import AccountService
from database.connection import DatabaseConnection

templates = Jinja2Templates(directory="web/templates")
router = APIRouter()
profile_data = ProfileDataService()
db = DatabaseConnection()
account_service = AccountService(db)


def _can_manage_mode(user_id: int, rsn: str) -> tuple[bool, int | None]:
    with db.get_connection() as conn:
        acct = conn.execute("SELECT id FROM accounts WHERE name = ?", (rsn,)).fetchone()
        if not acct:
            return False, None
        account_id = acct["id"]
        linked = conn.execute(
            "SELECT 1 FROM user_accounts WHERE user_id = ? AND account_id = ?",
            (user_id, account_id),
        ).fetchone()
        if linked:
            return True, account_id
        clan_owner = conn.execute(
            """
            SELECT 1
            FROM clans c
            JOIN clan_members cm ON cm.clan_id = c.id
            WHERE cm.account_id = ? AND c.owner_user_id = ?
            LIMIT 1
            """,
            (account_id, user_id),
        ).fetchone()
        return (clan_owner is not None), account_id


@router.get("/profiles/{rsn}", response_class=HTMLResponse)
async def profile_detail(request: Request, rsn: str):
    user = require_user(request)
    data = profile_data.get_profile(rsn)
    can_manage, _ = _can_manage_mode(user["id"], rsn)
    mode_value = data["latest"]["resolved_mode"] if data.get("latest") else "—"

    return templates.TemplateResponse(
        "profile_detail.html",
        {
            "request": request,
            "user": user,
            "rsn": rsn,
            "latest": data["latest"],
            "snapshots": data["timeline"],
            "total_snapshots": data["total"],
            "can_refresh_mode": can_manage,
            "mode_value": mode_value,
        },
    )


@router.get("/profiles/{rsn}/timeline", response_class=HTMLResponse)
async def profile_timeline(request: Request, rsn: str, page: int = Query(1, ge=1), page_size: int = Query(5, ge=1, le=50)):
    require_user(request)
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


@router.get("/profiles/{rsn}/series", response_class=JSONResponse)
async def profile_series(request: Request, rsn: str, frm: str = "", to: str = "", limit: int = 500):
    try:
        user = require_user(request)
    except Exception:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    series = profile_data.get_series(rsn, from_ts=frm or None, to_ts=to or None, limit=limit)
    return JSONResponse(series)


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


@router.get("/profiles/{rsn}/snapshot_detail", response_class=HTMLResponse)
async def profile_snapshot_detail(request: Request, rsn: str, snapshot_id: str, view: str = "panel"):
    payload = profile_data.get_snapshot_payload(snapshot_id)
    if not payload:
        return HTMLResponse("<div class='alert error'>Snapshot not found</div>", status_code=404)

    report_content = None
    json_content = None
    if view == "report":
        safe_rsn = rsn.replace(" ", "_")
        report_path = Path(f"reports/{safe_rsn}/{snapshot_id}.md")
        report_content = _safe_read(report_path)
    elif view == "json":
        json_content = json.dumps(payload, indent=2)

    return templates.TemplateResponse(
        "partials/snapshot_detail.html",
        {
            "request": request,
            "rsn": rsn,
            "payload": payload,
            "view": view,
            "report_content": report_content,
            "json_content": json_content,
            "delta_summary": payload.get("delta_summary"),
        },
    )


@router.post("/profiles/{rsn}/refresh-mode", response_class=HTMLResponse)
async def profile_refresh_mode(request: Request, rsn: str):
    user = require_user(request)
    can_manage, account_id = _can_manage_mode(user["id"], rsn)
    if not can_manage or not account_id:
        raise HTTPException(status_code=403, detail="Not permitted to adjust mode")

    result = detect_mode(rsn.strip(), requested_mode="auto", force=True)
    mode = result.get("mode") if result.get("status") == "found" else None
    if mode:
        account_service.ensure_account(rsn.strip(), display_name=None, mode=mode, update_default_mode=True)

    return templates.TemplateResponse(
        "partials/profile_mode_status.html",
        {
            "request": request,
            "mode": mode or "unknown",
            "result": result,
        },
    )


@router.delete("/profiles/{rsn}/snapshot", response_class=HTMLResponse)
async def profile_snapshot_delete(
    request: Request,
    rsn: str,
    snapshot_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(5, ge=1, le=50),
):
    require_user(request)

    # Clean up files if present
    payload = profile_data.get_snapshot_payload(snapshot_id)
    safe_rsn = rsn.replace(" ", "_")
    if payload:
        fetched_at = payload.get("metadata", {}).get("fetched_at")
        json_path = profile_data._snapshot_filename(fetched_at, rsn) if fetched_at else None
        if json_path:
            Path(json_path).unlink(missing_ok=True)
    report_path = Path(f"reports/{safe_rsn}/{snapshot_id}.md")
    report_path.unlink(missing_ok=True)

    # Delete from DB (cascades to skills/activities/deltas)
    try:
        with profile_data.db.get_connection() as conn:
            conn.execute("DELETE FROM snapshots WHERE snapshot_id = ?", (snapshot_id,))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to delete snapshot: {exc}")

    # Refresh timeline after deletion
    # Re-page in case we deleted the last item on the page
    total = profile_data.get_profile(rsn, limit=1, offset=0)["total"]
    total_pages = max(1, (total // page_size) + (1 if total % page_size else 0))
    page = min(page, total_pages)
    start = (page - 1) * page_size
    data = profile_data.get_profile(rsn, limit=page_size, offset=start)
    snapshots = data["timeline"]
    resp = templates.TemplateResponse(
        "partials/timeline.html",
        {
            "request": request,
            "rsn": rsn,
            "snapshots": snapshots,
            "total": data["total"],
            "page": page,
            "page_size": page_size,
            "refresh_snapshot_id": data["latest"]["snapshot_id"] if data.get("latest") else None,
        },
    )
    return resp
