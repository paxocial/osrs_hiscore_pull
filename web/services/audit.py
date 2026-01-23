"""
Audit Logging Service
Phase 3, Task 3.1: Audit Logging Infrastructure

Provides centralized audit logging for authentication events, security events,
and admin actions. All events are logged to the audit_log table with IP address,
user agent, and metadata for forensic analysis.
"""

from datetime import datetime
from typing import Optional, Dict, Any
import json

from fastapi import Request
from database.connection import DatabaseConnection


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


def _get_user_agent(request: Request) -> Optional[str]:
    """Extract user agent string from request headers."""
    if request is None:
        return None
    return request.headers.get("User-Agent")


def log_auth_event(
    event_type: str,
    request: Optional[Request] = None,
    user_id: Optional[int] = None,
    email: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log an authentication or security event to audit trail.

    Args:
        event_type: Type of event (login_success, login_failure, logout, register,
                   token_create, token_revoke, password_change, account_locked, etc.)
        request: FastAPI Request object (used to extract IP and user agent)
        user_id: User ID if event associated with specific user
        email: Email address if user_id not available
        ip_address: Override IP address (if not extracting from request)
        user_agent: Override user agent (if not extracting from request)
        metadata: Additional event data to store as JSON

    Example:
        log_auth_event("login_success", request=request, user_id=user["id"])
        log_auth_event("login_failure", request=request, email=email,
                      metadata={"reason": "invalid_password"})
    """
    # Extract IP and user agent from request if not provided
    if request is not None:
        if ip_address is None:
            ip_address = _get_client_ip(request)
        if user_agent is None:
            user_agent = _get_user_agent(request)

    # Serialize metadata to JSON
    metadata_json = json.dumps(metadata or {})

    db = DatabaseConnection()
    with db.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO audit_log (event_type, user_id, email, ip_address, user_agent, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_type,
                user_id,
                email,
                ip_address,
                user_agent,
                metadata_json,
                datetime.utcnow().isoformat(),
            )
        )
        conn.commit()


def log_admin_action(
    admin_id: int,
    action_type: str,
    metadata: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None
) -> None:
    """
    Log an admin action to audit trail.

    Admin actions are logged with event_type prefixed by "admin_" to distinguish
    them from regular auth events.

    Args:
        admin_id: User ID of admin performing action
        action_type: Type of action (e.g., "disable_user", "unlock_account", "toggle_admin")
        metadata: Additional action data (e.g., target_user_id, changes made)
        request: FastAPI Request object for IP/user agent extraction

    Example:
        log_admin_action(admin_id=1, action_type="disable_user",
                        metadata={"target_user_id": 42}, request=request)
    """
    log_auth_event(
        event_type=f"admin_{action_type}",
        request=request,
        user_id=admin_id,
        metadata=metadata
    )


def log_security_event(
    event_type: str,
    user_id: Optional[int] = None,
    email: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log a security-related event to audit trail.

    This is a convenience wrapper around log_auth_event for cases where
    a Request object is not available but IP/user agent are known.

    Args:
        event_type: Type of security event
        user_id: User ID if event associated with specific user
        email: Email address if user_id not available
        ip_address: IP address of actor
        user_agent: User agent string
        metadata: Additional event data

    Example:
        log_security_event("admin_access_denied", user_id=user_id,
                          ip_address=ip, metadata={"endpoint": "/admin/users"})
    """
    log_auth_event(
        event_type=event_type,
        request=None,
        user_id=user_id,
        email=email,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata
    )
