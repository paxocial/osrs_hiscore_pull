"""Server-side proxy for OSRS backend API endpoints.

Routes Council web requests to the OSRS backend (web.main:app) running
on a configurable port (default 8001).  Uses a persistent httpx client
with connection pooling for reliable same-host forwarding.
"""

from __future__ import annotations

import os
import re
from typing import Any, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse

router = APIRouter(tags=["osrs-proxy"])

# ---------------------------------------------------------------------------
# Backend connection config
# ---------------------------------------------------------------------------
DEFAULT_PORT = 8001

_BACKEND_TIMEOUT = httpx.Timeout(30.0, connect=10.0)

# Path-traversal guard: reject names/ids containing slash or double-dot
_UNSAFE_PATH_RE = re.compile(r"[/\\]|\.\.")


def _backend_base_url() -> str:
    """Resolve the OSRS backend base URL from environment or default."""
    port = os.environ.get("OSRS_BACKEND_PORT", str(DEFAULT_PORT))
    return f"http://127.0.0.1:{port}"


# Persistent client — connection pooling across all proxy requests.
_client = httpx.AsyncClient(
    base_url=_backend_base_url(),
    timeout=_BACKEND_TIMEOUT,
)


def _validate_path_param(value: str, label: str = "parameter") -> None:
    """Reject path parameters that could cause path traversal."""
    if _UNSAFE_PATH_RE.search(value):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {label}: must not contain '/' or '..'",
        )


# ---------------------------------------------------------------------------
# Error response helpers
# ---------------------------------------------------------------------------

_OFFLINE_BODY = {
    "detail": "OSRS backend is offline",
    "hint": "Start the backend from the Control Center",
}
_TIMEOUT_BODY = {"detail": "OSRS backend timed out"}
_PROXY_ERROR_BODY = {"detail": "Proxy error"}


def _handle_transport_error(exc: Exception) -> JSONResponse:
    """Map httpx transport errors to structured JSON error responses."""
    if isinstance(exc, httpx.ConnectError):
        return JSONResponse(content=_OFFLINE_BODY, status_code=503)
    if isinstance(exc, httpx.TimeoutException):
        return JSONResponse(content=_TIMEOUT_BODY, status_code=504)
    return JSONResponse(content=_PROXY_ERROR_BODY, status_code=502)


# ---------------------------------------------------------------------------
# Proxy helpers
# ---------------------------------------------------------------------------

async def _proxy_get(
    path: str,
    params: dict[str, Any] | None = None,
    *,
    raw_text: bool = False,
) -> JSONResponse | PlainTextResponse:
    """Forward a GET request to the OSRS backend."""
    cleaned_params = {k: v for k, v in (params or {}).items() if v is not None}
    try:
        resp = await _client.get(path, params=cleaned_params)
    except Exception as exc:
        return _handle_transport_error(exc)

    if resp.status_code >= 400:
        try:
            body = resp.json()
        except Exception:
            body = {"detail": resp.text}
        return JSONResponse(content=body, status_code=resp.status_code)

    if raw_text:
        content_type = resp.headers.get("content-type", "text/plain")
        return PlainTextResponse(
            content=resp.text,
            status_code=resp.status_code,
            media_type=content_type,
        )

    try:
        return JSONResponse(content=resp.json(), status_code=resp.status_code)
    except Exception:
        return PlainTextResponse(
            content=resp.text,
            status_code=resp.status_code,
        )


async def _proxy_post(
    path: str,
    body: Any = None,
) -> JSONResponse:
    """Forward a POST request to the OSRS backend."""
    try:
        resp = await _client.post(path, json=body)
    except Exception as exc:
        return _handle_transport_error(exc)

    if resp.status_code >= 400:
        try:
            body_json = resp.json()
        except Exception:
            body_json = {"detail": resp.text}
        return JSONResponse(content=body_json, status_code=resp.status_code)

    try:
        return JSONResponse(content=resp.json(), status_code=resp.status_code)
    except Exception:
        return JSONResponse(content={"detail": resp.text}, status_code=resp.status_code)


async def _proxy_delete(
    path: str,
) -> JSONResponse:
    """Forward a DELETE request to the OSRS backend."""
    try:
        resp = await _client.delete(path)
    except Exception as exc:
        return _handle_transport_error(exc)

    if resp.status_code >= 400:
        try:
            body = resp.json()
        except Exception:
            body = {"detail": resp.text}
        return JSONResponse(content=body, status_code=resp.status_code)

    if resp.status_code == 204:
        return JSONResponse(content=None, status_code=204)

    try:
        return JSONResponse(content=resp.json(), status_code=resp.status_code)
    except Exception:
        return JSONResponse(content={"detail": "deleted"}, status_code=resp.status_code)


# ===========================================================================
# Health
# ===========================================================================

@router.get("/api/osrs/health")
async def proxy_health() -> JSONResponse:
    """Proxy health check to OSRS backend."""
    return await _proxy_get("/api/health")


# ===========================================================================
# Accounts (6 endpoints)
# ===========================================================================

