"""
Admin Routes
Phase 4, Tasks 4.2-4.8: Admin UI Routes and Templates

Provides admin-only web interface for system management, user administration,
audit log viewing, rate limit management, clan oversight, and configuration viewing.

All routes protected by @require_admin middleware and all actions logged to audit trail.
"""

from typing import Optional
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from web.middleware.admin import require_admin, get_current_admin
from web.services.audit import log_admin_action
from database.connection import DatabaseConnection
from config.settings import AppConfig

templates = Jinja2Templates(directory="web/templates")
router = APIRouter(prefix="/admin", tags=["admin"])


# ===================================
# Admin Dashboard
# ===================================
@router.get("/", response_class=HTMLResponse)
@require_admin
async def admin_dashboard(request: Request):
    """
    Admin dashboard with system health overview.

    Displays:
    - Total users, active users, locked accounts
    - Total clans
    - Recent logins (last 24 hours)
    - Failed logins (last 24 hours)
    """
    admin = await get_current_admin(request)
    db = DatabaseConnection()
    with db.get_connection() as conn:
        stats = {
            "total_users": conn.execute("SELECT COUNT(*) as count FROM users").fetchone()["count"],
            "active_users": conn.execute("SELECT COUNT(*) as count FROM users WHERE is_active = 1").fetchone()["count"],
            "locked_accounts": conn.execute(
                "SELECT COUNT(*) as count FROM users WHERE locked_until IS NOT NULL AND locked_until > datetime('now')"
            ).fetchone()["count"],
            "total_clans": conn.execute("SELECT COUNT(*) as count FROM clans").fetchone()["count"],
            "recent_logins": conn.execute(
                "SELECT COUNT(*) as count FROM audit_log WHERE event_type = 'login_success' AND created_at > datetime('now', '-24 hours')"
            ).fetchone()["count"],
            "failed_logins_24h": conn.execute(
                "SELECT COUNT(*) as count FROM audit_log WHERE event_type = 'login_failure' AND created_at > datetime('now', '-24 hours')"
            ).fetchone()["count"],
        }

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "admin": admin,
        "stats": stats,
    })


# ===================================
# User Management
# ===================================
@router.get("/users", response_class=HTMLResponse)
@require_admin
async def admin_users_list(request: Request, page: int = 1, search: str = ""):
    """
    List all users with search and pagination.

    Query Parameters:
    - page: Page number (1-indexed)
    - search: Email search filter (substring match)
    """
    admin = await get_current_admin(request)
    db = DatabaseConnection()
    with db.get_connection() as conn:
        page_size = 50
        offset = (page - 1) * page_size

        query = """
            SELECT id, email, is_active, is_admin, created_at, last_login_at,
                   failed_login_attempts, locked_until, email_verified
            FROM users
        """
        params = []

        if search:
            query += " WHERE email LIKE ?"
            params.append(f"%{search}%")

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([page_size, offset])

        users = conn.execute(query, params).fetchall()

        # Get total count for pagination
        count_query = "SELECT COUNT(*) as count FROM users"
        if search:
            count_query += " WHERE email LIKE ?"
            total_users = conn.execute(count_query, [f"%{search}%"]).fetchone()["count"]
        else:
            total_users = conn.execute(count_query).fetchone()["count"]

    return templates.TemplateResponse("admin/users.html", {
        "request": request,
        "admin": admin,
        "users": users,
        "page": page,
        "total_pages": (total_users + page_size - 1) // page_size,
        "search": search,
    })


