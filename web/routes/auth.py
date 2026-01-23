"""Auth routes for register/login/logout and API token management."""

from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from web.deps import auth_service, get_current_user, require_user, get_csrf_token, verify_csrf
from web.middleware.rate_limit import rate_limit
from config.settings import AppConfig
from web.services.audit import log_auth_event

templates = Jinja2Templates(directory="web/templates")
router = APIRouter()


@router.get("/auth/register", response_class=HTMLResponse)
async def register_form(request: Request):
    return templates.TemplateResponse(
        "auth_register.html",
        {"request": request, "user": get_current_user(request), "csrf_token": get_csrf_token(request)},
    )


@router.post("/auth/register", response_class=HTMLResponse)
@rate_limit(AppConfig().rate_limits.register_limit)
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

    # Try to register user (catches password validation errors)
    # Get base URL from request
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    try:
        created_id = auth_service.register(email, password, base_url)
    except ValueError as e:
        # Password validation failed
        return templates.TemplateResponse(
            "auth_register.html",
            {
                "request": request,
                "error": str(e),
                "user": get_current_user(request),
                "csrf_token": get_csrf_token(request),
            },
            status_code=400,
        )

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

    # Log registration
    config = AppConfig()
    if config.features.enable_audit_logging:
        log_auth_event("register", request=request, user_id=created_id, email=email)

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
@rate_limit(AppConfig().rate_limits.login_limit)
async def login_submit(request: Request, email: str = Form(...), password: str = Form(...), csrf_token: str = Form(...)):
    verify_csrf(request, csrf_token)
    user = auth_service.authenticate(email, password, request)
    if not user:
        return templates.TemplateResponse(
            "auth_login.html",
            {"request": request, "error": "Invalid credentials.", "user": None},
            status_code=401,
        )
    # Regenerate session to prevent fixation attacks
    old_csrf = request.session.get("csrf_token")
    request.session.clear()
    request.session["csrf_token"] = old_csrf  # Preserve CSRF token
    request.session["user_id"] = user["id"]
    request.session["is_admin"] = user.get("is_admin", 0) == 1  # Load admin flag for role checking
    return RedirectResponse(url="/", status_code=303)


@router.post("/auth/logout")
async def logout(request: Request, csrf_token: str = Form(...)):
    verify_csrf(request, csrf_token)

    # Log logout event before clearing session
    user_id = request.session.get("user_id")
    config = AppConfig()
    if user_id and config.features.enable_audit_logging:
        log_auth_event("logout", request=request, user_id=user_id)

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
@rate_limit(AppConfig().rate_limits.api_token_limit)
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


@router.get("/auth/forgot-password", response_class=HTMLResponse)
async def forgot_password_form(request: Request):
    """
    Forgot password form.
    Phase 3, Task 3.4: Password Reset Flow
    """
    return templates.TemplateResponse(
        "auth_forgot_password.html",
        {"request": request, "user": get_current_user(request), "csrf_token": get_csrf_token(request)},
    )


@router.post("/auth/forgot-password", response_class=HTMLResponse)
@rate_limit(AppConfig().rate_limits.password_reset_limit)
async def forgot_password_submit(request: Request, email: str = Form(...), csrf_token: str = Form(...)):
    """
    Process forgot password request - generate token and send reset email.
    Phase 3, Task 3.4: Password Reset Flow
    """
    from datetime import datetime, timedelta
    import secrets
    from database.connection import DatabaseConnection
    from web.services.email_sender import send_password_reset_email

    verify_csrf(request, csrf_token)

    db = DatabaseConnection()
    with db.get_connection() as conn:
        # Find user by email
        user = conn.execute("SELECT id, email FROM users WHERE email = ? AND is_active = 1", (email,)).fetchone()

        # Always show success message to prevent email enumeration
        success_message = "If an account exists with that email address, you will receive a password reset link shortly."

        if user:
            user = dict(user)

            # Generate reset token (1 hour expiry)
            token = secrets.token_urlsafe(32)
            expires_at = (datetime.utcnow() + timedelta(hours=1)).isoformat()

            # Store token in database
            conn.execute(
                "INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (?, ?, ?)",
                (user["id"], token, expires_at)
            )
            conn.commit()

            # Send reset email
            base_url = f"{request.url.scheme}://{request.url.netloc}"
            send_password_reset_email(user["email"], token, base_url)

    return templates.TemplateResponse(
        "auth_forgot_password.html",
        {
            "request": request,
            "user": get_current_user(request),
            "csrf_token": get_csrf_token(request),
            "success": success_message,
        },
    )


