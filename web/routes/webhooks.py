"""Webhook configuration endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from web.deps import require_user, get_current_user
from web.services.webhooks import WebhookService
from web.services.clans import ClanService

templates = Jinja2Templates(directory="web/templates")
router = APIRouter()
webhooks = WebhookService()
clans = ClanService()


@router.get("/webhooks", response_class=HTMLResponse)
async def list_webhooks(request: Request):
    user = require_user(request)
    hooks = webhooks.list_webhooks(user["id"])
    return templates.TemplateResponse(
        "partials/webhooks.html",
        {"request": request, "hooks": hooks},
    )


@router.post("/webhooks/user", response_class=HTMLResponse)
async def create_user_webhook(request: Request, url: str = Form(...), events: str = Form("snapshot_complete"), provider: str = Form("custom")):
    user = require_user(request)
    webhooks.upsert_webhook(
        owner_user_id=user["id"],
        target_type="user",
        target_id=None,
        url=url.strip(),
        events=events.strip(),
        provider=provider.strip() or "custom",
        active=True,
    )
    hooks = webhooks.list_webhooks(user["id"])
    return templates.TemplateResponse(
        "partials/webhooks.html",
        {"request": request, "hooks": hooks},
    )


@router.post("/webhooks/clan", response_class=HTMLResponse)
async def create_clan_webhook(request: Request, clan_id: int = Form(...), url: str = Form(...), events: str = Form("snapshot_complete"), provider: str = Form("custom")):
    user = require_user(request)
    clan = clans.get_clan_by_slug("")  # placeholder to use service
    with clans.db.get_connection() as conn:
        c = conn.execute("SELECT * FROM clans WHERE id = ?", (clan_id,)).fetchone()
    if not c or c["owner_user_id"] != user["id"]:
        return HTMLResponse("<div class='alert error'>Not authorized for this clan</div>", status_code=403)

    webhooks.upsert_webhook(
        owner_user_id=user["id"],
        target_type="clan",
        target_id=clan_id,
        url=url.strip(),
        events=events.strip(),
        provider=provider.strip() or "custom",
        active=True,
    )
    hooks = webhooks.list_webhooks(user["id"])
    return templates.TemplateResponse(
        "partials/webhooks.html",
        {"request": request, "hooks": hooks},
    )
