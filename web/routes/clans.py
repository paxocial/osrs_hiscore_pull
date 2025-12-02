"""Routes for clan creation and member management."""

from __future__ import annotations

import re
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from web.deps import require_user, verify_csrf, get_csrf_token
from web.services.accounts import AccountService
from web.services.clans import ClanService

templates = Jinja2Templates(directory="web/templates")
router = APIRouter()
clan_service = ClanService()
account_service = AccountService()


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
    members = clan_service.list_members(clan["id"])
    modes = ["auto"] + list(["main", "ironman", "hardcore", "ultimate", "deadman", "tournament", "seasonal"])
    return templates.TemplateResponse(
        "clan_detail.html",
        {
            "request": request,
            "user": user,
            "clan": clan,
            "members": members,
            "csrf_token": get_csrf_token(request),
            "modes": modes,
        },
    )
