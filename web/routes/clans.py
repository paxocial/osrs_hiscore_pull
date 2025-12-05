"""Routes for clan creation and member management."""

from __future__ import annotations

import re
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from web.deps import require_user, verify_csrf, get_csrf_token
from web.services.accounts import AccountService
from web.services.clans import ClanService
from web.services.jobs import JobService
from web.services.clan_stats import ClanStatsService
from web.services.profile_data import ProfileDataService

templates = Jinja2Templates(directory="web/templates")
router = APIRouter()
clan_service = ClanService()
account_service = AccountService()
jobs = JobService()
clan_stats = ClanStatsService()
profile_data = ProfileDataService()


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip()).strip("-").lower()
    return slug or "clan"


@router.post("/clans/create", response_class=HTMLResponse)
async def create_clan(request: Request, name: str = Form(...), csrf_token: str = Form(...)):
    user = require_user(request)
    verify_csrf(request, csrf_token)

    # Require at least one linked RSN
    links = account_service.list_user_accounts(user["id"])
    if not links:
        return RedirectResponse(url="/profiles", status_code=303)

    slug = slugify(name)
    clan_id = clan_service.create_clan(user["id"], name, slug)

    # Auto-add default RSN as member if exists
    default = next((l for l in links if l.get("is_default")), links[0])
    clan_service.add_member(clan_id, default["name"], requested_mode=default.get("cached_mode") or default.get("default_mode") or "auto")

    return RedirectResponse(url="/profiles", status_code=303)


@router.post("/clans/add-member", response_class=HTMLResponse)
async def add_member(request: Request, clan_id: int = Form(...), account_name: str = Form(...), mode: str = Form("auto"), csrf_token: str = Form(...)):
    user = require_user(request)
    verify_csrf(request, csrf_token)
    clan_service.add_member(clan_id, account_name, requested_mode=mode)
    return RedirectResponse(url="/profiles", status_code=303)


@router.post("/clans/remove-member", response_class=HTMLResponse)
async def remove_member(request: Request, clan_id: int = Form(...), account_id: int = Form(...), csrf_token: str = Form(...)):
    user = require_user(request)
    verify_csrf(request, csrf_token)
    clan_service.remove_member(clan_id, account_id)
    return RedirectResponse(url="/profiles", status_code=303)


@router.get("/clans/{slug}", response_class=HTMLResponse)
async def clan_detail(request: Request, slug: str):
    user = require_user(request)
    clan = clan_service.get_clan_by_slug(slug)
    if not clan:
        return RedirectResponse(url="/profiles", status_code=303)
    members = clan_service.list_members_paginated(clan["id"], offset=0, limit=20)
    modes = ["auto"] + list(["main", "ironman", "hardcore", "ultimate", "deadman", "tournament", "seasonal"])
    return templates.TemplateResponse(
        "clan_detail.html",
        {
            "request": request,
            "user": user,
            "clan": clan,
            "members": members.get("rows", []),
            "members_total": members.get("total", 0),
            "csrf_token": get_csrf_token(request),
            "modes": modes,
        },
    )


@router.post("/clans/{clan_id}/snapshot", response_class=HTMLResponse)
async def run_clan_snapshot(request: Request, clan_id: int, csrf_token: str = Form(...)):
    user = require_user(request)
    verify_csrf(request, csrf_token)
    clan = clan_service.get_clan_by_id(clan_id)
    if not clan or clan["owner_user_id"] != user["id"]:
        return HTMLResponse("<div class='alert error'>Not authorized for this clan</div>", status_code=403)

    payload = {
        "clan_id": clan_id,
        "user_id": user["id"],
        "target_type": "clan",
    }
    job_id = jobs.create_job("clan_snapshot", payload)
    return templates.TemplateResponse(
        "partials/clan_snapshot_job.html",
        {"request": request, "job_id": job_id, "clan": clan},
    )


@router.get("/clans/jobs/status", response_class=HTMLResponse)
async def clan_job_status(request: Request, job_id: str):
    require_user(request)
    job = jobs.get_job(job_id)
    return templates.TemplateResponse(
        "partials/clan_snapshot_job.html",
        {"request": request, "job": job, "job_id": job_id},
    )


