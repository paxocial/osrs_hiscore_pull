"""Auth routes for register/login/logout and API token management."""

from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from web.deps import auth_service, get_current_user, require_user, get_csrf_token, verify_csrf

templates = Jinja2Templates(directory="web/templates")
router = APIRouter()


@router.get("/auth/register", response_class=HTMLResponse)
async def register_form(request: Request):
    return templates.TemplateResponse(
        "auth_register.html",
        {"request": request, "user": get_current_user(request), "csrf_token": get_csrf_token(request)},
    )


@router.post("/auth/register", response_class=HTMLResponse)
async def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    csrf_token: str = Form(...),
):
    verify_csrf(request, csrf_token)
    if password != confirm_password:
        return templates.TemplateResponse(
            "auth_register.html",
            {
                "request": request,
                "error": "Passwords do not match.",
                "user": get_current_user(request),
                "csrf_token": get_csrf_token(request),
            },
            status_code=400,
        )
    created_id = auth_service.register(email, password)
    if not created_id:
        return templates.TemplateResponse(
            "auth_register.html",
            {
                "request": request,
                "error": "Email already registered.",
                "user": get_current_user(request),
                "csrf_token": get_csrf_token(request),
            },
            status_code=400,
        )
    request.session["user_id"] = created_id
    response = RedirectResponse(url="/", status_code=303)
    return response


@router.get("/auth/login", response_class=HTMLResponse)
async def login_form(request: Request):
    current = get_current_user(request)
    if current:
        return RedirectResponse(url="/profiles", status_code=303)
    return templates.TemplateResponse(
        "auth_login.html",
        {"request": request, "user": current, "csrf_token": get_csrf_token(request)},
    )


@router.post("/auth/login", response_class=HTMLResponse)
async def login_submit(request: Request, email: str = Form(...), password: str = Form(...), csrf_token: str = Form(...)):
    verify_csrf(request, csrf_token)
    user = auth_service.authenticate(email, password)
    if not user:
        return templates.TemplateResponse(
            "auth_login.html",
            {"request": request, "error": "Invalid credentials.", "user": None},
            status_code=401,
        )
    request.session["user_id"] = user["id"]
    return RedirectResponse(url="/", status_code=303)


@router.post("/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


@router.get("/auth/tokens", response_class=HTMLResponse)
async def token_list(request: Request):
    user = require_user(request)
    tokens = auth_service.list_tokens(user["id"])
    return templates.TemplateResponse(
        "auth_tokens.html",
        {"request": request, "user": user, "tokens": tokens, "new_token": None, "csrf_token": get_csrf_token(request)},
    )


@router.post("/auth/tokens/issue", response_class=HTMLResponse)
async def token_issue(request: Request, scopes: str = Form("read"), label: str = Form(None), csrf_token: str = Form(...)):
    user = require_user(request)
    verify_csrf(request, csrf_token)
    plain_token, _ = auth_service.issue_token(user["id"], scopes=scopes, label=label)
    tokens = auth_service.list_tokens(user["id"])
    return templates.TemplateResponse(
        "auth_tokens.html",
        {"request": request, "user": user, "tokens": tokens, "new_token": plain_token, "csrf_token": get_csrf_token(request)},
    )


@router.post("/auth/tokens/revoke", response_class=HTMLResponse)
async def token_revoke(request: Request, token_id: int = Form(...), csrf_token: str = Form(...)):
    user = require_user(request)
    verify_csrf(request, csrf_token)
    auth_service.revoke_token(user["id"], token_id)
    tokens = auth_service.list_tokens(user["id"])
    return templates.TemplateResponse(
        "auth_tokens.html",
        {"request": request, "user": user, "tokens": tokens, "new_token": None, "csrf_token": get_csrf_token(request)},
    )
