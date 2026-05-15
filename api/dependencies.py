"""FastAPI dependencies and middleware for OSRS Analytics API."""

from __future__ import annotations

import hashlib
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Generator
from fastapi import Depends, HTTPException, status, Query, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from api.schemas import (
    AccountQueryParams,
    SnapshotQueryParams,
    AnalyticsQueryParams
)
from database.connection import DatabaseConnection

logger = logging.getLogger(__name__)

# Security setup (optional for future use)
security = HTTPBearer(auto_error=False)

# Use per-request connections configured via shared helper (thread-safe).
_shared_db = DatabaseConnection(reuse_connection=False, check_same_thread=False)


def get_database_connection() -> Generator[sqlite3.Connection, None, None]:
    """Dependency to get database connection."""
    try:
        with _shared_db.get_connection() as conn:
            yield conn
    except HTTPException:
        raise
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed"
        )


def get_optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """Optional authentication dependency for future use."""
    if credentials:
        return credentials.credentials
    return None


async def require_plugin_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    conn: sqlite3.Connection = Depends(get_database_connection)
) -> dict:
    """
    Require valid API token with 'plugin' scope.

    Args:
        x_api_key: API key from X-API-Key header
        conn: Database connection

    Returns:
        Dict with token metadata: {id, user_id, scopes, label}

    Raises:
        HTTPException: 401 if token missing/invalid/revoked, 403 if missing plugin scope
    """
    # Check if API key is provided
    if not x_api_key:
        logger.warning("Plugin API request missing X-API-Key header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Include X-API-Key header."
        )

    # Hash the token using SHA-256 (matching pattern from web/services/auth.py)
    token_hash = hashlib.sha256(x_api_key.encode("utf-8")).hexdigest()

    # Query api_tokens table for matching non-revoked token
    token_row = conn.execute(
        """
        SELECT id, user_id, scopes, label
        FROM api_tokens
        WHERE token_hash = ? AND revoked_at IS NULL
        """,
        (token_hash,)
    ).fetchone()

    # Check if token exists and is valid
    if not token_row:
        logger.warning(f"Invalid or revoked API token attempted")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key"
        )

    token = dict(token_row)

    # Validate that token has exact plugin scope token
    scopes = parse_token_scopes(token.get("scopes", ""))
    if "plugin" not in scopes and "plugin:ingest" not in scopes:
        logger.warning(f"API token {token['id']} lacks 'plugin' scope (has: {scopes})")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not have 'plugin' scope"
        )

    # Update last_used_at timestamp
    conn.execute(
        "UPDATE api_tokens SET last_used_at = CURRENT_TIMESTAMP WHERE id = ?",
        (token["id"],)
    )
    conn.commit()

    logger.info(f"Plugin API access authorized for token {token['id']} (user {token['user_id']})")

    return token


def parse_token_scopes(scopes: str) -> set[str]:
    """Parse comma/space-delimited scope strings into exact tokens."""
    if not scopes:
        return set()
    normalized = scopes.replace(",", " ")
    return {item.strip() for item in normalized.split() if item.strip()}


async def require_plugin_ingest_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    conn: sqlite3.Connection = Depends(get_database_connection),
) -> dict:
    """Require token valid for ledger ingest operations."""
    token = await require_plugin_key(x_api_key=x_api_key, conn=conn)
    scopes = parse_token_scopes(token.get("scopes", ""))
    if "plugin:ingest" not in scopes and "plugin" not in scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not have ledger ingest scope",
        )
    return token


def parse_account_query_params(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    active_only: bool = Query(True, description="Only show active accounts"),
    search: Optional[str] = Query(None, min_length=1, description="Search term")
) -> AccountQueryParams:
    """Parse and validate account query parameters."""
    return AccountQueryParams(
        page=page,
        page_size=page_size,
        active_only=active_only,
        search=search
    )