@router.get("/api/osrs/accounts")
async def proxy_list_accounts(
    page: Optional[int] = Query(None),
    page_size: Optional[int] = Query(None),
    active_only: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
) -> JSONResponse:
    """Proxy: list all accounts."""
    return await _proxy_get("/api/accounts/", params={
        "page": page,
        "page_size": page_size,
        "active_only": active_only,
        "search": search,
    })


@router.post("/api/osrs/accounts")
async def proxy_create_account(
    request: Request,
) -> JSONResponse:
    """Proxy: create a new account."""
    body = await request.json()
    return await _proxy_post("/api/accounts/", body=body)


@router.get("/api/osrs/accounts/search")
async def proxy_search_accounts(
    q: str = Query(...),
    limit: Optional[int] = Query(None),
) -> JSONResponse:
    """Proxy: search accounts by name."""
    return await _proxy_get("/api/accounts/search", params={
        "q": q,
        "limit": limit,
    })


@router.get("/api/osrs/accounts/{name}")
async def proxy_get_account(
    name: str,
    include_latest_snapshot: Optional[bool] = Query(None),
) -> JSONResponse:
    """Proxy: get account details."""
    _validate_path_param(name, "account name")
    return await _proxy_get(f"/api/accounts/{name}", params={
        "include_latest_snapshot": include_latest_snapshot,
    })


@router.delete("/api/osrs/accounts/{name}")
async def proxy_delete_account(
    name: str,
) -> JSONResponse:
    """Proxy: delete an account."""
    _validate_path_param(name, "account name")
    return await _proxy_delete(f"/api/accounts/{name}")


@router.get("/api/osrs/accounts/{name}/snapshots")
async def proxy_get_account_snapshots(
    name: str,
    page: Optional[int] = Query(None),
    page_size: Optional[int] = Query(None),
    include_skills: Optional[bool] = Query(None),
    include_activities: Optional[bool] = Query(None),
) -> JSONResponse:
    """Proxy: get snapshots for a specific account."""
    _validate_path_param(name, "account name")
    return await _proxy_get(f"/api/accounts/{name}/snapshots", params={
        "page": page,
        "page_size": page_size,
        "include_skills": include_skills,
        "include_activities": include_activities,
    })


# ===========================================================================
# Snapshots (5 endpoints)
# ===========================================================================

@router.get("/api/osrs/snapshots/latest")
async def proxy_latest_snapshots(
    limit: Optional[int] = Query(None),
    account_name: Optional[str] = Query(None),
    mode: Optional[str] = Query(None),
) -> JSONResponse:
    """Proxy: get latest snapshots."""
    return await _proxy_get("/api/snapshots/latest", params={
        "limit": limit,
        "account_name": account_name,
        "mode": mode,
    })


@router.post("/api/osrs/snapshots/run")
async def proxy_run_snapshots(
    request: Request,
) -> JSONResponse:
    """Proxy: trigger snapshot agent run."""
    body = await request.json()
    return await _proxy_post("/api/snapshots/run", body=body)


@router.get("/api/osrs/snapshots/{id}")
async def proxy_get_snapshot(
    id: str,
    include_deltas: Optional[bool] = Query(None),
) -> JSONResponse:
    """Proxy: get snapshot details."""
    _validate_path_param(id, "snapshot id")
    return await _proxy_get(f"/api/snapshots/{id}", params={
        "include_deltas": include_deltas,
    })


@router.get("/api/osrs/snapshots/{id}/deltas")
async def proxy_get_snapshot_deltas(
    id: str,
) -> JSONResponse:
    """Proxy: get snapshot deltas."""
    _validate_path_param(id, "snapshot id")
    return await _proxy_get(f"/api/snapshots/{id}/deltas")


@router.get("/api/osrs/snapshots/{id}/raw", response_model=None)
async def proxy_get_snapshot_raw(
    id: str,
):
    """Proxy: get raw snapshot payload (PlainText passthrough)."""
    _validate_path_param(id, "snapshot id")
    return await _proxy_get(f"/api/snapshots/{id}/raw", raw_text=True)


@router.get("/api/osrs/snapshots/{id}/report", response_model=None)
async def proxy_get_snapshot_report(
    id: str,
):
    """Proxy: get snapshot report (Markdown passthrough)."""
    _validate_path_param(id, "snapshot id")
    return await _proxy_get(f"/api/snapshots/{id}/report", raw_text=True)


# ===========================================================================
# Compare (2 endpoints) - NOTE: targets web-only routes, NOT /api/
# ===========================================================================

@router.get("/api/osrs/compare/data")
async def proxy_compare_data(
    a: str = Query(...),
    b: str = Query(...),
    timeframe: Optional[str] = Query(None),
) -> JSONResponse:
    """Proxy: get comparison data for two players."""
    return await _proxy_get("/compare/data", params={
        "a": a,
        "b": b,
        "timeframe": timeframe,
    })


@router.get("/api/osrs/compare/search")
async def proxy_compare_search(
    q: str = Query(...),
) -> JSONResponse:
    """Proxy: search for accounts (compare autocomplete)."""
    return await _proxy_get("/compare/search", params={
        "q": q,
    })
