"""Routes for managing user-linked RSNs (“My Profiles”)."""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from web.deps import require_user, get_csrf_token, verify_csrf
from web.services.accounts import AccountService
from web.services.clans import ClanService
from web.services.detect_mode import detect_mode

templates = Jinja2Templates(directory="web/templates")
router = APIRouter()
account_service = AccountService()
clan_service = ClanService()


@router.get("/profiles", response_class=HTMLResponse)
async def profiles(request: Request):
    user = require_user(request)
    links = account_service.list_user_accounts(user["id"])
    clans = clan_service.list_clans_for_user(user["id"])
    modes = ["auto"] + list(["main", "ironman", "hardcore", "ultimate", "deadman", "tournament", "seasonal"])
    return templates.TemplateResponse(
        "profiles.html",
        {
            "request": request,
            "user": user,
            "links": links,
            "clans": clans,
            "csrf_token": get_csrf_token(request),
            "modes": modes,
        },
    )


@router.post("/profiles/add", response_class=HTMLResponse)
async def add_profile(
    request: Request,
    name: str = Form(...),
    display_name: str = Form(""),
    mode: str = Form("auto"),
    make_default: bool = Form(False),
    csrf_token: str = Form(...),
):
    user = require_user(request)
    verify_csrf(request, csrf_token)
    requested_mode = (mode or "auto").strip().lower()
    final_mode = requested_mode

    if requested_mode in ("auto", "auto-detect"):
        detection = detect_mode(name.strip(), requested_mode="auto")
        if detection.get("status") == "found":
            final_mode = detection["mode"]
        else:
            final_mode = "main"
    elif requested_mode:
        final_mode = requested_mode

    account_id = account_service.ensure_account(
        name.strip(),
        display_name.strip() or None,
        mode=final_mode or "main",
        update_default_mode=True,
    )
    account_service.link_user_account(user["id"], account_id, role="owner", make_default=make_default)
    return RedirectResponse(url="/profiles", status_code=303)


@router.post("/profiles/default", response_class=HTMLResponse)
async def set_default(request: Request, account_id: int = Form(...), csrf_token: str = Form(...)):
    user = require_user(request)
    verify_csrf(request, csrf_token)
    account_service.set_default(user["id"], account_id)
    return RedirectResponse(url="/profiles", status_code=303)


@router.post("/profiles/remove", response_class=HTMLResponse)
async def remove_profile(request: Request, account_id: int = Form(...), csrf_token: str = Form(...)):
    user = require_user(request)
    verify_csrf(request, csrf_token)
    account_service.unlink_user_account(user["id"], account_id)
    return RedirectResponse(url="/profiles", status_code=303)


@router.post("/profiles/detect", response_class=HTMLResponse)
async def detect_profile_mode(request: Request, name: str = Form(...), csrf_token: str = Form(...)):
    user = require_user(request)
    verify_csrf(request, csrf_token)
    result = detect_mode(name.strip(), requested_mode="auto")
    return templates.TemplateResponse(
        "partials/detect_result.html",
        {"request": request, "result": result, "name": name},
    )
