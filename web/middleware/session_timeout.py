"""
Session Timeout Middleware
Phase 3, Task 3.2: Session Activity Timeout

Tracks last activity timestamp in session and clears session after 30 minutes
of inactivity. Reduces attack window for stolen session cookies.
"""

from datetime import datetime, timedelta
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse


class SessionTimeoutMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce session idle timeout.

    Tracks last_activity timestamp in session. If more than 30 minutes have
    passed since last activity, clears session and redirects to login.
    Updates last_activity on every request.
    """

    TIMEOUT_MINUTES = 30
    EXCLUDED_PATHS = ["/auth/login", "/auth/register", "/static/"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Check session timeout and update activity timestamp.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response or redirect to login if session timed out
        """
        # Skip timeout check for excluded paths (login, register, static assets)
        if any(request.url.path.startswith(path) for path in self.EXCLUDED_PATHS):
            return await call_next(request)

        # Check if user has active session
        if not hasattr(request, "session"):
            return await call_next(request)

        user_id = request.session.get("user_id")
        if not user_id:
            # No active session, proceed normally
            return await call_next(request)

        # Get last activity timestamp from session
        last_activity_str = request.session.get("last_activity")
        now = datetime.utcnow()

        if last_activity_str:
            try:
                last_activity = datetime.fromisoformat(last_activity_str)
                idle_time = now - last_activity

                # Check if session has timed out
                if idle_time > timedelta(minutes=self.TIMEOUT_MINUTES):
                    # Clear session and redirect to login
                    request.session.clear()
                    return RedirectResponse(
                        url=f"/auth/login?timeout=1&return_url={request.url.path}",
                        status_code=302
                    )
            except (ValueError, TypeError):
                # Invalid timestamp format, update and continue
                pass

        # Update last activity timestamp
        request.session["last_activity"] = now.isoformat()

        return await call_next(request)