@router.get("/clans/{slug}/stats", response_class=HTMLResponse)
async def clan_stats_view(request: Request, slug: str, timeframe: str = "7d"):
    user = require_user(request)
    clan = clan_service.get_clan_by_slug(slug)
    if not clan:
        return HTMLResponse("<div class='alert error'>Clan not found</div>", status_code=404)
    data = clan_stats.compute_stats(clan["id"], timeframe=timeframe)
    return templates.TemplateResponse(
        "partials/clan_stats.html",
        {"request": request, "clan": clan, "data": data},
    )


@router.get("/clans/{slug}/leaderboard", response_class=HTMLResponse)
async def clan_leaderboard(
    request: Request,
    slug: str,
    timeframe: str = "7d",
    metric: str = "xp",
    page: int = 1,
    page_size: int = 10,
):
    require_user(request)
    clan = clan_service.get_clan_by_slug(slug)
    if not clan:
        return HTMLResponse("<div class='alert error'>Clan not found</div>", status_code=404)
    lb = clan_stats.get_leaderboard(clan["id"], timeframe=timeframe, metric=metric, page=page, page_size=page_size)
    return templates.TemplateResponse(
        "partials/clan_leaderboard.html",
        {"request": request, "clan": clan, "lb": lb},
    )


@router.get("/clans/{slug}/last_run", response_class=HTMLResponse)
async def clan_last_run(request: Request, slug: str):
    require_user(request)
    clan = clan_service.get_clan_by_slug(slug)
    if not clan:
        return HTMLResponse("<div class='alert error'>Clan not found</div>", status_code=404)
    last = clan_stats.get_last_run(clan["id"])
    return templates.TemplateResponse(
        "partials/clan_last_run.html",
        {"request": request, "clan": clan, "last": last},
    )


@router.get("/clans/{slug}/member_overview", response_class=HTMLResponse)
async def clan_member_overview(request: Request, slug: str, name: str, timeframe: str = "7d"):
    require_user(request)
    clan = clan_service.get_clan_by_slug(slug)
    if not clan:
        return HTMLResponse("<div class='alert error'>Clan not found</div>", status_code=404)

    # Ensure the member belongs to this clan
    with clan_service.db.get_connection() as conn:
        membership = conn.execute(
            """
            SELECT a.id FROM clan_members cm
            JOIN accounts a ON cm.account_id = a.id
            WHERE cm.clan_id = ? AND a.name = ?
            """,
            (clan["id"], name),
        ).fetchone()
    if not membership:
        return HTMLResponse("<div class='alert error'>Member not found in clan</div>", status_code=404)

    profile = profile_data.get_profile(name, limit=1, offset=0)
    latest = profile.get("latest")

    # Recompute window-based delta for the requested timeframe
    if latest:
        since = profile_data._time_bounds(timeframe)
        with profile_data.db.get_connection() as conn:
            window_delta = profile_data._compute_window_delta(conn, latest.get("account_id"), since)
        if window_delta:
            latest["delta"] = window_delta
            latest["delta_summary"] = profile_data._delta_summary(window_delta)

    return templates.TemplateResponse(
        "partials/clan_member_overview.html",
        {
            "request": request,
            "clan": clan,
            "member_name": name,
            "latest": latest,
            "timeframe": timeframe,
        },
    )


@router.get("/clans/{slug}/members", response_class=HTMLResponse)
async def clan_members(request: Request, slug: str, offset: int = 0, limit: int = 20):
    require_user(request)
    clan = clan_service.get_clan_by_slug(slug)
    if not clan:
        return HTMLResponse("<div class='alert error'>Clan not found</div>", status_code=404)
    page = clan_service.list_members_paginated(clan["id"], offset=offset, limit=limit)
    return templates.TemplateResponse(
        "partials/clan_members.html",
        {
            "request": request,
            "clan": clan,
            "members": page.get("rows", []),
            "total": page.get("total", 0),
            "offset": page.get("offset", 0),
            "limit": page.get("limit", limit),
            "csrf_token": get_csrf_token(request),
        },
    )
