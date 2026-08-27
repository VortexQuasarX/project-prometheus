"""Structured (JSON-line) logging with PII masking.

The formatter masks emails / phones / cards / tokens via
:mod:`app.core.security` at format time, so sensitive values never reach
the console or log files. core/logging.py = setup + masking;
observability/logger.py = higher-level event helpers.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings

_MASKABLE_KEYS = ("request_id", "event", "model", "provider", "duration_ms", "status_code")


class JsonFormatter(logging.Formatter):
    """Emit one compact JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        # Lazy import: core.security imports db/session, and core.logging must
        # not create an import cycle at module load time.
        from app.core.security import mask_sensitive

        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": mask_sensitive(record.getMessage()),
        }
        for key in _MASKABLE_KEYS:
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging(level: str | int | None = None) -> None:
    """Configure the root logger with the JSON formatter (idempotent)."""
    resolved = str(level or settings.log_level or "INFO").upper()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.setLevel(resolved)
    root.handlers = [handler]
    # Keep library noise down without silencing app loggers.
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger (formatting/masking applied at the root)."""
    return logging.getLogger(name)