@router.post("/users/{user_id}/toggle-active")
@require_admin
async def admin_toggle_user_active(request: Request, user_id: int):
    """Enable or disable a user account."""
    admin = await get_current_admin(request)
    db = DatabaseConnection()
    with db.get_connection() as conn:
        user = conn.execute("SELECT is_active FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return JSONResponse({"ok": False, "error": "User not found"}, status_code=404)

        new_status = 0 if user["is_active"] else 1

        conn.execute("UPDATE users SET is_active = ? WHERE id = ?", (new_status, user_id))
        conn.commit()

    # Log admin action
    log_admin_action(admin["id"], "toggle_user_active", {"target_user_id": user_id, "new_status": new_status}, request)

    return JSONResponse({"ok": True, "new_status": new_status})


@router.post("/users/{user_id}/toggle-admin")
@require_admin
async def admin_toggle_user_admin(request: Request, user_id: int):
    """Grant or revoke admin role."""
    admin = await get_current_admin(request)

    # Prevent self-demotion
    if user_id == admin["id"]:
        return JSONResponse({"ok": False, "error": "Cannot modify own admin status"}, status_code=400)

    db = DatabaseConnection()
    with db.get_connection() as conn:
        user = conn.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return JSONResponse({"ok": False, "error": "User not found"}, status_code=404)

        new_status = 0 if user["is_admin"] else 1

        conn.execute("UPDATE users SET is_admin = ? WHERE id = ?", (new_status, user_id))
        conn.commit()

    # Log admin action
    log_admin_action(admin["id"], "toggle_user_admin", {"target_user_id": user_id, "new_status": new_status}, request)

    return JSONResponse({"ok": True, "new_status": new_status})


@router.post("/users/{user_id}/unlock")
@require_admin
async def admin_unlock_user(request: Request, user_id: int):
    """Manually unlock a locked user account."""
    admin = await get_current_admin(request)
    db = DatabaseConnection()
    with db.get_connection() as conn:
        conn.execute("UPDATE users SET locked_until = NULL, failed_login_attempts = 0 WHERE id = ?", (user_id,))
        conn.commit()

    # Log admin action
    log_admin_action(admin["id"], "unlock_user", {"target_user_id": user_id}, request)

    return JSONResponse({"ok": True})


# ===================================
# Audit Log Viewer
# ===================================
@router.get("/audit-logs", response_class=HTMLResponse)
@require_admin
async def admin_audit_logs(
    request: Request,
    page: int = 1,
    event_type: str = "",
    user_id: Optional[int] = None,
    days: int = 7
):
    """
    View audit logs with filtering.

    Query Parameters:
    - page: Page number (1-indexed)
    - event_type: Filter by event type (e.g., "login_success")
    - user_id: Filter by user ID
    - days: Time range in days (default: 7)
    """
    admin = await get_current_admin(request)
    db = DatabaseConnection()
    with db.get_connection() as conn:
        page_size = 100
        offset = (page - 1) * page_size

        query = f"SELECT * FROM audit_log WHERE created_at > datetime('now', '-{days} days')"
        params = []

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([page_size, offset])

        logs = conn.execute(query, params).fetchall()

        # Get total count
        count_query = f"SELECT COUNT(*) as count FROM audit_log WHERE created_at > datetime('now', '-{days} days')"
        count_params = []
        if event_type:
            count_query += " AND event_type = ?"
            count_params.append(event_type)
        if user_id:
            count_query += " AND user_id = ?"
            count_params.append(user_id)

        total_logs = conn.execute(count_query, count_params).fetchone()["count"]

        # Get unique event types for filter dropdown
        event_types = conn.execute("SELECT DISTINCT event_type FROM audit_log ORDER BY event_type").fetchall()

    return templates.TemplateResponse("admin/audit_logs.html", {
        "request": request,
        "admin": admin,
        "logs": logs,
        "page": page,
        "total_pages": (total_logs + page_size - 1) // page_size,
        "event_types": event_types,
        "selected_event_type": event_type,
        "selected_user_id": user_id,
        "days": days,
    })


# ===================================
# Rate Limit Management
# ===================================
@router.get("/rate-limits", response_class=HTMLResponse)
@require_admin
async def admin_rate_limits(request: Request):
    """View rate limit status and blocked IPs."""
    admin = await get_current_admin(request)
    db = DatabaseConnection()
    with db.get_connection() as conn:
        # Get currently blocked IPs (those exceeding rate limits)
        blocked_ips = conn.execute("""
            SELECT ip_address, endpoint, request_count, window_start
            FROM rate_limit_store
            WHERE window_start > datetime('now', '-1 hour')
            ORDER BY request_count DESC
        """).fetchall()

    return templates.TemplateResponse("admin/rate_limits.html", {
        "request": request,
        "admin": admin,
        "blocked_ips": blocked_ips,
    })


@router.post("/rate-limits/unblock")
@require_admin
async def admin_unblock_ip(request: Request, ip_address: str = Form(...)):
    """Manually unblock an IP address."""
    admin = await get_current_admin(request)
    db = DatabaseConnection()
    with db.get_connection() as conn:
        conn.execute("DELETE FROM rate_limit_store WHERE ip_address = ?", (ip_address,))
        conn.commit()

    # Log admin action
    log_admin_action(admin["id"], "unblock_ip", {"ip_address": ip_address}, request)

    return JSONResponse({"ok": True})


# ===================================
# Clan Oversight
# ===================================
@router.get("/clans", response_class=HTMLResponse)
@require_admin
async def admin_clans(request: Request, page: int = 1):
    """View all clans with admin oversight."""
    admin = await get_current_admin(request)
    db = DatabaseConnection()
    with db.get_connection() as conn:
        page_size = 50
        offset = (page - 1) * page_size

        clans = conn.execute("""
            SELECT c.*, u.email as owner_email
            FROM clans c
            JOIN users u ON c.owner_user_id = u.id
            ORDER BY c.created_at DESC
            LIMIT ? OFFSET ?
        """, (page_size, offset)).fetchall()

        total_clans = conn.execute("SELECT COUNT(*) as count FROM clans").fetchone()["count"]

    return templates.TemplateResponse("admin/clans.html", {
        "request": request,
        "admin": admin,
        "clans": clans,
        "page": page,
        "total_pages": (total_clans + page_size - 1) // page_size,
    })


# ===================================
# System Configuration UI
# ===================================
@router.get("/config", response_class=HTMLResponse)
@require_admin
async def admin_config(request: Request):
    """View system configuration (read-only)."""
    admin = await get_current_admin(request)
    config = AppConfig()

    # Build config view (read-only for now - editing requires restart)
    config_data = {
        "environment": config.environment,
        "security": {
            "session_max_age": config.security.session_max_age,
            "https_only": config.security.https_only,
            "same_site": config.security.same_site,
        },
        "rate_limits": {
            "login": config.rate_limits.login_limit,
            "register": config.rate_limits.register_limit,
            "password_reset": config.rate_limits.password_reset_limit,
            "api_token": config.rate_limits.api_token_limit,
        },
        "password": {
            "min_length": config.password.min_length,
            "require_uppercase": config.password.require_uppercase,
            "require_lowercase": config.password.require_lowercase,
            "require_digit": config.password.require_digit,
            "require_special": config.password.require_special,
        },
        "account": {
            "lockout_threshold": config.account.lockout_threshold,
            "lockout_duration_minutes": config.account.lockout_duration_minutes,
            "email_verification_required": config.account.email_verification_required,
            "verification_token_expiry_hours": config.account.verification_token_expiry_hours,
        },
        "features": {
            "audit_logging": config.features.enable_audit_logging,
            "rate_limiting": config.features.enable_rate_limiting,
            "email_verification": config.features.enable_email_verification,
            "admin_ui": config.features.enable_admin_ui,
        },
    }

    return templates.TemplateResponse("admin/config.html", {
        "request": request,
        "admin": admin,
        "config": config_data,
    })
