"""Prometheus metrics + OpenTelemetry tracing (production observability).

- ``/metrics`` exposes Prometheus-format counters/histograms (scrape target).
- ``tracing`` provides real OpenTelemetry spans around pipeline steps; the
  exporter is selected by ``OTEL_TRACES_EXPORTER`` (console | otlp | none) and
  defaults to none for tests. Unit tests verify spans via an in-memory
  exporter, so tracing is genuinely exercised without external infrastructure.
"""
from __future__ import annotations

import os
import time
from typing import Any

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

REGISTRY = CollectorRegistry(auto_describe=True)

REQUESTS_TOTAL = Counter(
    "prometheus_requests_total",
    "Total chat requests processed",
    ["model", "router_decision", "cache_hit"],
    registry=REGISTRY,
)
REQUEST_LATENCY = Histogram(
    "prometheus_request_latency_seconds",
    "Chat request latency in seconds",
    ["model"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=REGISTRY,
)
TOKENS_TOTAL = Counter(
    "prometheus_tokens_total",
    "Total LLM tokens processed",
    ["model", "direction"],
    registry=REGISTRY,
)
COST_USD_TOTAL = Counter(
    "prometheus_cost_usd_total",
    "Total estimated cost in USD",
    ["model"],
    registry=REGISTRY,
)
CACHE_SAVINGS_USD_TOTAL = Counter(
    "prometheus_cache_savings_usd_total",
    "Total cache savings in USD",
    registry=REGISTRY,
)
ERRORS_TOTAL = Counter(
    "prometheus_errors_total",
    "Total failed requests",
    ["error_type"],
    registry=REGISTRY,
)
IN_FLIGHT = Gauge(
    "prometheus_requests_in_flight",
    "Requests currently being processed",
    registry=REGISTRY,
)


def metrics_payload() -> bytes:
    """Render the Prometheus exposition format for the /metrics route."""
    return generate_latest(REGISTRY)


def record_request(
    model: str,
    router_decision: str,
    cache_hit: bool,
    latency_seconds: float,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    cache_saved_usd: float,
) -> None:
    """Update all request-level metrics (called at the end of the pipeline)."""
    REQUESTS_TOTAL.labels(
        model=model, router_decision=router_decision, cache_hit=str(bool(cache_hit))
    ).inc()
    REQUEST_LATENCY.labels(model=model).observe(latency_seconds)
    TOKENS_TOTAL.labels(model=model, direction="input").inc(input_tokens)
    TOKENS_TOTAL.labels(model=model, direction="output").inc(output_tokens)
    COST_USD_TOTAL.labels(model=model).inc(cost_usd)
    if cache_saved_usd > 0:
        CACHE_SAVINGS_USD_TOTAL.inc(cache_saved_usd)


def record_error(error_type: str) -> None:
    ERRORS_TOTAL.labels(error_type=error_type).inc()


# --------------------------------------------------------------------------
# OpenTelemetry tracing
# --------------------------------------------------------------------------
_TRACER: Any = None
_TRACER_READY = False


def _init_tracer() -> Any:
    """Build the OTel tracer according to OTEL_TRACES_EXPORTER (once)."""
    global _TRACER, _TRACER_READY
    if _TRACER_READY:
        return _TRACER
    _TRACER_READY = True
    exporter_kind = os.environ.get("OTEL_TRACES_EXPORTER", "none").strip().lower()
    if exporter_kind == "none":
        return None
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider

        provider = TracerProvider(
            resource=Resource.create({"service.name": "prometheus-api"})
        )
        if exporter_kind == "console":
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter

            provider.add_span_processor(
                __import__(
                    "opentelemetry.sdk.trace.export", fromlist=["BatchSpanProcessor"]
                ).BatchSpanProcessor(ConsoleSpanExporter())
            )
        elif exporter_kind in ("otlp", "otlp-http"):
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            endpoint = os.environ.get(
                "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
                "http://localhost:4318/v1/traces",
            )
            provider.add_span_processor(
                BatchSpanProcessor(
                    OTLPSpanExporter(endpoint=endpoint)
                )
            )
        else:
            return None
        trace.set_tracer_provider(provider)
        _TRACER = trace.get_tracer("prometheus.pipeline")
    except Exception:  # noqa: BLE001 - observability must never break the app
        _TRACER = None
    return _TRACER


def start_span(name: str, attributes: dict[str, Any] | None = None) -> Any:
    """Start an OTel span (or a no-op context manager when tracing is off)."""
    tracer = _init_tracer()
    if tracer is None:
        import contextlib

        return contextlib.nullcontext()
    return tracer.start_as_current_span(name, attributes=attributes or {})


def record_span_duration(name: str, duration_ms: int, attributes: dict[str, Any] | None = None) -> None:
    """Convenience: record a completed step duration as a span event."""
    tracer = _init_tracer()
    if tracer is None:
        return
    with tracer.start_as_current_span(name, attributes={**(attributes or {}), "duration_ms": duration_ms}):
        pass


class Timer:
    """Context manager measuring wall time in ms (for spans and traces)."""

    def __init__(self) -> None:
        self.ms = 0

    def __enter__(self) -> Timer:
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.ms = int((time.perf_counter() - self._start) * 1000)
