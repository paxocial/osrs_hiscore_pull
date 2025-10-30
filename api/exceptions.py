"""Custom exception handlers for OSRS Analytics API."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Union
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from api.schemas import ErrorResponse, ValidationErrorResponse

logger = logging.getLogger(__name__)


class OSRSAnalyticsException(Exception):
    """Base exception for OSRS Analytics API."""

    def __init__(
        self,
        message: str,
        error_code: str = "analytics_error",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Union[dict, None] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class DatabaseException(OSRSAnalyticsException):
    """Database-related exceptions."""

    def __init__(self, message: str, details: Union[dict, None] = None):
        super().__init__(
            message=message,
            error_code="database_error",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details
        )


class DataNotFoundException(OSRSAnalyticsException):
    """Exception for when requested data is not found."""

    def __init__(self, message: str, details: Union[dict, None] = None):
        super().__init__(
            message=message,
            error_code="not_found",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details
        )


class ValidationException(OSRSAnalyticsException):
    """Exception for validation errors."""

    def __init__(self, message: str, details: Union[dict, None] = None):
        super().__init__(
            message=message,
            error_code="validation_error",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class RateLimitException(OSRSAnalyticsException):
    """Exception for rate limiting."""

    def __init__(self, message: str = "Rate limit exceeded", details: Union[dict, None] = None):
        super().__init__(
            message=message,
            error_code="rate_limit_exceeded",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details
        )


async def osrs_analytics_exception_handler(request: Request, exc: OSRSAnalyticsException) -> JSONResponse:
    """Handle custom OSRS Analytics exceptions."""
    logger.error(
        f"OSRS Analytics Exception: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details,
            "path": str(request.url),
            "method": request.method
        }
    )

    response_data = ErrorResponse(
        error=exc.error_code,
        message=exc.message,
        details=exc.details,
        timestamp=datetime.now()
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=response_data.model_dump(mode="json")
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle standard HTTP exceptions."""
    logger.warning(
        f"HTTP Exception: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": str(request.url),
            "method": request.method
        }
    )

    # Map HTTP status codes to error types
    error_type_map = {
        status.HTTP_400_BAD_REQUEST: "bad_request",
        status.HTTP_401_UNAUTHORIZED: "unauthorized",
        status.HTTP_403_FORBIDDEN: "forbidden",
        status.HTTP_404_NOT_FOUND: "not_found",
        status.HTTP_405_METHOD_NOT_ALLOWED: "method_not_allowed",
        status.HTTP_422_UNPROCESSABLE_ENTITY: "validation_error",
        status.HTTP_429_TOO_MANY_REQUESTS: "rate_limit_exceeded",
        status.HTTP_500_INTERNAL_SERVER_ERROR: "internal_error",
        status.HTTP_502_BAD_GATEWAY: "bad_gateway",
        status.HTTP_503_SERVICE_UNAVAILABLE: "service_unavailable",
        status.HTTP_504_GATEWAY_TIMEOUT: "gateway_timeout"
    }

    error_type = error_type_map.get(exc.status_code, "http_error")

    response_data = ErrorResponse(
        error=error_type,
        message=str(exc.detail),
        timestamp=datetime.now()
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=response_data.model_dump(mode="json")
    )


async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    logger.warning(
        f"Validation Error: {len(exc.errors())} validation errors",
        extra={
            "validation_errors": exc.errors(),
            "path": str(request.url),
            "method": request.method
        }
    )

    # Format validation errors for response
    formatted_errors = []
    for error in exc.errors():
        formatted_errors.append({
            "field": ".".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input")
        })

    response_data = ValidationErrorResponse(
        error="validation_error",
        message="Request validation failed",
        validation_errors=formatted_errors,
        timestamp=datetime.now()
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response_data.model_dump(mode="json")
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle any uncaught exceptions."""
    logger.error(
        f"Unhandled Exception: {type(exc).__name__} - {str(exc)}",
        extra={
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "path": str(request.url),
            "method": request.method
        },
        exc_info=True
    )

    response_data = ErrorResponse(
        error="internal_error",
        message="An unexpected error occurred. Please try again later.",
        timestamp=datetime.now()
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response_data.model_dump(mode="json")
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI app."""
    app.add_exception_handler(OSRSAnalyticsException, osrs_analytics_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)