@router.get("/auth/reset-password", response_class=HTMLResponse)
async def reset_password_form(request: Request, token: str):
    """
    Password reset form (accessed via email link).
    Phase 3, Task 3.4: Password Reset Flow
    """
    from datetime import datetime
    from database.connection import DatabaseConnection

    db = DatabaseConnection()
    with db.get_connection() as conn:
        # Validate token exists and not expired
        reset_token = conn.execute(
            "SELECT id, user_id, expires_at, used_at FROM password_reset_tokens WHERE token = ?",
            (token,)
        ).fetchone()

        if not reset_token:
            return templates.TemplateResponse(
                "message.html",
                {
                    "request": request,
                    "user": get_current_user(request),
                    "title": "Invalid Token",
                    "message": "This password reset link is invalid or has already been used.",
                    "error": True,
                },
                status_code=400,
            )

        reset_token = dict(reset_token)

        # Check if already used
        if reset_token["used_at"]:
            return templates.TemplateResponse(
                "message.html",
                {
                    "request": request,
                    "user": get_current_user(request),
                    "title": "Token Already Used",
                    "message": "This password reset link has already been used. Please request a new one if you still need to reset your password.",
                    "error": True,
                },
                status_code=400,
            )

        # Check if expired
        expires_at = datetime.fromisoformat(reset_token["expires_at"])
        if datetime.utcnow() > expires_at:
            return templates.TemplateResponse(
                "message.html",
                {
                    "request": request,
                    "user": get_current_user(request),
                    "title": "Token Expired",
                    "message": "This password reset link has expired. Please request a new one.",
                    "error": True,
                },
                status_code=400,
            )

    # Token valid, show reset password form
    return templates.TemplateResponse(
        "auth_reset_password.html",
        {"request": request, "user": get_current_user(request), "token": token, "csrf_token": get_csrf_token(request)},
    )


