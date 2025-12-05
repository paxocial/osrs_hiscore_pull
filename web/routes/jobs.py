"""Job status endpoints for UI polling."""

from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from web.deps import require_user, get_current_user
from web.services.jobs import JobService
from web.services.schedule_service import ScheduleService
from web.services.clans import ClanService
from web.services.accounts import AccountService

templates = Jinja2Templates(directory="web/templates")
router = APIRouter()
jobs = JobService()
schedules = ScheduleService()
clans = ClanService()
accounts = AccountService()


@router.get("/jobs/status", response_class=HTMLResponse)
async def job_status(request: Request, player: str | None = None, clan_id: int | None = None):
    user = get_current_user(request)
    if not user:
        return HTMLResponse("", status_code=204)
    recent = jobs.list_recent(limit=5, user_id=user["id"], player=player, clan_id=clan_id)
    return templates.TemplateResponse(
        "partials/job_status.html",
        {"request": request, "jobs": recent},
    )


@router.post("/jobs/schedule/account", response_class=HTMLResponse)
async def schedule_account(
    request: Request,
    account_name: str = Form(...),
    cron: str = Form(...),
    custom_cron: str = Form(""),
):
    user = require_user(request)
    cron_expr = custom_cron.strip() if cron == "custom" and custom_cron.strip() else cron
    if not cron_expr:
        return HTMLResponse("<div class='alert error'>Select a schedule</div>", status_code=400)
    schedules.add_account_schedule(user["id"], account_name, cron_expr)
    user_schedules = schedules.list_user_schedules(user["id"])
    return templates.TemplateResponse(
        "partials/job_schedules.html",
        {"request": request, "schedules": user_schedules},
    )


@router.get("/jobs/schedule/list", response_class=HTMLResponse)
async def list_schedules(request: Request):
    user = get_current_user(request)
    if not user:
        return HTMLResponse("", status_code=204)
    user_schedules = schedules.list_user_schedules(user["id"])
    clan_schedules = schedules.list_clan_schedules(user["id"])
    return templates.TemplateResponse(
        "partials/job_schedules.html",
        {"request": request, "schedules": user_schedules, "clan_schedules": clan_schedules},
    )


@router.post("/jobs/schedule/delete", response_class=HTMLResponse)
async def delete_schedule(request: Request, schedule_id: int = Form(...)):
    user = require_user(request)
    schedules.delete_schedule(user["id"], schedule_id)
    user_schedules = schedules.list_user_schedules(user["id"])
    clan_schedules = schedules.list_clan_schedules(user["id"])
    return templates.TemplateResponse(
        "partials/job_schedules.html",
        {"request": request, "schedules": user_schedules, "clan_schedules": clan_schedules},
    )


@router.post("/jobs/schedule/clan", response_class=HTMLResponse)
async def schedule_clan(request: Request, clan_id: int = Form(...), cron: str = Form(...), custom_cron: str = Form("")):
    user = require_user(request)
    # Validate ownership
    clan = clans.get_clan_by_slug("")  # placeholder, will validate by id below
    with clans.db.get_connection() as conn:
        c = conn.execute("SELECT * FROM clans WHERE id = ?", (clan_id,)).fetchone()
    if not c or c["owner_user_id"] != user["id"]:
        return HTMLResponse("<div class='alert error'>Not authorized for this clan</div>", status_code=403)
    # Enforce allowed presets only (no custom cron) and cap to 2/day
    allowed = {
        "0 0 * * *": "daily",
        "0 12 * * *": "daily_mid",
        "0 0,12 * * *": "twice_daily",
    }
    cron_expr = cron.strip()
    if cron_expr not in allowed:
        return HTMLResponse("<div class='alert error'>Use allowed schedules only (daily or twice daily)</div>", status_code=400)
    schedules.add_clan_schedule(user["id"], clan_id, cron_expr, max_daily_runs=2)
    user_schedules = schedules.list_user_schedules(user["id"])
    clan_schedules = schedules.list_clan_schedules(user["id"])
    return templates.TemplateResponse(
        "partials/job_schedules.html",
        {"request": request, "schedules": user_schedules, "clan_schedules": clan_schedules},
    )
