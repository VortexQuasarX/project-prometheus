"""OpenTelemetry adapter stub (no-op until OTLP export is enabled).

The MVP stores traces/metrics in SQLite (see ``trace_store``/``metrics_store``);
this adapter maps the same events onto OTel span/metric concepts so a real
exporter can be plugged in later without changing producers.
"""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.observability.trace_store import TRACE_EVENT_NAMES

logger = get_logger("prometheus.otel")

TRACE_EVENT_TO_SPAN: dict[str, str] = {name: f"prometheus.{name}" for name in TRACE_EVENT_NAMES}


class OTelAdapter:
    """No-op OpenTelemetry adapter. ``enabled=True`` emits debug logs only."""

    def __init__(self, enabled: bool = False) -> None:
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        return self._enabled

    def export_trace_event(self, event: dict[str, Any]) -> None:
        if not self._enabled:
            return
        span_name = TRACE_EVENT_TO_SPAN.get(str(event.get("name", "")), "prometheus.event")
        logger.debug("otel span (stub): %s", span_name)

    def export_metric(self, name: str, value: float, attributes: dict[str, Any] | None = None) -> None:
        if not self._enabled:
            return
        logger.debug("otel metric (stub): %s=%s attrs=%s", name, value, attributes)

    def shutdown(self) -> None:
        logger.debug("otel adapter shutdown (no-op)")


otel_adapter = OTelAdapter()
