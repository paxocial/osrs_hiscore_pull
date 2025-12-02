"""Shared web dependencies and guards."""

from __future__ import annotations

import secrets
from typing import Optional

from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse

from web.services.auth import AuthService

auth_service = AuthService()


def get_current_user(request: Request) -> Optional[dict]:
    user_id = request.session.get("user_id") if hasattr(request, "session") else None
    if not user_id:
        return None
    return auth_service.get_user(user_id)


def require_user(request: Request) -> dict:
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            detail="Login required",
            headers={"Location": "/auth/login"},
        )
    return user


def get_csrf_token(request: Request) -> str:
    """Return a CSRF token for the session, generating if absent."""
    token = request.session.get("csrf_token") if hasattr(request, "session") else None
    if not token:
        token = secrets.token_urlsafe(24)
        request.session["csrf_token"] = token
    return token


def verify_csrf(request: Request, token: str) -> None:
    expected = request.session.get("csrf_token") if hasattr(request, "session") else None
    if not expected or token != expected:
        raise HTTPException(status_code=400, detail="Invalid CSRF token")
