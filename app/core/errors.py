"""Error hierarchy and the unified error envelope.

Every error response has the shape::

    {"request_id": "...", "error": {"code": "...", "message": "...", "details": ...}}

``register_exception_handlers(app)`` is called by ``app.main`` (another build
slice); handlers map PrometheusError / HTTPException / validation / unexpected
exceptions onto the envelope with the request id injected by
RequestContextMiddleware.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from starlette.responses import JSONResponse

logger = logging.getLogger("prometheus.errors")

_HTTP_CODE_MAP: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    429: "rate_limit_exceeded",
    500: "internal_error",
}


class PrometheusError(Exception):
    """Base application error carrying an HTTP status and error code."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "prometheus_error",
        status_code: int = 400,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class UnauthorizedError(PrometheusError):
    def __init__(self, message: str = "Authentication required", details: Any = None) -> None:
        super().__init__(message, code="unauthorized", status_code=401, details=details)


class ForbiddenError(PrometheusError):
    def __init__(self, message: str = "Forbidden", details: Any = None) -> None:
        super().__init__(message, code="forbidden", status_code=403, details=details)


class NotFoundError(PrometheusError):
    def __init__(self, message: str = "Not found", details: Any = None) -> None:
        super().__init__(message, code="not_found", status_code=404, details=details)


class ConflictError(PrometheusError):
    def __init__(self, message: str = "Conflict", details: Any = None) -> None:
        super().__init__(message, code="conflict", status_code=409, details=details)


class RateLimitError(PrometheusError):
    def __init__(self, message: str = "Rate limit exceeded", details: Any = None) -> None:
        super().__init__(message, code="rate_limit_exceeded", status_code=429, details=details)


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any = None


class ErrorEnvelope(BaseModel):
    request_id: str
    error: ErrorDetail


def error_response(request_id: str, code: str, message: str, details: Any = None) -> dict[str, Any]:
    """Build the canonical error envelope dict."""
    return {
        "request_id": request_id,
        "error": {"code": code, "message": message, "details": details},
    }


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or uuid.uuid4().hex


def _envelope_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
) -> JSONResponse:
    request_id = _request_id(request)
    return JSONResponse(
        status_code=status_code,
        content=error_response(request_id, code, message, details),
        headers={"X-Request-Id": request_id},
    )


def _sanitize_validation_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Strip submitted input values (potential PII) from pydantic error detail."""
    sanitized: list[dict[str, Any]] = []
    for error in errors:
        cleaned = {key: value for key, value in error.items() if key != "input"}
        ctx = dict(error.get("ctx") or {})
        ctx.pop("input", None)
        if ctx:
            cleaned["ctx"] = ctx
        sanitized.append(cleaned)
    return sanitized


def register_exception_handlers(app: FastAPI) -> None:
    """Register envelope-producing handlers for all error classes."""

    @app.exception_handler(PrometheusError)
    async def _prometheus_error_handler(request: Request, exc: PrometheusError) -> JSONResponse:
        return _envelope_response(request, exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(HTTPException)
    async def _http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        status = exc.status_code
        code = _HTTP_CODE_MAP.get(status, f"http_{status}")
        message = str(exc.detail) if exc.detail else "HTTP error"
        return _envelope_response(request, status, code, message)

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = _sanitize_validation_errors(exc.errors())
        return _envelope_response(request, 422, "validation_error", "Request validation failed", details)

    @app.exception_handler(Exception)
    async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled exception while serving %s %s", request.method, request.url.path, exc_info=exc
        )
        return _envelope_response(request, 500, "internal_error", "Internal server error")
