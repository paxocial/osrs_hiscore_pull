"""FastAPI application for OSRS Hiscore Analytics.

This module provides REST API endpoints for accessing OSRS hiscore data,
analytics, and insights. Built with FastAPI and Pydantic v2 for high performance
and automatic documentation.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from api.dependencies import rate_limiter
from api.exceptions import setup_exception_handlers
from api.endpoints import accounts, snapshots, analytics
from api import test_accounts

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle events."""
    # Startup
    logger.info("Starting OSRS Analytics API...")

    # Simple database initialization
    try:
        from pathlib import Path
        import sqlite3

        db_path = Path("data/analytics.db")
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Simple initialization check - just ensure directory exists
        # Database schema will be created by migrations as needed
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise RuntimeError("Database initialization failed")

    logger.info("OSRS Analytics API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down OSRS Analytics API...")


# Create FastAPI application
app = FastAPI(
    title="OSRS Prometheus Analytics API",
    description="""
    REST API for Old School RuneScape hiscore analytics and insights.

    ## Features

    * **Account Management**: Browse and manage OSRS accounts
    * **Snapshot Data**: Access historical hiscore snapshots with skills and activities
    * **Analytics**: Progress tracking, XP rates, milestones, and comparisons
    * **Real-time**: Up-to-date data from the OSRS hiscores API

    ## Game Modes Supported

    * Regular (main)
    * Ironman
    * Hardcore Ironman
    * Ultimate Ironman
    * Deadman Mode
    * Tournament
    * Seasonal (Leagues)

    ## Rate Limiting

    API is rate-limited to 100 requests per minute per IP address for development.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    contact={
        "name": "OSRS Analytics Support",
        "url": "https://github.com/yourusername/osrs_hiscore_pull",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    }
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Gzip compression for better performance
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Apply rate limiting to incoming requests."""
    client_ip = request.client.host if request.client else "unknown"

    if not rate_limiter.is_allowed(client_ip):
        from api.exceptions import RateLimitException
        raise RateLimitException(
            "Rate limit exceeded. Maximum 100 requests per minute allowed.",
            details={"limit": 100, "window_seconds": 60, "client_ip": client_ip}
        )

    response = await call_next(request)
    return response


# Request logging middleware
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log API requests with timing information."""
    import time

    start_time = time.time()

    # Log request
    logger.info(
        f"API Request: {request.method} {request.url}",
        extra={
            "method": request.method,
            "url": str(request.url),
            "client_ip": request.client.host if request.client else "unknown"
        }
    )

    response = await call_next(request)

    # Log response with timing
    process_time = time.time() - start_time
    logger.info(
        f"API Response: {request.method} {request.url} - {response.status_code} ({process_time:.3f}s)",
        extra={
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "process_time": process_time
        }
    )

    # Add timing header
    response.headers["X-Process-Time"] = str(process_time)

    return response


# Setup exception handlers
setup_exception_handlers(app)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring."""
    try:
        import sqlite3
        from pathlib import Path

        db_path = Path("data/analytics.db")
        if not db_path.exists():
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "database": "missing",
                    "error": "Database file not found"
                }
            )

        # Test database connection and get stats
        conn = sqlite3.connect(db_path, check_same_thread=False)
        cursor = conn.cursor()

        # Get basic stats
        accounts_count = cursor.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
        snapshots_count = cursor.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
        schema_version = cursor.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1").fetchone()

        conn.close()

        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "database": "connected",
                "stats": {
                    "accounts": accounts_count,
                    "snapshots": snapshots_count,
                    "schema_version": schema_version[0] if schema_version else "unknown"
                }
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "error",
                "error": str(e)
            }
        )


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "OSRS Prometheus Analytics API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "accounts": "/accounts",
            "snapshots": "/snapshots",
            "analytics": "/analytics"
        }
    }


# Include API routers
app.include_router(
    test_accounts.router,
    prefix="/test",
    tags=["Test"],
    responses={404: {"description": "Not found"}}
)

app.include_router(
    accounts.router,
    prefix="/accounts",
    tags=["Accounts"],
    responses={404: {"description": "Not found"}}
)

app.include_router(
    snapshots.router,
    prefix="/snapshots",
    tags=["Snapshots"],
    responses={404: {"description": "Not found"}}
)

app.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["Analytics"],
    responses={404: {"description": "Not found"}}
)


# Development server startup
if __name__ == "__main__":
    import uvicorn

    logger.info("Starting development server...")
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )