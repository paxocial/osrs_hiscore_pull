"""Routes for account comparison (head-to-head and search)."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from web.services.comparison import ComparisonService
from web.services.profile_data import ProfileDataService

templates = Jinja2Templates(directory="web/templates")
router = APIRouter()
comparison = ComparisonService()
profile_data = ProfileDataService()


@router.get("/compare", response_class=HTMLResponse)
async def compare_page(
    request: Request,
    a: str = Query("", description="Player A name"),
    b: str = Query("", description="Player B name"),
    timeframe: str = Query("7d", description="Timeframe for gains"),
):
    """Head-to-head comparison page."""
    from web.deps import get_current_user, get_csrf_token

    data = None
    if a and b:
        data = comparison.head_to_head(a, b, timeframe)

    return templates.TemplateResponse("compare.html", {
        "request": request,
        "user": get_current_user(request),
        "csrf_token": get_csrf_token(request),
        "player_a": a,
        "player_b": b,
        "timeframe": timeframe,
        "data": data,
    })


@router.get("/compare/results", response_class=HTMLResponse)
async def compare_results(
    request: Request,
    a: str = Query("", description="Player A name"),
    b: str = Query("", description="Player B name"),
    timeframe: str = Query("7d", description="Timeframe for gains"),
):
    """HTMX partial: returns just the comparison results."""
    from web.deps import get_current_user

    data = None
    if a and b:
        data = comparison.head_to_head(a, b, timeframe)

    return templates.TemplateResponse("partials/compare_results.html", {
        "request": request,
        "player_a": a,
        "player_b": b,
        "timeframe": timeframe,
        "data": data,
    })


@router.get("/compare/data", response_class=JSONResponse)
async def compare_data(
    request: Request,
    a: str = Query(..., description="Player A name"),
    b: str = Query(..., description="Player B name"),
    timeframe: str = Query("7d"),
):
    """JSON endpoint for comparison data (charts + HTMX)."""
    data = comparison.head_to_head(a, b, timeframe)

    # Attach series for chart overlay
    series_a = profile_data.get_series(a)
    series_b = profile_data.get_series(b)
    data["series"] = {
        a: series_a.get("series", []),
        b: series_b.get("series", []),
    }

    return data


@router.get("/compare/search", response_class=JSONResponse)
async def compare_search(
    request: Request,
    q: str = Query("", description="Search query"),
):
    """Autocomplete search for account names."""
    if len(q) < 2:
        return {"results": []}
    results = comparison.search_accounts(q, limit=10)
    return {"results": results}
