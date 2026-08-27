"""Higher-level event logging helpers (distinct from core/logging setup).

core/logging.py owns the JSON formatter and masking; this module adds
request-context binding and structured ``log_event`` calls for observability
consumers.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator

from app.core.security import mask_sensitive

request_id_var: ContextVar[str | None] = ContextVar("prometheus_request_id", default=None)

logger = logging.getLogger("prometheus.observability")


def current_request_id() -> str | None:
    """Request id bound to the current context (None outside a request)."""
    return request_id_var.get()


@contextmanager
def bind_request_context(request_id: str | None) -> Iterator[None]:
    """Bind a request id for the duration of the block (contextvar-scoped)."""
    token = request_id_var.set(request_id)
    try:
        yield
    finally:
        request_id_var.reset(token)


def log_event(event: str, *, level: int = logging.INFO, **fields: Any) -> None:
    """Emit a structured event log line; string fields are PII-masked."""
    safe_fields = {
        key: mask_sensitive(value) if isinstance(value, str) else value
        for key, value in fields.items()
    }
    extra = {"event": event, **safe_fields}
    request_id = current_request_id()
    if request_id:
        extra["request_id"] = request_id
    logger.log(level, event, extra=extra)