def parse_snapshot_query_params(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    account_name: Optional[str] = Query(None, description="Filter by account name"),
    mode: Optional[str] = Query(None, description="Filter by game mode"),
    start_date: Optional[str] = Query(None, description="Filter start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="Filter end date (ISO format)"),
    include_skills: bool = Query(False, description="Include skill data"),
    include_activities: bool = Query(False, description="Include activity data")
) -> SnapshotQueryParams:
    """Parse and validate snapshot query parameters."""
    # Parse dates if provided
    from datetime import datetime

    parsed_start_date = None
    parsed_end_date = None

    if start_date:
        try:
            parsed_start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
            )

    if end_date:
        try:
            parsed_end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
            )

    # Validate mode if provided
    if mode:
        from core.constants import GAME_MODES
        if mode not in GAME_MODES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid mode: {mode}. Valid modes: {list(GAME_MODES.keys())}"
            )

    return SnapshotQueryParams(
        page=page,
        page_size=page_size,
        account_name=account_name,
        mode=mode,
        start_date=parsed_start_date,
        end_date=parsed_end_date,
        include_skills=include_skills,
        include_activities=include_activities
    )


def parse_analytics_query_params(
    account_name: str = Query(..., description="Account name"),
    start_date: Optional[str] = Query(None, description="Analysis start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="Analysis end date (ISO format)"),
    skills: Optional[str] = Query(None, description="Comma-separated list of skills"),
    include_deltas: bool = Query(True, description="Include delta calculations")
) -> AnalyticsQueryParams:
    """Parse and validate analytics query parameters."""
    # Parse dates if provided
    from datetime import datetime

    parsed_start_date = None
    parsed_end_date = None

    if start_date:
        try:
            parsed_start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
            )

    if end_date:
        try:
            parsed_end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
            )

    # Parse skills if provided
    parsed_skills = None
    if skills:
        parsed_skills = [skill.strip() for skill in skills.split(',') if skill.strip()]

        # Validate skill names
        from core.constants import SKILLS
        for skill in parsed_skills:
            if skill.lower() not in [s.lower() for s in SKILLS]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid skill: {skill}. Valid skills: {SKILLS}"
                )

    return AnalyticsQueryParams(
        account_name=account_name,
        start_date=parsed_start_date,
        end_date=parsed_end_date,
        skills=parsed_skills,
        include_deltas=include_deltas
    )


def validate_account_exists(
    account_name: str,
    conn: sqlite3.Connection = Depends(get_database_connection)
) -> int:
    """Validate that an account exists and return its ID."""
    # Check if account exists in database
    account = conn.execute(
        "SELECT id FROM accounts WHERE name = ?",
        (account_name,)
    ).fetchone()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account '{account_name}' not found"
        )

    return account["id"]


def get_snapshot_or_404(
    snapshot_id: str,
    conn: sqlite3.Connection = Depends(get_database_connection)
) -> dict:
    """Get snapshot by ID or raise 404."""
    # Get snapshot metadata
    snapshot = conn.execute(
        """
        SELECT s.*, a.name as account_name
        FROM snapshots s
        JOIN accounts a ON s.account_id = a.id
        WHERE s.snapshot_id = ?
        """,
        (snapshot_id,)
    ).fetchone()

    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Snapshot '{snapshot_id}' not found"
        )

    return dict(snapshot)


# Rate limiting middleware (simplified version)
class RateLimiter:
    """Simple in-memory rate limiter for development."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}

    def is_allowed(self, client_ip: str) -> bool:
        """Check if client is allowed to make a request."""
        import time

        now = time.time()
        window_start = now - self.window_seconds

        # Clean old entries
        if client_ip in self.requests:
            self.requests[client_ip] = [
                req_time for req_time in self.requests[client_ip]
                if req_time > window_start
            ]
        else:
            self.requests[client_ip] = []

        # Check if under limit
        if len(self.requests[client_ip]) >= self.max_requests:
            return False

        # Add current request
        self.requests[client_ip].append(now)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter(max_requests=100, window_seconds=60)


class TokenRateLimiter:
    """Per-token rate limiter using sliding window."""

    def __init__(self, max_requests: int, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[int, list[float]] = {}

    def is_allowed(self, token_id: int) -> bool:
        """Check if token is allowed to make a request."""
        import time

        now = time.time()
        window_start = now - self.window_seconds

        # Clean old entries
        if token_id in self.requests:
            self.requests[token_id] = [
                req_time for req_time in self.requests[token_id]
                if req_time > window_start
            ]
        else:
            self.requests[token_id] = []

        # Check if under limit
        if len(self.requests[token_id]) >= self.max_requests:
            return False

        # Add current request
        self.requests[token_id].append(now)
        return True


# Global token rate limiter instances for plugin endpoints
plugin_rate_limiter = TokenRateLimiter(max_requests=30, window_seconds=60)
batch_rate_limiter = TokenRateLimiter(max_requests=10, window_seconds=60)
