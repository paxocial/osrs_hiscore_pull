"""Rate limiting middleware for authentication endpoints."""

from datetime import datetime, timedelta
from functools import wraps
from typing import Callable

from fastapi import Request, HTTPException

from database.connection import DatabaseConnection


def parse_limit(limit: str) -> tuple[int, int]:
    """
    Parse rate limit string into count and period in seconds.

    Args:
        limit: String like "5/minute" or "10/hour"

    Returns:
        Tuple of (count, period_in_seconds)

    Examples:
        "5/minute" -> (5, 60)
        "10/hour" -> (10, 3600)
        "3/day" -> (3, 86400)
    """
    count_str, period_str = limit.split("/")
    count = int(count_str)

    period_map = {
        "second": 1,
        "minute": 60,
        "hour": 3600,
        "day": 86400,
    }

    period = period_map.get(period_str, 60)  # Default to minute
    return count, period


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request.

    Checks X-Forwarded-For header first (for nginx proxy), then X-Real-IP,
    then falls back to request.client.host.

    Args:
        request: FastAPI Request object

    Returns:
        IP address string
    """
    # Check X-Forwarded-For (nginx proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take first IP if multiple (client, proxy1, proxy2, ...)
        return forwarded.split(",")[0].strip()

    # Check X-Real-IP
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fallback to direct connection IP
    return request.client.host if request.client else "unknown"


def is_rate_limited(ip: str, endpoint: str, limit_count: int, period_seconds: int) -> bool:
    """
    Check if IP has exceeded rate limit for endpoint.

    Args:
        ip: Client IP address
        endpoint: Request endpoint path
        limit_count: Maximum requests allowed in period
        period_seconds: Time window in seconds

    Returns:
        True if rate limit exceeded, False otherwise
    """
    db = DatabaseConnection()
    window_start = datetime.utcnow() - timedelta(seconds=period_seconds)

    with db.get_connection() as conn:
        # Get request count in current window
        row = conn.execute(
            """
            SELECT SUM(request_count) as total
            FROM rate_limit_store
            WHERE ip_address = ? AND endpoint = ? AND window_start >= ?
            """,
            (ip, endpoint, window_start.isoformat())
        ).fetchone()

        current_count = row["total"] if row and row["total"] else 0
        return current_count >= limit_count


def record_request(ip: str, endpoint: str) -> None:
    """
    Record a request in the rate limit store.

    Uses INSERT OR REPLACE to increment counter if record exists for current window,
    or creates new record if it doesn't.

    Args:
        ip: Client IP address
        endpoint: Request endpoint path
    """
    db = DatabaseConnection()

    # Round to current minute for window_start
    window_start = datetime.utcnow().replace(second=0, microsecond=0)

    with db.get_connection() as conn:
        # Try to increment existing record
        result = conn.execute(
            """
            UPDATE rate_limit_store
            SET request_count = request_count + 1
            WHERE ip_address = ? AND endpoint = ? AND window_start = ?
            """,
            (ip, endpoint, window_start.isoformat())
        )

        # If no record exists, insert new one
        if result.rowcount == 0:
            conn.execute(
                """
                INSERT INTO rate_limit_store (ip_address, endpoint, window_start, request_count)
                VALUES (?, ?, ?, 1)
                """,
                (ip, endpoint, window_start.isoformat())
            )

        conn.commit()


def rate_limit(limit: str) -> Callable:
    """
    Decorator for route-specific rate limiting.

    Usage:
        @router.post("/auth/login")
        @rate_limit("5/minute")
        async def login_submit(request: Request, ...):
            # Login logic

    Args:
        limit: Rate limit string (e.g., "5/minute", "10/hour")

    Returns:
        Decorator function
    """
    count, period = parse_limit(limit)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                request = kwargs.get("request")

            if not request:
                raise ValueError("rate_limit decorator requires Request parameter")

            # Get client IP and endpoint
            ip = get_client_ip(request)
            endpoint = request.url.path

            # Check rate limit
            if is_rate_limited(ip, endpoint, count, period):
                raise HTTPException(
                    status_code=429,
                    detail=f"Too many requests. Limit: {count} per {period}s. Please try again later."
                )

            # Record this request
            record_request(ip, endpoint)

            # Call original function
            return await func(*args, **kwargs)

        return wrapper
    return decorator