@router.post("/auth/reset-password", response_class=HTMLResponse)
async def reset_password_submit(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    csrf_token: str = Form(...)
):
    """
    Process password reset - validate token and update password.
    Phase 3, Task 3.4: Password Reset Flow
    """
    from datetime import datetime
    from database.connection import DatabaseConnection
    from web.services.password_validator import validate_password_strength

    verify_csrf(request, csrf_token)

    # Check passwords match
    if password != confirm_password:
        return templates.TemplateResponse(
            "auth_reset_password.html",
            {
                "request": request,
                "user": get_current_user(request),
                "token": token,
                "csrf_token": get_csrf_token(request),
                "error": "Passwords do not match.",
            },
            status_code=400,
        )

    # Validate password strength
    is_valid, error_msg = validate_password_strength(password)
    if not is_valid:
        return templates.TemplateResponse(
            "auth_reset_password.html",
            {
                "request": request,
                "user": get_current_user(request),
                "token": token,
                "csrf_token": get_csrf_token(request),
                "error": error_msg,
            },
            status_code=400,
        )

    db = DatabaseConnection()
    with db.get_connection() as conn:
        # Validate token again
        reset_token = conn.execute(
            "SELECT id, user_id, expires_at, used_at FROM password_reset_tokens WHERE token = ?",
            (token,)
        ).fetchone()

        if not reset_token:
            return templates.TemplateResponse(
                "message.html",
                {
                    "request": request,
                    "user": get_current_user(request),
                    "title": "Invalid Token",
                    "message": "This password reset link is invalid.",
                    "error": True,
                },
                status_code=400,
            )

        reset_token = dict(reset_token)

        # Check if already used
        if reset_token["used_at"]:
            return templates.TemplateResponse(
                "message.html",
                {
                    "request": request,
                    "user": get_current_user(request),
                    "title": "Token Already Used",
                    "message": "This password reset link has already been used.",
                    "error": True,
                },
                status_code=400,
            )

        # Check if expired
        expires_at = datetime.fromisoformat(reset_token["expires_at"])
        if datetime.utcnow() > expires_at:
            return templates.TemplateResponse(
                "message.html",
                {
                    "request": request,
                    "user": get_current_user(request),
                    "title": "Token Expired",
                    "message": "This password reset link has expired.",
                    "error": True,
                },
                status_code=400,
            )

        # Update password
        from web.services.auth import _hash_password
        password_hash = _hash_password(password)
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (password_hash, reset_token["user_id"])
        )

        # Mark token as used
        conn.execute(
            "UPDATE password_reset_tokens SET used_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), reset_token["id"])
        )
        conn.commit()

    # Log password change event
    config = AppConfig()
    if config.features.enable_audit_logging:
        log_auth_event("password_change", request=request, user_id=reset_token["user_id"],
                      metadata={"method": "password_reset"})

    return templates.TemplateResponse(
        "message.html",
        {
            "request": request,
            "user": get_current_user(request),
            "title": "Password Reset Successful",
            "message": "Your password has been reset successfully. You can now log in with your new password.",
            "success": True,
        },
    )


@router.get("/auth/verify", response_class=HTMLResponse)
async def verify_email(request: Request, token: str):
    """
    Email verification endpoint.

    Validates verification token and marks email as verified.
    Phase 3, Task 3.3: Email Verification Flow
    """
    from datetime import datetime
    from database.connection import DatabaseConnection

    config = AppConfig()

    # Check if email verification is enabled
    if not config.features.enable_email_verification:
        return templates.TemplateResponse(
            "message.html",
            {
                "request": request,
                "user": get_current_user(request),
                "title": "Email Verification Disabled",
                "message": "Email verification is not enabled on this system.",
            },
        )

    db = DatabaseConnection()
    with db.get_connection() as conn:
        # Find user with this verification token
        user = conn.execute(
            "SELECT id, email, email_verified, verification_expires FROM users WHERE verification_token = ?",
            (token,)
        ).fetchone()

        if not user:
            return templates.TemplateResponse(
                "message.html",
                {
                    "request": request,
                    "user": get_current_user(request),
                    "title": "Invalid Token",
                    "message": "This verification link is invalid or has already been used.",
                    "error": True,
                },
                status_code=400,
            )

        user = dict(user)

        # Check if already verified
        if user["email_verified"]:
            return templates.TemplateResponse(
                "message.html",
                {
                    "request": request,
                    "user": get_current_user(request),
                    "title": "Already Verified",
                    "message": "This email address has already been verified. You can log in now.",
                },
            )

        # Check if token expired
        if user["verification_expires"]:
            expires = datetime.fromisoformat(user["verification_expires"])
            if datetime.utcnow() > expires:
                return templates.TemplateResponse(
                    "message.html",
                    {
                        "request": request,
                        "user": get_current_user(request),
                        "title": "Token Expired",
                        "message": "This verification link has expired. Please request a new verification email.",
                        "error": True,
                    },
                    status_code=400,
                )

        # Mark email as verified and clear token
        conn.execute(
            "UPDATE users SET email_verified = 1, verification_token = NULL, verification_expires = NULL WHERE id = ?",
            (user["id"],)
        )
        conn.commit()

    return templates.TemplateResponse(
        "message.html",
        {
            "request": request,
            "user": get_current_user(request),
            "title": "Email Verified!",
            "message": f"Your email address ({user['email']}) has been verified successfully. You can now log in.",
            "success": True,
        },
    )
