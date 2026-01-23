"""
Admin Middleware
Phase 4, Task 4.1: Admin Middleware and Role Checking

Provides role-based access control for admin-only endpoints. Uses @require_admin
decorator to protect routes and logs unauthorized access attempts to audit trail.
"""

from functools import wraps
from typing import Optional, Dict, Any

from fastapi import Request, HTTPException
from database.connection import DatabaseConnection


def require_admin(func):
    """
    Decorator to require admin role for route access.

    Checks request.session for user_id and is_admin flag. If user is not logged in
    or not an admin, raises HTTPException with 401/403 status and logs the attempt.

    Usage:
        @router.get("/admin/dashboard")
        @require_admin
        async def admin_dashboard(request: Request):
            # Admin-only logic
            pass

    Raises:
        HTTPException: 401 if not authenticated, 403 if not admin
    """
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        # Check if user is logged in
        user_id = request.session.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Check if user has admin role
        is_admin = request.session.get("is_admin", False)
        if not is_admin:
            # Log unauthorized admin access attempt
            from web.services.audit import log_security_event
            log_security_event(
                event_type="admin_access_denied",
                user_id=user_id,
                ip_address=_get_client_ip(request),
                metadata={"endpoint": request.url.path}
            )
            raise HTTPException(status_code=403, detail="Admin access required")

        return await func(request, *args, **kwargs)
    return wrapper


async def get_current_admin(request: Request) -> Dict[str, Any]:
    """
    Dependency injection for admin user retrieval.

    Fetches full user details from database and verifies admin status. This is
    used as a FastAPI dependency to provide admin user data to route handlers.

    Args:
        request: FastAPI Request object with session containing user_id and is_admin

    Returns:
        Dict containing user details (id, email, is_admin, created_at)

    Raises:
        HTTPException: 403 if user is not admin or not found

    Usage:
        @router.get("/admin/dashboard")
        @require_admin
        async def admin_dashboard(request: Request):
            admin = await get_current_admin(request)
            # Use admin["id"], admin["email"], etc.
    """
    user_id = request.session.get("user_id")
    is_admin = request.session.get("is_admin", False)

    if not user_id or not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Fetch full user details from database
    db = DatabaseConnection()
    with db.get_connection() as conn:
        user = conn.execute(
            "SELECT id, email, is_admin, created_at FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()

        if not user or not user["is_admin"]:
            raise HTTPException(status_code=403, detail="Admin access required")

        return dict(user)


def _get_client_ip(request: Request) -> Optional[str]:
    """
    Extract client IP address from request headers.

    Prioritizes X-Forwarded-For (nginx proxy) over X-Real-IP, falls back to
    request.client.host if neither header present.
    """
    if request is None:
        return None

    # Check X-Forwarded-For first (nginx proxy chain)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, take first (original client)
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP (alternative proxy header)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fallback to direct connection IP
    if hasattr(request, "client") and request.client:
        return request.client.host

    return None
